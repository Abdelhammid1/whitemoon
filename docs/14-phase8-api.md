# 14 — Phase 8 API (EPIC 8: Point of Sale)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only.

## Non-negotiables enforced

- **Shared inventory, single source of truth** (US-8.2 impl note) — a POS
  sale deducts from the same `inventory.stock_balances` rows the main
  platform uses. There is no separate POS stock. Availability is checked
  before any deduction.
- **Stock is deducted immediately** — the moment a sale completes, so POS and
  the platform can never oversell the same unit.
- **Accounting is batched, not real-time** (US-8.2) — a completed sale is left
  `posted = false` and carries **no** journal. A settlement run posts the
  accounting for every unposted sale at once (e.g. end of day).
- **Settlement never double-posts** — it runs under a global advisory lock and
  only picks up `posted = false` sales; a second run with nothing pending is
  rejected (`nothing_to_settle`).
- **POS revenue is its own account line** — settlement posts `pos.sale.batch`,
  crediting the dedicated POS revenue accounts (4130 food / 4140 clothing),
  one journal entry per category.

## Settlement posting

For each category present in the batch:

| event | debit | credit |
|-------|-------|--------|
| `pos.sale.batch` | 1111 الصندوق (cash) | 4130 / 4140 POS revenue by category |

Balanced per entry (cash in = revenue out). COGS/inventory valuation on the
accounting side is **deferred** (same basis as production's cost layer):
stock quantity is already moved; a cost leg can be added later without
reworking the sale records.

## Schema (migration 0008 → schema `pos`)

- `pos_batches` — one settlement run: `posted_by`, `posted_at`, `sale_count`,
  `total`, `journal_entry_id`.
- `pos_sales` — `number`, `cashier_id`, `location_type`/`location_id`,
  `total`, `status` (`completed`|`voided`), `posted`, `batch_id`, `sold_at`.
- `pos_sale_lines` — `sale_id`, `product_id`, `supplier_id` (the shared stock
  slot drawn from), `category`, `qty`, `unit_price`, `line_total`.

## Endpoints (`/pos`)

| method | path | permission | notes |
|--------|------|------------|-------|
| POST | `/pos/sales` | `pos.sell` | `{location_type, location_id, lines[]}` → deducts stock, unposted |
| GET | `/pos/sales/<id>` | `pos.sell` | one sale |
| GET | `/pos/sales?posted=true|false` | `pos.sell` | list |
| POST | `/pos/settle` | `pos.settle` | `{entry_date?}` → posts all unposted in one batch |

`pos.sell` is held by `agent`, `branch`, `staff`, `admin`; `pos.settle` by
`admin` (finance). `admin.high` has both via `*`.

## Deferred (per the spec's "add if easy, else defer")

- **Offline queue** (sell while disconnected, sync on reconnect) — deferred.
  It is a mobile/client-side concern (the web app is online-first) and the
  server contract above already accepts a batch of sales, which is the sync
  endpoint such a queue would call. Revisit with the Flutter client.
