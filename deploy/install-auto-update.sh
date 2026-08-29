#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/apps/odoo-tv-dashboard}"
CRON_LINE="*/5 * * * * APP_DIR=$APP_DIR $APP_DIR/deploy/auto-update.sh >> $APP_DIR/auto-update.log 2>&1"

cd "$APP_DIR"
chmod 700 deploy/auto-update.sh deploy/install-auto-update.sh

current_crontab="$(crontab -l 2>/dev/null || true)"
filtered_crontab="$(printf '%s\n' "$current_crontab" | grep -v 'deploy/auto-update.sh' || true)"
{
  printf '%s\n' "$filtered_crontab"
  printf '%s\n' "$CRON_LINE"
} | sed '/^[[:space:]]*$/d' | crontab -

printf 'Auto-update installed. It checks origin/main every 5 minutes.\n'
