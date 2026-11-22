"""
Unit tests for Detection Engine.
Validates metric thresholds, breach detection, and healthy state recognition.
"""
import pytest
import pandas as pd
from src.monitor.detector import IncidentDetector, Alert
from config import THRESHOLDS

def test_detector_healthy_baseline():
    detector = IncidentDetector()
    df = pd.DataFrame([{
        "timestamp": "2026-11-20 18:00:00",
        "response_time_ms": 110.0,
        "error_rate_pct": 0.2,
        "queue_length": 2,
        "throughput_rps": 50.0,
        "cpu_percent": 25.0,
        "memory_percent": 30.0,
    }])
    alert = detector.evaluate(df)
    assert alert.is_alert is False
    assert alert.severity == "OK"
    assert len(alert.violations) == 0

def test_detector_response_time_breach():
    detector = IncidentDetector()
    df = pd.DataFrame([
        {"response_time_ms": 450.0, "error_rate_pct": 0.5, "queue_length": 5, "cpu_percent": 30.0},
        {"response_time_ms": 520.0, "error_rate_pct": 0.4, "queue_length": 6, "cpu_percent": 32.0},
        {"response_time_ms": 600.0, "error_rate_pct": 0.5, "queue_length": 5, "cpu_percent": 31.0},
    ])
    alert = detector.evaluate(df)
    assert alert.is_alert is True
    viol_names = [v.metric_name for v in alert.violations]
    assert "response_time_ms" in viol_names

def test_detector_error_rate_critical():
    detector = IncidentDetector()
    df = pd.DataFrame([
        {"response_time_ms": 120.0, "error_rate_pct": 35.0, "queue_length": 4, "cpu_percent": 25.0},
    ])
    alert = detector.evaluate(df)
    assert alert.is_alert is True
    assert alert.severity == "CRITICAL"
    viol_names = [v.metric_name for v in alert.violations]
    assert "error_rate_pct" in viol_names

def test_detector_queue_breach():
    detector = IncidentDetector()
    df = pd.DataFrame([
        {"response_time_ms": 150.0, "error_rate_pct": 0.5, "queue_length": 95, "cpu_percent": 40.0},
    ])
    alert = detector.evaluate(df)
    assert alert.is_alert is True
    viol_names = [v.metric_name for v in alert.violations]
    assert "queue_length" in viol_names
