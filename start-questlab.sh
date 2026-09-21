#!/usr/bin/env bash
set -euo pipefail

# WSL/native-Linux convenience entry point. The tools launcher remains the
# source of truth for branch, dependency, state-custody and PTY checks.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$script_dir/tools/questlab-launch.sh" "$@"
