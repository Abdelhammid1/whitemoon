# 01 — Database Schema Skeleton

**Scope:** Table-level sketch of the Postgres schema, grouped into logical domains that map 1-to-1 to Epics. Columns are intentionally minimal — each phase fleshes out its own schema and ships its own Alembic migration.
**Status:** Draft for architectural review. Not final.

Conventions:
- All PKs are `BIGINT GENERATED ALWAYS AS IDENTITY` unless noted.
- All monetary columns are `NUMERIC(18,4) NOT NULL` paired with `currency CHAR(3) NOT NULL DEFAULT 'EGP' CHECK (currency = 'EGP')`.
- All tables carry `created_at timestamptz NOT NULL DEFAULT now()` and `updated_at timestamptz NOT NULL DEFAULT now()` (trigger-maintained).
- Soft deletes use `deleted_at timestamptz NULL`. Hard delete is forbidden for financial rows.
- All FKs are `ON DELETE RESTRICT` by default — accounting integrity trumps convenience.

---

## Schema: `identity` — EPIC 0

| Table | Purpose |
|---|---|
| `users` | Core user. `phone`, `email`, `password_hash` (argon2), `status` (`pending`, `active`, `suspended`, `locked`), `kind` (`customer`, `supplier`, `agent`, `branch`, `staff`, `admin`), `locale` (`ar`, `en`), `created_from_ip`. |
| `supplier_profiles` | Supplier-specific KYC. FK → `users`. `legal_name`, `commercial_register_no`, `tax_card_no`, `national_id`, `approval_status`, `approved_by`, `approved_at`, `rejection_reason`. |
| `customer_profiles` | Customer-specific. FK → `users`. `display_name`, `default_shipping_address_id`. |
| `channel_partner_profiles` | Agents and branches, per US-6 ملاحظات التنفيذية (one unified table with a `type` flag). FK → `users`. `type` (`agent`, `branch`), `geo_scope`, `commission_rate_pct`, `deposit_amount`. |
| `roles` | `code` (unique), `name_ar`, `name_en`, `is_system`. |
| `permissions` | `code` (unique dotted, e.g. `supplier.approve`), `description_ar`. |
| `role_permissions` | M2M. |
| `user_roles` | M2M. |
| `otp_requests` | `user_id`, `channel` (`sms`, `whatsapp`), `code_hash`, `expires_at`, `consumed_at`, `attempts`. |
| `totp_secrets` | 2FA. `user_id`, `secret_encrypted`, `enrolled_at`. |
| `backup_codes` | `user_id`, `code_hash`, `used_at`. |
| `sessions` | `user_id`, `jwt_jti`, `device`, `ip`, `issued_at`, `revoked_at`. |
| `impersonation_grants` | `admin_user_id`, `target_user_id`, `granted_by`, `reason`, `granted_at`, `revoked_at`. Full audit per US-0.3. |

## Schema: `audit` — cross-cutting

| Table | Purpose |
|---|---|
| `events` | Append-only. `actor_user_id`, `action` (dotted), `target_type`, `target_id`, `before_json`, `after_json`, `ip`, `user_agent`, `at`. App DB role has `INSERT, SELECT` only. |

## Schema: `accounting` — EPIC 3 (PHASE 2)

| Table | Purpose |
|---|---|
| `accounts` | Chart of Accounts. `code` (unique), `name_ar`, `name_en`, `parent_id`, `type` (`asset`, `liability`, `equity`, `revenue`, `expense`), `is_postable`, `eta_code`. |
| `periods` | `year`, `month`, `starts_on`, `ends_on`, `is_closed`, `closed_by`, `closed_at`. |
| `journal_entries` | `entry_no`, `entry_date`, `period_id`, `source` (`system`, `manual`), `source_event_type`, `source_event_id`, `description`, `posted_by`, `posted_at`, `reversed_by_entry_id`. |
| `journal_lines` | `entry_id`, `account_id`, `debit` (money), `credit` (money), `currency`, `partner_type`, `partner_id`, `description`. CHECK: exactly one of debit/credit non-zero. Trigger-enforced: SUM(debit) = SUM(credit) per entry. |
| `event_journal_map` | Business-rule table: `event_type` → ordered line templates. Changes to this table require a `high.manual_journal` audit event. Mirrors `docs/03-journal-map.md`. |
| `bank_receipts` | `uploaded_by`, `image_s3_key`, `ocr_amount`, `ocr_reference`, `status` (`pending`, `matched`, `manual_review`), `matched_payment_id`, `ocr_raw_json`. |
| `deferred_terms` | Shariah-compliant per US-3.4. `order_id`, `cash_price`, `deferred_price` (both locked at order time), `early_settlement_discount`, `early_settlement_before`. No daily accrual. |

