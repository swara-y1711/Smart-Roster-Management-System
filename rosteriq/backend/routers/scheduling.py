from __future__ import annotations

import calendar
from datetime import date, time
from typing import Any, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.auth import get_db
from database import handle_supabase_error
from models.scheduling import (
    GenerateRosterRequest,
    SchedulingImpactRequest,
    SchedulingImpactResponse,
    SchedulingResponse,
    ValidateRosterRequest,
)
from services.scheduling import (
    Assignment,
    Availability,
    Brand,
    CoverageRule,
    Employee,
    EmployeePreference,
    Pod,
    Process,
    ScheduleData,
    Shift,
    TimeOff,
    evaluate_impact,
    generate_monthly_roster,
    validate_roster,
    with_brand_operating_calendar,
    with_coverage_rule,
    with_operating_calendar,
    with_time_off,
)

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


def _select(
    db: Client,
    table: str,
    *,
    column: Optional[str] = None,
    value: Optional[str] = None,
    values: Optional[Sequence[str]] = None,
    lower_bound: Optional[tuple[str, str]] = None,
    upper_bound: Optional[tuple[str, str]] = None,
) -> list[dict[str, Any]]:
    if values is not None and not values:
        return []
    try:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = db.table(table).select("*")
            if column is not None and value is not None:
                query = query.eq(column, value)
            if column is not None and values is not None:
                query = query.in_(column, list(values))
            if lower_bound is not None:
                query = query.gte(lower_bound[0], lower_bound[1])
            if upper_bound is not None:
                query = query.lte(upper_bound[0], upper_bound[1])
            page = query.range(offset, offset + 999).execute().data or []
            rows.extend(page)
            if len(page) < 1000:
                return rows
            offset += 1000
    except Exception as error:
        handle_supabase_error(error, table.replace("_", " ").title())
        raise


def _as_time(value: Any) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        return time.fromisoformat(value)
    raise ValueError(f"Unsupported time value: {type(value).__name__}")


