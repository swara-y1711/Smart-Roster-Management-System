import csv
import sys
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from models.scheduling import SchedulingResponse
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
from routers.scheduling import _report_response, load_schedule_data


ORG = "org-a"
NOVEMBER_2026 = date(2026, 11, 1)


def process_fixture(
    employee_ids=("e1", "e2"),
    *,
    required=1,
    operating_days=frozenset(range(7)),
    operates_on_public_holidays=False,
    holidays=frozenset(),
    weekly_offs=None,
    availability=None,
    time_off=None,
    preferences=None,
    organization_id=ORG,
):
    brand = Brand("b1", organization_id, "Brand One")
    process = Process(
        "p1",
        brand.id,
        "Support",
        operating_days=operating_days,
        operates_on_public_holidays=operates_on_public_holidays,
    )
    pod = Pod("pod1", process.id, "Support Pod")
    shift = Shift("s1", pod.id, "Day", time(9), time(17), required)
    employees = {}
    for employee_id in employee_ids:
        employees[employee_id] = Employee(
            id=employee_id,
            organization_id=organization_id,
            name=employee_id,
            weekly_off_days=frozenset((weekly_offs or {}).get(employee_id, ())),
            availability=tuple((availability or {}).get(employee_id, ())),
            time_off=tuple((time_off or {}).get(employee_id, ())),
            preferences=tuple((preferences or {}).get(employee_id, ())),
        )
    return ScheduleData(
        organization_id=ORG,
        brands={brand.id: brand},
        processes={process.id: process},
        pods={pod.id: pod},
        employees=employees,
        shifts={shift.id: shift},
        employee_pods=frozenset((employee_id, pod.id) for employee_id in employee_ids),
        public_holidays=holidays,
    )


def two_process_data(
    *,
    process_days=(frozenset(range(7)), frozenset(range(7))),
    brands=("b1", "b1"),
    shift_times=((time(9), time(17)), (time(13), time(21))),
    employees_per_process=(("e1",), ("e2",)),
    requirements=(1, 1),
):
    brand_map = {
        brand_id: Brand(brand_id, ORG, f"Brand {brand_id}")
        for brand_id in set(brands)
    }
    processes = {}
    pods = {}
    shifts = {}
    employees = {}
    employee_pods = set()
    for index in range(2):
        process_id = f"p{index + 1}"
        pod_id = f"pod{index + 1}"
        shift_id = f"s{index + 1}"
        processes[process_id] = Process(
            process_id,
            brands[index],
            f"Process {index + 1}",
            operating_days=process_days[index],
        )
        pods[pod_id] = Pod(pod_id, process_id, f"Pod {index + 1}")
        shifts[shift_id] = Shift(
            shift_id,
            pod_id,
            f"Shift {index + 1}",
            shift_times[index][0],
            shift_times[index][1],
            requirements[index],
        )
        for employee_id in employees_per_process[index]:
            employees[employee_id] = Employee(employee_id, ORG, employee_id)
            employee_pods.add((employee_id, pod_id))
    return ScheduleData(
        organization_id=ORG,
        brands=brand_map,
        processes=processes,
        pods=pods,
        employees=employees,
        shifts=shifts,
        employee_pods=frozenset(employee_pods),
    )


def test_successful_monthly_roster_generation_is_deterministic():
    data = process_fixture(("e1", "e2", "e3"))
    first = generate_monthly_roster(data, 2026, 11)
    second = generate_monthly_roster(data, 2026, 11)
    assert first.valid
    assert first.assignments == second.assignments
    assert len(first.assignments) == 30
    assert first.statistics["unfilled_positions"] == 0


def test_generated_roster_matches_the_structured_api_response_schema():
    data = process_fixture(("e1",))
    report = generate_monthly_roster(data, 2026, 11)
    response = SchedulingResponse.model_validate(
        _report_response(data, report, data.organization_id)
    )
    assert response.is_valid
    assert response.assignments[0].employee_name == "e1"
    assert response.required_staffing == response.actual_staffing == 30


def test_single_resource_brand_covers_its_required_shift():
    data = process_fixture(("e1",))
    report = validate_roster(
        data, [Assignment("e1", "s1", date(2026, 11, 2))],
        date(2026, 11, 2), date(2026, 11, 2),
    )
    assert report.valid
    assert report.coverage[0].actual_staff == 1


