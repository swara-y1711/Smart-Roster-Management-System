import os
import sys
from datetime import date, time
from pathlib import Path

backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from services.scheduling import (
    Assignment,
    Brand,
    Employee,
    Pod,
    Process,
    ScheduleData,
    Shift,
    generate_monthly_roster,
    validate_roster,
)


def test_generated_and_validated_reports_share_required_total_and_unfilled_formula():
    data = ScheduleData(
        organization_id="org",
        brands={"brand": Brand("brand", "org", "Brand")},
        processes={"process": Process("process", "brand", "Process")},
        pods={"pod": Pod("pod", "process", "Pod")},
        employees={"employee": Employee("employee", "org", "Employee")},
        shifts={"shift": Shift("shift", "pod", "Shift", time(9), time(17), 1)},
        employee_pods=frozenset({("employee", "pod")}),
    )
    generated = generate_monthly_roster(data, 2026, 11)
    validated = validate_roster(data, list(generated.assignments), date(2026, 11, 1), date(2026, 11, 30))

    assert generated.statistics["required_positions"] == validated.statistics["required_positions"]
    assert validated.statistics["unfilled_positions"] == max(
        0,
        validated.statistics["required_positions"] - validated.statistics["filled_positions"],
    )


def test_empty_saved_roster_has_no_assignments_to_count():
    data = ScheduleData(
        organization_id="org",
        brands={"brand": Brand("brand", "org", "Brand")},
        processes={"process": Process("process", "brand", "Process")},
        pods={"pod": Pod("pod", "process", "Pod")},
        employees={},
        shifts={"shift": Shift("shift", "pod", "Shift", time(9), time(17), 1)},
        employee_pods=frozenset(),
    )
    report = validate_roster(data, [], date(2026, 11, 1), date(2026, 11, 30))

    assert report.statistics["filled_positions"] == 0
    assert report.statistics["required_positions"] == 30

