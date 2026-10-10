"""/admin blueprint — supplier approval, impersonation, user search."""

from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, select

from ..audit.models import AuditEvent
from ..common.errors import BadRequest, Conflict, NotFound, Unauthorized
from ..common.money import to_money
from ..extensions import db
from ..identity.services.audit import emit as audit_emit
from .models import (
    ChannelPartnerProfile,
    CustomerProfile,
    Role,
    SupplierProfile,
    User,
    UserPermission,
    UserRole,
)
from .schemas import (
    AdminCreateUserIn,
    AdminUpdateUserProfileIn,
    ImpersonateStartIn,
    RejectSupplierIn,
)
from .services import impersonation as imp_svc
from .services import passwords
from .services import supplier_approval as supplier_svc
from .services.rbac import assign_role, require_permission

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _current_admin_id() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


@bp.post("/users")
@require_permission("admin.high")
def create_user():
    """Provision a user with any role from the admin console (T-07)."""
    body = request.get_json(silent=True) or {}
    try:
        payload = AdminCreateUserIn.model_validate(body)
    except Exception as e:
        raise BadRequest("Invalid payload", code="validation_error") from e
    if not payload.phone and not payload.email:
        raise BadRequest("مطلوب هاتف أو بريد", code="identifier_required")

    # Reject duplicate identifiers up front for a clean error.
    if payload.email and db.session.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none():
        raise Conflict("البريد مستخدم بالفعل", code="email_taken")
    if payload.phone and db.session.execute(
        select(User).where(User.phone == payload.phone)
    ).scalar_one_or_none():
        raise Conflict("الهاتف مستخدم بالفعل", code="phone_taken")

    # Every requested role must exist.
    for code in payload.roles:
        if db.session.execute(select(Role).where(Role.code == code)).scalar_one_or_none() is None:
            raise BadRequest(f"دور غير معروف: {code}", code="unknown_role")

    user = User(
        phone=payload.phone,
        email=payload.email,
        password_hash=passwords.hash_password(payload.password),
        kind=payload.kind,
        status=payload.status,
    )
    db.session.add(user)
    db.session.flush()

    # Minimal matching profile so downstream joins resolve.
    if payload.kind == "customer":
        db.session.add(
            CustomerProfile(
                user_id=user.id,
                display_name=payload.display_name,
                geo_area=payload.geo_area.strip() if payload.geo_area else None,
            )
        )
    elif payload.kind == "supplier":
        db.session.add(
            SupplierProfile(
                user_id=user.id,
                legal_name=payload.display_name,
                commercial_register_no="",
                tax_card_no="",
                national_id="",
                approval_status="approved",
            )
        )
    elif payload.kind in ("agent", "branch"):
        db.session.add(
            ChannelPartnerProfile(
                user_id=user.id, type=payload.kind, display_name=payload.display_name
            )
        )

    for code in payload.roles:
        assign_role(user.id, code)

    audit_emit(
        "admin.user.created",
        actor_user_id=_current_admin_id(),
        target_type="user",
        target_id=user.id,
        after={"kind": payload.kind, "roles": payload.roles, "status": payload.status},
    )
    db.session.commit()
    return jsonify(
        {"id": user.id, "kind": user.kind, "status": user.status, "roles": payload.roles}
    ), 201


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
    # Profile-level fields the admin can edit (T-01 / T-03).
    geo_area: str | None = None
    min_order_value: str | None = None
    if user.kind == "customer":
        cp = db.session.execute(
            select(CustomerProfile).where(CustomerProfile.user_id == user_id)
        ).scalar_one_or_none()
        geo_area = cp.geo_area if cp else None
    elif user.kind == "supplier":
        sp = db.session.execute(
            select(SupplierProfile).where(SupplierProfile.user_id == user_id)
        ).scalar_one_or_none()
        min_order_value = str(to_money(sp.min_order_value)) if sp else None
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
            "geo_area": geo_area,
            "min_order_value": min_order_value,
        }
    )


