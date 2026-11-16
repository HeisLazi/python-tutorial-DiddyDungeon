"""Brand-new scythe poses: a hero drawn from scratch (by Codex) with no weapon and two fists on an invisible pole.

The old scythe sheets had the pole baked into the hands. These sheets are new drawings in docs/review-art/scythe-redo/<run>/
(action-sheet.png and hurt-sheet.png, four 128x72 cells each). This script
  1. shrinks each frame so the hero matches the old sheets' size, and aligns his boots to the old baseline and column,
  2. writes art/held/base-<skin>-scythe-<action|hurt>-sheet.png (the weapon-less hero),
  3. draws every scythe along the pole line through the two fists, into art/held/<item id>-<skin>-scythe-<key>.png.

GRIPS are the two fists in each source frame, in source cell pixels: rear = nearest the butt, front = towards the blade.

Usage:  python3 new_scythe_poses.py [--skin tate]   (Tate: docs/review-art/scythe-redo/codex3; others: .../outfits/<skin>)       (then `godot --headless --path .. --import`)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

from held_weapons import ART, HELD, OUTFITS, draw_overlay, load_icon
from looks import source_stem
from held_polearms import SCYTHE_WEAPONS
import native_weapons

REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "docs" / "review-art" / "scythe-redo"
CELL_W, CELL_H = 128, 72
ANCHOR = (60.0, 69.0)  # boots centre / baseline in the source cells
BASELINE = 68  # where the old sheets stand
POLE = 16.0  # nominal pole length forward of the front fist, in cell pixels
REACH = 1.3  # the whole scythe: as long behind the front fist as in front of it, so both fists always sit on the shaft

GRIPS = {
    "codex3": {
        "action": [
            {"rear": (49, 40), "front": (76, 48)},
            {"rear": (56, 35), "front": (53, 25)},
            {"rear": (80, 44), "front": (88, 40)},
            {"rear": (72, 47), "front": (85, 46)},
        ],
        # Hurt: he reels with the scythe held upright against his chest, blade over his head and the butt towards the floor.
        "hurt": [
            {"rear": (69, 48), "front": (71, 40)},
            {"rear": (73, 49), "front": (75, 41)},
            {"rear": (75, 48), "front": (77, 40)},
            {"rear": (75, 52), "front": (77, 44)},
        ],
    },
}


def feet_x(cell: Image.Image) -> float:
    a = np.array(cell)[:, :, 3]
    ys, xs = np.where(a[-12:] > 0)
    return float(xs.mean()) if len(xs) else CELL_W / 2


def shrink(cell: Image.Image, k: float, dx: float) -> Image.Image:
    """Scale a cell about the boots and put the boots on the old baseline, then snap alpha to 0/255."""
    big = cell.resize((round(CELL_W * k), round(CELL_H * k)), Image.LANCZOS)
    out = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    out.alpha_composite(big, (round(ANCHOR[0] + dx - ANCHOR[0] * k), round(BASELINE - ANCHOR[1] * k)))
    a = np.array(out)
    a[:, :, 3] = np.where(a[:, :, 3] >= 128, 255, 0)
    a[a[:, :, 3] == 0] = 0
    return Image.fromarray(a, "RGBA")


def build(skin: str, run: str, scale: float) -> None:
    grips = GRIPS["codex3"]  # every outfit is drawn in the same eight poses with the fists in the same places
    for key, sheet_name in (("action", "action-sheet.png"), ("hurt", "hurt-sheet.png")):
        sheet = Image.open(RUNS / run / sheet_name).convert("RGBA")
        old = Image.open(ART / f"{source_stem('scythe', key, OUTFITS[skin] or '')}.png").convert("RGBA")
        # One shared shift per sheet keeps the stance-to-stance movement the artist drew.
        shifts = []
        for i in range(4):
            new_cell = sheet.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H))
            old_cell = old.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H))
            shifts.append(feet_x(old_cell) - (ANCHOR[0] + (feet_x(new_cell) - ANCHOR[0]) * scale))
        dx = float(np.median(shifts))
        out = Image.new("RGBA", (CELL_W * 4, CELL_H), (0, 0, 0, 0))
        frames = []
        for i in range(4):
            out.alpha_composite(shrink(sheet.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H)), scale, dx), (i * CELL_W, 0))
            g = grips[key][i]
            rear = np.array(g["rear"], float)
            front = np.array(g["front"], float)
            direction = (front - rear) / max(float(np.hypot(*(front - rear))), 1e-6)
            start = np.array([ANCHOR[0] + dx + (front[0] - ANCHOR[0]) * scale, BASELINE + (front[1] - ANCHOR[1]) * scale])
            frames.append({"start": start, "dir": direction, "len": POLE})
        out.save(HELD / f"base-{skin}-scythe-{key}-sheet.png")
        for item_id, spec in SCYTHE_WEAPONS.items():
            drawn = native_weapons.load("scythe", item_id)
            if drawn is not None:
                # A pixel-art sprite drawn for this weapon: turned along the pole line with its grip on the front fist.
                strip = native_weapons.strip(drawn[0], drawn[1], frames, (CELL_W, CELL_H))
            else:
                icon = load_icon(item_id)
                if icon is None:
                    continue
                strip = draw_overlay(frames, CELL_W, CELL_H, icon, {"grip": 0.5, "back": 0.5, "reach": REACH}, lead=2.0, fit=True)
            strip.save(HELD / f"{item_id}-{skin}-scythe-{key}.png")
        print(skin, key, "dx", round(dx, 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skin", help="one outfit, or all of them when left out")
    parser.add_argument("--scale", type=float, default=0.91)
    args = parser.parse_args()
    for skin in [args.skin] if args.skin else list(OUTFITS):
        run = "codex3" if skin == "tate" else f"outfits/{skin}"
        if (RUNS / run / "action-sheet.png").exists() and (RUNS / run / "hurt-sheet.png").exists():
            build(skin, run, args.scale)
        else:
            print(skin, "has no new sheets yet, left as it was")
