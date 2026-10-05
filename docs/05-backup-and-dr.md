# 05 — Backup & Disaster Recovery

**Scope:** Postgres, object storage, application code, secrets. v1 host = **Hetzner** (standard Manasati stack for Egypt projects). Mirrors the "استراتيجية نسخ احتياطي واسترجاع" cross-cutting item from the Epics doc.
**Status:** Second review — AWS specifics removed per Abdel-Hameed's instruction; everything is Hetzner-first.

### Changelog (reviewer round 3 — 2026-10-03)

- Full rewrite. All AWS primitives (RDS, S3, SES, Secrets Manager, CloudWatch, KMS, Object Lock, cross-region snapshot copy) replaced with Hetzner equivalents.
- Targets, retention windows, and drill cadences preserved — only infrastructure changed.

---

## 1 — Targets (RPO / RTO)

| Data class | Example | Recovery Point Objective | Recovery Time Objective |
|---|---|---|---|
| Financial (`accounting.*`, `audit.events`) | journals, chart of accounts | **≤ 5 minutes** (WAL streaming + archive) | ≤ 1 hour |
| Operational (`inventory`, `commerce`, `logistics`, `communications`) | orders, chats, shipments | ≤ 15 minutes | ≤ 2 hours |
| Object storage (receipts, chat images, invoices) | Hetzner Object Storage | ≤ 1 hour | ≤ 4 hours |
| Application code & infra | monorepo, Terraform/Ansible | 0 (git) | ≤ 1 hour |
| Secrets | SMS/WhatsApp keys, maps, SMTP | ≤ 1 day (manual rotation record) | ≤ 2 hours |

If a load-bearing financial write is lost, the whole system is suspect. 5-minute RPO is the floor.

## 2 — Compute topology on Hetzner

| Role | Hetzner product | Sizing (v1) | Notes |
|---|---|---|---|
| App VM (Flask + gunicorn + SocketIO) | **Hetzner Cloud CCX23** (dedicated vCPU) | 4 vCPU / 16 GB | 2× for HA behind a Hetzner Load Balancer |
| Postgres primary | **Hetzner Cloud CCX33** dedicated | 8 vCPU / 32 GB + **Volume** 100 GB (SSD, resizable) | Falkenstein (FSN1), AZ `fsn1-dc14` |
| Postgres hot standby (streaming replica) | **Hetzner Cloud CCX23** | 4 vCPU / 16 GB + Volume | Nuremberg (NBG1), AZ `nbg1-dc3` — different datacenter for AZ-level failure isolation |
| Celery workers | **Hetzner Cloud CPX31** | 4 vCPU / 8 GB | horizontal — 2+ |
| Redis | **Hetzner Cloud CPX21** | 3 vCPU / 4 GB | RDB snapshots + AOF |
| Object storage | **Hetzner Object Storage** (S3-compatible) | buckets per concern | region `fsn1` primary + `nbg1` replica |
| Backup archive | **Hetzner Storage Box BX21** (1 TB) | Nuremberg | pgBackRest repo + archived WAL + long-term dumps |

All VMs on a **private vSwitch** (`10.10.0.0/16`); only the Load Balancer and jump host face the public internet. Hetzner Cloud Firewall rules the LB → app, app → DB/Redis, DB → object-storage flows.

## 3 — Postgres strategy (self-managed, Hetzner-native)

We don't have a managed Postgres from Hetzner — this is the standard Manasati pattern already proven on other projects.

- **Backup tool: `pgBackRest`.** Chosen over `wal-g` for the easier retention policy syntax and built-in restore validation.
- **Repository:** Hetzner Storage Box (SFTP) `wm-prod-pgbackrest`.
- **Backup schedule (via systemd timers):**
  - Full backup every **Sunday 02:00 Africa/Cairo**.
  - Differential backup every weekday **02:00**.
  - WAL continuously archived to the Storage Box (push mode, `archive_push`).
- **Retention:**
  - `repo1-retention-full = 5` (keeps 5 weekly fulls → ~35 days PITR).
  - `repo1-retention-archive = 35` days of WAL.
- **PITR:** any second within the last 35 days is restorable; this gives the ≤ 5-min RPO.
- **Streaming replication:** physical replica in NBG1 with `synchronous_commit = remote_write` on money tables and `local` elsewhere, so a FSN1 datacenter loss costs no more than a few in-flight non-financial writes.
- **Logical dumps:** weekly `pg_dump --format=directory --jobs=4` per schema, GPG-encrypted, uploaded to **a second Storage Box in NBG1** (different data center from both primary and pgBackRest repo). Retention **7 years** for financial tables (`accounting.*`, `audit.events`), **5 years** for the rest.
- **Monitoring:** Prometheus `postgres_exporter` + Alertmanager rules on: WAL archive failure, replication lag > 30 s, backup job non-zero exit, disk usage > 70%.

## 4 — Object storage strategy

Hetzner Object Storage is S3-compatible; we use the standard `boto3` client with endpoint overrides.

- **Separate buckets per concern:** `wm-prod-receipts`, `wm-prod-chat`, `wm-prod-kyc`, `wm-prod-invoices`, `wm-prod-backups-logical`.
- **Versioning enabled** on all buckets. Delete markers are kept.
- **Immutability for financial evidence:** Hetzner Object Storage has versioning but no formal Object Lock / WORM compliance mode yet. We compensate with:
  - A **separate "cold" bucket per concern** (`-cold` suffix) replicated to NBG1, access limited to a dedicated IAM key that the app does *not* hold (held only by the backup worker role).
  - Nightly cron copies new objects into `-cold` and never deletes.
  - Finance / invoices additionally mirrored to the Storage Box archive (SFTP + GPG).
