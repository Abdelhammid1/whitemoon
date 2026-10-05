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
| `credit.nightly_scan` | daily 02:00 Africa/Cairo | `sales.services.escalation.nightly_scan`: recompute every active customer's credit tier, then open any due dunning/escalation events (docs/04 §1). Idempotent. |

Trigger it manually (eager, for a smoke test) from a Flask shell:

```python
from app.sales.services import escalation
escalation.nightly_scan()   # {'recomputed': N, 'escalations_opened': M}
```

## Still to layer on Celery (follow-ups)

- **Forced L3 colour downgrade + graduated de-escalation** (docs/04 §2) — a
  change to the *signed* credit classification; needs finance sign-off before
  implementation.
- **Real notification/OTP dispatch** — route `notifications.notify._dispatch`
  and OTP sending through Celery tasks once the SMS/WhatsApp/e-mail providers
  are wired (Twilio/SMTP credentials required).
- **Proactive 3-days-before-due reminders** (docs/04 §2) — a Beat task once the
  reminder channel is live.
