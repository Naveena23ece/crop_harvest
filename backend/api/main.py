"""
=============================================================================
FILE: backend/api/main.py
PROJECT: GrainGuard AI - Post-Harvest Grain Storage Risk Monitoring & RBAC DSS
DESCRIPTION:
    FastAPI application entry point.
    Provides comprehensive REST endpoints:
        - RBAC & Sessions: /auth/login, /auth/signup, /auth/logout, /auth/me
        - Admin Operations: /admin/users, /admin/audit-logs, /admin/notifications, /admin/storage-units
        - Multi-Storage Units: /storage-units, /storage-units/{unit_id}
        - Reporting & Exports: /export/csv, /export/pdf
        - Predictive Modeling: /predict, /predict-sequence, /latest-risk, /recommendations
        - Historical Telemetry: /history, /alerts
        - System Health & Model Performance: /health, /system/status, /model-info
=============================================================================
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.database.db import SessionLocal, get_db
from backend.database.models import (
    User, StorageUnit, SensorReading as DBSensorReading,
    Prediction as DBPrediction, Alert as DBAlert,
    NotificationConfig, NotificationLog, AuditLog, SystemSetting
)
from backend.database.init_db import initialize_database
from backend.utils.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    revoke_token, get_current_user, require_admin, require_viewer_or_admin,
    get_optional_user, oauth2_scheme
)
from backend.utils.notifier import (
    dispatch_alert_notification, test_notification_channel, get_notification_settings
)
from backend.utils.exporter import generate_csv_export, generate_pdf_report
from backend.utils.predictor import get_predictor, RECOMMENDATIONS
from backend.utils.local_store import local_store
from backend.utils.json_utils import sanitize_json_value
from backend.firebase.firebase_client import (
    get_latest_sensor_reading,
    get_sensor_history,
    get_prediction_history,
    get_alert_history,
    write_prediction,
    write_alert,
    update_model_info,
    get_mock_sensor_reading,
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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_audit(db: Session, username: str, action: str, resource: str = "", details: dict = None, ip_address: str = None, user_id: int = None):
    """Safely records an audit log entry in SQLite."""
    try:
        entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            details_json=json.dumps(details) if details else None,
            ip_address=ip_address
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not write audit log: {e}")


# ─────────────────────────────────────────────
# LIFESPAN (startup + shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing GrainGuard AI Platform Services...")
    try:
        initialize_database()
        logger.info("✓ SQLite persistence and default accounts verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

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
            logger.info("✓ Local Prototype Persistence active (backend/data/grainguard.db)")
    else:
        logger.warning("⚠ Model not loaded — running in demo mode (rule-based fallback)")
    yield
    # Shutdown
    logger.info("Shutting down GrainGuard AI Platform...")


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="GrainGuard AI — Post-Harvest Risk Monitoring & RBAC DSS",
    description="""
## GrainGuard AI — Advanced Grain Storage DSS
Integrates:
- Adaptive Risk-Aware Temporal Convolutional Network (AR-TCN)
- NIST-Compliant Role-Based Access Control (Admin / Viewer)
- Multi-Silo Storage Unit Management
- Configurable Automated Telegram & SMTP Mobile Alerting
- Regulatory Audit Logging & ReportLab PDF Reporting
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    email:    str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    email:    str
    password: str
    role:     str = Field(default="viewer", description="admin | viewer")


class UserUpdateRequest(BaseModel):
    role:      Optional[str]  = None
    is_active: Optional[bool] = None
    password:  Optional[str]  = None


class NotificationSettingsRequest(BaseModel):
    email_enabled:     bool
    email_recipients:  str
    smtp_host:         str
    smtp_port:         int
    smtp_user:         str
    smtp_password:     Optional[str] = None
    telegram_enabled:  bool
    telegram_bot_token: Optional[str] = None
    telegram_chat_id:  str
    min_risk_level:    str = "High"
    cooldown_minutes:  int = 15


class NotificationTestRequest(BaseModel):
    channel: str = Field(..., description="telegram | email")
    target:  Optional[str] = None


