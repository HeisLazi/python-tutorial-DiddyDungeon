#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
SOURCE="$ROOT/tools/home_art/source/online-raid/choef-chief-idle-pixel.png"
ROOM="$ROOT/tools/home_art/source/online-raid/choef-throne-room-source.png"
GETRICH_IDLE="$ROOT/tools/home_art/source/online-raid/sir-getrich-idle-strip.png"
OUT="$ROOT/prototypes/godot-combat/art"
HOME_OUT="$ROOT/ide/home-godot/art"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM

dimensions="$(magick identify -format '%wx%h' "$SOURCE")"
if [ "$dimensions" != "1774x887" ]; then
	echo "Unexpected Chief sheet dimensions: $dimensions (expected 1774x887). Review the 4x2 crop before exporting."
	exit 1
fi

# Crop one pixel off the right and bottom so Godot divides the sheet into
# eight exact 443x443 frames. Quantize RGB to a small indexed palette and
# threshold alpha separately to keep hard, readable sprite edges.
magick "$SOURCE" -crop 1772x886+0+0 +repage -alpha off -colors 20 -dither none "$TEMP_DIR/chief-rgb.png"
magick "$SOURCE" -crop 1772x886+0+0 +repage -alpha extract -threshold 50% "$TEMP_DIR/chief-alpha.png"
magick "$TEMP_DIR/chief-rgb.png" "$TEMP_DIR/chief-alpha.png" -compose CopyOpacity -composite "$OUT/choef-chief-idle.png"
cp "$ROOM" "$OUT/choef-throne-room.png"

# Sir Getrich has a four-pose idle strip for the walkable online house. Trim
# each source cell, keep its silhouette crisp, and fit it to a common 28x48
# canvas so every frame shares one baseline and the same sprite dimensions.
getrich_idle_dimensions="$(magick identify -format '%wx%h' "$GETRICH_IDLE")"
if [ "$getrich_idle_dimensions" != "2172x724" ]; then
	echo "Unexpected Sir Getrich idle sheet dimensions: $getrich_idle_dimensions (expected 2172x724). Review the 4-frame crop before exporting."
	exit 1
fi
for frame in 0 1 2 3; do
	magick "$GETRICH_IDLE" -crop "543x724+$((frame * 543))+0" +repage -trim +repage \
		-resize '28x48>' -gravity south -background none -extent 28x48 \
		-alpha off -colors 24 -dither none "$TEMP_DIR/getrich-$frame-rgb.png"
	magick "$GETRICH_IDLE" -crop "543x724+$((frame * 543))+0" +repage -trim +repage \
		-resize '28x48>' -gravity south -background none -extent 28x48 \
		-alpha extract -threshold 50% "$TEMP_DIR/getrich-$frame-alpha.png"
	magick "$TEMP_DIR/getrich-$frame-rgb.png" "$TEMP_DIR/getrich-$frame-alpha.png" \
		-compose CopyOpacity -composite "$TEMP_DIR/getrich-$frame.png"
done
magick "$TEMP_DIR/getrich-0.png" "$TEMP_DIR/getrich-1.png" \
	"$TEMP_DIR/getrich-2.png" "$TEMP_DIR/getrich-3.png" +append "$HOME_OUT/sir-getrich-home.png"

echo "Built The Choef Chief's 4x2 idle sheet, throne-room backdrop, and Sir Getrich's four-frame 28x48 house idle strip."