def load_schedule_data(
    db: Client,
    organization_id: str,
    first_day: date,
    last_day: date,
) -> ScheduleData:
    organization = _select(
        db, "organizations", column="id", value=organization_id
    )
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or you are not authorized to schedule it.",
        )

    brand_rows = _select(
        db, "brands", column="organization_id", value=organization_id
    )
    brand_ids = [str(row["id"]) for row in brand_rows]
    process_rows = _select(db, "processes", column="brand_id", values=brand_ids)
    process_ids = [str(row["id"]) for row in process_rows]
    pod_rows = _select(db, "pods", column="process_id", values=process_ids)
    pod_ids = [str(row["id"]) for row in pod_rows]
    employee_rows = _select(
        db, "employees", column="organization_id", value=organization_id
    )
    employee_ids = [str(row["id"]) for row in employee_rows]

    shift_rows = _select(db, "shifts", column="pod_id", values=pod_ids)
    employee_pod_rows = _select(
        db, "employee_pods", column="employee_id", values=employee_ids
    )
    availability_rows = _select(
        db, "employee_availability", column="employee_id", values=employee_ids
    )
    skill_rows = _select(
        db, "employee_skills", column="employee_id", values=employee_ids
    )
    weekly_off_rows = _select(
        db, "employee_weekly_offs", column="employee_id", values=employee_ids
    )
    time_off_rows = _select(
        db, "employee_time_off", column="employee_id", values=employee_ids
    )
    preference_rows = _select(
        db, "employee_preferences", column="employee_id", values=employee_ids
    )
    operating_rows = _select(
        db, "process_operating_rules", column="process_id", values=process_ids
    )
    override_rows = _select(
        db, "process_operating_overrides", column="process_id", values=process_ids
    )
    coverage_rows = _select(
        db, "process_coverage_requirements", column="process_id", values=process_ids
    )
    holiday_rows = _select(
        db,
        "public_holidays",
        column="organization_id",
        value=organization_id,
        lower_bound=("holiday_date", first_day.isoformat()),
        upper_bound=("holiday_date", last_day.isoformat()),
    )

    brands = {
        str(row["id"]): Brand(
            id=str(row["id"]),
            organization_id=str(row["organization_id"]),
            name=row["name"],
        )
        for row in brand_rows
    }
    operating_by_process = {
        str(row["process_id"]): row for row in operating_rows
    }
    processes = {}
    for row in process_rows:
        process_id = str(row["id"])
        operating = operating_by_process.get(process_id, {})
        processes[process_id] = Process(
            id=process_id,
            brand_id=str(row["brand_id"]),
            name=row["name"],
            operating_days=frozenset(
                int(day) for day in operating.get("operating_days", range(7))
            ),
            operates_on_public_holidays=bool(
                operating.get("operates_on_public_holidays", False)
            ),
        )
    pods = {
        str(row["id"]): Pod(
            id=str(row["id"]),
            process_id=str(row["process_id"]),
            name=row["name"],
        )
        for row in pod_rows
    }
    weekly_offs: dict[str, set[int]] = {}
    for row in weekly_off_rows:
        weekly_offs.setdefault(str(row["employee_id"]), set()).add(
            int(row["day_of_week"])
        )
    availability_by_employee: dict[str, list[Availability]] = {}
    for row in availability_rows:
        availability_by_employee.setdefault(str(row["employee_id"]), []).append(
            Availability(
                day_of_week=int(row["day_of_week"]),
                is_available=bool(row.get("is_available", True)),
                start_time=_as_time(row.get("start_time")),
                end_time=_as_time(row.get("end_time")),
            )
        )
    skills_by_employee: dict[str, set[str]] = {}
    for row in skill_rows:
        skills_by_employee.setdefault(str(row["employee_id"]), set()).add(
            str(row["skill_name"])
        )
    time_off_by_employee: dict[str, list[TimeOff]] = {}
    for row in time_off_rows:
        time_off_by_employee.setdefault(str(row["employee_id"]), []).append(
            TimeOff(
                start_date=date.fromisoformat(str(row["start_date"])[:10]),
                end_date=date.fromisoformat(str(row["end_date"])[:10]),
                kind=str(row["kind"]),
                status=str(row["status"]),
            )
        )
    preferences_by_employee: dict[str, list[EmployeePreference]] = {}
    for row in preference_rows:
        process_id = row.get("process_id")
        preferred_shift_id = row.get("preferred_shift_id")
        preferences_by_employee.setdefault(str(row["employee_id"]), []).append(
            EmployeePreference(
                process_id=str(process_id) if process_id else None,
                preferred_shift_id=(
                    str(preferred_shift_id) if preferred_shift_id else None
                ),
                preferred_days=frozenset(
                    int(day) for day in row.get("preferred_days_of_week") or []
                ),
                avoid_days=frozenset(
                    int(day) for day in row.get("avoid_days_of_week") or []
                ),
            )
        )
    employees = {}
    for row in employee_rows:
        employee_id = str(row["id"])
        max_hours = row.get("max_hours_per_week")
        employees[employee_id] = Employee(
            id=employee_id,
            organization_id=str(row["organization_id"]),
            name=" ".join(
                part for part in (row.get("first_name"), row.get("last_name")) if part
            ),
            active=str(row.get("status", "active")).lower() == "active",
            weekly_off_days=frozenset(weekly_offs.get(employee_id, set())),
            availability=tuple(availability_by_employee.get(employee_id, ())),
            time_off=tuple(time_off_by_employee.get(employee_id, ())),
            skills=frozenset(skills_by_employee.get(employee_id, set())),
            preferences=tuple(preferences_by_employee.get(employee_id, ())),
            max_hours_per_week=float(max_hours) if max_hours is not None else None,
        )

    shift_rows_by_id = {str(row["id"]): row for row in shift_rows}
    shifts = {
        shift_id: Shift(
            id=shift_id,
            pod_id=str(row["pod_id"]),
            name=row["shift_name"],
            start_time=_as_time(row["start_time"]) or time.min,
            end_time=_as_time(row["end_time"]) or time.min,
            required_headcount=int(row.get("required_headcount") or 1),
        )
        for shift_id, row in shift_rows_by_id.items()
    }
    for row in coverage_rows:
        shift_id = row.get("shift_id")
        if shift_id:
            shift = shifts.get(str(shift_id))
            pod = pods.get(shift.pod_id) if shift else None
            if pod is None or pod.process_id != str(row["process_id"]):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "A process coverage rule references a shift outside its "
                        "process. Correct the scheduling configuration before generating."
                    ),
                )
    employee_pods = frozenset(
        (str(row["employee_id"]), str(row["pod_id"]))
        for row in employee_pod_rows
        if str(row["pod_id"]) in pods
    )
    primary_employee_pods = frozenset(
        (str(row["employee_id"]), str(row["pod_id"]))
        for row in employee_pod_rows
        if row.get("is_primary") and str(row["pod_id"]) in pods
    )
    rules = tuple(
        CoverageRule(
            process_id=str(row["process_id"]),
            shift_id=str(row["shift_id"]) if row.get("shift_id") else None,
            target_date=(
                date.fromisoformat(str(row["target_date"])[:10])
                if row.get("target_date")
                else None
            ),
            day_of_week=(
                int(row["day_of_week"]) if row.get("day_of_week") is not None else None
            ),
            minimum_staff=int(row["minimum_staff"]),
        )
        for row in coverage_rows
    )
    operating_overrides = {
        (
            str(row["process_id"]),
            date.fromisoformat(str(row["operating_date"])[:10]),
        ): bool(row["is_operating"])
        for row in override_rows
    }
    return ScheduleData(
        organization_id=organization_id,
        brands=brands,
        processes=processes,
        pods=pods,
        employees=employees,
        shifts=shifts,
        employee_pods=employee_pods,
        primary_employee_pods=primary_employee_pods,
        coverage_rules=rules,
        public_holidays=frozenset(
            date.fromisoformat(str(row["holiday_date"])[:10])
            for row in holiday_rows
        ),
        operating_overrides=operating_overrides,
    )


