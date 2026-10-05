"""Cross-cutting: BI dashboard + Notification Center."""

from __future__ import annotations

from tests.helpers import auth_header, create_user


def _high(client):
    create_user(kind="admin", email="exec@example.com", roles=("admin.high",))
    return auth_header(client, email="exec@example.com")


def test_bi_dashboard(client) -> None:
    h = _high(client)
    r = client.get("/bi/dashboard", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert body["currency"] == "EGP"
    assert {"sales", "collection", "inventory", "pos", "logistics", "production", "communication"} <= body.keys()


def test_bi_requires_permission(client) -> None:
    create_user(kind="customer", email="nope@example.com", roles=("customer",))
    h = auth_header(client, email="nope@example.com")
    assert client.get("/bi/dashboard", headers=h).status_code == 403


def test_notifications_send_list_read(client) -> None:
    admin = _high(client)
    target = create_user(kind="customer", email="rcpt@example.com", roles=("customer",))
    th = auth_header(client, email="rcpt@example.com")

    sent = client.post("/notifications", headers=admin, json={
        "user_id": target.id, "title": "تنبيه ائتماني", "body": "اقترب سقفك", "type": "credit",
    })
    assert sent.status_code == 201

    lst = client.get("/notifications", headers=th)
    assert lst.status_code == 200
    data = lst.get_json()
    assert data["unread"] == 1 and len(data["items"]) == 1
    nid = data["items"][0]["id"]

    assert client.post(f"/notifications/{nid}/read", headers=th).status_code == 200
    assert client.get("/notifications", headers=th).get_json()["unread"] == 0

    # A customer can't broadcast.
    assert client.post("/notifications", headers=th, json={"user_id": target.id, "title": "x"}).status_code == 403


def test_notification_channels_from_backend(client) -> None:
    create_user(kind="customer", email="chan@example.com", roles=("customer",))
    h = auth_header(client, email="chan@example.com")
    r = client.get("/notifications/channels", headers=h)
    assert r.status_code == 200
    codes = {x["code"] for x in r.get_json()["items"]}
    assert {"in_app", "sms", "whatsapp", "email"} <= codes
