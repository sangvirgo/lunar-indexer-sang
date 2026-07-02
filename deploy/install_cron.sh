#!/bin/bash
set -euo pipefail

: "${APP_DIR:?APP_DIR environment variable is required}"

CRON_SCHEDULE="${CRON_SCHEDULE:-0 1-23/6 * * *}"
CRON_COMMAND="APP_DIR=\"$APP_DIR\" /bin/bash \"$APP_DIR/deploy/run_ingest.sh\""
CRON_LINE="$CRON_SCHEDULE $CRON_COMMAND"

CURRENT_CRONTAB="$(crontab -l 2>/dev/null || true)"

FILTERED_CRONTAB="$(printf '%s\n' "$CURRENT_CRONTAB" | grep -Fv "$CRON_COMMAND" | grep -Ev 'lunar-indexer|rag-ingest' || true)"

{
  printf '%s\n' "$FILTERED_CRONTAB"
  printf '%s\n' "$CRON_LINE"
} | sed '/^$/d' | crontab -

echo "Installed cron line:"
echo "$CRON_LINE"
echo
echo "Verification commands:"
echo "crontab -l"
echo "tail -n 100 /var/log/lunar-indexer/ingest.log"
echo "cat \"$APP_DIR/data/last_run.json\""
