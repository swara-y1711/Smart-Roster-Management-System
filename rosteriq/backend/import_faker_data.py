import argparse
import calendar
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg

from app.config import DATABASE_URL

DATA_DIR = Path(__file__).resolve().parents[2] / "rosteriq_synthetic_data"
CSV_FILES = {
    "organizations": "organizations.csv",
    "brands": "brands.csv",
    "processes": "processes.csv",
    "pods": "pods.csv",
    "employees": "employees.csv",
    "employee_skills": "employee_skills.csv",
    "employee_availability": "employee_availability.csv",
    "shifts": "shifts.csv",
    "roster_assignments": "roster_assignments.csv",
}


@dataclass
class ImportPlan:
    tables: dict[str, list[tuple[Any, ...]]]
    diagnostics: dict[str, int]
    obsolete_shift_ids: list[UUID]


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required Faker dataset file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _source_uuid(table: str, source_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"rosteriq-faker:{table}:{source_id}")


def load_csv_data() -> dict[str, list[dict[str, str]]]:
    return {table: _read_csv(filename) for table, filename in CSV_FILES.items()}


def build_import_plan(data: dict[str, list[dict[str, str]]]) -> ImportPlan:
    organizations = data["organizations"]
    brands = data["brands"]
    processes = data["processes"]
    pods = data["pods"]
    employees = data["employees"]
    skills = data["employee_skills"]
    availability = data["employee_availability"]
    shifts = data["shifts"]
    assignments = data["roster_assignments"]
    employee_pod_assignments = data.get("employee_pod_assignments")
    pod_shifts = data.get("pod_shifts")

    def keyed(rows: list[dict[str, str]], key: str, label: str) -> dict[str, dict[str, str]]:
        result = {row[key]: row for row in rows}
        if len(result) != len(rows):
            raise ValueError(f"{label} contains duplicate {key} values.")
        return result

    organization_by_id = keyed(organizations, "organization_id", "organizations")
    brand_by_id = keyed(brands, "brand_id", "brands")
    process_by_id = keyed(processes, "process_id", "processes")
    pod_by_id = keyed(pods, "pod_id", "pods")
    employee_by_id = keyed(employees, "employee_id", "employees")
    shift_by_id = keyed(shifts, "shift_id", "shifts")

    def require_reference(value: str, values: dict[str, Any], label: str) -> None:
        if value not in values:
            raise ValueError(f"Invalid CSV relationship: {label} references {value!r}.")

    for row in brands:
        require_reference(row["organization_id"], organization_by_id, "brand.organization_id")
    for row in processes:
        require_reference(row["organization_id"], organization_by_id, "process.organization_id")
    for row in pods:
        require_reference(row["process_id"], process_by_id, "pod.process_id")
    for row in employees:
        require_reference(row["organization_id"], organization_by_id, "employee.organization_id")
        require_reference(row["pod_id"], pod_by_id, "employee.pod_id")
        process_id = pod_by_id[row["pod_id"]]["process_id"]
        require_reference(process_id, process_by_id, "employee.pod_id.process_id")
        if process_by_id[process_id]["organization_id"] != row["organization_id"]:
            raise ValueError(f"Employee {row['employee_id']} and its pod belong to different organizations.")
    if employee_pod_assignments is not None:
        for row in employee_pod_assignments:
            require_reference(row["employee_id"], employee_by_id, "employee_pod_assignments.employee_id")
            require_reference(row["pod_id"], pod_by_id, "employee_pod_assignments.pod_id")
            if (
                process_by_id[pod_by_id[row["pod_id"]]["process_id"]]["organization_id"]
                != employee_by_id[row["employee_id"]]["organization_id"]
            ):
                raise ValueError("An employee pod assignment crosses organization boundaries.")
    for row in skills:
        require_reference(row["employee_id"], employee_by_id, "employee_skills.employee_id")
    availability_by_employee = keyed(availability, "employee_id", "employee_availability")
    if set(availability_by_employee) != set(employee_by_id):
        raise ValueError("employee_availability must contain exactly one row for every employee.")
    for row in assignments:
        require_reference(row["employee_id"], employee_by_id, "roster_assignments.employee_id")
        require_reference(row["brand_id"], brand_by_id, "roster_assignments.brand_id")
        require_reference(row["process_id"], process_by_id, "roster_assignments.process_id")
        require_reference(row["shift_id"], shift_by_id, "roster_assignments.shift_id")
        if (
            brand_by_id[row["brand_id"]]["organization_id"]
            != process_by_id[row["process_id"]]["organization_id"]
        ):
            raise ValueError("A roster assignment references a brand and process from different organizations.")

    brands_by_organization: dict[str, list[str]] = defaultdict(list)
    for row in brands:
        brands_by_organization[row["organization_id"]].append(row["brand_id"])
    process_brand_votes: dict[str, Counter[str]] = defaultdict(Counter)
    for row in assignments:
        process_brand_votes[row["process_id"]][row["brand_id"]] += 1

    process_brand: dict[str, str] = {}
    ambiguous_process_brands = 0
    processes_without_brand_votes = 0
    for row in processes:
        candidates = brands_by_organization[row["organization_id"]]
        votes = process_brand_votes[row["process_id"]]
        if votes:
            highest_vote = max(votes.values())
            winners = sorted(brand_id for brand_id, count in votes.items() if count == highest_vote)
            process_brand[row["process_id"]] = winners[0]
            ambiguous_process_brands += len(votes) > 1
        else:
            processes_without_brand_votes += 1
            process_brand[row["process_id"]] = sorted(candidates)[0]

    employees_by_id = employee_by_id
    employee_pod_organization_mismatches = sum(
        process_by_id[pod_by_id[row["pod_id"]]["process_id"]]["organization_id"]
        != row["organization_id"]
        for row in employees
    )
    assignment_process_mismatches = 0
    for row in assignments:
        employee = employees_by_id[row["employee_id"]]
        employee_process_id = pod_by_id[employee["pod_id"]]["process_id"]
        assignment_process_mismatches += row["process_id"] != employee_process_id

    organization_rows = [
        (_source_uuid("organizations", row["organization_id"]), row["organization_name"])
        for row in organizations
    ]
    brand_rows = [
        (
            _source_uuid("brands", row["brand_id"]),
            _source_uuid("organizations", row["organization_id"]),
            row["brand_name"],
            row["category"],
        )
        for row in brands
    ]
    process_rows = [
        (
            _source_uuid("processes", row["process_id"]),
            _source_uuid("brands", process_brand[row["process_id"]]),
            row["process_name"],
        )
        for row in processes
    ]
    pod_rows = [
        (
            _source_uuid("pods", row["pod_id"]),
            _source_uuid("processes", row["process_id"]),
            row["pod_name"],
        )
        for row in pods
    ]

    employee_rows = []
    employee_pod_rows = []
    employee_database_ids: dict[str, UUID] = {}
    for row in employees:
        employee_id = _source_uuid("employees", row["employee_id"])
        pod_id = _source_uuid("pods", row["pod_id"])
        employee_database_ids[row["employee_id"]] = employee_id
        first_name, _, last_name = row["employee_name"].strip().partition(" ")
        if not first_name:
            raise ValueError(f"Employee {row['employee_id']} has no name.")
        employee_rows.append(
            (
                employee_id,
                _source_uuid("organizations", row["organization_id"]),
                row["employee_code"],
                first_name,
                last_name or None,
                row["email"],
                row["phone"] or None,
                row["designation"],
            )
        )
        employee_pod_rows.append(
            (employee_id, pod_id, row["is_pod_lead"].strip().lower() == "true")
        )

    if employee_pod_assignments is not None:
        employee_pod_rows = [
            (
                employee_database_ids[row["employee_id"]],
                _source_uuid("pods", row["pod_id"]),
                row.get("is_primary", "false").strip().lower() == "true",
            )
            for row in employee_pod_assignments
        ]

    skill_rows = [
        (
            _source_uuid("employee_skills", f"{row['employee_id']}:{row['skill_name']}"),
            employee_database_ids[row["employee_id"]],
            row["skill_name"],
        )
        for row in skills
    ]

    availability_rows = []
    for row in availability:
        day_name = row["weekly_off"].strip().title()
        if day_name not in calendar.day_name:
            raise ValueError(f"Unknown weekly-off day {row['weekly_off']!r}.")
        status_value = row["availability_status"].strip().lower()
        if status_value not in {"available", "unavailable"}:
            raise ValueError(f"Unknown availability status {row['availability_status']!r}.")
        weekly_off = list(calendar.day_name).index(day_name)
        employee_id = employee_database_ids[row["employee_id"]]
        for day_of_week in range(7):
            availability_rows.append(
                (
                    _source_uuid("employee_availability", f"{row['employee_id']}:{day_of_week}"),
                    employee_id,
                    day_of_week,
                    status_value == "available" and day_of_week != weekly_off,
                )
            )

    shift_pod_pairs = (
        {
            (row["shift_id"], row["pod_id"])
            for row in pod_shifts
        }
        if pod_shifts is not None
        else {
            (
                row["shift_id"],
                employee_by_id[row["employee_id"]]["pod_id"],
            )
            for row in assignments
        }
    )
    if pod_shifts is not None:
        for row in pod_shifts:
            require_reference(row["pod_id"], pod_by_id, "pod_shifts.pod_id")
            require_reference(row["shift_id"], shift_by_id, "pod_shifts.shift_id")
        if {row["pod_id"] for row in pod_shifts} != set(pod_by_id):
            raise ValueError("pod_shifts must contain exactly one active shift for every pod.")
    used_source_shifts = {shift_id for shift_id, _ in shift_pod_pairs}
    if used_source_shifts != set(shift_by_id):
        raise ValueError("Every CSV shift must be referenced by at least one roster assignment.")

    shift_rows = []
    shift_database_ids: dict[tuple[str, str], UUID] = {}
    for source_shift in shifts:
        try:
            start_time = datetime.strptime(source_shift["start_time"], "%H:%M").time()
            end_time = datetime.strptime(source_shift["end_time"], "%H:%M").time()
        except ValueError as error:
            raise ValueError(f"Invalid time in shift {source_shift['shift_id']}.") from error
        for source_shift_id, pod_id in sorted(shift_pod_pairs):
            if source_shift_id != source_shift["shift_id"]:
                continue
            database_shift_id = _source_uuid(
                "shifts", f"{source_shift['shift_id']}:{pod_id}"
            )
            shift_database_ids[(source_shift["shift_id"], pod_id)] = database_shift_id
            shift_rows.append(
                (
                    database_shift_id,
                    _source_uuid("pods", pod_id),
                    source_shift["shift_name"],
                    start_time,
                    end_time,
                )
            )
    desired_shift_ids = {row[0] for row in shift_rows}
    obsolete_shift_ids = [
        _source_uuid("shifts", f"{shift['shift_id']}:{pod['pod_id']}")
        for shift in shifts
        for pod in pods
        if _source_uuid("shifts", f"{shift['shift_id']}:{pod['pod_id']}")
        not in desired_shift_ids
    ]

    assignment_rows = []
    for row in assignments:
        employee = employees_by_id[row["employee_id"]]
        pod_id = employee["pod_id"]
        # The existing schema links assignments to a pod-scoped shift, so the
        # employee's declared pod is the canonical source for this association.
        shift_id = shift_database_ids[(row["shift_id"], pod_id)]
        status_value = row["status"].strip().lower()
        if status_value == "assigned":
            status_value = "scheduled"
        if status_value not in {"scheduled", "completed", "cancelled", "published"}:
            raise ValueError(f"Unknown roster assignment status {row['status']!r}.")
        assignment_date = date.fromisoformat(row["roster_date"])
        assignment_rows.append(
            (
                _source_uuid(
                    "roster_assignments",
                    f"{row['employee_id']}:{row['shift_id']}:{row['roster_date']}",
                ),
                employee_database_ids[row["employee_id"]],
                shift_id,
                assignment_date,
                status_value,
            )
        )

    expected_table_rows = {
        "organizations": len(organization_rows),
        "brands": len(brand_rows),
        "processes": len(process_rows),
        "pods": len(pod_rows),
        "employees": len(employee_rows),
        "employee_skills": len(skill_rows),
        "employee_availability": len(availability_rows),
        "shifts": len(shift_rows),
        "roster_assignments": len(assignment_rows),
        "employee_pods": len(employee_pod_rows),
    }
    return ImportPlan(
        tables={
            "organizations": organization_rows,
            "brands": brand_rows,
            "processes": process_rows,
            "pods": pod_rows,
            "employees": employee_rows,
            "employee_pods": employee_pod_rows,
            "employee_skills": skill_rows,
            "employee_availability": availability_rows,
            "shifts": shift_rows,
            "roster_assignments": assignment_rows,
        },
        diagnostics={
            "ambiguous_process_brand_relationships": ambiguous_process_brands,
            "processes_without_brand_votes": processes_without_brand_votes,
            "roster_process_disagrees_with_employee_pod": assignment_process_mismatches,
            "employee_pod_organization_mismatches": employee_pod_organization_mismatches,
            **{f"planned_{table}": count for table, count in expected_table_rows.items()},
        },
        obsolete_shift_ids=obsolete_shift_ids,
    )