def test_multiple_resources_cover_multiple_processes_under_one_brand():
    data = two_process_data()
    report = generate_monthly_roster(data, 2026, 11)
    assert report.valid
    assert {row.process_id for row in report.coverage} == {"p1", "p2"}
    assert report.statistics["required_positions"] == 60


def test_multiple_employees_share_one_process_requirement():
    data = process_fixture(("e1", "e2"), required=2)
    report = validate_roster(
        data,
        [
            Assignment("e1", "s1", date(2026, 11, 2)),
            Assignment("e2", "s1", date(2026, 11, 2)),
        ],
        date(2026, 11, 2),
        date(2026, 11, 2),
    )
    assert report.valid
    assert report.coverage[0].actual_staff == 2


def test_processes_can_have_different_operating_calendars():
    data = two_process_data(
        process_days=(frozenset({0}), frozenset({1})),
    )
    report = generate_monthly_roster(data, 2026, 11)
    active_days = {(row.process_id, row.date.weekday()) for row in report.coverage}
    assert active_days == {("p1", 0), ("p2", 1)}
    assert report.valid


def test_365_day_process_operates_on_sundays_and_public_holidays():
    holiday = date(2026, 1, 1)
    data = process_fixture(
        ("e1",),
        operating_days=frozenset(range(7)),
        operates_on_public_holidays=True,
        holidays=frozenset({holiday}),
    )
    reports = [
        generate_monthly_roster(data, 2026, month) for month in range(1, 13)
    ]
    assignments = [assignment for report in reports for assignment in report.assignments]
    assert all(report.valid for report in reports)
    assert len(assignments) == 365
    assert any(assignment.assignment_date.weekday() == 6 for assignment in assignments)
    assert any(assignment.assignment_date == holiday for assignment in assignments)


def test_sundays_and_public_holidays_can_be_closed():
    holiday = date(2026, 11, 4)
    data = process_fixture(
        ("e1",),
        operating_days=frozenset(range(6)),
        operates_on_public_holidays=False,
        holidays=frozenset({holiday}),
    )
    report = generate_monthly_roster(data, 2026, 11)
    assert all(row.date.weekday() != 6 and row.date != holiday for row in report.coverage)
    assert not any(
        assignment.assignment_date.weekday() == 6 or assignment.assignment_date == holiday
        for assignment in report.assignments
    )


def test_individual_weekly_off_is_enforced():
    data = process_fixture(
        ("e1", "e2"),
        weekly_offs={"e1": {0}},
    )
    report = generate_monthly_roster(data, 2026, 11)
    assert all(
        not (assignment.employee_id == "e1" and assignment.assignment_date.weekday() == 0)
        for assignment in report.assignments
    )


def test_planned_leave_excludes_employee_from_generation():
    leave = TimeOff(date(2026, 11, 3), date(2026, 11, 3), "leave", "planned")
    data = process_fixture(("e1",), time_off={"e1": (leave,)})
    report = generate_monthly_roster(data, 2026, 11)
    assert not any(
        assignment.assignment_date == leave.start_date for assignment in report.assignments
    )
    assert any(
        conflict.conflict_type == "insufficient_staffing"
        and conflict.date == leave.start_date
        for conflict in report.conflicts
    )


def test_approved_comp_off_excludes_employee_from_generation():
    comp_off = TimeOff(date(2026, 11, 3), date(2026, 11, 3), "comp_off", "approved")
    data = process_fixture(("e1",), time_off={"e1": (comp_off,)})
    report = generate_monthly_roster(data, 2026, 11)
    assert not any(
        assignment.assignment_date == comp_off.start_date for assignment in report.assignments
    )


def test_recurring_employee_availability_is_enforced():
    data = process_fixture(
        ("e1",),
        availability={"e1": (Availability(0, False),)},
    )
    report = generate_monthly_roster(data, 2026, 11)
    assert not any(assignment.assignment_date.weekday() == 0 for assignment in report.assignments)


def test_configured_availability_does_not_assume_unlisted_weekdays_are_available():
    data = process_fixture(
        ("e1",),
        availability={
            "e1": (Availability(0, True, time(9), time(17)),)
        },
    )
    report = generate_monthly_roster(data, 2026, 11)
    assert all(assignment.assignment_date.weekday() == 0 for assignment in report.assignments)


