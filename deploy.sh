#!/usr/bin/env bash
# Manual deploy. Builds the SPA locally, rsyncs the repo to the server, then installs deps,
# runs migrations, and restarts the systemd service. The server keeps its own .env (excluded
# from rsync). For a NEW Alembic migration, validate it on a throwaway DB before deploying.
#
# Host/key/URL come from a gitignored ./deploy.env (copy deploy.env.example and fill it in) so
# no infrastructure details are committed.
set -euo pipefail
cd "$(dirname "$0")"

[ -f ./deploy.env ] && . ./deploy.env

HOST="${DEPLOY_HOST:?set DEPLOY_HOST (e.g. root@1.2.3.4) in deploy.env}"
KEY="${DEPLOY_KEY:-$HOME/.ssh/id_ed25519}"
DEST="${DEPLOY_DEST:-/opt/fitness-tracker}"
HEALTH_URL="${DEPLOY_HEALTH_URL:-}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"

echo "==> Building frontend (frontend/dist)"
( cd frontend && npm ci && npm run build )

echo "==> Rsyncing to $HOST:$DEST"
rsync -rlptz --delete -e "$SSH" \
  --exclude '.git/' --exclude '.venv/' --exclude '__pycache__/' \
  --exclude '.pytest_cache/' --exclude '.env' --exclude 'deploy.env' --exclude '*.egg-info/' \
  --exclude '.ruff_cache/' --exclude 'frontend/node_modules/' --exclude '*.db' \
  ./ "$HOST:$DEST/"

echo "==> Installing deps, migrating, restarting service"
$SSH "$HOST" 'bash -seo pipefail' <<EOS
set -euo pipefail
cd "$DEST"
.venv/bin/pip install --quiet -e .
set -a; . ./.env; set +a
.venv/bin/alembic upgrade head
systemctl restart fitness-tracker
systemctl is-active fitness-tracker
EOS

if [ -n "$HEALTH_URL" ]; then
  echo "==> Health check"
  ok=0
  for i in 1 2 3 4 5; do
    if curl -fsS "$HEALTH_URL"; then echo; ok=1; break; fi
    echo "  not ready yet (attempt $i/5)…"; sleep 3
  done
  [ "$ok" = 1 ] || { echo "!! health check failed after retries"; exit 1; }
fi
echo "==> Deployed."
