"""Chat orchestration (ticket §11/§12/§14/§15/§16/§22/§28).

Pipeline per question:
  redact → persist (user) + audit → cap check → retrieve → build prompt
  → stream DeepSeek → persist (assistant) + usage + knowledge-gap detection.

Business/customer data never enters here: the only inputs are the admin's
(redacted) question, the current route string, and KB passages (code/docs).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import select

from ...extensions import db
from ...identity.services.audit import emit as audit_emit
from ..models import AsstConversation, AsstMessage, KnowledgeGap, UsageCounter
from ..providers import deepseek
from . import redaction, retrieval

MAX_HISTORY = 10
GAP_SCORE_THRESHOLD = 0.28
DAILY_MESSAGE_CAP = int(os.getenv("ASSISTANT_DAILY_MESSAGE_CAP", "200"))

_SYSTEM = """أنت «مساعد وايت مون» الداخلي، مخصص لمدير المنصة فقط. مهمتك شرح كيف يعمل النظام وكيفية استخدامه خطوة بخطوة.

قواعد إلزامية:
- أنت للقراءة والشرح فقط. لا تنفّذ أي إجراء ولا تدّعي أنك نفّذت شيئًا.
- اعتمد فقط على «المصادر المسترجعة» وسياق النظام أدناه. لا تخترع معلومات. إن لم تكفِ المصادر، قل بوضوح إنك لا تملك معلومات كافية.
- لا تملك أي وصول لبيانات العملاء أو المبيعات أو الفواتير أو أي بيانات تشغيلية — اشرح كيف يعمل النظام الذي يتعامل معها، لا محتواها.
- اللغة: العربية المصرية افتراضيًا، والمصطلحات التقنية بالإنجليزية. لو كان السؤال بالإنجليزية فأجب بالإنجليزية.
- كن مباشرًا وعمليًا ومنظّمًا. نسّق إجابتك بـMarkdown: عناوين قصيرة، وقوائم مرقّمة للخطوات، وجداول (Markdown tables) عند المقارنة بين عناصر مثل الأدوار أو الصلاحيات. اذكر روابط الصفحات الداخلية ذات الصلة عند فائدتها (مثل /admin/orders).
- خاطب مدير أعمال وليس مطوّرًا بالضرورة؛ اشرح المصطلح عند الحاجة."""


def _render_context(hits: list[retrieval.Hit], route: str | None) -> str:
    parts: list[str] = []
    if route:
        parts.append(f"الصفحة الحالية للمدير: {route}")
    if hits:
        parts.append("المصادر المسترجعة (استعن بها فقط):")
        for h in hits:
            label = h.title or h.source_path
            parts.append(f"\n[{h.source_type} · {h.source_path}] {label}\n{h.text.strip()[:1200]}")
    else:
        parts.append("لا توجد مصادر مسترجعة لهذا السؤال.")
    return "\n".join(parts)


def _egress_clean(text: str, *, scope: str = "egress") -> str:
    """Final redaction at the ONLY boundary where data leaves to DeepSeek.
    Applied to every message part (KB context + history), not just the user's
    question, so neither an indexed secret the scanner missed nor any PII can
    be sent out. Counts are logged (kind+count, never value) as egress proof."""
    return redaction.redact_and_log(text, scope=scope)


def _history_messages(conversation: AsstConversation) -> list[dict]:
    rows = db.session.execute(
        select(AsstMessage)
        .where(AsstMessage.conversation_id == conversation.id, AsstMessage.role.in_(("user", "assistant")))
        .order_by(AsstMessage.id.desc())
        .limit(MAX_HISTORY)
    ).scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def _today_usage(user_id: int) -> UsageCounter:
    today = datetime.now(UTC).date()
    row = db.session.execute(
        select(UsageCounter).where(UsageCounter.day == today, UsageCounter.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        row = UsageCounter(day=today, user_id=user_id, message_count=0, token_count=0)
        db.session.add(row)
        db.session.flush()
    return row


def answer(conversation: AsstConversation, question: str, *, route: str | None, actor_id: int) -> Iterator[str]:
    """Stream the assistant's answer. Side effects (persist, audit, usage, gap)
    happen at the boundaries so the stream itself only yields text."""
    # 1) redact the question and persist it (redacted), then audit.
    clean_q = redaction.redact_and_log(question, scope="question")
    clean_route = (route or "")[:300] or None
    db.session.add(AsstMessage(conversation_id=conversation.id, role="user", content=clean_q, meta={"route": clean_route}))
    audit_emit(
        "assistant.ask",
        actor_user_id=actor_id,
        target_type="assistant_conversation",
        target_id=conversation.id,
        reason=clean_route,
    )
    db.session.commit()

    # 2) daily cap — reserve the slot NOW (atomic-ish increment then commit), so
    #    an aborted/failing stream still counts and concurrent requests can't all
    #    slip under the limit by incrementing only on success.
    usage = _today_usage(actor_id)
    if usage.message_count >= DAILY_MESSAGE_CAP:
        msg = "لقد بلغت الحد اليومي لعدد رسائل المساعد. حاول مجددًا غدًا أو ارفع الحد من الإعدادات."
        db.session.add(AsstMessage(conversation_id=conversation.id, role="assistant", content=msg, meta={"capped": True}))
        db.session.commit()
        yield msg
        return
    usage.message_count += 1
    db.session.commit()

    # 3) retrieve + build the prompt. EVERY part that leaves to DeepSeek passes
    #    through redaction here (the egress chokepoint) — KB context and history
    #    included, not just the question.
    hits = retrieval.retrieve(clean_q, k=6)
    context = _egress_clean(_render_context(hits, clean_route), scope="context")
    history = [
        {"role": m["role"], "content": _egress_clean(m["content"], scope="history")}
        for m in _history_messages(conversation)
    ]
    messages = [{"role": "system", "content": f"{_SYSTEM}\n\n=== سياق النظام ===\n{context}"}] + history

    # 4) stream DeepSeek, accumulating for persistence.
    buf: list[str] = []
    for delta in deepseek.chat_stream(messages):
        buf.append(delta)
        yield delta
    full = "".join(buf).strip() or "—"

    # 5) persist assistant reply + usage + knowledge-gap detection.
    top = max((h.score for h in hits), default=0.0)
    is_gap = (not hits) or top < GAP_SCORE_THRESHOLD
    db.session.add(
        AsstMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=full,
            meta={
                "citations": [h.source_path for h in hits],
                "top_score": round(top, 3),
                "mode": deepseek.health()["mode"],
                "knowledge_gap": is_gap,
            },
        )
    )
    usage.token_count += (len(clean_q) + len(full)) // 4  # rough estimate (slot already reserved)
    if is_gap:
        db.session.add(
            KnowledgeGap(
                conversation_id=conversation.id,
                question=clean_q,  # already redacted
                context=redaction.redact_and_log(context[:1000], scope="gap"),
                route=clean_route,
                status="open",
            )
        )
    conversation.updated_at = datetime.now(UTC)
    db.session.commit()