def test_validation_reports_mandatory_calendar_and_employee_conflict_types():
    monday = date(2026, 11, 2)
    holiday = date(2026, 11, 3)
    scenarios = (
        (
            process_fixture(("e1",), holidays=frozenset({holiday})),
            holiday,
            "public_holiday_violation",
        ),
        (
            process_fixture(("e1",), weekly_offs={"e1": {monday.weekday()}}),
            monday,
            "weekly_off_violation",
        ),
        (
            process_fixture(
                ("e1",),
                time_off={
                    "e1": (TimeOff(monday, monday, "leave", "planned"),)
                },
            ),
            monday,
            "employee_unavailable",
        ),
        (
            process_fixture(
                ("e1",),
                time_off={
                    "e1": (TimeOff(monday, monday, "comp_off", "approved"),)
                },
            ),
            monday,
            "employee_unavailable",
        ),
        (
            process_fixture(
                ("e1",),
                availability={"e1": (Availability(monday.weekday(), False),)},
            ),
            monday,
            "employee_unavailable",
        ),
    )
    for data, day, expected_type in scenarios:
        report = validate_roster(
            data,
            [Assignment("e1", "s1", day)],
            day,
            day,
        )
        assert any(conflict.conflict_type == expected_type for conflict in report.conflicts)


def test_minimum_staffing_requirement_is_reported():
    data = process_fixture(("e1",), required=2)
    report = generate_monthly_roster(data, 2026, 11)
    monday = next(row for row in report.coverage if row.date == date(2026, 11, 2))
    assert monday.required_staff == 2
    assert monday.actual_staff == 1
    assert len(monday.unfilled_positions) == 1


def test_employee_can_be_assigned_to_multiple_brands_without_overlap():
    data = two_process_data(
        brands=("b1", "b2"),
        shift_times=((time(9), time(13)), (time(13), time(17))),
        employees_per_process=(("e1",), ("e1",)),
    )
    report = validate_roster(
        data,
        [
            Assignment("e1", "s1", date(2026, 11, 2)),
            Assignment("e1", "s2", date(2026, 11, 2)),
        ],
        date(2026, 11, 2),
        date(2026, 11, 2),
    )
    assert report.valid
    assert len(report.assignments) == 2


def test_overlapping_shifts_are_rejected():
    data = two_process_data(
        shift_times=((time(9), time(17)), (time(13), time(21))),
        employees_per_process=(("e1",), ("e1",)),
    )
    report = validate_roster(
        data,
        [
            Assignment("e1", "s1", date(2026, 11, 2)),
            Assignment("e1", "s2", date(2026, 11, 2)),
        ],
        date(2026, 11, 2),
        date(2026, 11, 2),
    )
    assert any(conflict.conflict_type == "overlapping_assignment" for conflict in report.conflicts)
    assert report.statistics["filled_positions"] == 0


def test_preferences_guide_generation_and_validate_as_warnings():
    data = process_fixture(("e1", "e2"))
    second_shift = Shift("s2", "pod1", "Late", time(13), time(21), 1)
    employees = dict(data.employees)
    employees["e1"] = Employee(
        id="e1",
        organization_id=ORG,
        name="e1",
        preferences=(EmployeePreference(preferred_shift_id="s2"),),
    )
    data = ScheduleData(
        organization_id=data.organization_id,
        brands=data.brands,
        processes=data.processes,
        pods=data.pods,
        employees=employees,
        shifts={**data.shifts, second_shift.id: second_shift},
        employee_pods=data.employee_pods,
        coverage_rules=(CoverageRule("p1", 1),),
    )
    report = generate_monthly_roster(data, 2026, 11)
    assert report.assignments[0].employee_id == "e1"
    assert report.assignments[0].shift_id == "s2"
    modified = validate_roster(
        data,
        [Assignment("e1", "s1", date(2026, 11, 2))],
        date(2026, 11, 2),
        date(2026, 11, 2),
    )
    assert any(
        conflict.conflict_type == "preference_violation"
        and conflict.severity == "warning"
        for conflict in modified.conflicts
    )
    assert modified.valid