def _assignment_response(data: ScheduleData, assignment: Assignment) -> dict[str, Any]:
    employee = data.employees.get(assignment.employee_id)
    shift = data.shifts.get(assignment.shift_id)
    pod = data.pods.get(shift.pod_id) if shift else None
    process = data.processes.get(pod.process_id) if pod else None
    brand = data.brands.get(process.brand_id) if process else None
    return {
        "assignment_date": assignment.assignment_date,
        "employee_id": assignment.employee_id,
        "employee_name": employee.name if employee else None,
        "brand_id": brand.id if brand else None,
        "brand": brand.name if brand else None,
        "process_id": process.id if process else None,
        "process": process.name if process else None,
        "pod_id": pod.id if pod else None,
        "pod": pod.name if pod else None,
        "shift_id": assignment.shift_id,
        "shift": shift.name if shift else None,
        "start_time": shift.start_time.isoformat() if shift else None,
        "end_time": shift.end_time.isoformat() if shift else None,
    }


def _report_response(
    data: ScheduleData, report: Any, organization_id: str
) -> dict[str, Any]:
    coverage = [
        {
            "date": row.date,
            "brand_id": row.brand_id,
            "brand": row.brand,
            "process_id": row.process_id,
            "process": row.process,
            "shift_id": row.shift_id,
            "shift": row.shift,
            "required_staff": row.required_staff,
            "actual_staff": row.actual_staff,
            "unfilled_positions": list(row.unfilled_positions),
        }
        for row in report.coverage
    ]
    conflicts = [
        {
            "date": row.date,
            "brand_id": row.brand_id,
            "brand": row.brand,
            "process_id": row.process_id,
            "process": row.process,
            "employee_id": row.employee_id,
            "conflict_type": row.conflict_type,
            "severity": row.severity,
            "explanation": row.explanation,
            "suggested_resolution": row.suggested_resolution,
        }
        for row in report.conflicts
    ]
    return {
        "organization_id": organization_id,
        "is_valid": report.valid,
        "assignments": [
            _assignment_response(data, assignment)
            for assignment in report.assignments
        ],
        "coverage_summary": coverage,
        "required_staffing": int(report.statistics["required_positions"]),
        "actual_staffing": int(report.statistics["filled_positions"]),
        "unfilled_positions": [
            row for row in coverage if row["unfilled_positions"]
        ],
        "conflicts": conflicts,
        "warnings": [row for row in conflicts if row["severity"] == "warning"],
        "statistics": report.statistics,
    }


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


