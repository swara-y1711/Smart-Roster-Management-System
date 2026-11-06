import sys
from datetime import date, time
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

backend_root = str(Path(__file__).resolve().parents[1])
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from models.scheduling import OperatingOverrideUpdate, PublicHolidayUpdate
from models.schemas import RosterAssignmentCreate, RosterAssignmentProposal
from routers import roster_assignments
from services.scheduling import Brand, Employee, Pod, Process, ScheduleData, Shift


ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
EMPLOYEE_ID = UUID("00000000-0000-0000-0000-000000000002")
SHIFT_ID = UUID("00000000-0000-0000-0000-000000000003")


class Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def in_(self, *_args):
        return self

    def gte(self, *_args):
        return self

    def lte(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeDatabase:
    def table(self, name):
        if name == "employees":
            return Query([{"id": str(EMPLOYEE_ID)}])
        if name == "roster_assignments":
            return Query([])
        raise AssertionError(f"Unexpected table: {name}")


def schedule_data():
    org_id = str(ORG_ID)
    employee_id = str(EMPLOYEE_ID)
    shift_id = str(SHIFT_ID)
    return ScheduleData(
        organization_id=org_id,
        brands={"brand": Brand("brand", org_id, "Brand")},
        processes={"process": Process("process", "brand", "Process")},
        pods={"pod": Pod("pod", "process", "Pod")},
        employees={
            employee_id: Employee(
                employee_id,
                org_id,
                "Employee",
                weekly_off_days=frozenset({0}),
            )
        },
        shifts={shift_id: Shift(shift_id, "pod", "Shift", time(9), time(17))},
        employee_pods=frozenset({(employee_id, "pod")}),
    )


def test_direct_roster_write_rejects_mandatory_constraint_violation(monkeypatch):
    monkeypatch.setattr(roster_assignments, "load_schedule_data", lambda *_args: schedule_data())
    monkeypatch.setattr(roster_assignments, "_report_response", lambda *_args: {"valid": False})

    with pytest.raises(HTTPException) as error:
        roster_assignments._validate_month_roster(
            FakeDatabase(),
            ORG_ID,
            date(2026, 11, 1),
            date(2026, 11, 30),
            replacement={
                "employee_id": str(EMPLOYEE_ID),
                "shift_id": str(SHIFT_ID),
                "assignment_date": "2026-11-02",
            },
        )

    assert error.value.status_code == 422
    assert error.value.detail["validation"]["valid"] is False


def test_direct_roster_write_accepts_valid_assignment(monkeypatch):
    monkeypatch.setattr(roster_assignments, "load_schedule_data", lambda *_args: schedule_data())
    assignment = {
        "employee_id": str(EMPLOYEE_ID),
        "shift_id": str(SHIFT_ID),
        "assignment_date": "2026-11-03",
    }

    roster_assignments._validate_month_roster(
        FakeDatabase(),
        ORG_ID,
        date(2026, 11, 1),
        date(2026, 11, 30),
        replacement=assignment,
    )


def test_roster_crud_cannot_publish_without_publish_endpoint():
    payload = RosterAssignmentCreate(
        employee_id=EMPLOYEE_ID,
        shift_id=SHIFT_ID,
        assignment_date=date(2026, 11, 3),
        status="published",
    )
    with pytest.raises(HTTPException) as error:
        roster_assignments.create_roster_assignment(payload, db=FakeDatabase())
    assert error.value.status_code == 422


def test_validated_batch_cannot_publish_without_publish_endpoint():
    from models.schemas import RosterAssignmentBatchSave

    payload = RosterAssignmentBatchSave(
        organization_id=ORG_ID,
        year=2026,
        month=11,
        status="published",
        assignments=[
            RosterAssignmentProposal(
                employee_id=EMPLOYEE_ID,
                shift_id=SHIFT_ID,
                assignment_date=date(2026, 11, 3),
            )
        ],
    )
    with pytest.raises(HTTPException) as error:
        roster_assignments.validate_and_save_roster(payload, db=FakeDatabase())
    assert error.value.status_code == 422


def test_update_models_support_editable_override_fields():
    override = OperatingOverrideUpdate(operating_date=date(2026, 12, 25))
    holiday = PublicHolidayUpdate(holiday_date=date(2026, 12, 25), name="Christmas")
    assert override.operating_date == date(2026, 12, 25)
    assert holiday.name == "Christmas"


def test_update_models_reject_empty_edits():
    with pytest.raises(ValueError):
        OperatingOverrideUpdate()
    with pytest.raises(ValueError):
        PublicHolidayUpdate()
