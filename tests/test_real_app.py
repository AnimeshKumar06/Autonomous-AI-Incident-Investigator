"""
Integration tests for FastAPI Real E-Commerce Web Service.
Validates orders, catalog, metrics, fault injection, and remediation endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.real_app.api import app, service_instance

client = TestClient(app)

def setup_function():
    service_instance.reset_state()

def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["service"] == "shop-api-service"

    res_h = client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"

def test_catalog_and_orders():
    res_cat = client.get("/catalog")
    assert res_cat.status_code == 200
    assert len(res_cat.json()["products"]) >= 3

    res_ord = client.post("/orders", json={"item_id": "PROD-1001", "quantity": 2, "customer_id": "CUST-99"})
    assert res_ord.status_code == 200
    assert res_ord.json()["status"] == "CONFIRMED"

def test_metrics_endpoint():
    res_m = client.get("/metrics")
    assert res_m.status_code == 200
    data = res_m.json()
    assert "response_time_ms" in data
    assert "error_rate_pct" in data
    assert "queue_length" in data
    assert "active_workers" in data

def test_fault_injection_and_remediation():
    # Inject fault
    res_f = client.post("/faults/inject", json={"scenario": "high_error_rate"})
    assert res_f.status_code == 200
    assert service_instance.active_scenario == "high_error_rate"
    assert service_instance.config_version == "v2.5.0-bad"

    # Remediate with approved action
    res_r = client.post("/admin/remediate", json={"action": "ROLLBACK_CONFIG", "parameters": {}})
    assert res_r.status_code == 200
    assert res_r.json()["success"] is True
    assert service_instance.config_version == "v2.4.1"
    assert service_instance.active_scenario is None
