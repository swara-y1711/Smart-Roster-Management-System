import os
import sys

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from import_faker_data import _source_uuid, build_import_plan, load_csv_data


def test_faker_dataset_maps_all_rows_to_existing_schema_and_stable_ids():
    data = load_csv_data()
    first_plan = build_import_plan(data)
    second_plan = build_import_plan(data)

    assert {table: len(rows) for table, rows in first_plan.tables.items()} == {
        "organizations": 5,
        "brands": 10,
        "processes": 20,
        "pods": 40,
        "employees": 35,
        "employee_pods": 35,
        "employee_skills": 75,
        "employee_availability": 245,
        "shifts": 31,
        "roster_assignments": 35,
    }
    assert len(first_plan.obsolete_shift_ids) == 89
    assert first_plan.tables == second_plan.tables
    assert first_plan.tables["employees"][0][0] == _source_uuid(
        "employees", data["employees"][0]["employee_id"]
    )
    assert _source_uuid("employees", "1") != _source_uuid("organizations", "1")
    assert first_plan.diagnostics["roster_process_disagrees_with_employee_pod"] == 26
    assert first_plan.diagnostics["employee_pod_organization_mismatches"] == 0

    employee_ids = {row[0] for row in first_plan.tables["employees"]}
    assert all(row[1] in employee_ids for row in first_plan.tables["employee_skills"])
    assert all(row[1] in employee_ids for row in first_plan.tables["employee_availability"])
    assert all(row[0] in employee_ids for row in first_plan.tables["employee_pods"])
    shift_ids = {row[0] for row in first_plan.tables["shifts"]}
    assert all(row[2] in shift_ids for row in first_plan.tables["roster_assignments"])
