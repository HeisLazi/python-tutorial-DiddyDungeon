#!/bin/sh
# Re-import the Home project and save test screenshots at a few spots.
# Usage: tools/home_art/shots.sh   (writes ide/home-godot/shot_*.png, git-ignored)
set -e
cd "$(dirname "$0")/../../ide/home-godot"
HERE="$(pwd)"
godot --headless --path . --import >/dev/null 2>&1 || true
shot() { # name x,y facing [extra]
  timeout 60 godot --path . --resolution 960x640 -- "--shot=$HERE/shot_$1.png" "--pos=$2" "--face=$3" --tiers $4 >/dev/null 2>&1 || true
}
shot a 160,86 up
shot b 70,86 up
shot c 232,128 left
shot d 160,176 down --unlit
ls shot_*.png
