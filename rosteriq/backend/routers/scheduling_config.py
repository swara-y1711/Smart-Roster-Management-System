from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from app.auth import get_db
from database import handle_supabase_error
from models.scheduling import (
    CoverageRequirementCreate,
    CoverageRequirementUpdate,
    EmployeePreferenceCreate,
    EmployeePreferenceUpdate,
    OperatingOverrideCreate,
    OperatingOverrideUpdate,
    OperatingRuleCreate,
    OperatingRuleUpdate,
    PublicHolidayCreate,
    PublicHolidayUpdate,
    TimeOffCreate,
    TimeOffUpdate,
    WeeklyOffCreate,
)

router = APIRouter(prefix="/scheduling", tags=["Scheduling Configuration"])


def _execute(query: Any, resource: str) -> list[dict[str, Any]]:
    try:
        return query.execute().data or []
    except Exception as error:
        handle_supabase_error(error, resource)
        raise


def _one(
    db: Client,
    table: str,
    resource: str,
    **filters: str,
) -> dict[str, Any]:
    query = db.table(table).select("*")
    for column, value in filters.items():
        query = query.eq(column, value)
    rows = _execute(query.limit(1), resource)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found or you are not authorized to access it.",
        )
    return rows[0]


def _require_organization(db: Client, organization_id: UUID) -> dict[str, Any]:
    return _one(db, "organizations", "Organization", id=str(organization_id))


def _require_employee(db: Client, employee_id: UUID) -> dict[str, Any]:
    return _one(db, "employees", "Employee", id=str(employee_id))


def _require_process(db: Client, process_id: UUID) -> tuple[dict[str, Any], str]:
    process = _one(db, "processes", "Process", id=str(process_id))
    brand = _one(db, "brands", "Brand", id=str(process["brand_id"]))
    return process, str(brand["organization_id"])


