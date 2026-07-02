#!/bin/bash
set -euo pipefail

: "${APP_DIR:?APP_DIR environment variable is required}"

LOG_DIR="${LOG_DIR:-/var/log/lunar-indexer}"
LOG_FILE="$LOG_DIR/ingest.log"
COMMAND='docker compose --profile job run --rm ingest'

mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR/data"

{
  echo "===== ingest run start ====="
  date -Iseconds
  echo "app dir: $APP_DIR"
  echo "command: $COMMAND"
  echo
} >>"$LOG_FILE"

(
  cd "$APP_DIR"
  docker compose --profile job run --rm ingest
) >>"$LOG_FILE" 2>&1

{
  echo "===== ingest run end ====="
  date -Iseconds
  echo "app dir: $APP_DIR"
  echo "command: $COMMAND"
  echo
} >>"$LOG_FILE"

echo "Ingestion log written to: $LOG_FILE"
