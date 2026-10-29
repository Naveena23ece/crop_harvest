"""
=============================================================================
FILE: backend/api/main.py
PROJECT: AI-Integrated Predictive Modeling and Adaptive Risk Evaluation DSS
DESCRIPTION:
    FastAPI application entry point.
    Provides all REST API endpoints for the grain storage risk prediction system.

    Endpoints:
        POST /predict              — Single sensor reading prediction
        POST /predict-sequence     — Sequence (24 readings) prediction
        GET  /latest-risk          — Latest risk from Firebase
        POST /train                — Trigger model training
        POST /retrain              — Retrain with new data
        GET  /history              — Prediction history
        GET  /sensor-history       — Sensor reading history
        GET  /model-info           — Model metadata
        GET  /alerts               — Alert history
        GET  /health               — Health check
        GET  /docs                 — Swagger UI (auto-generated)

    Start the server:
        uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
=============================================================================
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager

# Add root to path for module resolution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.utils.predictor    import get_predictor, RECOMMENDATIONS
from backend.utils.local_store  import local_store
from backend.utils.json_utils   import sanitize_json_value
from backend.firebase.firebase_client import (
    get_latest_sensor_reading,
    get_sensor_history,
    get_prediction_history,
    get_alert_history,
    write_prediction,
    write_alert,
    update_model_info,
    get_mock_sensor_reading,
    init_firebase,
    is_firebase_available,
)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("api")

# ─────────────────────────────────────────────
# LIFESPAN (startup + shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Grain Storage Risk API (Software Phase Prototype) ...")
    predictor = get_predictor()
    if predictor._loaded:
        logger.info("✓ AR-TCN model checkpoint loaded successfully")
        if is_firebase_available():
            try:
                update_model_info(predictor.get_model_info())
                logger.info("✓ Firebase Realtime Database synced")
            except Exception as e:
                logger.warning(f"Could not update Firebase model info: {e}")
        else:
            logger.info("✓ Local Prototype Persistence active (backend/data/local_storage.json)")
    else:
        logger.warning("⚠ Model not loaded — running in demo mode (rule-based fallback)")
    yield
    # Shutdown
    logger.info("Shutting down Grain Storage Risk API ...")


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="Grain Storage Risk Prediction API",
    description="""
## AI-Integrated Predictive Modeling & Adaptive Risk Evaluation DSS

This API provides real-time grain storage risk predictions using an
**Adaptive Risk-Aware Temporal Convolution Network (AR-TCN)**.

### Key Features
- 🌾 Real-time spoilage risk prediction (Low / Moderate / High)
- 📊 Sequence-based temporal predictions (24-step windows)
- 🔥 Firebase Realtime Database integration
- 📡 ESP32 IoT sensor data ingestion
- 🚨 Automated high-risk alerting
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the React dashboard to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────
class SensorReading(BaseModel):
    """Represents a single ESP32 sensor reading."""
    temperature_c:       float = Field(..., ge=-10, le=80,   description="Temperature in °C")
    humidity_pct:        float = Field(..., ge=0,   le=100,  description="Relative humidity %")
    gas_concentration:   float = Field(..., ge=0,   le=5000, description="Gas concentration (ppm)")
    grain_moisture:      float = Field(..., ge=0,   le=50,   description="Grain moisture content %")
    storage_duration:    int   = Field(default=30,  ge=0,    description="Days in storage")
    ext_temperature_c:   float = Field(default=30.0,         description="External temperature °C")
    ventilation_status:  int   = Field(default=1,   ge=0, le=1, description="0=OFF, 1=ON")
    battery_voltage:     float = Field(default=3.9,           description="Battery voltage (V)")
    sensor_health:       int   = Field(default=1,   ge=0, le=1, description="1=healthy, 0=degraded")
    timestamp:           Optional[str] = Field(default=None,  description="ISO timestamp")

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v):
        return v or datetime.now(timezone.utc).isoformat()


class SensorSequence(BaseModel):
    """Represents a 24-step sequence of sensor readings for temporal prediction."""
    readings: List[SensorReading] = Field(
        ..., min_items=1, max_items=24,
        description="Sequence of sensor readings (up to 24)"
    )


class PredictionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    timestamp:       str
    risk_category:   str
    confidence:      float
    probabilities:   Dict[str, float]
    model_name:      str
    recommendations: List[str]
    alert:           bool
    sensor_snapshot: Dict[str, Any]


class TrainRequest(BaseModel):
    dataset_path: Optional[str] = None
    model:        str            = Field(default="artcn",
                                         description="Model to train: all|rf|xgb|lgb|lstm|gru|tcn|artcn")
    force:        bool           = False


class RetrainRequest(BaseModel):
    new_data_path: str
    fine_tune:     bool = True


