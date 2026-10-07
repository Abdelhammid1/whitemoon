# 22 — Admin AI Assistant (DeepSeek + RAG)

Admin-only, **read-only** knowledge assistant that explains how the platform
works (roles, features, workflows, pages) — it never executes actions, never
reads business/customer data, and never sends secrets or business data to the
LLM.

## 1. Architecture

```
Admin UI (chat panel + /assistant page)
      │  question + current route (no screen data)
      ▼
Backend  app/assistant/            ── gated by permission `assistant.use`
  routes.py      REST + token streaming (no write endpoints into the domain)
  services/
    redaction.py   mask email/phone/amount/id/token  ← applied to EVERYTHING
    retrieval.py   pgvector cosine search (current index version)
    chat.py        orchestration: redact → cap → retrieve → prompt → DeepSeek
    indexer.py     scan code+docs, secret-scan, chunk, embed, version
    ocr.py         local Tesseract / pypdf (file never leaves the server)
  providers/
    embeddings.py  local bge-m3 (fallback: deterministic hash embedding)
    deepseek.py    OpenAI-compatible streaming (mock when no key)
  models.py        schema `assistant` (pgvector) — isolated from business data
```

Isolation is **structural**, not prompt-only: the `assistant` package imports no
business models (enforced by `tests/test_assistant.py::
test_assistant_module_does_not_import_business_models`) and has no operational-DB
access. Its only inputs are the admin's (redacted) question, the current route
string, and KB passages (code/docs).

## 2. Data flow & the egress boundary

The single point where anything leaves to DeepSeek is `deepseek.chat_stream()`.
**Every** message part sent there — the user's question, the retrieved KB
context, and the conversation history — is passed through `redaction` first
(`chat._egress_clean`). So even if a secret slipped past the indexer or a KB
chunk carried PII, it is masked before egress. Redaction records only *kind +
count* (`assistant.redaction_log`), never the value — this is the §23 egress
proof.

## 3. Security layers

| Concern | Control |
|---|---|
| Access | `assistant.use` permission (admin / admin.high), enforced on **every** route — not UI-hidden |
| Business data | No business-model imports, no operational-DB connection (structural) |
| PII/secret egress | Redaction at the egress boundary on question + context + history |
| Secrets at index time | `.env`/seed/git excluded; gitleaks (or regex) scan skips any hit |
| Read-only | No write/mutation endpoints into the domain; assistant never calls business services |
| Uploads | OCR/extract locally; original file held in memory, only redacted text leaves |
| Audit | Every ask → `audit.events` (`assistant.ask`), plus uploads and gap answers |
| Abuse | Per-admin daily message cap, reserved up front |

## 4. Configuration (env / secret store)

| Var | Default | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | DeepSeek key (Vault/secret; never in code). Absent → mock mode |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible base |
| `DEEPSEEK_MODEL` | `deepseek-chat` | model id |
| `ASSISTANT_EMBED_MODEL` | `BAAI/bge-m3` | local embeddings model |
| `ASSISTANT_DAILY_MESSAGE_CAP` | `200` | per-admin daily cap |
| `ASSISTANT_INDEX_ROOT` | repo root | root the indexer walks |

Install the embeddings model for real retrieval quality: `pip install -e ".[ai]"`
(pulls `sentence-transformers`; first run downloads bge-m3). Without it the app
runs in a **degraded** mode (deterministic fallback embedding) — the admin sees
a warning on the assistant page.

## 5. Knowledge base & reindexing (ticket §7)

Build/refresh the index:

```bash
cd backend
python scripts/reindex_assistant.py <git_sha>
```

It walks `docs/`, `README.md`, `DESIGN.md`, the user guide, `web/src/content`
(page-help T-17, onboarding T-18) and `backend/app` source; secret-scans and
skips any file that trips gitleaks/regex; chunks → embeds → stores a **new index
version**. Retrieval only reads the latest `ready` version, so a reindex is
atomic for readers; older versions are pruned on success. The current version is
shown to the admin on the assistant page (`GET /assistant/status`).

**Post-deploy hook.** Run the reindex on the server after a successful deploy and
migrate, e.g. in the deploy script:

```bash
python -m alembic upgrade head
python scripts/reindex_assistant.py "$GIT_SHA"
```

CI (`.github/workflows/ci.yml`, job `assistant-index-smoke`) runs the pipeline on
every push to `main` so indexing stays green.

## 6. Knowledge gaps (ticket §15)

When retrieval finds nothing relevant (top similarity below threshold) the
question is logged (already redacted) as a knowledge gap. Admins review and
answer them at **/assistant/gaps**; answered gaps become curated content to fold
into docs/help on the next reindex.

## 7. API surface (all under `assistant.use`)

- `POST /assistant/conversations` · `GET /assistant/conversations` · `GET /assistant/conversations/<id>`
- `POST /assistant/conversations/<id>/ask` → streams the answer (text/plain)
- `POST /assistant/upload` → `{text, redaction}` (local OCR + redaction)
- `GET /assistant/status` → index version, DeepSeek mode, today's usage/cap
- `GET /assistant/gaps` · `POST /assistant/gaps/<id>/answer`

## 8. Testing

`tests/test_assistant.py` covers permission gating, redaction (unit + egress of
question **and** KB context), structural isolation, knowledge-gap logging, the
daily cap, and conversation ownership. Extend with the §24 100-question suite as
content matures (see `tests/assistant_eval/` when added).

## 9. Maintenance checklist

- Rotate `DEEPSEEK_API_KEY` in the secret store; it never appears in code/logs.
- After large doc/feature changes, reindex (the deploy hook does this).
- Review `/assistant/gaps` periodically; answer and fold into `docs/`.
- Watch `assistant.redaction_log` and `audit.events` for egress proof / usage.
- If DeepSeek is down, the assistant shows a clear notice and the platform keeps
  working (answers degrade to the mock notice).