def test_insufficient_staffing_is_a_mandatory_error():
    report = generate_monthly_roster(process_fixture(("e1",), required=2), 2026, 11)
    assert not report.valid
    assert any(
        conflict.conflict_type == "insufficient_staffing"
        and conflict.severity == "error"
        for conflict in report.conflicts
    )


def test_single_resource_absence_recommends_backup_and_preserves_coverage():
    data = process_fixture(("e1", "e2"))
    day = date(2026, 11, 2)
    after = with_time_off(data, "e1", day, day, "unavailability", "active")
    impact = evaluate_impact(
        data,
        after,
        [Assignment("e1", "s1", day)],
        day,
        day,
    )
    assert len(impact["invalidated_assignments"]) == 1
    assert impact["report"].statistics["unfilled_positions"] == 0
    assert impact["recommended_backups"][0]["employee_ids"] == ("e2",)
    assert impact["replacement_assignments"] == (Assignment("e2", "s1", day),)


def test_single_resource_absence_without_backup_reports_coverage_gap():
    data = process_fixture(("e1",), required=1)
    day = date(2026, 11, 2)
    after = with_time_off(data, "e1", day, day, "unavailability", "active")
    impact = evaluate_impact(
        data,
        after,
        [Assignment("e1", "s1", day)],
        day,
        day,
    )
    assert len(impact["invalidated_assignments"]) == 1
    assert impact["report"].statistics["unfilled_positions"] == 1
    assert impact["replacement_assignments"] == ()


def test_multi_resource_brand_replaces_absent_employee_with_remaining_resource():
    data = process_fixture(("e1", "e2"), required=1)
    day = date(2026, 11, 2)
    after = with_time_off(data, "e1", day, day, "unavailability", "active")
    impact = evaluate_impact(
        data,
        after,
        [Assignment("e1", "s1", day)],
        day,
        day,
    )
    assert len(impact["invalidated_assignments"]) == 1
    assert impact["report"].statistics["unfilled_positions"] == 0
    assert impact["replacement_assignments"] == (Assignment("e2", "s1", day),)


def test_revalidation_after_requirement_change_finds_new_gap():
    data = process_fixture(("e1",))
    updated = with_coverage_rule(data, CoverageRule("p1", 2))
    day = date(2026, 11, 2)
    impact = evaluate_impact(
        data,
        updated,
        [Assignment("e1", "s1", day)],
        day,
        day,
    )
    assert impact["report"].statistics["unfilled_positions"] == 1
    assert any(
        conflict.conflict_type == "insufficient_staffing"
        for conflict in impact["report"].conflicts
    )


def test_calendar_change_explicitly_invalidates_existing_assignment():
    data = process_fixture(("e1",))
    day = date(2026, 11, 8)
    updated = with_operating_calendar(data, "p1", frozenset(range(6)), False)
    impact = evaluate_impact(
        data,
        updated,
        [Assignment("e1", "s1", day)],
        day,
        day,
    )
    assert len(impact["invalidated_assignments"]) == 1
    assert any(
        conflict.conflict_type == "process_not_operating"
        for conflict in impact["report"].conflicts
    )


def test_brand_calendar_change_revalidates_all_its_processes():
    data = two_process_data()
    day = date(2026, 11, 8)
    updated = with_brand_operating_calendar(
        data, "b1", frozenset(range(6)), False
    )
    impact = evaluate_impact(
        data,
        updated,
        [
            Assignment("e1", "s1", day),
            Assignment("e2", "s2", day),
        ],
        day,
        day,
    )
    assert len(impact["invalidated_assignments"]) == 2
    assert {
        conflict.process_id
        for conflict in impact["report"].conflicts
        if conflict.conflict_type == "process_not_operating"
    } == {"p1", "p2"}


def test_cross_organization_employee_cannot_cover_a_process():
    data = process_fixture(("e1",))
    employees = dict(data.employees)
    employees["foreign"] = Employee("foreign", "org-b", "Foreign")
    data = ScheduleData(
        organization_id=data.organization_id,
        brands=data.brands,
        processes=data.processes,
        pods=data.pods,
        employees=employees,
        shifts=data.shifts,
        employee_pods=data.employee_pods | frozenset({("foreign", "pod1")}),
    )
    day = date(2026, 11, 2)
    report = validate_roster(
        data, [Assignment("foreign", "s1", day)], day, day
    )
    assert report.statistics["filled_positions"] == 0
    assert any(
        conflict.conflict_type == "invalid_resource_allocation"
        for conflict in report.conflicts
    )


