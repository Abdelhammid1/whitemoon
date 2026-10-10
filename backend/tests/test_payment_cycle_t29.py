"""T-29 — customer payment cycle: upload → notify approvers → approve settles
the due + posts the GL + notifies the customer; the queue is visible to an
agent/branch approver without user.read."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.accounting.models import Account, JournalEntry, JournalLine
from app.extensions import db
from app.identity.models import ChannelPartnerProfile, CustomerProfile
from app.notifications.models import Notification
from app.sales.models import CustomerDue
from tests.helpers import auth_header, create_user


def _uniq(p: str) -> str:
    return f"{p}{uuid.uuid4().hex[:6]}@wm.eg"


def _customer(geo: str | None = None) -> int:
    u = create_user(kind="customer", email=_uniq("cust"), roles=("customer",))
    db.session.add(CustomerProfile(user_id=u.id, display_name="عميل", geo_area=geo))
    db.session.commit()
    return u.id


def _deferred_due(customer_id: int, amount: str = "1000") -> CustomerDue:
    from app.sales.services import credit as credit_svc

    due = credit_svc.record_due(
        customer_id=customer_id, order_id=None, amount=Decimal(amount), due_date=date.today()
    )
    db.session.commit()
    return due


def test_upload_notifies_approvers_and_sets_source(client) -> None:
    from app.sales.services import payments as pay_svc

    cid = _customer()
    admin = create_user(kind="admin", email=_uniq("adm"), roles=("admin",))  # has payment.approve
    due = _deferred_due(cid)

    row = pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )
    assert row.source == "customer" and row.status == "pending"

    # The approver received a payment_pending notification.
    notes = db.session.execute(
        select(Notification).where(
            Notification.user_id == admin.id, Notification.type == "payment_pending"
        )
    ).scalars().all()
    assert len(notes) == 1


def test_agent_approver_sees_customer_upload_in_queue(client) -> None:
    from app.sales.services import payments as pay_svc

    cid = _customer(geo="cairo")
    agent = create_user(kind="agent", email=_uniq("agt"), roles=("agent",))
    db.session.add(ChannelPartnerProfile(user_id=agent.id, type="agent", display_name="وكيل", geo_scope="cairo"))
    db.session.commit()
    due = _deferred_due(cid)
    pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )

    # The agent has payment.approve + payment.collect but NOT user.read; the
    # customer upload must still appear in their queue (the visibility fix).
    h = auth_header(client, email=agent.email)
    r = client.get("/credit/payments?status=pending", headers=h)
    assert r.status_code == 200, r.get_json()
    items = r.get_json()["items"]
    assert any(it["source"] == "customer" and it["due_id"] == due.id for it in items)


def test_out_of_scope_agent_cannot_see_or_view_receipt(client) -> None:
    """Territory isolation (T-01): an approver in another geo must not see a
    customer's upload in the queue, nor fetch its receipt image."""
    from app.sales.services import payments as pay_svc

    cid = _customer(geo="alex")
    agent = create_user(kind="agent", email=_uniq("agt"), roles=("agent",))
    db.session.add(ChannelPartnerProfile(user_id=agent.id, type="agent", display_name="وكيل", geo_scope="cairo"))
    db.session.commit()
    due = _deferred_due(cid)
    row = pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )

    h = auth_header(client, email=agent.email)
    listing = client.get("/credit/payments?status=pending", headers=h)
    assert listing.status_code == 200
    assert all(it["id"] != row.id for it in listing.get_json()["items"])

    # And the receipt image is not reachable by an out-of-scope partner.
    rcpt = client.get(f"/credit/payments/{row.id}/receipt", headers=h)
    assert rcpt.status_code == 403


def test_approve_settles_due_posts_gl_and_notifies_customer(client) -> None:
    from app.sales.services import payments as pay_svc

    cid = _customer()
    approver = create_user(kind="admin", email=_uniq("apr"), roles=("admin",))
    due = _deferred_due(cid, amount="1000")
    row = pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )

    done = pay_svc.approve_payment(approval_id=row.id, approver_id=approver.id)
    assert done.status == "approved"

    # Due settled.
    settled = db.session.get(CustomerDue, due.id)
    assert settled is not None and settled.status == "paid"

    # A balanced GL entry was posted: debit 1112 (bank), credit 1132 (deferred).
    entry = db.session.execute(
        select(JournalEntry).where(JournalEntry.source_event_type == "payment.received")
    ).scalar_one()
    lines = db.session.execute(
        select(JournalLine, Account.code)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id == entry.id)
    ).all()
    legs = {code: (ln.debit, ln.credit) for ln, code in lines}
    assert legs["1112"][0] == Decimal("1000.00") and legs["1112"][1] == Decimal("0")
    assert legs["1132"][1] == Decimal("1000.00") and legs["1132"][0] == Decimal("0")

    # The customer was notified of the approval.
    note = db.session.execute(
        select(Notification).where(
            Notification.user_id == cid, Notification.type == "payment_approved"
        )
    ).scalar_one_or_none()
    assert note is not None


def test_customer_cannot_self_approve(client) -> None:
    from app.common.errors import Forbidden
    from app.sales.services import payments as pay_svc

    cid = _customer()
    due = _deferred_due(cid)
    row = pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )
    # The customer is the collector of record — they cannot approve it.
    try:
        pay_svc.approve_payment(approval_id=row.id, approver_id=cid)
        raise AssertionError("expected Forbidden on self-approval")
    except Forbidden:
        pass


def test_reject_notifies_customer_with_reason(client) -> None:
    from app.sales.services import payments as pay_svc

    cid = _customer()
    approver = create_user(kind="admin", email=_uniq("apr"), roles=("admin",))
    due = _deferred_due(cid)
    row = pay_svc.upload_customer_receipt(
        customer_id=cid, due_id=due.id, amount=Decimal("1000"), paid_on=date.today(),
        receipt_key="receipts/x.png",
    )
    pay_svc.reject_payment(approval_id=row.id, approver_id=approver.id, reason="الصورة غير واضحة")
    note = db.session.execute(
        select(Notification).where(
            Notification.user_id == cid, Notification.type == "payment_rejected"
        )
    ).scalar_one()
    assert "الصورة غير واضحة" in (note.body or "")
    # No due settled on reject.
    unchanged = db.session.get(CustomerDue, due.id)
    assert unchanged is not None and unchanged.status == "open"


def test_open_dues_for_selector(client) -> None:
    from app.sales.services import credit as credit_svc

    cid = _customer()
    _deferred_due(cid, amount="750")
    items = credit_svc.open_dues_for_customer(cid)
    assert len(items) == 1
    assert items[0]["amount"] == "750.0000"
    assert items[0]["days_overdue"] == 0
