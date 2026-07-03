#!/bin/bash
set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

: "${APP_DIR:?APP_DIR environment variable is required}"

LOG_DIR="${LOG_DIR:-/var/log/lunar-indexer}"
LOG_FILE="$LOG_DIR/ingest.log"
ENV_FILE="$APP_DIR/.env"
LAST_RUN_FILE="$APP_DIR/data/last_run.json"

mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR/data"

extract_store_name() {
  sed -n 's/.*"store_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" | head -n 1
}

sync_store_name_to_env() {
  local store_name="$1"
  local current_store_name=""
  local tmp_file

  if [ ! -f "$ENV_FILE" ]; then
    echo "Missing env file: $ENV_FILE"
    return 1
  fi

  current_store_name="$(sed -n 's/^GEMINI_FILE_SEARCH_STORE_NAME=//p' "$ENV_FILE" | head -n 1)"
  if [ "$current_store_name" = "$store_name" ]; then
    echo "Store name unchanged in .env"
    return 0
  fi

  tmp_file="$(mktemp)"
  awk -v store_name="$store_name" '
    BEGIN { updated = 0 }
    /^GEMINI_FILE_SEARCH_STORE_NAME=/ {
      print "GEMINI_FILE_SEARCH_STORE_NAME=" store_name
      updated = 1
      next
    }
    { print }
    END {
      if (!updated) {
        print "GEMINI_FILE_SEARCH_STORE_NAME=" store_name
      }
    }
  ' "$ENV_FILE" > "$tmp_file"
  mv "$tmp_file" "$ENV_FILE"

  echo "Updated GEMINI_FILE_SEARCH_STORE_NAME in $ENV_FILE"
  (
    cd "$APP_DIR"
    docker compose up -d --force-recreate web
  )
  echo "Recreated web service to load updated store name"
}

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
  if [ ! -f "$LAST_RUN_FILE" ]; then
    echo "Missing last run artifact: $LAST_RUN_FILE"
    exit 1
  fi

  STORE_NAME="$(extract_store_name "$LAST_RUN_FILE")"
  if [ -z "$STORE_NAME" ]; then
    echo "Missing store_name in $LAST_RUN_FILE"
    exit 1
  fi

  echo "Resolved store name from last_run.json: $STORE_NAME"
  sync_store_name_to_env "$STORE_NAME"
} >>"$LOG_FILE" 2>&1

{
  echo
  echo "===== $(date -Iseconds) ingest run end ====="
  echo "app dir: $APP_DIR"
  echo "command: docker compose --profile job run --rm ingest"
  echo
} >>"$LOG_FILE"

printf 'Ingestion log: %s\n' "$LOG_FILE"