UPSERTS = {
    "organizations": """
        INSERT INTO public.organizations (id, name) VALUES (%s, %s)
        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
    """,
    "brands": """
        INSERT INTO public.brands (id, organization_id, name, industry)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            organization_id = EXCLUDED.organization_id,
            name = EXCLUDED.name,
            industry = EXCLUDED.industry
    """,
    "processes": """
        INSERT INTO public.processes (id, brand_id, name)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            brand_id = EXCLUDED.brand_id,
            name = EXCLUDED.name
    """,
    "pods": """
        INSERT INTO public.pods (id, process_id, name)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            process_id = EXCLUDED.process_id,
            name = EXCLUDED.name
    """,
    "employees": """
        INSERT INTO public.employees
            (id, organization_id, employee_code, first_name, last_name, email, phone, designation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            organization_id = EXCLUDED.organization_id,
            employee_code = EXCLUDED.employee_code,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            designation = EXCLUDED.designation
    """,
    "employee_pods": """
        INSERT INTO public.employee_pods (employee_id, pod_id, is_primary)
        VALUES (%s, %s, %s)
        ON CONFLICT (employee_id, pod_id) DO UPDATE SET is_primary = EXCLUDED.is_primary
    """,
    "employee_skills": """
        INSERT INTO public.employee_skills (id, employee_id, skill_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            skill_name = EXCLUDED.skill_name
    """,
    "employee_availability": """
        INSERT INTO public.employee_availability (id, employee_id, day_of_week, is_available)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            day_of_week = EXCLUDED.day_of_week,
            is_available = EXCLUDED.is_available
    """,
    "shifts": """
        INSERT INTO public.shifts (id, pod_id, shift_name, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            pod_id = EXCLUDED.pod_id,
            shift_name = EXCLUDED.shift_name,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time
    """,
    "roster_assignments": """
        INSERT INTO public.roster_assignments (id, employee_id, shift_id, assignment_date, status)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            employee_id = EXCLUDED.employee_id,
            shift_id = EXCLUDED.shift_id,
            assignment_date = EXCLUDED.assignment_date,
            status = EXCLUDED.status
    """,
}


