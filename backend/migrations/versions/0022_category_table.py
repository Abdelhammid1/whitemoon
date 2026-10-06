"""Admin-managed product categories (T-15).

Turns the hardcoded category vocabulary into a DB table the admin can edit,
and replaces the products.category CHECK with an FK to categories.code so
data integrity is enforced against live rows. Seeds the existing 9 categories.

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | Sequence[str] | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED = [
    ("food", "غذائية", "restaurant"),
    ("clothing", "ملابس", "checkroom"),
    ("electronics", "إلكترونيات", "devices"),
    ("home", "أدوات منزلية", "home"),
    ("beauty", "عناية وتجميل", "spa"),
    ("construction", "مواد بناء", "construction"),
    ("stationery", "قرطاسية", "edit"),
    ("automotive", "قطع غيار", "directions_car"),
    ("other", "أخرى", "category"),
]
_OLD_CHECK = (
    "category in ('food','clothing','electronics','home','beauty',"
    "'construction','stationery','automotive','other')"
)


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120)),
        sa.Column("icon", sa.String(length=120)),
        sa.Column("image_url", sa.String(length=500)),
        sa.Column("parent_code", sa.String(length=40)),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_categories_code"),
        sa.ForeignKeyConstraint(
            ["parent_code"], ["inventory.categories.code"], name="fk_categories_parent_code_categories"
        ),
        sa.Index("ix_categories_parent", "parent_code"),
        schema="inventory",
    )

    cats = sa.table(
        "categories",
        sa.column("code", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("icon", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        schema="inventory",
    )
    op.bulk_insert(
        cats,
        [
            {"code": c, "name_ar": ar, "icon": ic, "sort_order": i, "is_active": True}
            for i, (c, ar, ic) in enumerate(_SEED)
        ],
    )

    # Replace the CHECK with an FK (existing product.category values are all
    # in the seeded set, so the FK validates cleanly).
    op.drop_constraint("ck_products_category", "products", schema="inventory", type_="check")
    op.alter_column("products", "category", schema="inventory", type_=sa.String(length=40))
    op.create_foreign_key(
        "fk_products_category_categories",
        "products",
        "categories",
        ["category"],
        ["code"],
        source_schema="inventory",
        referent_schema="inventory",
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_category_categories", "products", schema="inventory", type_="foreignkey")
    # Any admin-added category can't survive the old 9-value CHECK; fold those
    # products back into 'other' so the downgrade reverts cleanly.
    _defaults = "','".join(c for c, _, _ in _SEED)
    op.execute(
        f"UPDATE inventory.products SET category='other' WHERE category NOT IN ('{_defaults}')"
    )
    op.alter_column("products", "category", schema="inventory", type_=sa.String(length=20))
    op.create_check_constraint("ck_products_category", "products", _OLD_CHECK, schema="inventory")
    op.drop_table("categories", schema="inventory")
