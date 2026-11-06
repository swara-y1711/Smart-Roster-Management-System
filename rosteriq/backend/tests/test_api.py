import os
import sys
import uuid
from datetime import date
import pytest
import psycopg
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from main import app
from database import get_supabase_client, DATABASE_URL

client = TestClient(app)


def _create_test_workspace(manager_id: str, name: str) -> str:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.organizations (name) VALUES (%s) RETURNING id;",
                (name,),
            )
            organization_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO public.organization_members (organization_id, manager_id)
                VALUES (%s, %s);
                """,
                (organization_id, manager_id),
            )
        conn.commit()
    return str(organization_id)


def _delete_test_workspace(organization_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.organizations WHERE id = %s;",
                (organization_id,),
            )
        conn.commit()


# Helper for test user management
TEST_USER_A_EMAIL = f"test_mgr_a_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_B_EMAIL = f"test_mgr_b_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"

@pytest.fixture(scope="session")
def auth_tokens():
    """Sets up test managers and an internal workspace for access-isolation tests."""
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required to provision test manager profiles.")

    supabase = get_supabase_client()
    created_user_ids = []
    tokens = {}

    for email, label in [
        (TEST_USER_A_EMAIL, "user_a"),
        (TEST_USER_B_EMAIL, "user_b")
    ]:
        emp_id = f"MGR-{uuid.uuid4().hex[:6].upper()}"
        res = supabase.auth.sign_up({
            "email": email,
            "password": TEST_USER_PASSWORD,
            "options": {
                "data": {
                    "full_name": f"Manager {label}",
                    "employee_id": emp_id
                }
            }
        })
        user_id = res.user.id
        token = res.session.access_token
        created_user_ids.append(user_id)
        tokens[label] = {
            "user_id": user_id,
            "employee_id": emp_id,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"}
        }

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.manager_profiles
                        (id, full_name, work_email, employee_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        work_email = EXCLUDED.work_email,
                        employee_id = EXCLUDED.employee_id;
                    """,
                    (user_id, f"Manager {label}", email, emp_id),
                )
            conn.commit()

    yield tokens

    # Teardown: Clean up test users from auth.users
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    for uid in created_user_ids:
                        cur.execute(
                            """
                            DELETE FROM public.organizations
                            WHERE id IN (
                                SELECT organization_id
                                FROM public.organization_members
                                WHERE manager_id = %s
                            )
                            AND id <> (
                                SELECT value::uuid
                                FROM public.app_settings
                                WHERE key = 'rosteriq.shared_organization_id'
                            );
                            """,
                            (uid,),
                        )
                        cur.execute("DELETE FROM public.manager_profiles WHERE id = %s;", (uid,))
                        cur.execute("DELETE FROM auth.users WHERE id = %s;", (uid,))
                conn.commit()
        except Exception as e:
            print("Teardown cleanup exception:", e)


