#!/usr/bin/env bash
set -Eeuo pipefail

# Start Quest Lab on a throwaway "everything unlocked" save, for testing.
# It never touches the real progress.json: the test save lives under
# ${QUESTLAB_TEST_DIR:-$HOME/.local/share/questlab-test}.
#
# Usage: tools/questlab-test.sh [--reset] [--no-browser] [--backend-port PORT]
#   --reset   rebuild the test save from scratch (otherwise your test progress is kept)
# Every Dungeon run also starts with all gear in the pack and a big purse (QUESTLAB_TEST_UNLOCKS=1).

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
test_dir="${QUESTLAB_TEST_DIR:-$HOME/.local/share/questlab-test}"
python_bin="$repo_root/.venv/bin/python"
[[ -x "$python_bin" ]] || python_bin="$(command -v python3)"

reset=()
pass=()
while (($#)); do
  case "$1" in
    --reset) reset=(--force); shift ;;
    *) pass+=("$1"); shift ;;
  esac
done

mkdir -p "$test_dir/workspace"
"$python_bin" "$repo_root/tools/make_test_save.py" "$test_dir/progress.json" "${reset[@]}"

export QUESTLAB_TEST_UNLOCKS=1
export QUESTLAB_STATE_PATH="$test_dir/progress.json"
export QUESTLAB_WORKSPACE="$test_dir/workspace"
echo "Test save: $QUESTLAB_STATE_PATH (real progress.json is not used)"
cd "$repo_root"
exec "$python_bin" ide/quest.py --app --workspace "$test_dir/workspace" "${pass[@]}"
