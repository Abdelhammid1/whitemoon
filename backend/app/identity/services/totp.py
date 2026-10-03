"""Time-based OTP (RFC 6238) 2FA for admin and agent accounts.

- `start_enrollment` returns the shared secret + an otpauth URI so an app
  like Google Authenticator can scan a QR.
- `finish_enrollment` requires one valid TOTP code to confirm the user set
  up their app correctly before 2FA is activated.
- `verify` checks a code at login (within a +-1 window).
- Backup codes are issued once at enrollment, hashed, and marked `used_at`
  when a code is consumed.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

import pyotp
from flask import current_app
from sqlalchemy import select

from ...common.errors import BadRequest, Unauthorized
from ...extensions import db
from ..models import BackupCode, TotpSecret, User


@dataclass(frozen=True)
class EnrollmentStart:
    secret: str
    otpauth_uri: str
    backup_codes: list[str]


def _hash_backup(code: str) -> str:
    secret = current_app.config["JWT_SECRET_KEY"].encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def start_enrollment(user: User) -> EnrollmentStart:
    secret = pyotp.random_base32()
    issuer = current_app.config["TOTP_ISSUER"]
    label = user.email or user.phone or f"user-{user.id}"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)

    existing = db.session.get(TotpSecret, user.id)
    if existing is None:
        db.session.add(TotpSecret(user_id=user.id, secret=secret))
    else:
        existing.secret = secret
        existing.enrolled_at = None

    # Fresh backup codes — invalidate any prior ones.
    db.session.query(BackupCode).filter(BackupCode.user_id == user.id).delete()
    backups = [secrets.token_hex(5).upper() for _ in range(8)]
    for raw in backups:
        db.session.add(BackupCode(user_id=user.id, code_hash=_hash_backup(raw)))

    db.session.flush()
    return EnrollmentStart(secret=secret, otpauth_uri=uri, backup_codes=backups)


def finish_enrollment(user: User, code: str) -> None:
    row = db.session.get(TotpSecret, user.id)
    if row is None:
        raise BadRequest("Enrollment not started", code="totp_not_started")
    if not pyotp.TOTP(row.secret).verify(code, valid_window=1):
        raise Unauthorized("Invalid TOTP", code="totp_invalid")
    row.enrolled_at = datetime.now(UTC)
    row.last_used_at = datetime.now(UTC)
    db.session.flush()


def is_enrolled(user_id: int) -> bool:
    row = db.session.get(TotpSecret, user_id)
    return row is not None and row.enrolled_at is not None


def verify(user_id: int, code: str) -> bool:
    row = db.session.get(TotpSecret, user_id)
    if row is None or row.enrolled_at is None:
        return False
    # Normal TOTP
    if pyotp.TOTP(row.secret).verify(code, valid_window=1):
        row.last_used_at = datetime.now(UTC)
        db.session.flush()
        return True
    # Backup code fallback
    stmt = select(BackupCode).where(
        BackupCode.user_id == user_id,
        BackupCode.code_hash == _hash_backup(code.upper()),
        BackupCode.used_at.is_(None),
    )
    bc = db.session.execute(stmt).scalar_one_or_none()
    if bc is None:
        return False
    bc.used_at = datetime.now(UTC)
    db.session.flush()
    return True
