#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$HOME/apps/odoo-tv-dashboard}"
BRANCH="${DEPLOY_BRANCH:-main}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/odoo-tv-dashboard-update.lock"
FAILED_SHA_FILE="$APP_DIR/.last-failed-deploy"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

cd "$APP_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "another update is already running"
  exit 0
fi

if [[ ! -f backend/config/.env ]]; then
  log "missing backend/config/.env; refusing to deploy"
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  log "tracked files have local changes; refusing to overwrite them"
  exit 1
fi

git fetch --quiet origin "$BRANCH"
current_sha="$(git rev-parse HEAD)"
target_sha="$(git rev-parse "origin/$BRANCH")"

container_running="$(docker container inspect --format '{{.State.Running}}' odoo-tv-dashboard 2>/dev/null || true)"
if [[ "$current_sha" == "$target_sha" ]] && [[ "$container_running" == "true" ]]; then
  exit 0
fi

if [[ -f "$FAILED_SHA_FILE" ]] && [[ "$(<"$FAILED_SHA_FILE")" == "$target_sha" ]]; then
  log "commit $target_sha already failed; waiting for a newer commit"
  exit 0
fi

previous_image=""
if docker container inspect odoo-tv-dashboard >/dev/null 2>&1; then
  previous_image="$(docker container inspect --format '{{.Image}}' odoo-tv-dashboard)"
fi

log "deploying $target_sha"
if [[ "$current_sha" != "$target_sha" ]]; then
  git merge --ff-only "origin/$BRANCH"
fi
docker compose build --pull app
docker compose up -d --no-deps app

healthy=false
for _ in $(seq 1 20); do
  if curl --fail --silent --show-error --max-time 5 \
      http://127.0.0.1:8000/health >/dev/null; then
    healthy=true
    break
  fi
  sleep 3
done

if [[ "$healthy" == true ]]; then
  rm -f "$FAILED_SHA_FILE"
  log "deployment healthy: $target_sha"
  exit 0
fi

log "health check failed; rolling back to $current_sha"
printf '%s\n' "$target_sha" >"$FAILED_SHA_FILE"
git reset --hard "$current_sha"

if [[ -n "$previous_image" ]]; then
  docker rm -f odoo-tv-dashboard >/dev/null 2>&1 || true
  docker run -d \
    --name odoo-tv-dashboard \
    --restart unless-stopped \
    --env-file backend/config/.env \
    -p 127.0.0.1:8000:8000 \
    "$previous_image" >/dev/null
  log "previous image restored"
else
  log "no previous image was available to restore"
fi

exit 1