@router.post(
    "/generate",
    response_model=SchedulingResponse,
    summary="Generate a monthly roster proposal",
)
def generate_roster(
    payload: GenerateRosterRequest,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    first_day, last_day = _month_bounds(payload.year, payload.month)
    data = load_schedule_data(db, str(payload.organization_id), first_day, last_day)
    report = generate_monthly_roster(data, payload.year, payload.month)
    return _report_response(data, report, str(payload.organization_id))


@router.post(
    "/validate",
    response_model=SchedulingResponse,
    summary="Validate a proposed or modified roster",
)
def validate_proposed_roster(
    payload: ValidateRosterRequest,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    first_day, last_day = _month_bounds(payload.year, payload.month)
    data = load_schedule_data(db, str(payload.organization_id), first_day, last_day)
    assignments = [
        Assignment(
            employee_id=str(row.employee_id),
            shift_id=str(row.shift_id),
            assignment_date=row.assignment_date,
        )
        for row in payload.assignments
    ]
    report = validate_roster(data, assignments, first_day, last_day)
    return _report_response(data, report, str(payload.organization_id))


def _apply_change(data: ScheduleData, request: SchedulingImpactRequest) -> ScheduleData:
    change = request.change
    if change.change_type in {
        "employee_unavailable",
        "planned_leave",
        "approved_leave",
        "approved_comp_off",
    }:
        employee_id = str(change.employee_id)
        if employee_id not in data.employees:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found in this organization.",
            )
        kinds = {
            "employee_unavailable": ("unavailability", "active"),
            "planned_leave": ("leave", "planned"),
            "approved_leave": ("leave", "approved"),
            "approved_comp_off": ("comp_off", "approved"),
        }
        kind, state = kinds[change.change_type]
        return with_time_off(
            data,
            employee_id,
            change.start_date,
            change.end_date,
            kind,
            state,
        )
    if change.change_type == "coverage_requirement":
        process_id = str(change.process_id)
        if process_id not in data.processes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found in this organization.",
            )
        shift_id = str(change.shift_id) if change.shift_id else None
        if shift_id:
            shift = data.shifts.get(shift_id)
            pod = data.pods.get(shift.pod_id) if shift else None
            if pod is None or pod.process_id != process_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The shift does not belong to the selected process.",
                )
        exact_date = change.target_date
        rule = CoverageRule(
            process_id=process_id,
            shift_id=shift_id,
            target_date=exact_date,
            effective_from=(
                request.start_date if exact_date is None else None
            ),
            effective_to=(
                request.end_date if exact_date is None else None
            ),
            minimum_staff=change.minimum_staff,
        )
        return with_coverage_rule(data, rule)
    if change.brand_id is not None:
        brand_id = str(change.brand_id)
        if brand_id not in data.brands:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand not found in this organization.",
            )
        return with_brand_operating_calendar(
            data,
            brand_id,
            frozenset(change.operating_days),
            bool(change.operates_on_public_holidays),
        )
    process_id = str(change.process_id)
    if process_id not in data.processes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found in this organization.",
        )
    return with_operating_calendar(
        data,
        process_id,
        frozenset(change.operating_days),
        bool(change.operates_on_public_holidays),
    )


def _load_existing_assignments(
    db: Client,
    data: ScheduleData,
    first_day: date,
    last_day: date,
) -> list[Assignment]:
    employee_ids = list(data.employees)
    if not employee_ids:
        return []
    try:
        rows = (
            db.table("roster_assignments")
            .select("*")
            .in_("employee_id", employee_ids)
            .gte("assignment_date", first_day.isoformat())
            .lte("assignment_date", last_day.isoformat())
            .execute()
            .data
            or []
        )
    except Exception as error:
        handle_supabase_error(error, "Roster Assignment")
        raise
    active_statuses = {"scheduled", "assigned", "confirmed"}
    return [
        Assignment(
            employee_id=str(row["employee_id"]),
            shift_id=str(row["shift_id"]),
            assignment_date=date.fromisoformat(str(row["assignment_date"])[:10]),
        )
        for row in rows
        if str(row.get("status") or "scheduled").lower() in active_statuses
        and str(row.get("shift_id")) in data.shifts
    ]


@router.post(
    "/impact",
    response_model=SchedulingImpactResponse,
    summary="Evaluate workforce or scheduling-rule changes",
)
def scheduling_impact(
    payload: SchedulingImpactRequest,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    data = load_schedule_data(
        db,
        str(payload.organization_id),
        payload.start_date,
        payload.end_date,
    )
    assignments = _load_existing_assignments(
        db, data, payload.start_date, payload.end_date
    )
    updated_data = _apply_change(data, payload)
    impact = evaluate_impact(
        data,
        updated_data,
        assignments,
        payload.start_date,
        payload.end_date,
    )
    report = impact["report"]
    response = _report_response(updated_data, report, str(payload.organization_id))
    backups_by_assignment = {
        (
            item["date"],
            item["process_id"],
            item["shift_id"],
        ): list(item["employee_ids"])
        for item in impact["recommended_backups"]
    }
    affected = []
    for item in impact["invalidated_assignments"]:
        assignment = item["assignment"]
        key = (
            assignment.assignment_date,
            item["process_id"],
            item["shift_id"],
        )
        affected.append({
            "assignment": _assignment_response(data, assignment),
            "reason": item["reason"],
            "conflict_type": item["conflict_type"],
            "suggested_resolution": item["suggested_resolution"],
            "possible_backup_employee_ids": backups_by_assignment.get(key, []),
        })
    return {
        "organization_id": str(payload.organization_id),
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "invalidated_assignments": affected,
        "replacement_assignments": [
            _assignment_response(updated_data, assignment)
            for assignment in impact["replacement_assignments"]
        ],
        "coverage_summary": response["coverage_summary"],
        "conflicts": response["conflicts"],
        "warnings": response["warnings"],
        "required_staffing": response["required_staffing"],
        "actual_staffing": response["actual_staffing"],
        "unfilled_positions": response["unfilled_positions"],
        "statistics": response["statistics"],
    }
