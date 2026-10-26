#!/bin/sh
# Re-import the Home project and save test screenshots at a few spots.
# Usage: tools/home_art/shots.sh   (writes ide/home-godot/shot_*.png, git-ignored)
set -e
cd "$(dirname "$0")/../../ide/home-godot"
HERE="$(pwd)"
godot --headless --path . --import >/dev/null 2>&1 || true
shot() { # name x,y facing look
  timeout 60 godot --path . --resolution 960x640 -- "--shot=$HERE/shot_$1.png" "--pos=$2" "--face=$3" "--look=$4" --tiers >/dev/null 2>&1 || true
}
shot a 224,86 up dracula
shot b 90,86 up dracula
shot c 70,162 left alucard
shot d 224,216 down dracula
shot e 100,214 right belmont
shot f 372,170 down dracula
shot g 352,86 up dracula
shot h 392,206 down dracula
ls shot_*.png
