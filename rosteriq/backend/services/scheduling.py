from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from typing import Iterable, Mapping, Optional, Sequence


@dataclass(frozen=True)
class Brand:
    id: str
    organization_id: str
    name: str


@dataclass(frozen=True)
class Process:
    id: str
    brand_id: str
    name: str
    operating_days: frozenset[int] = frozenset(range(7))
    operates_on_public_holidays: bool = False


@dataclass(frozen=True)
class Pod:
    id: str
    process_id: str
    name: str


@dataclass(frozen=True)
class Shift:
    id: str
    pod_id: str
    name: str
    start_time: time
    end_time: time
    required_headcount: int = 1


@dataclass(frozen=True)
class Availability:
    day_of_week: int
    is_available: bool
    start_time: Optional[time] = None
    end_time: Optional[time] = None


@dataclass(frozen=True)
class TimeOff:
    start_date: date
    end_date: date
    kind: str
    status: str


@dataclass(frozen=True)
class EmployeePreference:
    process_id: Optional[str] = None
    preferred_shift_id: Optional[str] = None
    preferred_days: frozenset[int] = frozenset()
    avoid_days: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Employee:
    id: str
    organization_id: str
    name: str
    active: bool = True
    weekly_off_days: frozenset[int] = frozenset()
    availability: tuple[Availability, ...] = ()
    time_off: tuple[TimeOff, ...] = ()
    skills: frozenset[str] = frozenset()
    preferences: tuple[EmployeePreference, ...] = ()
    max_hours_per_week: Optional[float] = None


@dataclass(frozen=True)
class CoverageRule:
    process_id: str
    minimum_staff: int
    shift_id: Optional[str] = None
    target_date: Optional[date] = None
    day_of_week: Optional[int] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


@dataclass(frozen=True)
class Assignment:
    employee_id: str
    shift_id: str
    assignment_date: date