class StorageUnitCreateRequest(BaseModel):
    unit_id:           str
    name:              str
    grain_type:        str = "Wheat"
    capacity_tons:     float = 500.0
    current_fill_tons: float = 320.0
    location:          str = "Sector A"
    status:            str = "Operational"


class StorageUnitUpdateRequest(BaseModel):
    name:              Optional[str]   = None
    grain_type:        Optional[str]   = None
    capacity_tons:     Optional[float] = None
    current_fill_tons: Optional[float] = None
    location:          Optional[str]   = None
    status:            Optional[str]   = None


class SensorReading(BaseModel):
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
    model:        str            = Field(default="artcn")
    force:        bool           = False


class RetrainRequest(BaseModel):
    new_data_path: str
    fine_tune:     bool = True


# ─────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS (Phase 1)
# ─────────────────────────────────────────────
@app.post("/auth/login", tags=["Authentication"])
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates credentials, generates JWT access token, and records login audit log."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        log_audit(db, req.username, "LOGIN_FAILED", "auth", {"error": "Invalid credentials"}, request.client.host if request.client else None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not user.is_active:
        log_audit(db, req.username, "LOGIN_BLOCKED", "auth", {"error": "Account deactivated"}, request.client.host if request.client else None, user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Contact an administrator.")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": user.username, "role": user.role, "uid": user.id})
    log_audit(db, user.username, "LOGIN_SUCCESS", "auth", {"role": user.role}, request.client.host if request.client else None, user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }


@app.post("/auth/signup", tags=["Authentication"])
async def public_signup(req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    """
    Public self-registration is strictly disabled.
    All accounts must be provisioned by an Administrator via the Admin Portal.
    """
    log_audit(db, req.username, "SIGNUP_REJECTED", "auth", {"error": "Public registration disabled"}, request.client.host if request.client else None)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public self-registration is disabled. User accounts must be created by an Administrator."
    )


