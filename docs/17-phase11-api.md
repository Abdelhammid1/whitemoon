# 17 — Phase 11 API (EPIC 11: Legal Compliance)

Backend only. JSON in/out.

## Non-negotiables enforced

- **Structurally ETA-ready, no live API** (US-11.1) — products carry an
  `eta_code` (item code) and an `eta_ready` flag; the chart of accounts
  already carries `eta_code`, and supplier profiles carry the tax number.
  Nothing calls the Egyptian Tax Authority in this version — the data is
  simply shaped so the integration can be switched on later without a
  rebuild. A product cannot be marked `eta_ready` without an item code.
- **EGP only, between Egyptian parties** (US-11.2) — enforced two ways:
  - **Structurally**: every monetary table has a `currency = 'EGP'` CHECK, so
    the database refuses a row in any other currency.
  - **At runtime**: `assert_egp(currency)` rejects a non-EGP currency on any
    code path that accepts one, with a clear error.

## Schema (migration 0011)

- `inventory.products.eta_ready` (boolean, default false) — the item-level
  tax-integration readiness flag.

## Endpoints (`/compliance`)

| method | path | permission | notes |
|--------|------|------------|-------|
| PUT | `/compliance/products/<id>/eta` | `product.manage` | `{eta_code?, eta_ready}` — can't be ready without a code |
| GET | `/compliance/eta-readiness` | `product.manage` | counts ready / not-ready, lists products missing an item code |

No new permission — this reuses `product.manage` (catalogue ownership).

## Deferred

The module has **no expansion suggestions** per the spec ("الأولوية الالتزام
الدقيق بالنطاق المعتمد" — priority is strict adherence to the approved
scope). The live ETA API submission is intentionally out of scope for v1.
