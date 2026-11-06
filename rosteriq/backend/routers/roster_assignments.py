import calendar
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    RosterAssignmentCreate,
    RosterAssignmentUpdate,
    RosterAssignmentResponse,
    RosterAssignmentBatchSave,
    RosterPublishRequest,
    MessageResponse
)
from routers.scheduling import _report_response, load_schedule_data
from services.scheduling import Assignment, validate_roster

router = APIRouter(prefix="/roster-assignments", tags=["Roster Assignments"])


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _organization_employee_ids(db: Client, organization_id: UUID) -> list[str]:
    rows = db.table("employees").select("id").eq("organization_id", str(organization_id)).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Organization has no accessible employees.")
    return [str(row["id"]) for row in rows]


def _validate_month_roster(
    db: Client,
    organization_id: UUID,
    first_day: date,
    last_day: date,
    replacement: Optional[dict] = None,
    excluded_assignment_id: Optional[UUID] = None,
) -> None:
    employee_ids = _organization_employee_ids(db, organization_id)
    data = load_schedule_data(db, str(organization_id), first_day, last_day)
    rows = (
        db.table("roster_assignments")
        .select("*")
        .in_("employee_id", employee_ids)
        .in_("status", ["scheduled", "published"])
        .gte("assignment_date", first_day.isoformat())
        .lte("assignment_date", last_day.isoformat())
        .execute()
        .data
        or []
    )
    assignments = [
        Assignment(
            employee_id=str(row["employee_id"]),
            shift_id=str(row["shift_id"]),
            assignment_date=date.fromisoformat(str(row["assignment_date"])[:10]),
        )
        for row in rows
        if str(row["id"]) != str(excluded_assignment_id)
    ]
    if replacement is not None:
        assignments.append(
            Assignment(
                employee_id=str(replacement["employee_id"]),
                shift_id=str(replacement["shift_id"]),
                assignment_date=date.fromisoformat(
                    str(replacement["assignment_date"])[:10]
                ),
            )
        )
    report = validate_roster(data, assignments, first_day, last_day)
    assignment_conflicts = [
        conflict
        for conflict in report.conflicts
        if conflict.severity == "error"
        and conflict.conflict_type != "insufficient_staffing"
    ]
    if assignment_conflicts:
        response = _report_response(data, report, str(organization_id))
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Roster contains mandatory scheduling violations.",
                "validation": jsonable_encoder(response),
            },
        )


@router.post("/validated", response_model=list[RosterAssignmentResponse], status_code=status.HTTP_201_CREATED,
             summary="Validate and save a complete roster proposal")
