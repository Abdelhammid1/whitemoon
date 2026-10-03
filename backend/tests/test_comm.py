"""EPIC 10 — mediated chat: contact-leak filter, isolation, oversight."""

from __future__ import annotations

import uuid

import pytest

from app.comm.services import chat as svc
from app.comm.services import filters
from app.extensions import db
from tests.helpers import create_user


def _user(kind: str):
    u = create_user(kind=kind, email=f"{kind}{uuid.uuid4().hex[:6]}@example.com", roles=(kind,))
    db.session.commit()
    return u


# ---------------------------------------------------------------- filter (US-10.2)


@pytest.mark.parametrize(
    "text",
    [
        "اتصل بي على 01012345678",          # plain digits
        "رقمي 0101-234-5678",                # dashed
        "my number is 0 1 0 1 2 3 4 5 6 7 8",  # spaced
        "رقمي ٠١٠١٢٣٤٥٦٧٨",                   # Arabic-Indic numerals
        "صفر واحد صفر واحد اثنين ثلاثة اربعة",  # spelled Arabic
        "zero one zero one two three four",   # spelled English
        "راسلني على ahmed@gmail.com",         # email
        "تواصل واتساب wa.me/20100",            # social/link
    ],
)
def test_filter_blocks_contact_exchange(text) -> None:
    assert filters.scan_text(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "السعر 500 جنيه والكمية 20 كرتونة",     # normal numbers, short runs
        "تمام، سأرسل الطلب غدًا إن شاء الله",     # no numbers
        "الطلب رقم 12345 جاهز",                  # 5-digit order ref, under threshold
    ],
)
def test_filter_allows_normal_text(text) -> None:
    assert filters.scan_text(text) is None


# ---------------------------------------------------------------- chat flow


def test_blocked_message_not_delivered_but_kept(client) -> None:
    cust = _user("customer")
    sup = _user("supplier")
    conv = svc.start_conversation(customer_id=cust.id, supplier_id=sup.id)

    blocked = svc.send_message(conversation_id=conv.id, sender_id=cust.id, body="رقمي 01012345678")
    assert blocked.status == "blocked"
    assert blocked.block_reason == "phone_number_digits"

    ok = svc.send_message(conversation_id=conv.id, sender_id=cust.id, body="أهلاً، متى يصل الطلب؟")
    assert ok.status == "sent"

    # The supplier never sees the blocked message; the customer sees their own.
    sup_view = svc.list_messages(conversation_id=conv.id, viewer_id=sup.id, is_admin=False)
    assert [m.id for m in sup_view] == [ok.id]
    cust_view = svc.list_messages(conversation_id=conv.id, viewer_id=cust.id, is_admin=False)
    assert blocked.id in [m.id for m in cust_view]
    # An admin/moderator sees everything (US-10.3).
    admin_view = svc.list_messages(conversation_id=conv.id, viewer_id=1, is_admin=True)
    assert {blocked.id, ok.id} <= {m.id for m in admin_view}


def test_identity_hidden_from_participants(client) -> None:
    cust = _user("customer")
    sup = _user("supplier")
    conv = svc.start_conversation(customer_id=cust.id, supplier_id=sup.id)
    msg = svc.send_message(conversation_id=conv.id, sender_id=sup.id, body="تم تجهيز طلبك")

    # Customer's view of the supplier's message carries no supplier user id.
    as_customer = svc.serialize_message(msg, viewer_id=cust.id, is_admin=False)
    assert "sender_id" not in as_customer
    assert as_customer["sender_role"] == "supplier"
    # Conversation view exposes only the counterpart role, not the id.
    conv_view = svc.serialize_conversation(conv, viewer_id=cust.id, is_admin=False)
    assert "supplier_id" not in conv_view and conv_view["counterpart_role"] == "supplier"
    # Admin view does include ids for oversight.
    admin_conv = svc.serialize_conversation(conv, viewer_id=1, is_admin=True)
    assert admin_conv["supplier_id"] == sup.id


def test_non_participant_cannot_read_or_send(client) -> None:
    from app.common.errors import Forbidden

    cust = _user("customer")
    sup = _user("supplier")
    intruder = _user("customer")
    conv = svc.start_conversation(customer_id=cust.id, supplier_id=sup.id)
    with pytest.raises(Forbidden):
        svc.send_message(conversation_id=conv.id, sender_id=intruder.id, body="مرحبا")
    with pytest.raises(Forbidden):
        svc.list_messages(conversation_id=conv.id, viewer_id=intruder.id, is_admin=False)
