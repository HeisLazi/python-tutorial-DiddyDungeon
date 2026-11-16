"""Place a natively drawn pixel-art weapon on a hero frame, rotated without blurring it.

docs/review-art/weapons-native/<style>/<item id>.png is a straight horizontal sprite (butt at the left, tip at the right) and <item id>.json says
which pixel the fist closes on. `place` turns it to any angle with a RotSprite-style pass (8x nearest-neighbour up, rotate, majority vote back down), so the
sprite keeps its hard pixels, its outline and its palette no matter how it is turned.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
NATIVE = REPO / "docs" / "review-art" / "weapons-native"
UP = 8


def load(style: str, item_id: str):
    """(sprite, grip x) or None when the weapon has not been drawn."""
    png = NATIVE / style / f"{item_id}.png"
    meta = NATIVE / style / f"{item_id}.json"
    if not png.exists() or not meta.exists():
        return None
    return Image.open(png).convert("RGBA"), float(json.loads(meta.read_text())["grip"])


def vote_down(big: np.ndarray) -> np.ndarray:
    """Shrink an RGBA array by UP with a majority vote per block, so no new colours appear and edges stay hard."""
    h, w = big.shape[0] // UP, big.shape[1] // UP
    out = np.zeros((h, w, 4), np.uint8)
    key = (big[..., 0].astype(np.uint32) << 24) | (big[..., 1].astype(np.uint32) << 16) | (big[..., 2].astype(np.uint32) << 8) | big[..., 3].astype(np.uint32)
    blocks = key.reshape(h, UP, w, UP).transpose(0, 2, 1, 3).reshape(h, w, UP * UP)
    opaque = (blocks & 0xFF) > 0
    ys, xs = np.nonzero(opaque.sum(-1) >= UP * UP // 2)
    for y, x in zip(ys, xs):
        vals = blocks[y, x][opaque[y, x]]
        uniq, counts = np.unique(vals, return_counts=True)
        k = int(uniq[counts.argmax()])
        out[y, x] = ((k >> 24) & 255, (k >> 16) & 255, (k >> 8) & 255, 255)
    return out


def place(sprite: Image.Image, grip: float, anchor: tuple[float, float], angle_deg: float, size: tuple[int, int], push: float = 0.0) -> Image.Image:
    """The sprite's grip pixel lands on `anchor` (cell pixels) and its tip points along `angle_deg` (image space, y down). `push` slides it along its axis."""
    w, h = size
    big = Image.new("RGBA", (w * UP, h * UP), (0, 0, 0, 0))
    s = sprite.resize((sprite.width * UP, sprite.height * UP), Image.NEAREST)
    ax = (anchor[0] + push * math.cos(math.radians(angle_deg))) * UP
    ay = (anchor[1] + push * math.sin(math.radians(angle_deg))) * UP
    # Paste with the grip column (and the sprite's middle row) on the anchor, then turn the whole canvas about the anchor.
    gx, gy = (grip + 0.5) * UP, sprite.height / 2 * UP
    canvas = Image.new("RGBA", (w * UP * 3, h * UP * 3), (0, 0, 0, 0))
    ox, oy = w * UP, h * UP
    canvas.alpha_composite(s, (round(ox + ax - gx), round(oy + ay - gy)))
    turned = canvas.rotate(-angle_deg, resample=Image.NEAREST, center=(ox + ax, oy + ay))
    big = turned.crop((ox, oy, ox + w * UP, oy + h * UP))
    return Image.fromarray(vote_down(np.array(big)), "RGBA")


def strip(sprite: Image.Image, grip: float, frames: list, cell: tuple[int, int], push: float = 0.0) -> Image.Image:
    """One weapon-only sheet: for every frame `start` is where the fist closes and `dir` the unit vector the tip points along."""
    out = Image.new("RGBA", (cell[0] * len(frames), cell[1]), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        angle = math.degrees(math.atan2(f["dir"][1], f["dir"][0]))
        anchor = (float(f["start"][0]), float(f["start"][1]))
        best = place(sprite, grip, anchor, angle, cell, push)
        # A raised or far-reaching weapon can run off the cell; slide it back along its own axis (the fist moves up the shaft) until it fits.
        for slide in range(1, 25):
            box = best.getbbox()
            if box is None or (box[0] >= 1 and box[1] >= 1 and box[2] <= cell[0] - 1 and box[3] <= cell[1] - 1):
                break
            best = place(sprite, grip, anchor, angle, cell, push - slide)
        out.alpha_composite(best, (i * cell[0], 0))
    return out
