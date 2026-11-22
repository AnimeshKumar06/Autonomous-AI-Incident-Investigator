"""
Data models for simulated service metrics, logs, and state.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class MetricPoint:
    timestamp: str
    response_time_ms: float
    error_rate_pct: float
    queue_length: int
    throughput_rps: float
    cpu_percent: float
    memory_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class LogEntry:
    timestamp: str
    level: str  # INFO, WARN, ERROR, CRITICAL
    message: str
    source: str = "app-service"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        return f"[{self.timestamp}] [{self.level}] ({self.source}) {self.message}"

@dataclass
class ServiceState:
    is_healthy: bool = True
    active_scenario: Optional[str] = None
    workers: int = 4
    config_version: str = "v2.4.1"
    cache_clean: bool = True
    rate_limiting_enabled: bool = False
    external_provider_connected: bool = True
    uptime_seconds: int = 0
