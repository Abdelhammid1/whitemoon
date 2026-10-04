# 19 — Cross-cutting: BI dashboard + Notification Center

Backend + UI. Money NUMERIC(18,4), EGP only.

## BI dashboard

A single read-only executive view aggregating the critical indicators across
modules (the spec's "لوحة تحليلات (BI) موحّدة"). No schema of its own — it
reads existing tables.

- `GET /bi/dashboard` — permission **`bi.view`** (admin + admin.high). Returns:
  - **sales**: orders by status, realized revenue (confirmed+fulfilled cash).
  - **collection**: dues by status, outstanding, defaulted.
  - **inventory**: low-stock slots (on_hand ≤ reorder_point).
  - **pos**: unsettled total.
  - **logistics**: shipments by status.
  - **production**: manufacturing orders by status.
  - **communication**: open + flagged conversations.
- UI: `/dashboard` (finance), KPI tiles + status breakdowns.

## Notification Center

Unified multi-channel store (the spec's "مركز إشعارات موحّد"). Every
notification is persisted and shown in-app; non-in-app channels
(SMS/WhatsApp/e-mail) go through a pluggable dispatcher that is a **no-op stub**
in this version — the model and API are ready for a real provider (Twilio,
WhatsApp Cloud, SMTP) without an API change.

### Schema (migration 0018 → schema `notifications`)
- `notifications` — `user_id`, `type`, `title`, `body`, `channel`
  (`in_app`|`sms`|`whatsapp`|`email`), `is_read`, `created_at`.

### Endpoints (`/notifications`)
| method | path | who | notes |
|--------|------|-----|-------|
| GET | `/notifications?unread=` | authenticated | own inbox + unread count |
| POST | `/notifications/<id>/read` | owner | mark one read |
| POST | `/notifications/read-all` | owner | mark all read |
| POST | `/notifications` | `notify.send` (admin) | `{user_id, title, body?, type?, channel?}` |

UI: `/notifications` — list, per-item mark-read, mark-all; nav group visible
to every role. A reader only ever sees their own notifications; broadcasting
is admin-only.

## New permissions
`bi.view` and `notify.send` — granted to `admin` (and `admin.high` via `*`).

## Still deferred
Real SMS/WhatsApp/e-mail delivery (dispatcher is a stub); scheduled/event
-driven auto-notifications (e.g. firing a notification from the dunning run)
can be layered on `notify()` later.
