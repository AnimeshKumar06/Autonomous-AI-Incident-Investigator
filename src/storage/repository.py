"""
Incident Repository layer.
Coordinates SQLite storage and flat JSON file exports for transparency and auditing.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import INCIDENTS_JSON_PATH
from src.storage.db import DatabaseManager

class IncidentRepository:
    """Provides high-level persistence API across SQLite and JSON files."""
    def __init__(self, db_manager: Optional[DatabaseManager] = None, json_path: Path = INCIDENTS_JSON_PATH):
        self.db = db_manager or DatabaseManager()
        self.json_path = json_path

    def _sync_json(self):
        """Export all current incidents to the JSON records file."""
        incidents = self.db.get_all_incidents()
        for inc in incidents:
            inc["actions"] = self.db.get_actions_for_incident(inc["id"])

        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(incidents, f, indent=2)
        except Exception:
            pass

    def record_incident(self, incident_data: Dict[str, Any]):
        self.db.save_incident(incident_data)
        self._sync_json()

    def record_action(self, action_data: Dict[str, Any]):
        self.db.save_action(action_data)
        self._sync_json()

    def list_incidents(self) -> List[Dict[str, Any]]:
        incidents = self.db.get_all_incidents()
        for inc in incidents:
            inc["actions"] = self.db.get_actions_for_incident(inc["id"])
        return incidents

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        incidents = self.list_incidents()
        for inc in incidents:
            if inc["id"] == incident_id:
                return inc
        return None
