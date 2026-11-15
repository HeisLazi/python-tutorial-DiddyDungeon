"""Build weapon-less hunter bases and per-weapon held-weapon overlay strips.

Contract (also the brief for any artist-made replacement strips):
  * A base sheet is the hunter sheet with the weapon's blade and guard removed. The glove and grip stay.
  * An overlay strip has exactly the same pixel size and cell layout as its base sheet. It is
    transparent except for the weapon, drawn in place for every pose, and Godot draws it above the
    hunter with the same frame index, offset and scale.
  * Strips are generated from the 128px item icon (grip bottom-left, tip top-right) unless a
    hand-made file with the same name already exists in art/held/ (then it is left alone).

Usage (system python3 with Pillow and numpy):
    python3 held_weapons.py            # rebuild bases and every sword strip
    python3 held_weapons.py --preview  # also write a contact sheet to ../../../tmp path given by --out
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ART = HERE.parent / "art"
HELD = ART / "held"
ICONS = HERE.parents[2] / "ide" / "frontend" / "public" / "campaign-art" / "items"
SS = 4  # supersample factor for rotation so the downscaled edge stays crisp

# skin -> style -> sheet key -> (file, cell width)
SOURCES = {
    "tate": {
        "sword": {
            "idle": ("tate-idle-sheet.png", 96),
            "action": ("tate-sword-v2-sheet.png", 96),
            "follow": ("tate-followthrough-sheet.png", 96),
            "hurt": ("tate-hurt-sheet.png", 96),
        },
    },
}

# Per item: the share of the icon (pommel to tip) that is grip, and the blade reach relative to
# the baked sword. Anything not listed gets SWORD_DEFAULT.
SWORD_DEFAULT = {"grip": 0.28, "reach": 1.0}
SWORD_WEAPONS = {
    "lv-01": {"grip": 0.28, "reach": 1.0},
    "lv-02": {"grip": 0.30, "reach": 1.05},
    "lv-05": {"grip": 0.28, "reach": 1.1},
    "bj-card-edge-dagger": {"grip": 0.32, "reach": 0.6},
    "bj-ace-of-spades-blade": {"grip": 0.30, "reach": 1.15},
    "bj-the-house-cutter": {"grip": 0.28, "reach": 0.95},
    "dc-lantern-lit-shortsword": {"grip": 0.30, "reach": 0.8},
    "merchant-vigil-sabre": {"grip": 0.28, "reach": 1.0},
    "campaign-dungeon-syntax-sabre": {"grip": 0.28, "reach": 1.0},
    "campaign-dungeon-loopblade": {"grip": 0.28, "reach": 1.0},
    "campaign-dungeon-hollow-fang": {"grip": 0.22, "reach": 0.85},
}
# Icons are filed under item id unless the Journal echo shares the Dungeon file.
ICON_NAME = lambda item_id: f"weapon-{item_id}.png"  # noqa: E731


def components(mask: np.ndarray) -> list[np.ndarray]:
    h, w = mask.shape
    seen = np.zeros_like(mask)
    found = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                stack, pts = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    pts.append((cx, cy))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                stack.append((ny, nx))
                found.append(np.array(pts))
    return found


def steel_mask(cell: np.ndarray) -> np.ndarray:
    lum = cell[:, :, :3].mean(2)
    sat = cell[:, :, :3].max(2) - cell[:, :, :3].min(2)
    return (cell[:, :, 3] > 0) & (lum > 150) & (sat < 60)


def gold_mask(cell: np.ndarray) -> np.ndarray:
    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]
    return (cell[:, :, 3] > 0) & (r > 150) & (g > 100) & (b < 120) & (r > b + 60)


def detect_blade(cell: np.ndarray):
    """Return (blade start, blade end) as float x,y points inside the cell."""
    parts = [p for p in components(steel_mask(cell)) if len(p) >= 6]
    best = max(parts, key=lambda p: math.hypot(*(p.max(0) - p.min(0))))
    pts = best.astype(float)
    mean = pts.mean(0)
    direction = np.linalg.svd(pts - mean)[2][0]
    t = (pts - mean) @ direction
    a, b = mean + direction * t.min(), mean + direction * t.max()
    return (a, b) if a[0] <= b[0] else (b, a)


def capsule(shape, a, b, radius):
    ys, xs = np.mgrid[0 : shape[0], 0 : shape[1]]
    p = np.stack([xs, ys], -1).astype(float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(1e-6, ab @ ab), 0, 1)
    nearest = a + t[..., None] * ab
    return np.hypot(*(p - nearest).transpose(2, 0, 1)) <= radius


def blade_frames(sheet: Image.Image, cell_w: int):
    arr = np.array(sheet.convert("RGBA")).astype(int)
    frames = []
    for i in range(sheet.width // cell_w):
        cell = arr[:, i * cell_w : (i + 1) * cell_w]
        a, b = detect_blade(cell)
        d = (b - a) / np.hypot(*(b - a))
        frames.append({"cell": cell, "start": a, "end": b, "dir": d, "len": float(np.hypot(*(b - a)))})
    return frames


def strip_weapon(sheet: Image.Image, cell_w: int, frames) -> Image.Image:
    """Erase the blade and crossguard, keep the glove."""
    arr = np.array(sheet.convert("RGBA"))
    for i, f in enumerate(frames):
        cell = arr[:, i * cell_w : (i + 1) * cell_w]
        d = f["dir"]
        blade = capsule(cell.shape[:2], f["start"] - d * 1.0, f["end"] + d * 1.5, 2.6) & steel_mask(cell.astype(int))
        guard = capsule(cell.shape[:2], f["start"] - d * 6.0, f["start"] + d * 1.5, 3.2) & gold_mask(cell.astype(int))
        cell[blade | guard] = (0, 0, 0, 0)
        # The blade's dark outline is left behind; peel it away from the outside in, but only near the blade.
        zone = capsule(cell.shape[:2], f["start"] - d * 1.0, f["end"] + d * 3.0, 2.8)
        for _ in range(4):
            dark = (cell[:, :, 3] > 0) & (cell[:, :, :3].astype(int).mean(2) < 150) & zone
            clear = cell[:, :, 3] == 0
            near = np.zeros_like(clear)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    near |= np.roll(np.roll(clear, dy, 0), dx, 1)
            peel = dark & near
            if not peel.any():
                break
            cell[peel] = (0, 0, 0, 0)
    return Image.fromarray(arr, "RGBA")


def load_icon(item_id: str):
    path = ICONS / ICON_NAME(item_id)
    if not path.is_file():
        return None
    return Image.open(path).convert("RGBA")


def horizontal_weapon(icon: Image.Image, grip: float):
    """Rotate the diagonal icon so pommel->tip is +x, then keep the part beyond the grip.

    Returns (image, pivot x, pivot y) with the pivot at the guard position, in the image."""
    arr = np.array(icon)
    ys, xs = np.where(arr[:, :, 3] > 40)
    score = xs - ys
    pommel = np.array([xs[score.argmin()], ys[score.argmin()]], float)
    tip = np.array([xs[score.argmax()], ys[score.argmax()]], float)
    angle = math.degrees(math.atan2(-(tip[1] - pommel[1]), tip[0] - pommel[0]))  # PIL rotates counter-clockwise
    length = float(np.hypot(*(tip - pommel)))
    pad = 40
    canvas = Image.new("RGBA", (icon.width + 2 * pad, icon.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(icon, (pad, pad))
    centre = (pommel + pad)
    rotated = canvas.rotate(-angle, resample=Image.BICUBIC, center=tuple(centre))
    r = np.array(rotated)
    ys, xs = np.where(r[:, :, 3] > 40)
    guard_x = centre[0] + length * grip
    keep = xs >= guard_x - 2
    ys, xs = ys[keep], xs[keep]
    box = (int(guard_x), int(ys.min()) - 1, int(xs.max()) + 2, int(ys.max()) + 2)
    crop = rotated.crop(box)
    return crop, 0.0, (centre[1] - box[1])


def draw_overlay(base_frames, cell_w: int, height: int, icon: Image.Image, spec) -> Image.Image:
    weapon, px, py = horizontal_weapon(icon, spec["grip"])
    out = Image.new("RGBA", (cell_w * len(base_frames), height), (0, 0, 0, 0))
    for i, f in enumerate(base_frames):
        reach = spec["reach"] * (f["len"] + 3.5)
        scale = reach / weapon.width
        big_w = max(2, round(weapon.width * scale * SS))
        big_h = max(2, round(weapon.height * scale * SS))
        sprite = weapon.resize((big_w, big_h), Image.LANCZOS)
        angle = math.degrees(math.atan2(f["dir"][1], f["dir"][0]))  # image-space (y down)
        pad = max(big_w, big_h) + 8
        canvas = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
        # The weapon's axis sits on y=pad and its guard on x=pad, so rotating about (pad, pad) swings it from the guard.
        canvas.alpha_composite(sprite, (pad, int(pad - py * scale * SS)))
        turned = canvas.rotate(-angle, resample=Image.BICUBIC, center=(pad, pad))
        anchor = f["start"] - f["dir"] * 3.5
        full = Image.new("RGBA", (cell_w * SS, height * SS), (0, 0, 0, 0))
        _paste_clipped(full, turned, round(anchor[0] * SS) - pad, round(anchor[1] * SS) - pad)
        small = full.resize((cell_w, height), Image.BOX)
        a = np.array(small)
        a[:, :, 3] = np.where(a[:, :, 3] >= 110, 255, 0)
        # Icons are painted for a 128px canvas; lift them so thin blades still read against the dark coat.
        a[:, :, :3] = (255 * (a[:, :, :3] / 255.0) ** 0.7).astype(np.uint8)
        a[a[:, :, 3] == 0] = 0
        out.alpha_composite(Image.fromarray(a, "RGBA"), (i * cell_w, 0))
    return out


def _paste_clipped(dst: Image.Image, src: Image.Image, x: int, y: int) -> None:
    box = (max(0, -x), max(0, -y), min(src.width, dst.width - x), min(src.height, dst.height - y))
    if box[2] > box[0] and box[3] > box[1]:
        dst.alpha_composite(src.crop(box), (max(0, x), max(0, y)))


def build(skin: str, style: str, weapons: dict) -> dict:
    HELD.mkdir(exist_ok=True)
    report = {}
    sheets = SOURCES[skin][style]
    for key, (name, cell_w) in sheets.items():
        sheet = Image.open(ART / name).convert("RGBA")
        frames = blade_frames(sheet, cell_w)
        report[key] = [
            {"start": [round(v, 1) for v in f["start"]], "end": [round(v, 1) for v in f["end"]], "len": round(f["len"], 1)}
            for f in frames
        ]
        strip_weapon(sheet, cell_w, frames).save(HELD / f"base-{skin}-{style}-{key}-sheet.png")
        for item_id, spec in weapons.items():
            target = HELD / f"{item_id}-{skin}-{style}-{key}.png"
            icon = load_icon(item_id)
            if icon is None:
                print(f"skip {item_id}: no icon", file=sys.stderr)
                continue
            draw_overlay(frames, cell_w, sheet.height, icon, spec).save(target)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma separated item ids")
    args = parser.parse_args()
    weapons = SWORD_WEAPONS
    if args.only:
        weapons = {k: v for k, v in weapons.items() if k in args.only.split(",")}
    report = build("tate", "sword", weapons)
    (HELD / "keypoints-tate-sword.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("built", len(weapons), "weapon strips and 4 bases")


if __name__ == "__main__":
    main()
