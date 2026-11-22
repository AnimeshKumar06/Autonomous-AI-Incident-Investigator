"""
Unit tests for Safety Engine.
Validates strict action whitelisting, rejection of arbitrary shell commands,
attempt budgeting, and parameter sanitization.
"""
import pytest
from src.safety.safety_engine import SafetyEngine, ActionRecord
from config import APPROVED_ACTIONS

def test_approved_action_validation():
    safety = SafetyEngine(max_attempts=2)
    is_valid, msg, code = safety.validate_action(
        incident_id="INC-001",
        action_name="SCALE_WORKERS",
        parameters={"worker_count": 8}
    )
    assert is_valid is True
    assert code == "APPROVED"

def test_unapproved_arbitrary_command_blocked():
    safety = SafetyEngine(max_attempts=2)
    # Attempt arbitrary unapproved commands
    dangerous_commands = [
        "DROP TABLE users",
        "rm -rf /",
        "format C:",
        "reboot --force",
        "EXECUTE_RANDOM_SCRIPT",
    ]
    for cmd in dangerous_commands:
        is_valid, msg, code = safety.validate_action(
            incident_id="INC-002",
            action_name=cmd,
            parameters={}
        )
        assert is_valid is False
        assert code == "BLOCKED_UNAPPROVED"
        assert "SECURITY VIOLATION" in msg

def test_max_attempts_budget_enforcement():
    safety = SafetyEngine(max_attempts=2)
    incident_id = "INC-BUDGET-01"

    # Attempt 1 - Allowed
    rec1 = safety.execute_action(incident_id, "ROLLBACK_CONFIG")
    assert rec1.is_approved is True
    assert rec1.attempt_number == 1

    # Attempt 2 - Allowed
    rec2 = safety.execute_action(incident_id, "RESTART_SERVICE")
    assert rec2.is_approved is True
    assert rec2.attempt_number == 2

    # Attempt 3 - BLOCKED by safety budget
    rec3 = safety.execute_action(incident_id, "CLEAR_CACHE")
    assert rec3.is_approved is False
    assert rec3.status == "BLOCKED_MAX_ATTEMPTS"
    assert "BUDGET EXCEEDED" in rec3.execution_message

def test_parameter_bounds_validation():
    safety = SafetyEngine(max_attempts=2)

    # Worker count too high (e.g. 500 workers)
    is_valid, msg, code = safety.validate_action(
        incident_id="INC-PARAM-01",
        action_name="SCALE_WORKERS",
        parameters={"worker_count": 500}
    )
    assert is_valid is False
    assert code == "PARAMETER_VIOLATION"

    # Worker count negative
    is_valid, msg, code = safety.validate_action(
        incident_id="INC-PARAM-02",
        action_name="SCALE_WORKERS",
        parameters={"worker_count": -5}
    )
    assert is_valid is False
    assert code == "PARAMETER_VIOLATION"
