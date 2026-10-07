"""Admin AI Assistant — security + behaviour tests (ticket §23/§24/§25).

Covers: permission gating (backend, not just UI), redaction of anything that
reaches DeepSeek, architectural isolation from business data, knowledge-gap
logging, the daily cap, and read-only (no write endpoints into the domain).
"""

from __future__ import annotations

import pathlib
import uuid

from app.assistant.services import redaction
from tests.helpers import auth_header, create_user


def _admin():
    return create_user(kind="admin", email=f"adm{uuid.uuid4().hex[:6]}@wm.eg", roles=("admin",))


def _mk_conversation(client, h) -> int:
    r = client.post("/assistant/conversations", json={}, headers=h)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def _ask(client, h, cid: int, question: str, route: str | None = None) -> str:
    """Post a question and fully consume the stream (so the generator's final
    persistence — assistant message, usage, knowledge gap — runs)."""
    r = client.post(
        f"/assistant/conversations/{cid}/ask",
        json={"question": question, "route": route},
        headers=h,
    )
    assert r.status_code == 200
    return r.get_data(as_text=True)


# ---------------------------------------------------------------- permission

def test_assistant_requires_permission(client) -> None:
    cust = create_user(kind="customer", email="c@wm.eg", roles=("customer",))
    ch = auth_header(client, email="c@wm.eg")
    assert client.get("/assistant/status", headers=ch).status_code == 403
    assert client.post("/assistant/conversations", json={}, headers=ch).status_code == 403

    adm = _admin()
    ah = auth_header(client, email=adm.email)
    assert client.get("/assistant/status", headers=ah).status_code == 200


# ---------------------------------------------------------------- redaction unit

def test_redaction_masks_sensitive_values() -> None:
    r = redaction.redact("تواصل a.customer@example.com أو 01012345678 بمبلغ 15000 ج.م رقم ضريبي 302555123")
    assert "example.com" not in r.text and "01012345678" not in r.text
    assert "⟪email⟫" in r.text and "⟪phone⟫" in r.text and "⟪amount⟫" in r.text
    assert r.findings.get("email") == 1 and r.findings.get("phone") == 1
    # ordinary Arabic text is untouched
    plain = redaction.redact("ازاي اضيف فرع جديد؟")
    assert plain.text == "ازاي اضيف فرع جديد؟" and plain.total == 0


# ---------------------------------------------------------------- redaction before LLM

def test_question_is_redacted_before_reaching_deepseek(client, monkeypatch) -> None:
    captured: dict = {}

    def fake_stream(messages, **_):
        captured["messages"] = messages
        yield "تمام"

    monkeypatch.setattr("app.assistant.providers.deepseek.chat_stream", fake_stream)

    adm = _admin()
    h = auth_header(client, email=adm.email)
    cid = _mk_conversation(client, h)
    _ask(client, h, cid, "العميل a@b.com ورقمه 01087654321 ليه مش شايف الصفحة؟", route="/admin/users")
    blob = "\n".join(m["content"] for m in captured["messages"])
    # Nothing sensitive reached the model
    assert "a@b.com" not in blob and "01087654321" not in blob
    assert "⟪email⟫" in blob and "⟪phone⟫" in blob
    # The route context is passed (ticket §12) but no screen data
    assert "/admin/users" in blob


# ---------------------------------------------------------------- knowledge gap

def test_unanswerable_question_is_logged_as_gap(client, monkeypatch) -> None:
    monkeypatch.setattr("app.assistant.providers.deepseek.chat_stream", lambda messages, **_: iter(["لا أملك معلومات كافية"]))
    adm = _admin()
    h = auth_header(client, email=adm.email)
    cid = _mk_conversation(client, h)
    # No index is built in this test → retrieval returns nothing → gap.
    _ask(client, h, cid, "سؤال نادر جدًا 0199999")
    gaps = client.get("/assistant/gaps", headers=h).get_json()["items"]
    assert len(gaps) >= 1
    assert "0199" not in gaps[0]["question"]  # redacted in the stored gap


# ---------------------------------------------------------------- daily cap

def test_daily_cap_blocks_without_calling_model(client, monkeypatch) -> None:
    called = {"n": 0}

    def fake_stream(messages, **_):
        called["n"] += 1
        yield "x"

    monkeypatch.setattr("app.assistant.providers.deepseek.chat_stream", fake_stream)
    monkeypatch.setattr("app.assistant.services.chat.DAILY_MESSAGE_CAP", 0)

    adm = _admin()
    h = auth_header(client, email=adm.email)
    cid = _mk_conversation(client, h)
    r = client.post(f"/assistant/conversations/{cid}/ask", json={"question": "مرحبا"}, headers=h)
    assert "الحد اليومي" in r.get_data(as_text=True)
    assert called["n"] == 0  # the model was never called once capped


# ---------------------------------------------------------------- conversation ownership

def test_cannot_read_another_users_conversation(client) -> None:
    a1 = _admin()
    a2 = _admin()
    h1 = auth_header(client, email=a1.email)
    cid = _mk_conversation(client, h1)
    h2 = auth_header(client, email=a2.email)
    assert client.get(f"/assistant/conversations/{cid}", headers=h2).status_code == 403


# ---------------------------------------------------------------- architectural isolation

def test_assistant_module_does_not_import_business_models() -> None:
    """Read-only + no business-data access must be structural, not prompt-only:
    the assistant package never imports commerce/sales/partners/pos/accounting
    business models."""
    pkg = pathlib.Path(__file__).resolve().parents[1] / "app" / "assistant"
    forbidden = ("commerce.models", "sales.models", "partners.models", "pos.models", "accounting.models", "inventory.models")
    offenders: list[str] = []
    for py in pkg.rglob("*.py"):
        src = py.read_text("utf-8", errors="ignore")
        for mod in forbidden:
            if mod in src:
                offenders.append(f"{py.name}: {mod}")
    assert not offenders, f"assistant must not import business models: {offenders}"