## Schema: `inventory` — EPIC 4

| Table | Purpose |
|---|---|
| `products` | Catalog item, supplier-agnostic. `sku`, `name_ar`, `category` (`food`, `clothing`, …), `unit`, `eta_code` (US-11.1 "ETA-ready"), `food_expiry_tracked` bool. |
| `supplier_offers` | Separate from catalog per EPIC 1 ملاحظات التنفيذية. `product_id`, `supplier_id`, `price`, `moq`, `available_qty`, `is_active`. |
| `stock_balances` | Per-supplier, per-location. `supplier_id`, `product_id`, `location_type` (`supplier`, `channel_partner`, `customer_hold`), `location_id`, `on_hand`, `reserved`, `reorder_point`. |
| `transfer_orders` | First-class entity per US-4.2 ملاحظات التنفيذية. `number`, `from_location_type`, `from_location_id`, `to_location_type`, `to_location_id`, `status`, `issued_by`, `journal_entry_id` FK. |
| `transfer_order_lines` | `transfer_order_id`, `product_id`, `qty`, `unit_cost`. |
| `batches` (optional expansion from spec) | For food expiry. `product_id`, `supplier_id`, `batch_code`, `expiry_date`, `qty`. |
| `shortages` | US-4.4. `reporter_user_id`, `transfer_order_id`, `product_id`, `qty`, `responsible_party_type`, `responsible_party_id`, `evidence_s3_keys[]`, `resulting_journal_entry_id`. |

## Schema: `commerce` — EPICs 1, 5

| Table | Purpose |
|---|---|
| `product_views` | For "best price" caching only. Pre-computed per product + optional geo bucket. |
| `carts` | `customer_id`, `status` (`active`, `checked_out`, `abandoned`). |
| `cart_items` | `cart_id`, `product_id`, `supplier_offer_id`, `qty`, `price_locked_until`. |
| `orders` | `number`, `customer_id`, `status`, `payment_mode` (`cash`, `deferred`), `total_cash`, `total_deferred`, `placed_at`, `credit_check_at`. |
| `order_sub_orders` | One per supplier within the unified cart (US-1.2 — invisible to the customer). `order_id`, `supplier_id`, `status`, `subtotal`. |
| `order_lines` | `sub_order_id`, `product_id`, `supplier_offer_id`, `qty`, `unit_price`, `line_total`. |
| `rfqs` | US-1.4. `initiator_user_id`, `initiator_type` (`customer`, `supplier`), `product_id`, `qty`, `deadline`, `qualification_requirements`, `status`. |
| `rfq_offers` | `rfq_id`, `supplier_id`, `unit_price`, `moq`, `submitted_at`. |
| `price_locks` | US-1.6. `supplier_offer_id`, `locked_qty`, `locked_price`, `expires_at`, `cart_item_id`. |
| `customer_credit_tiers` | `customer_id`, `tier` (`white`, `green`, `yellow`, `red`), `credit_limit`, `last_recomputed_at`. Four-color scheme per `docs/04-credit-rating-rules.md` (reviewer round 3, 2026-10-03). |
| `escalation_events` | US-5.3. `customer_id`, `level` (1..5), `triggered_at`, `trigger_reason`, `is_automatic`, `actor_user_id` (null for 1–4, required for 5). |

## Schema: `logistics` — EPIC 9

