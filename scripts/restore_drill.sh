#!/usr/bin/env bash
# Weekly restore drill — restores last night's RDS snapshot into a sandbox
# instance and runs a smoke suite. See docs/05-backup-and-dr.md §6.
#
# Pre-reqs: AWS CLI v2, jq, psql.
# Env: AWS_PROFILE, SANDBOX_SG, SANDBOX_SUBNET_GROUP.
set -euo pipefail

STAMP="$(date -u +%Y%m%d-%H%M)"
SRC_INSTANCE="${SRC_INSTANCE:-wm-prod-db}"
SANDBOX_INSTANCE="wm-drill-${STAMP}"

echo "[drill] Looking up latest snapshot of ${SRC_INSTANCE}..."
SNAP="$(aws rds describe-db-snapshots \
    --db-instance-identifier "${SRC_INSTANCE}" \
    --snapshot-type automated \
    --query 'reverse(sort_by(DBSnapshots,&SnapshotCreateTime))[0].DBSnapshotIdentifier' \
    --output text)"
echo "[drill] Snapshot: ${SNAP}"

echo "[drill] Restoring to ${SANDBOX_INSTANCE}..."
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier "${SANDBOX_INSTANCE}" \
    --db-snapshot-identifier "${SNAP}" \
    --db-instance-class db.t4g.small \
    --no-publicly-accessible \
    --db-subnet-group-name "${SANDBOX_SUBNET_GROUP}" \
    --vpc-security-group-ids "${SANDBOX_SG}" \
    --tags Key=purpose,Value=drill Key=cleanup,Value=true

aws rds wait db-instance-available --db-instance-identifier "${SANDBOX_INSTANCE}"

echo "[drill] Running smoke suite..."
# TODO (Phase 2): point SMOKE_DATABASE_URL at the sandbox and run `pytest -m smoke`
echo "[drill] Smoke placeholder — real tests ship with Phase 2."

echo "[drill] Deleting sandbox..."
aws rds delete-db-instance \
    --db-instance-identifier "${SANDBOX_INSTANCE}" \
    --skip-final-snapshot \
    --delete-automated-backups

echo "[drill] Done."
