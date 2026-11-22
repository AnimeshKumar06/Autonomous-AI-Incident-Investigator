"""
Unit tests for LLM Root Cause Investigator.
Validates structured Pydantic output, evidence extraction, and classification accuracy.
"""
import pytest
import pandas as pd
from src.investigator.llm_investigator import LLMInvestigator, LLMInvestigationResult
from src.monitor.detector import IncidentDetector
from src.fake_app.service import SimulatedService

def test_llm_investigator_queue_bottleneck():
    service = SimulatedService()
    service.inject_fault("queue_bottleneck")
    for _ in range(2):
        service.tick()

    detector = IncidentDetector()
    df = service.get_metrics_df()
    alert = detector.evaluate(df)
    logs = service.get_recent_logs(20)

    investigator = LLMInvestigator()
    result: LLMInvestigationResult = investigator.investigate(
        incident_id="INC-LLM-01",
        alert=alert,
        metrics_df=df,
        recent_logs=logs,
    )

    assert isinstance(result, LLMInvestigationResult)
    assert "Queue Bottleneck" in result.root_cause
    assert result.confidence_score >= 0.80
    assert len(result.evidence_metrics) >= 1
    assert result.recommended_action == "SCALE_WORKERS"
    assert result.requires_human_escalation is False

def test_llm_investigator_unfixable_outage():
    service = SimulatedService()
    service.inject_fault("unfixable_outage")
    for _ in range(2):
        service.tick()

    detector = IncidentDetector()
    df = service.get_metrics_df()
    alert = detector.evaluate(df)
    logs = service.get_recent_logs(20)

    investigator = LLMInvestigator()
    result: LLMInvestigationResult = investigator.investigate(
        incident_id="INC-LLM-02",
        alert=alert,
        metrics_df=df,
        recent_logs=logs,
    )

    assert "External Infrastructure" in result.root_cause or "Outage" in result.root_cause
    assert result.requires_human_escalation is True