def validate_and_save_roster(
    payload: RosterAssignmentBatchSave,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Atomically gate the manager save workflow on mandatory scheduling validation."""
    if payload.status != "scheduled":
        raise HTTPException(
            status_code=422,
            detail="A validated proposal must be saved with scheduled status before publishing.",
        )
    first_day, last_day = _month_bounds(payload.year, payload.month)
    data = load_schedule_data(db, str(payload.organization_id), first_day, last_day)
    assignments = [Assignment(employee_id=str(item.employee_id), shift_id=str(item.shift_id), assignment_date=item.assignment_date) for item in payload.assignments]
    report = validate_roster(data, assignments, first_day, last_day)
    if not report.valid:
        response = _report_response(data, report, str(payload.organization_id))
        raise HTTPException(status_code=422, detail={"message": "Roster contains mandatory scheduling violations.", "validation": jsonable_encoder(response)})

    employee_ids = _organization_employee_ids(db, payload.organization_id)
    try:
        db.table("roster_assignments").delete().in_("employee_id", employee_ids).gte("assignment_date", first_day.isoformat()).lte("assignment_date", last_day.isoformat()).execute()
        rows = db.table("roster_assignments").insert([
            {"employee_id": str(item.employee_id), "shift_id": str(item.shift_id), "assignment_date": item.assignment_date.isoformat(), "status": payload.status}
            for item in payload.assignments
        ]).execute().data or []
        return rows
    except Exception as error:
        handle_supabase_error(error, "Roster Assignment")


@router.post("/publish", response_model=list[RosterAssignmentResponse], summary="Validate and publish a saved roster")
def publish_roster(
    payload: RosterPublishRequest,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    first_day, last_day = _month_bounds(payload.year, payload.month)
    data = load_schedule_data(db, str(payload.organization_id), first_day, last_day)
    employee_ids = _organization_employee_ids(db, payload.organization_id)
    rows = db.table("roster_assignments").select("*").in_("employee_id", employee_ids).eq("status", "scheduled").gte("assignment_date", first_day.isoformat()).lte("assignment_date", last_day.isoformat()).execute().data or []
    assignments = [Assignment(employee_id=str(row["employee_id"]), shift_id=str(row["shift_id"]), assignment_date=date.fromisoformat(str(row["assignment_date"])[:10])) for row in rows]
    report = validate_roster(data, assignments, first_day, last_day)
    if not report.valid:
        response = _report_response(data, report, str(payload.organization_id))
        raise HTTPException(status_code=422, detail={"message": "Only a valid saved roster can be published.", "validation": jsonable_encoder(response)})
    published = db.table("roster_assignments").update({"status": "published"}).in_("employee_id", employee_ids).eq("status", "scheduled").gte("assignment_date", first_day.isoformat()).lte("assignment_date", last_day.isoformat()).execute().data or []
    return published

@router.get("", response_model=list[RosterAssignmentResponse], summary="List roster assignments")
def list_roster_assignments(
    employee_id: Optional[UUID] = Query(None, description="Filter by employee ID"),
    shift_id: Optional[UUID] = Query(None, description="Filter by shift ID"),
    assignment_date: Optional[date] = Query(None, description="Filter by assignment date (YYYY-MM-DD)"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve roster assignments accessible to the manager with optional filters."""
    try:
        query = db.table("roster_assignments").select("*")
        if employee_id:
            query = query.eq("employee_id", str(employee_id))
        if shift_id:
            query = query.eq("shift_id", str(shift_id))
        if assignment_date:
            query = query.eq("assignment_date", assignment_date.isoformat())
        res = query.order("assignment_date").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.get("/{id}", response_model=RosterAssignmentResponse, summary="Get roster assignment by ID")
def get_roster_assignment(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific roster assignment by ID."""
    try:
        res = db.table("roster_assignments").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.post("", response_model=RosterAssignmentResponse, status_code=status.HTTP_201_CREATED, summary="Create roster assignment")
def create_roster_assignment(
    payload: RosterAssignmentCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Assign an employee to a shift for a specific date."""
    if payload.status == "published":
        raise HTTPException(
            status_code=422,
            detail="Use POST /roster-assignments/publish to publish a validated roster.",
        )
    employee_rows = (
        db.table("employees")
        .select("id, organization_id")
        .eq("id", str(payload.employee_id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not employee_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {payload.employee_id} not found or you do not have permission."
        )
    insert_data = {
        "employee_id": str(payload.employee_id),
        "shift_id": str(payload.shift_id),
        "assignment_date": payload.assignment_date.isoformat(),
        "status": payload.status or "scheduled"
    }
    first_day, last_day = _month_bounds(
        payload.assignment_date.year, payload.assignment_date.month
    )
    _validate_month_roster(
        db,
        UUID(str(employee_rows[0]["organization_id"])),
        first_day,
        last_day,
        replacement=insert_data,
    )
    try:
        res = db.table("roster_assignments").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create roster assignment."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.patch("/{id}", response_model=RosterAssignmentResponse, summary="Update roster assignment")
@router.put("/{id}", response_model=RosterAssignmentResponse, summary="Update roster assignment")
def update_roster_assignment(
    id: UUID,
    payload: RosterAssignmentUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update a roster assignment."""
    current_rows = (
        db.table("roster_assignments")
        .select("*")
        .eq("id", str(id))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not current_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roster assignment {id} not found or access denied."
        )
    current = current_rows[0]
    if current.get("status") == "published":
        raise HTTPException(
            status_code=409,
            detail="Published assignments must be changed through a validated roster proposal.",
        )
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    # Convert dates or UUIDs to string for Supabase payload
    if "assignment_date" in update_data and isinstance(update_data["assignment_date"], date):
        update_data["assignment_date"] = update_data["assignment_date"].isoformat()
    if "employee_id" in update_data and update_data["employee_id"]:
        update_data["employee_id"] = str(update_data["employee_id"])
    if "shift_id" in update_data and update_data["shift_id"]:
        update_data["shift_id"] = str(update_data["shift_id"])
    if update_data.get("status") == "published":
        raise HTTPException(
            status_code=422,
            detail="Use POST /roster-assignments/publish to publish a validated roster.",
        )

    replacement = {**current, **update_data}
    old_employee = (
        db.table("employees")
        .select("organization_id")
        .eq("id", str(current["employee_id"]))
        .limit(1)
        .execute()
        .data
        or []
    )
    new_employee = (
        db.table("employees")
        .select("organization_id")
        .eq("id", str(replacement["employee_id"]))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not old_employee or not new_employee:
        raise HTTPException(status_code=404, detail="Employee not found or access denied.")
    if old_employee[0]["organization_id"] != new_employee[0]["organization_id"]:
        raise HTTPException(
            status_code=422,
            detail="An assignment cannot be moved between organizations.",
        )
    old_date = date.fromisoformat(str(current["assignment_date"])[:10])
    new_date = date.fromisoformat(str(replacement["assignment_date"])[:10])
    new_first, new_last = _month_bounds(new_date.year, new_date.month)
    if (old_date.year, old_date.month) == (new_date.year, new_date.month):
        _validate_month_roster(
            db,
            UUID(str(new_employee[0]["organization_id"])),
            new_first,
            new_last,
            replacement=replacement,
            excluded_assignment_id=id,
        )
    else:
        old_first, old_last = _month_bounds(old_date.year, old_date.month)
        _validate_month_roster(
            db,
            UUID(str(old_employee[0]["organization_id"])),
            old_first,
            old_last,
            excluded_assignment_id=id,
        )
        _validate_month_roster(
            db,
            UUID(str(new_employee[0]["organization_id"])),
            new_first,
            new_last,
            replacement=replacement,
        )

    try:
        res = db.table("roster_assignments").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete roster assignment")
def delete_roster_assignment(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete a roster assignment."""
    try:
        rows = (
            db.table("roster_assignments")
            .select("*")
            .eq("id", str(id))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        assignment = rows[0]
        if assignment.get("status") == "published":
            raise HTTPException(
                status_code=409,
                detail="Published assignments must be changed through a validated roster proposal.",
            )
        employee = (
            db.table("employees")
            .select("organization_id")
            .eq("id", str(assignment["employee_id"]))
            .limit(1)
            .execute()
            .data
            or []
        )
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found or access denied.")
        assignment_date = date.fromisoformat(str(assignment["assignment_date"])[:10])
        first_day, last_day = _month_bounds(assignment_date.year, assignment_date.month)
        _validate_month_roster(
            db,
            UUID(str(employee[0]["organization_id"])),
            first_day,
            last_day,
            excluded_assignment_id=id,
        )
        res = db.table("roster_assignments").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster assignment {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Roster assignment {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Roster Assignment")
