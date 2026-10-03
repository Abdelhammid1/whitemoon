"""Impersonation ("View as") — admin can act as any user for support.

Governed by permission `user.impersonate` plus a mandatory reason. Each
start AND stop writes to both `impersonation_grants` and `audit.events`.
Tokens carry both `sub` (effective user) and `act` (admin actor), so
every downstream audit event records who really did the thing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from flask_jwt_extended import create_access_token
from sqlalchemy import select

from ...common.errors import BadRequest, NotFound
from ...extensions import db
from ..models import ImpersonationGrant, User
from . import audit

MIN_REASON_LEN = 5


@dataclass(frozen=True)
class ImpersonationResult:
    grant_id: int
    access_token: str
    acting_as_user_id: int
    admin_user_id: int


def start(*, admin_user_id: int, target_user_id: int, reason: str) -> ImpersonationResult:
    if not reason or len(reason.strip()) < MIN_REASON_LEN:
        raise BadRequest(
            "Reason required (≥5 chars)", code="impersonation_reason_required"
        )
    target = db.session.get(User, target_user_id)
    if target is None:
        raise NotFound("Target user not found", code="target_not_found")

    grant = ImpersonationGrant(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        reason=reason.strip(),
    )
    db.session.add(grant)
    db.session.flush()

    audit.emit(
        "user.impersonate.start",
        actor_user_id=admin_user_id,
        target_type="user",
        target_id=target_user_id,
        reason=reason,
    )
    db.session.commit()

    token = create_access_token(
        identity=str(target_user_id),
        additional_claims={"act": admin_user_id, "imp": grant.id},
    )
    return ImpersonationResult(
        grant_id=grant.id,
        access_token=token,
        acting_as_user_id=target_user_id,
        admin_user_id=admin_user_id,
    )


def stop(*, admin_user_id: int, grant_id: int) -> None:
    grant = db.session.execute(
        select(ImpersonationGrant).where(
            ImpersonationGrant.id == grant_id,
            ImpersonationGrant.admin_user_id == admin_user_id,
            ImpersonationGrant.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if grant is None:
        raise NotFound("Active grant not found", code="grant_not_found")
    grant.revoked_at = datetime.now(UTC)
    audit.emit(
        "user.impersonate.stop",
        actor_user_id=admin_user_id,
        target_type="user",
        target_id=grant.target_user_id,
    )
    db.session.commit()
