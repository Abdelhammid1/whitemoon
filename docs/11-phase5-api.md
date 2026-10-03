# 11 — Phase 5 API (EPIC 5: Sales & Customers — Credit System)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only. Implements the
signed `docs/04-credit-rating-rules.md`.

## Non-negotiables enforced

- **Four colour tiers only** — `white`, `green`, `yellow`, `red`. No orange
  (dropped per the signed contract).
- **Tier → default limit / deferred %** (`TIER_LIMITS`):
  | tier   | credit limit (EGP) | deferred % |
  |--------|--------------------|-----------:|
  | green  | 500,000            | 100%       |
  | white  | 250,000            | 60%        |
  | yellow | 100,000            | 40%        |
  | red    | 0                  | 0%         |
- **New / thin-history accounts are white** — fewer than 3 settled dues, or
  account age < 90 days, classifies white with `score = null`.
- **Red cannot defer** — any deferred order from a red customer is rejected
  (`deferred_blocked_red`); red is cash-only.
- **Credit limit is enforced at checkout** — a deferred order whose
  (outstanding open dues + order amount) exceeds the effective limit is
  rejected (`credit_limit_exceeded`). The effective limit is the active,
  non-revoked, non-expired override if one exists, else the tier default.
- **Override requires a reason (≥5 chars)** and is audited
  (`credit.override`); gated by `credit.override`.
- **Level 5 freeze is manual-only** — requires `admin.high`, records the
  acting admin's id, suspends the user, and is audited
  (`credit.freeze.level5`). Levels 1–4 are automatic from the overdue scan.
- **Payment date cannot be in the future** — judged against the Egypt
  business calendar (Africa/Cairo), not UTC, so a UTC+2 client sending
  "today" is never wrongly rejected (`paid_on_future`).

## Scoring (docs/04)

Window = last 365 days of settled dues. Score =
`100 × on_time_ratio − 10 × weighted_late`, clamped to [0, 100], where
weighted_late averages per-due penalty weights
(1/3/6/10 for 1–7 / 8–30 / 31–60 / 61+ days late, 20 for a default).

Tier from score + behaviour (strictest wins):
- **red** — score < 50, or any open due > 60 days overdue, or ≥1 default.
- **green** — score ≥ 85 and worst open due ≤ 30 days.
- **yellow** — otherwise.

A due paid > 90 days late is marked `defaulted` (not `paid`).

## 5-level dunning (US-5.3)

Automatic levels by worst open-due overdue days: 1 (1–7), 2 (8–15),
3 (16–30, also triggers an immediate tier recompute toward red), 4 (31–60).
A level is opened at most once per customer. Level 5 (full freeze) is manual.

## Schema (migration 0005_sales → schema `sales`)

- `customer_credit_tiers` — one row per customer: `tier`, `score`,
  `credit_limit`, `deferred_pct`, `last_recomputed_at`.
- `credit_overrides` — `credit_limit`, `reason`, `set_by`, `expires_at`,
  `revoked_at`. Highest live override wins.
- `customer_dues` — `amount`, `due_date`, `paid_date`, `days_late`,
  `status` (`open` | `paid` | `defaulted`), optional `order_id`.
- `escalation_events` — `level` (1–5), `trigger_reason`, `is_automatic`,
  `actor_user_id` (set for level 5), `triggered_at`.

## Endpoints (`/credit`)

| method | path                                    | permission        | notes |
|--------|-----------------------------------------|-------------------|-------|
| GET    | `/credit/customers/<id>`                | `user.read`       | tier, score, default + effective limit, deferred %, outstanding |
| POST   | `/credit/customers/<id>/recompute`      | `credit.manage`   | reclassify now |
| POST   | `/credit/overrides`                     | `credit.override` | `{customer_id, credit_limit, reason}` — audited |
| POST   | `/credit/dues/<id>/pay`                 | `credit.manage`   | `{paid_on}` ≤ business-today — audited |
| POST   | `/credit/escalation/run`                | `credit.manage`   | scans all open dues, opens levels 1–4 |
| POST   | `/credit/customers/<id>/freeze`         | `admin.high`      | `{reason}` — level 5, suspends user, audited |
| GET    | `/credit/customers/<id>/escalations`    | `user.read`       | event history |

`credit.manage` is a new write permission (finance staff); held by `admin`
and `staff`. Read endpoints keep `user.read`; the financial mutations
(`recompute`, `pay`, `escalation/run`) require `credit.manage`.

## Checkout integration

`commerce/services/orders.checkout` calls `credit.check_credit()` before
accepting a deferred order and `credit.record_due()` after, so the credit
limit and red-cannot-defer rules are enforced at the point of sale (lazy
import to avoid the commerce↔sales cycle).

### Concurrency & freshness guarantees

- **No stale tier at decision time.** `check_credit` recomputes the tier
  before deciding, so a customer who has defaulted since the last recompute
  is reclassified and blocked rather than let through on a cached green.
- **No limit-check TOCTOU.** `check_credit` takes a transaction-scoped
  Postgres advisory lock (`pg_advisory_xact_lock`) keyed on the customer,
  held through the whole checkout commit. Two concurrent deferred orders for
  the same customer are serialised — the second sees the first's committed
  due before its own limit check, so they can't both slip under the limit.
- Cash orders consume no credit and skip the check (and the lock) entirely.

## Permission model note

`credit.manage` is granted to `admin` (and `admin.high` via `*`) only — not
to the generic `staff` role; recording payments, recomputes, and running the
dunning scan are finance actions.
