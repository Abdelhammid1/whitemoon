"""/admin blueprint — supplier approval, impersonation, user search."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, select

from ..audit.models import AuditEvent
from ..common.errors import BadRequest, NotFound, Unauthorized
from ..extensions import db
from .models import Role, SupplierProfile, User, UserRole
from .schemas import ImpersonateStartIn, RejectSupplierIn
from .services import impersonation as imp_svc
from .services import supplier_approval as supplier_svc
from .services.rbac import require_permission

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _current_admin_id() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


@bp.get("/users")
@require_permission("user.read")
def list_users():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind")
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", "50")), 200)

    stmt = select(User).limit(limit).order_by(User.id.desc())
    if kind:
        stmt = stmt.where(User.kind == kind)
    if status:
        stmt = stmt.where(User.status == status)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(User.phone.ilike(pattern), User.email.ilike(pattern)))

    users = db.session.execute(stmt).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": u.id,
                    "phone": u.phone,
                    "email": u.email,
                    "kind": u.kind,
                    "status": u.status,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
        }
    )


@bp.get("/users/<int:user_id>")
@require_permission("user.read")
def get_user(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound("المستخدم غير موجود", code="user_not_found")
    role_codes = list(
        db.session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        ).scalars()
    )
    return jsonify(
        {
            "id": user.id,
            "phone": user.phone,
            "email": user.email,
            "kind": user.kind,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "activated_at": user.activated_at.isoformat() if user.activated_at else None,
            "roles": role_codes,
        }
    )


@bp.get("/audit")
@require_permission("user.read")
def list_audit():
    action = request.args.get("action")
    limit = min(int(request.args.get("limit", "100")), 500)
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    rows = db.session.execute(stmt).scalars().all()
    return jsonify(
        {
            "items": [
                {
                    "id": e.id,
                    "at": e.at.isoformat(),
                    "actor_user_id": e.actor_user_id,
                    "action": e.action,
                    "target_type": e.target_type,
                    "target_id": e.target_id,
                    "reason": e.reason,
                }
                for e in rows
            ]
        }
    )


@bp.post("/suppliers/<int:user_id>/approve")
@require_permission("supplier.approve")
def approve_supplier(user_id: int):
    admin_id = _current_admin_id()
    user = supplier_svc.approve(admin_user_id=admin_id, user_id=user_id)
    return jsonify({"user_id": user.id, "status": user.status})


@bp.post("/suppliers/<int:user_id>/reject")
@require_permission("supplier.approve")
def reject_supplier(user_id: int):
    body = request.get_json(silent=True) or {}
    try:
        payload = RejectSupplierIn.model_validate(body)
    except Exception as e:
        raise BadRequest("Invalid payload", code="validation_error") from e
    admin_id = _current_admin_id()
    user = supplier_svc.reject(
        admin_user_id=admin_id, user_id=user_id, reason=payload.reason
    )
    return jsonify({"user_id": user.id, "status": user.status})


@bp.get("/suppliers/pending")
@require_permission("supplier.approve")
def pending_suppliers():
    stmt = (
        select(User, SupplierProfile)
        .join(SupplierProfile, SupplierProfile.user_id == User.id)
        .where(SupplierProfile.approval_status == "pending")
    )
    rows = db.session.execute(stmt).all()
    return jsonify(
        {
            "items": [
                {
                    "user_id": u.id,
                    "legal_name": p.legal_name,
                    "commercial_register_no": p.commercial_register_no,
                    "tax_card_no": p.tax_card_no,
                    "national_id": p.national_id,
                    "created_at": u.created_at.isoformat(),
                }
                for (u, p) in rows
            ],
        }
    )


@bp.post("/impersonate/start")
@require_permission("user.impersonate")
def impersonate_start():
    body = request.get_json(silent=True) or {}
    try:
        payload = ImpersonateStartIn.model_validate(body)
    except Exception as e:
        raise BadRequest("Invalid payload", code="validation_error") from e
    admin_id = _current_admin_id()
    result = imp_svc.start(
        admin_user_id=admin_id,
        target_user_id=payload.target_user_id,
        reason=payload.reason,
    )
    return jsonify(
        {
            "grant_id": result.grant_id,
            "access_token": result.access_token,
            "acting_as_user_id": result.acting_as_user_id,
            "admin_user_id": result.admin_user_id,
        }
    )


@bp.post("/impersonate/<int:grant_id>/stop")
@require_permission("user.impersonate")
def impersonate_stop(grant_id: int):
    admin_id = _current_admin_id()
    imp_svc.stop(admin_user_id=admin_id, grant_id=grant_id)
    return jsonify({"status": "stopped"})
