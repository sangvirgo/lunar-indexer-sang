#!/bin/bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

: "${APP_DIR:?APP_DIR environment variable is required}"

LOG_DIR="${LOG_DIR:-/var/log/lunar-indexer}"
LOG_FILE="$LOG_DIR/ingest.log"

mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR/data"

{
  echo "===== $(date -Iseconds) ingest run start ====="
  echo "app dir: $APP_DIR"
  echo "command: docker compose --profile job run --rm ingest"
  echo
} >>"$LOG_FILE"

(
  cd "$APP_DIR"
  docker compose --profile job run --rm ingest
) >>"$LOG_FILE" 2>&1

{
  echo
  echo "===== $(date -Iseconds) ingest run end ====="
  echo "app dir: $APP_DIR"
  echo "command: docker compose --profile job run --rm ingest"
  echo
} >>"$LOG_FILE"

printf 'Ingestion log: %s\n' "$LOG_FILE"
