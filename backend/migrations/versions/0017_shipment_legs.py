"""shipment legs — mixed internal/external routing (T-05, US-9.4).

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | Sequence[str] | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shipment_legs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("shipment_id", sa.BigInteger(), sa.ForeignKey("logistics.shipments.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("carrier_type", sa.String(10), nullable=False),
        sa.Column("carrier_ref", sa.String(120), nullable=True),
        sa.Column("from_label", sa.String(200), nullable=True),
        sa.Column("to_label", sa.String(200), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default=sa.text("'pending'")),
        sa.UniqueConstraint("shipment_id", "seq", name="uq_shipment_legs_seq"),
        sa.CheckConstraint("carrier_type in ('internal','external')", name="ck_shipment_legs_carrier"),
        sa.CheckConstraint("status in ('pending','in_transit','done')", name="ck_shipment_legs_status"),
        schema="logistics",
    )
    op.create_index("ix_shipment_legs_shipment", "shipment_legs", ["shipment_id"], schema="logistics")


def downgrade() -> None:
    op.drop_index("ix_shipment_legs_shipment", table_name="shipment_legs", schema="logistics")
    op.drop_table("shipment_legs", schema="logistics")
