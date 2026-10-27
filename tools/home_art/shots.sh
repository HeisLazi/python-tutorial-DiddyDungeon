#!/bin/sh
# Re-import the Home project and save test screenshots.
# Usage: tools/home_art/shots.sh [room] [tier ...]   (writes ide/home-godot/shot_<room>_t<tier>.png, git-ignored)
#   tools/home_art/shots.sh great_hall 0 3
# Runs desktop Godot with the Compatibility renderer, the same one the web export uses.
# Extra args after the tiers are not supported; edit `shot` for other positions.
set -e
cd "$(dirname "$0")/../../ide/home-godot"
HERE="$(pwd)"
ROOM="${1:-great_hall}"
[ $# -gt 0 ] && shift
TIERS="${*:-0 3}"
godot --headless --path . --import >/dev/null 2>&1 || true
for t in $TIERS; do
  timeout 60 godot --path . --rendering-method gl_compatibility --resolution 960x540 -- "--shot=$HERE/shot_${ROOM}_t$t.png" "--room=$ROOM" "--tier=$t" "--pos=160,150" --face=up >/dev/null 2>&1 || true
done
ls shot_${ROOM}_t*.png