- **Server-side encryption at rest:** enabled per bucket. Client-side encryption with `age` for KYC and invoices (keys in Vault).
- **Cross-datacenter replication:** `rclone sync` cron FSN1 → NBG1 every 15 minutes, with `--immutable` so an upstream deletion doesn't propagate.

## 5 — Secrets

- **HashiCorp Vault** (OSS) running in HA on two Hetzner VMs, backed by **Consul** or **Integrated Raft Storage**. Auto-unseal via a KMS-shaped Hetzner shim is **not available**, so unseal is a bootstrap operation documented in the runbook (2-person).
- No secret in a `.env` file in staging or prod. The app reads via `vault agent` sidecar.
- Rotation schedule:
  - JWT signing keys: every **90 days**, 24h overlap window.
  - Postgres `wm` app role password: every **180 days**.
  - SMS/WhatsApp/Maps keys: every **365 days** or on team departure.
- Vault audit log → separate Loki instance, retained **1 year**.

## 6 — Code & infrastructure

- Monorepo on GitHub (private, 2FA mandatory on org). Nightly mirror push to a **Hetzner Storage Box git bundle** for provider-outage insurance.
- **Terraform** manages Hetzner Cloud resources; state in a Hetzner Object Storage bucket with versioning + a lock file in the same bucket (locking via `tflock` sidecar — Hetzner doesn't give DynamoDB-equivalent).
- Container images in a self-hosted **Harbor** registry on a Hetzner VM, immutable tags.
- Ansible playbooks for DB server, Vault, Harbor, monitoring — in the same repo under `infra/ansible/`.

## 7 — Backup verification (not optional)

A backup that has never been restored does not exist. Scheduled drills:

| Drill | Frequency | Owner | Pass criterion |
|---|---|---|---|
| Restore last pgBackRest full+diff into a sandbox VM, run smoke tests | **Weekly, Sunday 04:00 Africa/Cairo** | On-call eng | All migrations clean, sample journal reconciles |
| PITR restore to a random point in the last 24 h | **Monthly** | On-call eng | Table checksums match for 5 random tables |
| Datacenter failover drill: promote NBG1 standby, flip Load Balancer backend | **Quarterly** | Eng lead | Sandbox app serves traffic end-to-end within 1 h |
| Object-storage restore (delete + recover a test object via version history and `-cold` mirror) | **Monthly** | On-call eng | Object returns byte-identical |
| Full tabletop DR scenario with Abdel-Hameed | **Semiannually** | Eng lead + Finance | Decision tree followed under 2 h |

`scripts/restore_drill.sh` automates the first three (rewritten for Hetzner / pgBackRest in the Phase 2 ops task).

## 8 — Incident playbook (short form)

1. **Detect:** Alertmanager page or human report. Declare in `#incidents` with severity.
2. **Preserve:** snapshot current DB + buckets *before* any remediation. `pgBackRest --type=full` on-demand; `rclone copy` buckets to a timestamped prefix. Do not mutate the primary.
3. **Decide:** failover vs. restore. Rule of thumb — if the primary is corrupted (not just down), **restore**, don't fail over.
4. **Communicate:** status to the client every 30 min from T+0.
5. **Recover:** execute the matching runbook.
6. **Postmortem:** blameless, within 5 business days, outcomes logged.

## 9 — Legal / contractual retention

- Financial records (journals, invoices, receipts): **7 years** minimum per Egyptian commercial law. Enforced by `-cold` bucket immutability + Storage Box archive duplicates + GPG-encrypted monthly logical dumps retained 7 years.
- Audit log (`audit.events`): **5 years** minimum, append-only at the DB-role level.
- KYC documents: **5 years** after supplier relationship ends.
- Chat messages subject to admin monitoring (US-10.3): **2 years**, then auto-purged (compliance with reasonable privacy expectation).

## 11 — Implementation (scripts & timers)

Hetzner-native, no cloud CLI (the old AWS-RDS drill is removed):

- **`scripts/backup_pg.sh`** — logical `pg_dump` (custom format, compressed),
  verifies the archive (`pg_restore --list`), optional off-site `rclone copy`
  (`RCLONE_REMOTE`), and local retention pruning (`RETENTION_DAYS`). Auth via
  `PGPASSWORD`/`~/.pgpass`.
- **`scripts/restore_drill.sh`** — restores the latest dump into a throwaway
  `*_drill_*` database, smoke-checks it (`alembic_version` present +
  `accounting.accounts` populated), then drops it. Fails loudly so a broken
  backup is caught early. *Validated against the current schema (restored to
  rev 0021 with the 72-row chart of accounts intact).*
- **`deploy/systemd/`** — `wm-pg-backup.{service,timer}` (daily 01:30) and
  `wm-restore-drill.{service,timer}` (weekly Sun 03:00), with
  `backup.env.example` → `/etc/white-moon/backup.env` (chmod 600).

Logical dumps cover portability/retention here; continuous PITR (≤5-min RPO
for financial data, §1) is WAL archiving via pgBackRest on the primary — its
repo + stanza config is the one remaining ops task to provision on the host.

## 10 — Open items for sign-off

1. Confirm **FSN1 + NBG1** as the two Hetzner locations. Alternative: HEL1 (Helsinki) if latency / GDPR shaping differently.
2. Confirm **7-year retention via Storage Box + `-cold` bucket mirror** is an acceptable substitute for a WORM-locked bucket (Hetzner has no Object Lock equivalent yet).
3. Confirm the **Hetzner Load Balancer** is acceptable, or if a self-hosted HAProxy pair is preferred.
4. Confirm the **Twilio / WhatsApp Business** choice for OTP delivery (unchanged from `00-stack-and-architecture.md`), or name a local Egyptian gateway so we build its adapter first.
