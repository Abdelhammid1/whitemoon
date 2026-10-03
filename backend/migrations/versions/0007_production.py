"""production schema — manufacturing orders, stages, materials.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS production")

    op.create_table(
        "manufacturing_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("number", sa.String(40), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("output_product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("output_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("location_type", sa.String(20), nullable=False, server_default=sa.text("'supplier'")),
        sa.Column("location_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("total_material_cost", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'EGP'")),
        sa.Column("journal_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint("number", name="uq_manufacturing_orders_number"),
        sa.CheckConstraint("output_qty > 0", name="ck_mo_output_qty_positive"),
        sa.CheckConstraint("status in ('draft','in_progress','completed','cancelled')", name="ck_mo_status"),
        sa.CheckConstraint(
            "location_type in ('supplier','channel_partner','in_transit','customer_hold')",
            name="ck_mo_location_type",
        ),
        sa.CheckConstraint("currency = 'EGP'", name="ck_mo_currency_egp"),
        schema="production",
    )
    op.create_index("ix_mo_owner", "manufacturing_orders", ["owner_id"], schema="production")

    op.create_table(
        "mo_stages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("mo_id", sa.BigInteger(), sa.ForeignKey("production.manufacturing_orders.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("mo_id", "seq", name="uq_mo_stages_seq"),
        sa.CheckConstraint("status in ('pending','done')", name="ck_mo_stages_status"),
        schema="production",
    )

    op.create_table(
        "mo_materials",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("mo_id", sa.BigInteger(), sa.ForeignKey("production.manufacturing_orders.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.CheckConstraint("qty > 0", name="ck_mo_materials_qty_positive"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_mo_materials_unit_cost_nonneg"),
        schema="production",
    )
    op.create_index("ix_mo_materials_mo", "mo_materials", ["mo_id"], schema="production")


def downgrade() -> None:
    op.drop_index("ix_mo_materials_mo", table_name="mo_materials", schema="production")
    op.drop_table("mo_materials", schema="production")
    op.drop_table("mo_stages", schema="production")
    op.drop_index("ix_mo_owner", table_name="manufacturing_orders", schema="production")
    op.drop_table("manufacturing_orders", schema="production")
    op.execute("DROP SCHEMA IF EXISTS production")
