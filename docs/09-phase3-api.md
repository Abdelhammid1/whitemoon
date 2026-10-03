# 09 — Phase 3 API (EPIC 4: Inventory & Purchasing)

Backend only. JSON in/out. Quantities and money are NUMERIC(18,4) strings.
All amounts EGP.

Hard rules enforced:
- **Supplier isolation (US-4.1):** a supplier sees/edits only their own
  offers and stock. `best-price` never returns a supplier id.
- **Transfer → journal (US-4.2):** issuing and receiving a transfer each
  post an automatic journal via the accounting event-map; a transfer is
  single-category so account resolution stays unambiguous.
- **Responsible-party accounting (US-4.4):** resolving a shortage debits
  the supplier payable, the agent/branch receivable, or the unallocated
  loss account — picked by the responsible party.

## New accounting events (seeded into event_journal_map)

| Event | Debit | Credit |
|---|---|---|
| `inventory.transfer.issued` | 9100 clearing | source inventory (1151/1152/1153/1154 by location) |
| `inventory.transfer.received` | destination inventory | 9100 clearing |
| `shortage.resolved.supplier` | 2111/2112 (by category) | 1151/1152 |
| `shortage.resolved.partner` | 1141 (agent) / 1142 (branch) | 1151/1152 |
| `shortage.resolved.unallocated` | 5310 loss | 1151/1152 |

Seed now has **72 accounts, 35 map rows**.

## New permissions

- `product.manage` — create products (admin, staff)
- `inventory.manage` — adjust stock, run transfers, reorder check (admin, staff)
- `offer.manage` — manage own offers (supplier)
- `shortage.resolve` — resolve shortages (admin)

## Endpoints (prefix `/inventory`)

### Products

- `POST /inventory/products` (`product.manage`) — `{sku, name_ar, name_en?, category: food|clothing, unit?, eta_code?, food_expiry_tracked?}`
- `GET /inventory/products?q=&category=&limit=` (auth)
- `GET /inventory/products/<id>/best-price` (auth) — returns `{product_id, best: {best_price, moq} | null}`. **No supplier identity.**

### Offers (supplier-owned)

- `POST /inventory/offers` (`offer.manage`) — `{product_id, unit_price, moq?, is_active?}`; `supplier_id` is taken from the JWT, never the body.
- `GET /inventory/offers/mine` (`offer.manage`) — only the caller's offers.

### Stock

- `POST /inventory/stock/adjust` (`inventory.manage`) — `{supplier_id, product_id, location_type, location_id?, delta, reorder_point?}`
- `GET /inventory/stock-balances?supplier_id=&location_type=` — suppliers get only their own rows; admins/staff may pass `supplier_id`.

### Transfer orders

- `POST /inventory/transfers` (`inventory.manage`) — `{supplier_id, from_location_type, from_location_id?, to_location_type, to_location_id?, lines:[{product_id, qty, unit_cost}]}`. Creates a `draft` with number `TRF-YYYYMM-NNNNNN`. All lines must share one category.
- `POST /inventory/transfers/<id>/issue` (`inventory.manage`) — decrements source stock, posts `inventory.transfer.issued`, status → `issued`, links `issue_entry_id`.
- `POST /inventory/transfers/<id>/receive` (`inventory.manage`) — increments destination stock, posts `inventory.transfer.received`, status → `received`, links `receive_entry_id`.
- `GET /inventory/transfers/<id>` (auth; supplier can only read their own).

### Shortages

- `POST /inventory/shortages` (auth) — `{supplier_id, product_id, qty, unit_cost, transfer_order_id?, evidence_s3_keys:[...]}`. Evidence images are **required** (US-4.4 توثيق بالصور إلزامي).
- `POST /inventory/shortages/<id>/resolve` (`shortage.resolve`) — `{responsible_party_type: supplier|channel_partner|unallocated, responsible_party_id?, reason}`. Posts the matching journal; reason ≥5 chars, audited.
- `GET /inventory/shortages?status=` (`shortage.resolve`).

### Reorder

- `POST /inventory/reorder/check?supplier_id=` (`inventory.manage`) — opens level-1 `ReorderAlert`s for balances at/under their reorder point (deduped against open alerts).

## Audit actions

`inventory.product.create`, `inventory.offer.upsert`, `inventory.stock.adjust`,
`inventory.transfer.create|issue|receive`, `inventory.shortage.report|resolve`.

## Tests

14 new cases in `tests/test_inventory.py`:
- category enforcement, best-price hides supplier, offers endpoint isolation
- transfer issue+receive post the right journals and move stock; issue
  blocked without stock; mixed-category transfer rejected
- shortage resolved vs supplier → 2111, vs agent → 1141, unallocated → 5310
- reorder opens one alert and dedupes
- RBAC: customer can't create products, supplier isolation on stock endpoint

Full suite: **73 passed** (59 Phases 1–2 + 14 Phase 3). ruff clean, pyright
0/0/0.

## Phase 3 gate

```powershell
cd D:\Programming\marsoud\white-moon
docker compose up -d
cd backend; .\.venv\Scripts\Activate.ps1
$env:DATABASE_URL='postgresql+psycopg://wm:wm@localhost:5433/whitemoon'
alembic upgrade head          # 0003 already applied
python scripts\seed_dev.py    # 72 accounts, 35 map rows
pytest                        # 73 passed
```

## Deferred to later

- Reorder escalation ladder advancement (levels 2–4) via Celery Beat.
- Batch/expiry enforcement (FEFO) — model exists, no workflow yet.
- Barcode/QR per batch.
- Inventory UI — will be built from the Stitch design the user is
  exporting, not before.
