"""
=============================================================================
FILE: backend/firebase/firebase_client.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    Firebase Realtime Database client module.
    Handles:
      - Initialising the Firebase Admin SDK
      - Reading latest sensor readings from the ESP32 node
      - Writing prediction results and alert records
      - Reading/writing history collections
      - Realtime listener registration for live data streaming

    Setup:
      1. Download your Firebase Admin SDK JSON key from the Firebase console.
      2. Set the path in FIREBASE_CREDENTIALS_PATH (or via env variable).
      3. Set your database URL in FIREBASE_DB_URL (or via env variable).
=============================================================================
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger("firebase_client")

# ─────────────────────────────────────────────
# CONFIGURATION (override with environment vars)
# ─────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
)
FIREBASE_DB_URL = os.environ.get(
    "FIREBASE_DB_URL",
    "https://grain-storage-monitor-default-rtdb.firebaseio.com"
)

# Realtime Database node paths
NODES = {
    "sensor_data":   "/sensor_data",          # ESP32 writes here
    "predictions":   "/predictions",          # ML backend writes here
    "alerts":        "/alerts",               # Alert history
    "history":       "/history",              # Aggregated history
    "model_info":    "/model_info",           # Model metadata
    "latest":        "/sensor_data/latest",   # Single latest reading
}


# ─────────────────────────────────────────────
# INITIALISE FIREBASE
# ─────────────────────────────────────────────
_firebase_initialized = False
_firebase_available = False


def is_firebase_available() -> bool:
    """Returns True if Firebase has been initialized with valid credentials."""
    global _firebase_initialized
    if not _firebase_initialized:
        init_firebase()
    return _firebase_available


def init_firebase() -> None:
    """
    Initialise the Firebase Admin SDK if credentials exist.
    If credentials are not found, cleanly enables Local Prototype Mode.
    Idempotent — safe to call multiple times.
    """
    global _firebase_initialized, _firebase_available
    if _firebase_initialized:
        return

    if not firebase_admin._apps:
        if os.path.exists(FIREBASE_CREDENTIALS_PATH):
            try:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
                _firebase_available = True
                logger.info(f"Firebase initialised with service account: {FIREBASE_CREDENTIALS_PATH}")
            except Exception as e:
                _firebase_available = False
                logger.warning(f"Failed to initialise Firebase with service account: {e}")
        else:
            _firebase_available = False
            logger.info("Firebase serviceAccountKey.json not detected — operating in Local Prototype Mode.")

    _firebase_initialized = True


# ─────────────────────────────────────────────
# READ HELPERS
# ─────────────────────────────────────────────
def get_latest_sensor_reading() -> Optional[Dict[str, Any]]:
    """
    Reads the most recent sensor reading written by the ESP32.

    Expected Firebase structure:
        /sensor_data/latest → {
            "timestamp":       "2024-01-15T10:30:00Z",
            "temperature_c":   27.5,
            "humidity_pct":    65.2,
            "gas_concentration": 420.0,
            "grain_moisture":  12.3,
            "storage_duration": 45,
            "ext_temperature_c": 30.0,
            "ventilation_status": 1,
            "battery_voltage": 3.95,
            "sensor_health":   1
        }
    """
    if not is_firebase_available():
        return None
    try:
        ref  = db.reference(NODES["latest"])
        data = ref.get()
        if data:
            logger.debug(f"Latest sensor reading retrieved: {data}")
        return data
    except Exception as e:
        logger.error(f"Failed to read latest sensor data: {e}")
        return None


def get_sensor_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Reads the most recent `limit` sensor readings from /sensor_data.
    Returns a list sorted by timestamp (oldest first).
    """
    if not is_firebase_available():
        return []
    try:
        ref  = db.reference(NODES["sensor_data"])
        data = ref.order_by_key().limit_to_last(limit + 1).get()
        if not data:
            return []
        # Convert the nested dict (keyed by push ID) to list
        records = [v for k, v in data.items() if k != "latest"]
        # Sort by timestamp string
        records.sort(key=lambda r: r.get("timestamp", ""))
        return records[-limit:]
    except Exception as e:
        logger.error(f"Failed to read sensor history: {e}")
        return []


def get_prediction_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Reads the most recent `limit` prediction records."""
    if not is_firebase_available():
        return []
    try:
        ref  = db.reference(NODES["predictions"])
        data = ref.order_by_key().limit_to_last(limit).get()
        if not data:
            return []
        records = list(data.values())
        records.sort(key=lambda r: r.get("timestamp", ""))
        return records
    except Exception as e:
        logger.error(f"Failed to read prediction history: {e}")
        return []


def get_alert_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Reads the most recent `limit` alert records."""
    if not is_firebase_available():
        return []
    try:
        ref  = db.reference(NODES["alerts"])
        data = ref.order_by_key().limit_to_last(limit).get()
        if not data:
            return []
        records = list(data.values())
        records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return records
    except Exception as e:
        logger.error(f"Failed to read alert history: {e}")
        return []


