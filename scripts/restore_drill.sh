#!/usr/bin/env bash
# Restore drill for White Moon (Hetzner-native; no cloud CLI).
# Restores the latest logical dump into a throwaway database, runs smoke
# checks (schema version + key tables are populated), then drops it. Fails
# loudly on any problem so a broken backup is caught before it's needed.
# See docs/05-backup-and-dr.md §6. Run from a weekly systemd timer.
#
# Auth: PGPASSWORD / ~/.pgpass, and a role that may CREATE/DROP DATABASE.
set -euo pipefail

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-wm}"
SRC_DB="${PGDATABASE:-whitemoon}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/whitemoon}"
export PGHOST PGPORT PGUSER

STAMP="$(date -u +%Y%m%d%H%M%S)"
DRILL_DB="${SRC_DB}_drill_${STAMP}"

LATEST="${DUMP_FILE:-$(ls -1t "${BACKUP_DIR}/${SRC_DB}-"*.dump 2>/dev/null | head -1 || true)}"
[[ -n "$LATEST" ]] || { echo "[drill] FAIL: no dump found in ${BACKUP_DIR}"; exit 1; }
echo "[drill] restoring ${LATEST} -> ${DRILL_DB}"

cleanup() { psql -d postgres -c "DROP DATABASE IF EXISTS \"${DRILL_DB}\";" >/dev/null 2>&1 || true; }
trap cleanup EXIT

psql -d postgres -c "CREATE DATABASE \"${DRILL_DB}\";" >/dev/null
pg_restore --no-owner --no-privileges --dbname="${DRILL_DB}" "$LATEST"

echo "[drill] smoke checks..."
VER="$(psql -tA -d "${DRILL_DB}" -c "SELECT version_num FROM alembic_version;")"
[[ -n "$VER" ]] || { echo "[drill] FAIL: alembic_version missing"; exit 1; }
ACCTS="$(psql -tA -d "${DRILL_DB}" -c "SELECT count(*) FROM accounting.accounts;")"
[[ "${ACCTS:-0}" -gt 0 ]] || { echo "[drill] FAIL: accounting.accounts is empty"; exit 1; }

echo "[drill] PASS — schema=${VER}, accounts=${ACCTS} (scratch db dropped)"
