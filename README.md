# White Moon — منظومة وايت مون المتكاملة

B2B multi-vendor marketplace fused with a full ERP. Flask + Postgres + Celery/Redis. Web-first in v1; Flutter mobile apps deferred.

Status: **Web platform built and under active iteration.** Phases 1–13 (identity through BI/notifications) are implemented across the Flask backend and the React/Vite web app, with migrations `0001`–`0025` and a full test suite. Post-MVP refinement tickets **T-12 → T-26** are delivered (admin orders console, pro product form, category tree, per-page help + onboarding, Arabization, customer statement + exports, shipment board, customer receipt upload, supplier RFQ inbox, Arabic invoices, number formatting, periods fix, report exports). **Phase 14 (Flutter apps) is deferred.** `docs/` holds the architecture, schema skeleton, CoA, Journal Map, Credit-Rating Rules, and Backup/DR plan.

> Keep this status current. Each session reads it — leaving it stale makes tooling (and humans) assume the project is greenfield when it is not.

## Phase gates

Each phase ended with a stop/audit gate. Status below reflects what is in the repo today, not a forward plan.

| Phase | Epic | What ships | Status |
|---|---|---|---|
| 0 | — | Architecture docs, CoA, journal map, credit rules, backup plan, repo skeleton | ✅ done |
| 1 | 0 | Identity, RBAC, OTP, audit, 2FA, impersonation | ✅ done |
| 2 | 3 | Chart of Accounts, journal engine, 5 reports, period close, receipt OCR | ✅ done |
| 3 | 4 | Inventory, transfer orders, reorder escalation, shortages | ✅ done |
| 4 | 1 (backend) | Catalog, best-price, unified cart, RFQ, price-lock | ✅ done |
| 5 | 1 (frontend) | React/Vite web UI ("Nightfall" design system) | ✅ done |
| 6 | 5 | Credit tiers, limits, escalation (1–4 auto, 5 manual) | ✅ done |
| 7 | 6 | Agents, branches, deposits, monthly accrual | ✅ done |
| 8 | 9 | Logistics, slots, GPS, delivery proof | ✅ done |
| 9 | 8 | POS, shared inventory, EOD batch posting | ✅ done |
| 10 | 10 | Mediated chat, text filter, OCR image scan | ✅ done |
| 11 | 7 | Basic manufacturing orders | ✅ done |
| 12 | 11 | ETA-ready structure, EGP enforcement | ✅ done |
| 13 | — | BI dashboard, Notification Center, scheduled reports | ✅ done |
| 14 (later) | 2 | Flutter customer + supplier apps | ⏸ deferred — starts only after web is **released, live and client-confirmed stable for 14 consecutive days** (see `docs/00-stack-and-architecture.md` §1). |

## Local setup

```powershell
# Prereqs: Python 3.12, Docker Desktop, Node 20+, git
docker compose up -d       # postgres (:5433), redis, minio, mailhog
cd backend
$env:DATABASE_URL = 'postgresql+psycopg://wm:wm@localhost:5433/whitemoon'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m alembic upgrade head
python scripts/seed_dev.py      # RBAC + bootstrap admin + chart of accounts
python scripts/seed_mock.py     # demo customers/suppliers/orders/shipments/RFQs
flask --app app run --port 5055

# Frontend (separate terminal)
cd web && npm install && npm run dev    # http://localhost:5173  (proxies /api -> :5055)
```

Bootstrap admin: `admin@whitemoon.eg` / `ChangeMeNow!2026` (override via `BOOTSTRAP_ADMIN_EMAIL`/`_PASSWORD`). All seeded demo accounts share `WhiteMoon#2026`.

## Repo map

```
backend/   Flask app (app factory, Blueprints per domain) + Alembic migrations + tests
docs/      Signed-off architecture & accounting docs
scripts/   Dev + ops scripts (seed_dev, seed_mock, restore drill)
web/       React + Vite + TypeScript + Tailwind web app ("Nightfall" design system)
infra/     Terraform (deployment)
```

## Non-negotiables

Read `docs/00-stack-and-architecture.md` §5 before writing code.

- No `float` for money. Ever.
- Supplier identity never surfaces in a customer-facing response.
- Every sensitive mutation emits an `AuditEvent`.
- EGP only, enforced at DB level.
- Period-close enforcement in Postgres triggers.
- `audit.events` is append-only at the DB-role level.

## License

Proprietary — © White Moon. All rights reserved.
