# 15 — Phase 9 API (EPIC 9: Logistics)

Backend only. JSON in/out. Money NUMERIC(18,4), EGP only.

## Non-negotiables enforced

- **Capacity-bounded slots, no double-booking** (US-9.1) — each delivery slot
  has a hard `capacity`. Booking locks the slot row (`FOR UPDATE`), re-checks
  `booked < capacity`, and increments, so two concurrent bookings can never
  push a slot over capacity. A full slot is dropped from the available list.
- **One unified shipment status** (US-9.2 impl note) — `scheduled → shipped →
  in_transit → delivered` (or `failed`), identical whether the carrier is the
  internal fleet or an external company (`carrier_type`). Transitions are
  validated; `delivered` is reachable only through delivery confirmation.
- **Live location** (US-9.2) — the rep pushes `{lat, lng}`; the first ping
  moves a scheduled/shipped shipment to `in_transit`. The customer reads the
  current position + status from the order's tracking endpoint.
- **Electronic delivery proof** (US-9.3) — confirmation requires either the
  matching confirmation code (handed to the rep by the customer at booking)
  **or** a signature. A wrong code is rejected.
- **Shortages are the returns log** (US-9.3) — shortages recorded at delivery
  carry a photo URL and note and are tied to the shipment; they are the
  returns-log entries for delivery discrepancies.

## Schema (migration 0009 → schema `logistics`)

- `delivery_slots` — `slot_date`, `window`, `capacity`, `booked`,
  `is_active`; unique on (slot_date, window); `booked ≤ capacity` enforced by
  a CHECK as well as the booking logic.
- `shipments` — one per order: `order_id`, `slot_id`, `carrier_type`,
  `carrier_ref`, `status`, `current_lat/lng`, `confirmation_code`,
  `signature`, `delivered_by`, and the timestamps.
- `delivery_shortages` — `shipment_id`, `product_id`, `qty`, `photo_url`,
  `note`.

## Endpoints (`/logistics`)

| method | path | permission | notes |
|--------|------|------------|-------|
| POST | `/logistics/slots` | `logistics.manage` | create a slot |
| GET | `/logistics/slots?from=&to=` | any authenticated | available (not full) slots |
| POST | `/logistics/book` | order owner or `logistics.manage` | `{order_id, slot_id, carrier_type}` → shipment + confirmation code |
| GET | `/logistics/orders/<id>/shipment` | order owner or `logistics.manage` | tracking (status + location) |
| POST | `/logistics/shipments/<id>/status` | `logistics.manage` | `{status}` (shipped/in_transit/failed) |
| POST | `/logistics/shipments/<id>/location` | `logistics.deliver` | `{lat, lng}` |
| POST | `/logistics/shipments/<id>/confirm` | `logistics.deliver` | `{confirmation_code?, signature?, shortages[]}` |

`logistics.manage` and `logistics.deliver` are held by `admin` and `staff`
(reps are staff); `admin.high` via `*`. A customer books and tracks only
their own order's shipment.

## Deferred (per the spec's "add if easy, else defer")

- **Dynamic ETA** (live time-to-arrival from distance + current load) —
  deferred; needs routing/geo integration. The fixed slot window is the v1
  promise, and `current_lat/lng` + `location_updated_at` are already stored,
  so an ETA layer can be added on top without schema changes.
