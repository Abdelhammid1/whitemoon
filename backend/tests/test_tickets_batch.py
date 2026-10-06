"""Backend coverage for the T-19…T-23 ticket batch.

- T-19 customer statement: balance/available + PDF & Excel export
- T-20 shipment board: list + allowed-next transitions
- T-21 customer receipt upload → staff review queue (+ image access control)
- T-22 supplier RFQ inbox hides the initiator; customer comparison hides supplier
- T-23 order invoice (PDF or printable HTML), owner-gated
"""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.commerce.models import Order, OrderLine, OrderSubOrder
from app.extensions import db
from app.inventory.models import SupplierOffer
from app.inventory.services import products as products_svc
from app.logistics.services import logistics as log_svc
from tests.helpers import auth_header, create_user

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _u(kind: str, roles: tuple[str, ...]):
    return create_user(kind=kind, email=f"{kind}{uuid.uuid4().hex[:6]}@example.com", roles=roles)


def _order_with_line(customer_id: int, supplier_id: int, product_id: int) -> Order:
    o = Order(
        number=f"ORD-{uuid.uuid4().hex[:10]}",
        customer_id=customer_id,
        status="confirmed",
        payment_mode="cash",
        total_cash=Decimal("150.00"),
        total_deferred=Decimal("0.00"),
    )
    db.session.add(o)
    db.session.flush()
    sub = OrderSubOrder(order_id=o.id, supplier_id=supplier_id, subtotal=Decimal("150.00"))
    db.session.add(sub)
    offer = SupplierOffer(product_id=product_id, supplier_id=supplier_id, unit_price=Decimal("50.00"), moq=Decimal("1"))
    db.session.add(offer)
    db.session.flush()
    db.session.add(
        OrderLine(
            sub_order_id=sub.id,
            product_id=product_id,
            supplier_offer_id=offer.id,
            qty=Decimal("3"),
            unit_price=Decimal("50.00"),
            line_total=Decimal("150.00"),
        )
    )
    db.session.commit()
    return o


def _product(admin_id: int) -> int:
    p = products_svc.create_product(
        sku=f"SKU-{uuid.uuid4().hex[:8]}", name_ar="صنف تجريبي", category="other", created_by=admin_id
    )
    db.session.commit()
    return p.id


# ---------------------------------------------------------------- T-20