def _require_employee_process(
    db: Client,
    employee_id: UUID,
    process_id: Optional[UUID],
    shift_id: Optional[UUID],
) -> tuple[dict[str, Any], Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    employee = _require_employee(db, employee_id)
    process = None
    shift = None
    if shift_id is not None:
        shift = _one(db, "shifts", "Shift", id=str(shift_id))
        pod = _one(db, "pods", "Pod", id=str(shift["pod_id"]))
        shift_process_id = str(pod["process_id"])
        if process_id is not None and str(process_id) != shift_process_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The selected shift does not belong to the selected process.",
            )
        process_id = UUID(shift_process_id)
    if process_id is not None:
        process, process_organization_id = _require_process(db, process_id)
        if process_organization_id != str(employee["organization_id"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found in the employee's organization.",
            )
    return employee, process, shift


def _validate_requirement_relation(
    db: Client,
    process_id: UUID,
    shift_id: Optional[UUID],
) -> None:
    _require_process(db, process_id)
    if shift_id is not None:
        shift = _one(db, "shifts", "Shift", id=str(shift_id))
        pod = _one(db, "pods", "Pod", id=str(shift["pod_id"]))
        if str(pod["process_id"]) != str(process_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The selected shift does not belong to the selected process.",
            )


@router.get("/processes/{process_id}/operating-rules")
def list_process_operating_rules(
    process_id: UUID,
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_process(db, process_id)
    return _execute(
        db.table("process_operating_rules")
        .select("*")
        .eq("process_id", str(process_id)),
        "Process Operating Rule",
    )


@router.get("/processes/{process_id}/operating-rules/current")
def get_process_operating_rule(
    process_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, process_id)
    rows = _execute(
        db.table("process_operating_rules")
        .select("*")
        .eq("process_id", str(process_id))
        .limit(1),
        "Process Operating Rule",
    )
    if rows:
        return rows[0]
    return {
        "process_id": str(process_id),
        "operating_days": list(range(7)),
        "operates_on_public_holidays": False,
    }


@router.post(
    "/operating-rules",
    status_code=status.HTTP_201_CREATED,
)
def create_process_operating_rule(
    payload: OperatingRuleCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, payload.process_id)
    rows = _execute(
        db.table("process_operating_rules").insert({
            "process_id": str(payload.process_id),
            "operating_days": payload.operating_days,
            "operates_on_public_holidays": payload.operates_on_public_holidays,
        }),
        "Process Operating Rule",
    )
    return rows[0]


@router.put("/operating-rules/{process_id}")
def update_process_operating_rule(
    process_id: UUID,
    payload: OperatingRuleUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, process_id)
    update = payload.model_dump(exclude_unset=True)
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    rows = _execute(
        db.table("process_operating_rules")
        .update(update)
        .eq("process_id", str(process_id)),
        "Process Operating Rule",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Operating rule not found.")
    return rows[0]


@router.delete("/operating-rules/{process_id}")
def delete_process_operating_rule(
    process_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_process(db, process_id)
    rows = _execute(
        db.table("process_operating_rules")
        .delete()
        .eq("process_id", str(process_id)),
        "Process Operating Rule",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Operating rule not found.")
    return {"message": "Operating rule deleted; the process now uses the default calendar."}


@router.get("/processes/{process_id}/operating-overrides")
def list_process_operating_overrides(
    process_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_process(db, process_id)
    query = db.table("process_operating_overrides").select("*").eq(
        "process_id", str(process_id)
    )
    if start_date:
        query = query.gte("operating_date", start_date.isoformat())
    if end_date:
        query = query.lte("operating_date", end_date.isoformat())
    return _execute(query.order("operating_date"), "Process Operating Override")


@router.get("/processes/{process_id}/operating-overrides/{operating_date}")
def get_process_operating_override(
    process_id: UUID,
    operating_date: date,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, process_id)
    return _one(
        db,
        "process_operating_overrides",
        "Process Operating Override",
        process_id=str(process_id),
        operating_date=operating_date.isoformat(),
    )


@router.post(
    "/operating-overrides",
    status_code=status.HTTP_201_CREATED,
)
def create_process_operating_override(
    payload: OperatingOverrideCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, payload.process_id)
    rows = _execute(
        db.table("process_operating_overrides").insert({
            "process_id": str(payload.process_id),
            "operating_date": payload.operating_date.isoformat(),
            "is_operating": payload.is_operating,
        }),
        "Process Operating Override",
    )
    return rows[0]


@router.put("/processes/{process_id}/operating-overrides/{operating_date}")
def update_process_operating_override(
    process_id: UUID,
    operating_date: date,
    payload: OperatingOverrideUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_process(db, process_id)
    update = payload.model_dump(exclude_unset=True, mode="json")
    rows = _execute(
        db.table("process_operating_overrides")
        .update(update)
        .eq("process_id", str(process_id))
        .eq("operating_date", operating_date.isoformat()),
        "Process Operating Override",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Operating override not found.")
    return rows[0]


@router.delete("/processes/{process_id}/operating-overrides/{operating_date}")
def delete_process_operating_override(
    process_id: UUID,
    operating_date: date,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_process(db, process_id)
    rows = _execute(
        db.table("process_operating_overrides")
        .delete()
        .eq("process_id", str(process_id))
        .eq("operating_date", operating_date.isoformat()),
        "Process Operating Override",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Operating override not found.")
    return {"message": "Operating override deleted."}


@router.get("/coverage-requirements")
def list_coverage_requirements(
    process_id: Optional[UUID] = Query(None),
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    query = db.table("process_coverage_requirements").select("*")
    if process_id is not None:
        _require_process(db, process_id)
        query = query.eq("process_id", str(process_id))
    return _execute(query.order("process_id"), "Process Coverage Requirement")


@router.post(
    "/coverage-requirements",
    status_code=status.HTTP_201_CREATED,
)
def create_coverage_requirement(
    payload: CoverageRequirementCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _validate_requirement_relation(db, payload.process_id, payload.shift_id)
    rows = _execute(
        db.table("process_coverage_requirements").insert(
            payload.model_dump(mode="json")
        ),
        "Process Coverage Requirement",
    )
    return rows[0]


@router.get("/coverage-requirements/{requirement_id}")
def get_coverage_requirement(
    requirement_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    row = _one(
        db, "process_coverage_requirements", "Process Coverage Requirement",
        id=str(requirement_id),
    )
    _validate_requirement_relation(
        db, UUID(str(row["process_id"])),
        UUID(str(row["shift_id"])) if row.get("shift_id") else None,
    )
    return row


@router.patch("/coverage-requirements/{requirement_id}")
@router.put("/coverage-requirements/{requirement_id}")
def update_coverage_requirement(
    requirement_id: UUID,
    payload: CoverageRequirementUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    existing = _one(
        db, "process_coverage_requirements", "Process Coverage Requirement",
        id=str(requirement_id),
    )
    update = payload.model_dump(exclude_unset=True, mode="json")
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    merged = {**existing, **update}
    validated = CoverageRequirementCreate.model_validate(merged)
    _validate_requirement_relation(db, validated.process_id, validated.shift_id)
    rows = _execute(
        db.table("process_coverage_requirements")
        .update(update)
        .eq("id", str(requirement_id)),
        "Process Coverage Requirement",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Coverage requirement not found.")
    return rows[0]


@router.delete("/coverage-requirements/{requirement_id}")
def delete_coverage_requirement(
    requirement_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _one(
        db, "process_coverage_requirements", "Process Coverage Requirement",
        id=str(requirement_id),
    )
    rows = _execute(
        db.table("process_coverage_requirements")
        .delete()
        .eq("id", str(requirement_id)),
        "Process Coverage Requirement",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Coverage requirement not found.")
    return {"message": "Coverage requirement deleted."}


@router.get("/organizations/{organization_id}/public-holidays")
def list_public_holidays(
    organization_id: UUID,
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_organization(db, organization_id)
    return _execute(
        db.table("public_holidays")
        .select("*")
        .eq("organization_id", str(organization_id))
        .order("holiday_date"),
        "Public Holiday",
    )


@router.post(
    "/organizations/{organization_id}/public-holidays",
    status_code=status.HTTP_201_CREATED,
)
def create_public_holiday(
    organization_id: UUID,
    payload: PublicHolidayCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_organization(db, organization_id)
    rows = _execute(
        db.table("public_holidays").insert({
            "organization_id": str(organization_id),
            **payload.model_dump(mode="json"),
        }),
        "Public Holiday",
    )
    return rows[0]


@router.get("/organizations/{organization_id}/public-holidays/{holiday_date}")
def get_public_holiday(
    organization_id: UUID,
    holiday_date: date,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_organization(db, organization_id)
    return _one(
        db,
        "public_holidays",
        "Public Holiday",
        organization_id=str(organization_id),
        holiday_date=holiday_date.isoformat(),
    )


@router.put("/organizations/{organization_id}/public-holidays/{holiday_date}")
@router.patch("/organizations/{organization_id}/public-holidays/{holiday_date}")
def update_public_holiday(
    organization_id: UUID,
    holiday_date: date,
    payload: PublicHolidayUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_organization(db, organization_id)
    rows = _execute(
        db.table("public_holidays")
        .update(payload.model_dump(exclude_unset=True, mode="json"))
        .eq("organization_id", str(organization_id))
        .eq("holiday_date", holiday_date.isoformat()),
        "Public Holiday",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Public holiday not found.")
    return rows[0]


@router.delete("/organizations/{organization_id}/public-holidays/{holiday_date}")
def delete_public_holiday(
    organization_id: UUID,
    holiday_date: date,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_organization(db, organization_id)
    rows = _execute(
        db.table("public_holidays")
        .delete()
        .eq("organization_id", str(organization_id))
        .eq("holiday_date", holiday_date.isoformat()),
        "Public Holiday",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Public holiday not found.")
    return {"message": "Public holiday deleted."}


@router.get("/employees/{employee_id}/weekly-offs")
def list_employee_weekly_offs(
    employee_id: UUID,
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_employee(db, employee_id)
    return _execute(
        db.table("employee_weekly_offs")
        .select("*")
        .eq("employee_id", str(employee_id))
        .order("day_of_week"),
        "Employee Weekly Off",
    )


@router.post(
    "/employees/{employee_id}/weekly-offs",
    status_code=status.HTTP_201_CREATED,
)
def create_employee_weekly_off(
    employee_id: UUID,
    payload: WeeklyOffCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_weekly_offs").insert({
            "employee_id": str(employee_id),
            **payload.model_dump(),
        }),
        "Employee Weekly Off",
    )
    return rows[0]


@router.put("/employees/{employee_id}/weekly-offs/{day_of_week}")
def update_employee_weekly_off(
    employee_id: UUID,
    day_of_week: int,
    payload: WeeklyOffCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    if day_of_week < 0 or day_of_week > 6:
        raise HTTPException(status_code=422, detail="day_of_week must be 0 through 6.")
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_weekly_offs")
        .update({"day_of_week": payload.day_of_week})
        .eq("employee_id", str(employee_id))
        .eq("day_of_week", day_of_week),
        "Employee Weekly Off",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Weekly off not found.")
    return rows[0]


@router.delete("/employees/{employee_id}/weekly-offs/{day_of_week}")
def delete_employee_weekly_off(
    employee_id: UUID,
    day_of_week: int,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_weekly_offs")
        .delete()
        .eq("employee_id", str(employee_id))
        .eq("day_of_week", str(day_of_week)),
        "Employee Weekly Off",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Weekly off not found.")
    return {"message": "Weekly off deleted."}


@router.get("/employees/{employee_id}/time-off")
def list_employee_time_off(
    employee_id: UUID,
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_employee(db, employee_id)
    return _execute(
        db.table("employee_time_off")
        .select("*")
        .eq("employee_id", str(employee_id))
        .order("start_date"),
        "Employee Time Off",
    )


@router.post(
    "/employees/{employee_id}/time-off",
    status_code=status.HTTP_201_CREATED,
)
def create_employee_time_off(
    employee_id: UUID,
    payload: TimeOffCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_time_off").insert({
            "employee_id": str(employee_id),
            **payload.model_dump(mode="json"),
        }),
        "Employee Time Off",
    )
    return rows[0]


@router.get("/employees/{employee_id}/time-off/{record_id}")
def get_employee_time_off(
    employee_id: UUID,
    record_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    return _one(
        db,
        "employee_time_off",
        "Employee Time Off",
        id=str(record_id),
        employee_id=str(employee_id),
    )


@router.patch("/employees/{employee_id}/time-off/{record_id}")
@router.put("/employees/{employee_id}/time-off/{record_id}")
def update_employee_time_off(
    employee_id: UUID,
    record_id: UUID,
    payload: TimeOffUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    existing = _one(
        db,
        "employee_time_off",
        "Employee Time Off",
        id=str(record_id),
        employee_id=str(employee_id),
    )
    update = payload.model_dump(exclude_unset=True, mode="json")
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    candidate = TimeOffCreate.model_validate({**existing, **update})
    rows = _execute(
        db.table("employee_time_off")
        .update(candidate.model_dump(mode="json"))
        .eq("id", str(record_id))
        .eq("employee_id", str(employee_id)),
        "Employee Time Off",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Time-off record not found.")
    return rows[0]


@router.delete("/employees/{employee_id}/time-off/{record_id}")
def delete_employee_time_off(
    employee_id: UUID,
    record_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_time_off")
        .delete()
        .eq("id", str(record_id))
        .eq("employee_id", str(employee_id)),
        "Employee Time Off",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Time-off record not found.")
    return {"message": "Time-off record deleted."}


@router.get("/employees/{employee_id}/preferences")
def list_employee_preferences(
    employee_id: UUID,
    db: Client = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_employee(db, employee_id)
    return _execute(
        db.table("employee_preferences")
        .select("*")
        .eq("employee_id", str(employee_id)),
        "Employee Preference",
    )


@router.post(
    "/employees/{employee_id}/preferences",
    status_code=status.HTTP_201_CREATED,
)
def create_employee_preference(
    employee_id: UUID,
    payload: EmployeePreferenceCreate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee_process(
        db, employee_id, payload.process_id, payload.preferred_shift_id
    )
    rows = _execute(
        db.table("employee_preferences").insert({
            "employee_id": str(employee_id),
            **payload.model_dump(mode="json"),
        }),
        "Employee Preference",
    )
    return rows[0]


@router.get("/employees/{employee_id}/preferences/{preference_id}")
def get_employee_preference(
    employee_id: UUID,
    preference_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    row = _one(
        db,
        "employee_preferences",
        "Employee Preference",
        id=str(preference_id),
        employee_id=str(employee_id),
    )
    _require_employee_process(
        db,
        employee_id,
        UUID(str(row["process_id"])) if row.get("process_id") else None,
        UUID(str(row["preferred_shift_id"])) if row.get("preferred_shift_id") else None,
    )
    return row


@router.patch("/employees/{employee_id}/preferences/{preference_id}")
@router.put("/employees/{employee_id}/preferences/{preference_id}")
def update_employee_preference(
    employee_id: UUID,
    preference_id: UUID,
    payload: EmployeePreferenceUpdate,
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    _require_employee(db, employee_id)
    existing = _one(
        db,
        "employee_preferences",
        "Employee Preference",
        id=str(preference_id),
        employee_id=str(employee_id),
    )
    update = payload.model_dump(exclude_unset=True, mode="json")
    if not update:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    candidate = EmployeePreferenceCreate.model_validate({**existing, **update})
    _require_employee_process(
        db, employee_id, candidate.process_id, candidate.preferred_shift_id
    )
    rows = _execute(
        db.table("employee_preferences")
        .update(candidate.model_dump(mode="json"))
        .eq("id", str(preference_id))
        .eq("employee_id", str(employee_id)),
        "Employee Preference",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Employee preference not found.")
    return rows[0]


@router.delete("/employees/{employee_id}/preferences/{preference_id}")
def delete_employee_preference(
    employee_id: UUID,
    preference_id: UUID,
    db: Client = Depends(get_db),
) -> dict[str, str]:
    _require_employee(db, employee_id)
    rows = _execute(
        db.table("employee_preferences")
        .delete()
        .eq("id", str(preference_id))
        .eq("employee_id", str(employee_id)),
        "Employee Preference",
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Employee preference not found.")
    return {"message": "Employee preference deleted."}
