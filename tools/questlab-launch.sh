#!/usr/bin/env bash
set -Eeuo pipefail

# Native Linux launcher for Quest Lab. The Python launcher owns port
# selection, state custody and graceful PTY shutdown. This wrapper validates
# the checkout and forwards explicit launch options without enabling reload.

expected_branch='feature/cloud-sync-desktop'
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
workspace="$repo_root"
backend_port=7331
frontend_port=5173
no_browser=0
migrate_local_state=0
confirm_local_state=0
allow_other_branch=0
allow_stale_checkout=0

usage() {
  cat <<'EOF'
Usage: tools/questlab-launch.sh [options]

Options:
  --workspace PATH              Quest workspace (default: repository root)
  --backend-port PORT           Preferred backend port (default: 7331)
  --frontend-port PORT          Preferred frontend port (default: 5173)
  --no-browser                  Do not open a browser automatically
  --migrate-local-state         Review and opt into this device's local cache
  --confirm-local-state         Accept the migration token non-interactively
  --allow-other-branch          Allow a branch other than feature/cloud-sync-desktop
  --allow-stale-checkout        Allow an intentionally offline/stale checkout
  -h, --help                    Show this help
EOF
}

die() {
  printf 'Quest Lab launcher: %s\n' "$1" >&2
  exit 1
}

require_path() {
  local path="$1"
  local description="$2"
  [[ -e "$path" ]] || die "$description is missing: $path (see FRIEND_ONBOARDING.md)"
}

is_port() {
  [[ "$1" =~ ^[0-9]+$ ]] && ((1 <= 10#$1 && 10#$1 <= 65535))
}

while (($#)); do
  case "$1" in
    --workspace)
      (($# >= 2)) || die '--workspace requires a path'
      workspace="$2"
      shift 2
      ;;
    --backend-port)
      (($# >= 2)) || die '--backend-port requires a number'
      backend_port="$2"
      shift 2
      ;;
    --frontend-port)
      (($# >= 2)) || die '--frontend-port requires a number'
      frontend_port="$2"
      shift 2
      ;;
    --no-browser) no_browser=1; shift ;;
    --migrate-local-state) migrate_local_state=1; shift ;;
    --confirm-local-state) confirm_local_state=1; shift ;;
    --allow-other-branch) allow_other_branch=1; shift ;;
    --allow-stale-checkout) allow_stale_checkout=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

is_port "$backend_port" || die "invalid backend port: $backend_port"
is_port "$frontend_port" || die "invalid frontend port: $frontend_port"
((confirm_local_state == 0 || migrate_local_state == 1)) ||
  die '--confirm-local-state requires --migrate-local-state'

command -v git >/dev/null 2>&1 || die 'git is not on PATH'
command -v npm >/dev/null 2>&1 || die 'npm is not on PATH'
require_path "$repo_root/ide/quest.py" 'Quest Lab launcher'
require_path "$repo_root/.venv/bin/python" 'native Python environment'
require_path "$repo_root/ide/frontend/node_modules" 'frontend dependencies'

[[ -d "$workspace" ]] || die "workspace does not exist: $workspace"
workspace="$(cd -- "$workspace" && pwd -P)"

branch="$(git -C "$repo_root" branch --show-current)"
if ((allow_other_branch == 0)) && [[ "$branch" != "$expected_branch" ]]; then
  die "wrong checkout branch '$branch'; switch to '$expected_branch' or pass --allow-other-branch"
fi

upstream_ref=''
if [[ -n "$branch" ]]; then
  upstream_ref="$(git -C "$repo_root" for-each-ref --format='%(upstream:short)' "refs/heads/$branch" || true)"
fi
if [[ -n "$upstream_ref" ]] && ((allow_stale_checkout == 0)); then
  git -C "$repo_root" fetch --quiet origin ||
    die "could not refresh '$upstream_ref'; pass --allow-stale-checkout only for intentional offline use"
  head_sha="$(git -C "$repo_root" rev-parse --verify --quiet HEAD)" || die 'could not resolve checkout HEAD'
  upstream_sha="$(git -C "$repo_root" rev-parse --verify --quiet "refs/remotes/$upstream_ref")" ||
    die "could not resolve upstream '$upstream_ref'"
  [[ "$head_sha" == "$upstream_sha" ]] ||
    die "checkout is not at upstream '$upstream_ref'; run git pull --ff-only or pass --allow-stale-checkout"
fi

if [[ -n "$(git -C "$repo_root" status --short -- progress.json)" ]]; then
  printf 'Warning: canonical progress.json has local player-state changes; it will not be overwritten.\n' >&2
fi

printf '\nPython Quest Lab — Forge v2 (native Linux)\n'
printf '  platform:  %s\n' "$repo_root"
printf '  workspace: %s\n' "$workspace"
printf '  branch:    %s\n' "$branch"
printf '  state:     %s/progress.json (gateway-owned)\n' "$repo_root"
printf '  PTYs:      stable mode (backend reload disabled)\n\n'

launcher=(
  "$repo_root/.venv/bin/python" -m ide.quest
  --workspace "$workspace"
  --backend-port "$backend_port"
  --frontend-port "$frontend_port"
)
((no_browser == 1)) && launcher+=(--no-browser)
((migrate_local_state == 1)) && launcher+=(--use-local-state)
((confirm_local_state == 1)) && launcher+=(--confirm-local-state)

cd -- "$repo_root"
exec env PYTHONPATH=. "${launcher[@]}"
