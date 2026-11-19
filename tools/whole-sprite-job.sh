#!/bin/zsh
# Runs one hero-and-weapon redraw job with Codex. Usage: tools/whole-sprite-job.sh <skin>/<style>/<item id>
cd "$(dirname "$0")/.."
codex exec -C "$PWD" -s workspace-write "Read docs/review-art/whole/$1/BRIEF.md and do exactly what it says, including the Method section. Repo root is the current directory. Write your outputs into docs/review-art/whole/$1/" > "docs/review-art/whole/$1/codex.log" 2>&1
echo "done $1"