@app.post("/auth/logout", tags=["Authentication"])
async def logout(request: Request, token: Optional[str] = Depends(oauth2_scheme), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revokes the current access token and records logout audit event."""
    auth_token = token or request.cookies.get("access_token")
    if auth_token:
        revoke_token(auth_token)
    log_audit(db, user.username, "LOGOUT", "auth", {}, request.client.host if request.client else None, user.id)
    return {"message": "Logged out successfully."}


@app.get("/auth/me", tags=["Authentication"])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return {"user": current_user.to_dict()}


# ─────────────────────────────────────────────
# ADMIN MANAGEMENT ENDPOINTS (Phase 1 & 6)
# ─────────────────────────────────────────────
@app.get("/admin/users", tags=["Admin Management"])
async def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: Retrieve list of all registered user accounts."""
    users = db.query(User).order_by(User.id.asc()).all()
    return {"users": [u.to_dict() for u in users], "total": len(users)}


@app.post("/admin/users", tags=["Admin Management"])
async def create_user_as_admin(
    req: UserCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Create user with explicit role assignment ('admin' or 'viewer')."""
    if req.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'viewer'.")
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters long.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")
    if db.query(User).filter(User.username == req.username.strip()).first():
        raise HTTPException(status_code=400, detail="Username is already in use.")
    if db.query(User).filter(User.email == req.email.strip()).first():
        raise HTTPException(status_code=400, detail="Email is already in use.")

    new_user = User(
        username=req.username.strip(),
        email=req.email.strip(),
        hashed_password=hash_password(req.password),
        role=req.role,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(db, admin.username, "ADMIN_CREATE_USER", "users", {"target_user": req.username, "role": req.role}, user_id=admin.id)
    return {"message": f"User account '{new_user.username}' created as {new_user.role.upper()}.", "user": new_user.to_dict()}


@app.patch("/admin/users/{user_id}", tags=["Admin Management"])
async def update_user_status(
    user_id: int,
    req: UserUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Activate, deactivate, change role, or reset password for an account."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Guard: Do not deactivate or demote self if you are the current admin
    if target_user.id == admin.id:
        if req.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own administrative account.")
        if req.role and req.role != "admin":
            raise HTTPException(status_code=400, detail="You cannot demote your own administrative role.")

    changes = {}
    if req.role is not None:
        if req.role not in ("admin", "viewer"):
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'.")
        target_user.role = req.role
        changes["role"] = req.role

    if req.is_active is not None:
        target_user.is_active = req.is_active
        changes["is_active"] = req.is_active

    if req.password is not None:
        if len(req.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
        target_user.hashed_password = hash_password(req.password)
        changes["password_reset"] = True

    db.commit()
    log_audit(db, admin.username, "ADMIN_UPDATE_USER", "users", {"target_user_id": user_id, "changes": changes}, user_id=admin.id)
    return {"message": "User updated successfully.", "user": target_user.to_dict()}


@app.get("/admin/audit-logs", tags=["Admin Management"])
async def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: View system audit trail with pagination."""
    total = db.query(AuditLog).count()
    logs = db.query(AuditLog).order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
    return {"total": total, "limit": limit, "offset": offset, "logs": [l.to_dict() for l in logs]}


@app.get("/admin/notifications/config", tags=["Admin Management"])
async def get_notification_config(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: View current notification settings with sensitive credentials masked."""
    settings = get_notification_settings()
    # Mask password
    masked = settings.copy()
    masked["smtp_password_configured"] = bool(settings.get("smtp_password"))
    masked["telegram_token_configured"] = bool(settings.get("telegram_bot_token"))
    masked.pop("smtp_password", None)
    masked.pop("telegram_bot_token", None)
    return {"config": masked}


@app.post("/admin/notifications/config", tags=["Admin Management"])
async def update_notification_config(
    req: NotificationSettingsRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Update external notification parameters in database."""
    config = db.query(NotificationConfig).first()
    if not config:
        config = NotificationConfig()
        db.add(config)

    config.email_enabled = req.email_enabled
    config.email_recipients = req.email_recipients
    config.smtp_host = req.smtp_host
    config.smtp_port = req.smtp_port
    config.smtp_user = req.smtp_user
    if req.smtp_password:
        os.environ["SMTP_PASSWORD"] = req.smtp_password
    config.telegram_enabled = req.telegram_enabled
    if req.telegram_bot_token:
        os.environ["TELEGRAM_BOT_TOKEN"] = req.telegram_bot_token
    config.telegram_chat_id = req.telegram_chat_id
    config.min_risk_level = req.min_risk_level
    config.cooldown_minutes = req.cooldown_minutes

    db.commit()
    log_audit(db, admin.username, "UPDATE_NOTIFICATION_CONFIG", "notifications", {"email_enabled": req.email_enabled, "telegram_enabled": req.telegram_enabled}, user_id=admin.id)
    return {"message": "Notification configuration updated successfully."}


@app.post("/admin/notifications/test", tags=["Admin Management"])
async def trigger_test_notification(
    req: NotificationTestRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Safely send a test notification via Telegram or Email."""
    result = test_notification_channel(req.channel, req.target)
    log_audit(db, admin.username, "TEST_NOTIFICATION", f"channel:{req.channel}", result, user_id=admin.id)
    return result


@app.get("/admin/notifications/logs", tags=["Admin Management"])
async def get_notification_logs(
    limit: int = Query(default=50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Retrieve history of alert notifications sent and delivery attempts."""
    logs = db.query(NotificationLog).order_by(desc(NotificationLog.timestamp)).limit(limit).all()
    return {"logs": [l.to_dict() for l in logs]}


@app.post("/admin/storage-units", tags=["Admin Management"])
async def create_storage_unit(
    req: StorageUnitCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Register a new silo / storage unit."""
    if db.query(StorageUnit).filter(StorageUnit.unit_id == req.unit_id).first():
        raise HTTPException(status_code=400, detail="Storage unit with this ID already exists.")

    unit = StorageUnit(
        unit_id=req.unit_id,
        name=req.name,
        grain_type=req.grain_type,
        capacity_tons=req.capacity_tons,
        current_fill_tons=req.current_fill_tons,
        location=req.location,
        status=req.status,
        created_at=datetime.now(timezone.utc)
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    log_audit(db, admin.username, "CREATE_STORAGE_UNIT", "storage_units", {"unit_id": req.unit_id, "name": req.name}, user_id=admin.id)
    return {"message": "Storage unit created.", "unit": unit.to_dict()}


@app.patch("/admin/storage-units/{unit_id}", tags=["Admin Management"])
async def update_storage_unit(
    unit_id: str,
    req: StorageUnitUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Update storage unit properties."""
    unit = db.query(StorageUnit).filter(StorageUnit.unit_id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Storage unit not found.")

    if req.name is not None: unit.name = req.name
    if req.grain_type is not None: unit.grain_type = req.grain_type
    if req.capacity_tons is not None: unit.capacity_tons = req.capacity_tons
    if req.current_fill_tons is not None: unit.current_fill_tons = req.current_fill_tons
    if req.location is not None: unit.location = req.location
    if req.status is not None: unit.status = req.status

    db.commit()
    log_audit(db, admin.username, "UPDATE_STORAGE_UNIT", "storage_units", {"unit_id": unit_id}, user_id=admin.id)
    return {"message": "Storage unit updated.", "unit": unit.to_dict()}


@app.post("/alerts/{alert_id}/acknowledge", tags=["Alerts"])
async def acknowledge_alert(
    alert_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: Mark an alert as acknowledged."""
    alert = db.query(DBAlert).filter(DBAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.acknowledged = True
    alert.acknowledged_by = admin.username
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(db, admin.username, "ACKNOWLEDGE_ALERT", "alerts", {"alert_id": alert_id}, user_id=admin.id)
    return {"message": f"Alert {alert_id} acknowledged by {admin.username}."}


# ─────────────────────────────────────────────
# STORAGE UNITS & SYSTEM STATUS (Accessible to Viewers & Admins)
# ─────────────────────────────────────────────
@app.get("/storage-units", tags=["Storage Units"])
async def list_storage_units(db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)):
    """Returns all storage units with their latest telemetry readings and current risk status."""
    units = db.query(StorageUnit).all()
    results = []
    for u in units:
        u_dict = u.to_dict()
        latest_pred = db.query(DBPrediction).filter(DBPrediction.unit_id == u.unit_id).order_by(desc(DBPrediction.timestamp)).first()
        latest_reading = db.query(DBSensorReading).filter(DBSensorReading.unit_id == u.unit_id).order_by(desc(DBSensorReading.timestamp)).first()
        u_dict["current_risk"] = latest_pred.risk_category if latest_pred else "Low"
        u_dict["confidence"] = latest_pred.confidence if latest_pred else 0.85
        u_dict["latest_telemetry"] = latest_reading.to_dict() if latest_reading else None
        results.append(u_dict)
    return {"storage_units": results, "total": len(results)}


@app.get("/storage-units/{unit_id}", tags=["Storage Units"])
async def get_storage_unit(unit_id: str, db: Session = Depends(get_db)):
    """Returns single storage unit metadata."""
    unit = db.query(StorageUnit).filter(StorageUnit.unit_id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Storage unit not found.")
    return {"unit": unit.to_dict()}


@app.get("/system/status", tags=["System"])
async def get_system_status(db: Session = Depends(get_db)):
    """Provides high-level system diagnostics, database health, and hardware integration state."""
    predictor = get_predictor()
    users_count = db.query(User).count()
    units_count = db.query(StorageUnit).count()
    preds_count = db.query(DBPrediction).count()
    alerts_count = db.query(DBAlert).count()

    return {
        "status": "operational",
        "timestamp": _utcnow(),
        "database": {
            "engine": "SQLite / SQLAlchemy",
            "file": "backend/data/grainguard.db",
            "users_count": users_count,
            "storage_units_count": units_count,
            "predictions_count": preds_count,
            "alerts_count": alerts_count,
        },
        "model": {
            "name": predictor._model_info.get("name", "AR-TCN"),
            "loaded": predictor._loaded,
            "architecture": "Adaptive Risk-Aware Temporal Convolutional Network (61 inputs)",
        },
        "hardware_integration": {
            "mode": "Local Prototype Mode (Simulated Telemetry Replay)",
            "esp32_connected": False,
            "notice": "Physical ESP32 hardware and sensor probes will be connected in the subsequent hardware integration phase.",
        }
    }


# ─────────────────────────────────────────────
# EXPORT & REPORTING ENDPOINTS (Phase 5)
# ─────────────────────────────────────────────
@app.get("/export/csv", tags=["Reports & Exports"])
async def export_csv(
    type: str = Query(default="predictions", description="predictions | sensors | alerts"),
    unit_id: Optional[str] = Query(None, description="Optional unit filter e.g. silo-1"),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Exports historical data to CSV formatted per RFC-4180."""
    try:
        if type == "predictions":
            query = db.query(DBPrediction)
            if unit_id:
                query = query.filter(DBPrediction.unit_id == unit_id)
            records = [p.to_dict() for p in query.order_by(desc(DBPrediction.timestamp)).limit(limit).all()]
            fieldnames = ["id", "unit_id", "timestamp", "risk_category", "confidence", "model_name", "alert"]

        elif type == "sensors":
            query = db.query(DBSensorReading)
            if unit_id:
                query = query.filter(DBSensorReading.unit_id == unit_id)
            records = [r.to_dict() for r in query.order_by(desc(DBSensorReading.timestamp)).limit(limit).all()]
            fieldnames = [
                "id", "unit_id", "timestamp", "temperature_c", "humidity_pct",
                "gas_concentration", "grain_moisture", "storage_duration",
                "ext_temperature_c", "ventilation_status", "battery_voltage", "sensor_health"
            ]

        elif type == "alerts":
            query = db.query(DBAlert)
            if unit_id:
                query = query.filter(DBAlert.unit_id == unit_id)
            records = [a.to_dict() for a in query.order_by(desc(DBAlert.timestamp)).limit(limit).all()]
            fieldnames = ["id", "unit_id", "timestamp", "level", "message", "acknowledged", "acknowledged_by"]

        else:
            raise HTTPException(status_code=400, detail="Invalid export type. Must be predictions|sensors|alerts.")

        csv_content = generate_csv_export(records, fieldnames)
        filename = f"grainguard_{type}_{unit_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate CSV: {str(e)}")


@app.get("/export/pdf", tags=["Reports & Exports"])
async def export_pdf_report(
    unit_id: Optional[str] = Query(None, description="Optional unit filter e.g. silo-1"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Generates an executive PDF Risk Audit Report using ReportLab."""
    try:
        unit_info = {"name": "All Grain Storage Units", "capacity_tons": 1500.0, "crop_type": "Wheat / Barley / Corn"}
        if unit_id:
            db_unit = db.query(StorageUnit).filter(StorageUnit.unit_id == unit_id).first()
            if db_unit:
                unit_info = db_unit.to_dict()

        # Telemetry statistics
        s_query = db.query(DBSensorReading)
        a_query = db.query(DBAlert)
        p_query = db.query(DBPrediction)
        if unit_id:
            s_query = s_query.filter(DBSensorReading.unit_id == unit_id)
            a_query = a_query.filter(DBAlert.unit_id == unit_id)
            p_query = p_query.filter(DBPrediction.unit_id == unit_id)

        recent_readings = [r.to_dict() for r in s_query.order_by(desc(DBSensorReading.timestamp)).limit(15).all()]
        recent_alerts = [a.to_dict() for a in a_query.order_by(desc(DBAlert.timestamp)).limit(10).all()]
        latest_pred = p_query.order_by(desc(DBPrediction.timestamp)).first()

        avg_temp = sum(r.get("temperature_c", 0) for r in recent_readings) / max(len(recent_readings), 1)
        avg_hum = sum(r.get("humidity_pct", 0) for r in recent_readings) / max(len(recent_readings), 1)

        stats = {
            "current_risk": latest_pred.risk_category if latest_pred else "Low Risk",
            "total_readings": s_query.count(),
            "avg_temp": avg_temp,
            "avg_humidity": avg_hum,
            "high_risk_alerts": a_query.filter(DBAlert.level == "HIGH").count()
        }

        operator_name = current_user.username if current_user else "Authorized Operator"
        pdf_bytes = generate_pdf_report(unit_info, stats, recent_alerts, recent_readings, generated_by=operator_name)

        filename = f"grainguard_risk_report_{unit_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# ─────────────────────────────────────────────
# PREDICTION & TELEMETRY ENDPOINTS
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Returns API health status."""
    predictor = get_predictor()
    return {
        "status":       "ok",
        "timestamp":    _utcnow(),
        "model_loaded": predictor._loaded,
        "model_name":   predictor._model_info.get("name", "demo"),
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_single(
    reading: SensorReading,
    background_tasks: BackgroundTasks,
    unit_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Predict grain storage risk from a single sensor reading.
    Maintains manual prediction repeatability without background stream interference.
    """
    try:
        target_unit = unit_id or "silo-1"
        predictor = get_predictor()
        result = predictor.predict_single(reading.dict(), is_telemetry=False)

        # Background persistence and external alerting
        background_tasks.add_task(_persist_prediction_db, result, target_unit, reading.dict())

        logger.info(f"/predict [{target_unit}] → {result['risk_category']} ({result['confidence']:.3f})")
        return result
    except Exception as e:
        logger.error(f"/predict error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict-sequence", response_model=PredictionResponse, tags=["Prediction"])
async def predict_sequence(
    payload: SensorSequence,
    background_tasks: BackgroundTasks,
    unit_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Predict grain storage risk from a temporal sequence of sensor readings (up to 24 timesteps).
    """
    try:
        target_unit = unit_id or "silo-1"
        predictor = get_predictor()
        sequence = [r.dict() for r in payload.readings]
        result = predictor.predict_sequence(sequence)

        last_reading = sequence[-1] if sequence else {}
        background_tasks.add_task(_persist_prediction_db, result, target_unit, last_reading)

        logger.info(f"/predict-sequence [{target_unit}] → {result['risk_category']} ({result['confidence']:.3f})")
        return result
    except Exception as e:
        logger.error(f"/predict-sequence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/latest-risk", tags=["Prediction"])
async def get_latest_risk(
    background_tasks: BackgroundTasks,
    unit_id: Optional[str] = None,
    use_mock: bool = Query(default=False, description="Use mock data for demo"),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Fetches the latest sensor reading from SQLite persistence or synthetic telemetry replay,
    evaluates risk via AR-TCN, updates history, and dispatches external alerts on High Risk.
    """
    try:
        target_unit = unit_id or "silo-1"
        data_source = "simulated_telemetry_replay"
        sensor_data = None

        if use_mock:
            sensor_data = get_mock_sensor_reading()
        else:
            # First check SQLite DB for latest reading of this unit
            db = SessionLocal()
            try:
                db_reading = db.query(DBSensorReading).filter(DBSensorReading.unit_id == target_unit).order_by(desc(DBSensorReading.timestamp)).first()
                if db_reading:
                    sensor_data = db_reading.to_dict()
                    data_source = "sqlite_database"
            finally:
                db.close()

            # Second fallback: local_store
            if not sensor_data:
                sensor_data = local_store.get_latest_sensor_reading()
                if sensor_data:
                    data_source = "local_prototype_persistence"

            # Third fallback: synthetic replay
            if not sensor_data:
                sensor_data = get_mock_sensor_reading()
                data_source = "simulated_telemetry_replay"

        predictor = get_predictor()
        result = predictor.predict_single(sensor_data, is_telemetry=True)

        background_tasks.add_task(_persist_prediction_db, result, target_unit, sensor_data)

        response_payload = {
            "unit_id":        target_unit,
            "sensor_data":    sensor_data,
            "prediction":     result,
            "data_source":    data_source,
            "is_simulated":   True,
            "operating_mode": "Local Prototype Mode (Simulated Telemetry Replay)",
            "hardware_notice": "Physical ESP32 hardware and sensor probes will be connected in the subsequent hardware integration phase.",
            "timestamp":      _utcnow(),
        }
        return sanitize_json_value(response_payload)
    except Exception as e:
        logger.error(f"/latest-risk error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", tags=["History"])
async def get_history(
    limit: int = Query(default=50, ge=1, le=500, description="Number of records to return"),
    type:  str = Query(default="predictions", description="predictions | sensors | alerts"),
    unit_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Returns historical records from SQLite with fallback to local storage or dataset."""
    try:
        data_source = "sqlite_database"
        records = []
        db = SessionLocal()

        try:
            if type == "predictions":
                query = db.query(DBPrediction)
                if unit_id:
                    query = query.filter(DBPrediction.unit_id == unit_id)
                db_preds = query.order_by(desc(DBPrediction.timestamp)).limit(limit).all()
                if db_preds:
                    records = [p.to_dict() for p in db_preds]
                if not records:
                    records = local_store.get_predictions(limit)
                    data_source = "local_prototype_persistence"

            elif type == "sensors":
                query = db.query(DBSensorReading)
                if unit_id:
                    query = query.filter(DBSensorReading.unit_id == unit_id)
                db_sensors = query.order_by(desc(DBSensorReading.timestamp)).limit(limit).all()
                if db_sensors and len(db_sensors) >= limit:
                    records = [r.to_dict() for r in db_sensors]
                if not records:
                    records = local_store.get_sensor_history(limit)
                    if records and len(records) >= limit:
                        data_source = "local_prototype_persistence"
                    else:
                        records = []
                if not records or len(records) < limit:
                    csv_path = os.path.join(
                        os.path.dirname(__file__), "..", "..", "dataset", "grain_storage_dataset.csv"
                    )
                    if os.path.exists(csv_path):
                        try:
                            df_tail = pd.read_csv(csv_path).tail(limit)
                            raw_records = df_tail.to_dict(orient="records")
                            records = [sanitize_json_value(r) for r in raw_records]
                            data_source = "simulated_telemetry_replay"
                        except Exception as err:
                            logger.warning(f"Failed to read dataset tail: {err}")
                            records = []

            elif type == "alerts":
                query = db.query(DBAlert)
                if unit_id:
                    query = query.filter(DBAlert.unit_id == unit_id)
                db_alerts = query.order_by(desc(DBAlert.timestamp)).limit(limit).all()
                if db_alerts:
                    records = [a.to_dict() for a in db_alerts]
                if not records:
                    records = local_store.get_alerts(limit)
                    data_source = "local_prototype_persistence"

            else:
                raise HTTPException(status_code=400, detail="type must be: predictions|sensors|alerts")

        finally:
            db.close()

        response_payload = {
            "type":               type,
            "unit_id":            unit_id or "all",
            "count":              len(records),
            "records":            records,
            "data_source":        data_source,
            "is_physical_sensor": False,
            "mode":               "Simulated Telemetry Replay (Phase 1 Software Prototype)",
            "timestamp":          _utcnow(),
        }
        return sanitize_json_value(response_payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts", tags=["History"])
async def get_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    unit_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Returns recent high-risk alerts from SQLite or local storage."""
    try:
        alerts = []
        data_source = "local_prototype_persistence"
        db = SessionLocal()
        try:
            query = db.query(DBAlert)
            if unit_id:
                query = query.filter(DBAlert.unit_id == unit_id)
            db_alerts = query.order_by(desc(DBAlert.timestamp)).limit(limit).all()
            if db_alerts:
                alerts = [a.to_dict() for a in db_alerts]
            if not alerts:
                alerts = local_store.get_alerts(limit)
        finally:
            db.close()

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


@app.get("/model-info", tags=["Model"])
async def model_info():
    """Returns metadata about the currently loaded AR-TCN model and evaluation results."""
    try:
        predictor = get_predictor()
        info = predictor.get_model_info()

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
# TRAINING ENDPOINTS (Admin Only)
# ─────────────────────────────────────────────
_training_status = {"running": False, "last_run": None, "status": "idle"}

@app.post("/train", tags=["Training"])
async def trigger_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin)
):
    """Admin-only: Triggers model training as a background task."""
    if _training_status["running"]:
        raise HTTPException(status_code=409, detail="Training is already in progress")

    background_tasks.add_task(_run_training, request.model, request.dataset_path)
    _training_status["running"] = True
    _training_status["last_run"] = _utcnow()
    _training_status["status"] = "started"

    return {
        "message": f"Training started for model: {request.model}",
        "status": "running",
        "timestamp": _utcnow(),
    }


@app.post("/retrain", tags=["Training"])
async def retrain_model(
    request: RetrainRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin)
):
    """Admin-only: Retrains the model on new data."""
    if not os.path.exists(request.new_data_path):
        raise HTTPException(status_code=404, detail=f"Data file not found: {request.new_data_path}")

    background_tasks.add_task(_run_training, "artcn", request.new_data_path)
    return {
        "message": "Retraining started",
        "data_path": request.new_data_path,
        "timestamp": _utcnow(),
    }


# ─────────────────────────────────────────────
# INTERNAL PERSISTENCE & ALERTING HELPERS
# ─────────────────────────────────────────────
async def _persist_prediction_db(result: Dict, unit_id: str = "silo-1", raw_reading: Dict = None):
    """
    Saves prediction and telemetry to SQLite and local_store,
    and dispatches automated external notifications if High Risk is detected.
    """
    try:
        # 1. Update SQLite DB
        db = SessionLocal()
        try:
            pred_row = DBPrediction(
                unit_id=unit_id,
                timestamp=datetime.now(timezone.utc),
                risk_category=result.get("risk_category", "Low"),
                confidence=float(result.get("confidence", 0.0)),
                low_proba=float(result.get("probabilities", {}).get("Low", 0.0)),
                mod_proba=float(result.get("probabilities", {}).get("Moderate", 0.0)),
                high_proba=float(result.get("probabilities", {}).get("High", 0.0)),
                model_name=result.get("model_name", "artcn"),
                alert=bool(result.get("alert", False)),
                recommendations_json=json.dumps(result.get("recommendations", [])),
                sensor_snapshot_json=json.dumps(result.get("sensor_snapshot", {})),
            )
            db.add(pred_row)

            if raw_reading:
                reading_row = DBSensorReading(
                    unit_id=unit_id,
                    timestamp=datetime.now(timezone.utc),
                    temperature_c=raw_reading.get("temperature_c", raw_reading.get("temperature")),
                    humidity_pct=raw_reading.get("humidity_pct", raw_reading.get("humidity")),
                    gas_concentration=raw_reading.get("gas_concentration"),
                    grain_moisture=raw_reading.get("grain_moisture"),
                    storage_duration=raw_reading.get("storage_duration", 30),
                    ext_temperature_c=raw_reading.get("ext_temperature_c", 30.0),
                    ventilation_status=raw_reading.get("ventilation_status", 1),
                    battery_voltage=raw_reading.get("battery_voltage", 3.9),
                    sensor_health=raw_reading.get("sensor_health", 1),
                    is_simulated=True,
                    source="simulated_telemetry_replay"
                )
                db.add(reading_row)

            # High risk alert generation
            if result.get("alert"):
                alert_row = DBAlert(
                    unit_id=unit_id,
                    timestamp=datetime.now(timezone.utc),
                    level="HIGH",
                    message=f"CRITICAL: Spoilage Risk Alert ({result['confidence']*100:.1f}%) in {unit_id}",
                    details_json=json.dumps(result),
                    acknowledged=False
                )
                db.add(alert_row)

            db.commit()
        finally:
            db.close()

        # 2. Local prototype persistence for backwards compatibility
        local_store.save_prediction(result)

        # 3. External alert notification
        if result.get("alert"):
            dispatch_alert_notification(
                unit_id=unit_id,
                unit_name=f"Storage Silo ({unit_id})",
                risk_category=result.get("risk_category", "High"),
                confidence=result.get("confidence", 0.9),
                readings=result.get("sensor_snapshot", raw_reading or {}),
                recommendations=result.get("recommendations", [])
            )

        # 4. Firebase write if available
        if is_firebase_available():
            write_prediction(result)
            if result.get("alert"):
                write_alert({
                    "unit_id": unit_id,
                    "risk_category": result["risk_category"],
                    "message": "HIGH RISK detected — immediate action required",
                    "recommendations": result["recommendations"],
                    "sensor_snapshot": result["sensor_snapshot"],
                    "timestamp": result["timestamp"],
                })

    except Exception as e:
        logger.warning(f"Failed to persist prediction in DB: {e}")


async def _run_training(model: str, dataset_path = None):
    """Runs model training in background subprocess."""
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
