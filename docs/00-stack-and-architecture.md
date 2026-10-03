# 00 — Stack & Architecture

**Project:** White Moon (منظومة وايت مون المتكاملة) — B2B Multi-Vendor Marketplace + ERP
**Scope of this doc:** Final technology stack, service topology, host choice, and monorepo layout for v1.
**Author:** Zyad Wael
**Date:** 2026-10-03
**Status:** Second review — host swapped from AWS to Hetzner per Abdel-Hameed; mobile deferral precondition made explicit.

### Scope of v1 — web only, with an explicit mobile precondition

v1 ships the **web platforms only** (customer, supplier, admin). The two Flutter mobile apps (customer + supplier) are **conditionally deferred** — the condition is explicit, not a lapse:

> Mobile development does **not** begin until the full web platform is complete, released to production, and confirmed stable by the client in writing. "Complete and confirmed" means: all 11 Epics shipped on web, UAT signed off, and no open P0/P1 defects for 14 consecutive days.

Agents and branches already use the responsive web platform per the spec (US-2.3), so this does not block any Epic.

---

## 1. Stack decisions (locked)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Spec-aligned; strong OCR/AI libraries for US-3.3 (receipt OCR) and US-10.2 (phone-number OCR on images). |
| Web framework | Flask 3 (app factory + Blueprints) | Chosen by the client. Minimal, explicit, pairs cleanly with SQLAlchemy and Celery. |
| ORM | SQLAlchemy 2 (typed) | Mature, works with Alembic, supports multiple Postgres schemas natively. |
| Migrations | Alembic | Standard; supports branched schemas we need (identity / accounting / inventory / commerce / logistics / communications / audit). |
| Auth | Flask-JWT-Extended + Argon2 password hashing | US-0.1 (password hashing, never plaintext), US-0.2 (RBAC). JWT works across web and the future Flutter apps without rework. |
| 2FA | pyotp (TOTP) + a backup-codes table | US-0.3 and the "ميزة اضافية" under EPIC 0 (2FA for admin + agents). |
| OTP delivery | Pluggable provider interface. v1 adapters: Twilio SMS, Twilio WhatsApp Business API. | US-0.1 requires SMS or WhatsApp OTP. We abstract behind an interface so Egyptian local providers (Vodafone/WE/Etisalat gateways) can be swapped in without touching call sites. |
| Background jobs | Celery + Redis | OCR, notifications, OCR-on-image chat filter (US-10.2), scheduled reports (ميزة اضافية under EPIC 3), reorder escalations (US-4.3). |
| Scheduler | Celery Beat | Daily/weekly report emails, period-close reminders, credit-rating recomputation. |
| OCR engine | Tesseract via `pytesseract` for v1 behind an adapter interface; a hosted OCR provider can be swapped in later for receipts if accuracy demands. | US-3.3 (bank receipt matching) + US-10.2 (phone-number detection in images). |
| File storage | **Hetzner Object Storage** (S3-compatible API; standard `boto3` client with endpoint override). Local S3Mock in dev. | Receipts, chat images, supplier KYC docs, invoice PDFs, backups. |
| Email | SMTP via a transactional provider (SendGrid / Mailgun / local Egyptian provider) — chosen at provisioning time. | Weekly reports to Abdel-Hameed, order notifications, password resets. |
| Maps / GPS | Google Maps JS + Routes API for live tracking (US-9.2). Driver app sends GPS pings via WebSocket. | Egypt has reliable Google Maps coverage; alternative Mapbox adapter kept behind an interface. |
| Realtime | Flask-SocketIO on Redis pubsub | GPS live updates (US-9.2), mediated chat (Epic 10), order status push. |
| PDF export | WeasyPrint (HTML → PDF) with Arabic/RTL support via a Noto Naskh / IBM Plex Sans Arabic font bundle. | Reports export per US-3.5. |
| Excel export | openpyxl | US-3.5 (both PDF and Excel). |
| Testing | pytest + pytest-flask + factory_boy + Playwright for E2E (Phase 5+) | Standard; fast, works with CI. |
| Type checking | pyright (strict on `backend/accounting`, basic elsewhere) | Required by global CLAUDE.md ("After editing Python/Flask files → check pyright and fix errors"). Strict on accounting because wrong types in money code = silent corruption. |
| Lint / format | ruff | One tool, fast, replaces flake8/isort/black. |
| Money type | `decimal.Decimal` throughout, stored as `NUMERIC(18,4)` in Postgres. **Floats are forbidden in any monetary field.** | Non-negotiable for an accounting system. |
| Currency | EGP only. Enforced at the DB level with a `currency` column that is `NOT NULL DEFAULT 'EGP' CHECK (currency = 'EGP')` on every monetary table. | US-11.2. |

