import os
import sys

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from routers.sample_workforce import load_sample_workforce


def test_default_sample_workforce_has_related_employee_and_operations_data():
    data = load_sample_workforce()

    assert data["employees"]
    assert data["brands"]
    assert data["processes"]
    assert data["pods"]
    assert all(employee["first_name"] for employee in data["employees"])
    assert all(brand["name"] for brand in data["brands"])

    brand_ids = {brand["id"] for brand in data["brands"]}
    process_ids = {process["id"] for process in data["processes"]}
    pod_ids = {pod["id"] for pod in data["pods"]}
    employee_ids = {employee["id"] for employee in data["employees"]}

    assert all(process["brand_id"] in brand_ids for process in data["processes"])
    assert all(pod["process_id"] in process_ids for pod in data["pods"])
    assert all(item["employee_id"] in employee_ids for item in data["employeePods"])
    assert all(item["pod_id"] in pod_ids for item in data["employeePods"])
