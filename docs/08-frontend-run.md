# 08 — Frontend run (Phase 1 + Phase 2 UI)

Vite + React 18 + TypeScript (strict) + Tailwind v4. Follows `DESIGN.md`
(Perplexity parchment + single deep-teal accent, flat, 900 px max width,
RTL Arabic as the primary direction).

**Scope on `web/`:** every endpoint already shipped on the backend —
auth (login, register customer + supplier, OTP verify, 2FA enroll, me),
admin (users list, pending suppliers approve/reject, impersonation
start/stop), and accounting (periods ensure/close/reopen, manual journal
with balance check, OCR receipts, deferred terms, and all five reports:
trial balance, income statement, balance sheet, cash flow, general
ledger).

## Local run

Run the backend first (see `docs/06-phase1-api.md` / `docs/07-phase2-api.md`):

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
python scripts\seed_dev.py
flask --app app run --port 5055
```

Then in another terminal:

```powershell
cd D:\Programming\marsoud\white-moon\web
npm install   # first time only
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server forwards `/api/*` → `http://127.0.0.1:5055/*` with the
`/api` prefix stripped. So the frontend hits `/api/auth/login`, the proxy
turns it into `/auth/login` on Flask.

## Login as the bootstrap admin

The seed script creates `admin@whitemoon.local` with the default password
printed in the terminal (overridable via `BOOTSTRAP_ADMIN_EMAIL` /
`BOOTSTRAP_ADMIN_PASSWORD`). **However**, the backend's pydantic email
validator rejects `.local` TLDs. For a working login you have two options:

1. **Preferred — set the admin email at seed time to a real-shape domain:**
   ```powershell
   $env:BOOTSTRAP_ADMIN_EMAIL = 'admin@example.com'
   $env:BOOTSTRAP_ADMIN_PASSWORD = 'ChangeMeNow!2026'
   python scripts\seed_dev.py
   ```
2. Or create a fresh admin via the identity flow (register customer → verify OTP) and promote through `admin/users` once we build the role editor (not in this phase).

## Design conformance checklist

Every page follows the hard rules in `DESIGN.md`:

- Page canvas is **Parchment** `#faf8f5`; cards are **Soft Paper** `#fdfbfa`. Pure white never appears.
- Primary text is **Ink** `#27251e`; secondary is **Graphite** `#72706b`.
- **Deep Teal** `#016a71` is used only for: active sidebar item fill, "NEW" badge (via `Badge tone="teal"` — reserved; not used in Phase 1/2 pages yet), and the active chip in forms.
- Weight ladder is **400 / 500 only**. No bold.
- Radii: cards 16 px, inputs & filled buttons 12 px, ghost buttons 6 px, chips & badges 9999 px.
- One shadow only — `card-shadow` on elevated cards. Everything else is flat with hairline Warm Mist borders.
- 900 px max content width, 32 px section gap, 16 px card padding, 8 px element gap.
- RTL by default; Arabic strings everywhere; input fields that hold phone / email / numbers switch to `dir="ltr"` individually so the digits stay LTR as they must.
- Font stack: IBM Plex Sans Arabic → Inter → system-ui. (`pplxSans` is not licensed; the DESIGN.md explicitly names Inter as the substitute.)

## Static checks

- `npm run typecheck` — TypeScript strict, no errors (confirmed 2026-10-03).
- `npm run build` — Vite production build: 69 modules, 220 KB JS /
  13.75 KB CSS gzipped to 66.9 KB + 3.7 KB.

## Routes

| Public (unauth) | What |
|---|---|
| `/login` | Phone or email + password + optional TOTP code |
| `/register` | Customer registration |
| `/register/supplier` | Supplier registration (KYC inputs) |
| `/otp` | OTP verify (reads `user_id`, `channel`, `debug` from the query string) |

| Protected | Role gate |
|---|---|
| `/` | all authenticated |
| `/2fa` | all authenticated (admins and above see this in sidebar) |
| `/admin/users` | admin + staff |
| `/admin/suppliers/pending` | admin + staff |
| `/admin/impersonation` | admin + staff (service calls still enforce `user.impersonate`) |
| `/accounting/periods` | admin + staff (backend permission is `period.close` / `period.reopen`) |
| `/accounting/journal/manual` | admin + staff (backend: `high.manual_journal`) |
| `/accounting/receipts` | any authenticated for upload; resolve needs finance |
| `/accounting/deferred` | admin + staff |
| `/accounting/reports/trial-balance` | admin + staff |
| `/accounting/reports/income-statement` | admin + staff |
| `/accounting/reports/balance-sheet` | admin + staff |
| `/accounting/reports/cash-flow` | admin + staff |
| `/accounting/reports/general-ledger` | admin + staff |

Sidebar hides sections the current user is not allowed to see; the backend
is still the source of truth and will return `403` to any direct call that
bypasses the sidebar.

## Not in scope here

- No inventory UI yet — Phase 3 backend is still in progress (models +
  migration `0003_inventory` written locally, services/routes TODO).
- No marketplace UI — Phase 4 backend hasn't been built.
- No real OCR engine wiring — the receipts page uses the stub provider
  (fill the "OCR stub" fields in the form to simulate an OCR response).
- No PDF/Excel export yet — reports are JSON-only.
