from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SchedulingModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def validate_weekdays(values: list[int]) -> list[int]:
    if any(day < 0 or day > 6 for day in values):
        raise ValueError("Weekday values must use Monday=0 through Sunday=6.")
    if len(set(values)) != len(values):
        raise ValueError("Weekday values must not contain duplicates.")
    return values


class OperatingRuleCreate(SchedulingModel):
    process_id: UUID
    operating_days: list[int] = Field(default_factory=lambda: list(range(7)))
    operates_on_public_holidays: bool = False

    @model_validator(mode="after")
    def validate_days(self) -> "OperatingRuleCreate":
        validate_weekdays(self.operating_days)
        return self


class OperatingRuleUpdate(SchedulingModel):
    operating_days: Optional[list[int]] = None
    operates_on_public_holidays: Optional[bool] = None

    @model_validator(mode="after")
    def validate_days(self) -> "OperatingRuleUpdate":
        if self.operating_days is not None:
            validate_weekdays(self.operating_days)
        return self


class OperatingOverrideCreate(SchedulingModel):
    process_id: UUID
    operating_date: date
    is_operating: bool


class OperatingOverrideUpdate(SchedulingModel):
    operating_date: Optional[date] = None
    is_operating: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update(self) -> "OperatingOverrideUpdate":
        if self.operating_date is None and self.is_operating is None:
            raise ValueError("Provide operating_date or is_operating.")
        return self


class CoverageRequirementCreate(SchedulingModel):
    process_id: UUID
    shift_id: Optional[UUID] = None
    target_date: Optional[date] = None
    day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    minimum_staff: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_date_selector(self) -> "CoverageRequirementCreate":
        if self.target_date is not None and self.day_of_week is not None:
            raise ValueError("Choose target_date or day_of_week, not both.")
        return self


class CoverageRequirementUpdate(SchedulingModel):
    process_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None
    target_date: Optional[date] = None
    day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    minimum_staff: Optional[int] = Field(default=None, ge=0)


class PublicHolidayCreate(SchedulingModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=255)


class PublicHolidayUpdate(SchedulingModel):
    holiday_date: Optional[date] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_update(self) -> "PublicHolidayUpdate":
        if self.holiday_date is None and self.name is None:
            raise ValueError("Provide holiday_date or name.")
        return self


class WeeklyOffCreate(SchedulingModel):
    day_of_week: int = Field(ge=0, le=6)


class TimeOffCreate(SchedulingModel):
    start_date: date
    end_date: date
    kind: Literal["leave", "comp_off", "unavailability"]
    status: Literal["planned", "approved", "pending", "rejected", "active"]
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_range(self) -> "TimeOffCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        if self.kind == "comp_off" and self.status not in {"approved", "pending", "rejected"}:
            raise ValueError("Comp-off status must be approved, pending, or rejected.")
        if self.kind == "leave" and self.status == "active":
            raise ValueError("Leave status cannot be active.")
        return self


