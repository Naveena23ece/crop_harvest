"""
Database initialization and data migration service for GrainGuard AI.
Handles:
  1. Creating SQLite database schema.
  2. Initializing Admin and Viewer accounts (using environment variables or safe defaults).
  3. Seeding default storage units (silos).
  4. Migrating historical predictions and alerts from local_storage.json.
  5. Initializing default notification configurations.
"""

import os
import json
import logging
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    for candidate in [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        ".env",
        "backend/.env",
    ]:
        if os.path.exists(candidate):
            load_dotenv(candidate)
except ImportError:
    pass

from backend.database.db import engine, SessionLocal, Base, DATA_DIR
from backend.database.models import (
    User, StorageUnit, SensorReading, Prediction, Alert,
    NotificationConfig, AuditLog, SystemSetting
)
from backend.utils.auth import hash_password

logger = logging.getLogger("grainguard.database")


def _utcnow():
    return datetime.now(timezone.utc)


def initialize_database():
    """Initializes tables, seeds initial accounts, storage units, and migrates legacy data."""
    # 1. Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Initialize default accounts
        _init_accounts(db)

        # 3. Initialize storage units
        _init_storage_units(db)

        # 4. Initialize notification config
        _init_notification_config(db)

        # 5. Migrate local_storage.json if present
        _migrate_local_storage(db)

        # 6. Seed baseline sensor readings if empty
        seed_sensor_readings(db)

        db.commit()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during database initialization: {e}")
        raise
    finally:
        db.close()


def _init_accounts(db):
    """
    Creates the default Admin and Viewer accounts if they do not already exist.
    Credentials can be configured via environment variables.
    If the accounts already exist, passwords are NOT overwritten.
    """
    admin_user = os.environ.get("GRAINGUARD_ADMIN_USER", "Naveena")
    admin_pass = os.environ.get("GRAINGUARD_ADMIN_PASS", "2004")
    admin_email = os.environ.get("GRAINGUARD_ADMIN_EMAIL", "naveena@grainguard.local")

    viewer_user = os.environ.get("GRAINGUARD_VIEWER_USER", "viewer")
    viewer_pass = os.environ.get("GRAINGUARD_VIEWER_PASS", "viewer2026")
    viewer_email = os.environ.get("GRAINGUARD_VIEWER_EMAIL", "viewer@grainguard.local")

    # Check Admin
    existing_admin = db.query(User).filter(User.username == admin_user).first()
    if not existing_admin:
        admin = User(
            username=admin_user,
            email=admin_email,
            hashed_password=hash_password(admin_pass),
            role="admin",
            is_active=True,
            created_at=_utcnow(),
        )
        db.add(admin)
        db.flush()
        db.add(AuditLog(
            username="system",
            action="INITIALIZE_ACCOUNT",
            resource=f"user:{admin_user}",
            details_json=json.dumps({"role": "admin", "email": admin_email}),
        ))
        logger.info(f"Initialized default Admin account: '{admin_user}'")

    # Check Viewer
    existing_viewer = db.query(User).filter(User.username == viewer_user).first()
    if not existing_viewer:
        viewer = User(
            username=viewer_user,
            email=viewer_email,
            hashed_password=hash_password(viewer_pass),
            role="viewer",
            is_active=True,
            created_at=_utcnow(),
        )
        db.add(viewer)
        db.flush()
        db.add(AuditLog(
            username="system",
            action="INITIALIZE_ACCOUNT",
            resource=f"user:{viewer_user}",
            details_json=json.dumps({"role": "viewer", "email": viewer_email}),
        ))
        logger.info(f"Initialized default Viewer account: '{viewer_user}'")


def _init_storage_units(db):
    """Seeds default storage silos if none exist."""
    count = db.query(StorageUnit).count()
    if count == 0:
        default_units = [
            StorageUnit(
                unit_id="silo-1",
                name="Silo Alpha - Durum Wheat",
                grain_type="Durum Wheat",
                capacity_tons=500.0,
                current_fill_tons=385.0,
                location="Sector A - Main Storage",
                status="Operational",
            ),
            StorageUnit(
                unit_id="silo-2",
                name="Silo Beta - Feed Barley",
                grain_type="Barley",
                capacity_tons=750.0,
                current_fill_tons=420.0,
                location="Sector B - North Complex",
                status="Operational",
            ),
            StorageUnit(
                unit_id="silo-3",
                name="Silo Gamma - Yellow Corn",
                grain_type="Yellow Corn",
                capacity_tons=1000.0,
                current_fill_tons=610.0,
                location="Sector C - Rail Loading",
                status="Operational",
            ),
        ]
        db.add_all(default_units)
        db.flush()
        logger.info("Initialized 3 default storage units (silo-1, silo-2, silo-3).")