Rejected / deferred: FastAPI (client asked for Flask), MongoDB (ACID is mandatory for accounting), MySQL (Postgres schemas + partial indexes + CHECK constraints are a better fit).

## 2. Host: **Hetzner** (locked by client — standard Manasati stack for Egypt projects)

Decision made by Abdel-Hameed in review round 3 (2026-10-03). Primary location **FSN1 (Falkenstein, Germany)** with hot standby in **NBG1 (Nuremberg)** across datacenters, mirroring other Manasati Egypt-facing deployments.

Nothing in the application code is Hetzner-specific — the storage adapter is S3-compatible, the SMS/WhatsApp adapter is behind an interface, and the DB is self-managed Postgres on Linux. See `docs/05-backup-and-dr.md` for the full host-side layout, backup chain, and failover plan.

## 3. Service topology (v1)

```
                                 Internet
                                     |
                        [Hetzner Load Balancer, TLS]
                                     |
            -------------------------+-------------------------
            |                        |                        |
   [Flask API × 2]            [SocketIO node × 2]       [Static web]
   (gunicorn, CCX23)          (gunicorn+eventlet)       (customer, supplier, admin SPAs)
            |                        |
            +-----------+------------+
                        |         Private vSwitch 10.10.0.0/16
         ---------------+---------------
         |                              |
  [Postgres primary]            [Redis — CPX21]
  CCX33 + Volume (FSN1)         (cache + queues + pubsub)
         |
         | streaming replica
         v
  [Postgres standby]  (NBG1, different DC)

Background:
   [Celery workers × N — CPX31]
      - ocr-worker        (receipts + image chat scan)
      - notification-worker (push/SMS/WhatsApp/email)
      - accounting-worker (period close, batch POS journal posting)
      - reports-worker    (scheduled report generation)
   [Celery Beat] — single instance, scheduled jobs

Backups + archive:
   [Hetzner Object Storage]     — receipts, chat, kyc, invoices (versioned, FSN1 + NBG1 mirror)
   [Hetzner Storage Box × 2]    — pgBackRest repo, GPG-encrypted logical dumps
```

Only the Load Balancer and a jump host face the public internet; everything else is on the private vSwitch. Secrets live in **HashiCorp Vault** (HA), not in `.env` files in prod. See §5 of `05-backup-and-dr.md`.

## 4. Monorepo layout

