#!/usr/bin/env bash
# Manual deploy to the Hetzner box — used until GitHub Actions billing is active
# (.github/workflows/deploy.yml does the same on push to main once billing + the
# DEPLOY_SSH_KEY secret are in place).
#
# Builds the SPA locally, rsyncs the repo to /opt/fitness-tracker, then installs deps,
# runs migrations, and restarts the systemd service. The server keeps its own .env
# (excluded from rsync). For a NEW Alembic migration, validate it on the throwaway
# `fitness_migtest` DB before deploying to prod.
set -euo pipefail

HOST="root@REDACTED"
KEY="${DEPLOY_KEY:-$HOME/.ssh/id_ed25519_github_kipphard}"
DEST="/opt/fitness-tracker"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"

cd "$(dirname "$0")"

echo "==> Building frontend (frontend/dist)"
( cd frontend && npm ci && npm run build )

echo "==> Rsyncing to $HOST:$DEST"
rsync -rlptz --delete -e "$SSH" \
  --exclude '.git/' --exclude '.venv/' --exclude '__pycache__/' \
  --exclude '.pytest_cache/' --exclude '.env' --exclude '*.egg-info/' \
  --exclude '.ruff_cache/' --exclude 'frontend/node_modules/' --exclude '*.db' \
  ./ "$HOST:$DEST/"

echo "==> Installing deps, migrating, restarting service"
$SSH "$HOST" 'bash -seo pipefail' <<'EOS'
set -euo pipefail
cd /opt/fitness-tracker
.venv/bin/pip install --quiet -e .
set -a; . ./.env; set +a
.venv/bin/alembic upgrade head
systemctl restart fitness-tracker
systemctl is-active fitness-tracker
EOS

echo "==> Health check"
# The service needs a moment to come up after restart; retry before declaring failure
# (avoids a spurious 502 the instant nginx beats the app to the punch).
ok=0
for i in 1 2 3 4 5; do
  if curl -fsS https://fitness-tracker.kipphard.com/health; then echo; ok=1; break; fi
  echo "  not ready yet (attempt $i/5)…"; sleep 3
done
[ "$ok" = 1 ] || { echo "!! health check failed after retries"; exit 1; }
echo "==> Deployed."