class TestPublicEndpoints:
    def test_root_endpoint(self):
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "RosterIQ API"
        assert data["status"] == "online"
        assert data["documentation"] == "/docs"

    def test_health_check(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data
        assert "timestamp" in data

    def test_openapi_docs_available(self):
        res = client.get("/openapi.json")
        assert res.status_code == 200
        data = res.json()
        assert "paths" in data
        assert "/organizations" in data["paths"]
        assert "/brands" in data["paths"]
        assert "/processes" in data["paths"]
        assert "/pods" in data["paths"]
        assert "/employees" in data["paths"]
        assert "/employee-skills" in data["paths"]
        assert "/employee-availability" in data["paths"]
        assert "/shifts" in data["paths"]
        assert "/roster-assignments" in data["paths"]
        assert "/scheduling/generate" in data["paths"]
        assert "/scheduling/validate" in data["paths"]
        assert "/scheduling/impact" in data["paths"]
        assert "/scheduling/coverage-requirements" in data["paths"]
        assert "/scheduling/operating-rules" in data["paths"]
        assert "post" not in data["paths"]["/organizations"]
        assert "patch" not in data["paths"]["/organizations/{id}"]
        assert "delete" not in data["paths"]["/organizations/{id}"]


class TestUnauthenticatedAccessRejected:
    @pytest.mark.parametrize("path", [
        "/auth/me",
        "/organizations",
        "/brands",
        "/processes",
        "/pods",
        "/employees",
        "/employee-skills",
        "/employee-availability",
        "/shifts",
        "/roster-assignments",
        "/employee-pods"
    ])
    def test_unauthenticated_requests_return_401(self, path):
        res = client.get(path)
        assert res.status_code in (401, 403), f"Expected 401/403 for {path}, got {res.status_code}"

    @pytest.mark.parametrize("path,payload", [
        (
            "/scheduling/generate",
            {
                "organization_id": str(uuid.uuid4()),
                "year": 2026,
                "month": 11,
            },
        ),
        (
            "/scheduling/validate",
            {
                "organization_id": str(uuid.uuid4()),
                "year": 2026,
                "month": 11,
                "assignments": [],
            },
        ),
        (
            "/scheduling/impact",
            {
                "organization_id": str(uuid.uuid4()),
                "start_date": "2026-11-01",
                "end_date": "2026-11-30",
                "change": {
                    "change_type": "employee_unavailable",
                    "employee_id": str(uuid.uuid4()),
                    "start_date": "2026-11-10",
                    "end_date": "2026-11-10",
                },
            },
        ),
    ])
    def test_scheduling_post_endpoints_require_authentication(self, path, payload):
        response = client.post(path, json=payload)
        assert response.status_code in (401, 403)

    @pytest.mark.parametrize("path", [
        "/scheduling/coverage-requirements",
        f"/scheduling/organizations/{uuid.uuid4()}/public-holidays",
    ])
    def test_scheduling_configuration_requires_authentication(self, path):
        response = client.get(path)
        assert response.status_code in (401, 403)


class TestCrudLifecycle:
    def test_complete_crud_flow(self, auth_tokens):
        headers_a = auth_tokens["user_a"]["headers"]
        headers_b = auth_tokens["user_b"]["headers"]

        # 1. Check Manager Profile (/auth/me)
        res_me = client.get("/auth/me", headers=headers_a)
        assert res_me.status_code == 200
        assert res_me.json()["employee_id"] == auth_tokens["user_a"]["employee_id"]

        # 2. Workspaces are provisioned administratively, not through the API.
        org_name = f"Test Corp {uuid.uuid4().hex[:6]}"
        org_id = _create_test_workspace(auth_tokens["user_a"]["user_id"], org_name)
        assert client.post("/organizations", json={"name": org_name}, headers=headers_a).status_code == 405

        # 3. Read Organization
        res_get_org = client.get(f"/organizations/{org_id}", headers=headers_a)
        assert res_get_org.status_code == 200
        assert res_get_org.json()["id"] == org_id

        # List organizations (User A sees it)
        res_list_orgs_a = client.get("/organizations", headers=headers_a)
        assert res_list_orgs_a.status_code == 200
        assert any(o["id"] == org_id for o in res_list_orgs_a.json())

        # Tenant isolation check: User B cannot see User A's organization
        res_list_orgs_b = client.get("/organizations", headers=headers_b)
        assert res_list_orgs_b.status_code == 200
        assert not any(o["id"] == org_id for o in res_list_orgs_b.json())

        res_get_org_b = client.get(f"/organizations/{org_id}", headers=headers_b)
        assert res_get_org_b.status_code == 404

        res_schedule_org_b = client.post(
            "/scheduling/generate",
            json={
                "organization_id": org_id,
                "year": 2026,
                "month": 11,
            },
            headers=headers_b,
        )
        assert res_schedule_org_b.status_code == 404

        # 4. Create Brand
        brand_name = f"Brand {uuid.uuid4().hex[:4]}"
        res_brand = client.post(
            "/brands",
            json={
                "organization_id": org_id,
                "name": brand_name,
                "industry": "E-Commerce",
                "description": "Primary Brand"
            },
            headers=headers_a
        )
        assert res_brand.status_code == 201
        brand = res_brand.json()
        brand_id = brand["id"]
        assert brand["name"] == brand_name

        # 6. Read & Update Brand
        res_get_brand = client.get(f"/brands/{brand_id}", headers=headers_a)
        assert res_get_brand.status_code == 200

        res_put_brand = client.put(
            f"/brands/{brand_id}",
            json={"name": f"{brand_name} v2", "industry": "Fashion", "description": "Updated"},
            headers=headers_a
        )
        assert res_put_brand.status_code == 200
        assert res_put_brand.json()["name"] == f"{brand_name} v2"

        # 7. Create Process
        proc_name = f"Process {uuid.uuid4().hex[:4]}"
        res_proc = client.post(
            "/processes",
            json={
                "brand_id": brand_id,
                "name": proc_name,
                "description": "Order Processing"
            },
            headers=headers_a
        )
        assert res_proc.status_code == 201
        proc = res_proc.json()
        proc_id = proc["id"]

        # 8. Create Pod
        pod_name = f"Pod {uuid.uuid4().hex[:4]}"
        res_pod = client.post(
            "/pods",
            json={
                "process_id": proc_id,
                "name": pod_name,
                "description": "Tier 1 Support"
            },
            headers=headers_a
        )
        assert res_pod.status_code == 201
        pod = res_pod.json()
        pod_id = pod["id"]

        # 9. Create Employee
        emp_code = f"E{uuid.uuid4().hex[:6].upper()}"
        res_emp = client.post(
            "/employees",
            json={
                "organization_id": org_id,
                "employee_code": emp_code,
                "first_name": "Alice",
                "last_name": "Smith",
                "email": f"{emp_code.lower()}@example.com",
                "phone": "+1-555-0100",
                "employment_type": "full_time",
                "status": "active",
                "max_hours_per_week": 40.0,
                "designation": "Associate"
            },
            headers=headers_a
        )
        assert res_emp.status_code == 201
        emp = res_emp.json()
        emp_id = emp["id"]

        # 10. Assign Employee to Pod
        res_emp_pod = client.post(
            "/employee-pods",
            json={"employee_id": emp_id, "pod_id": pod_id, "is_primary": True},
            headers=headers_a
        )
        assert res_emp_pod.status_code == 201

        # 11. Add Employee Skill
        res_skill = client.post(
            "/employee-skills",
            json={"employee_id": emp_id, "skill_name": "Customer Support", "proficiency": "advanced"},
            headers=headers_a
        )
        assert res_skill.status_code == 201
        skill_id = res_skill.json()["id"]

        # 12. Add Employee Availability
        res_avail = client.post(
            "/employee-availability",
            json={
                "employee_id": emp_id,
                "day_of_week": 1,
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "is_available": True
            },
            headers=headers_a
        )
        assert res_avail.status_code == 201
        avail_id = res_avail.json()["id"]

        # 13. Create Shift
        res_shift = client.post(
            "/shifts",
            json={
                "pod_id": pod_id,
                "shift_name": "Morning Shift",
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "required_headcount": 2
            },
            headers=headers_a
        )
        assert res_shift.status_code == 201
        shift_id = res_shift.json()["id"]

        # 14. Create Roster Assignment
        res_assign = client.post(
            "/roster-assignments",
            json={
                "employee_id": emp_id,
                "shift_id": shift_id,
                "assignment_date": "2026-11-10",
                "status": "scheduled"
            },
            headers=headers_a
        )
        assert res_assign.status_code == 201
        assign_id = res_assign.json()["id"]

        # 15. Verify listing with query filters
        res_filter_assign = client.get(
            f"/roster-assignments?employee_id={emp_id}&assignment_date=2026-11-10",
            headers=headers_a
        )
        assert res_filter_assign.status_code == 200
        assert len(res_filter_assign.json()) == 1

        # 16. Validation: User B cannot insert brand into User A's organization
        res_unauth_brand = client.post(
            "/brands",
            json={
                "organization_id": org_id,
                "name": "Intruder Brand",
            },
            headers=headers_b
        )
        assert res_unauth_brand.status_code in (403, 404)

        # 17. Workspace deletion is not exposed to the manager API.
        assert client.delete(f"/organizations/{org_id}", headers=headers_a).status_code == 405
        _delete_test_workspace(org_id)

        # Confirm deleted
        res_check_org = client.get(f"/organizations/{org_id}", headers=headers_a)
        assert res_check_org.status_code == 404


class TestSchedulingConfigurationAndLiveScenarios:
    def test_authenticated_configuration_crud_and_live_scheduling(
        self, auth_tokens
    ):
        headers_a = auth_tokens["user_a"]["headers"]
        headers_b = auth_tokens["user_b"]["headers"]

        def request(method, path, *, json=None, headers=headers_a, expected=200):
            arguments = {"headers": headers}
            if json is not None:
                arguments["json"] = json
            response = getattr(client, method)(path, **arguments)
            assert response.status_code == expected, (
                f"{method.upper()} {path}: expected {expected}, "
                f"got {response.status_code}: {response.text}"
            )
            return response.json() if response.content else None

        org_id = _create_test_workspace(
            auth_tokens["user_a"]["user_id"],
            f"Scheduling Integration {uuid.uuid4().hex[:8]}",
        )

        brand_single = request("post", "/brands", json={
            "organization_id": org_id,
            "name": "Single Resource",
        }, expected=201)
        brand_multi = request("post", "/brands", json={
            "organization_id": org_id,
            "name": "Multi Resource",
        }, expected=201)

        process_single = request("post", "/processes", json={
            "brand_id": brand_single["id"],
            "name": "Weekday Process",
        }, expected=201)
        process_multi = request("post", "/processes", json={
            "brand_id": brand_multi["id"],
            "name": "365 Day Process",
        }, expected=201)

        pod_single = request("post", "/pods", json={
            "process_id": process_single["id"],
            "name": "Weekday Pod",
        }, expected=201)
        pod_multi = request("post", "/pods", json={
            "process_id": process_multi["id"],
            "name": "365 Day Pod",
        }, expected=201)

        employees = {}
        for key, first_name in (
            ("single1", "Single One"),
            ("single2", "Single Two"),
            ("multi1", "Multi One"),
            ("multi2", "Multi Two"),
        ):
            code = f"SI-{uuid.uuid4().hex[:8].upper()}"
            first, _, last = first_name.partition(" ")
            employees[key] = request("post", "/employees", json={
                "organization_id": org_id,
                "employee_code": code,
                "first_name": first,
                "last_name": last,
                "email": f"{code.lower()}@example.com",
                "employment_type": "full_time",
                "status": "active",
                "max_hours_per_week": 40.0,
                "designation": "Associate",
            }, expected=201)

        for key, pod in (
            ("single1", pod_single),
            ("single2", pod_multi),
            ("multi1", pod_multi),
            ("multi2", pod_multi),
        ):
            request("post", "/employee-pods", json={
                "employee_id": employees[key]["id"],
                "pod_id": pod["id"],
                "is_primary": True,
            }, expected=201)

        shift_single = request("post", "/shifts", json={
            "pod_id": pod_single["id"],
            "shift_name": "Weekday Shift",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "required_headcount": 1,
        }, expected=201)
        shift_multi = request("post", "/shifts", json={
            "pod_id": pod_multi["id"],
            "shift_name": "365 Day Shift",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "required_headcount": 1,
        }, expected=201)

        request("post", "/scheduling/operating-rules", json={
            "process_id": process_single["id"],
            "operating_days": [0],
            "operates_on_public_holidays": False,
        }, expected=201)
        request("put", f"/scheduling/operating-rules/{process_single['id']}", json={
            "operating_days": [0],
            "operates_on_public_holidays": False,
        })
        assert request(
            "get",
            f"/scheduling/processes/{process_single['id']}/operating-rules/current",
        )["operating_days"] == [0]
        request("post", "/scheduling/operating-rules", json={
            "process_id": process_multi["id"],
            "operating_days": list(range(7)),
            "operates_on_public_holidays": True,
        }, expected=201)

        override_date = "2026-11-10"
        request("post", "/scheduling/operating-overrides", json={
            "process_id": process_single["id"],
            "operating_date": override_date,
            "is_operating": True,
        }, expected=201)
        assert request(
            "get",
            f"/scheduling/processes/{process_single['id']}/operating-overrides/{override_date}",
        )["is_operating"]
        request(
            "put",
            f"/scheduling/processes/{process_single['id']}/operating-overrides/{override_date}",
            json={"is_operating": True},
        )

        coverage = request("post", "/scheduling/coverage-requirements", json={
            "process_id": process_single["id"],
            "shift_id": shift_single["id"],
            "target_date": "2026-11-02",
            "minimum_staff": 1,
        }, expected=201)
        assert request(
            "get", f"/scheduling/coverage-requirements/{coverage['id']}"
        )["minimum_staff"] == 1
        request(
            "put",
            f"/scheduling/coverage-requirements/{coverage['id']}",
            json={"minimum_staff": 1},
        )

        holiday_date = "2026-11-08"
        request(
            "post",
            f"/scheduling/organizations/{org_id}/public-holidays",
            json={"holiday_date": holiday_date, "name": "Integration Holiday"},
            expected=201,
        )
        request(
            "patch",
            f"/scheduling/organizations/{org_id}/public-holidays/{holiday_date}",
            json={"name": "Integration Holiday"},
        )
        assert request(
            "get",
            f"/scheduling/organizations/{org_id}/public-holidays/{holiday_date}",
        )["name"] == "Integration Holiday"

        weekly_off_path = (
            f"/scheduling/employees/{employees['multi2']['id']}/weekly-offs"
        )
        request("post", weekly_off_path, json={"day_of_week": 6}, expected=201)
        assert request("get", weekly_off_path)[0]["day_of_week"] == 6
        request("put", f"{weekly_off_path}/6", json={"day_of_week": 6})

        time_off_path = f"/scheduling/employees/{employees['multi1']['id']}/time-off"
        time_off = request("post", time_off_path, json={
            "start_date": "2026-11-03",
            "end_date": "2026-11-03",
            "kind": "leave",
            "status": "planned",
            "reason": "Integration test",
        }, expected=201)
        time_off_item_path = f"{time_off_path}/{time_off['id']}"
        assert request("get", time_off_item_path)["status"] == "planned"
        request("patch", time_off_item_path, json={"status": "approved"})
        request("put", time_off_item_path, json={"status": "planned"})

        preference_path = (
            f"/scheduling/employees/{employees['multi1']['id']}/preferences"
        )
        preference = request("post", preference_path, json={
            "process_id": process_multi["id"],
            "preferred_shift_id": shift_multi["id"],
            "preferred_days_of_week": [6],
            "avoid_days_of_week": [],
        }, expected=201)
        preference_item_path = f"{preference_path}/{preference['id']}"
        assert request("get", preference_item_path)["preferred_days_of_week"] == [6]
        request("patch", preference_item_path, json={
            "preferred_days_of_week": [5, 6],
        })
        comp_off_path = (
            f"/scheduling/employees/{employees['single2']['id']}/time-off"
        )
        comp_off = request("post", comp_off_path, json={
            "start_date": "2026-11-04",
            "end_date": "2026-11-04",
            "kind": "comp_off",
            "status": "approved",
            "reason": "Integration test",
        }, expected=201)
        comp_off_item_path = f"{comp_off_path}/{comp_off['id']}"
        assert request("get", comp_off_item_path)["status"] == "approved"

        # A second authenticated manager cannot read or configure this tenant's data.
        request(
            "get",
            f"/scheduling/processes/{process_single['id']}/operating-rules/current",
            headers=headers_b,
            expected=404,
        )
        request(
            "get",
            f"/scheduling/coverage-requirements/{coverage['id']}",
            headers=headers_b,
            expected=404,
        )
        request(
            "get",
            f"/scheduling/organizations/{org_id}/public-holidays",
            headers=headers_b,
            expected=404,
        )
        request(
            "post",
            "/scheduling/operating-rules",
            headers=headers_b,
            json={
                "process_id": process_single["id"],
                "operating_days": [0],
                "operates_on_public_holidays": False,
            },
            expected=404,
        )

        generated = request("post", "/scheduling/generate", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
        })
        assert generated["is_valid"]
        assignments = generated["assignments"]
        single_nov2 = next(
            assignment for assignment in assignments
            if assignment["process_id"] == process_single["id"]
            and assignment["assignment_date"] == "2026-11-02"
        )
        multi_assignment = next(
            assignment for assignment in assignments
            if assignment["process_id"] == process_multi["id"]
            and assignment["assignment_date"] == "2026-11-04"
        )
        assert not any(
            assignment["employee_id"] == employees["multi1"]["id"]
            and assignment["assignment_date"] == "2026-11-03"
            for assignment in assignments
        )
        assert not any(
            assignment["employee_id"] == employees["multi2"]["id"]
            and date.fromisoformat(assignment["assignment_date"]).weekday() == 6
            for assignment in assignments
        )
        multi_coverage = [
            row for row in generated["coverage_summary"]
            if row["process_id"] == process_multi["id"]
        ]
        assert len(multi_coverage) == 30
        assert any(row["date"] == "2026-11-08" for row in multi_coverage)
        assert any(row["date"] == "2026-11-01" for row in multi_coverage)
        assert any(
            row["process_id"] == process_single["id"]
            and row["date"] == override_date
            for row in generated["coverage_summary"]
        )

        validated = request("post", "/scheduling/validate", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
            "assignments": assignments,
        })
        assert validated["is_valid"]

        invalid_assignments = [dict(assignment) for assignment in assignments]
        assignment_index = next(
            index for index, assignment in enumerate(invalid_assignments)
            if assignment["employee_id"] == single_nov2["employee_id"]
            and assignment["shift_id"] == single_nov2["shift_id"]
            and assignment["assignment_date"] == "2026-11-02"
        )
        invalid_assignments[assignment_index]["employee_id"] = str(uuid.uuid4())
        invalid_manual = request("post", "/scheduling/validate", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
            "assignments": invalid_assignments,
        })
        assert not invalid_manual["is_valid"]

        # Validate before saving manual assignments through the existing roster API.
        request("post", "/roster-assignments", json={
            "employee_id": single_nov2["employee_id"],
            "shift_id": single_nov2["shift_id"],
            "assignment_date": "2026-11-02",
            "status": "scheduled",
        }, expected=201)
        request("post", "/roster-assignments", json={
            "employee_id": multi_assignment["employee_id"],
            "shift_id": multi_assignment["shift_id"],
            "assignment_date": "2026-11-04",
            "status": "scheduled",
        }, expected=201)

        single_impact = request("post", "/scheduling/impact", json={
            "organization_id": org_id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "change": {
                "change_type": "employee_unavailable",
                "employee_id": single_nov2["employee_id"],
                "start_date": "2026-11-02",
                "end_date": "2026-11-02",
            },
        })
        assert len(single_impact["invalidated_assignments"]) == 1
        assert not single_impact["replacement_assignments"]
        assert single_impact["invalidated_assignments"][0][
            "possible_backup_employee_ids"
        ] == []
        assert single_impact["invalidated_assignments"][0]["suggested_resolution"]
        assert any(
            row["process_id"] == process_single["id"]
            and row["date"] == "2026-11-02"
            and row["unfilled_positions"]
            for row in single_impact["unfilled_positions"]
        )

        multi_impact = request("post", "/scheduling/impact", json={
            "organization_id": org_id,
            "start_date": "2026-11-04",
            "end_date": "2026-11-04",
            "change": {
                "change_type": "employee_unavailable",
                "employee_id": multi_assignment["employee_id"],
                "start_date": "2026-11-04",
                "end_date": "2026-11-04",
            },
        })
        assert len(multi_impact["invalidated_assignments"]) == 1
        assert multi_impact["replacement_assignments"]
        assert multi_impact["replacement_assignments"][0]["employee_id"] in {
            employees["multi1"]["id"], employees["multi2"]["id"]
        } - {multi_assignment["employee_id"]}

        # Persist an availability restriction after generation and revalidate the proposal.
        availability = request("post", "/employee-availability", json={
            "employee_id": single_nov2["employee_id"],
            "day_of_week": 0,
            "is_available": False,
        }, expected=201)
        assert availability["is_available"] is False
        revalidated = request("post", "/scheduling/validate", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
            "assignments": assignments,
        })
        assert not revalidated["is_valid"]
        assert any(
            conflict["conflict_type"] == "employee_unavailable"
            for conflict in revalidated["conflicts"]
        )

        request("delete", f"/employee-availability/{availability['id']}")
        restored_validation = request("post", "/scheduling/validate", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
            "assignments": assignments,
        })
        assert restored_validation["is_valid"]
        saved = request("post", "/roster-assignments/validated", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
            "assignments": assignments,
            "status": "scheduled",
        }, expected=201)
        assert len(saved) == len(assignments)
        published = request("post", "/roster-assignments/publish", json={
            "organization_id": org_id,
            "year": 2026,
            "month": 11,
        })
        assert published and all(row["status"] == "published" for row in published)

        request(
            "delete",
            preference_item_path,
        )
        request("delete", time_off_item_path)
        request("delete", comp_off_item_path)
        request("delete", f"{weekly_off_path}/6")
        request(
            "delete",
            f"/scheduling/organizations/{org_id}/public-holidays/{holiday_date}",
        )
        request("delete", f"/scheduling/coverage-requirements/{coverage['id']}")
        request(
            "delete",
            f"/scheduling/processes/{process_single['id']}/operating-overrides/{override_date}",
        )
        request("delete", f"/scheduling/operating-rules/{process_single['id']}")
        request("delete", f"/scheduling/operating-rules/{process_multi['id']}")
        _delete_test_workspace(org_id)


