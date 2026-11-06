from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from app.auth import get_db, get_current_user, AuthenticatedUser
from database import handle_supabase_error
from models.schemas import (
    EmployeeSkillCreate,
    EmployeeSkillUpdate,
    EmployeeSkillResponse,
    MessageResponse
)

router = APIRouter(prefix="/employee-skills", tags=["Employee Skills"])

@router.get("", response_model=list[EmployeeSkillResponse], summary="List employee skills")
def list_employee_skills(
    employee_id: Optional[UUID] = Query(None, description="Filter skills by employee ID"),
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve skills, optionally filtered by employee ID."""
    try:
        query = db.table("employee_skills").select("*")
        if employee_id:
            query = query.eq("employee_id", str(employee_id))
        res = query.order("skill_name").execute()
        return res.data or []
    except Exception as e:
        handle_supabase_error(e, "Employee Skill")

@router.get("/{id}", response_model=EmployeeSkillResponse, summary="Get skill by ID")
def get_employee_skill(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieve a specific employee skill record."""
    try:
        res = db.table("employee_skills").select("*").eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee skill {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Skill")

@router.post("", response_model=EmployeeSkillResponse, status_code=status.HTTP_201_CREATED, summary="Add skill to employee")
def create_employee_skill(
    payload: EmployeeSkillCreate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Assign a skill to an employee."""
    # Verify employee exists and is in user's organization
    emp_check = db.table("employees").select("id").eq("id", str(payload.employee_id)).execute()
    if not emp_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {payload.employee_id} not found or you do not have permission."
        )

    insert_data = {
        "employee_id": str(payload.employee_id),
        "skill_name": payload.skill_name,
        "proficiency": payload.proficiency or "intermediate"
    }
    try:
        res = db.table("employee_skills").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create employee skill."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Skill")

@router.patch("/{id}", response_model=EmployeeSkillResponse, summary="Update employee skill")
@router.put("/{id}", response_model=EmployeeSkillResponse, summary="Update employee skill")
def update_employee_skill(
    id: UUID,
    payload: EmployeeSkillUpdate,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Update employee skill or proficiency."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )
    try:
        res = db.table("employee_skills").update(update_data).eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee skill {id} not found or access denied."
            )
        return res.data[0]
    except Exception as e:
        handle_supabase_error(e, "Employee Skill")

@router.delete("/{id}", response_model=MessageResponse, summary="Delete employee skill")
def delete_employee_skill(
    id: UUID,
    db: Client = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Delete an employee skill."""
    try:
        res = db.table("employee_skills").delete().eq("id", str(id)).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee skill {id} not found or access denied."
            )
        return MessageResponse(
            message=f"Employee skill {id} deleted successfully.",
            id=id
        )
    except Exception as e:
        handle_supabase_error(e, "Employee Skill")
