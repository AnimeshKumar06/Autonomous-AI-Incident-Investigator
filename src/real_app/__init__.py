"""
Real Web Application Package (FastAPI E-Commerce Service).
Provides a live HTTP service with order/catalog routes, telemetry instrumentation,
fault injection, and operational remediation interfaces.
"""
from src.real_app.api import app, create_app
from src.real_app.traffic_generator import TrafficGenerator

__all__ = ["app", "create_app", "TrafficGenerator"]