class TestValidationAndIntegrity:
    def test_invalid_email_format(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/employees",
            json={
                "organization_id": str(uuid.uuid4()),
                "employee_code": "TEST-BAD-EMAIL",
                "first_name": "Bad",
                "email": "not-an-email",
                "designation": "Associate"
            },
            headers=headers
        )
        assert res.status_code == 422

    def test_invalid_day_of_week(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/employee-availability",
            json={
                "employee_id": str(uuid.uuid4()),
                "day_of_week": 9,  # Must be 0-6
                "is_available": True
            },
            headers=headers
        )
        assert res.status_code == 422

    def test_brand_under_nonexistent_org(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/brands",
            json={
                "organization_id": str(uuid.uuid4()),
                "name": "Ghost Brand"
            },
            headers=headers
        )
        assert res.status_code in (404, 400, 403)

    def test_shift_under_nonexistent_pod(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/shifts",
            json={
                "pod_id": str(uuid.uuid4()),
                "shift_name": "Ghost Shift",
                "start_time": "09:00:00",
                "end_time": "17:00:00"
            },
            headers=headers
        )
        assert res.status_code in (404, 400, 403)

    def test_organization_creation_is_not_exposed(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/organizations",
            json={"name": ""},
            headers=headers
        )
        assert res.status_code == 405
