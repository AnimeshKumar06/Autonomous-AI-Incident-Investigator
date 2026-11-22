"""
Production FastAPI Incident Investigator Server.
Exposes RESTful endpoints for autonomous telemetry monitoring, LangGraph workflow execution,
safety audit queries, and historical incident management.
"""
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import (
    API_HOST,
    API_PORT,
    THRESHOLDS,
    APPROVED_ACTIONS,
    SAFETY_CONFIG,
    LLM_PROVIDER,
    LLM_MODEL,
)
from src.utils.logger import get_logger
from src.fake_app.service import SimulatedService
from src.fake_app.scenarios import SCENARIOS
from src.workflow.loop import AutonomousInvestigator
from src.storage.repository import IncidentRepository
from src.safety.safety_engine import SafetyEngine
from src.real_app.api import app as real_app_router

logger = get_logger("api.server")

# Shared singletons
service_instance = SimulatedService()
repository_instance = IncidentRepository()
safety_instance = SafetyEngine()
investigator_instance = AutonomousInvestigator(
    service=service_instance,
    repository=repository_instance,
    safety_engine=safety_instance,
)

# Pydantic Schemas
class ScenarioExecutionRequest(BaseModel):
    scenario_id: str = Field(description="Scenario to trigger: queue_bottleneck, high_error_rate, slow_response, unfixable_outage")

class DirectActionRequest(BaseModel):
    incident_id: str
    action_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

def create_investigator_api() -> FastAPI:
    api = FastAPI(
        title="Autonomous AI Incident Investigator API",
        description="Production SRE Autonomous Investigator powered by LangGraph, FastAPI, and LLM reasoning.",
        version="2.0.0",
    )

    # Enable CORS for modern web dashboards and microservices
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount the real e-commerce application under /service
    api.mount("/service", real_app_router)

    @api.get("/", tags=["Info"])
    def root():
        return {
            "name": "Autonomous AI Incident Investigator API",
            "version": "2.0.0",
            "orchestrator": "LangGraph StateGraph",
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL,
            "status": "operational",
            "endpoints": {
                "telemetry": "/api/v1/telemetry/live",
                "scenarios": "/api/v1/scenarios",
                "execute": "/api/v1/scenarios/execute",
                "incidents": "/api/v1/incidents",
                "safety_audit": "/api/v1/safety/audit",
                "graph_info": "/api/v1/graph/info",
                "ecommerce_app": "/service",
            }
        }

    @api.get("/api/v1/health", tags=["System"])
    def health_check():
        return {
            "status": "healthy",
            "llm_provider": LLM_PROVIDER,
            "max_attempts": SAFETY_CONFIG["max_fix_attempts"],
            "approved_actions": APPROVED_ACTIONS,
        }

    @api.get("/api/v1/telemetry/live", tags=["Telemetry"])
    def get_live_telemetry():
        df = service_instance.get_metrics_df(limit=10)
        latest = df.iloc[-1].to_dict() if not df.empty else {}
        return {
            "latest_metrics": latest,
            "thresholds": THRESHOLDS,
            "service_state": {
                "workers": service_instance.state.workers,
                "config_version": service_instance.state.config_version,
                "active_scenario": service_instance.state.active_scenario,
                "is_healthy": service_instance.state.is_healthy,
            }
        }

    @api.get("/api/v1/scenarios", tags=["Scenarios"])
    def list_scenarios():
        return {
            k: {
                "id": v.id,
                "name": v.name,
                "description": v.description,
                "symptoms": v.symptoms,
                "resolvable": v.resolvable,
            }
            for k, v in SCENARIOS.items()
        }

    @api.post("/api/v1/scenarios/execute", tags=["Investigation"])
    def execute_scenario(req: ScenarioExecutionRequest):
        if req.scenario_id not in SCENARIOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown scenario '{req.scenario_id}'. Available: {list(SCENARIOS.keys())}"
            )

        logger.info(f"API request to run scenario: {req.scenario_id}")
        result = investigator_instance.run_scenario(req.scenario_id)
        return result.to_dict()

    @api.get("/api/v1/incidents", tags=["Incidents"])
    def list_incidents(limit: int = Query(default=50, ge=1, le=200)):
        incidents = repository_instance.list_incidents()
        return {"total": len(incidents), "incidents": incidents[:limit]}

    @api.get("/api/v1/incidents/{incident_id}", tags=["Incidents"])
    def get_incident(incident_id: str):
        inc = repository_instance.get_incident(incident_id)
        if not inc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident '{incident_id}' not found.")
        return inc

    @api.get("/api/v1/safety/audit", tags=["Safety"])
    def get_safety_audit():
        actions = [a.to_dict() for a in safety_instance.action_history]
        return {
            "max_attempts": SAFETY_CONFIG["max_fix_attempts"],
            "approved_actions": APPROVED_ACTIONS,
            "total_actions": len(actions),
            "audit_trail": actions[-50:],
        }

    @api.post("/api/v1/safety/validate", tags=["Safety"])
    def validate_action(req: DirectActionRequest):
        is_valid, reason, code = safety_instance.validate_action(req.incident_id, req.action_name, req.parameters)
        return {
            "action_name": req.action_name,
            "is_approved": is_valid,
            "status_code": code,
            "reason": reason,
        }

    @api.get("/api/v1/graph/info", tags=["LangGraph"])
    def get_graph_info():
        return {
            "orchestrator": "LangGraph StateGraph",
            "nodes": [
                {"id": "detect_node", "role": "Telemetry SLA Anomaly Evaluation"},
                {"id": "investigate_node", "role": "LLM Root Cause Diagnosis & Evidence Extraction"},
                {"id": "safety_eval_node", "role": "Whitelist, Parameter & Attempt Guardrails"},
                {"id": "remediate_node", "role": "Safe Operational Remediation Execution"},
                {"id": "verify_node", "role": "Post-Fix Stabilization & SLA Recovery Verification"},
                {"id": "escalate_node", "role": "Human On-Call Engineer Handover Synthesis"},
            ],
            "routing": {
                "from_detect": "If healthy -> END; If breach -> investigate_node",
                "from_investigate": "Always -> safety_eval_node",
                "from_safety_eval": "If approved -> remediate_node; If blocked -> escalate_node",
                "from_remediate": "Always -> verify_node",
                "from_verify": "If recovered -> END (RESOLVED); If retry allowed -> safety_eval_node; Else -> escalate_node",
                "from_escalate": "Always -> END (ESCALATED)",
            }
        }

    return api

app = create_investigator_api()
