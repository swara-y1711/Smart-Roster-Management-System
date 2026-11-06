import os
import sys

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from faker_seed import build_seed_data
from import_faker_data import build_import_plan


def test_deterministic_seed_has_fifty_employees_and_two_resources_per_pod():
    first = build_seed_data()
    second = build_seed_data()

    assert first == second
    assert len(first["employees"]) == 50
    assert len(first["pod_shifts"]) == 40
    eligibility_counts = {
        pod_id: sum(row["pod_id"] == pod_id for row in first["employee_pod_assignments"])
        for pod_id in {row["pod_id"] for row in first["pods"]}
    }
    assert len(eligibility_counts) == 40
    assert min(eligibility_counts.values()) >= 2


def test_seed_import_plan_has_one_active_shift_per_pod_and_stable_totals():
    plan = build_import_plan(build_seed_data())

    assert len(plan.tables["employees"]) == 50
    assert len(plan.tables["employee_pods"]) >= 80
    assert len(plan.tables["shifts"]) == 40
    assert len(plan.tables["roster_assignments"]) == 50
    assert len(plan.obsolete_shift_ids) == 80

