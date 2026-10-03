# 13 — Phase 7 API (EPIC 7: Production)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only. **Deliberately
minimal scope** (US-7): manufacturing orders tracked through predefined
stages, with automatic stock + journal on completion. No cost layer, no
resource scheduling — the relations allow adding those later without a
rebuild.

## Non-negotiables enforced

- **Material → finished product through predefined stages** (US-7.1) — a
  manufacturing order (MO) carries an ordered list of stages; it advances one
  stage at a time and tracks status (`draft` → `in_progress` → `completed`).
- **Automatic stock + journal on completion** (US-7.2) — completing an MO
  (only once every stage is `done`) deducts each material from stock, adds the
  finished good, and posts `production.mo.closed`. No manual stock edits.
- **No stock moves until completion** — advancing stages changes only status;
  the physical/accounting move happens once, atomically, at completion.
- **Idempotent completion** — a per-order advisory lock plus a status check
  means a second completion is rejected, never double-deducted or
  double-posted. Availability of every material is checked before any stock
  moves.

## Stock & accounting model

Stock is keyed in `inventory.stock_balances` by its owner (`supplier_id`).
An MO's `owner_id` is that key and `location_type='supplier'` (location_id
null) is the owner's own warehouse. Completion posts `production.mo.closed`
with `cost = Σ(material qty × unit_cost)` and the finished product's category:

| event | debit | credit |
|-------|-------|--------|
| `production.mo.closed` | 115x finished-good inventory (by category) | 115x material inventory (by category) |

With this basic scope (no labour/overhead), the two legs net to zero value —
material value is transformed into finished-good value at the same cost. The
entry records the event and stays balanced; a cost layer can later split the
legs across accounts.

## Schema (migration 0007 → schema `production`)

- `manufacturing_orders` — `number`, `owner_id`, `output_product_id`,
  `output_qty`, `location_type`/`location_id`, `status`,
  `total_material_cost`, `journal_entry_id`, `started_at`, `completed_at`.
- `mo_stages` — `mo_id`, `seq`, `name`, `status` (`pending` | `done`),
  `done_at`; unique on (mo_id, seq).
- `mo_materials` — `mo_id`, `product_id`, `qty`, `unit_cost`.

## Endpoints (`/production`, all `production.manage`)

| method | path | notes |
|--------|------|-------|
| POST | `/production/orders` | `{owner_id, output_product_id, output_qty, materials[], stages[]}` → draft |
| GET | `/production/orders/<id>` | full MO with stages + materials |
| GET | `/production/orders?owner_id=` | list |
| POST | `/production/orders/<id>/advance` | mark next pending stage done |
| POST | `/production/orders/<id>/complete` | `{entry_date?}` → consume + produce + post |
| POST | `/production/orders/<id>/cancel` | only while not completed |

`production.manage` is held by `admin` and `staff` (and `admin.high` via `*`).

Every mutation emits its audit event inside the service transaction.
