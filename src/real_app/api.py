"""
FastAPI E-Commerce Web Service with Live Operational Telemetry and Fault Injection.
Simulates a real-world shopping service handling orders, catalog browsing,
real-time metrics calculation, and SRE administrative remediation.
"""
import time
import random
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from config import THRESHOLDS, BASELINE_METRICS, APPROVED_ACTIONS, SAFETY_CONFIG
from src.utils.logger import get_logger

logger = get_logger("real_app.api")

# Pydantic Schemas
class OrderRequest(BaseModel):
    item_id: str = Field(default="PROD-1001", description="Catalog product ID")
    quantity: int = Field(default=1, ge=1, le=50, description="Quantity to purchase")
    customer_id: str = Field(default="CUST-42", description="Customer identifier")

class FaultInjectionRequest(BaseModel):
    scenario: str = Field(description="Scenario ID: queue_bottleneck, high_error_rate, slow_response, unfixable_outage")

class RemediationRequest(BaseModel):
    action: str = Field(description="Approved action name from whitelist")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for action")

class ServiceMetrics(BaseModel):
    timestamp: str
    response_time_ms: float
    error_rate_pct: float
    queue_length: int
    throughput_rps: float
    cpu_percent: float
    memory_percent: float
    active_workers: int
    config_version: str
    is_healthy: bool
    active_scenario: Optional[str]