# (lifespan defined above, before app instantiation)


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Returns API health status."""
    predictor = get_predictor()
    return {
        "status":      "ok",
        "timestamp":   _utcnow(),
        "model_loaded": predictor._loaded,
        "model_name":  predictor._model_info.get("name", "demo"),
    }


# ─────────────────────────────────────────────
# PREDICTION ENDPOINTS
# ─────────────────────────────────────────────
@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_single(
    reading: SensorReading,
    background_tasks: BackgroundTasks,
):
    """
    Predict grain storage risk from a single sensor reading.

    The model maintains an internal history buffer; the first 24 calls
    will gradually build up a proper temporal context.
    """
    try:
        predictor = get_predictor()
        result    = predictor.predict_single(reading.dict(), is_telemetry=False)

        # Persist to Firebase in background (non-blocking)
        background_tasks.add_task(_persist_prediction, result)

        logger.info(f"/predict → {result['risk_category']} ({result['confidence']:.3f})")
        return result
    except Exception as e:
        logger.error(f"/predict error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict-sequence", response_model=PredictionResponse, tags=["Prediction"])
async def predict_sequence(
    payload: SensorSequence,
    background_tasks: BackgroundTasks,
):
    """
    Predict grain storage risk from a sequence of sensor readings.
    Provides the most accurate prediction by giving the model
    full temporal context (up to 24 timesteps = 6 hours).
    """
    try:
        predictor = get_predictor()
        sequence  = [r.dict() for r in payload.readings]
        result    = predictor.predict_sequence(sequence)

        background_tasks.add_task(_persist_prediction, result)

        logger.info(f"/predict-sequence → {result['risk_category']} ({result['confidence']:.3f})")
        return result
    except Exception as e:
        logger.error(f"/predict-sequence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/latest-risk", tags=["Prediction"])
async def get_latest_risk(
    background_tasks: BackgroundTasks,
    use_mock: bool = Query(default=False, description="Use mock data for demo")
):
    """
    Fetches the latest sensor reading from Firebase, local store, or simulated telemetry
    and evaluates risk using the AR-TCN model. Polled by the frontend dashboard.
    """
    try:
        data_source = "simulated_telemetry"
        if use_mock:
            sensor_data = get_mock_sensor_reading()
        else:
            sensor_data = None
            if is_firebase_available():
                sensor_data = get_latest_sensor_reading()
                if sensor_data:
                    data_source = "firebase"
            if not sensor_data:
                sensor_data = local_store.get_latest_sensor_reading()
                if sensor_data:
                    data_source = "local_prototype_persistence"
                else:
                    sensor_data = get_mock_sensor_reading()
                    data_source = "simulated_telemetry"

        predictor = get_predictor()
        result    = predictor.predict_single(sensor_data, is_telemetry=True)

        background_tasks.add_task(_persist_prediction, result)

        response_payload = {
            "sensor_data":    sensor_data,
            "prediction":     result,
            "data_source":    data_source,
            "is_simulated":   False if data_source == "firebase" else True,
            "operating_mode": "Live Cloud Sync" if data_source == "firebase" else "Local Prototype Mode (Phase 1 Software Review)",
            "timestamp":      _utcnow(),
        }
        return sanitize_json_value(response_payload)
    except Exception as e:
        logger.error(f"/latest-risk error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# HISTORY ENDPOINTS
# ─────────────────────────────────────────────
@app.get("/history", tags=["History"])
async def get_history(
    limit: int = Query(default=50, ge=1, le=500, description="Number of records to return"),
    type:  str = Query(default="predictions", description="predictions | sensors | alerts")
):
    """Returns historical data from Firebase or local simulated replay buffer."""
    try:
        data_source = "firebase" if is_firebase_available() else "local_prototype_persistence"
        is_simulation = not is_firebase_available()
        records = []

        if type == "predictions":
            if is_firebase_available():
                records = get_prediction_history(limit)
            if not records:
                records = local_store.get_predictions(limit)
                data_source = "local_prototype_persistence"
                is_simulation = True

        elif type == "sensors":
            if is_firebase_available():
                records = get_sensor_history(limit)
            if not records:
                records = local_store.get_sensor_history(limit)
                if records:
                    data_source = "local_prototype_persistence"
                    is_simulation = True
            if not records:
                # Load simulated replay from synthetic dataset
                csv_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "dataset", "grain_storage_dataset.csv"
                )
                if os.path.exists(csv_path):
                    try:
                        df_tail = pd.read_csv(csv_path).tail(limit)
                        # Sanitize floats into JSON-compliant values
                        raw_records = df_tail.to_dict(orient="records")
                        records = [sanitize_json_value(r) for r in raw_records]
                        data_source = "simulated_telemetry_replay"
                        is_simulation = True
                    except Exception as err:
                        logger.warning(f"Failed to read dataset tail: {err}")
                        records = []

        elif type == "alerts":
            if is_firebase_available():
                records = get_alert_history(limit)
            if not records:
                records = local_store.get_alerts(limit)
                data_source = "local_prototype_persistence"
                is_simulation = True
        else:
            raise HTTPException(status_code=400, detail="type must be: predictions|sensors|alerts")

        response_payload = {
            "type":               type,
            "count":              len(records),
            "records":            records,
            "data_source":        data_source,
            "is_physical_sensor": False if is_simulation else True,
            "mode":               "Simulated Telemetry Replay (Phase 1 Software Prototype)" if is_simulation else "Live Sensor Telemetry",
            "timestamp":          _utcnow(),
        }
        return sanitize_json_value(response_payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts", tags=["History"])
async def get_alerts(limit: int = Query(default=20, ge=1, le=100)):
    """Returns recent high-risk alerts."""
    try:
        alerts = []
        data_source = "firebase"
        if is_firebase_available():
            alerts = get_alert_history(limit)
        if not alerts:
            alerts = local_store.get_alerts(limit)
            data_source = "local_prototype_persistence"

        response_payload = {
            "count":       len(alerts),
            "alerts":      alerts,
            "data_source": data_source,
            "timestamp":   _utcnow(),
        }
        return sanitize_json_value(response_payload)
    except Exception as e:
        logger.error(f"/alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# MODEL INFO ENDPOINT
# ─────────────────────────────────────────────
@app.get("/model-info", tags=["Model"])
async def model_info():
    """Returns metadata about the currently loaded model and evaluation results."""
    try:
        predictor = get_predictor()
        info = predictor.get_model_info()

        # Try to add metrics from saved JSON
        metrics_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "models", "metrics.json"
        )
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                all_metrics = json.load(f)
            artcn_metrics = next((m for m in all_metrics if m["model"] == "artcn"), None)
            if artcn_metrics:
                info["evaluation_metrics"] = artcn_metrics
            info["all_model_metrics"] = all_metrics

        return info
    except Exception as e:
        logger.error(f"/model-info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# TRAINING ENDPOINTS
# ─────────────────────────────────────────────
_training_status = {"running": False, "last_run": None, "status": "idle"}


@app.post("/train", tags=["Training"])
async def trigger_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
):
    """
    Triggers model training as a background task.
    Training runs asynchronously; poll /model-info for completion.

    ⚠ This will take 10–60 minutes depending on hardware.
    """
    if _training_status["running"]:
        raise HTTPException(status_code=409, detail="Training is already in progress")

    background_tasks.add_task(_run_training, request.model, request.dataset_path)
    _training_status["running"] = True
    _training_status["last_run"] = _utcnow()
    _training_status["status"]  = "started"

    return {
        "message":   f"Training started for model: {request.model}",
        "status":    "running",
        "timestamp": _utcnow(),
    }


@app.post("/retrain", tags=["Training"])
async def retrain_model(request: RetrainRequest, background_tasks: BackgroundTasks):
    """
    Retrains the model on new data (incremental learning).
    Provide path to a new CSV file with the same schema.
    """
    if not os.path.exists(request.new_data_path):
        raise HTTPException(status_code=404,
                             detail=f"Data file not found: {request.new_data_path}")

    background_tasks.add_task(_run_training, "artcn", request.new_data_path)
    return {
        "message":   "Retraining started",
        "data_path": request.new_data_path,
        "timestamp": _utcnow(),
    }


# ─────────────────────────────────────────────
# RECOMMENDATIONS ENDPOINT
# ─────────────────────────────────────────────
@app.get("/recommendations/{risk_level}", tags=["Prediction"])
async def get_recommendations(risk_level: str):
    """Returns actionable recommendations for a given risk level."""
    risk_level = risk_level.capitalize()
    if risk_level not in RECOMMENDATIONS:
        raise HTTPException(status_code=400, detail="risk_level must be: Low|Moderate|High")
    return {
        "risk_level":     risk_level,
        "recommendations": RECOMMENDATIONS[risk_level],
    }


# ─────────────────────────────────────────────
# BACKGROUND TASK HELPERS
# ─────────────────────────────────────────────
async def _persist_prediction(result: Dict):
    """Saves prediction to local prototype persistence and Firebase if available."""
    try:
        # 1. Local cross-restart persistence
        local_store.save_prediction(result)

        # 2. Firebase write if configured
        if is_firebase_available():
            write_prediction(result)
            if result.get("alert"):
                write_alert({
                    "risk_category":   result["risk_category"],
                    "message":         "HIGH RISK detected — immediate action required",
                    "recommendations": result["recommendations"],
                    "sensor_snapshot": result["sensor_snapshot"],
                    "timestamp":       result["timestamp"],
                })
    except Exception as e:
        logger.warning(f"Failed to persist prediction: {e}")


async def _run_training(model: str, dataset_path = None):
    """Runs the training script in a subprocess."""
    global _training_status
    try:
        logger.info(f"Starting training: model={model}")
        train_script = os.path.join(
            os.path.dirname(__file__), "..", "..", "training", "train.py"
        )
        cmd = [sys.executable, train_script, f"--model={model}"]
        if dataset_path:
            cmd.append(f"--dataset={dataset_path}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            _training_status["status"] = "completed"
            logger.info("Training completed successfully")
            # Reload model
            predictor = get_predictor()
            predictor.load()
        else:
            _training_status["status"] = "failed"
            logger.error(f"Training failed: {stderr.decode()}")

    except Exception as e:
        _training_status["status"] = "error"
        logger.error(f"Training error: {e}")
    finally:
        _training_status["running"] = False


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
