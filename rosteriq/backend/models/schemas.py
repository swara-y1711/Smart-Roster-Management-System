from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Base configuration for Pydantic models
class RosterIQBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ---------------------------------------------------------------------------
# Organization Schemas
# ---------------------------------------------------------------------------
class OrganizationBase(RosterIQBaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(RosterIQBaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)

class OrganizationResponse(OrganizationBase):
    id: UUID
    created_at: datetime

# ---------------------------------------------------------------------------
# Brand Schemas
# ---------------------------------------------------------------------------
class BrandBase(RosterIQBaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Brand name")
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

class BrandCreate(BrandBase):
    organization_id: UUID

class BrandUpdate(RosterIQBaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

class BrandResponse(BrandBase):
    id: UUID
    organization_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Process Schemas
# ---------------------------------------------------------------------------
class ProcessBase(RosterIQBaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Process name")
    description: Optional[str] = None

class ProcessCreate(ProcessBase):
    brand_id: UUID

class ProcessUpdate(RosterIQBaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

class ProcessResponse(ProcessBase):
    id: UUID
    brand_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Pod Schemas
# ---------------------------------------------------------------------------
class PodBase(RosterIQBaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Pod name")
    description: Optional[str] = None

class PodCreate(PodBase):
    process_id: UUID

class PodUpdate(RosterIQBaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

class PodResponse(PodBase):
    id: UUID
    process_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Employee Schemas
# ---------------------------------------------------------------------------
class EmployeeBase(RosterIQBaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50, description="Unique employee identifier code")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    employment_type: Optional[str] = Field("full_time", max_length=50)
    status: Optional[str] = Field("active", max_length=50)
    max_hours_per_week: Optional[float] = Field(40.0, ge=0, le=168)
    designation: str = Field(..., min_length=1, max_length=100)

class EmployeeCreate(EmployeeBase):
    organization_id: UUID

class EmployeeUpdate(RosterIQBaseModel):
    employee_code: Optional[str] = Field(None, min_length=1, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    employment_type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    max_hours_per_week: Optional[float] = Field(None, ge=0, le=168)
    designation: Optional[str] = Field(None, min_length=1, max_length=100)

class EmployeeResponse(EmployeeBase):
    id: UUID
    organization_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Employee Skill Schemas
# ---------------------------------------------------------------------------
class EmployeeSkillBase(RosterIQBaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency: Optional[str] = Field("intermediate", max_length=50)

class EmployeeSkillCreate(EmployeeSkillBase):
    employee_id: UUID

class EmployeeSkillUpdate(RosterIQBaseModel):
    skill_name: Optional[str] = Field(None, min_length=1, max_length=100)
    proficiency: Optional[str] = Field(None, max_length=50)

class EmployeeSkillResponse(EmployeeSkillBase):
    id: UUID
    employee_id: UUID

# ---------------------------------------------------------------------------
# Employee Availability Schemas
# ---------------------------------------------------------------------------
class EmployeeAvailabilityBase(RosterIQBaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Sunday/Monday .. 6)")
    start_time: Optional[str] = Field(None, description="Start time (HH:MM or HH:MM:SS)")
    end_time: Optional[str] = Field(None, description="End time (HH:MM or HH:MM:SS)")
    is_available: Optional[bool] = True

class EmployeeAvailabilityCreate(EmployeeAvailabilityBase):
    employee_id: UUID

class EmployeeAvailabilityUpdate(RosterIQBaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_available: Optional[bool] = None

class EmployeeAvailabilityResponse(EmployeeAvailabilityBase):
    id: UUID
    employee_id: UUID

# ---------------------------------------------------------------------------
# Shift Schemas
# ---------------------------------------------------------------------------
class ShiftBase(RosterIQBaseModel):
    shift_name: str = Field(..., min_length=1, max_length=100)
    start_time: str = Field(..., description="Start time (HH:MM or HH:MM:SS)")
    end_time: str = Field(..., description="End time (HH:MM or HH:MM:SS)")
    required_headcount: Optional[int] = Field(1, ge=1)

class ShiftCreate(ShiftBase):
    pod_id: UUID

class ShiftUpdate(RosterIQBaseModel):
    shift_name: Optional[str] = Field(None, min_length=1, max_length=100)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    required_headcount: Optional[int] = Field(None, ge=1)

class ShiftResponse(ShiftBase):
    id: UUID
    pod_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Roster Assignment Schemas
# ---------------------------------------------------------------------------
class RosterAssignmentBase(RosterIQBaseModel):
    assignment_date: date
    status: Optional[str] = Field("scheduled", max_length=50)

class RosterAssignmentCreate(RosterAssignmentBase):
    employee_id: UUID
    shift_id: UUID

class RosterAssignmentUpdate(RosterIQBaseModel):
    employee_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None
    assignment_date: Optional[date] = None
    status: Optional[str] = Field(None, max_length=50)

class RosterAssignmentResponse(RosterAssignmentBase):
    id: UUID
    employee_id: UUID
    shift_id: UUID
    created_at: Optional[datetime] = None

# ---------------------------------------------------------------------------
# Employee Pod Schemas (Junction)
# ---------------------------------------------------------------------------
class EmployeePodBase(RosterIQBaseModel):
    employee_id: UUID
    pod_id: UUID
    is_primary: Optional[bool] = False

class EmployeePodCreate(EmployeePodBase):
    pass

class EmployeePodResponse(EmployeePodBase):
    pass

# ---------------------------------------------------------------------------
# General / Auth Responses
# ---------------------------------------------------------------------------
class MessageResponse(RosterIQBaseModel):
    message: str
    id: Optional[UUID] = None

class ManagerProfileResponse(RosterIQBaseModel):
    id: UUID
    full_name: str
    work_email: str
    employee_id: str
    created_at: Optional[datetime] = None
