#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
vite_bin="$repo_root/ide/frontend/node_modules/.bin/vite"

if [[ ! -x "$vite_bin" ]]; then
  echo "Forge frontend dependencies are missing. Run npm ci in ide/frontend first." >&2
  exit 1
fi

cd "$repo_root/prototypes/campaign-v1"

exec "$vite_bin" \
  --config "$repo_root/ide/frontend/vite.config.js" \
  --host 127.0.0.1 \
  --port "${QUESTLAB_CAMPAIGN_PORT:-5207}" \
  --strictPort
