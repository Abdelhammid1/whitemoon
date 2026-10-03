# 12 — Phase 6 API (EPIC 6: Agents & Branches)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only. One domain serves
both agents and branches; the `type` on `identity.channel_partner_profiles`
discriminates.

## Non-negotiables enforced

- **One partner model, `type` discriminates** (US-6 impl note) — agents and
  branches share tables; behaviour differs by `type`, not by a second model.
- **Deposits are recoverable liabilities** (US-6.1) — recording a deposit
  posts `agent.deposit.received` (debit 1111 cash / credit **2120 Agent
  Deposits**, a liability). Recovery conditions are mandatory and stored on
  the row. A refund posts `agent.deposit.refunded` (reverse).
- **Branches earn neither commission nor investment return** (US-6.3) —
  `set_terms` rejects enabling either for a `branch`. (The UI additionally
  hides those screens; the backend refuses the data regardless.)
- **Accruals are server-computed** (US-6.2) — the monthly commission /
  investment-return amount is `basis × rate`, where basis = the partner's
  **realized** sales that month. Never client input.
- **Realized = confirmed or fulfilled** — pending and cancelled orders never
  enter the accrual basis.
- **One accrual per (partner, kind, year, month)** — a repeat call is
  rejected (`accrual_exists`), so a period is never double-posted.
- **Audit is atomic** — every mutation emits its audit event inside the
  service transaction (so it commits with the change, never after it).

## Accounts & events (already in the signed CoA / journal map)

| event | debit | credit |
|-------|-------|--------|
| `agent.deposit.received` | 1111 الصندوق | 2120 تأمينات الوكلاء |
| `agent.deposit.refunded` | 2120 تأمينات الوكلاء | 1111 الصندوق |
| `agent.commission.accrued` | 5281 عمولة الوكلاء — مصروف | 2130 عمولات مستحقة |
| `agent.investment_return.accrued` | 5290 عائد استثماري — مصروف | 2140 عوائد مستحقة |

## Schema (migration 0006 → schema `partners`)

- `partner_terms` (PK partner_user_id) — `earns_commission`,
  `commission_rate_pct`, `earns_investment_return`,
  `investment_return_rate_pct`.
- `partner_deposits` — `amount`, `deposit_date`, `recovery_conditions`,
  `status` (`held` | `refunded`), `refunded_at`, `refund_reason`, and the two
  journal-entry links.
- `partner_accruals` — `kind` (`commission` | `investment_return`),
  `period_year`, `period_month`, `basis_amount`, `rate_pct`, `amount`,
  `computed_at`, `journal_entry_id`; unique on (partner, kind, year, month).
- `commerce.orders.partner_user_id` (new column) — attributes a realized sale
  to the agent/branch whose scope it falls in; the accrual basis.

## Endpoints (`/partners`)

| method | path | permission | notes |
|--------|------|------------|-------|
| GET | `/partners/<id>/terms` | self or `partner.manage` | entitlement |
| PUT | `/partners/<id>/terms` | `partner.manage` | branch can't earn |
| POST | `/partners/<id>/deposits` | `partner.manage` | `{amount, deposit_date, recovery_conditions}` → posts 2120 |
| GET | `/partners/<id>/deposits` | self or `partner.manage` | list |
| POST | `/partners/deposits/<dep_id>/refund` | `partner.manage` | `{reason}` — reverses |
| POST | `/partners/<id>/accruals` | `partner.manage` | `{kind, year, month}` — server-computed |
| GET | `/partners/<id>/accruals` | self or `partner.manage` | list |
| GET | `/partners/<id>/accruals/statement?kind=&year=&month=` | self or `partner.manage` | detailed basis (US-6.2 statement) |
| POST | `/partners/orders/<order_id>/attribute` | `partner.manage` | `{partner_id}` — attribute a sale |

`partner.manage` is a new permission held by `admin` (and `admin.high` via
`*`). A partner may read **their own** terms / deposits / accruals.

## Deferred (per the spec's "add if easy, else defer")

- **Partner performance-comparison dashboard** (sales / collection / late
  ratio across partners, admin-only). Deferred: a faithful collection/late
  metric needs partner-level dues attribution that doesn't exist yet;
  building it half-way would mislead. Revisit after logistics/POS land.
