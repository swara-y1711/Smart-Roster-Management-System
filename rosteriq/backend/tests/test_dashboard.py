import os
import sys
from uuid import uuid4

from fastapi.testclient import TestClient

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.auth import AuthenticatedUser, get_current_user, get_db
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, columns):
        assert columns == "*"
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return FakeQuery(self.rows[name])


def test_dashboard_returns_all_visible_employees_without_relationship_filters():
    rows = {
        "organizations": [],
        "brands": [],
        "processes": [],
        "pods": [],
        "employees": [{"id": str(index)} for index in range(35)],
        "employee_pods": [],
        "employee_skills": [],
        "employee_availability": [],
        "shifts": [],
        "roster_assignments": [],
    }
    app.dependency_overrides[get_db] = lambda: FakeDatabase(rows)
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=uuid4())
    try:
        response = TestClient(app).get("/dashboard")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()["employees"]) == 35


def test_two_authenticated_users_receive_the_same_employee_count():
    rows = {
        "organizations": [{"id": "shared-org"}],
        "brands": [{"id": "brand-1"}],
        "processes": [{"id": "process-1"}],
        "pods": [{"id": "pod-1"}],
        "employees": [{"id": str(index)} for index in range(35)],
        "employee_pods": [],
        "employee_skills": [],
        "employee_availability": [],
        "shifts": [],
        "roster_assignments": [],
    }
    counts = []
    try:
        for _ in range(2):
            app.dependency_overrides[get_db] = lambda: FakeDatabase(rows)
            app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=uuid4())
            response = TestClient(app).get("/dashboard")
            assert response.status_code == 200
            counts.append(len(response.json()["employees"]))
    finally:
        app.dependency_overrides.clear()

    assert counts == [35, 35]
