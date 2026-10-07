# 06 — Phase 1 API (EPIC 0: Identity & Permissions)

Working backend only. All endpoints JSON-in, JSON-out. Errors look like:

```json
{"error": "<code>", "message": "<human>"}
```

HTTP status reflects category (400, 401, 403, 404, 409, 422, 429); the `error`
code is stable and intended for i18n in the UI.

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

alembic upgrade head
python scripts\seed_dev.py       # creates bootstrap admin & RBAC baseline
flask --app app run --port 5055  # http://127.0.0.1:5055
```

The seed script prints the bootstrap admin credentials. Override via
`BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`.

## OTP delivery in dev

With `OTP_PROVIDER=console`, the server logs each OTP and the registration
response includes `otp.debug_code`. That field is `null` in staging/prod.

## Endpoints

### `POST /auth/register/customer`

```json
{
  "phone": "+201000000001",
  "email": "ahmed@example.com",
  "password": "secret-pw-123",
  "display_name": "أحمد"
}
```

Response `201`:

```json
{
  "user_id": 42,
  "status": "pending",
  "otp": {"channel": "sms", "expires_at": "...", "debug_code": "834217"}
}
```

### `POST /auth/register/supplier`

```json
{
  "phone": "+201000000002",
  "password": "secret-pw-123",
  "legal_name": "شركة الفجر للتوريدات",
  "commercial_register_no": "CR-12345",
  "tax_card_no": "TAX-98765",
  "national_id": "29800000000000"
}
```

Response `201` — same shape as customer. User stays `pending` even after
OTP; admin must approve.

### `POST /auth/otp/verify`

```json
{"user_id": 42, "code": "834217"}
```

Response `200`:

```json
{"user_id": 42, "status": "active", "kind": "customer"}
```

For suppliers, `status` is still `pending` — awaiting admin approval.

### `POST /auth/login`

```json
{"phone": "+201000000001", "password": "secret-pw-123"}
```

Response `200`:

```json
{
  "user_id": 42,
  "requires_2fa": false,
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci..."
}
```

If the user has 2FA enrolled and no `totp_code` was supplied:

```json
{"user_id": 42, "requires_2fa": true}
```

Re-POST with `"totp_code": "123456"` to complete.

### `POST /auth/logout`

Bearer the access token. Revokes it (JWT jti blacklist).

### `POST /auth/refresh`

Bearer the **refresh** token. Returns a new access token.

### `GET /auth/me`

```json
{"id": 42, "kind": "customer", "status": "active", "phone": "...", "email": null, "locale": "ar"}
```

### `POST /auth/2fa/enroll/start`

Returns a TOTP secret, an `otpauth://` URI (scan into Google Authenticator /
Authy), and 8 one-time backup codes. Backup codes are the only way back in
if the device is lost.

### `POST /auth/2fa/enroll/finish`

```json
{"code": "123456"}
```

Confirms the user set up their app correctly before 2FA becomes mandatory.

### Admin — require JWT with specific permissions

| Endpoint | Permission | Purpose |
|---|---|---|
| `GET /admin/users?q=&kind=&status=&limit=` | `user.read` | Filter/search users |
| `GET /admin/suppliers/pending` | `supplier.approve` | List pending supplier KYC |
| `POST /admin/suppliers/<id>/approve` | `supplier.approve` | Activate a supplier |
| `POST /admin/suppliers/<id>/reject` | `supplier.approve` | Reject w/ reason |
| `POST /admin/impersonate/start` | `user.impersonate` | "View as" (support) |
| `POST /admin/impersonate/<grant_id>/stop` | `user.impersonate` | End a session |

The reject body:

```json
{"reason": "Commercial register image is unreadable."}
```

The impersonate body:

```json
{"target_user_id": 42, "reason": "Debug missing-order ticket #142"}
```

Response includes a special access token whose claims carry `act` = admin id
and `imp` = grant id. Downstream audit events will record both.

## RBAC seed catalog

Roles (`code → name_ar / name_en`):

- `admin.high` → إدارة عليا / Senior Admin (holds `*` wildcard)
- `admin` → مدير / Admin
- `staff` → موظف شركة / Staff
- `customer` → عميل / Customer
- `supplier` → مورد / Supplier
- `agent` → وكيل / Agent
- `branch` → فرع / Branch

Permissions:

- `*` — wildcard, granted only to `admin.high`
- `user.read` — list users
- `user.impersonate` — view-as
- `supplier.approve` — approve/reject suppliers
- `credit.override` — override credit limit (Phase 6)
- `period.close`, `period.reopen` — accounting (Phase 2)
- `high.manual_journal`, `high.manual_journal.closed_period`, `high.map.edit`
- `admin.high` — senior-admin flag (Step 5 escalation, etc.)

## Audit log

`audit.events` is append-only. Phase 1 writes these actions:

- `user.register`, `supplier.register`
- `user.otp.verify`
- `user.login`
- `supplier.approve`, `supplier.reject`
- `user.impersonate.start`, `user.impersonate.stop`

Each event stores actor, target, dotted action, IP, user-agent, optional
reason, and before/after snapshots.

## Test harness

26 tests cover:
- Customer register → OTP → active
- Supplier register → OTP → *still pending* → admin approve/reject
- Password hashed (Argon2) and never stored plaintext
- Duplicate phone/email rejected
- OTP mismatch returns 401 and increments attempts
- Login w/ wrong password, suspended account, logout, /me revocation
- RBAC denies customer, admits admin, grants `admin.high` wildcard
- TOTP enrollment, 2FA-gated login, backup code single-use
- Impersonation audit trail (start + stop)

Run with:

```powershell
pytest
```

## Phase 1 — stop & audit gate

Smoke tests you can run yourself with the stack up:

```powershell
# 1. Register a customer
$body = @{phone="+201111111111"; password="secret-pw-123"; display_name="Test"} | ConvertTo-Json
$r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5055/auth/register/customer -Body $body -ContentType 'application/json'
$r | ConvertTo-Json

# 2. Verify OTP (debug_code from above)
$code = $r.otp.debug_code
$verify = @{user_id=$r.user_id; code=$code} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5055/auth/otp/verify -Body $verify -ContentType 'application/json'

# 3. Login
$login = @{phone="+201111111111"; password="secret-pw-123"} | ConvertTo-Json
$tok = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5055/auth/login -Body $login -ContentType 'application/json'

# 4. Me
Invoke-RestMethod -Uri http://127.0.0.1:5055/auth/me -Headers @{Authorization="Bearer $($tok.access_token)"}
```

Also inspect `audit.events` directly:

```powershell
docker exec white-moon-postgres-1 psql -U wm -d whitemoon -c "select at, action, actor_user_id, target_id from audit.events order by id desc limit 10;"
```

> **Historical note.** This is the original Phase-1 handoff doc. Phase 1 (and
> every phase through 13) is **built and merged** — see the status table in the
> root `README.md`. The accounting engine (EPIC 3 / Phase 2) described next in
> `docs/07-phase2-api.md` is implemented. Treat these `NN-phaseN-api.md` files as
> the original API specifications, not as the current project status.
