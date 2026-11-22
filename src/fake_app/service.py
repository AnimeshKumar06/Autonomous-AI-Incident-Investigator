"""
Simulated Web Application Service.
Generates live metrics and logs, supports fault injection, and executes approved system actions.
"""
import random
import time
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd

from config import BASELINE_METRICS, THRESHOLDS
from src.fake_app.models import MetricPoint, LogEntry, ServiceState
from src.fake_app.scenarios import SCENARIOS, FailureScenario

class SimulatedService:
    """
    Simulates a production e-commerce web application with realistic metrics,
    log generation, fault injection capabilities, and operational action handlers.
    """
    def __init__(self, service_name: str = "shop-api-service"):
        self.service_name = service_name
        self.state = ServiceState()
        self.metrics_history: List[MetricPoint] = []
        self.logs_history: List[LogEntry] = []
        self._current_cycle = 0

        # Prime with 10 initial healthy baseline cycles
        for _ in range(10):
            self.tick()

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _emit_log(self, level: str, message: str):
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            level=level,
            message=message,
            source=self.service_name
        )
        self.logs_history.append(entry)
        if len(self.logs_history) > 500:
            self.logs_history.pop(0)

    def tick(self) -> MetricPoint:
        """Advance simulation clock by 1 tick and generate current metrics & logs."""
        self._current_cycle += 1
        self.state.uptime_seconds += 5
        ts = self._get_timestamp()

        # Healthy baseline values with natural variance
        resp_time = float(np.clip(np.random.normal(BASELINE_METRICS["response_time_ms"], 12.0), 60.0, 220.0))
        err_rate = float(np.clip(np.random.normal(BASELINE_METRICS["error_rate_pct"], 0.1), 0.0, 1.5))
        queue_len = int(np.clip(np.random.poisson(BASELINE_METRICS["queue_length"]), 0, 10))
        throughput = float(np.clip(np.random.normal(BASELINE_METRICS["throughput_rps"], 3.0), 20.0, 80.0))
        cpu = float(np.clip(np.random.normal(BASELINE_METRICS["cpu_percent"], 4.0), 10.0, 50.0))
        mem = float(np.clip(np.random.normal(BASELINE_METRICS["memory_percent"], 2.0), 20.0, 60.0))

        # Apply active fault scenario effects
        if self.state.active_scenario == "queue_bottleneck":
            queue_len = int(np.random.randint(90, 180))
            resp_time = float(np.random.uniform(750.0, 1300.0))
            err_rate = float(np.random.uniform(4.0, 8.5))
            cpu = float(np.random.uniform(88.0, 97.0))
            self._emit_log("WARN", f"Request queue length critical: {queue_len} requests waiting for worker thread.")
            self._emit_log("ERROR", f"Worker pool saturated (concurrency={self.state.workers}). Request latency {resp_time:.1f}ms exceeds SLA.")

        elif self.state.active_scenario == "high_error_rate":
            err_rate = float(np.random.uniform(28.0, 52.0))
            resp_time = float(np.random.uniform(320.0, 580.0))
            queue_len = int(np.random.randint(15, 35))
            self._emit_log("ERROR", f"HTTP 500 InternalServerError: Failed reading config key 'gateway.route_timeout' in release {self.state.config_version}.")
            self._emit_log("CRITICAL", f"Error rate spike: {err_rate:.2f}% requests failing. Upstream connection dropped.")

        elif self.state.active_scenario == "slow_response":
            resp_time = float(np.random.uniform(1800.0, 2900.0))
            queue_len = int(np.random.randint(30, 65))
            mem = float(np.random.uniform(89.0, 98.0))
            self._emit_log("WARN", "Cache memory fragmentation exceeds 90%. Eviction thread blocked.")
            self._emit_log("ERROR", f"Slow query detected: DB cache lock wait timeout after {resp_time:.1f}ms.")

        elif self.state.active_scenario == "unfixable_outage":
            err_rate = float(np.random.uniform(85.0, 100.0))
            resp_time = float(np.random.uniform(2500.0, 4500.0))
            queue_len = int(np.random.randint(120, 250))
            self._emit_log("CRITICAL", "External Payment Gateway provider connection refused (ConnectionResetError: ECONNRESET).")
            self._emit_log("CRITICAL", "Physical storage array I/O hardware failure on disk volume /dev/sda1.")

        else:
            # Healthy tick log
            if random.random() < 0.3:
                self._emit_log("INFO", f"HTTP 200 OK: Processed order #{random.randint(1000, 9999)} in {resp_time:.1f}ms.")

        point = MetricPoint(
            timestamp=ts,
            response_time_ms=round(resp_time, 2),
            error_rate_pct=round(err_rate, 2),
            queue_length=queue_len,
            throughput_rps=round(throughput, 2),
            cpu_percent=round(cpu, 2),
            memory_percent=round(mem, 2),
        )

        self.metrics_history.append(point)
        if len(self.metrics_history) > 200:
            self.metrics_history.pop(0)

        return point

    def inject_fault(self, scenario_id: str) -> bool:
        """Inject a specific failure scenario into the service."""
        if scenario_id not in SCENARIOS:
            self._emit_log("ERROR", f"Unknown failure scenario '{scenario_id}' requested.")
            return False

        scenario = SCENARIOS[scenario_id]
        self.state.active_scenario = scenario_id
        self.state.is_healthy = False

        if scenario_id == "high_error_rate":
            self.state.config_version = "v2.5.0-bad"
        elif scenario_id == "slow_response":
            self.state.cache_clean = False
        elif scenario_id == "unfixable_outage":
            self.state.external_provider_connected = False

        self._emit_log("CRITICAL", f"FAULT INJECTION TRIGGERED: {scenario.name} - {scenario.description}")
        return True

    def apply_action(self, action_name: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Execute an approved system operational action.
        Returns (success_flag, status_message).
        """
        params = params or {}
        ts = self._get_timestamp()

        if action_name == "SCALE_WORKERS":
            worker_count = params.get("worker_count", 8)
            self.state.workers = worker_count
            self._emit_log("INFO", f"Action applied: Worker pool scaled to {worker_count} concurrent workers.")
            if self.state.active_scenario == "queue_bottleneck":
                self.state.active_scenario = None
                self.state.is_healthy = True
                self._emit_log("INFO", "Queue backlog drained successfully. System returned to nominal load.")
                return True, f"Successfully scaled workers to {worker_count}. Queue backlog cleared."
            return True, f"Workers scaled to {worker_count}."

        elif action_name == "DRAIN_QUEUE":
            self._emit_log("INFO", "Action applied: Draining and shedding stale request queue backlog.")
            if self.state.active_scenario == "queue_bottleneck":
                self.state.active_scenario = None
                self.state.is_healthy = True
                self._emit_log("INFO", "Pending queue drained to zero. Latency normalized.")
                return True, "Request queue backlog drained."
            return True, "Queue backlog drained."

        elif action_name == "ROLLBACK_CONFIG":
            previous_version = "v2.4.1"
            self.state.config_version = previous_version
            self._emit_log("INFO", f"Action applied: Config rolled back to stable release {previous_version}.")
            if self.state.active_scenario == "high_error_rate":
                self.state.active_scenario = None
                self.state.is_healthy = True
                self._emit_log("INFO", "Bad configuration rolled back. Error rate returning to baseline.")
                return True, f"Configuration successfully rolled back to stable version {previous_version}."
            return True, f"Configuration rolled back to {previous_version}."

        elif action_name == "CLEAR_CACHE":
            self.state.cache_clean = True
            self._emit_log("INFO", "Action applied: In-memory cache cleared and lock tables reset.")
            if self.state.active_scenario == "slow_response":
                self.state.active_scenario = None
                self.state.is_healthy = True
                self._emit_log("INFO", "Cache refreshed. Latency returned to healthy SLA.")
                return True, "Cache successfully flushed. Lock contention resolved."
            return True, "Cache cleared."

        elif action_name == "RESTART_SERVICE":
            self._emit_log("INFO", "Action applied: Graceful rolling service restart executed.")
            if self.state.active_scenario in ["slow_response", "queue_bottleneck"]:
                self.state.active_scenario = None
                self.state.is_healthy = True
                self._emit_log("INFO", "Service restarted cleanly. Health probes passing.")
                return True, "Service restarted cleanly. Health probes nominal."
            elif self.state.active_scenario == "unfixable_outage":
                self._emit_log("ERROR", "Service restarted, but external upstream provider is STILL unreachable (ECONNREFUSED).")
                return False, "Service restarted, but upstream dependency remains offline. Incident unresolved."
            return True, "Service restarted cleanly."

        elif action_name == "ENABLE_RATE_LIMITING":
            self.state.rate_limiting_enabled = True
            self._emit_log("INFO", "Action applied: Ingress rate limiting enabled at 50 req/sec.")
            if self.state.active_scenario == "queue_bottleneck":
                self.state.active_scenario = None
                self.state.is_healthy = True
                return True, "Rate limiting throttled incoming traffic surge. Queue normalized."
            return True, "Rate limiting enabled."

        else:
            self._emit_log("ERROR", f"Unrecognized action attempted: '{action_name}'.")
            return False, f"Action '{action_name}' is not recognized by simulated service."

    def get_metrics_df(self, limit: int = 50) -> pd.DataFrame:
        """Return pandas DataFrame of recent metric history."""
        recent = self.metrics_history[-limit:] if limit else self.metrics_history
        if not recent:
            return pd.DataFrame()
        return pd.DataFrame([p.to_dict() for p in recent])

    def get_recent_logs(self, limit: int = 20) -> List[LogEntry]:
        """Return recent log entries."""
        return self.logs_history[-limit:] if limit else self.logs_history

    def reset(self):
        """Reset service state and baseline."""
        self.state = ServiceState()
        self.metrics_history.clear()
        self.logs_history.clear()
        self._current_cycle = 0
        self._emit_log("INFO", "Service initialized and started in nominal state.")
        for _ in range(10):
            self.tick()
