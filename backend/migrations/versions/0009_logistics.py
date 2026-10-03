"""logistics schema — delivery slots, shipments, delivery shortages.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS logistics")

    op.create_table(
        "delivery_slots",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("window", sa.String(40), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("booked", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_ts(),
        sa.UniqueConstraint("slot_date", "window", name="uq_delivery_slots_date_window"),
        sa.CheckConstraint("capacity > 0", name="ck_delivery_slots_capacity_positive"),
        sa.CheckConstraint("booked >= 0", name="ck_delivery_slots_booked_nonneg"),
        sa.CheckConstraint("booked <= capacity", name="ck_delivery_slots_booked_lte_capacity"),
        schema="logistics",
    )
    op.create_index("ix_delivery_slots_date", "delivery_slots", ["slot_date"], schema="logistics")

    op.create_table(
        "shipments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), sa.ForeignKey("commerce.orders.id"), nullable=False),
        sa.Column("slot_id", sa.BigInteger(), sa.ForeignKey("logistics.delivery_slots.id"), nullable=True),
        sa.Column("carrier_type", sa.String(10), nullable=False, server_default=sa.text("'internal'")),
        sa.Column("carrier_ref", sa.String(120), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column("current_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("current_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("confirmation_code", sa.String(12), nullable=False),
        sa.Column("signature", sa.String(2000), nullable=True),
        sa.Column("delivered_by", sa.BigInteger(), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint("order_id", name="uq_shipments_order"),
        sa.CheckConstraint("carrier_type in ('internal','external')", name="ck_shipments_carrier"),
        sa.CheckConstraint(
            "status in ('scheduled','shipped','in_transit','delivered','failed')",
            name="ck_shipments_status",
        ),
        schema="logistics",
    )
    op.create_index("ix_shipments_status", "shipments", ["status"], schema="logistics")

    op.create_table(
        "delivery_shortages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("shipment_id", sa.BigInteger(), sa.ForeignKey("logistics.shipments.id"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("inventory.products.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("qty > 0", name="ck_delivery_shortages_qty_positive"),
        schema="logistics",
    )
    op.create_index("ix_delivery_shortages_shipment", "delivery_shortages", ["shipment_id"], schema="logistics")


def downgrade() -> None:
    op.drop_index("ix_delivery_shortages_shipment", table_name="delivery_shortages", schema="logistics")
    op.drop_table("delivery_shortages", schema="logistics")
    op.drop_index("ix_shipments_status", table_name="shipments", schema="logistics")
    op.drop_table("shipments", schema="logistics")
    op.drop_index("ix_delivery_slots_date", table_name="delivery_slots", schema="logistics")
    op.drop_table("delivery_slots", schema="logistics")
    op.execute("DROP SCHEMA IF EXISTS logistics")
