"""Build the deterministic Faker workforce used by the sample-data importer."""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from faker import Faker
except ImportError:  # pragma: no cover - the fallback keeps dry-run tooling usable
    Faker = None  # type: ignore[assignment,misc]


SEED = 20261106
DATA_DIR = Path(__file__).resolve().parents[2] / "rosteriq_synthetic_data"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _base_data() -> dict[str, list[dict[str, str]]]:
    names = (
        "organizations",
        "brands",
        "processes",
        "pods",
        "shifts",
        "employees",
        "employee_skills",
        "employee_availability",
    )
    return {name: _read_csv(DATA_DIR / f"{name}.csv") for name in names}


def _new_person(fake: Any, index: int, organization_id: str, pod_id: str) -> dict[str, str]:
    if fake is not None:
        full_name = fake.name()
        email = fake.unique.email()
        phone = fake.phone_number()
    else:
        full_name = f"Sample Employee {index:03d}"
        email = f"sample.employee{index:03d}@example.com"
        phone = f"+1-555-010-{index:03d}"
    return {
        "employee_id": str(index),
        "employee_code": f"EMP{index:03d}",
        "employee_name": full_name,
        "email": email,
        "phone": phone,
        "organization_id": organization_id,
        "pod_id": pod_id,
        "designation": "Operations Associate",
        "is_pod_lead": "False",
    }


def build_seed_data() -> dict[str, list[dict[str, str]]]:
    """Return a stable, database-shaped sample dataset without writing files."""
    data = _base_data()
    fake = None
    if Faker is not None:
        fake = Faker()
        fake.seed_instance(SEED)
    rng = random.Random(SEED)

    process_org: dict[str, str] = {}
    brand_org = {row["brand_id"]: row["organization_id"] for row in data["brands"]}
    process_brand: dict[str, str] = {}
    for row in data["processes"]:
        process_org[row["process_id"]] = row["organization_id"]
        candidates = [
            brand["brand_id"]
            for brand in data["brands"]
            if brand["organization_id"] == row["organization_id"]
        ]
        process_brand[row["process_id"]] = sorted(candidates)[0]

    pod_org: dict[str, str] = {}
    pods_by_org: dict[str, list[str]] = defaultdict(list)
    for row in data["pods"]:
        organization_id = process_org[row["process_id"]]
        pod_org[row["pod_id"]] = organization_id
        pods_by_org[organization_id].append(row["pod_id"])
    for pods in pods_by_org.values():
        pods.sort(key=int)

    employees = [dict(row) for row in data["employees"]]
    employee_pods: list[dict[str, str]] = [
        {
            "employee_id": row["employee_id"],
            "pod_id": row["pod_id"],
            "is_primary": row["is_pod_lead"],
        }
        for row in employees
    ]
    links_by_pod: Counter[str] = Counter(row["pod_id"] for row in employee_pods)
    employees_by_org: dict[str, list[str]] = defaultdict(list)
    for row in employees:
        employees_by_org[row["organization_id"]].append(row["employee_id"])

    # Preserve all existing employee identities and add exactly three employees
    # per source organization. New employees start on the least-covered pod.
    for index in range(36, 51):
        organization_id = str(((index - 36) % len(pods_by_org)) + 1)
        primary_pod = min(
            pods_by_org[organization_id],
            key=lambda pod_id: (links_by_pod[pod_id], int(pod_id)),
        )
        employee = _new_person(fake, index, organization_id, primary_pod)
        employees.append(employee)
        employees_by_org[organization_id].append(employee["employee_id"])
        employee_pods.append({
            "employee_id": employee["employee_id"],
            "pod_id": primary_pod,
            "is_primary": "False",
        })
        links_by_pod[primary_pod] += 1

    # Add secondary eligibility links until every pod has at least two resources.
    for organization_id, pod_ids in sorted(pods_by_org.items()):
        candidates = employees_by_org[organization_id]
        cursor = 0
        while any(links_by_pod[pod_id] < 2 for pod_id in pod_ids):
            pod_id = min(
                (pod_id for pod_id in pod_ids if links_by_pod[pod_id] < 2),
                key=lambda item: (links_by_pod[item], int(item)),
            )
            employee_id = candidates[cursor % len(candidates)]
            cursor += 1
            if any(
                row["employee_id"] == employee_id and row["pod_id"] == pod_id
                for row in employee_pods
            ):
                continue
            employee_pods.append({
                "employee_id": employee_id,
                "pod_id": pod_id,
                "is_primary": "False",
            })
            links_by_pod[pod_id] += 1

    if len(employees) != 50 or min(links_by_pod.values()) < 2:
        raise AssertionError("The deterministic seed must contain 50 employees and two resources per pod.")

    existing_skills = [dict(row) for row in data["employee_skills"] if int(row["employee_id"]) <= 35]
    skill_names = ("Customer Support", "Sales", "Logistics", "Order Management")
    for employee in employees:
        if int(employee["employee_id"]) <= 35:
            continue
        count = 1 + rng.randrange(2)
        for skill_name in rng.sample(skill_names, count):
            existing_skills.append({
                "employee_id": employee["employee_id"],
                "skill_name": skill_name,
            })

    availability = [dict(row) for row in data["employee_availability"] if int(row["employee_id"]) <= 35]
    weekdays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
    for employee in employees:
        if int(employee["employee_id"]) <= 35:
            continue
        availability.append({
            "employee_id": employee["employee_id"],
            "weekly_off": weekdays[(int(employee["employee_id"]) - 36) % len(weekdays)],
            "availability_status": "Available",
        })

    # One global shift definition is assigned to every pod. The importer turns
    # this map into pod-scoped shift rows, so all 40 pods have an active shift
    # while headcount remains the existing default of one.
    pod_shifts = [
        {"pod_id": row["pod_id"], "shift_id": str(((int(row["pod_id"]) - 1) % 3) + 1)}
        for row in sorted(data["pods"], key=lambda item: int(item["pod_id"]))
    ]
    shift_by_pod = {row["pod_id"]: row["shift_id"] for row in pod_shifts}
    assignments = []
    for employee in employees:
        pod = employee["pod_id"]
        process_id = next(row["process_id"] for row in data["pods"] if row["pod_id"] == pod)
        assignments.append({
            "employee_id": employee["employee_id"],
            "brand_id": process_brand[process_id],
            "process_id": process_id,
            "shift_id": shift_by_pod[pod],
            "roster_date": "2026-11-09",
            "status": "Assigned",
        })

    return {
        **data,
        "employees": employees,
        "employee_pod_assignments": employee_pods,
        "employee_skills": existing_skills,
        "employee_availability": availability,
        "pod_shifts": pod_shifts,
        "roster_assignments": assignments,
    }