def _init_notification_config(db):
    """Ensures a default notification configuration row exists and schema columns are present."""
    try:
        from sqlalchemy import text
        conn = db.connection()
        col_tuples = conn.execute(text("PRAGMA table_info(notification_configs)")).fetchall()
        col_names = [c[1] for c in col_tuples]
        if "whatsapp_enabled" not in col_names:
            conn.execute(text("ALTER TABLE notification_configs ADD COLUMN whatsapp_enabled BOOLEAN DEFAULT 0"))
        if "whatsapp_phone" not in col_names:
            conn.execute(text("ALTER TABLE notification_configs ADD COLUMN whatsapp_phone VARCHAR(32) DEFAULT ''"))
        if "whatsapp_apikey" not in col_names:
            conn.execute(text("ALTER TABLE notification_configs ADD COLUMN whatsapp_apikey VARCHAR(64) DEFAULT ''"))
    except Exception as e:
        logger.warning(f"Could not auto-migrate notification_configs columns: {e}")

    config = db.query(NotificationConfig).first()
    if not config:
        default_config = NotificationConfig(
            email_enabled=False,
            email_recipients="",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="",
            smtp_password_env="SMTP_PASSWORD",
            telegram_enabled=False,
            telegram_bot_token_env="TELEGRAM_BOT_TOKEN",
            telegram_chat_id="",
            whatsapp_enabled=False,
            whatsapp_phone="",
            whatsapp_apikey="",
            min_risk_level="High",
            cooldown_minutes=15,
        )
        db.add(default_config)
        db.flush()
        logger.info("Initialized default notification settings.")


def _migrate_local_storage(db):
    """Migrates historical records from backend/data/local_storage.json into SQLite."""
    storage_json_path = os.path.join(DATA_DIR, "local_storage.json")
    if not os.path.exists(storage_json_path):
        return

    try:
        with open(storage_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Migrate predictions
        existing_pred_count = db.query(Prediction).count()
        if existing_pred_count == 0 and "predictions" in data:
            migrated_preds = []
            for item in data.get("predictions", []):
                p = item.get("data", item)
                ts_str = p.get("timestamp")
                ts = None
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        ts = _utcnow()
                proba = p.get("probabilities", {})
                recs = p.get("recommendations", [])
                snapshot = p.get("sensor_snapshot", {})

                pred_record = Prediction(
                    unit_id="silo-1",
                    timestamp=ts or _utcnow(),
                    risk_category=p.get("risk_category", "Low"),
                    confidence=float(p.get("confidence", 0.0)),
                    low_proba=float(proba.get("Low", 0.0)),
                    mod_proba=float(proba.get("Moderate", 0.0)),
                    high_proba=float(proba.get("High", 0.0)),
                    model_name=p.get("model_name", "artcn"),
                    alert=bool(p.get("alert", False)),
                    recommendations_json=json.dumps(recs),
                    sensor_snapshot_json=json.dumps(snapshot),
                )
                migrated_preds.append(pred_record)

            if migrated_preds:
                db.add_all(migrated_preds)
                logger.info(f"Migrated {len(migrated_preds)} predictions from local_storage.json to SQLite.")

        # 2. Migrate alerts
        existing_alert_count = db.query(Alert).count()
        if existing_alert_count == 0 and "alerts" in data:
            migrated_alerts = []
            for item in data.get("alerts", []):
                a = item.get("data", item)
                ts_str = a.get("timestamp")
                ts = None
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        ts = _utcnow()
                alert_record = Alert(
                    unit_id="silo-1",
                    timestamp=ts or _utcnow(),
                    level=a.get("level", "HIGH"),
                    message=a.get("message", "Environmental risk alert"),
                    details_json=json.dumps(a.get("details", {})),
                    acknowledged=bool(a.get("acknowledged", False)),
                )
                migrated_alerts.append(alert_record)

            if migrated_alerts:
                db.add_all(migrated_alerts)
                logger.info(f"Migrated {len(migrated_alerts)} alerts from local_storage.json to SQLite.")

    except Exception as e:
        logger.warning(f"Failed to migrate legacy local_storage.json (safe to continue): {e}")


def seed_sensor_readings(db):
    """Seeds baseline telemetry records if sensor_readings table is empty."""
    count = db.query(SensorReading).count()
    if count == 0:
        import random
        from datetime import timedelta
        now = _utcnow()
        readings = []
        for unit in ["silo-1", "silo-2", "silo-3"]:
            base_temp = 24.5 if unit == "silo-1" else (22.0 if unit == "silo-2" else 26.0)
            base_hum = 62.0 if unit == "silo-1" else (58.0 if unit == "silo-2" else 65.0)
            base_moist = 13.5 if unit == "silo-1" else (12.8 if unit == "silo-2" else 14.2)
            base_gas = 420.0 if unit == "silo-1" else (390.0 if unit == "silo-2" else 450.0)

            for i in range(50, -1, -1):
                t = now - timedelta(minutes=i * 5)
                readings.append(SensorReading(
                    unit_id=unit,
                    timestamp=t,
                    temperature_c=round(base_temp + random.uniform(-1.2, 1.2), 2),
                    humidity_pct=round(base_hum + random.uniform(-2.0, 2.0), 2),
                    gas_concentration=round(base_gas + random.uniform(-15.0, 15.0), 1),
                    grain_moisture=round(base_moist + random.uniform(-0.4, 0.4), 2),
                    storage_duration=round(14.0 + (50 - i) * 0.05, 2),
                    ext_temperature_c=round(base_temp + 2.5 + random.uniform(-1.0, 1.0), 2),
                    ventilation_status=1,
                    battery_voltage=3.62,
                    sensor_health=100,
                    is_simulated=True,
                    source="simulated_telemetry_replay"
                ))
        db.add_all(readings)
        db.flush()
        logger.info(f"Seeded {len(readings)} baseline telemetry records into sensor_readings.")


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
