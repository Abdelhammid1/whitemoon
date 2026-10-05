#!/usr/bin/env bash
# Logical Postgres backup for White Moon (Hetzner-native; no cloud CLI).
# Takes a compressed pg_dump custom-format archive, verifies it, copies it
# off-site (optional rclone remote), and prunes old local copies.
# See docs/05-backup-and-dr.md. Run from a daily systemd timer (deploy/systemd).
#
# Auth: set PGPASSWORD or use ~/.pgpass on the host. Never hard-code it here.
set -euo pipefail

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-wm}"
PGDATABASE="${PGDATABASE:-whitemoon}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/whitemoon}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"   # e.g. hetzner-box:whitemoon/pg (optional)
export PGHOST PGPORT PGUSER

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/${PGDATABASE}-${STAMP}.dump"

echo "[backup] pg_dump ${PGDATABASE} -> ${OUT}"
pg_dump --format=custom --compress=6 --file="$OUT" "$PGDATABASE"

# Integrity: the archive's table of contents must parse.
pg_restore --list "$OUT" >/dev/null
echo "[backup] verified ($(du -h "$OUT" | cut -f1))"

if [[ -n "$RCLONE_REMOTE" ]]; then
  echo "[backup] off-site copy -> ${RCLONE_REMOTE}"
  rclone copy "$OUT" "${RCLONE_REMOTE}/"
fi

# Retention: drop local dumps older than RETENTION_DAYS.
find "$BACKUP_DIR" -maxdepth 1 -name "${PGDATABASE}-*.dump" -mtime "+${RETENTION_DAYS}" -delete
echo "[backup] done (retention ${RETENTION_DAYS}d)"
