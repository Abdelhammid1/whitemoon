"""Partner current account (الحساب الجاري) — operational running-balance ledger.

Cash paid to / received from a partner, plus manual adjustments. No GL posting;
the balance is SUM(amount * direction) as 'partner owes management'.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.common.errors import BadRequest, NotFound
from app.extensions import db
from app.identity.models import ChannelPartnerProfile
from app.partners.services import partners as svc
from tests.helpers import auth_header, create_user


def _make_partner(email: str, ptype: str = "agent"):
    u = create_user(kind=ptype, email=email, roles=(ptype,))
    db.session.add(
        ChannelPartnerProfile(user_id=u.id, type=ptype, display_name="شريك", geo_scope="القاهرة")
    )
    db.session.commit()
    return u


# ---------------------------------------------------------------- balance & sign


def test_balance_starts_zero(client) -> None:
    agent = _make_partner("led0@example.com")
    assert svc.ledger_balance(agent.id) == Decimal("0.0000")
    summary = svc.ledger_summary(agent.id)
    assert summary["owed_by"] == "settled"
    assert summary["count"] == 0


def test_cash_moves_sign(client) -> None:
    agent = _make_partner("led1@example.com")
    # We paid the partner 100 → he owes management more.
    svc.record_ledger_entry(
        partner_id=agent.id, kind="payment_made", amount=Decimal("100"),
        direction=None, note=None, posted_by=1,
    )
    assert svc.ledger_balance(agent.id) == Decimal("100.0000")
    # He paid us 30 back → balance drops.
    svc.record_ledger_entry(
        partner_id=agent.id, kind="payment_received", amount=Decimal("30"),
        direction=None, note="دفعة نقدية", posted_by=1,
    )
    summary = svc.ledger_summary(agent.id)
    assert summary["balance"] == "70.0000"
    assert summary["abs_balance"] == "70.0000"
    assert summary["owed_by"] == "partner"
    assert summary["count"] == 2


def test_management_owes_when_negative(client) -> None:
    agent = _make_partner("led2@example.com")
    svc.record_ledger_entry(
        partner_id=agent.id, kind="payment_received", amount=Decimal("500"),
        direction=None, note=None, posted_by=1,
    )
    summary = svc.ledger_summary(agent.id)
    assert summary["balance"] == "-500.0000"
    assert summary["abs_balance"] == "500.0000"
    assert summary["owed_by"] == "management"


def test_payment_ignores_client_direction(client) -> None:
    agent = _make_partner("led3@example.com")
    # A cash move's sign is fixed by its kind; a hostile direction is ignored.
    entry = svc.record_ledger_entry(
        partner_id=agent.id, kind="payment_made", amount=Decimal("40"),
        direction=-1, note=None, posted_by=1,
    )
    assert entry.direction == 1
    assert svc.ledger_balance(agent.id) == Decimal("40.0000")


# ---------------------------------------------------------------- manual adjustment


def test_manual_credit_and_debit(client) -> None:
    agent = _make_partner("led4@example.com")
    # زوّده له (credit, direction -1)
    svc.record_ledger_entry(
        partner_id=agent.id, kind="manual", amount=Decimal("50"),
        direction=-1, note="تسوية يدوية لصالحه", posted_by=1,
    )
    # حمّله عليه (debit, direction +1)
    svc.record_ledger_entry(
        partner_id=agent.id, kind="manual", amount=Decimal("20"),
        direction=1, note="تحميل مصاريف تشغيلية", posted_by=1,
    )
    assert svc.ledger_balance(agent.id) == Decimal("-30.0000")


def test_manual_requires_direction(client) -> None:
    agent = _make_partner("led5@example.com")
    with pytest.raises(BadRequest):
        svc.record_ledger_entry(
            partner_id=agent.id, kind="manual", amount=Decimal("10"),
            direction=None, note="سبب كافٍ للتعديل", posted_by=1,
        )


def test_manual_requires_reason(client) -> None:
    agent = _make_partner("led6@example.com")
    with pytest.raises(BadRequest):
        svc.record_ledger_entry(
            partner_id=agent.id, kind="manual", amount=Decimal("10"),
            direction=1, note="قصير", posted_by=1,
        )


# ---------------------------------------------------------------- guards


def test_amount_must_be_positive(client) -> None:
    agent = _make_partner("led7@example.com")
    with pytest.raises(BadRequest):
        svc.record_ledger_entry(
            partner_id=agent.id, kind="payment_made", amount=Decimal("0"),
            direction=None, note=None, posted_by=1,
        )


def test_non_partner_rejected(client) -> None:
    cust = create_user(kind="customer", email="notpartner@example.com", roles=("customer",))
    db.session.commit()
    with pytest.raises(NotFound):
        svc.record_ledger_entry(
            partner_id=cust.id, kind="payment_made", amount=Decimal("10"),
            direction=None, note=None, posted_by=1,
        )


def test_audit_emitted(client) -> None:
    agent = _make_partner("led8@example.com")
    entry = svc.record_ledger_entry(
        partner_id=agent.id, kind="payment_made", amount=Decimal("10"),
        direction=None, note=None, posted_by=1,
    )
    from app.audit.models import AuditEvent
    ev = db.session.execute(
        db.select(AuditEvent).where(
            AuditEvent.action == "partner.ledger.recorded",
            AuditEvent.target_id == str(entry.id),
        )
    ).first()
    assert ev is not None


# ---------------------------------------------------------------- HTTP / permission


def test_ledger_endpoint_requires_permission(client) -> None:
    agent = _make_partner("ledhttp1@example.com")
    outsider = create_user(kind="customer", email="outsider@example.com", roles=("customer",))
    db.session.commit()
    hdr = auth_header(client, email="outsider@example.com")
    r = client.get(f"/partners/{agent.id}/ledger", headers=hdr)
    assert r.status_code == 403
    # The partner themselves cannot view it in this version (admin-only).
    _ = outsider


def test_record_via_http_returns_balance(client) -> None:
    agent = _make_partner("ledhttp2@example.com")
    create_user(kind="admin", email="ledadmin@example.com", roles=("admin",))
    db.session.commit()
    hdr = auth_header(client, email="ledadmin@example.com")
    r = client.post(
        f"/partners/{agent.id}/ledger",
        json={"kind": "payment_made", "amount": 250, "note": "سلفة تشغيل"},
        headers=hdr,
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["balance"] == "250.0000"
    assert body["owed_by"] == "partner"
    assert body["entry"]["kind"] == "payment_made"

    r2 = client.get(f"/partners/{agent.id}/ledger", headers=hdr)
    assert r2.status_code == 200
    assert r2.get_json()["count"] == 1
