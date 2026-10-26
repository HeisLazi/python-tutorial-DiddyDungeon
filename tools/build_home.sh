#!/bin/sh
# Build the walkable Home (Godot) into ide/frontend/public/home/ so the app can
# embed it. The output is git-ignored and optional: without it the app shows the
# classic Home. Needs Godot 4.7 and its Web export templates (see README).
#
#   tools/build_home.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/ide/home-godot"
python3 "$ROOT/tools/home_art/make_tiles.py"
# the hunter sheets are committed (made by tools/home_art/from_sheets.py)
cp "$ROOT"/tools/home_art/assets/hunter/hunter_*.png art/
mkdir -p "$ROOT/ide/frontend/public/home"
godot --headless --path . --import >/dev/null 2>&1 || true
godot --headless --path . --export-release "Web" ../frontend/public/home/index.html
ls -lh "$ROOT/ide/frontend/public/home"
