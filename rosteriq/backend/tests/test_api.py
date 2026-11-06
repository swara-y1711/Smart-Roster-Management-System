import os
import sys
import uuid
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

# Helper for test user management
TEST_USER_A_EMAIL = f"test_mgr_a_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_B_EMAIL = f"test_mgr_b_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"

@pytest.fixture(scope="session")
def auth_tokens():
    """Sets up two test users to verify authentication and tenant isolation."""
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

        # Ensure manager profile exists
        authed_sb = get_supabase_client()
        authed_sb.postgrest.auth(token)
        authed_sb.table("manager_profiles").upsert({
            "id": user_id,
            "full_name": f"Manager {label}",
            "work_email": email,
            "employee_id": emp_id
        }).execute()

    yield tokens

    # Teardown: Clean up test users from auth.users
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    for uid in created_user_ids:
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


class TestCrudLifecycle:
    def test_complete_crud_flow(self, auth_tokens):
        headers_a = auth_tokens["user_a"]["headers"]
        headers_b = auth_tokens["user_b"]["headers"]

        # 1. Check Manager Profile (/auth/me)
        res_me = client.get("/auth/me", headers=headers_a)
        assert res_me.status_code == 200
        assert res_me.json()["employee_id"] == auth_tokens["user_a"]["employee_id"]

        # 2. Create Organization
        org_name = f"Test Corp {uuid.uuid4().hex[:6]}"
        res_org = client.post("/organizations", json={"name": org_name}, headers=headers_a)
        assert res_org.status_code == 201
        org = res_org.json()
        org_id = org["id"]
        assert org["name"] == org_name

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

        # 4. Update Organization
        res_patch_org = client.patch(
            f"/organizations/{org_id}",
            json={"name": f"{org_name} Updated"},
            headers=headers_a
        )
        assert res_patch_org.status_code == 200
        assert res_patch_org.json()["name"] == f"{org_name} Updated"

        # 5. Create Brand
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

        # 17. Cleanup via Cascade Delete of Organization
        res_del_org = client.delete(f"/organizations/{org_id}", headers=headers_a)
        assert res_del_org.status_code == 200

        # Confirm deleted
        res_check_org = client.get(f"/organizations/{org_id}", headers=headers_a)
        assert res_check_org.status_code == 404


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

    def test_empty_organization_name(self, auth_tokens):
        headers = auth_tokens["user_a"]["headers"]
        res = client.post(
            "/organizations",
            json={"name": ""},
            headers=headers
        )
        assert res.status_code == 422