def _wipe_sample_rows(cursor: Any, plan: ImportPlan) -> None:
    """Delete only rows owned by this deterministic sample dataset."""
    employee_ids = [row[0] for row in plan.tables["employees"]]
    shift_ids = [row[0] for row in plan.tables["shifts"]] + plan.obsolete_shift_ids
    cursor.execute(
        "DELETE FROM public.roster_assignments WHERE employee_id = ANY(%s) OR shift_id = ANY(%s)",
        (employee_ids, shift_ids),
    )
    for table in ("employee_availability", "employee_skills", "employee_pods"):
        cursor.execute(
            f'DELETE FROM public."{table}" WHERE employee_id = ANY(%s)',
            (employee_ids,),
        )
    cursor.execute(
        "DELETE FROM public.shifts WHERE id = ANY(%s)",
        (shift_ids,),
    )
    cursor.execute(
        "DELETE FROM public.employees WHERE id = ANY(%s)",
        (employee_ids,),
    )


def import_plan(plan: ImportPlan, manager_id: UUID, apply: bool, wipe: bool = False) -> dict[str, int]:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    table_order = (
        "organizations",
        "brands",
        "processes",
        "pods",
        "employees",
        "employee_pods",
        "employee_skills",
        "employee_availability",
        "shifts",
        "roster_assignments",
    )
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM public.manager_profiles WHERE id = %s",
                (manager_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("The supplied manager ID does not exist in manager_profiles.")
            if not apply:
                return {}

            with connection.transaction():
                if wipe:
                    _wipe_sample_rows(cursor, plan)
                for table in table_order:
                    if table == "employee_pods":
                        continue
                    if table == "brands":
                        for row in plan.tables["organizations"]:
                            cursor.execute(
                                """
                                INSERT INTO public.organization_members (organization_id, manager_id)
                                VALUES (%s, %s)
                                ON CONFLICT (organization_id, manager_id) DO NOTHING
                                """,
                                (row[0], manager_id),
                            )
                    cursor.executemany(UPSERTS[table], plan.tables[table])
                cursor.executemany(UPSERTS["employee_pods"], plan.tables["employee_pods"])

                if plan.obsolete_shift_ids:
                    cursor.execute(
                        """
                        DELETE FROM public.shifts AS shift
                        WHERE shift.id = ANY(%s)
                          AND NOT EXISTS (
                              SELECT 1
                              FROM public.roster_assignments AS assignment
                              WHERE assignment.shift_id = shift.id
                          )
                        """,
                        (plan.obsolete_shift_ids,),
                    )
                    cursor.execute(
                        "SELECT count(*) FROM public.shifts WHERE id = ANY(%s)",
                        (plan.obsolete_shift_ids,),
                    )
                    if cursor.fetchone()[0]:
                        raise RuntimeError("Unused imported shifts are still referenced by roster assignments.")

                actual_counts = {}
                for table in table_order:
                    if table == "employee_pods":
                        cursor.execute(
                            """
                            SELECT count(*)
                            FROM public.employee_pods
                            WHERE employee_id = ANY(%s)
                            """,
                            ([row[0] for row in plan.tables["employee_pods"]],),
                        )
                    else:
                        cursor.execute(
                            f'SELECT count(*) FROM public."{table}" WHERE id = ANY(%s)',
                            ([row[0] for row in plan.tables[table]],),
                        )
                    actual_counts[table] = cursor.fetchone()[0]
                    expected = len(plan.tables[table])
                    if actual_counts[table] != expected:
                        raise RuntimeError(
                            f"Post-import verification failed for {table}: "
                            f"expected {expected}, found {actual_counts[table]}."
                        )

                cursor.execute(
                    """
                    SELECT count(*)
                    FROM public.organization_members
                    WHERE organization_id = ANY(%s) AND manager_id = %s
                    """,
                    ([row[0] for row in plan.tables["organizations"]], manager_id),
                )
                if cursor.fetchone()[0] != len(plan.tables["organizations"]):
                    raise RuntimeError("Post-import verification failed for manager workspace access.")
    return actual_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the repository's Faker workforce CSVs.")
    parser.add_argument("--manager-id", required=True, type=UUID, help="Existing manager_profiles.id.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the idempotent import. Without this flag, only validate and report the plan.",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete rows owned by this deterministic sample dataset before importing.",
    )
    args = parser.parse_args()

    plan = build_import_plan(load_csv_data())
    print("Planned database rows:")
    for table, rows in plan.tables.items():
        print(f"  {table}: {len(rows)}")
    print("Source relationship diagnostics:")
    for key, value in plan.diagnostics.items():
        if key.startswith("planned_"):
            continue
        print(f"  {key}: {value}")

    if args.wipe and not args.apply:
        parser.error("--wipe requires --apply")
    counts = import_plan(plan, args.manager_id, args.apply, wipe=args.wipe)
    if not args.apply:
        print("Dry run only. Re-run with --apply to import these rows.")
        return
    print("Verified imported rows:")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
