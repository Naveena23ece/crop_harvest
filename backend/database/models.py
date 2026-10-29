"""
SQLAlchemy database models for GrainGuard AI.
Defines tables for RBAC, Storage Units, Telemetry, Predictions, Alerts, and Auditing.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.database.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default="viewer")  # "admin" or "viewer"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class StorageUnit(Base):
    __tablename__ = "storage_units"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(32), unique=True, index=True, nullable=False)  # e.g. "silo-1"
    name = Column(String(128), nullable=False)                            # e.g. "Main Silo - Wheat"
    grain_type = Column(String(64), nullable=False, default="Wheat")
    capacity_tons = Column(Float, nullable=False, default=500.0)
    current_fill_tons = Column(Float, nullable=False, default=320.0)
    location = Column(String(128), nullable=False, default="Sector A - Warehouse 1")
    status = Column(String(32), nullable=False, default="Operational")    # "Operational", "Maintenance", "Empty"
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "name": self.name,
            "grain_type": self.grain_type,
            "capacity_tons": self.capacity_tons,
            "current_fill_tons": self.current_fill_tons,
            "location": self.location,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(32), index=True, nullable=False, default="silo-1")
    timestamp = Column(DateTime, index=True, default=_utcnow, nullable=False)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    gas_concentration = Column(Float, nullable=True)
    grain_moisture = Column(Float, nullable=True)
    storage_duration = Column(Float, nullable=True)
    ext_temperature_c = Column(Float, nullable=True)
    ventilation_status = Column(Integer, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    sensor_health = Column(Integer, nullable=True)
    is_simulated = Column(Boolean, default=True, nullable=False)
    source = Column(String(64), default="simulated_telemetry_replay", nullable=False)

    __table_args__ = (
        Index("idx_sensor_unit_timestamp", "unit_id", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "gas_concentration": self.gas_concentration,
            "grain_moisture": self.grain_moisture,
            "storage_duration": self.storage_duration,
            "ext_temperature_c": self.ext_temperature_c,
            "ventilation_status": self.ventilation_status,
            "battery_voltage": self.battery_voltage,
            "sensor_health": self.sensor_health,
            "is_simulated": self.is_simulated,
            "source": self.source,
        }


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(32), index=True, nullable=False, default="silo-1")
    timestamp = Column(DateTime, index=True, default=_utcnow, nullable=False)
    risk_category = Column(String(16), nullable=False)   # "Low", "Moderate", "High"
    confidence = Column(Float, nullable=False)
    low_proba = Column(Float, nullable=True)
    mod_proba = Column(Float, nullable=True)
    high_proba = Column(Float, nullable=True)
    model_name = Column(String(32), default="artcn", nullable=False)
    alert = Column(Boolean, default=False, nullable=False)
    recommendations_json = Column(Text, nullable=True)
    sensor_snapshot_json = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_pred_unit_timestamp", "unit_id", "timestamp"),
    )

    def to_dict(self):
        recs = json.loads(self.recommendations_json) if self.recommendations_json else []
        snapshot = json.loads(self.sensor_snapshot_json) if self.sensor_snapshot_json else {}
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "risk_category": self.risk_category,
            "confidence": round(self.confidence, 4),
            "probabilities": {
                "Low": round(self.low_proba or 0.0, 4),
                "Moderate": round(self.mod_proba or 0.0, 4),
                "High": round(self.high_proba or 0.0, 4),
            },
            "model_name": self.model_name,
            "alert": self.alert,
            "recommendations": recs,
            "sensor_snapshot": snapshot,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(String(32), index=True, nullable=False, default="silo-1")
    timestamp = Column(DateTime, index=True, default=_utcnow, nullable=False)
    level = Column(String(16), nullable=False, default="HIGH")   # "INFO", "WARNING", "HIGH", "CRITICAL"
    message = Column(String(256), nullable=False)
    details_json = Column(Text, nullable=True)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String(64), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    def to_dict(self):
        details = json.loads(self.details_json) if self.details_json else {}
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "message": self.message,
            "details": details,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True)
    email_enabled = Column(Boolean, default=False, nullable=False)
    email_recipients = Column(String(512), default="", nullable=False)
    smtp_host = Column(String(128), default="smtp.gmail.com", nullable=False)
    smtp_port = Column(Integer, default=587, nullable=False)
    smtp_user = Column(String(128), default="", nullable=False)
    smtp_password_env = Column(String(64), default="SMTP_PASSWORD", nullable=False)
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    telegram_bot_token_env = Column(String(64), default="TELEGRAM_BOT_TOKEN", nullable=False)
    telegram_chat_id = Column(String(64), default="", nullable=False)
    min_risk_level = Column(String(16), default="High", nullable=False)
    cooldown_minutes = Column(Integer, default=15, nullable=False)
    last_sent_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "email_enabled": self.email_enabled,
            "email_recipients": self.email_recipients,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": self.smtp_user,
            "telegram_enabled": self.telegram_enabled,
            "telegram_chat_id": self.telegram_chat_id,
            "min_risk_level": self.min_risk_level,
            "cooldown_minutes": self.cooldown_minutes,
            "last_sent_at": self.last_sent_at.isoformat() if self.last_sent_at else None,
        }


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False)
    channel = Column(String(32), nullable=False)       # "email", "telegram"
    recipient = Column(String(128), nullable=False)
    subject = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False)        # "sent", "failed", "simulated", "cooldown_suppressed"
    error_message = Column(Text, nullable=True)
    alert_id = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "status": self.status,
            "error_message": self.error_message,
            "alert_id": self.alert_id,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=_utcnow, nullable=False)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), nullable=False, default="system")
    action = Column(String(64), nullable=False)        # "LOGIN", "SIGNUP", "UPDATE_THRESHOLD", "DELETE_USER", etc.
    resource = Column(String(128), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)

    def to_dict(self):
        details = json.loads(self.details_json) if self.details_json else {}
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "username": self.username,
            "action": self.action,
            "resource": self.resource,
            "details": details,
            "ip_address": self.ip_address,
        }


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, index=True, nullable=False)
    value = Column(String(256), nullable=False)
    description = Column(String(256), nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    updated_by = Column(String(64), default="system")