```
white-moon/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # create_app() factory
│   │   ├── config.py                # Config, DevConfig, TestConfig, ProdConfig
│   │   ├── extensions.py            # db, migrate, jwt, celery, socketio, redis
│   │   ├── identity/                # EPIC 0
│   │   │   ├── models.py            # User, Role, Permission, AuditEvent
│   │   │   ├── routes.py            # /auth/register, /auth/otp, /auth/login, /auth/2fa
│   │   │   ├── services.py
│   │   │   └── schemas.py           # pydantic-style request/response
│   │   ├── accounting/              # EPIC 3 — built in Phase 2
│   │   │   ├── models.py            # Account, JournalEntry, JournalLine, Period
│   │   │   ├── events.py            # event-to-journal mapping engine
│   │   │   ├── reports/             # trial_balance, income, balance, cashflow, ledger
│   │   │   └── routes.py
│   │   ├── inventory/               # EPIC 4
│   │   ├── commerce/                # EPIC 1, 5
│   │   ├── logistics/               # EPIC 9
│   │   ├── communications/          # EPIC 10
│   │   ├── pos/                     # EPIC 8
│   │   ├── production/              # EPIC 7
│   │   ├── compliance/              # EPIC 11
│   │   ├── notifications/           # cross-cutting Notification Center
│   │   ├── bi/                      # cross-cutting BI endpoints
│   │   └── common/
│   │       ├── money.py             # Decimal helpers, currency guard
│   │       ├── pagination.py
│   │       ├── errors.py
│   │       └── rbac.py              # @require_permission decorator
│   ├── migrations/                  # Alembic
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── factories/
│   ├── pyproject.toml
│   ├── pyrightconfig.json
│   ├── ruff.toml
│   └── wsgi.py
├── web/                             # (populated in Phase 5 from Stitch output)
│   ├── customer/
│   ├── supplier/
│   └── admin/
├── docs/
│   ├── 00-stack-and-architecture.md (this file)
│   ├── 01-db-schema-skeleton.md
│   ├── 02-chart-of-accounts.md       (SIGNATURE REQUIRED)
│   ├── 03-journal-map.md             (SIGNATURE REQUIRED)
│   ├── 04-credit-rating-rules.md     (SIGNATURE REQUIRED)
│   └── 05-backup-and-dr.md
├── scripts/
│   ├── seed_dev.py
│   └── restore_drill.sh
├── infra/                           # (added in Phase 1 end — Terraform skeleton)
├── .github/workflows/
│   └── ci.yml                       # lint, pyright, pytest, migrations check
├── .env.example
├── .gitignore
├── docker-compose.yml               # local: postgres, redis, minio, mailhog
└── README.md
```

Mobile apps live in a sibling `mobile/` folder when they begin. They're deferred under the **explicit precondition stated in §1 above**: web platform complete, released, and client-confirmed stable for 14 consecutive days before mobile work starts.

## 5. Non-negotiable architectural rules

These are enforced in code reviews and in CI where possible:

1. **No float for money.** Lint rule rejects `float` in any `backend/app/accounting/**` or any column typed as money in migrations.
2. **No raw SQL for monetary operations.** Journals go through the `events.post()` engine, never ad-hoc inserts.
3. **Supplier identity is never in a customer-facing API response.** Enforced by a response-schema guard in `commerce` tests.
4. **Every sensitive mutation emits an `AuditEvent`.** The decorator `@audited(action="supplier.approve")` wraps the handler; forgetting it fails a CI check that scans route handlers tagged `@sensitive`.
5. **Every monetary table has `currency NOT NULL DEFAULT 'EGP' CHECK (currency = 'EGP')`.** Alembic has a custom check in CI.
6. **Period-close enforcement.** A trigger on `journal_lines` rejects inserts/updates whose `entry_date` falls inside a `period` row with `is_closed = true`, unless the connection has set a session variable that only the "high privilege manual journal" endpoint sets.
7. **Audit log is append-only.** DB role for the app has `INSERT, SELECT` on `audit.events` and no `UPDATE/DELETE`.

## 6. Environments

| Env | DB | Users | Purpose |
|---|---|---|---|
| local | Dockerized Postgres | seeded | each developer |
| ci | ephemeral Postgres per job | synthetic | tests only |
| staging | Hetzner CCX13 Postgres (FSN1) | internal + Abdel-Hameed | acceptance per phase |
| prod | Hetzner CCX33 Postgres + NBG1 standby | real users | live |

Promotion is strictly: local → PR → ci green → merge → staging deploy → sign-off → prod deploy.

## 7. Open items for client sign-off before Phase 2

1. Confirm **FSN1 + NBG1** as the two Hetzner locations (default). Alternative HEL1 (Helsinki) if different latency / GDPR shaping is desired.
2. Confirm **Twilio** as the v1 SMS/WhatsApp provider, or name the preferred Egyptian gateway so we build its adapter first.
3. Confirm **Google Maps** JS/Routes API licensing budget is approved; otherwise we start on Mapbox.
4. Confirm the brand name on the identity provider / sender: "White Moon" vs "وايت مون" for Arabic-first OTP messages and emails.