| Table | Purpose |
|---|---|
| `delivery_slots` | `slot_date`, `window_start`, `window_end`, `capacity`, `booked`. |
| `shipments` | Unified abstraction over internal + external (ملاحظات التنفيذية). `order_id`, `carrier_type` (`internal`, `external`), `carrier_ref`, `status` (`pending`, `in_transit`, `delivered`, `failed`), `scheduled_slot_id`, `assigned_courier_user_id`. |
| `courier_pings` | `shipment_id`, `lat`, `lng`, `at`. |
| `delivery_proofs` | `shipment_id`, `signature_s3_key`, `otp_confirmed`, `shortage_report_id`. |

## Schema: `communications` — EPIC 10

| Table | Purpose |
|---|---|
| `conversations` | `order_id` (nullable), `customer_id`, `supplier_id`, `started_at`. Server-mediated per US-10.1 — no direct peer link. |
| `messages` | `conversation_id`, `sender_user_id`, `kind` (`text`, `image`, `file`), `body`, `image_s3_key`, `filter_verdict` (`clean`, `blocked_text`, `blocked_ocr`, `manual_review`), `blocked_reason`. |
| `filter_rules` | Patterns and image-OCR thresholds; editable by admin with audit event. |

## Schema: `pos` — EPIC 8

| Table | Purpose |
|---|---|
| `pos_terminals` | `channel_partner_id`, `code`, `offline_queue_size`. |
| `pos_sales` | `terminal_id`, `sold_at`, `cashier_user_id`, `total`, `batch_id`. Inventory movement is immediate; accounting posts via `pos_sale_batches` nightly. |
| `pos_sale_lines` | `sale_id`, `product_id`, `qty`, `unit_price`, `line_total`. |
| `pos_sale_batches` | Dates and the single consolidated `journal_entry_id`. |

## Schema: `production` — EPIC 7

| Table | Purpose |
|---|---|
| `manufacturing_orders` | `number`, `output_product_id`, `output_qty`, `status`, `opened_at`, `closed_at`, `journal_entry_id`. |
| `mo_stages` | `mo_id`, `stage_no`, `name_ar`, `entered_at`, `exited_at`. |
| `mo_input_lines` | Materials consumed. `mo_id`, `product_id`, `qty`. |

## Schema: `notifications` — cross-cutting

| Table | Purpose |
|---|---|
| `notification_templates` | `code`, `channels[]` (push, sms, wa, email), `subject_ar`, `body_ar`. |
| `notifications` | `user_id`, `template_code`, `payload_json`, `sent_at`, `channel`, `status`. |
| `user_notification_prefs` | `user_id`, `channel`, `is_enabled`. |

---

## Cross-domain diagram (textual)

```
identity.users ───▶ supplier_profiles / customer_profiles / channel_partner_profiles
     │
     │ (actor on every mutation)
     ▼
audit.events  ◀──── every @audited handler

commerce.orders ─▶ order_sub_orders ─▶ order_lines ─▶ inventory.supplier_offers ─▶ inventory.products
     │
     ├─▶ accounting.event_journal_map ─▶ accounting.journal_entries ─▶ journal_lines ─▶ accounting.accounts
     │
     ├─▶ logistics.shipments ─▶ delivery_slots / courier_pings / delivery_proofs
     │
     └─▶ communications.conversations ─▶ messages (filtered)

inventory.transfer_orders ─▶ accounting (auto journal, US-4.2)
inventory.shortages        ─▶ accounting (debit responsible party, US-4.4)
pos.pos_sale_batches       ─▶ accounting (nightly consolidated, US-8.2)
production.manufacturing_orders (on close) ─▶ accounting (US-7.2)
```

## Open points for review

1. Should `products` be truly supplier-agnostic (single catalog, suppliers attach offers) or should each supplier maintain their own catalog and the admin curate a merged view? Spec leans toward option A — confirm.
2. Should `channel_partner_profiles.type` support future values (`master_agent`, `franchisee`)? If yes, use a small `partner_types` lookup table instead of an enum.
3. Confirm batch/expiry tracking is desired at v1 for food category (EPIC 4 "ميزة اضافية").
