"""
GrainGuard AI - External Notification Service
Supports Telegram Bot API and SMTP Email notifications.
Includes:
- Duplicate alert suppression and configurable cooldowns
- Safe error handling (never crashes prediction pipeline)
- Test notification endpoint
- Persistent delivery tracking in NotificationLog
- Clear reporting of simulated vs real delivery
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import urllib.request
import urllib.parse
import json

from backend.database.db import SessionLocal
from backend.database.models import NotificationConfig, NotificationLog

logger = logging.getLogger("grainguard.notifier")

# In-memory alert cooldown tracker: {f"{unit_id}_{risk_category}": last_sent_datetime}
_ALERT_COOLDOWNS: Dict[str, datetime] = {}

def _utcnow():
    return datetime.now(timezone.utc)

def get_notification_settings() -> Dict[str, Any]:
    """Retrieve notification configuration from DB with environment variable fallbacks."""
    settings = {
        "email_enabled": os.getenv("GRAINGUARD_EMAIL_ENABLED", "false").lower() == "true",
        "smtp_host": os.getenv("GRAINGUARD_SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("GRAINGUARD_SMTP_PORT", "587")),
        "smtp_user": os.getenv("GRAINGUARD_SMTP_USER", ""),
        "smtp_password": os.getenv("GRAINGUARD_SMTP_PASS", ""),
        "email_recipients": os.getenv("GRAINGUARD_EMAIL_RECIPIENTS", ""),
        "telegram_enabled": os.getenv("GRAINGUARD_TELEGRAM_ENABLED", "false").lower() == "true",
        "telegram_bot_token": os.getenv("GRAINGUARD_TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("GRAINGUARD_TELEGRAM_CHAT_ID", ""),
        "whatsapp_enabled": os.getenv("GRAINGUARD_WHATSAPP_ENABLED", "false").lower() == "true",
        "whatsapp_phone": os.getenv("GRAINGUARD_WHATSAPP_PHONE", ""),
        "whatsapp_apikey": os.getenv("GRAINGUARD_WHATSAPP_APIKEY", ""),
        "min_risk_level": os.getenv("GRAINGUARD_NOTIFY_MIN_RISK", "High"),
        "cooldown_minutes": int(os.getenv("GRAINGUARD_NOTIFY_COOLDOWN_MIN", "15")),
    }
    
    try:
        db = SessionLocal()
        db_config = db.query(NotificationConfig).first()
        if db_config:
            # Resolve secrets from environment if env var name is stored
            smtp_pass = os.getenv(db_config.smtp_password_env, settings["smtp_password"])
            tg_token = os.getenv(db_config.telegram_bot_token_env, settings["telegram_bot_token"])

            settings.update({
                "email_enabled": db_config.email_enabled,
                "smtp_host": db_config.smtp_host or settings["smtp_host"],
                "smtp_port": db_config.smtp_port or settings["smtp_port"],
                "smtp_user": db_config.smtp_user or settings["smtp_user"],
                "smtp_password": smtp_pass,
                "email_recipients": db_config.email_recipients or settings["email_recipients"],
                "telegram_enabled": db_config.telegram_enabled,
                "telegram_bot_token": tg_token,
                "telegram_chat_id": db_config.telegram_chat_id or settings["telegram_chat_id"],
                "min_risk_level": db_config.min_risk_level or settings["min_risk_level"],
                "cooldown_minutes": db_config.cooldown_minutes or settings["cooldown_minutes"],
            })
            if hasattr(db_config, "whatsapp_enabled") and db_config.whatsapp_enabled is not None:
                settings["whatsapp_enabled"] = db_config.whatsapp_enabled
            if hasattr(db_config, "whatsapp_phone") and db_config.whatsapp_phone:
                settings["whatsapp_phone"] = db_config.whatsapp_phone
            if hasattr(db_config, "whatsapp_apikey") and db_config.whatsapp_apikey:
                settings["whatsapp_apikey"] = db_config.whatsapp_apikey
        db.close()
    except Exception as e:
        logger.warning(f"Could not load NotificationConfig from DB: {e}")

    return settings

def is_in_cooldown(unit_id: str, risk_category: str, cooldown_minutes: int) -> bool:
    """Check if an alert for this unit and risk category was sent recently."""
    key = f"{unit_id}_{risk_category}"
    last_sent = _ALERT_COOLDOWNS.get(key)
    if not last_sent:
        return False
    if _utcnow() - last_sent < timedelta(minutes=cooldown_minutes):
        return True
    return False

def record_cooldown(unit_id: str, risk_category: str):
    key = f"{unit_id}_{risk_category}"
    _ALERT_COOLDOWNS[key] = _utcnow()

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> Dict[str, Any]:
    """Send message via Telegram Bot API."""
    if not bot_token or not chat_id:
        return {"success": False, "error": "Telegram Bot Token or Chat ID not configured"}
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return {"success": True, "message_id": data.get("result", {}).get("message_id")}
            return {"success": False, "error": data.get("description", "Unknown Telegram error")}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_smtp_email(server: str, port: int, user: str, password: str, recipients: str, subject: str, body: str) -> Dict[str, Any]:
    """Send notification email via SMTP."""
    if not server or not user or not password or not recipients:
        return {"success": False, "error": "SMTP server, credentials, or recipients missing"}
    
    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = recipients
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

        with smtplib.SMTP(server, port, timeout=10) as s:
            s.starttls()
            s.login(user, password)
            s.sendmail(user, recipient_list, msg.as_string())
        
        return {"success": True, "recipients": recipient_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_whatsapp_message(phone: str, apikey: str, message: str) -> Dict[str, Any]:
    """
    Send WhatsApp alert via CallMeBot free community API.
    CallMeBot sends direct WhatsApp messages via standard HTTPS GET.
    """
    if not phone or not apikey:
        return {"success": False, "error": "WhatsApp Phone Number or CallMeBot API Key not configured"}
    
    clean_phone = phone.strip().replace(" ", "").replace("-", "")
    if clean_phone.startswith("+"):
        clean_phone = clean_phone[1:]
    
    encoded_text = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_text}&apikey={apikey.strip()}"
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GrainGuard-AI/2.0 (Agricultural Storage DSS)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read().decode("utf-8")
            if "error" in body.lower() or "invalid" in body.lower():
                return {"success": False, "error": body.strip()}
            return {"success": True, "response": body.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def log_notification_attempt(channel: str, recipient: str, subject: str, status: str, error_msg: Optional[str] = None):
    """Safely log notification delivery attempt to SQLite database."""
    try:
        db = SessionLocal()
        log_entry = NotificationLog(
            timestamp=_utcnow(),
            channel=channel,
            recipient=recipient or "None",
            subject=subject,
            status=status,
            error_message=error_msg
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Failed to log notification attempt: {e}")

def dispatch_alert_notification(
    unit_id: str,
    unit_name: str,
    risk_category: str,
    confidence: float,
    readings: Dict[str, Any],
    recommendations: list,
    force: bool = False
) -> Dict[str, Any]:
    """
    Evaluate conditions, check cooldowns, format alert, and dispatch to configured channels.
    Never raises an unhandled exception.
    """
    settings = get_notification_settings()
    
    # Check minimum risk threshold
    risk_rank = {"Low": 1, "Moderate": 2, "High": 3}
    min_rank = risk_rank.get(settings["min_risk_level"], 3)
    curr_rank = risk_rank.get(risk_category, 1)

    if not force and curr_rank < min_rank:
        return {"dispatched": False, "reason": f"Risk level '{risk_category}' below threshold '{settings['min_risk_level']}'"}

    # Cooldown check
    if not force and is_in_cooldown(unit_id, risk_category, settings["cooldown_minutes"]):
        log_notification_attempt("suppressed", "system", f"Suppressed {risk_category} for {unit_id}", "cooldown_suppressed", "Duplicate alert suppressed within cooldown window")
        return {"dispatched": False, "reason": f"Duplicate alert suppressed (cooldown active for {unit_id})"}

    timestamp_str = _utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Format message
    temp = readings.get("temperature", readings.get("temperature_c", "N/A"))
    hum = readings.get("humidity", readings.get("humidity_pct", "N/A"))
    gas = readings.get("gas_concentration", "N/A")
    moist = readings.get("grain_moisture", "N/A")

    actions_text = "\n".join([f"- {rec}" for rec in recommendations[:3]]) if recommendations else "- Monitor storage conditions."

    message_body = (
        f"🚨 *GrainGuard AI Risk Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Storage Unit:* {unit_name} ({unit_id})\n"
        f"• *Risk Level:* {risk_category} ({confidence*100:.1f}% confidence)\n"
        f"• *Timestamp:* {timestamp_str}\n\n"
        f"📊 *Current Sensor Telemetry:*\n"
        f"• Temperature: {temp}°C\n"
        f"• Humidity: {hum}%\n"
        f"• CO2/Gas: {gas} ppm\n"
        f"• Moisture: {moist}%\n\n"
        f"💡 *Recommended Urgent Actions:*\n"
        f"{actions_text}\n\n"
        f"⚠️ _Note: Generated by GrainGuard AI Automated Risk Monitoring._"
    )

    results = {}

    # Telegram dispatch
    if settings["telegram_enabled"]:
        tg_res = send_telegram_message(
            settings["telegram_bot_token"],
            settings["telegram_chat_id"],
            message_body
        )
        results["telegram"] = tg_res
        log_notification_attempt(
            channel="telegram",
            recipient=settings["telegram_chat_id"],
            subject=f"GrainGuard Risk Alert: {risk_category}",
            status="sent" if tg_res["success"] else "failed",
            error_msg=tg_res.get("error")
        )

    # Email dispatch
    if settings["email_enabled"]:
        subject = f"[GrainGuard ALERT] {risk_category} detected in {unit_name}"
        em_res = send_smtp_email(
            settings["smtp_host"],
            settings["smtp_port"],
            settings["smtp_user"],
            settings["smtp_password"],
            settings["email_recipients"],
            subject,
            message_body
        )
        results["email"] = em_res
        log_notification_attempt(
            channel="email",
            recipient=settings["email_recipients"],
            subject=subject,
            status="sent" if em_res["success"] else "failed",
            error_msg=em_res.get("error")
        )

    # WhatsApp dispatch (CallMeBot)
    if settings["whatsapp_enabled"]:
        wa_res = send_whatsapp_message(
            settings["whatsapp_phone"],
            settings["whatsapp_apikey"],
            message_body
        )
        results["whatsapp"] = wa_res
        log_notification_attempt(
            channel="whatsapp",
            recipient=settings["whatsapp_phone"],
            subject=f"GrainGuard Risk Alert: {risk_category}",
            status="sent" if wa_res["success"] else "failed",
            error_msg=wa_res.get("error")
        )

    record_cooldown(unit_id, risk_category)
    return {
        "dispatched": True,
        "channels": results,
        "timestamp": timestamp_str
    }

def test_notification_channel(channel: str, test_target: Optional[str] = None) -> Dict[str, Any]:
    """Execute a safe test notification to verify integration credentials."""
    settings = get_notification_settings()
    test_msg = (
        f"🔔 *GrainGuard AI Notification Test*\n"
        f"Timestamp: {_utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Channel: {channel.upper()}\n"
        f"Status: Integration connection verified successfully."
    )

    if channel.lower() == "telegram":
        token = settings["telegram_bot_token"]
        chat = test_target or settings["telegram_chat_id"]
        if not token or not chat:
            log_notification_attempt("telegram", chat or "unconfigured", "Telegram Test", "failed", "Bot token or Chat ID not configured")
            return {
                "success": False,
                "error": "Telegram Bot Token or Chat ID is not configured. Configure them in Admin Settings or environment variables."
            }
        res = send_telegram_message(token, chat, test_msg)
        log_notification_attempt("telegram", chat, "Telegram Test", "sent" if res["success"] else "failed", res.get("error"))
        return res

    elif channel.lower() == "email":
        recipients = test_target or settings["email_recipients"]
        if not settings["smtp_user"] or not settings["smtp_password"] or not recipients:
            log_notification_attempt("email", recipients or "unconfigured", "Email Test", "failed", "SMTP credentials or recipients missing")
            return {
                "success": False,
                "error": "SMTP server, login credentials, or test recipient not configured."
            }
        res = send_smtp_email(
            settings["smtp_host"],
            settings["smtp_port"],
            settings["smtp_user"],
            settings["smtp_password"],
            recipients,
            "[GrainGuard AI] Notification Integration Test",
            test_msg
        )
        log_notification_attempt("email", recipients, "Email Test", "sent" if res["success"] else "failed", res.get("error"))
        return res

    elif channel.lower() == "whatsapp":
        phone = test_target or settings["whatsapp_phone"]
        apikey = settings["whatsapp_apikey"]
        if not phone or not apikey:
            log_notification_attempt("whatsapp", phone or "unconfigured", "WhatsApp Test", "failed", "WhatsApp Phone or API Key missing")
            return {
                "success": False,
                "error": "WhatsApp phone number or CallMeBot API Key is not configured. Configure GRAINGUARD_WHATSAPP_PHONE and GRAINGUARD_WHATSAPP_APIKEY."
            }
        res = send_whatsapp_message(phone, apikey, test_msg)
        log_notification_attempt("whatsapp", phone, "WhatsApp Test", "sent" if res["success"] else "failed", res.get("error"))
        return res

    return {"success": False, "error": f"Unsupported notification channel '{channel}'"}
