"""OTP code generation, hashing, delivery, verification.

The code is HMAC-hashed before storage; plaintext never touches the DB.
Delivery goes through a pluggable provider: console in dev, SMS/WhatsApp
(Twilio) in prod — pickable via `OTP_PROVIDER` env var.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import desc, select

from ...common.errors import TooManyRequests, Unauthorized
from ...extensions import db
from ..models import OtpRequest, User
from ..providers.otp_provider import get_provider


@dataclass(frozen=True)
class OtpIssued:
    user_id: int
    channel: str
    expires_at: datetime
    # Only returned by the console provider for dev convenience; empty otherwise.
    debug_code: str | None


def _hash_code(code: str) -> str:
    secret = current_app.config["JWT_SECRET_KEY"].encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def _generate_code(length: int) -> str:
    pool = "0123456789"
    return "".join(secrets.choice(pool) for _ in range(length))


def issue(user: User, *, channel: str, purpose: str) -> OtpIssued:
    cfg = current_app.config
    length: int = cfg["OTP_LENGTH"]
    ttl: int = cfg["OTP_TTL_SECONDS"]

    code = _generate_code(length)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    db.session.add(
        OtpRequest(
            user_id=user.id,
            channel=channel,
            purpose=purpose,
            code_hash=_hash_code(code),
            expires_at=expires_at,
        )
    )
    db.session.flush()

    provider = get_provider(cfg["OTP_PROVIDER"])
    delivery_target = user.phone if channel in ("sms", "whatsapp") else user.email
    provider.send(channel=channel, target=delivery_target or "", code=code)

    return OtpIssued(
        user_id=user.id,
        channel=channel,
        expires_at=expires_at,
        debug_code=code if cfg["OTP_PROVIDER"] == "console" else None,
    )


def verify(user_id: int, *, channel: str, purpose: str, code: str) -> OtpRequest:
    cfg = current_app.config
    max_attempts: int = cfg["OTP_MAX_ATTEMPTS"]

    stmt = (
        select(OtpRequest)
        .where(
            OtpRequest.user_id == user_id,
            OtpRequest.channel == channel,
            OtpRequest.purpose == purpose,
            OtpRequest.consumed_at.is_(None),
        )
        .order_by(desc(OtpRequest.created_at))
        .limit(1)
    )
    req = db.session.execute(stmt).scalar_one_or_none()
    if req is None:
        raise Unauthorized("No active OTP", code="otp_not_found")

    if req.expires_at < datetime.now(UTC):
        raise Unauthorized("OTP expired", code="otp_expired")

    if req.attempts >= max_attempts:
        raise TooManyRequests("Too many attempts", code="otp_too_many_attempts")

    req.attempts = req.attempts + 1
    if not hmac.compare_digest(req.code_hash, _hash_code(code)):
        db.session.flush()
        raise Unauthorized("Wrong code", code="otp_mismatch")

    req.consumed_at = datetime.now(UTC)
    db.session.flush()
    return req
