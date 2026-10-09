"""Chat orchestration (ticket §11/§12/§14/§15/§16/§22/§28).

Pipeline per question:
  redact → persist (user) + audit → cap check → retrieve → build prompt
  → stream DeepSeek → persist (assistant) + usage + knowledge-gap detection.

Business/customer data never enters here: the only inputs are the admin's
(redacted) question, the current route string, and KB passages (code/docs).
"""

from __future__ import annotations

import json
import os
import re
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
# LLM-judge: after answering, grade the answer with DeepSeek and log a gap if it
# wasn't correct/accurate/clear/sufficient. Disable with ASSISTANT_JUDGE_ENABLED=0.
JUDGE_ENABLED = os.getenv("ASSISTANT_JUDGE_ENABLED", "1") != "0"

# The reply itself admitting it couldn't answer (covers cases where retrieval
# was "confident" but the answer was a refusal / "not enough info").
_INSUFFICIENT_RE = re.compile(
    r"(مش كافي|غير كافي|غير كافية|لا أملك معلومات كافية|مش عندي معلومات كافية|"
    r"المصادر .{0,20}(مش|غير) كافية|محتاج مصادر إضافية|مش شايف في المصادر|"
    r"معلومة ناقصة|معلومات ناقصة|لا توجد معلومات كافية|لا أعرف|مش عارف|مش قادر أجاوب|"
    r"not enough info|insufficient information|don'?t have enough|cannot answer)",
    re.IGNORECASE,
)

_JUDGE_SYSTEM = (
    "أنت مُقيّم صارم لجودة إجابات مساعد داخلي للمدير. احكم فقط بناءً على السؤال "
    "والمصادر المتاحة وإجابة المساعد، ولا تضف معلومات من عندك."
)


def _answer_insufficient(text: str) -> bool:
    return bool(_INSUFFICIENT_RE.search(text or ""))


def _judge_answer(question: str, context: str, answer: str) -> tuple[bool, str | None]:
    """Ask DeepSeek to grade the answer. Returns (adequate, reason). If the judge
    is unavailable it returns (True, None) so we never flag on judge failure."""
    out = deepseek.complete(
        [
            {"role": "system", "content": _JUDGE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"السؤال:\n{question}\n\n"
                    f"المصادر المتاحة للمساعد:\n{context[:1500]}\n\n"
                    f"إجابة المساعد:\n{answer[:1500]}\n\n"
                    "هل الإجابة صحيحة ودقيقة وواضحة وكافية فعلًا لفهم أو تنفيذ المطلوب بناءً على المصادر؟ "
                    "اعتبرها غير كافية لو اعتذرت أو قالت إنها لا تملك معلومات، أو خمّنت، أو كانت ناقصة الخطوات العملية، أو عامة جدًا. "
                    'ردّ بـJSON فقط: {"adequate": true|false, "reason": "سبب مختصر جدًا بالعربي"}'
                ),
            },
        ]
    )
    if not out:
        return (True, None)
    try:
        m = re.search(r"\{.*\}", out, re.S)
        data = json.loads(m.group(0)) if m else {}
        return (bool(data.get("adequate", True)), (str(data.get("reason") or "")[:500] or None))
    except (json.JSONDecodeError, ValueError):
        low = out.lower().replace(" ", "")
        if '"adequate":false' in low:
            return (False, out[:300])
        return (True, None)


def _log_gap(
    conversation_id: int, question: str, context: str, route: str | None,
    answer: str, source: str, detail: str | None,
) -> None:
    db.session.add(
        KnowledgeGap(
            conversation_id=conversation_id,
            question=question,  # already redacted
            context=redaction.redact_and_log(context[:1000], scope="gap"),
            route=route,
            assistant_answer=redaction.redact(answer[:2000]).text,
            source=source,
            detail=detail,
            status="open",
        )
    )

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


def log_user_feedback(*, conversation_id: int, question: str, answer: str, route: str | None = None) -> None:
    """Record a 👎 'الإجابة لم تفد' as a knowledge gap (#2) — the strongest
    signal, logged even when retrieval/judge thought the answer was fine."""
    clean_q = redaction.redact_and_log(question, scope="feedback")
    _log_gap(
        conversation_id, clean_q, context="", route=(route or "")[:300] or None,
        answer=answer, source="user_feedback", detail="المستخدم: الإجابة لم تفد",
    )
    db.session.commit()


def answer(conversation_id: int, question: str, *, route: str | None, actor_id: int) -> Iterator[str]:
    """Stream the assistant's answer. Side effects (persist, audit, usage, gap)
    happen at the boundaries so the stream itself only yields text.

    Takes the conversation *id* (not an ORM object): this generator runs after
    the request handler returns, so it loads the conversation in its own live
    session — passing a possibly-expired instance would raise
    DetachedInstanceError on the first attribute access."""
    conversation = db.session.get(AsstConversation, conversation_id)
    if conversation is None:
        return
    # 1) redact the question and persist it (redacted); title a fresh conversation
    #    from its first question (within this live session), then audit.
    clean_q = redaction.redact_and_log(question, scope="question")
    clean_route = (route or "")[:300] or None
    if not conversation.title:
        conversation.title = redaction.redact(question).text[:80]
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

    # 5) persist assistant reply + usage. Gap detection (#1): weak retrieval OR
    #    the reply itself admitting it couldn't answer.
    top = max((h.score for h in hits), default=0.0)
    retrieval_gap = (not hits) or top < GAP_SCORE_THRESHOLD
    heuristic_gap = _answer_insufficient(full)
    is_gap = retrieval_gap or heuristic_gap
    source: str | None = "retrieval" if retrieval_gap else ("heuristic" if heuristic_gap else None)
    detail: str | None = None

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
    conversation.updated_at = datetime.now(UTC)
    db.session.commit()

    # 5b) LLM judge (#1, user's request): if not already flagged, ask DeepSeek to
    #     grade correctness/accuracy/clarity/sufficiency and log a gap if poor.
    if not is_gap and JUDGE_ENABLED:
        adequate, reason = _judge_answer(clean_q, context, full)
        if not adequate:
            is_gap, source, detail = True, "judge", reason

    if is_gap:
        _log_gap(conversation.id, clean_q, context, clean_route, full, source or "retrieval", detail)
        db.session.commit()
