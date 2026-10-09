"""DeepSeek chat client (ticket §20/§27 — DeepSeek is the ONLY answer LLM).

OpenAI-compatible REST over httpx with token streaming. The API key is read
from the environment (kept in a secret/Vault in prod, never in code or logs).

When no key is configured the client runs in a clearly-labelled *mock* mode so
the full pipeline (retrieval, redaction, persistence, UI streaming) works in
dev/CI without calling out — it never fabricates system facts, it just states it
is offline and lists the context it would have used.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import httpx

_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))


def _api_key() -> str | None:
    key = os.getenv("DEEPSEEK_API_KEY")
    return key.strip() if key else None


def is_configured() -> bool:
    return _api_key() is not None


def health() -> dict:
    """Lightweight status for the admin's assistant page (no key is exposed)."""
    return {"configured": is_configured(), "model": _MODEL, "mode": "live" if is_configured() else "mock"}


def _mock_stream(messages: list[dict]) -> Iterator[str]:
    yield "⚠️ مساعد الذكاء الاصطناعي في وضع تجريبي (DeepSeek غير مُهيّأ على هذا الخادم). "
    yield "بمجرد ضبط مفتاح DeepSeek ستظهر إجابة كاملة معتمدة على معرفة النظام.\n\n"
    # Surface which knowledge the retrieval step found, without inventing facts.
    sys = next((m["content"] for m in messages if m["role"] == "system"), "")
    if "المصادر المسترجعة" in sys:
        tail = sys.split("المصادر المسترجعة", 1)[1][:600]
        yield "المصادر التي كان سيُعتمد عليها:\n" + tail


def complete(messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 300) -> str | None:
    """Non-streaming completion — used by the answer-quality judge. Returns the
    text, or None when DeepSeek isn't configured or the call fails (caller then
    skips judging)."""
    key = _api_key()
    if key is None:
        return None
    payload = {"model": _MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_BASE_URL}/chat/completions", json=payload, headers=headers)
        if resp.status_code != 200:
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None


def chat_stream(
    messages: list[dict], *, temperature: float = 0.2, max_tokens: int = 1200
) -> Iterator[str]:
    """Yield answer text deltas. Raises nothing to the caller on a transport
    error mid-stream — it yields a short Arabic notice instead, so the UI never
    hangs (ticket §28: DeepSeek down → clear message, platform keeps working)."""
    key = _api_key()
    if key is None:
        yield from _mock_stream(messages)
        return

    payload = {
        "model": _MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            with client.stream(
                "POST", f"{_BASE_URL}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status_code != 200:
                    yield "تعذّر الاتصال بمساعد الذكاء الاصطناعي حاليًا. حاول مرة أخرى لاحقًا."
                    return
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    if delta:
                        yield delta
    except httpx.HTTPError:
        yield "تعذّر الاتصال بمساعد الذكاء الاصطناعي حاليًا. المنصة تعمل بشكل طبيعي."
