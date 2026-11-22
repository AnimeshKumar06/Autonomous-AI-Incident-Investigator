"""
Integration tests for Autonomous AI Incident Investigator FastAPI Server.
Validates telemetry endpoints, LangGraph scenario execution, and safety endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)

def test_api_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "orchestrator" in data
    assert data["orchestrator"] == "LangGraph StateGraph"

    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"

def test_api_telemetry_and_scenarios():
    res_t = client.get("/api/v1/telemetry/live")
    assert res_t.status_code == 200
    assert "latest_metrics" in res_t.json()

    res_s = client.get("/api/v1/scenarios")
    assert res_s.status_code == 200
    scenarios = res_s.json()
    assert "queue_bottleneck" in scenarios
    assert "high_error_rate" in scenarios

def test_api_execute_scenario():
    res = client.post("/api/v1/scenarios/execute", json={"scenario_id": "queue_bottleneck"})
    assert res.status_code == 200
    result = res.json()
    assert result["status"] == "RESOLVED"
    assert "Queue Bottleneck" in result["root_cause"]
    assert len(result["actions_taken"]) >= 1

def test_api_safety_audit():
    res = client.get("/api/v1/safety/audit")
    assert res.status_code == 200
    assert "approved_actions" in res.json()

def test_api_graph_info():
    res = client.get("/api/v1/graph/info")
    assert res.status_code == 200
    assert len(res.json()["nodes"]) == 6
