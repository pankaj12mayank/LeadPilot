from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _smtp() -> dict:
    from backend.services import runtime_settings

    return runtime_settings.get_smtp()


def is_smtp_configured() -> bool:
    sm = _smtp()
    return bool(sm.get("host") and sm.get("email") and sm.get("password"))


def _compose_body(body: str) -> str:
    sig = str(_smtp().get("signature") or "") or ""
    if sig.strip():
        return f"{body.rstrip()}\n\n{sig.rstrip()}"
    return body


def send_html(
    to: str,
    subject: str,
    body_html: str,
    smtp_host: str,
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    from_email: str = "",
    from_name: str = "",
) -> bool:
    """Send HTML email with explicit SMTP config (used by subscription service)."""
    to = (to or "").strip()
    if not to:
        logger.warning("send_html: empty recipient")
        return False
    if not smtp_host:
        logger.warning("send_html: no SMTP host")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name or 'LeadPilot'} <{from_email}>"
    msg["To"] = to
    msg.set_content(body_html, subtype="html")
    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
                server.starttls(context=ssl.create_default_context())
                if smtp_user:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
        logger.info("send_html: sent to=%s subject=%s", to, subject)
        return True
    except Exception as e:
        logger.error("send_html: send failed: %s", e)
        return False


def send_email(
    to_address: str,
    subject: str,
    body: str,
    *,
    lead_id: Optional[str] = None,
    record_history: bool = True,
) -> bool:
    """
    Send via SMTP when configured; otherwise log stub.
    When lead_id is set and record_history True, writes email_history row.
    """
    to_address = (to_address or "").strip()
    if not to_address:
        logger.warning("send_email: empty recipient")
        return False

    full_body = _compose_body(body)
    sm = _smtp()
    sender_email = sm.get("sender_email") or ""
    sender_name = sm.get("sender_name") or "Lead Engine"

    if not is_smtp_configured():
        logger.info(
            "email_service: SMTP not configured; stub send to=%s subject=%s",
            to_address,
            subject,
        )
        if lead_id and record_history:
            from backend.services import email_history_service

            email_history_service.record(
                lead_id, to_address, subject, full_body, "skipped_no_smtp"
            )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_address
    msg.set_content(full_body)

    sm = _smtp()
    host = str(sm.get("host") or "")
    port = int(sm.get("port") or 587)
    user = str(sm.get("email") or "")
    password = str(sm.get("password") or "")
    use_tls = bool(sm.get("use_tls", True))

    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as server:
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
        logger.info("email_service: sent to=%s subject=%s", to_address, subject)
        if lead_id and record_history:
            from backend.services import email_history_service

            email_history_service.record(
                lead_id, to_address, subject, full_body, "sent"
            )
        return True
    except Exception as e:
        logger.error("email_service: send failed: %s", e)
        if lead_id and record_history:
            from backend.services import email_history_service

            email_history_service.record(
                lead_id, to_address, subject, full_body, f"failed:{type(e).__name__}"
            )
        return False
