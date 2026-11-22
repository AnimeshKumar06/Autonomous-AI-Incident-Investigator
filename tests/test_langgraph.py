"""
Unit tests for LangGraph StateGraph Incident Investigation Workflow.
Validates node transitions, conditional routing, attempt budgeting, and state evolution.
"""
import pytest
from src.workflow.graph import build_incident_graph, IncidentWorkflowState
from src.fake_app.service import SimulatedService
from config import SAFETY_CONFIG

def test_langgraph_healthy_path():
    graph = build_incident_graph()
    service = SimulatedService()

    state: IncidentWorkflowState = {
        "incident_id": "INC-TEST-01",
        "scenario_id": "none",
        "target_type": "simulated",
        "service_ref": service,
        "metrics_snapshot": {},
        "alert_data": None,
        "is_healthy": True,
        "investigation_data": None,
        "current_action": None,
        "actions_taken": [],
        "attempt_count": 0,
        "max_attempts": 2,
        "verification_passed": False,
        "status": "HEALTHY",
        "handover_notes": None,
        "timeline": [],
    }

    result = graph.invoke(state)
    assert result["is_healthy"] is True
    assert result["status"] == "HEALTHY"
    assert len(result["actions_taken"]) == 0

def test_langgraph_queue_bottleneck_resolution():
    graph = build_incident_graph()
    service = SimulatedService()
    service.inject_fault("queue_bottleneck")
    for _ in range(2):
        service.tick()

    state: IncidentWorkflowState = {
        "incident_id": "INC-TEST-02",
        "scenario_id": "queue_bottleneck",
        "target_type": "simulated",
        "service_ref": service,
        "metrics_snapshot": {},
        "alert_data": None,
        "is_healthy": True,
        "investigation_data": None,
        "current_action": None,
        "actions_taken": [],
        "attempt_count": 0,
        "max_attempts": 2,
        "verification_passed": False,
        "status": "HEALTHY",
        "handover_notes": None,
        "timeline": [],
    }

    result = graph.invoke(state)
    assert result["verification_passed"] is True
    assert result["status"] == "RESOLVED"
    assert len(result["actions_taken"]) >= 1
    assert result["actions_taken"][0]["action_name"] in ["SCALE_WORKERS", "DRAIN_QUEUE"]

def test_langgraph_unfixable_outage_escalation():
    graph = build_incident_graph()
    service = SimulatedService()
    service.inject_fault("unfixable_outage")
    for _ in range(2):
        service.tick()

    state: IncidentWorkflowState = {
        "incident_id": "INC-TEST-03",
        "scenario_id": "unfixable_outage",
        "target_type": "simulated",
        "service_ref": service,
        "metrics_snapshot": {},
        "alert_data": None,
        "is_healthy": True,
        "investigation_data": None,
        "current_action": None,
        "actions_taken": [],
        "attempt_count": 0,
        "max_attempts": 2,
        "verification_passed": False,
        "status": "HEALTHY",
        "handover_notes": None,
        "timeline": [],
    }

    result = graph.invoke(state)
    assert result["verification_passed"] is False
    assert result["status"] == "ESCALATED"
    assert result["attempt_count"] <= 2
    assert result["handover_notes"] is not None
    assert "CRITICAL SRE ESCALATION" in result["handover_notes"]