@dataclass(frozen=True)
class ScheduleData:
    organization_id: str
    brands: Mapping[str, Brand]
    processes: Mapping[str, Process]
    pods: Mapping[str, Pod]
    employees: Mapping[str, Employee]
    shifts: Mapping[str, Shift]
    employee_pods: frozenset[tuple[str, str]]
    primary_employee_pods: frozenset[tuple[str, str]] = frozenset()
    coverage_rules: tuple[CoverageRule, ...] = ()
    public_holidays: frozenset[date] = frozenset()
    operating_overrides: Mapping[tuple[str, date], bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Conflict:
    date: date
    brand_id: Optional[str]
    brand: Optional[str]
    process_id: Optional[str]
    process: Optional[str]
    employee_id: Optional[str]
    conflict_type: str
    severity: str
    explanation: str
    suggested_resolution: Optional[str] = None


@dataclass(frozen=True)
class EmployeeDiagnostic:
    employee_id: str
    scheduled_assignments: int
    eligible_requirement_slots: int
    reason: str


@dataclass(frozen=True)
class Coverage:
    date: date
    brand_id: str
    brand: str
    process_id: str
    process: str
    shift_id: Optional[str]
    shift: Optional[str]
    required_staff: int
    actual_staff: int
    unfilled_positions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleReport:
    assignments: tuple[Assignment, ...]
    coverage: tuple[Coverage, ...]
    conflicts: tuple[Conflict, ...]
    statistics: Mapping[str, int | float]
    employee_diagnostics: tuple[EmployeeDiagnostic, ...] = ()

    @property
    def valid(self) -> bool:
        return not any(conflict.severity == "error" for conflict in self.conflicts)


def _process_for_shift(data: ScheduleData, shift: Shift) -> Optional[Process]:
    pod = data.pods.get(shift.pod_id)
    return data.processes.get(pod.process_id) if pod else None


def _open_on(data: ScheduleData, process: Process, day: date) -> bool:
    override = data.operating_overrides.get((process.id, day))
    if override is not None:
        return override
    if day.weekday() not in process.operating_days:
        return False
    return day not in data.public_holidays or process.operates_on_public_holidays


def _matching_rule(
    rules: Iterable[CoverageRule], day: date
) -> Optional[CoverageRule]:
    applicable = [
        rule
        for rule in rules
        if (rule.target_date is None or rule.target_date == day)
        and (rule.day_of_week is None or rule.day_of_week == day.weekday())
        and (rule.effective_from is None or rule.effective_from <= day)
        and (rule.effective_to is None or rule.effective_to >= day)
    ]
    if not applicable:
        return None
    return max(
        applicable,
        key=lambda rule: (
            rule.target_date is not None,
            rule.effective_from is not None,
            rule.effective_from or date.min,
            rule.effective_to or date.max,
            rule.day_of_week is not None,
            rule.minimum_staff,
        ),
    )


def _requirements_for(
    data: ScheduleData, process: Process, day: date, process_shifts: Sequence[Shift]
) -> list[tuple[Optional[str], tuple[str, ...], int]]:
    shifts = tuple(
        sorted(
            process_shifts,
            key=lambda shift: (shift.start_time, shift.id),
        )
    )
    process_rules = [
        rule
        for rule in data.coverage_rules
        if rule.process_id == process.id and rule.shift_id is None
    ]
    process_rule = _matching_rule(process_rules, day)
    if process_rule is not None:
        return [(None, tuple(shift.id for shift in shifts), process_rule.minimum_staff)]

    requirements: list[tuple[Optional[str], tuple[str, ...], int]] = []
    for shift in shifts:
        shift_rule = _matching_rule(
            (
                rule
                for rule in data.coverage_rules
                if rule.process_id == process.id and rule.shift_id == shift.id
            ),
            day,
        )
        required = shift_rule.minimum_staff if shift_rule else shift.required_headcount
        if required > 0:
            requirements.append((shift.id, (shift.id,), required))
    return requirements


def _shift_bounds(shift: Shift, day: date) -> tuple[int, int]:
    start_minute = shift.start_time.hour * 60 + shift.start_time.minute
    start = day.toordinal() * 1440 + start_minute
    end_minute = shift.end_time.hour * 60 + shift.end_time.minute
    end = day.toordinal() * 1440 + end_minute
    if end_minute <= start_minute:
        end += 1440
    return start, end


def _overlaps(first: Assignment, second: Assignment, data: ScheduleData) -> bool:
    first_shift = data.shifts.get(first.shift_id)
    second_shift = data.shifts.get(second.shift_id)
    if first_shift is None or second_shift is None:
        return first.assignment_date == second.assignment_date
    first_start, first_end = _shift_bounds(first_shift, first.assignment_date)
    second_start, second_end = _shift_bounds(second_shift, second.assignment_date)
    return first_start < second_end and second_start < first_end


def _shift_duration(shift: Shift) -> float:
    start = shift.start_time.hour * 60 + shift.start_time.minute
    end = shift.end_time.hour * 60 + shift.end_time.minute
    if end <= start:
        end += 1440
    return (end - start) / 60


def _time_contains(available_start: time, available_end: time, shift: Shift) -> bool:
    available_start_min = available_start.hour * 60 + available_start.minute
    available_end_min = available_end.hour * 60 + available_end.minute
    shift_start_min = shift.start_time.hour * 60 + shift.start_time.minute
    shift_end_min = shift.end_time.hour * 60 + shift.end_time.minute
    if available_end_min <= available_start_min:
        available_end_min += 1440
    if shift_end_min <= shift_start_min:
        shift_end_min += 1440
    return available_start_min <= shift_start_min and shift_end_min <= available_end_min


def _availability_issue(employee: Employee, shift: Shift, day: date) -> Optional[str]:
    if not employee.availability:
        return None
    rows = [row for row in employee.availability if row.day_of_week == day.weekday()]
    if not rows:
        return "The employee has no availability record for this weekday."
    available = [row for row in rows if row.is_available]
    if not available:
        return "Employee is marked unavailable for this day of the week."
    if all(
        row.start_time is not None
        and row.end_time is not None
        and not _time_contains(row.start_time, row.end_time, shift)
        for row in available
    ):
        return "The shift falls outside the employee's available hours."
    return None


def _time_off_issue(employee: Employee, day: date) -> Optional[str]:
    for record in employee.time_off:
        if not record.start_date <= day <= record.end_date:
            continue
        kind = record.kind.lower()
        state = record.status.lower()
        if kind == "leave" and state in {"planned", "approved"}:
            return "Employee has planned or approved leave on this date."
        if kind == "comp_off" and state == "approved":
            return "Employee has an approved comp-off on this date."
        if kind == "unavailability" and state in {"active", "approved"}:
            return "Employee is marked unavailable on this date."
    return None


def _weekly_hours(
    employee_id: str, day: date, assignments: Sequence[Assignment], data: ScheduleData
) -> float:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    total = 0.0
    for assignment in assignments:
        if assignment.employee_id != employee_id:
            continue
        shift = data.shifts.get(assignment.shift_id)
        if shift is None:
            continue
        if monday <= assignment.assignment_date <= sunday:
            total += _shift_duration(shift)
    return total


def _relevant_assignments(
    employee_id: str,
    day: date,
    assignments_by_employee: Mapping[str, Sequence[Assignment]],
) -> list[Assignment]:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    return [
        assignment
        for assignment in assignments_by_employee.get(employee_id, ())
        if monday <= assignment.assignment_date <= sunday
        or abs((assignment.assignment_date - day).days) <= 1
    ]


def _assignment_issues(
    assignment: Assignment,
    data: ScheduleData,
    other_assignments: Sequence[Assignment],
) -> list[tuple[str, str, Optional[str]]]:
    issues: list[tuple[str, str, Optional[str]]] = []
    employee = data.employees.get(assignment.employee_id)
    shift = data.shifts.get(assignment.shift_id)
    if employee is None or shift is None:
        return [(
            "invalid_assignment",
            "The assignment references an employee or shift outside this organization.",
            "Select an employee and shift belonging to this organization.",
        )]
    process = _process_for_shift(data, shift)
    if process is None or process.id not in data.processes:
        return [(
            "invalid_assignment",
            "The shift is not linked to a process in this organization.",
            "Correct the shift, pod, or process relationship.",
        )]
    if employee.organization_id != data.organization_id:
        issues.append((
            "invalid_resource_allocation",
            "The employee does not belong to the selected organization.",
            "Choose an employee from this organization.",
        ))
    brand = data.brands.get(process.brand_id)
    if brand is None or brand.organization_id != data.organization_id:
        issues.append((
            "invalid_resource_allocation",
            "The process does not belong to this organization.",
            "Choose a process and brand belonging to this organization.",
        ))
    if not employee.active:
        issues.append((
            "employee_inactive",
            "The employee is not active.",
            "Reactivate the employee or assign an active employee.",
        ))
    if (employee.id, shift.pod_id) not in data.employee_pods:
        issues.append((
            "invalid_resource_allocation",
            "The employee is not assigned to the pod serving this process.",
            "Assign the employee to an eligible pod or choose an eligible employee.",
        ))
    if not _open_on(data, process, assignment.assignment_date):
        conflict_type = (
            "public_holiday_violation"
            if assignment.assignment_date in data.public_holidays
            and not process.operates_on_public_holidays
            else "process_not_operating"
        )
        issues.append((
            conflict_type,
            "The process is not operating on this date under its configured calendar.",
            "Change the process calendar or remove the assignment.",
        ))
    if assignment.assignment_date.weekday() in employee.weekly_off_days:
        issues.append((
            "weekly_off_violation",
            "The assignment falls on the employee's weekly day off.",
            "Select another eligible employee or update the weekly-off pattern.",
        ))
    time_off_issue = _time_off_issue(employee, assignment.assignment_date)
    if time_off_issue:
        issues.append((
            "employee_unavailable",
            time_off_issue,
            "Select an available employee or change the approved time-off record.",
        ))
    availability_issue = _availability_issue(employee, shift, assignment.assignment_date)
    if availability_issue:
        issues.append((
            "employee_unavailable",
            availability_issue,
            "Select a shift within the employee's availability or choose another employee.",
        ))
    for other in other_assignments:
        if other.employee_id != employee.id:
            continue
        if other == assignment:
            issues.append((
                "duplicate_assignment",
                "The employee is assigned to the same shift more than once on this date.",
                "Remove the duplicate assignment.",
            ))
        elif _overlaps(assignment, other, data):
            issues.append((
                "overlapping_assignment",
                "The employee has another assignment whose shift overlaps this shift.",
                "Move one assignment to a non-overlapping shift or choose another employee.",
            ))
            break
    max_hours = employee.max_hours_per_week
    if max_hours is not None:
        hours = _weekly_hours(employee.id, assignment.assignment_date, other_assignments, data)
        if hours + _shift_duration(shift) > max_hours:
            issues.append((
                "weekly_hours_exceeded",
                f"The assignment would exceed the employee's {max_hours:g}-hour weekly limit.",
                "Reduce the employee's weekly hours or assign another employee.",
            ))
    return issues


def _preference_violated(
    employee: Employee, process: Process, shift: Shift, day: date
) -> bool:
    for preference in employee.preferences:
        if preference.process_id and preference.process_id != process.id:
            continue
        if preference.preferred_shift_id and preference.preferred_shift_id != shift.id:
            return True
        if preference.preferred_days and day.weekday() not in preference.preferred_days:
            return True
        if day.weekday() in preference.avoid_days:
            return True
    return False


def _preference_penalty(
    employee: Employee, process: Process, shift: Shift, day: date
) -> int:
    return int(_preference_violated(employee, process, shift, day))


def _candidate_pairs(
    data: ScheduleData,
    process: Process,
    day: date,
    shift_ids: Sequence[str],
    assigned_by_employee: Mapping[str, Sequence[Assignment]],
) -> list[tuple[Employee, Shift]]:
    candidates: list[tuple[Employee, Shift]] = []
    for shift_id in shift_ids:
        shift = data.shifts.get(shift_id)
        if shift is None or (
            candidate_process := _process_for_shift(data, shift)
        ) is None or candidate_process.id != process.id:
            continue
        for employee in data.employees.values():
            if (employee.id, shift.pod_id) not in data.employee_pods:
                continue
            trial = Assignment(employee.id, shift.id, day)
            existing = _relevant_assignments(employee.id, day, assigned_by_employee)
            if not _assignment_issues(trial, data, existing):
                candidates.append((employee, shift))
    return candidates


def _unfilled_reason(
    data: ScheduleData,
    process: Process,
    day: date,
    shift_ids: Sequence[str],
    assignments: Sequence[Assignment],
) -> str:
    reasons: Counter[str] = Counter()
    candidate_employees = [
        employee
        for employee in data.employees.values()
        if employee.organization_id == data.organization_id and employee.active
    ]
    assignments_by_employee: dict[str, list[Assignment]] = defaultdict(list)
    for assignment in assignments:
        assignments_by_employee[assignment.employee_id].append(assignment)
    resource_count = 0
    for shift_id in shift_ids:
        shift = data.shifts.get(shift_id)
        if shift is None or (
            candidate_process := _process_for_shift(data, shift)
        ) is None or candidate_process.id != process.id:
            continue
        for employee in candidate_employees:
            if (employee.id, shift.pod_id) not in data.employee_pods:
                continue
            resource_count += 1
            trial = Assignment(employee.id, shift.id, day)
            existing = _relevant_assignments(employee.id, day, assignments_by_employee)
            for _, explanation, _ in _assignment_issues(trial, data, existing):
                reasons[explanation] += 1
    if not shift_ids or not any(data.shifts.get(shift_id) for shift_id in shift_ids):
        return "No shift is configured for this process."
    if resource_count == 0:
        return "No active employee is assigned to a pod serving this process."
    if not reasons:
        return "No eligible employee is available for this requirement."
    return min(reasons, key=lambda explanation: (-reasons[explanation], explanation))


def _employee_diagnostics(
    data: ScheduleData,
    demands: Sequence[tuple[date, Process, Optional[str], tuple[str, ...], int]],
    assignments: Sequence[Assignment],
    invalid_assignment_indexes: frozenset[int],
) -> tuple[EmployeeDiagnostic, ...]:
    assignments_by_employee: dict[str, list[Assignment]] = defaultdict(list)
    for index, assignment in enumerate(assignments):
        if index not in invalid_assignment_indexes:
            assignments_by_employee[assignment.employee_id].append(assignment)

    diagnostics: list[EmployeeDiagnostic] = []
    for employee in sorted(data.employees.values(), key=lambda item: (item.name.casefold(), item.id)):
        reasons: Counter[str] = Counter()
        eligible_slots = 0
        existing = assignments_by_employee.get(employee.id, [])
        for day, process, _, shift_ids, _ in demands:
            for shift_id in shift_ids:
                shift = data.shifts.get(shift_id)
                if shift is None:
                    continue
                issues = _assignment_issues(
                    Assignment(employee.id, shift.id, day), data, existing
                )
                if issues:
                    for _, explanation, _ in issues:
                        reasons[explanation] += 1
                else:
                    eligible_slots += 1
        scheduled = len(existing)
        if scheduled:
            reason = f"Scheduled in {scheduled} valid assignment(s)."
        elif eligible_slots:
            reason = (
                f"Eligible for {eligible_slots} requirement slot(s), but the load-balanced "
                "proposal did not select this employee."
            )
        elif reasons:
            reason = min(reasons, key=lambda explanation: (-reasons[explanation], explanation))
        else:
            reason = "No operating shift or staffing requirement matches the employee's eligible pod."
        diagnostics.append(EmployeeDiagnostic(
            employee_id=employee.id,
            scheduled_assignments=scheduled,
            eligible_requirement_slots=eligible_slots,
            reason=reason,
        ))
    return tuple(diagnostics)


def _active_requirements(
    data: ScheduleData, first_day: date, last_day: date
) -> list[tuple[date, Process, Optional[str], tuple[str, ...], int]]:
    demands = []
    shifts_by_process: dict[str, list[Shift]] = defaultdict(list)
    for shift in data.shifts.values():
        process = _process_for_shift(data, shift)
        if process:
            shifts_by_process[process.id].append(shift)
    for offset in range((last_day - first_day).days + 1):
        day = first_day + timedelta(days=offset)
        for process in sorted(data.processes.values(), key=lambda item: item.id):
            if not _open_on(data, process, day):
                continue
            for shift_id, shift_ids, required in _requirements_for(
                data, process, day, shifts_by_process.get(process.id, ())
            ):
                if required > 0:
                    demands.append((day, process, shift_id, shift_ids, required))
    return demands


def _coverage_rows(
    data: ScheduleData,
    demands: Sequence[tuple[date, Process, Optional[str], tuple[str, ...], int]],
    assignments: Sequence[Assignment],
    invalid_assignment_indexes: frozenset[int],
) -> tuple[Coverage, ...]:
    rows = []
    valid_staffing: Counter[tuple[date, str, str]] = Counter()
    for index, assignment in enumerate(assignments):
        if index in invalid_assignment_indexes:
            continue
        shift = data.shifts.get(assignment.shift_id)
        process = _process_for_shift(data, shift) if shift else None
        if process:
            valid_staffing[(assignment.assignment_date, process.id, assignment.shift_id)] += 1
    for day, process, shift_id, shift_ids, required in demands:
        actual = sum(
            valid_staffing[(day, process.id, eligible_shift_id)]
            for eligible_shift_id in shift_ids
        )
        missing = max(0, required - actual)
        brand = data.brands.get(process.brand_id)
        shift = data.shifts.get(shift_id) if shift_id else None
        if brand is None:
            continue
        reason = (
            _unfilled_reason(data, process, day, shift_ids, assignments)
            if missing
            else ""
        )
        rows.append(Coverage(
            date=day,
            brand_id=brand.id,
            brand=brand.name,
            process_id=process.id,
            process=process.name,
            shift_id=shift_id,
            shift=shift.name if shift else None,
            required_staff=required,
            actual_staff=actual,
            unfilled_positions=tuple(reason for _ in range(missing)),
        ))
    return tuple(rows)


def _conflict_for_assignment(
    assignment: Assignment,
    data: ScheduleData,
    conflict_type: str,
    explanation: str,
    resolution: Optional[str],
    severity: str = "error",
) -> Conflict:
    shift = data.shifts.get(assignment.shift_id)
    process = _process_for_shift(data, shift) if shift else None
    brand = data.brands.get(process.brand_id) if process else None
    employee_id = assignment.employee_id if assignment.employee_id in data.employees else None
    return Conflict(
        date=assignment.assignment_date,
        brand_id=brand.id if brand else None,
        brand=brand.name if brand else None,
        process_id=process.id if process else None,
        process=process.name if process else None,
        employee_id=employee_id,
        conflict_type=conflict_type,
        severity=severity,
        explanation=explanation,
        suggested_resolution=resolution,
    )


def validate_roster(
    data: ScheduleData,
    assignments: Sequence[Assignment],
    first_day: date,
    last_day: date,
) -> ScheduleReport:
    conflicts: list[Conflict] = []
    invalid_indexes: set[int] = set()
    indexed_by_employee: dict[str, list[tuple[int, Assignment]]] = defaultdict(list)
    for index, assignment in enumerate(assignments):
        indexed_by_employee[assignment.employee_id].append((index, assignment))
    for index, assignment in enumerate(assignments):
        if not first_day <= assignment.assignment_date <= last_day:
            invalid_indexes.add(index)
            conflicts.append(_conflict_for_assignment(
                assignment,
                data,
                "assignment_outside_period",
                "The assignment date is outside the requested validation period.",
                "Move the assignment into the selected period or validate the correct period.",
            ))
            continue
        others = [
            candidate
            for other_index, candidate in indexed_by_employee[assignment.employee_id]
            if other_index != index
            and (
                abs((candidate.assignment_date - assignment.assignment_date).days) <= 1
                or (
                    assignment.assignment_date
                    - timedelta(days=assignment.assignment_date.weekday())
                )
                <= candidate.assignment_date
                <= (
                    assignment.assignment_date
                    - timedelta(days=assignment.assignment_date.weekday())
                    + timedelta(days=6)
                )
            )
        ]
        issues = _assignment_issues(assignment, data, others)
        if issues:
            invalid_indexes.add(index)
            for conflict_type, explanation, resolution in issues:
                conflicts.append(_conflict_for_assignment(
                    assignment, data, conflict_type, explanation, resolution
                ))
        else:
            shift = data.shifts[assignment.shift_id]
            process = _process_for_shift(data, shift)
            employee = data.employees[assignment.employee_id]
            if process and _preference_violated(
                employee, process, shift, assignment.assignment_date
            ):
                conflicts.append(_conflict_for_assignment(
                    assignment,
                    data,
                    "preference_violation",
                    "The assignment does not match one or more configured employee preferences.",
                    "Choose a preferred shift or date when coverage permits.",
                    severity="warning",
                ))

    demands = _active_requirements(data, first_day, last_day)
    coverage = _coverage_rows(data, demands, assignments, frozenset(invalid_indexes))
    for item in coverage:
        missing = item.required_staff - item.actual_staff
        if missing > 0:
            reasons = sorted(set(item.unfilled_positions))
            shift_desc = f" on shift '{item.shift}'" if item.shift else ""
            conflicts.append(Conflict(
                date=item.date,
                brand_id=item.brand_id,
                brand=item.brand,
                process_id=item.process_id,
                process=item.process,
                employee_id=None,
                conflict_type="insufficient_staffing",
                severity="error",
                explanation=(
                    f"{missing} of {item.required_staff} required position(s) remain unfilled"
                    f"{shift_desc}. " + (" ".join(reasons) if reasons else "")
                ).strip(),
                suggested_resolution=(
                    "Assign an eligible employee, adjust the minimum staffing rule, "
                    "or review the process operating calendar."
                ),
            ))

    total_required = sum(item.required_staff for item in coverage)
    total_filled = sum(item.actual_staff for item in coverage)
    statistics: dict[str, int | float] = {
        "days_in_period": (last_day - first_day).days + 1,
        "operating_process_days": len({(item.date, item.process_id) for item in coverage}),
        "required_positions": total_required,
        "filled_positions": total_filled,
        "unfilled_positions": max(0, total_required - total_filled),
        "employee_count": len({item.employee_id for item in assignments if item.employee_id in data.employees}),
    }
    diagnostics = _employee_diagnostics(
        data, demands, assignments, frozenset(invalid_indexes)
    )
    return ScheduleReport(
        assignments=tuple(assignments),
        coverage=coverage,
        conflicts=tuple(conflicts),
        statistics=statistics,
        employee_diagnostics=diagnostics,
    )


def generate_monthly_roster(
    data: ScheduleData, year: int, month: int
) -> ScheduleReport:
    first_day = date(year, month, 1)
    last_day = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    demands = _active_requirements(data, first_day, last_day)
    assignments: list[Assignment] = []
    assigned_by_employee: dict[str, list[Assignment]] = defaultdict(list)
    demand_slots = []
    for day, process, shift_id, shift_ids, required in demands:
        eligible = _candidate_pairs(data, process, day, shift_ids, {})
        eligible_count = len({employee.id for employee, _ in eligible})
        for slot_index in range(required):
            demand_slots.append((
                eligible_count,
                day,
                process,
                shift_id,
                shift_ids,
                slot_index,
            ))
    demand_slots.sort(key=lambda slot: (
        slot[0], slot[1], slot[2].id, slot[3] or "", slot[5]
    ))
    employee_load: Counter[str] = Counter()
    for _, day, process, _, shift_ids, _ in demand_slots:
        candidates = _candidate_pairs(
            data, process, day, shift_ids, assigned_by_employee
        )
        if not candidates:
            continue
        candidates.sort(key=lambda pair: (
            employee_load[pair[0].id],
            _weekly_hours(pair[0].id, day, assignments, data),
            _preference_penalty(pair[0], process, pair[1], day),
            (pair[0].id, pair[1].pod_id) not in data.employee_pods,
            process.name.casefold() not in {skill.casefold() for skill in pair[0].skills},
            (pair[0].id, pair[1].pod_id) not in data.primary_employee_pods,
            pair[0].id,
            pair[1].id,
        ))
        employee, shift = candidates[0]
        assignment = Assignment(employee.id, shift.id, day)
        assignments.append(assignment)
        assigned_by_employee[employee.id].append(assignment)
        employee_load[employee.id] += 1
    return validate_roster(data, assignments, first_day, last_day)


def with_time_off(
    data: ScheduleData,
    employee_id: str,
    start_date: date,
    end_date: date,
    kind: str,
    status: str,
) -> ScheduleData:
    employee = data.employees.get(employee_id)
    if employee is None:
        return data
    updated = replace(
        employee,
        time_off=employee.time_off + (TimeOff(start_date, end_date, kind, status),),
    )
    employees = dict(data.employees)
    employees[employee_id] = updated
    return replace(data, employees=employees)


def with_coverage_rule(data: ScheduleData, rule: CoverageRule) -> ScheduleData:
    return replace(data, coverage_rules=data.coverage_rules + (rule,))


def with_operating_calendar(
    data: ScheduleData,
    process_id: str,
    operating_days: frozenset[int],
    operates_on_public_holidays: bool,
) -> ScheduleData:
    process = data.processes.get(process_id)
    if process is None:
        return data
    processes = dict(data.processes)
    processes[process_id] = replace(
        process,
        operating_days=operating_days,
        operates_on_public_holidays=operates_on_public_holidays,
    )
    return replace(data, processes=processes)


def with_brand_operating_calendar(
    data: ScheduleData,
    brand_id: str,
    operating_days: frozenset[int],
    operates_on_public_holidays: bool,
) -> ScheduleData:
    if brand_id not in data.brands:
        return data
    processes = {
        process_id: replace(
            process,
            operating_days=operating_days,
            operates_on_public_holidays=operates_on_public_holidays,
        )
        if process.brand_id == brand_id
        else process
        for process_id, process in data.processes.items()
    }
    return replace(data, processes=processes)


def evaluate_impact(
    before: ScheduleData,
    after: ScheduleData,
    assignments: Sequence[Assignment],
    first_day: date,
    last_day: date,
) -> dict[str, object]:
    updated = validate_roster(after, assignments, first_day, last_day)
    indexed_by_employee: dict[str, list[tuple[int, Assignment]]] = defaultdict(list)
    for index, assignment in enumerate(assignments):
        indexed_by_employee[assignment.employee_id].append((index, assignment))
    invalidated = []
    for index, assignment in enumerate(assignments):
        others = [
            candidate
            for other_index, candidate in indexed_by_employee[assignment.employee_id]
            if other_index != index
        ]
        before_issues = _assignment_issues(assignment, before, others)
        after_issues = _assignment_issues(assignment, after, others)
        if after_issues and not before_issues:
            shift = after.shifts.get(assignment.shift_id)
            process = _process_for_shift(after, shift) if shift else None
            invalidated.append({
                "assignment_index": index,
                "assignment": assignment,
                "reason": after_issues[0][1],
                "conflict_type": after_issues[0][0],
                "suggested_resolution": after_issues[0][2],
                "process_id": process.id if process else None,
                "shift_id": assignment.shift_id,
            })

    backups: dict[tuple[date, str, str], list[str]] = defaultdict(list)
    replacement_assignments: list[Assignment] = []
    replaced_indexes: set[int] = set()
    invalidated_indexes = {
        int(item["assignment_index"]) for item in invalidated
    }
    proposed_assignments = [
        assignment
        for index, assignment in enumerate(assignments)
        if index not in invalidated_indexes
    ]
    for item in invalidated:
        assignment = item["assignment"]
        process = after.processes.get(item["process_id"])
        if process is None:
            continue
        shift_ids = (item["shift_id"],)
        occupied = list(proposed_assignments)
        occupied_by_employee: dict[str, list[Assignment]] = defaultdict(list)
        for candidate in occupied:
            occupied_by_employee[candidate.employee_id].append(candidate)
        replacement_employee_id = None
        for employee, _ in _candidate_pairs(
            after,
            process,
            assignment.assignment_date,
            shift_ids,
            occupied_by_employee,
        ):
            if employee.id != assignment.employee_id:
                key = (assignment.assignment_date, process.id, assignment.shift_id)
                if employee.id not in backups[key]:
                    backups[key].append(employee.id)
                if replacement_employee_id is None:
                    replacement_employee_id = employee.id
        key = (assignment.assignment_date, process.id, assignment.shift_id)
        if replacement_employee_id is not None:
            replacement = Assignment(
                replacement_employee_id, assignment.shift_id, assignment.assignment_date
            )
            replacement_assignments.append(replacement)
            proposed_assignments.append(replacement)
            replaced_indexes.add(int(item["assignment_index"]))

    recommended_report = validate_roster(
        after, proposed_assignments, first_day, last_day
    )
    unresolved_conflicts = []
    for item in invalidated:
        if int(item["assignment_index"]) in replaced_indexes:
            continue
        assignment = item["assignment"]
        process = after.processes.get(item["process_id"])
        brand = after.brands.get(process.brand_id) if process else None
        unresolved_conflicts.append(Conflict(
            date=assignment.assignment_date,
            brand_id=brand.id if brand else None,
            brand=brand.name if brand else None,
            process_id=process.id if process else None,
            process=process.name if process else None,
            employee_id=assignment.employee_id,
            conflict_type=item["conflict_type"],
            severity="error",
            explanation=item["reason"],
            suggested_resolution=item["suggested_resolution"],
        ))
    if unresolved_conflicts:
        recommended_report = replace(
            recommended_report,
            conflicts=recommended_report.conflicts + tuple(unresolved_conflicts),
        )

    return {
        "invalidated_assignments": tuple(invalidated),
        "replacement_assignments": tuple(replacement_assignments),
        "recommended_backups": tuple(
            {
                "date": day,
                "process_id": process_id,
                "shift_id": shift_id,
                "employee_ids": tuple(employee_ids),
            }
            for (day, process_id, shift_id), employee_ids in sorted(
                backups.items(), key=lambda entry: entry[0]
            )
        ),
        "report": recommended_report,
        "original_report": updated,
    }
