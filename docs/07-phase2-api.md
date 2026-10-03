# 07 — Phase 2 API (EPIC 3: Accounting Engine)

Backend only. All endpoints JSON-in, JSON-out. Monetary values are strings
(serialized Decimals) — never floats.

Hard rules enforced by the stack:

- `(debit > 0 ∧ credit = 0) ∨ (debit = 0 ∧ credit > 0)` on every line (CHECK).
- `SUM(debit) = SUM(credit)` per entry (deferred Postgres trigger).
- `currency = 'EGP'` on every monetary row (CHECK).
- Inserts into `journal_lines` whose entry date is inside a closed period
  are rejected unless the session sets `app.allow_closed_period = 'yes'`,
  which only the manual-journal endpoint does — and only when the caller
  has `high.manual_journal.closed_period`.

## Running locally

```powershell
cd D:\Programming\marsoud\white-moon
docker compose up -d

cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = 'postgresql+psycopg://wm:wm@localhost:5433/whitemoon'
$env:JWT_SECRET_KEY = 'dev-jwt-key-at-least-32-bytes-long-please!!'
$env:FLASK_SECRET_KEY = 'dev'
$env:OTP_PROVIDER = 'console'
$env:OCR_PROVIDER = 'stub'

alembic upgrade head
python scripts\seed_dev.py        # identity + accounting seed
flask --app app run --port 5055
```

The seed prints how many accounts and map rows landed (85 accounts, 24 map
rows in the current CoA/journal revision 2).

## Endpoints

Everything below is prefixed with `/accounting`. Bearer the JWT access token.

### Periods

#### `POST /accounting/periods/ensure`  (`period.close`)

```json
{"year": 2026, "month": 10}
```

Idempotent. Returns the row id.

#### `POST /accounting/periods/close`  (`period.close`)

```json
{"year": 2026, "month": 10}
```

Flips `is_closed = true`. Emits `accounting.period.close`.

#### `POST /accounting/periods/reopen`  (`period.reopen`)

Flips `is_closed = false`. Emits `accounting.period.reopen`.

### Manual journal (US-3.6 override path)

#### `POST /accounting/journal/manual`  (`high.manual_journal`)

```json
{
  "entry_date": "2026-10-10",
  "description": "correction of OCR-mismatched October receipt",
  "reason": "finance review found receipt mis-attributed to supplier X",
  "allow_closed_period": false,
  "lines": [
    {"account_code": "1111", "debit": "250"},
    {"account_code": "4400", "credit": "250"}
  ]
}
```

- `description` and `reason` both ≥ 10 chars.
- `lines` must balance (sum debit = sum credit).
- Each line passes the `one_side` CHECK (exactly one of debit/credit > 0).
- `allow_closed_period: true` needs the additional `high.manual_journal.closed_period` permission.

Emits `accounting.journal.manual` with the reason captured in audit.

### Receipts (US-3.3)

#### `POST /accounting/receipts/upload`  (any authenticated user)

```json
{
  "image_s3_key": "receipts/customer-42/2026-10-10.jpg",
  "expected_amount": "500",
  "expected_reference": "REF-12345",
  "ocr_stub_amount": "500",
  "ocr_stub_reference": "REF-12345"
}
```

- With `OCR_PROVIDER=stub` (dev), the two `ocr_stub_*` fields prime the
  OCR response so you can smoke-test matching without an image.
- The real image bytes are not read in this stub path; in prod the service
  pulls them from object storage using `image_s3_key`.
- When OCR output matches `expected_*` → `status = matched`. Otherwise
  `manual_review` with the diff in `manual_review_reason`.

#### `POST /accounting/receipts/<receipt_id>/resolve`  (`period.close`)

```json
{"status": "matched"}       // or "rejected"
```

### Deferred terms (US-3.4)

#### `POST /accounting/deferred-terms`  (`period.close`)

```json
{
  "order_id": 7,
  "cash_price": "1000",
  "deferred_price": "1200",
  "early_settlement_discount": "100",
  "early_settlement_before": "2026-11-01"
}
```