@bp.patch("/users/<int:user_id>")
@require_permission("admin.high")
def update_user_profile(user_id: int):
    """Edit profile-level fields: a customer's geo_area (T-01) or a supplier's
    min_order_value (T-03). Only the field matching the user's kind applies."""
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound("المستخدم غير موجود", code="user_not_found")
    body = request.get_json(silent=True) or {}
    try:
        payload = AdminUpdateUserProfileIn.model_validate(body)
    except Exception as e:
        raise BadRequest("Invalid payload", code="validation_error") from e

    changed: dict[str, object] = {}
    if payload.geo_area is not None:
        if user.kind != "customer":
            raise BadRequest("المنطقة الجغرافية للعملاء فقط", code="geo_area_customer_only")
        cp = db.session.execute(
            select(CustomerProfile).where(CustomerProfile.user_id == user_id)
        ).scalar_one_or_none()
        if cp is None:
            raise NotFound("ملف العميل غير موجود", code="customer_profile_not_found")
        cp.geo_area = payload.geo_area.strip() or None
        changed["geo_area"] = cp.geo_area
    if payload.min_order_value is not None:
        if user.kind != "supplier":
            raise BadRequest("الحد الأدنى للطلب للموردين فقط", code="min_order_supplier_only")
        sp = db.session.execute(
            select(SupplierProfile).where(SupplierProfile.user_id == user_id)
        ).scalar_one_or_none()
        if sp is None:
            raise NotFound("ملف المورد غير موجود", code="supplier_profile_not_found")
        sp.min_order_value = to_money(Decimal(str(payload.min_order_value)))
        changed["min_order_value"] = str(sp.min_order_value)
    if not changed:
        raise BadRequest("لا توجد تغييرات", code="no_changes")

    audit_emit(
        "admin.user.profile_updated",
        actor_user_id=_current_admin_id(),
        target_type="user",
        target_id=user_id,
        after=changed,
    )
    db.session.commit()
    return jsonify({"id": user_id, **changed})


@bp.get("/roles")
@require_permission("user.read")
def list_roles():
    """The assignable roles, from the identity.roles table — so the create-user
    form's options come from the DB, not a hand-maintained client list."""
    rows = db.session.execute(select(Role).order_by(Role.id)).scalars().all()
    return jsonify(
        {"items": [{"code": r.code, "name_ar": r.name_ar, "name_en": r.name_en} for r in rows]}
    )


@bp.get("/user-kinds")
@require_permission("user.read")
def list_user_kinds():
    """User kinds (code + Arabic label) — single source for the UI's pickers."""
    from .models import USER_KIND_LABELS, USER_KINDS

    return jsonify(
        {"items": [{"code": k, "label": USER_KIND_LABELS.get(k, k)} for k in USER_KINDS]}
    )


@bp.get("/user-statuses")
@require_permission("user.read")
def list_user_statuses():
    """Account statuses (code + Arabic label) — single source for the UI's filters."""
    from .models import USER_STATUS_LABELS, USER_STATUSES

    return jsonify(
        {"items": [{"code": s, "label": USER_STATUS_LABELS.get(s, s)} for s in USER_STATUSES]}
    )


def _user_labels(user_ids: set[int]) -> dict[int, str]:
    """Best human label for each user id: store/legal/partner name, else email,
    else phone, else #id. One batched pass (no N+1)."""
    ids = {i for i in user_ids if i}
    if not ids:
        return {}
    from ..identity.models import ChannelPartnerProfile, CustomerProfile, SupplierProfile, User

    cust: dict[int, str] = {
        uid: name
        for uid, name in db.session.execute(
            select(CustomerProfile.user_id, CustomerProfile.display_name).where(CustomerProfile.user_id.in_(ids))
        )
    }
    supp: dict[int, str] = {
        uid: name
        for uid, name in db.session.execute(
            select(SupplierProfile.user_id, SupplierProfile.legal_name).where(SupplierProfile.user_id.in_(ids))
        )
    }
    part: dict[int, str] = {
        uid: name
        for uid, name in db.session.execute(
            select(ChannelPartnerProfile.user_id, ChannelPartnerProfile.display_name).where(ChannelPartnerProfile.user_id.in_(ids))
        )
    }
    labels: dict[int, str] = {}
    for u in db.session.execute(select(User).where(User.id.in_(ids))).scalars():
        labels[u.id] = cust.get(u.id) or supp.get(u.id) or part.get(u.id) or u.email or u.phone or f"#{u.id}"
    return labels


