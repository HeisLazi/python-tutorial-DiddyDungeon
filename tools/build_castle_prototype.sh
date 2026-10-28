#!/bin/sh
# Build the isolated castle layout prototype without touching Home's export or saves.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="$ROOT/ide/castle-prototype"
mkdir -p "$PROJECT/art" "$PROJECT/export"
cp "$ROOT/ide/home-godot/art/tiles.png" "$ROOT/ide/home-godot/art/tiles_data.gd" "$ROOT/ide/home-godot/art/pyr_stage_1.png" "$PROJECT/art/"
cp "$ROOT"/tools/home_art/assets/hunter/hunter_*.png "$PROJECT/art/"
cp "$ROOT/ide/home-godot/shaders/home_unarmed.gdshader" "$PROJECT/art/"
godot --headless --path "$PROJECT" --import >/dev/null
godot --headless --path "$PROJECT" --export-release Web export/index.html