- `deferred_price ≥ cash_price` enforced in Python + DB CHECK.
- No daily accrual — the whole deferred value is locked at creation.

#### `POST /accounting/deferred-terms/apply-early-discount`  (`period.close`)

```json
{"order_id": 7, "settled_on": "2026-10-20"}
```

Idempotent: calling twice is a no-op after the first application.

### Reports (US-3.5)

All five accept a filter body with ISO date strings:

```json
{
  "date_from": "2026-10-01",
  "date_to": "2026-10-31",
  "account_prefix": "11",       // optional
  "partner_type": "supplier",   // optional
  "partner_id": 7               // optional
}
```

| Endpoint | Permission | Returns |
|---|---|---|
| `POST /accounting/reports/trial-balance` | `period.close` | `rows[]` + `totals.balanced` |
| `POST /accounting/reports/income-statement` | `period.close` | `revenues[]`, `expenses[]`, `net_income` |
| `POST /accounting/reports/balance-sheet` | `period.close` | `assets[]`, `liabilities[]`, `equity[]`, `balances` |
| `POST /accounting/reports/cash-flow` | `period.close` | `sources[]`, `uses[]`, `net_cash_change` |
| `GET  /accounting/reports/general-ledger/<code>?date_from=...&date_to=...&limit=...` | `period.close` | per-account movements + running balance |

PDF/Excel export is a Phase 2.5 ops task (templates in WeasyPrint + openpyxl).
The JSON contract is stable and locked here.

## Event→journal catalog

Current (revision 2 of docs/03) covers:

- `order.placed.cash`
- `order.placed.deferred`
- `inventory.issued`   — **location-aware** per reviewer round 2
- `payment.ocr.matched.upload` / `payment.ocr.matched.confirm`
- `payment.early_discount.applied`
- `supply.received`
- `supplier.payment.recorded`
- `agent.deposit.received`
- `agent.commission.accrued`             — debits **5281**, not 5280
- `agent.investment_return.accrued`      — debits **5290**
- `production.mo.closed`

Add new events by inserting rows into `accounting.event_journal_map` with
`high.map.edit` and emitting `audit.events`.

## Audit actions written in Phase 2

- `accounting.period.close`, `accounting.period.reopen`
- `accounting.journal.manual`
- `accounting.receipt.upload`, `accounting.receipt.resolve`
- `accounting.deferred.create`, `accounting.deferred.early_discount`

Every one carries actor, target, reason (where present), IP, user-agent.

## Phase 2 stop & audit gate

```powershell
# A. Seed is right
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select count(*) from accounting.accounts"      # 85
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select count(*) from accounting.event_journal_map"  # 24
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select 1 from accounting.accounts where code='5281'"
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select 1 from accounting.accounts where code='5290'"
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select 0 from accounting.accounts where code='2121'"  # 0 rows

# B. End-to-end: open period, post a cash order via the engine, run TB
#    (do it from PowerShell against the running flask instance)
# Login as admin.high → close/reopen a period → trial balance.
```

### Full test suite

```powershell
pytest
```

Expected: 26 Phase-1 tests + ~35 Phase-2 tests, all green. Breakdown:

- `test_accounting_seed.py`      — CoA + event-map integrity (5 cases)
- `test_accounting_events.py`    — engine rules (10 cases)
- `test_accounting_periods.py`   — close + guard + override (3 cases)
- `test_accounting_reports.py`   — 5 reports (5 cases)
- `test_accounting_deferred.py`  — US-3.4 (5 cases)
- `test_accounting_receipts.py`  — US-3.3 stub flow (3 cases)
- `test_accounting_routes.py`    — end-to-end + RBAC (3 cases)

### What's deferred to Phase 2.5

- Real OCR engine wiring (Tesseract / Document AI).
- PDF (WeasyPrint) + Excel (openpyxl) templates for the five reports.
- Scheduled weekly report email (cross-cutting Notification Center).
- BI-dashboard aggregator (cross-cutting).

None of these change the Phase 2 contract — they add presentation on top.

When tests pass against your DB, say **"start Phase 3"** and I'll build
inventory + transfer orders + reorder escalation (EPIC 4).