# ─────────────────────────────────────────────
# WRITE HELPERS
# ─────────────────────────────────────────────
def write_prediction(prediction: Dict[str, Any]) -> str:
    """
    Writes a prediction record to /predictions.
    Returns the Firebase push key.
    prediction dict should include:
        timestamp, risk_category, probabilities, sensor_snapshot
    """
    if not is_firebase_available():
        return ""
    try:
        ref = db.reference(NODES["predictions"])
        record = {
            "timestamp":    prediction.get("timestamp", _utcnow()),
            "risk_category": prediction["risk_category"],
            "confidence":    prediction.get("confidence", 0.0),
            "probabilities": prediction.get("probabilities", {}),
            "model_name":    prediction.get("model_name", "artcn"),
            "sensor_snapshot": prediction.get("sensor_snapshot", {}),
        }
        push_ref = ref.push(record)
        logger.info(f"Prediction written: {push_ref.key} → {record['risk_category']}")
        return push_ref.key
    except Exception as e:
        logger.error(f"Failed to write prediction: {e}")
        return ""


def write_alert(alert: Dict[str, Any]) -> str:
    """
    Writes an alert record to /alerts.
    alert dict should include: risk_category, message, recommendations
    """
    if not is_firebase_available():
        return ""
    try:
        ref = db.reference(NODES["alerts"])
        record = {
            "timestamp":       alert.get("timestamp", _utcnow()),
            "risk_category":   alert["risk_category"],
            "message":         alert.get("message", ""),
            "recommendations": alert.get("recommendations", []),
            "acknowledged":    False,
            "sensor_snapshot": alert.get("sensor_snapshot", {}),
        }
        push_ref = ref.push(record)
        logger.info(f"Alert written: {push_ref.key} → {record['risk_category']}")
        return push_ref.key
    except Exception as e:
        logger.error(f"Failed to write alert: {e}")
        return ""


def update_model_info(info: Dict[str, Any]) -> None:
    """Updates the model metadata node in Firebase."""
    if not is_firebase_available():
        return None
    try:
        ref = db.reference(NODES["model_info"])
        ref.set(info)
        logger.info("Model info updated in Firebase")
    except Exception as e:
        logger.error(f"Failed to update model info: {e}")


# ─────────────────────────────────────────────
# REALTIME LISTENER
# ─────────────────────────────────────────────
def register_sensor_listener(callback: Callable[[Dict], None]) -> Any:
    """
    Registers a Firebase realtime listener on /sensor_data/latest.
    The `callback` is invoked whenever new data is written by the ESP32.

    Args:
        callback: Function(data: dict) → None

    Returns:
        The listener handle (call .close() to stop listening).
    """
    if not is_firebase_available():
        return None
    ref = db.reference(NODES["latest"])

    def _on_update(event):
        if event.data and isinstance(event.data, dict):
            logger.info(f"Realtime update received: {event.data}")
            callback(event.data)

    listener = ref.listen(_on_update)
    logger.info("Realtime sensor listener registered")
    return listener


# ─────────────────────────────────────────────
# MOCK DATA (development mode without Firebase)
# ─────────────────────────────────────────────
def get_mock_sensor_reading() -> Dict[str, Any]:
    """
    Returns a mock sensor reading for local development
    when Firebase credentials are not available.
    """
    import random
    import math
    hour = datetime.now().hour
    season_factor = math.sin(2 * math.pi * datetime.now().timetuple().tm_yday / 365)
    return {
        "timestamp":          _utcnow(),
        "temperature_c":      round(27 + 8 * season_factor + random.gauss(0, 1.5), 2),
        "humidity_pct":       round(60 + 20 * season_factor + random.gauss(0, 4),  2),
        "gas_concentration":  round(450 + random.gauss(0, 60),                     1),
        "grain_moisture":     round(12  + random.gauss(0, 1.5),                    2),
        "storage_duration":   random.randint(10, 90),
        "ext_temperature_c":  round(30 + 5 * season_factor + random.gauss(0, 2),   2),
        "ventilation_status": random.choice([0, 1]),
        "battery_voltage":    round(3.7 + random.gauss(0, 0.1),                   3),
        "sensor_health":      1,
    }


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────
def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test with mock data
    reading = get_mock_sensor_reading()
    print("Mock reading:", json.dumps(reading, indent=2))
