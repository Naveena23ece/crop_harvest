"""
=============================================================================
FILE: backend/utils/local_store.py
DESCRIPTION:
    Local prototype persistence engine for Phase 1 Software Review.
    Provides reliable, cross-restart persistence for:
      - Predictions history
      - Alert history
      - Sensor snapshots
    when Firebase credentials are not configured.
=============================================================================
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("local_store")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
STORAGE_FILE = os.path.join(DATA_DIR, "local_storage.json")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalStore:
    def __init__(self, storage_path: str = STORAGE_FILE):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {
            "predictions": [],
            "alerts": [],
            "sensor_readings": [],
            "latest_sensor": None,
        }
        self._init_storage()

    def _init_storage(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, dict):
                        self._data.update(content)
                        logger.info(f"Loaded local store: {len(self._data['predictions'])} predictions, {len(self._data['alerts'])} alerts")
            except Exception as e:
                logger.warning(f"Could not read local storage ({e}), re-initializing.")
                self._save()
        else:
            self._seed_baseline()
            self._save()

    def _seed_baseline(self) -> None:
        """Seed baseline alert so UI tables are informative on fresh startup."""
        if not self._data.get("alerts"):
            self._data["alerts"].append({
                "id": "alert-baseline-seed-001",
                "risk_category": "High",
                "message": "HIGH RISK: Storage temperature and moisture threshold exceeded",
                "recommendations": [
                    "IMMEDIATE ACTION REQUIRED: Activate emergency ventilation.",
                    "Inspect silo core and lower plenum for localized hot spots."
                ],
                "sensor_snapshot": {
                    "temperature_c": 38.0,
                    "humidity_pct": 88.0,
                    "gas_concentration": 1600.0,
                    "grain_moisture": 19.0,
                    "ventilation_status": 0
                },
                "timestamp": _utcnow(),
                "data_source": "local_prototype_persistence",
                "is_physical_sensor": False
            })

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist local store: {e}")

    def save_prediction(self, prediction: Dict[str, Any]) -> str:
        with self._lock:
            record = dict(prediction)
            record["persisted_at"] = _utcnow()
            record["data_source"] = "local_prototype_persistence"
            self._data["predictions"].append(record)
            if len(self._data["predictions"]) > 500:
                self._data["predictions"] = self._data["predictions"][-500:]

            # If prediction triggered an alert, save to alert history
            if prediction.get("alert"):
                alert_record = {
                    "id": f"alert-{len(self._data['alerts']) + 1:04d}",
                    "risk_category": prediction.get("risk_category", "High"),
                    "message": "HIGH RISK: Environmental anomaly detected by AR-TCN model",
                    "recommendations": prediction.get("recommendations", []),
                    "sensor_snapshot": prediction.get("sensor_snapshot", {}),
                    "timestamp": prediction.get("timestamp", _utcnow()),
                    "data_source": "local_prototype_persistence",
                    "is_physical_sensor": False
                }
                self._data["alerts"].insert(0, alert_record)
                if len(self._data["alerts"]) > 100:
                    self._data["alerts"] = self._data["alerts"][:100]

            snapshot = prediction.get("sensor_snapshot")
            if snapshot and isinstance(snapshot, dict):
                self._data["latest_sensor"] = dict(snapshot)

            self._save()
            return f"local-{len(self._data['predictions'])}"

    def save_sensor_reading(self, reading: Dict[str, Any]) -> None:
        with self._lock:
            rec = dict(reading)
            rec["data_source"] = "local_prototype_persistence"
            rec["is_physical_sensor"] = False
            self._data["sensor_readings"].append(rec)
            if len(self._data["sensor_readings"]) > 200:
                self._data["sensor_readings"] = self._data["sensor_readings"][-200:]
            self._data["latest_sensor"] = rec
            self._save()

    def get_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            preds = list(self._data["predictions"])
            preds.reverse()
            return preds[:limit]

    def get_alerts(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._data["alerts"])[:limit]

    def get_sensor_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._data["sensor_readings"])[-limit:]

    def get_latest_sensor_reading(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._data.get("latest_sensor"):
                return dict(self._data["latest_sensor"])
            return None


# Global singleton instance
local_store = LocalStore()
