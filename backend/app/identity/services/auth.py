"""Registration, OTP flow, login (optionally 2FA-gated), refresh, logout.

Rules enforced here:
- Customer accounts activate when OTP verifies successfully.
- Supplier accounts stay in `pending` until admin approves (US-1.3).
- Agents and admins must present a valid TOTP code at login once enrolled.
- JWT access + refresh tokens are issued; a `sessions` row tracks each JTI
  so logout and revocation work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
)
from sqlalchemy import or_, select

from ...common.errors import BadRequest, Conflict, Forbidden, NotFound, Unauthorized
from ...extensions import db
from ..models import (
    ChannelPartnerProfile,
    CustomerProfile,
    Session,
    SupplierProfile,
    User,
)
from ...settings import service as settings
from . import audit, passwords, rbac
from . import otp as otp_svc
from . import totp as totp_svc

# T-46: «تذكرني على هذا الجهاز» is available only to these account kinds. Admin,
# staff, agent and branch always re-authenticate (and keep 2FA) to protect the
# high-privilege flows they can reach.
REMEMBER_ELIGIBLE_KINDS = ("customer", "supplier")

# ---------------------------------------------------------------- registration


@dataclass
class RegistrationResult:
    user_id: int
    status: str
    channel: str
    otp_expires_at: datetime
    otp_debug_code: str | None


def register_customer(
    *, phone: str | None, email: str | None, password: str, display_name: str
) -> RegistrationResult:
    _require_identifier(phone, email)
    _require_available(phone, email)

    user = User(
        phone=phone,
        email=email,
        password_hash=passwords.hash_password(password),
        kind="customer",
        status="pending",
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(CustomerProfile(user_id=user.id, display_name=display_name))
    rbac.assign_role(user.id, "customer")

    issued = _issue_registration_otp(user)
    audit.emit(
        "user.register", actor_user_id=user.id, target_type="user", target_id=user.id
    )
    db.session.commit()
    return RegistrationResult(
        user_id=user.id,
        status=user.status,
        channel=issued.channel,
        otp_expires_at=issued.expires_at,
        otp_debug_code=issued.debug_code,
    )


def register_supplier(
    *,
    phone: str | None,
    email: str | None,
    password: str,
    legal_name: str,
    commercial_register_no: str,
    tax_card_no: str,
    national_id: str,
) -> RegistrationResult:
    _require_identifier(phone, email)
    _require_available(phone, email)

    user = User(
        phone=phone,
        email=email,
        password_hash=passwords.hash_password(password),
        kind="supplier",
        status="pending",
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(
        SupplierProfile(
            user_id=user.id,
            legal_name=legal_name,
            commercial_register_no=commercial_register_no,
            tax_card_no=tax_card_no,
            national_id=national_id,
        )
    )
    rbac.assign_role(user.id, "supplier")

    issued = _issue_registration_otp(user)
    audit.emit(
        "supplier.register",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
    )
    db.session.commit()
    return RegistrationResult(
        user_id=user.id,
        status=user.status,
        channel=issued.channel,
        otp_expires_at=issued.expires_at,
        otp_debug_code=issued.debug_code,
    )


def _issue_registration_otp(user: User) -> otp_svc.OtpIssued:
    channel = "sms" if user.phone else "email"
    return otp_svc.issue(user, channel=channel, purpose="register")


def _require_identifier(phone: str | None, email: str | None) -> None:
    if not phone and not email:
        raise BadRequest(
            "Provide phone or email", code="identifier_required"
        )


def _require_available(phone: str | None, email: str | None) -> None:
    clauses: list[Any] = []
    if phone:
        clauses.append(User.phone == phone)
    if email:
        clauses.append(User.email == email)
    stmt = select(User).where(or_(*clauses))
    if db.session.execute(stmt).first() is not None:
        raise Conflict("Account already exists", code="user_exists")


# ---------------------------------------------------------------- OTP verify


def verify_registration_otp(*, user_id: int, code: str) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound("User not found", code="user_not_found")

    channel = "sms" if user.phone else "email"
    otp_svc.verify(user_id, channel=channel, purpose="register", code=code)

    now = datetime.now(UTC)
    if channel == "sms":
        user.phone_verified_at = now
    else:
        user.email_verified_at = now

    # Customer: activate immediately. Supplier: still pending admin approval.
    if user.kind == "customer":
        user.status = "active"
        user.activated_at = now
    audit.emit(
        "user.otp.verify",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
    )
    db.session.commit()
    return user


# ---------------------------------------------------------------- login


@dataclass
class LoginResult:
    user_id: int
    access_token: str
    refresh_token: str
    requires_2fa: bool
    remembered: bool = False


def login(
    *, phone: str | None, email: str | None, password: str, totp_code: str | None,
    remember_me: bool = False,
) -> LoginResult:
    if not phone and not email:
        raise BadRequest("Provide phone or email", code="identifier_required")
    clauses: list[Any] = []
    if phone:
        clauses.append(User.phone == phone)
    if email:
        clauses.append(User.email == email)
    stmt = select(User).where(or_(*clauses))
    user = db.session.execute(stmt).scalar_one_or_none()
    if user is None or not passwords.verify_password(user.password_hash, password):
        raise Unauthorized("Invalid credentials", code="bad_credentials")

    if user.status != "active":
        raise Forbidden(
            f"Account not active (status={user.status})",
            code="account_not_active",
        )

    # 2FA mandatory for admin, staff, agent — these roles touch sensitive flows.
    if user.kind in ("admin", "staff", "agent"):
        if not totp_svc.is_enrolled(user.id):
            # First login after promotion: tokens still issue but caller
            # is told to immediately enroll.
            pass
        else:
            if not totp_code:
                return LoginResult(
                    user_id=user.id, access_token="", refresh_token="", requires_2fa=True
                )
            if not totp_svc.verify(user.id, totp_code):
                raise Unauthorized("Invalid 2FA code", code="totp_invalid")

    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # T-46: only customer/supplier may keep a long-lived "remembered" session.
    remembered = remember_me and user.kind in REMEMBER_ELIGIBLE_KINDS
    access = create_access_token(identity=str(user.id))
    if remembered:
        refresh = create_refresh_token(
            identity=str(user.id),
            expires_delta=timedelta(days=settings.get_int("auth.remember_me_days")),
        )
    else:
        refresh = create_refresh_token(identity=str(user.id))
    _record_session(user.id, access, kind="access")
    _record_session(user.id, refresh, kind="refresh", remembered=remembered)

    audit.emit(
        "user.login", actor_user_id=user.id, target_type="user", target_id=user.id
    )
    if remembered:
        audit.emit(
            "auth.device_remembered", actor_user_id=user.id, target_type="user", target_id=user.id
        )
    db.session.commit()
    return LoginResult(
        user_id=user.id,
        access_token=access,
        refresh_token=refresh,
        requires_2fa=False,
        remembered=remembered,
    )


def _record_session(user_id: int, token: str, *, kind: str, remembered: bool = False) -> None:
    claims = decode_token(token)
    exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
    db.session.add(
        Session(
            user_id=user_id,
            jwt_jti=claims["jti"],
            kind=kind,
            device=request.headers.get("User-Agent"),
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
            expires_at=exp,
            remembered=remembered,
        )
    )


# ---------------------------------------------------------------- logout + refresh


def logout_current() -> None:
    claims = get_jwt()
    jti = claims["jti"]
    row = db.session.execute(
        select(Session).where(Session.jwt_jti == jti)
    ).scalar_one_or_none()
    if row is not None:
        row.revoked_at = datetime.now(UTC)
        db.session.commit()


def change_password(
    *, user_id: int, current_password: str, new_password: str, keep_jti: str | None = None
) -> None:
    """Self-service password change for any authenticated user. Verifies the
    current password, requires the new one to differ, then revokes every other
    active session so other devices must sign in again (the caller's own session
    — `keep_jti` — is left valid so they stay logged in)."""
    user = db.session.get(User, user_id)
    if user is None:
        raise Unauthorized("User not found", code="user_not_found")
    if not passwords.verify_password(user.password_hash, current_password):
        raise Unauthorized("كلمة المرور الحالية غير صحيحة", code="wrong_current_password")
    if passwords.verify_password(user.password_hash, new_password):
        raise BadRequest("كلمة المرور الجديدة يجب أن تختلف عن الحالية", code="password_unchanged")

    user.password_hash = passwords.hash_password(new_password)
    others = db.session.execute(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    ).scalars().all()
    now = datetime.now(UTC)
    for s in others:
        if keep_jti is None or s.jwt_jti != keep_jti:
            s.revoked_at = now
    audit.emit("auth.password_changed", actor_user_id=user_id, target_type="user", target_id=user_id)
    db.session.commit()


def refresh_current() -> str:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    user_id = int(raw)
    # Advance last_used_at on the refresh session doing the refresh (T-46), so
    # «أجهزتي» can show recency.
    jti = get_jwt().get("jti")
    if jti:
        row = db.session.execute(
            select(Session).where(Session.jwt_jti == jti)
        ).scalar_one_or_none()
        if row is not None:
            row.last_used_at = datetime.now(UTC)
    access = create_access_token(identity=str(user_id))
    _record_session(user_id, access, kind="access")
    db.session.commit()
    return access


# ---------------------------------------------------------------- T-46 devices


def verify_password_or_raise(user_id: int, password: str) -> None:
    """Step-up check for sensitive operations (T-46): re-verify the user's
    password even on a remembered device. Raises on mismatch."""
    user = db.session.get(User, user_id)
    if user is None or not passwords.verify_password(user.password_hash, password):
        raise Unauthorized("كلمة المرور غير صحيحة", code="password_reauth_failed")


def list_devices(user_id: int) -> list[dict[str, Any]]:
    """The user's active remembered devices for «أجهزتي» — a remembered refresh
    session that is neither revoked nor expired."""
    now = datetime.now(UTC)
    rows = db.session.execute(
        select(Session)
        .where(
            Session.user_id == user_id,
            Session.kind == "refresh",
            Session.remembered.is_(True),
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        )
        .order_by(Session.issued_at.desc())
    ).scalars().all()
    return [
        {
            "id": s.id,
            "device": s.device,
            "ip": s.ip,
            "issued_at": s.issued_at.isoformat() if s.issued_at else None,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        }
        for s in rows
    ]


def revoke_device(*, user_id: int, session_id: int) -> None:
    row = db.session.get(Session, session_id)
    if row is None or row.user_id != user_id:
        raise NotFound("Device not found", code="device_not_found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        audit.emit(
            "auth.device_revoked", actor_user_id=user_id, target_type="session", target_id=session_id
        )
        db.session.commit()


def revoke_all_devices(*, user_id: int, keep_jti: str | None = None) -> int:
    """Revoke every remembered device (optionally keeping the caller's own
    session). Returns how many were revoked."""
    rows = db.session.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.kind == "refresh",
            Session.remembered.is_(True),
            Session.revoked_at.is_(None),
        )
    ).scalars().all()
    now = datetime.now(UTC)
    n = 0
    for s in rows:
        if keep_jti is not None and s.jwt_jti == keep_jti:
            continue
        s.revoked_at = now
        n += 1
    if n:
        audit.emit(
            "auth.devices_revoked_all", actor_user_id=user_id, target_type="user", target_id=user_id
        )
        db.session.commit()
    return n


def is_token_revoked(jti: str) -> bool:
    row = db.session.execute(
        select(Session).where(Session.jwt_jti == jti)
    ).scalar_one_or_none()
    return row is not None and row.revoked_at is not None


# ---------------------------------------------------------------- misc helpers


def user_summary(user: User) -> dict[str, Any]:
    from .rbac import get_user_permissions

    return {
        "id": user.id,
        "kind": user.kind,
        "status": user.status,
        "phone": user.phone,
        "email": user.email,
        "locale": user.locale,
        # Effective permission codes (role grants + direct delegation), so the
        # UI can gate capability-based screens/nav without hardcoding roles.
        "permissions": sorted(get_user_permissions(user.id)),
    }


_ = ChannelPartnerProfile  # keep import for alembic autogen; unused directly here
_ = current_app  # pragma: no cover
