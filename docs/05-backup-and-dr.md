# 05 — Backup & Disaster Recovery

**Scope:** Postgres, object storage, application code, secrets. v1 cloud = AWS, region `me-south-1` (Bahrain). Mirrors the "استراتيجية نسخ احتياطي واسترجاع" cross-cutting item from the Epics doc.
**Status:** Draft for architectural review.

---

## 1 — Targets (RPO / RTO)

| Data class | Example | Recovery Point Objective | Recovery Time Objective |
|---|---|---|---|
| Financial (`accounting.*`, `audit.events`) | journals, chart of accounts | **≤ 5 minutes** (PITR) | ≤ 1 hour |
| Operational (`inventory`, `commerce`, `logistics`, `communications`) | orders, chats, shipments | ≤ 15 minutes | ≤ 2 hours |
| Object storage (receipts, chat images, invoices) | S3 buckets | ≤ 1 hour (replication lag) | ≤ 4 hours |
| Application code & infra | monorepo, Terraform | 0 (git) | ≤ 1 hour |
| Secrets | SES, Twilio, Google Maps keys | ≤ 1 day (manual rotation record) | ≤ 2 hours |

If a load-bearing financial write is lost, the whole system is suspect. 5-minute PITR is the floor.

## 2 — Postgres (RDS) strategy

- **Automated snapshots:** daily, retention **35 days**, encrypted with a dedicated KMS key.
- **Point-in-Time Recovery (PITR):** `backup_retention_period = 35`, continuous WAL to S3 managed by RDS. Allows restore to any second within window.
- **Multi-AZ:** sync replica in a second AZ in `me-south-1`. Automatic failover with ~60s DNS switch.
- **Cross-region snapshot copy:** nightly job copies the daily snapshot to `eu-south-1` (Milan) encrypted with a separate KMS key. Retention **90 days**. This is the off-site copy.
- **Logical dumps:** weekly `pg_dump --format=custom` per schema, uploaded to a Glacier Deep Archive bucket. Retention **7 years** (financial record requirement). Encrypted.
- **Monitoring:** CloudWatch alarm on failed snapshots, replication lag, and WAL archiving errors.

## 3 — Object storage (S3) strategy

- Separate buckets per concern: `wm-prod-receipts`, `wm-prod-chat`, `wm-prod-kyc`, `wm-prod-invoices`, `wm-prod-backups`.
- **Versioning enabled** on all buckets. Delete markers kept, lifecycle to Glacier after 90 days for old versions.
- **Object Lock in compliance mode** on `wm-prod-receipts` and `wm-prod-invoices`: once written, cannot be deleted or overwritten within 7 years. Protects financial evidence from both insiders and ransomware.
- **Cross-region replication** to `eu-south-1` for all buckets, same-account.
- **Server-side encryption** with KMS CMKs. Separate CMK for KYC.

## 4 — Secrets

- All secrets in **AWS Secrets Manager**, rotated per the schedule below.
- No secret in a `.env` file in staging or prod.
- Rotation schedule:
  - JWT signing keys: every **90 days**, with 24h overlap window.
  - DB master password: every **180 days**.
  - Twilio / Google Maps / SES: every **365 days** or on team departure.
- Secret access audited via CloudTrail; alerts on access outside the app's IAM role.

## 5 — Code & infrastructure

- Monorepo on GitHub (private, 2FA-mandatory on org). Mirror pushed nightly to a second provider (CodeCommit) for provider-outage insurance.
- Terraform state in S3 with DynamoDB lock table; state file is itself backed up by S3 versioning.
- Container images in ECR, immutable tags.

## 6 — Backup verification (not optional)

A backup that has never been restored does not exist. Scheduled drills:

| Drill | Frequency | Owner | Pass criterion |
|---|---|---|---|
| Restore last night's RDS snapshot into a sandbox DB, run smoke tests | **Weekly, Sunday 02:00 UTC** | On-call eng | All migrations clean, sample journal reconciles |
| PITR restore to a random point in the last 24h | **Monthly** | On-call eng | Table checksums match for 5 random tables |
| Cross-region failover drill (promote `eu-south-1` snapshot in isolation) | **Quarterly** | Eng lead | Sandbox app serves traffic end-to-end |
| Object-storage restore (delete + recover a test object) | **Monthly** | On-call eng | Object returns byte-identical |
| Full tabletop DR scenario with Abdel-Hameed | **Semiannually** | Eng lead + Finance | Decision tree followed under 2h |

`scripts/restore_drill.sh` automates the first three.

## 7 — Incident playbook (short form)

1. **Detect:** CloudWatch alarm or human report. Declare in `#incidents` with severity.
2. **Preserve:** snapshot current RDS + buckets *before* any remediation. Do not mutate the primary.
3. **Decide:** failover vs. restore. Rule of thumb — if the primary is corrupted (not just down), **restore**, don't fail over.
4. **Communicate:** status to the client every 30 min from T+0.
5. **Recover:** execute the matching runbook.
6. **Postmortem:** blameless, within 5 business days, outcomes logged.

## 8 — Legal / contractual retention

- Financial records (journals, invoices, receipts): **7 years** minimum per Egyptian commercial law. Enforced by S3 Object Lock + Glacier Deep Archive logical dumps.
- Audit log (`audit.events`): **5 years** minimum, append-only.
- KYC documents: **5 years** after supplier relationship ends.
- Chat messages subject to admin monitoring (US-10.3): **2 years**, then auto-purged (compliance with reasonable privacy expectation).

## 9 — Open items for sign-off

1. Approve 7-year retention and the Object Lock compliance mode (it is irrevocable per bucket).
2. Approve cross-region copy to `eu-south-1`. Alternative: `me-south-1` + a second cloud (GCP) if sovereignty concerns.
3. Approve the drill cadence and name the responsible on-call eng.
