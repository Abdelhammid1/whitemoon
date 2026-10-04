"""Server-side receipt image upload + storage + OCR + fetch."""

from __future__ import annotations

import io

from tests.helpers import auth_header, create_user

# A 1x1 PNG.
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _high(client):
    create_user(kind="admin", email="rcp@example.com", roles=("admin.high",))
    return auth_header(client, email="rcp@example.com")


def test_upload_receipt_file_stores_and_matches(client) -> None:
    h = _high(client)
    r = client.post(
        "/accounting/receipts/file",
        headers=h,
        data={
            "image": (io.BytesIO(_PNG), "receipt.png"),
            "expected_amount": "1500.00",
            "expected_reference": "TRX-9",
            "ocr_stub_amount": "1500.00",
            "ocr_stub_reference": "TRX-9",
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["status"] == "matched"
    assert body["image_s3_key"].startswith("receipts/")

    # The stored image streams back, gated to finance.
    img = client.get(f"/accounting/receipts/{body['receipt_id']}/image", headers=h)
    assert img.status_code == 200
    assert img.data == _PNG
    assert img.mimetype == "image/png"


def test_upload_rejects_missing_file(client) -> None:
    h = _high(client)
    r = client.post("/accounting/receipts/file", headers=h, data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_rejects_bad_type(client) -> None:
    h = _high(client)
    r = client.post(
        "/accounting/receipts/file",
        headers=h,
        data={"image": (io.BytesIO(b"xx"), "evil.exe")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
