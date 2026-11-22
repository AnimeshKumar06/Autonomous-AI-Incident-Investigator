"""
FastAPI Server Package for Incident Investigator API.
"""
from src.api.server import app, create_investigator_api

__all__ = ["app", "create_investigator_api"]