class TimeOffUpdate(SchedulingModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    kind: Optional[Literal["leave", "comp_off", "unavailability"]] = None
    status: Optional[Literal["planned", "approved", "pending", "rejected", "active"]] = None
    reason: Optional[str] = None


class EmployeePreferenceCreate(SchedulingModel):
    process_id: Optional[UUID] = None
    preferred_shift_id: Optional[UUID] = None
    preferred_days_of_week: list[int] = Field(default_factory=list)
    avoid_days_of_week: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_days(self) -> "EmployeePreferenceCreate":
        validate_weekdays(self.preferred_days_of_week)
        validate_weekdays(self.avoid_days_of_week)
        return self


class EmployeePreferenceUpdate(SchedulingModel):
    process_id: Optional[UUID] = None
    preferred_shift_id: Optional[UUID] = None
    preferred_days_of_week: Optional[list[int]] = None
    avoid_days_of_week: Optional[list[int]] = None

    @model_validator(mode="after")
    def validate_days(self) -> "EmployeePreferenceUpdate":
        if self.preferred_days_of_week is not None:
            validate_weekdays(self.preferred_days_of_week)
        if self.avoid_days_of_week is not None:
            validate_weekdays(self.avoid_days_of_week)
        return self


class GenerateRosterRequest(SchedulingModel):
    organization_id: UUID
    year: int = Field(ge=2000, le=2200)
    month: int = Field(ge=1, le=12)


class ProposedAssignmentInput(SchedulingModel):
    employee_id: UUID
    shift_id: UUID
    assignment_date: date


class ValidateRosterRequest(GenerateRosterRequest):
    assignments: list[ProposedAssignmentInput]


class ImpactChange(SchedulingModel):
    change_type: Literal[
        "employee_unavailable",
        "planned_leave",
        "approved_leave",
        "approved_comp_off",
        "coverage_requirement",
        "operating_calendar",
    ]
    employee_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    process_id: Optional[UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_date: Optional[date] = None
    shift_id: Optional[UUID] = None
    minimum_staff: Optional[int] = Field(default=None, ge=0)
    operating_days: Optional[list[int]] = None
    operates_on_public_holidays: Optional[bool] = None

    @model_validator(mode="after")
    def validate_change_fields(self) -> "ImpactChange":
        if self.change_type in {
            "employee_unavailable",
            "planned_leave",
            "approved_leave",
            "approved_comp_off",
        }:
            if self.employee_id is None or self.start_date is None or self.end_date is None:
                raise ValueError("Employee time-off changes require employee_id, start_date, and end_date.")
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date.")
        elif self.change_type == "coverage_requirement":
            if self.process_id is None or self.minimum_staff is None:
                raise ValueError("Coverage changes require process_id and minimum_staff.")
        elif self.change_type == "operating_calendar":
            if (self.process_id is None) == (self.brand_id is None):
                raise ValueError(
                    "Calendar changes require exactly one of process_id or brand_id."
                )
            if self.operating_days is None:
                raise ValueError("Calendar changes require operating_days.")
            if self.operates_on_public_holidays is None:
                raise ValueError(
                    "Calendar changes must specify operates_on_public_holidays."
                )
            if any(day < 0 or day > 6 for day in self.operating_days):
                raise ValueError("operating_days values must use Monday=0 through Sunday=6.")
        return self


class SchedulingImpactRequest(SchedulingModel):
    organization_id: UUID
    start_date: date
    end_date: date
    change: ImpactChange

    @model_validator(mode="after")
    def validate_period(self) -> "SchedulingImpactRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class SchedulingConflictResponse(SchedulingModel):
    date: date
    brand_id: Optional[str] = None
    brand: Optional[str] = None
    process_id: Optional[str] = None
    process: Optional[str] = None
    employee_id: Optional[str] = None
    conflict_type: str
    severity: Literal["error", "warning"]
    explanation: str
    suggested_resolution: Optional[str] = None


class AssignmentResponse(SchedulingModel):
    assignment_date: date
    employee_id: str
    employee_name: Optional[str] = None
    brand_id: Optional[str] = None
    brand: Optional[str] = None
    process_id: Optional[str] = None
    process: Optional[str] = None
    pod_id: Optional[str] = None
    pod: Optional[str] = None
    shift_id: str
    shift: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class CoverageResponse(SchedulingModel):
    date: date
    brand_id: str
    brand: str
    process_id: str
    process: str
    shift_id: Optional[str] = None
    shift: Optional[str] = None
    required_staff: int
    actual_staff: int
    unfilled_positions: list[str]


class SchedulingStatistics(SchedulingModel):
    days_in_period: int
    operating_process_days: int
    required_positions: int
    filled_positions: int
    unfilled_positions: int
    employee_count: int


class EmployeeDiagnosticResponse(SchedulingModel):
    employee_id: str
    scheduled_assignments: int
    eligible_requirement_slots: int
    reason: str


class SchedulingResponse(SchedulingModel):
    organization_id: str
    is_valid: bool
    assignments: list[AssignmentResponse]
    coverage_summary: list[CoverageResponse]
    required_staffing: int
    actual_staffing: int
    unfilled_positions: list[CoverageResponse]
    conflicts: list[SchedulingConflictResponse]
    warnings: list[SchedulingConflictResponse]
    statistics: SchedulingStatistics
    employee_diagnostics: list[EmployeeDiagnosticResponse] = Field(default_factory=list)


class ImpactedAssignment(SchedulingModel):
    assignment: AssignmentResponse
    reason: str
    conflict_type: str
    suggested_resolution: Optional[str] = None
    possible_backup_employee_ids: list[str]


class SchedulingImpactResponse(SchedulingModel):
    organization_id: str
    start_date: date
    end_date: date
    invalidated_assignments: list[ImpactedAssignment]
    replacement_assignments: list[AssignmentResponse]
    coverage_summary: list[CoverageResponse]
    conflicts: list[SchedulingConflictResponse]
    warnings: list[SchedulingConflictResponse]
    required_staffing: int
    actual_staffing: int
    unfilled_positions: list[CoverageResponse]
    statistics: SchedulingStatistics
