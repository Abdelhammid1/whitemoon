# 21 — Background jobs & scheduling (Celery)

Celery runs asynchronous work and scheduled (cron-style) jobs against the Redis
broker. Deps and config already exist: `celery[redis]` + `redis` in
`backend/pyproject.toml`, and `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in
`.env.example` (Redis DB 1/2). Redis itself is the `redis` service in
`docker-compose.yml`.

## Layout

- `backend/app/celery_app.py` — the Celery application. Binds a Flask app
  context to every task (so tasks use the DB + services), sets the timezone to
  `Africa/Cairo`, and declares the Beat schedule.
- `backend/app/tasks.py` — task definitions, thin wrappers over the service
  layer. The logic lives in services, so it is unit-tested without a worker
  (`tests/test_celery_tasks.py`).

## Running (dev)

Redis must be up (`docker compose up -d redis`), then in two shells from
`backend/` with the app env loaded:

```
celery -A app.celery_app.celery_app worker --loglevel=info
celery -A app.celery_app.celery_app beat   --loglevel=info
```

On a Windows dev box use `--pool=solo` for the worker. In production (Hetzner)
the worker and Beat run as separate `systemd` services.

## Scheduled jobs

| job (task name) | schedule | what it does |
|---|---|---|
| `credit.nightly_scan` | daily 02:00 Africa/Cairo | `escalation.nightly_scan`: recompute every active customer's tier, then open due dunning/escalation events (docs/04 §1). Idempotent. |
| `credit.due_reminders` | daily 08:00 Africa/Cairo | `credit.due_reminders`: notify customers of open dues coming due in 3 days (docs/04 §2). In-app today; flip the channel to sms/whatsapp once a provider is configured. |

Also available (not scheduled): `notifications.dispatch(notification_id)` —
async delivery of one notification on its external channel.

Trigger a job manually (for a smoke test) from a Flask shell:

```python
from app.sales.services import escalation, credit
escalation.nightly_scan()   # {'recomputed': N, 'escalations_opened': M}
credit.due_reminders()      # count of reminders sent
```

## Notification delivery providers

`app/notifications/providers/delivery.py` sends SMS/WhatsApp (Twilio) and
e-mail (SMTP) **for real when configured**, and gracefully no-ops otherwise —
so nothing breaks before credentials exist, and delivery starts with no code
change once the env vars are set (see `.env.example`: `TWILIO_*`, `SMTP_*`).
`notify._dispatch` routes external channels through it; in-app is the stored
row. Delivery never raises — a provider failure cannot roll back a notification.

## Still to layer on (follow-ups)

- **Forced L3 colour downgrade + graduated de-escalation** (docs/04 §2) — a
  change to the *signed* credit classification; needs finance sign-off first.
- **Real OTP delivery** — point `identity.providers.otp_provider.TwilioProvider`
  at the same Twilio path (currently console-only in dev); needs credentials.
- Switch the due-reminder channel from in-app to SMS/WhatsApp once Twilio is
  live.
