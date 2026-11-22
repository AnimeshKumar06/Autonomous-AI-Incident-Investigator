"""
Unit tests for full Autonomous Workflow Lifecycle and Storage.
"""
import pytest
from src.workflow.loop import AutonomousInvestigator
from src.storage.repository import IncidentRepository
from src.storage.db import DatabaseManager

def test_workflow_database_persistence():
    repo = IncidentRepository()
    investigator = AutonomousInvestigator(repository=repo)

    result = investigator.run_scenario("queue_bottleneck")

    stored = repo.get_incident(result.incident_id)
    assert stored is not None
    assert stored["id"] == result.incident_id
    assert stored["status"] == "RESOLVED"
    assert len(stored["actions"]) >= 1

def test_workflow_healthy_state_when_no_fault():
    investigator = AutonomousInvestigator()
    # Check baseline health
    df = investigator.service.get_metrics_df()
    alert = investigator.detector.evaluate(df)
    assert alert.is_alert is False