def _os_from_ua(ua: str | None) -> str | None:
    """Short OS/platform label from a User-Agent string."""
    if not ua:
        return None
    s = ua.lower()
    if "windows" in s:
        return "Windows"
    if "iphone" in s or "ipad" in s or "ios" in s:
        return "iOS"
    if "android" in s:
        return "Android"
    if "mac os" in s or "macintosh" in s:
        return "macOS"
    if "linux" in s:
        return "Linux"
    return "غير معروف"


@bp.get("/audit")
@require_permission("admin.high")
def list_audit():
    action = request.args.get("action")
    limit = min(int(request.args.get("limit", "100")), 500)
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    rows = db.session.execute(stmt).scalars().all()

    # Resolve actor + (user-)target ids to names in one batch.
    ref_ids: set[int] = set()
    for e in rows:
        if e.actor_user_id:
            ref_ids.add(e.actor_user_id)
        if e.target_type == "user" and e.target_id and e.target_id.isdigit():
            ref_ids.add(int(e.target_id))
    labels = _user_labels(ref_ids)

    def _target_name(e: AuditEvent) -> str | None:
        if e.target_type == "user" and e.target_id and e.target_id.isdigit():
            return labels.get(int(e.target_id))
        return None

    return jsonify(
        {
            "items": [
                {
                    "id": e.id,
                    "at": e.at.isoformat(),
                    "actor_user_id": e.actor_user_id,
                    "actor_name": labels.get(e.actor_user_id) if e.actor_user_id else None,
                    "action": e.action,
                    "target_type": e.target_type,
                    "target_id": e.target_id,
                    "target_name": _target_name(e),
                    "reason": e.reason,
                    "ip": e.ip,
                    "user_agent": e.user_agent,
                    "os": _os_from_ua(e.user_agent),
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


# ---------------------------------------------------------------- per-user permission delegation

# Permissions an admin may delegate to a specific user (curated — not every code).
DELEGATABLE_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("deferred.settings.manage", "إدارة إعدادات البيع الآجل"),
)


@bp.get("/users/<int:user_id>/permissions")
@require_permission("admin.high")
def get_user_permissions(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound("المستخدم غير موجود", code="user_not_found")
    direct = list(
        db.session.execute(
            select(UserPermission.permission_code).where(UserPermission.user_id == user_id)
        ).scalars()
    )
    return jsonify(
        {
            "direct": direct,
            "delegatable": [{"code": c, "label": lbl} for c, lbl in DELEGATABLE_PERMISSIONS],
        }
    )


@bp.post("/users/<int:user_id>/permissions")
@require_permission("admin.high")
def grant_user_permission(user_id: int):
    code = (request.get_json(silent=True) or {}).get("code")
    if code not in {c for c, _ in DELEGATABLE_PERMISSIONS}:
        raise BadRequest("صلاحية غير قابلة للتفويض", code="not_delegatable")
    if db.session.get(User, user_id) is None:
        raise NotFound("المستخدم غير موجود", code="user_not_found")
    existing = db.session.execute(
        select(UserPermission.id).where(
            UserPermission.user_id == user_id, UserPermission.permission_code == code
        )
    ).first()
    if existing is None:
        db.session.add(
            UserPermission(user_id=user_id, permission_code=code, granted_by=_current_admin_id())
        )
        audit_emit(
            "user.permission.grant", actor_user_id=_current_admin_id(),
            target_type="user", target_id=user_id, reason=code,
        )
        db.session.commit()
    return jsonify({"user_id": user_id, "code": code, "granted": True})


@bp.delete("/users/<int:user_id>/permissions/<code>")
@require_permission("admin.high")
def revoke_user_permission(user_id: int, code: str):
    row = db.session.execute(
        select(UserPermission).where(
            UserPermission.user_id == user_id, UserPermission.permission_code == code
        )
    ).scalar_one_or_none()
    if row is not None:
        db.session.delete(row)
        audit_emit(
            "user.permission.revoke", actor_user_id=_current_admin_id(),
            target_type="user", target_id=user_id, reason=code,
        )
        db.session.commit()
    return jsonify({"user_id": user_id, "code": code, "granted": False})
