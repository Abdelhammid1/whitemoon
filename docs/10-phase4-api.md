# 10 — Phase 4 API (EPIC 1: Marketplace / Commerce)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only.

## Non-negotiables enforced

- **Supplier identity is never in a customer-facing response** (US-1.1):
  `/catalog/products`, `/commerce/cart`, and the customer order view expose
  no `supplier_id` or supplier name — only product + price. A dedicated test
  asserts the absence.
- **Unified multi-supplier cart** (US-1.2): one cart spans suppliers;
  checkout splits into one `order_sub_order` per supplier, hidden from the
  customer and visible only to admins.
- **Price-lock on reserved quantity** (US-1.6): adding to cart locks the
  offer price for that qty for 60 min. A supplier may lower a locked price
  (the live lock follows down, to the customer's benefit) but may **not
  raise** it while a lock is live — the offer-update path rejects the raise.
- **"Lower price exists" hint** (US-1.5): a supplier's own offer carries a
  bare `lower_price_exists` boolean — no competitor identity, no exact price.
- **RFQ offers hidden from the initiator** (US-1.4): the customer who opened
  an RFQ sees prices but not which supplier gave them; only admins see the
  supplier id.

## Schema (migration 0004_commerce)

`commerce.carts`, `cart_items`, `price_locks`, `orders`, `order_sub_orders`,
`order_lines`, `rfqs`, `rfq_offers` — all monetary columns carry
`currency CHECK = 'EGP'`.

## Journals on checkout

One journal **per category** present in the order:
- cash → `order.placed.cash` (dr 1131 customer-cash, cr 4110/4120)
- deferred → `order.placed.deferred` (dr 1132, cr 4110/4120 at cash price,
  cr 4200 spread). The whole-order spread (`deferred_total − cash_total`) is
  split across categories in proportion to each category's cash share, and a
  single Shariah `accounting.deferred_terms` row is created for the order.

## Endpoints

### Catalogue (customer-facing)

- `GET /catalog/products?q=&category=&limit=` — products + `best_price`,
  **no supplier**.

### Cart

- `GET /commerce/cart` — the caller's active cart (locked prices + totals).
- `POST /commerce/cart/items` — `{offer_id, qty}`; enforces MOQ; creates the
  price-lock. 201.
- `PATCH /commerce/cart/items/<id>` — `{qty}`; re-locks at the held price.
- `DELETE /commerce/cart/items/<id>` — removes the item, releases the lock.

### Checkout + orders

- `POST /commerce/checkout` —
  `{payment_mode: cash|deferred, deferred_total?, early_settlement_discount?,
  early_settlement_before?}`. Returns the customer order view (no suppliers).
- `GET /commerce/orders` — the caller's orders.
- `GET /commerce/orders/<id>` — customer sees the merged line view; an admin
  (holds `user.read`) sees the per-supplier sub-order breakdown.

### RFQ (US-1.4)

- `POST /commerce/rfqs` — `{product_id, qty, deadline?, qualification_requirements?}`.
- `GET /commerce/rfqs/<id>`.
- `POST /commerce/rfqs/<id>/offers` — **supplier only** — `{unit_price, moq?}`.
- `GET /commerce/rfqs/<id>/offers` — initiator sees price-only; admin sees
  supplier id.

### Inventory offer update (price-lock aware)

- `POST /inventory/offers` now rejects a price **raise** while any lock on
  that offer is live (`409 price_locked`); a **cut** is accepted and lowers
  the live locks. The offer's own listing (`GET /inventory/offers/mine`)
  includes `lower_price_exists`.

## Audit actions

`commerce.order.placed`, `commerce.rfq.create`, `commerce.rfq.offer`.

## Tests

12 new cases in `tests/test_commerce.py`:
- catalog browse + endpoint hide supplier
- supplier can't raise a locked price; can lower (lock follows)
- multi-supplier checkout splits into sub-orders, customer view has no supplier
- cash checkout posts the 1131 journal; deferred creates deferred_terms + spread
- checkout uses the locked price after a cut
- below-MOQ add rejected
- `lower_price_exists` hint without identity
- RFQ offers hidden from initiator, visible to admin
- cart endpoint hides supplier

Full suite: **85 passed** (73 Phases 1–3 + 12). ruff clean, pyright 0/0/0.

## Deferred to later phases

- Credit-limit enforcement at checkout (hook `credit_check_at` set now; full
  4-colour tiers + limits = Phase 6).
- Order fulfilment → `inventory.issued` journal + shipment (Phase 8 logistics).
- RFQ awarding workflow + qualification gating enforcement.
- "Save for later" cart, abandoned-cart recovery (EPIC 1 ميزة اضافية).
