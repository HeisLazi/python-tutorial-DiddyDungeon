"""Copy finished hero-and-weapon sheets from docs/review-art/whole/<skin>/<style>/<item>/ into art/held/whole-<item>-<skin>-<style>-<key>.png.

DEFAULTS are the weapons the outfit's original sheets already show; they get the original sheet as their whole sheet.
Usage:  python3 install_whole.py        (then `godot --headless --path .. --import`)
"""
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import held_weapons as hw  # noqa: E402
from looks import source_stem  # noqa: E402

WHOLE = HERE.parents[2] / "docs" / "review-art" / "whole"
DEFAULTS = {"scythe": "hunter-sparring-scythe"}
count = 0
for sheet in sorted(WHOLE.glob("*/*/*/*-sheet.png")):
    skin, style, item = sheet.parts[-4:-1]
    if skin == "_ref":
        continue
    shutil.copy(sheet, hw.HELD / f"whole-{item}-{skin}-{style}-{sheet.stem.removesuffix('-sheet')}.png")
    count += 1
for style, item in DEFAULTS.items():
    for skin in {p.parts[-4] for p in WHOLE.glob(f"*/{style}/*/action-sheet.png")}:
        for key in ("action", "hurt"):
            shutil.copy(hw.ART / f"{source_stem(style, key, hw.OUTFITS[skin] or '')}.png", hw.HELD / f"whole-{item}-{skin}-{style}-{key}.png")
            count += 1
print(count, "whole sheets installed")