class RealAppService:
    """Thread-safe state manager for the FastAPI e-commerce application."""
    def __init__(self):
        self._lock = threading.Lock()
        self.active_scenario: Optional[str] = None
        self.workers = SAFETY_CONFIG["default_workers"]
        self.config_version = "v2.4.1"
        self.cache_clean = True
        self.rate_limiting_enabled = False
        self.external_provider_connected = True
        self.is_healthy = True

        # Telemetry rolling history
        self.total_requests = 0
        self.failed_requests = 0
        self.latency_samples: List[float] = [BASELINE_METRICS["response_time_ms"]]
        self.queue_depth = 2
        self.last_reset_time = time.time()

    def record_request(self, latency_ms: float, is_error: bool):
        with self._lock:
            self.total_requests += 1
            if is_error:
                self.failed_requests += 1
            self.latency_samples.append(latency_ms)
            if len(self.latency_samples) > 100:
                self.latency_samples.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            avg_latency = float(sum(self.latency_samples) / max(len(self.latency_samples), 1))
            error_rate = float((self.failed_requests / max(self.total_requests, 1)) * 100.0)

            # Apply active scenario biases to make metrics visible and realistic
            if self.active_scenario == "queue_bottleneck":
                q_len = random.randint(90, 160)
                resp = max(avg_latency, random.uniform(700.0, 1200.0))
                err = max(error_rate, random.uniform(4.5, 7.5))
                cpu = random.uniform(88.0, 96.0)
                mem = random.uniform(45.0, 60.0)
                healthy = False
            elif self.active_scenario == "high_error_rate":
                q_len = random.randint(10, 25)
                resp = random.uniform(280.0, 520.0)
                err = random.uniform(30.0, 55.0)
                cpu = random.uniform(40.0, 65.0)
                mem = random.uniform(35.0, 50.0)
                healthy = False
            elif self.active_scenario == "slow_response":
                q_len = random.randint(30, 55)
                resp = random.uniform(1600.0, 2800.0)
                err = random.uniform(0.5, 2.0)
                cpu = random.uniform(50.0, 75.0)
                mem = random.uniform(88.0, 96.0)
                healthy = False
            elif self.active_scenario == "unfixable_outage":
                q_len = random.randint(120, 220)
                resp = random.uniform(2500.0, 4200.0)
                err = random.uniform(85.0, 99.0)
                cpu = random.uniform(90.0, 98.0)
                mem = random.uniform(75.0, 90.0)
                healthy = False
            else:
                # Nominal healthy metrics
                q_len = int(max(0, random.poisson(BASELINE_METRICS["queue_length"]))) if hasattr(random, 'poisson') else random.randint(0, 4)
                resp = max(60.0, avg_latency + random.uniform(-10.0, 10.0))
                err = max(0.05, min(error_rate, 1.2))
                cpu = random.uniform(20.0, 35.0)
                mem = random.uniform(30.0, 45.0)
                healthy = True

            return {
                "timestamp": ts,
                "response_time_ms": round(resp, 2),
                "error_rate_pct": round(err, 2),
                "queue_length": q_len,
                "throughput_rps": round(random.uniform(40.0, 65.0), 2),
                "cpu_percent": round(cpu, 2),
                "memory_percent": round(mem, 2),
                "active_workers": self.workers,
                "config_version": self.config_version,
                "is_healthy": healthy,
                "active_scenario": self.active_scenario,
            }

    def inject_fault(self, scenario: str) -> bool:
        with self._lock:
            valid_scenarios = ["queue_bottleneck", "high_error_rate", "slow_response", "unfixable_outage"]
            if scenario not in valid_scenarios:
                return False
            self.active_scenario = scenario
            self.is_healthy = False
            if scenario == "high_error_rate":
                self.config_version = "v2.5.0-bad"
            elif scenario == "slow_response":
                self.cache_clean = False
            elif scenario == "unfixable_outage":
                self.external_provider_connected = False
            logger.warning(f"Injected fault scenario: {scenario}")
            return True

    def reset_state(self):
        with self._lock:
            self.active_scenario = None
            self.workers = SAFETY_CONFIG["default_workers"]
            self.config_version = "v2.4.1"
            self.cache_clean = True
            self.rate_limiting_enabled = False
            self.external_provider_connected = True
            self.is_healthy = True
            self.total_requests = 10
            self.failed_requests = 0
            self.latency_samples = [BASELINE_METRICS["response_time_ms"]]
            logger.info("Service state reset to nominal healthy baseline.")

    def apply_remediation(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        with self._lock:
            if action not in APPROVED_ACTIONS:
                return False, f"Action '{action}' is rejected by safety policy."

            if action == "SCALE_WORKERS":
                count = params.get("worker_count", 8)
                self.workers = count
                if self.active_scenario == "queue_bottleneck":
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, f"Worker pool scaled to {count}. Queue backlog drained."
                return True, f"Worker pool scaled to {count}."

            elif action == "ROLLBACK_CONFIG":
                self.config_version = "v2.4.1"
                if self.active_scenario == "high_error_rate":
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, "Config successfully rolled back to stable release v2.4.1. Errors cleared."
                return True, "Config rolled back to v2.4.1."

            elif action == "CLEAR_CACHE":
                self.cache_clean = True
                if self.active_scenario == "slow_response":
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, "In-memory cache flushed. Query lock contention resolved."
                return True, "In-memory cache cleared."

            elif action == "RESTART_SERVICE":
                if self.active_scenario in ["slow_response", "queue_bottleneck"]:
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, "Graceful service restart complete. All probes nominal."
                elif self.active_scenario == "unfixable_outage":
                    return False, "Service restarted, but upstream payment provider remains unreachable."
                return True, "Service restarted gracefully."

            elif action == "DRAIN_QUEUE":
                if self.active_scenario == "queue_bottleneck":
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, "Backlogged request queue safely drained."
                return True, "Queue drained."

            elif action == "ENABLE_RATE_LIMITING":
                self.rate_limiting_enabled = True
                if self.active_scenario == "queue_bottleneck":
                    self.active_scenario = None
                    self.is_healthy = True
                    return True, "Ingress rate limiting enabled at 50 rps. Traffic surge stabilized."
                return True, "Rate limiting enabled."

            return False, f"Unhandled action '{action}'."

# Singleton service instance
service_instance = RealAppService()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Production E-Commerce Shop API",
        description="Production web application with telemetry instrumentation and automated remediation hooks.",
        version="1.0.0",
    )

    @app.get("/", tags=["Info"])
    def root():
        return {
            "service": "shop-api-service",
            "status": "online",
            "version": service_instance.config_version,
            "is_healthy": service_instance.is_healthy,
        }

    @app.get("/health", tags=["Telemetry"])
    def health_check():
        snapshot = service_instance.get_snapshot()
        if not snapshot["is_healthy"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "degraded", "metrics": snapshot}
            )
        return {"status": "healthy", "metrics": snapshot}

    @app.get("/catalog", tags=["E-Commerce"])
    def get_catalog():
        start = time.time()
        # Simulated fault effect for slow_response
        if service_instance.active_scenario == "slow_response":
            time.sleep(0.3)
        if service_instance.active_scenario == "high_error_rate" and random.random() < 0.4:
            service_instance.record_request(50.0, True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Config route_timeout null error")

        latency = (time.time() - start) * 1000.0
        service_instance.record_request(latency, False)
        return {
            "products": [
                {"id": "PROD-1001", "name": "Mechanical Keyboard", "price": 89.99},
                {"id": "PROD-1002", "name": "4K Ultra Monitor", "price": 349.50},
                {"id": "PROD-1003", "name": "Ergonomic Desk Chair", "price": 199.00},
            ]
        }

    @app.post("/orders", tags=["E-Commerce"])
    def create_order(order: OrderRequest):
        start = time.time()
        if service_instance.active_scenario == "unfixable_outage":
            service_instance.record_request(150.0, True)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="External Payment Gateway unreachable (ECONNRESET)")
        if service_instance.active_scenario == "high_error_rate" and random.random() < 0.5:
            service_instance.record_request(40.0, True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="NullPointerException in OrderProcessor")
        if service_instance.active_scenario == "queue_bottleneck":
            time.sleep(0.1)

        latency = (time.time() - start) * 1000.0
        service_instance.record_request(latency, False)
        return {
            "order_id": f"ORD-{random.randint(10000, 99999)}",
            "item_id": order.item_id,
            "status": "CONFIRMED",
            "processed_by_worker": random.randint(1, service_instance.workers),
        }

    @app.get("/metrics", response_model=ServiceMetrics, tags=["Telemetry"])
    def get_metrics():
        return service_instance.get_snapshot()

    @app.post("/faults/inject", tags=["Fault Injection"])
    def inject_fault(req: FaultInjectionRequest):
        ok = service_instance.inject_fault(req.scenario)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Invalid scenario: {req.scenario}")
        return {"status": "fault_injected", "scenario": req.scenario}

    @app.post("/faults/reset", tags=["Fault Injection"])
    def reset_fault():
        service_instance.reset_state()
        return {"status": "reset_successful"}

    @app.post("/admin/remediate", tags=["SRE Remediation"])
    def remediate(req: RemediationRequest):
        success, message = service_instance.apply_remediation(req.action, req.parameters)
        return {"success": success, "action": req.action, "message": message}

    @app.get("/admin/state", tags=["SRE Remediation"])
    def get_admin_state():
        return {
            "workers": service_instance.workers,
            "config_version": service_instance.config_version,
            "cache_clean": service_instance.cache_clean,
            "rate_limiting_enabled": service_instance.rate_limiting_enabled,
            "external_provider_connected": service_instance.external_provider_connected,
            "active_scenario": service_instance.active_scenario,
        }

    return app

app = create_app()
