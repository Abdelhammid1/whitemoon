# White Moon — منظومة وايت مون المتكاملة

B2B multi-vendor marketplace fused with a full ERP. Flask + Postgres + Celery/Redis. Web-first in v1; Flutter mobile apps deferred.

Status: **Phase 0 — Foundations.** No app code yet; see `docs/` for the architecture, schema skeleton, Chart of Accounts, Journal Map, Credit-Rating Rules, and Backup/DR plan.

## Phase gates

Each phase ends with a stop/audit gate. Nothing moves forward until the gate's acceptance tests pass and (for Phase 0, 2, 6) the relevant document is signed.

| Phase | Epic | What ships | Gate |
|---|---|---|---|
| 0 | — | Architecture docs, CoA, journal map, credit rules, backup plan, repo skeleton | Three signatures from Abdel-Hameed |
| 1 | 0 | Identity, RBAC, OTP, audit, 2FA, impersonation | API tests + audit review |
| 2 | 3 | Chart of Accounts, journal engine, 5 reports, period close, receipt OCR | Seed-and-close test; all 5 reports render |
| 3 | 4 | Inventory, transfer orders, reorder escalation, shortages | Transfer + shortage flows + matching journals |
| 4 | 1 (backend) | Catalog, best-price, unified cart, RFQ, price-lock | Supplier-identity leak test green |
| 5 | 1 (frontend) | **Stitch prompt produced; UI built from Stitch output** | Visual review against docs; Playwright E2E |
| 6 | 5 | Credit tiers, limits, escalation (1–4 auto, 5 manual) | Dunning simulation |
| 7 | 6 | Agents, branches, deposits, monthly accrual | Role-separation tests |
| 8 | 9 | Logistics, slots, GPS, delivery proof | GPS stream + double-book prevention |
| 9 | 8 | POS, shared inventory, EOD batch posting | Dual-channel inventory + journal reconcile |
| 10 | 10 | Mediated chat, text filter, OCR image scan | Bypass battery (text, Arabic numerals, image) |
| 11 | 7 | Basic manufacturing orders | End-to-end MO close with journal |
| 12 | 11 | ETA-ready structure, EGP enforcement | USD attempt blocked; ETA payload shape |
| 13 | — | BI dashboard, Notification Center, scheduled reports | Restore drill passes |
| 14 (later) | 2 | Flutter customer + supplier apps | Separate planning cycle |

## Local setup (will be fleshed out in Phase 1)

```powershell
# Prereqs: Python 3.12, Docker Desktop, Node (for later), git
cp .env.example .env
docker compose up -d       # postgres, redis, minio, mailhog
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
pytest
flask --app app run --debug
```

## Repo map

```
backend/   Flask app (app factory, Blueprints per Epic)
docs/      Signed-off architecture & accounting docs
scripts/   Dev + ops scripts (seed, restore drill)
web/       Frontend workspaces (populated in Phase 5 from Stitch)
infra/     Terraform (added in Phase 1 end)
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
