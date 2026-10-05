"""External notification delivery (SMS / WhatsApp / e-mail).

Each channel sends for real when its provider is configured via environment
variables, and otherwise gracefully no-ops (returns False) — so the system
works end-to-end today and starts delivering the moment credentials are added,
with no code change. Delivery never raises: a provider failure must not break
the transaction that created the notification.

Env (matches .env.example):
  SMS / WhatsApp (Twilio): TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_SMS_FROM (SMS sender), TWILIO_WHATSAPP_FROM (WhatsApp sender).
  E-mail (SMTP): SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM, SMTP_STARTTLS (default true).
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger(__name__)


def _twilio_send(*, to: str, body: str, whatsapp: bool = False) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    frm = (
        os.getenv("TWILIO_WHATSAPP_FROM")
        if whatsapp
        else (os.getenv("TWILIO_SMS_FROM") or os.getenv("TWILIO_FROM"))
    )
    if not (sid and token and frm):
        return False  # not configured → graceful no-op
    try:
        from twilio.rest import Client  # lazy: optional dependency
    except ImportError:
        log.warning("twilio package not installed; %s not sent", "WhatsApp" if whatsapp else "SMS")
        return False
    try:
        client = Client(sid, token)
        to_fmt = f"whatsapp:{to}" if whatsapp else to
        frm_fmt = frm if frm.startswith("whatsapp:") or not whatsapp else f"whatsapp:{frm}"
        client.messages.create(to=to_fmt, from_=frm_fmt, body=body)
        return True
    except Exception:
        log.exception("Twilio send failed")
        return False


def _email_send(*, to: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        return False  # not configured → graceful no-op
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pw = os.getenv("SMTP_PASSWORD")
    frm = os.getenv("SMTP_FROM", user or "no-reply@whitemoon.local")
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = frm
        msg["To"] = to
        msg.set_content(body)
        starttls = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.ehlo()
            if starttls:
                # Fail closed: if TLS was requested it must succeed (any error
                # propagates to the outer handler → returns False), and the
                # server certificate is verified.
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
            if user and pw:
                # Never put credentials on the wire without TLS.
                if not starttls:
                    raise RuntimeError("Refusing to send SMTP credentials without STARTTLS")
                s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception:
        log.exception("SMTP send failed")
        return False


def deliver(*, channel: str, target: str | None, title: str, body: str | None) -> bool:
    """Send one notification on an external channel. Returns True only if it was
    actually dispatched; False when unconfigured, no target, or on error. Never
    raises. `in_app` is stored, not delivered here, so it returns False."""
    if not target:
        return False
    text = title if not body else f"{title}\n{body}"
    if channel == "sms":
        return _twilio_send(to=target, body=text)
    if channel == "whatsapp":
        return _twilio_send(to=target, body=text, whatsapp=True)
    if channel == "email":
        return _email_send(to=target, subject=title, body=body or title)
    return False