def test_loader_rejects_an_organization_hidden_by_authenticated_rls():
    class InvisibleOrganizationQuery:
        def select(self, *args):
            _ = args
            return self

        def eq(self, *args):
            _ = args
            return self

        def range(self, *args):
            _ = args
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class AuthenticatedClient:
        def table(self, name):
            assert name == "organizations"
            return InvisibleOrganizationQuery()

    with pytest.raises(HTTPException) as error:
        load_schedule_data(
            AuthenticatedClient(), "other-organization",
            date(2026, 11, 1), date(2026, 11, 30),
        )
    assert error.value.status_code == 404


def _read_csv(name):
    root = Path(__file__).resolve().parents[3]
    with (root / "rosteriq_synthetic_data" / name).open(
        encoding="utf-8-sig", newline=""
    ) as file:
        return list(csv.DictReader(file))


def test_existing_synthetic_workforce_data_generates_roster():
    brands = _read_csv("brands.csv")
    processes = _read_csv("processes.csv")
    pods = _read_csv("pods.csv")
    employees = _read_csv("employees.csv")
    weekly_offs = _read_csv("employee_availability.csv")
    skills = _read_csv("employee_skills.csv")
    org_id = "1"
    brand_row = next(row for row in brands if row["organization_id"] == org_id)
    org_processes = [row for row in processes if row["organization_id"] == org_id]
    org_employees = [row for row in employees if row["organization_id"] == org_id]
    process_ids = {row["process_id"] for row in org_processes}
    org_pods = [row for row in pods if row["process_id"] in process_ids]
    off_names = {row["employee_id"]: row["weekly_off"] for row in weekly_offs}
    weekday_numbers = {
        name: number
        for number, name in enumerate(
            ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        )
    }
    skill_names = {}
    for row in skills:
        skill_names.setdefault(row["employee_id"], set()).add(row["skill_name"])

    assigned_pod_ids = {row["pod_id"] for row in org_employees}
    assigned_process_ids = {
        row["process_id"] for row in org_pods if row["pod_id"] in assigned_pod_ids
    }
    process_map = {
        row["process_id"]: Process(
            row["process_id"],
            brand_row["brand_id"],
            row["process_name"],
            operating_days=frozenset(range(6)),
        )
        for row in org_processes
        if row["process_id"] in assigned_process_ids
    }
    pod_map = {
        row["pod_id"]: Pod(row["pod_id"], row["process_id"], row["pod_name"])
        for row in org_pods
        if row["pod_id"] in assigned_pod_ids
    }
    shift_map = {
        f"s-{pod['pod_id']}": Shift(
            f"s-{pod['pod_id']}", pod["pod_id"], "Synthetic Day", time(9), time(17)
        )
        for pod in org_pods
        if pod["pod_id"] in assigned_pod_ids
    }
    employee_map = {
        row["employee_id"]: Employee(
            id=row["employee_id"],
            organization_id=org_id,
            name=row["employee_name"],
            weekly_off_days=frozenset(
                {weekday_numbers[off_names[row["employee_id"]]]}
            ),
            skills=frozenset(skill_names.get(row["employee_id"], set())),
        )
        for row in org_employees
    }
    # Use the pod recorded on each synthetic employee row as the resource assignment.
    employee_pods = frozenset(
        (row["employee_id"], row["pod_id"])
        for row in org_employees
        if row["pod_id"] in assigned_pod_ids
    )
    synthetic = ScheduleData(
        organization_id=org_id,
        brands={
            brand_row["brand_id"]: Brand(
                brand_row["brand_id"], org_id, brand_row["brand_name"]
            )
        },
        processes=process_map,
        pods=pod_map,
        employees=employee_map,
        shifts=shift_map,
        employee_pods=employee_pods,
    )
    report = generate_monthly_roster(synthetic, 2026, 11)
    assert report.valid
    assert report.statistics["required_positions"] > 0
    assert report.statistics["unfilled_positions"] == 0
