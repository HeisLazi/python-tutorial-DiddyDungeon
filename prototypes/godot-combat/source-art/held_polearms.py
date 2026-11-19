"""Whole-weapon scythes: a weapon-less hero and a complete scythe, drawn separately and combined afterwards.

The scythe sheets used to keep the hero's baked pole and swap only the head. The pole passes through the hands, so it
could not be erased, and the result was a blade stuck on somebody else's stick that never changed with the weapon.

A scythe now borrows the hero's *sword* poses. Those sheets are already weapon-less (the sword was erased and is drawn
separately by held_weapons.py), so a scythe is drawn on them exactly like a sword: the whole weapon, shaft and head, laid
along each frame's blade axis with the hand on the shaft. The sword's 96px cells are padded to the scythe style's 128px
cells (the hip anchor moves from x=35 to x=45, matching the scythe style's offset), so nothing else in the game changes.

Writes, for every outfit:  art/held/base-<skin>-scythe-<action|hurt>-sheet.png   (the weapon-less hero)
                           art/held/<item id>-<skin>-scythe-<action|hurt>.png    (the whole weapon only)

Usage:  python3 held_polearms.py [--only item,item] [--skins a,b]       (then `godot --headless --path .. --import`)
Needs the sword bases and keypoints first (held_weapons.py --style sword). Every outfit's sword base must really be
weapon-less in every frame: a baked blade left in a sword base shows as a second weapon under the scythe (Norse's
strike frames once did; see MANUAL_BLADE in held_weapons.py).
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
from PIL import Image

import held_weapons as hw
from held_weapons import HELD, OUTFITS, draw_overlay, load_icon

PAD_LEFT = 10  # the sword anchors the hip at x=35 in a 96px cell, the scythe style at x=45 in a 128px cell
SCYTHE_WEAPONS = {
    # grip: where the hand holds the shaft (share of its length from the butt); reach: how long the forward part is
    # relative to the sword blade it replaces.
    "hunter-sparring-scythe": {"grip": 0.40, "reach": 1.55},
    "hunter-jack-scythe": {"grip": 0.40, "reach": 1.5},
    "campaign-dungeon-grave-scythe": {"grip": 0.40, "reach": 1.55},
    "campaign-dungeon-undertow-scythe": {"grip": 0.40, "reach": 1.55},
    "dc-miner-s-pickaxe": {"grip": 0.42, "reach": 1.45},
}
KEYS = ("action", "hurt")


def pad_sheet(sheet: Image.Image) -> Image.Image:
    """Four 96px cells -> four 128px cells."""
    cell = sheet.width // 4
    out = Image.new("RGBA", (128 * 4, sheet.height), (0, 0, 0, 0))
    for i in range(4):
        out.alpha_composite(sheet.crop((i * cell, 0, (i + 1) * cell, sheet.height)), (i * 128 + PAD_LEFT, 0))
    return out


def frames_of(report: list) -> list:
    out = []
    for f in report:
        start, end = np.array(f["start"], float), np.array(f["end"], float)
        length = float(np.hypot(*(end - start)))
        out.append({"start": start, "dir": (end - start) / max(length, 1e-6), "len": f["len"]})
    return out


def build(skin: str, weapons: dict, force: bool) -> int:
    keypoints = HELD / f"keypoints-{skin}-sword.json"
    if not keypoints.exists():
        print(f"  {skin}: no sword keypoints, skipped", file=sys.stderr)
        return 0
    report = json.loads(keypoints.read_text())
    written = 0
    for key in KEYS:
        base_path = HELD / f"base-{skin}-sword-{key}-sheet.png"
        if not base_path.exists():
            continue
        pad_sheet(Image.open(base_path).convert("RGBA")).save(HELD / f"base-{skin}-scythe-{key}-sheet.png")
        written += 1
        frames = frames_of(report[key])
        for item_id, spec in weapons.items():
            target = HELD / f"{item_id}-{skin}-scythe-{key}.png"
            if target.exists() and not force:
                continue
            icon = load_icon(item_id)
            if icon is None:
                print(f"skip {item_id}: no icon", file=sys.stderr)
                continue
            # The whole weapon: `back` keeps the shaft behind the hand, so the hand sits partway along it.
            strip = draw_overlay(frames, 96, 72, icon, {"grip": spec["grip"], "back": spec["grip"], "reach": spec["reach"]}, lead=2.0, fit=True)
            pad_sheet(strip).save(target)
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--skins")
    parser.add_argument("--force", action="store_true", default=True)
    args = parser.parse_args()
    weapons = {k: v for k, v in SCYTHE_WEAPONS.items() if not args.only or k in args.only.split(",")}
    skins = args.skins.split(",") if args.skins else list(OUTFITS)
    for skin in skins:
        print(skin, build(skin, weapons, args.force))


if __name__ == "__main__":
    main()
