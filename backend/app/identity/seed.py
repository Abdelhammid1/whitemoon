"""Seed baseline roles, permissions, and a bootstrap admin.

Idempotent — safe to re-run. Any role/permission already present is left
alone; a bootstrap admin is created only if no admin user exists.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import select

from ..extensions import db
from .models import Permission, Role, RolePermission, User, UserRole
from .services import passwords, rbac

# ---------------------------------------------------------------- catalogs

ROLES: tuple[tuple[str, str, str], ...] = (
    ("admin.high", "إدارة عليا", "Senior Admin"),
    ("admin", "مدير", "Admin"),
    ("staff", "موظف شركة", "Staff"),
    ("customer", "عميل", "Customer"),
    ("supplier", "مورد", "Supplier"),
    ("agent", "وكيل", "Agent"),
    ("branch", "فرع", "Branch"),
)

PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("*", "جميع الصلاحيات — تُمنح لحساب الإدارة العليا فقط"),
    ("user.read", "قراءة قائمة المستخدمين"),
    ("user.impersonate", "تمثيل مستخدم آخر (View as) للدعم الفني"),
    ("supplier.approve", "اعتماد أو رفض حساب مورد"),
    ("credit.override", "استثناء على السقف الائتماني"),
    ("credit.manage", "تسجيل سداد الذمم وإعادة احتساب التصنيف وتشغيل التصعيد"),
    ("payment.collect", "تحصيل سداد من عميل (وكيل/فرع/موظف)"),
    ("payment.approve", "اعتماد تحصيل السداد (مستوى واحد قبل الشركة)"),
    ("period.close", "إقفال فترة محاسبية"),
    ("period.reopen", "إعادة فتح فترة مُقفلة"),
    ("high.manual_journal", "قيد يدوي استثنائي"),
    ("high.manual_journal.closed_period", "قيد يدوي على فترة مُقفلة"),
    ("high.map.edit", "تعديل خريطة القيود"),
    ("admin.high", "صلاحية الإدارة العليا (تجميد حساب، تجاوز سقف…)"),
    # Inventory (EPIC 4)
    ("product.manage", "إدارة كتالوج المنتجات"),
    ("inventory.manage", "تعديل أرصدة المخزون وإصدار إذون التحويل"),
    ("offer.manage", "إدارة عروض المورد (المورد لعروضه فقط)"),
    ("shortage.resolve", "حسم النواقص وتحديد الطرف المسؤول"),
    # Commerce / orders (EPIC 3)
    ("order.manage", "إدارة الطلبات: عرض الكل، تأكيد، تجهيز، إلغاء"),
    # Partners (EPIC 6)
    ("partner.manage", "إدارة الوكلاء والفروع: التأمينات، الشروط، الاستحقاقات"),
    # Production (EPIC 7)
    ("production.manage", "إدارة أوامر التصنيع"),
    # POS (EPIC 8)
    ("pos.sell", "البيع عبر نقطة البيع"),
    ("pos.settle", "ترحيل تسوية مبيعات نقطة البيع"),
    # Logistics (EPIC 9)
    ("logistics.manage", "إدارة مواعيد التسليم والشحنات"),
    ("logistics.deliver", "مندوب التسليم: تحديث الموقع وتأكيد الاستلام"),
    # Communication (EPIC 10)
    ("comm.moderate", "مراقبة المحادثات وإنشاؤها والتدخل عند الحاجة"),
    # Cross-cutting
    ("bi.view", "عرض لوحة التحليلات التنفيذية"),
    ("notify.send", "إرسال إشعار لمستخدم"),
    ("assistant.use", "استخدام مساعد الذكاء الاصطناعي للمدير (قراءة وشرح فقط)"),
)

# role_code -> list of permission codes
ROLE_PERMS: dict[str, tuple[str, ...]] = {
    "admin.high": ("*",),
    "admin": (
        "user.read",
        "user.impersonate",
        "supplier.approve",
        "credit.manage",
        "partner.manage",
        "product.manage",
        "inventory.manage",
        "shortage.resolve",
        "order.manage",
        "production.manage",
        "pos.sell",
        "pos.settle",
        "logistics.manage",
        "logistics.deliver",
        "comm.moderate",
        "payment.collect",
        "payment.approve",
        "bi.view",
        "notify.send",
        "assistant.use",
    ),
    "staff": (
        "user.read",
        "product.manage",
        "inventory.manage",
        "order.manage",
        "production.manage",
        "pos.sell",
        "logistics.manage",
        "logistics.deliver",
        "payment.collect",
    ),
    "customer": (),
    "supplier": ("offer.manage",),
    "agent": ("pos.sell", "payment.collect", "payment.approve"),
    "branch": ("pos.sell", "payment.collect", "payment.approve"),
}


def seed_rbac() -> None:
    for code, ar, en in ROLES:
        exists = db.session.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
        if exists is None:
            db.session.add(Role(code=code, name_ar=ar, name_en=en, is_system=True))

    for code, desc in PERMISSIONS:
        exists = db.session.execute(
            select(Permission).where(Permission.code == code)
        ).scalar_one_or_none()
        if exists is None:
            db.session.add(Permission(code=code, description_ar=desc))

    db.session.flush()

    # Declarative reconcile: grant what ROLE_PERMS declares AND revoke any
    # grant it no longer declares. Add-only seeding would leave a stale
    # permission attached to a role after it's removed from the catalog
    # (privilege-revocation gap), so we prune here for every managed role.
    for role_code, perm_codes in ROLE_PERMS.items():
        role = db.session.execute(select(Role).where(Role.code == role_code)).scalar_one()
        desired_perm_ids: set[int] = set()
        for p_code in perm_codes:
            perm = db.session.execute(
                select(Permission).where(Permission.code == p_code)
            ).scalar_one()
            desired_perm_ids.add(perm.id)
            exists = db.session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            ).first()
            if exists is None:
                db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        current = db.session.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        ).scalars().all()
        for rp in current:
            if rp.permission_id not in desired_perm_ids:
                db.session.delete(rp)

    db.session.commit()


def seed_bootstrap_admin() -> User | None:
    """Create the bootstrap admin.high user only if NO admin already exists.

    Idempotency must not assume exactly one admin: the Users screen now lets
    staff add more admins, so an equality query like `scalar_one_or_none()`
    raises `MultipleResultsFound` once there are two. We only need *existence*,
    so limit to one row. We also never spawn a default-password admin when any
    admin (of any role count) is already present — a security precondition for
    re-running this against a live database.
    """
    stmt = (
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code == "admin.high")
        .limit(1)
    )
    if db.session.execute(stmt).first() is not None:
        return None
    # Belt-and-suspenders: also skip if any admin-kind user exists at all, so a
    # deployment with admins but (somehow) no admin.high role is never handed a
    # fresh default-password superadmin.
    if db.session.execute(select(User.id).where(User.kind == "admin").limit(1)).first() is not None:
        return None

    # Not a .local/.test address: those are special-use TLDs the email
    # validator rejects, which would make the seeded admin unable to log in.
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@whitemoon.eg")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMeNow!2026")

    admin = User(
        email=email,
        password_hash=passwords.hash_password(password),
        kind="admin",
        status="active",
        activated_at=datetime.now(UTC),
        email_verified_at=datetime.now(UTC),
    )
    db.session.add(admin)
    db.session.flush()
    rbac.assign_role(admin.id, "admin.high")
    db.session.commit()
    return admin


def run() -> None:
    # RBAC first and committed on its own, so a later problem creating the
    # bootstrap admin can never leave the system without roles/permissions.
    seed_rbac()  # commits internally
    try:
        admin = seed_bootstrap_admin()
    except Exception as exc:  # pragma: no cover - defensive; RBAC is already safe
        db.session.rollback()
        print(f"Bootstrap admin step failed ({exc!r}) — RBAC was seeded; continuing.")
        return
    if admin is not None:
        print(f"Bootstrap admin created (id={admin.id}, email={admin.email}).")
        print("Change the password immediately via /auth/login then your admin flow.")
    else:
        print("Bootstrap admin already exists — skipped.")