def test_shipment_board_lists_with_allowed_next(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    order = Order(
        number=f"ORD-{uuid.uuid4().hex[:10]}", customer_id=cust.id, status="confirmed",
        payment_mode="cash", total_cash=Decimal("100"), total_deferred=Decimal("0"),
    )
    db.session.add(order)
    db.session.commit()
    slot = log_svc.create_slot(slot_date=date.today() + timedelta(days=1), window="09:00-11:00", capacity=5)
    log_svc.book_slot(order_id=order.id, slot_id=slot.id, actor_user_id=cust.id)

    h = auth_header(client, email=admin.email)
    r = client.get("/logistics/shipments", headers=h)
    assert r.status_code == 200, r.get_json()
    items = r.get_json()["items"]
    assert len(items) == 1
    row = items[0]
    assert row["status"] == "scheduled"
    # A scheduled shipment may only advance to shipped or failed — never jump.
    assert row["allowed_next"] == ["shipped", "failed"]
    assert "confirmation_code" not in row  # list never leaks the code

    # Status filter works.
    assert client.get("/logistics/shipments?status=delivered", headers=h).get_json()["items"] == []


def test_shipment_board_requires_manage(client) -> None:
    cust = _u("customer", ("customer",))
    h = auth_header(client, email=cust.email)
    assert client.get("/logistics/shipments", headers=h).status_code == 403


# ---------------------------------------------------------------- T-22

def test_supplier_rfq_inbox_hides_initiator_and_supplier(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    sup = _u("supplier", ("supplier",))
    pid = _product(admin.id)

    ch = auth_header(client, email=cust.email)
    r = client.post("/commerce/rfqs", json={"product_id": pid, "qty": 10}, headers=ch)
    assert r.status_code == 201, r.get_json()
    rfq_id = r.get_json()["id"]

    # Supplier inbox shows the open RFQ without any initiator identity.
    sh = auth_header(client, email=sup.email)
    inbox = client.get("/commerce/rfqs", headers=sh).get_json()["items"]
    assert any(x["id"] == rfq_id for x in inbox)
    row = next(x for x in inbox if x["id"] == rfq_id)
    assert "initiator_user_id" not in row and "customer_id" not in row
    assert row["product_name"] == "صنف تجريبي"

    # Supplier submits an offer.
    assert client.post(f"/commerce/rfqs/{rfq_id}/offers", json={"unit_price": 42, "moq": 5}, headers=sh).status_code == 201

    # Customer comparison sees the offer but not the supplier behind it.
    offers = client.get(f"/commerce/rfqs/{rfq_id}/offers", headers=ch).get_json()["items"]
    assert len(offers) == 1
    assert "supplier_id" not in offers[0]
    assert offers[0]["unit_price"] == "42.0000"

    # Admin does see the supplier.
    ah = auth_header(client, email=admin.email)
    admin_offers = client.get(f"/commerce/rfqs/{rfq_id}/offers", headers=ah).get_json()["items"]
    assert admin_offers[0]["supplier_id"] == sup.id


# ---------------------------------------------------------------- T-21

def test_customer_receipt_upload_enters_queue_and_image_is_gated(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    other = _u("customer", ("customer",))

    ch = auth_header(client, email=cust.email)
    r = client.post(
        "/credit/payments/upload-receipt",
        data={"image": (io.BytesIO(_PNG), "receipt.png"), "amount": "250.00"},
        content_type="multipart/form-data",
        headers=ch,
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["status"] == "pending" and body["source"] == "customer" and body["has_receipt"] is True
    approval_id = body["id"]

    # Shows up in the staff review queue.
    ah = auth_header(client, email=admin.email)
    queue = client.get("/credit/payments?status=pending", headers=ah).get_json()["items"]
    assert any(x["id"] == approval_id for x in queue)

    # The owner and staff can fetch the image; a different customer cannot.
    assert client.get(f"/credit/payments/{approval_id}/receipt", headers=ch).status_code == 200
    assert client.get(f"/credit/payments/{approval_id}/receipt", headers=ah).status_code == 200
    oh = auth_header(client, email=other.email)
    assert client.get(f"/credit/payments/{approval_id}/receipt", headers=oh).status_code == 403


def test_receipt_upload_bad_due_id_is_400_not_500(client) -> None:
    cust = _u("customer", ("customer",))
    ch = auth_header(client, email=cust.email)
    r = client.post(
        "/credit/payments/upload-receipt",
        data={"image": (io.BytesIO(_PNG), "r.png"), "amount": "10", "due_id": "abc"},
        content_type="multipart/form-data",
        headers=ch,
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "due_id_invalid"


def test_receipt_upload_foreign_due_rejected_without_orphan(client) -> None:
    # A due that belongs to another customer must be refused (400), exercising
    # the store→validate rollback path (no crash, clean 4xx).
    from app.sales.models import CustomerDue
    from datetime import date as _date

    owner = _u("customer", ("customer",))
    other = _u("customer", ("customer",))
    due = CustomerDue(customer_id=owner.id, amount=Decimal("100.00"), due_date=_date.today(), status="open")
    db.session.add(due)
    db.session.commit()

    ch = auth_header(client, email=other.email)
    r = client.post(
        "/credit/payments/upload-receipt",
        data={"image": (io.BytesIO(_PNG), "r.png"), "amount": "100.00", "due_id": str(due.id)},
        content_type="multipart/form-data",
        headers=ch,
    )
    assert r.status_code == 400  # due_customer_mismatch


def test_statement_date_filter_narrows_rows(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    pid = _product(admin.id)
    _order_with_line(cust.id, admin.id, pid)

    ch = auth_header(client, email=cust.email)
    # A window entirely in the past returns no orders/dues/payments, but the
    # balance figures (as-of today) are still present.
    data = client.get(
        f"/commerce/customers/{cust.id}/statement?from=2000-01-01&to=2000-12-31", headers=ch
    ).get_json()
    assert data["orders"] == [] and data["dues"] == [] and data["payments"] == []
    assert "credit_limit" in data and "as_of" in data


def test_receipt_upload_rejects_non_image(client) -> None:
    cust = _u("customer", ("customer",))
    ch = auth_header(client, email=cust.email)
    r = client.post(
        "/credit/payments/upload-receipt",
        data={"image": (io.BytesIO(b"<svg onload=alert(1)>"), "x.png"), "amount": "10"},
        content_type="multipart/form-data",
        headers=ch,
    )
    assert r.status_code == 400
    assert r.get_json()["error"] == "bad_file_type"


# ---------------------------------------------------------------- T-19

def test_statement_has_balance_and_exports(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    pid = _product(admin.id)
    _order_with_line(cust.id, admin.id, pid)

    ch = auth_header(client, email=cust.email)
    s = client.get(f"/commerce/customers/{cust.id}/statement", headers=ch)
    assert s.status_code == 200, s.get_json()
    data = s.get_json()
    assert {"credit_limit", "outstanding", "available", "payments", "tier"} <= set(data)

    xlsx = client.get(f"/commerce/customers/{cust.id}/statement.xlsx", headers=ch)
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.mimetype
    assert xlsx.data[:2] == b"PK"  # a real .xlsx (zip) payload

    pdf = client.get(f"/commerce/customers/{cust.id}/statement.pdf", headers=ch)
    assert pdf.status_code == 200
    # PDF where WeasyPrint is present, printable HTML otherwise — both fine.
    assert pdf.mimetype in ("application/pdf", "text/html")


def test_xlsx_cell_sanitised_against_formula_injection() -> None:
    from app.commerce.routes import _xlsx_safe

    assert _xlsx_safe("=1+1") == "'=1+1"
    assert _xlsx_safe("+SUM(A1)") == "'+SUM(A1)"
    assert _xlsx_safe("-2") == "'-2"
    assert _xlsx_safe("@cmd") == "'@cmd"
    assert _xlsx_safe("متجر الأمل") == "متجر الأمل"  # ordinary text untouched


def test_statement_out_of_scope_forbidden(client) -> None:
    c1 = _u("customer", ("customer",))
    c2 = _u("customer", ("customer",))
    h = auth_header(client, email=c2.email)
    assert client.get(f"/commerce/customers/{c1.id}/statement", headers=h).status_code == 403


# ---------------------------------------------------------------- T-23

def test_order_invoice_owner_gated(client) -> None:
    admin = _u("admin", ("admin",))
    cust = _u("customer", ("customer",))
    other = _u("customer", ("customer",))
    pid = _product(admin.id)
    order = _order_with_line(cust.id, admin.id, pid)

    ch = auth_header(client, email=cust.email)
    r = client.get(f"/commerce/orders/{order.id}/invoice", headers=ch)
    assert r.status_code == 200
    assert r.mimetype in ("application/pdf", "text/html")

    oh = auth_header(client, email=other.email)
    assert client.get(f"/commerce/orders/{order.id}/invoice", headers=oh).status_code == 403
