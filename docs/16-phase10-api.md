# 16 — Phase 10 API (EPIC 10: Communication)

Backend only. JSON in/out.

## Non-negotiables enforced

- **Mediated, no peer-to-peer** (US-10.1) — every message is created and
  stored server-side through `/comm`. There is no direct channel between the
  two parties.
- **Identity isolation** (US-10.1) — a participant's view of the other side
  is by role only (`counterpart_role`, `sender_role`); the counterpart's user
  id is never serialized to a participant. Only a moderator sees ids.
- **Contact exchange is blocked in any form** (US-10.2) — the filter catches:
  - digit runs (≥7) with separators/brackets: `01012345678`, `0101-234-5678`,
    `0 1 0 1 2 …`;
  - Arabic-Indic (`٠١٢`) and Persian (`۰۱۲`) numerals;
  - numbers spelled as words, Arabic and English (`صفر واحد …`, `zero one …`);
  - (bonus) e-mail addresses and social handles / links.
- **Images are OCR-scanned** (US-10.2) — an uploaded image is run through OCR
  (`pytesseract`, ara+eng) and the extracted text goes through the same
  filter, so a number photographed instead of typed is still caught.
- **Blocked ≠ deleted** — a message that fails the filter is stored with
  `status='blocked'` and a `block_reason`, is **not** delivered to the other
  party, but is retained (and audited) for moderator oversight (US-10.3).
- **Moderator oversight** (US-10.3) — a moderator reads every conversation and
  can filter by status and by `flagged` (has a blocked message).

## Filter thresholds

`MIN_PHONE_DIGITS = 7` and `MIN_SPELLED_DIGITS = 7` (Egypt landline is 7–8
local digits; mobile 11). The bar is deliberately low: over-blocking a long
numeric string is acceptable here, letting a phone number through is not.

## Schema (migration 0010 → schema `comm`)

- `conversations` — `order_id?`, `customer_id`, `supplier_id`, `status`
  (`open`|`closed`), `subject`.
- `messages` — `conversation_id`, `sender_id`, `sender_role`, `body`,
  `image_url`, `status` (`sent`|`blocked`), `block_reason`.

## Endpoints (`/comm`)

| method | path | permission | notes |
|--------|------|------------|-------|
| POST | `/comm/conversations` | `comm.moderate` | `{customer_id, supplier_id, order_id?, subject?}` |
| GET | `/comm/conversations?status=&flagged=` | authenticated | own conversations; moderator sees all |
| GET | `/comm/conversations/<id>/messages` | participant or moderator | isolation applied |
| POST | `/comm/conversations/<id>/messages` | participant or moderator | `{body?, image_url?, image_b64?}` → filtered |

`comm.moderate` is held by `admin` (and `admin.high` via `*`). Messaging is
open to the conversation's two participants; a non-participant is refused.

## Notes & deferral

- **Conversation creation is a moderator action** in v1 so that the supplier's
  identity is never exposed to the customer at creation time; a
  customer-initiated flow (supplier resolved from the order server-side) is a
  thin follow-up — the isolation guarantee already holds on every read.
- The e-mail / social-handle filter is the spec's optional extension, included
  because it is the same evasion by another channel and cheap to add.
