"""Shared pytest fixtures.

Strategy: hit a real Postgres (same container as dev), truncate every schema
table before each test. Fast enough for the current test count and keeps
behavior identical to prod (schemas, FKs, CHECKs). Each test runs in its own
app context + a nested transaction isn't used because many endpoints commit.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import text

os.environ.setdefault("FLASK_SECRET_KEY", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://wm:wm@localhost:5433/whitemoon",
)
os.environ.setdefault("OTP_PROVIDER", "console")

from app import create_app
from app.accounting import seed as accounting_seed
from app.extensions import db
from app.identity import seed as identity_seed
from app.identity.providers import otp_provider


@pytest.fixture(scope="session")
def app() -> Iterator[Flask]:
    flask_app = create_app()
    yield flask_app


@pytest.fixture(autouse=True)
def _reset_db(app: Flask) -> Iterator[None]:
    with app.app_context():
        # Order matters because of FKs. TRUNCATE ... CASCADE wipes it all.
        db.session.execute(
            text(
                "TRUNCATE TABLE "
                "notifications.notifications, "
                "comm.messages, "
                "comm.conversations, "
                "logistics.delivery_shortages, "
                "logistics.shipment_legs, "
                "logistics.shipments, "
                "logistics.delivery_slots, "
                "pos.pos_sale_lines, "
                "pos.pos_sales, "
                "pos.pos_batches, "
                "production.mo_materials, "
                "production.mo_stages, "
                "production.manufacturing_orders, "
                "partners.partner_ledger, "
                "partners.partner_accruals, "
                "partners.partner_deposits, "
                "partners.partner_terms, "
                "sales.escalation_events, "
                "sales.customer_dues, "
                "sales.credit_overrides, "
                "sales.payment_approvals, "
                "sales.credit_tier_settings, "
                "sales.customer_credit_tiers, "
                "commerce.rfq_offers, "
                "commerce.rfqs, "
                "commerce.order_lines, "
                "commerce.order_sub_orders, "
                "commerce.orders, "
                "commerce.price_locks, "
                "commerce.cart_items, "
                "commerce.carts, "
                "inventory.product_variants, "
                "inventory.reorder_alerts, "
                "inventory.shortages, "
                "inventory.batches, "
                "inventory.transfer_order_lines, "
                "inventory.transfer_orders, "
                "inventory.stock_balances, "
                "inventory.supplier_offers, "
                "inventory.products, "
                "accounting.bank_receipts, "
                "accounting.deferred_terms, "
                "accounting.event_journal_map, "
                "accounting.journal_lines, "
                "accounting.journal_entries, "
                "accounting.periods, "
                "accounting.accounts, "
                "audit.events, "
                "identity.impersonation_grants, "
                "identity.sessions, "
                "identity.backup_codes, "
                "identity.totp_secrets, "
                "identity.otp_requests, "
                "identity.user_roles, "
                "identity.role_permissions, "
                "identity.permissions, "
                "identity.roles, "
                "identity.channel_partner_profiles, "
                "identity.customer_profiles, "
                "identity.supplier_profiles, "
                "identity.users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.session.commit()
        identity_seed.seed_rbac()
        # Tests reference user id=1 for posted_by / uploaded_by / closed_by.
        # Seed a bootstrap admin so those FKs resolve.
        identity_seed.seed_bootstrap_admin()
        accounting_seed.seed_accounts()
        accounting_seed.seed_event_map()
        from app.sales.services import credit as _credit
        _credit.seed_tier_settings()
        db.session.commit()
        otp_provider.LAST_CODES.clear()
        yield


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
