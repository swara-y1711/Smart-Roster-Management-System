import csv
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/sample-workforce", tags=["Sample Workforce"])

DATA_DIR = Path(__file__).resolve().parents[3] / "rosteriq_synthetic_data"


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"The default workforce dataset is missing {name}.",
        )
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def load_sample_workforce() -> dict[str, list[dict[str, object]]]:
    organizations = _read_csv("organizations.csv")
    if not organizations:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The default workforce dataset contains no records.",
        )

    organization_id = organizations[0]["organization_id"]
    brands = [
        {
            "id": row["brand_id"],
            "organization_id": row["organization_id"],
            "name": row["brand_name"],
            "industry": row["category"],
        }
        for row in _read_csv("brands.csv")
        if row["organization_id"] == organization_id
    ]
    brand_ids = {str(brand["id"]) for brand in brands}
    processes_source = [
        row for row in _read_csv("processes.csv")
        if row["organization_id"] == organization_id
    ]
    employees_source = [
        row for row in _read_csv("employees.csv")
        if row["organization_id"] == organization_id
    ]
    employee_ids = {row["employee_id"] for row in employees_source}
    assignments_source = [
        row for row in _read_csv("roster_assignments.csv")
        if row["employee_id"] in employee_ids and row["brand_id"] in brand_ids
    ]
    process_brands: dict[str, Counter[str]] = {}
    for row in assignments_source:
        process_brands.setdefault(row["process_id"], Counter())[row["brand_id"]] += 1

    default_brand_id = str(brands[0]["id"]) if brands else ""
    processes = [
        {
            "id": row["process_id"],
            "brand_id": process_brands.get(row["process_id"], Counter()).most_common(1)[0][0]
            if process_brands.get(row["process_id"])
            else default_brand_id,
            "name": row["process_name"],
        }
        for row in processes_source
    ]
    process_ids = {str(process["id"]) for process in processes}
    pods = [
        {
            "id": row["pod_id"],
            "process_id": row["process_id"],
            "name": row["pod_name"],
        }
        for row in _read_csv("pods.csv")
        if row["process_id"] in process_ids
    ]
    pod_ids = {str(pod["id"]) for pod in pods}

    employees = []
    employee_pods = []
    for row in employees_source:
        first_name, _, last_name = row["employee_name"].partition(" ")
        employees.append({
            "id": row["employee_id"],
            "organization_id": row["organization_id"],
            "employee_code": row["employee_code"],
            "first_name": first_name,
            "last_name": last_name,
            "email": row["email"],
            "designation": row["designation"],
        })
        if row["pod_id"] in pod_ids:
            employee_pods.append({
                "employee_id": row["employee_id"],
                "pod_id": row["pod_id"],
                "is_primary": row["is_pod_lead"].lower() == "true",
            })

    assignments = [
        {
            "employee_id": row["employee_id"],
            "shift_id": row["shift_id"],
            "assignment_date": row["roster_date"],
            "status": row["status"].lower(),
        }
        for row in assignments_source
    ]

    return {
        "brands": brands,
        "processes": processes,
        "pods": pods,
        "employees": employees,
        "employeePods": employee_pods,
        "shifts": [],
        "assignments": assignments,
    }


@router.get("", summary="Get the default sample workforce dataset")
def get_sample_workforce(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, list[dict[str, object]]]:
    """Return read-only demo records from the existing Faker-generated CSV files."""
    return load_sample_workforce()
