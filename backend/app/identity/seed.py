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
        "production.manage",
        "pos.sell",
        "pos.settle",
        "logistics.manage",
        "logistics.deliver",
    ),
    "staff": (
        "user.read",
        "product.manage",
        "inventory.manage",
        "production.manage",
        "pos.sell",
        "logistics.manage",
        "logistics.deliver",
    ),
    "customer": (),
    "supplier": ("offer.manage",),
    "agent": ("pos.sell",),
    "branch": ("pos.sell",),
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
    """Create an admin.high user if none exists. Credentials from env."""
    stmt = select(User).join(UserRole).join(Role).where(Role.code == "admin.high")
    existing = db.session.execute(stmt).scalar_one_or_none()
    if existing is not None:
        return None

    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@whitemoon.local")
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
    seed_rbac()
    admin = seed_bootstrap_admin()
    if admin is not None:
        print(f"Bootstrap admin created (id={admin.id}, email={admin.email}).")
        print("Change the password immediately via /auth/login then your admin flow.")
    else:
        print("Bootstrap admin already exists — skipped.")
