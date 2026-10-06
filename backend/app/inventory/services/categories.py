"""Admin-managed product categories (T-15).

The categories table is the source of truth for the product taxonomy; the
hardcoded CATEGORIES tuple is kept only as the migration seed. These helpers
back the catalog/product pickers and the admin management page.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, select

from ...common.errors import Conflict, NotFound
from ...extensions import db
from ..models import Category, Product

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")


def _slug(code: str) -> str:
    code = (code or "").strip().lower()
    code = re.sub(r"[\s-]+", "_", code)
    code = re.sub(r"[^a-z0-9_]", "", code)
    return code.strip("_")


def _derive_code(explicit: str | None, name_en: str | None, name_ar: str) -> str:
    """Pick a valid, unique code. Prefer the explicit code, then a slug of the
    English name; for an Arabic-only name (slug is empty) generate cat_<n>."""
    for candidate in (explicit, name_en):
        s = _slug(candidate or "")
        if _CODE_RE.match(s):
            return s
    # Arabic-only name → stable generated code.
    n = int(db.session.execute(select(func.count()).select_from(Category)).scalar_one()) + 1
    code = f"cat_{n}"
    while db.session.execute(select(Category.id).where(Category.code == code)).scalar_one_or_none():
        n += 1
        code = f"cat_{n}"
    return code


def serialize(c: Category) -> dict[str, Any]:
    return {
        "code": c.code,
        "label": c.name_ar,  # back-compat with the existing pickers
        "name_ar": c.name_ar,
        "name_en": c.name_en,
        "icon": c.icon,
        "image_url": c.image_url,
        "parent_code": c.parent_code,
        "sort_order": c.sort_order,
        "is_active": c.is_active,
    }


def list_categories(*, active_only: bool = True) -> list[Category]:
    stmt = select(Category).order_by(Category.sort_order, Category.code)
    if active_only:
        stmt = stmt.where(Category.is_active.is_(True))
    return list(db.session.execute(stmt).scalars().all())


def get(code: str) -> Category:
    c = db.session.execute(select(Category).where(Category.code == code)).scalar_one_or_none()
    if c is None:
        raise NotFound(f"category {code} not found", code="category_not_found")
    return c


def assert_assignable(code: str) -> None:
    """Validate a category is usable for a product (exists + active)."""
    c = db.session.execute(select(Category).where(Category.code == code)).scalar_one_or_none()
    if c is None:
        raise Conflict(f"category {code} does not exist", code="bad_category")
    if not c.is_active:
        raise Conflict(f"category {code} is inactive", code="inactive_category")


def product_counts() -> dict[str, int]:
    rows = db.session.execute(
        select(Product.category, func.count()).group_by(Product.category)
    ).all()
    return {str(k): int(v) for k, v in rows}


def list_for_management() -> list[dict[str, Any]]:
    """All categories (incl. inactive) with their product counts — for the
    admin page tree."""
    counts = product_counts()
    out = []
    for c in list_categories(active_only=False):
        d = serialize(c)
        d["product_count"] = counts.get(c.code, 0)
        out.append(d)
    return out


def create(
    *,
    code: str | None = None,
    name_ar: str,
    name_en: str | None = None,
    icon: str | None = None,
    image_url: str | None = None,
    parent_code: str | None = None,
    sort_order: int | None = None,
) -> Category:
    # An explicit code must be valid; otherwise derive one (slug of EN name, or
    # a generated cat_<n> for an Arabic-only name) so the Arabic happy path works.
    if (code or "").strip() and not _CODE_RE.match(_slug(code or "")):
        raise Conflict("code must be lowercase latin letters/digits/underscore", code="bad_code")
    code = _derive_code(code, name_en, name_ar)
    if db.session.execute(select(Category.id).where(Category.code == code)).scalar_one_or_none():
        raise Conflict(f"category {code} already exists", code="duplicate_code")
    if parent_code:
        parent = get(parent_code)  # 404 if missing
        if parent.parent_code is not None:
            raise Conflict("categories nest one level only", code="too_deep")
    if sort_order is None:
        sort_order = int(
            db.session.execute(select(func.coalesce(func.max(Category.sort_order), 0))).scalar_one()
        ) + 1
    c = Category(
        code=code,
        name_ar=name_ar.strip(),
        name_en=(name_en or None),
        icon=(icon or None),
        image_url=(image_url or None),
        parent_code=(parent_code or None),
        sort_order=sort_order,
        is_active=True,
    )
    db.session.add(c)
    db.session.commit()
    return c


def update(
    code: str,
    *,
    name_ar: str | None = None,
    name_en: str | None = None,
    icon: str | None = None,
    image_url: str | None = None,
    parent_code: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> Category:
    c = get(code)
    if name_ar is not None:
        c.name_ar = name_ar.strip()
    if name_en is not None:
        c.name_en = name_en or None
    if icon is not None:
        c.icon = icon or None
    if image_url is not None:
        c.image_url = image_url or None
    if sort_order is not None:
        c.sort_order = sort_order
    if parent_code is not None:
        if parent_code == "":
            c.parent_code = None
        else:
            if parent_code == code:
                raise Conflict("a category cannot be its own parent", code="bad_parent")
            parent = get(parent_code)
            if parent.parent_code is not None:
                raise Conflict("categories nest one level only", code="too_deep")
            # The category being moved must not itself have children, or we'd
            # create a third level (parent → c → c's children).
            if db.session.execute(
                select(func.count()).select_from(Category).where(Category.parent_code == code)
            ).scalar_one():
                raise Conflict("move its subcategories first", code="has_children")
            c.parent_code = parent_code
    if is_active is not None:
        # Can't deactivate a category that still has products attached.
        if not is_active and product_counts().get(code, 0) > 0:
            raise Conflict("category has products; move them first", code="category_in_use")
        c.is_active = is_active
    db.session.commit()
    return c


def seed_defaults() -> None:
    """Idempotently seed the baseline category vocabulary (the former
    hardcoded set). Used by migrations' seed, dev seed, and tests."""
    from ..models import CATEGORIES, CATEGORY_ICONS, CATEGORY_LABELS

    existing = {c.code for c in list_categories(active_only=False)}
    added = False
    for i, code in enumerate(CATEGORIES):
        if code in existing:
            continue
        db.session.add(
            Category(
                code=code,
                name_ar=CATEGORY_LABELS[code],
                icon=CATEGORY_ICONS.get(code),
                sort_order=i,
                is_active=True,
            )
        )
        added = True
    if added:
        db.session.commit()


def delete(code: str) -> None:
    c = get(code)
    if product_counts().get(code, 0) > 0:
        raise Conflict("category has products; move or reassign them first", code="category_in_use")
    children = db.session.execute(
        select(func.count()).select_from(Category).where(Category.parent_code == code)
    ).scalar_one()
    if children:
        raise Conflict("category has subcategories; remove them first", code="has_children")
    db.session.delete(c)
    db.session.commit()
