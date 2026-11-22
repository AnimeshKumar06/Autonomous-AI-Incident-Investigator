"""
Synthetic Traffic Generator for Real FastAPI E-Commerce Application.
Generates concurrent customer traffic (browsing, ordering, health probes)
to create real load and test autonomous incident response.
"""
import time
import random
import threading
from typing import Dict, Any, Optional
import httpx

from config import REAL_APP_URL, TRAFFIC_CONFIG
from src.utils.logger import get_logger

logger = get_logger("traffic_generator")

class TrafficGenerator:
    """
    Simulates real-world user activity against the e-commerce service.
    Runs concurrently in a background daemon thread.
    """
    def __init__(self, target_base_url: str = REAL_APP_URL, target_rps: int = TRAFFIC_CONFIG["default_rps"]):
        self.target_url = target_base_url.rstrip("/")
        self.target_rps = target_rps
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Telemetry metrics
        self.requests_sent = 0
        self.success_count = 0
        self.error_count = 0
        self.latencies: list[float] = []

    def start(self):
        """Starts the traffic generator thread."""
        with self._lock:
            if self._is_running:
                logger.info("Traffic generator is already running.")
                return
            self._is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="traffic-gen-thread")
            self._thread.start()
            logger.info(f"Traffic generator started targeting {self.target_url} at {self.target_rps} RPS.")

    def stop(self):
        """Stops the traffic generator."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            logger.info("Traffic generator stop requested.")

    def set_rps(self, rps: int):
        """Dynamically adjusts requests per second."""
        with self._lock:
            self.target_rps = max(1, min(rps, 200))
            logger.info(f"Traffic generator RPS adjusted to {self.target_rps}.")

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics of traffic generated."""
        with self._lock:
            avg_lat = float(sum(self.latencies) / max(len(self.latencies), 1))
            return {
                "is_running": self._is_running,
                "target_rps": self.target_rps,
                "requests_sent": self.requests_sent,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "error_rate_pct": round((self.error_count / max(self.requests_sent, 1)) * 100.0, 2),
                "avg_latency_ms": round(avg_lat, 2),
            }

    def _run_loop(self):
        endpoints = ["/health", "/catalog", "/orders"]
        client = httpx.Client(base_url=self.target_url, timeout=TRAFFIC_CONFIG["timeout_seconds"])

        while self._is_running:
            delay = 1.0 / max(self.target_rps, 1)
            endpoint = random.choice(endpoints)
            start_time = time.time()

            try:
                if endpoint == "/orders":
                    payload = {
                        "item_id": f"PROD-{random.randint(1001, 1003)}",
                        "quantity": random.randint(1, 3),
                        "customer_id": f"CUST-{random.randint(10, 99)}"
                    }
                    resp = client.post("/orders", json=payload)
                else:
                    resp = client.get(endpoint)

                lat = (time.time() - start_time) * 1000.0
                with self._lock:
                    self.requests_sent += 1
                    self.latencies.append(lat)
                    if len(self.latencies) > 200:
                        self.latencies.pop(0)

                    if resp.status_code < 400:
                        self.success_count += 1
                    else:
                        self.error_count += 1

            except Exception:
                with self._lock:
                    self.requests_sent += 1
                    self.error_count += 1

            time.sleep(delay)

        try:
            client.close()
        except Exception:
            pass
