"""Turn raw generated frames (agy: a hero on flat chroma green) into 128x72-cell scythe sheets.

Each frame is keyed out of the green, cropped, scaled so its box matches the approved Tate frame in the same pose
(docs/review-art/scythe-redo/codex3), reduced to a hard-edged palette, and placed so the feet stand on the same row and the body
sits in the same place. That makes every outfit a drop-in for new_scythe_poses.py.

Usage:  python3 clean_agy_frames.py <skin>        reads  docs/review-art/scythe-redo/outfits-agy/<skin>/{action,hurt}_{1..4}.(png|jpg)
                                                  writes docs/review-art/scythe-redo/outfits/<skin>/{action,hurt}-sheet.png   (add --out to change)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "docs" / "review-art" / "scythe-redo"
CELL_W, CELL_H = 128, 72
COLOURS = 28


def key_out_green(img: Image.Image) -> Image.Image:
    a = np.array(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > 120) & (g - r > 60) & (g - b > 60)
    out = np.dstack([a, np.where(green, 0, 255)]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    # Drop green fringe left on edge pixels by the generator's anti-aliasing.
    arr = np.array(im).astype(int)
    fringe = (arr[..., 3] > 0) & (arr[..., 1] - np.maximum(arr[..., 0], arr[..., 2]) > 25)
    arr[fringe, 3] = 0
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def largest_blob(alpha: np.ndarray) -> np.ndarray:
    """Keep only the biggest connected part, so stray specks of background do not stretch the crop."""
    from collections import deque
    h, w = alpha.shape
    seen = np.zeros_like(alpha, bool)
    best: list = []
    for y in range(h):
        for x in range(w):
            if alpha[y, x] and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                pts = []
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and alpha[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((ny, nx))
                if len(pts) > len(best):
                    best = pts
    keep = np.zeros_like(alpha, bool)
    for y, x in best:
        keep[y, x] = True
    return keep


def find_frame(folder: Path, name: str) -> Path | None:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = folder / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def clean(raw: Image.Image, target_box: tuple[int, int, int, int]) -> Image.Image:
    # Work from a reduced copy: the generator draws big "pixels", so a first shrink cheaply merges them before keying.
    keyed = key_out_green(raw)
    a = np.array(keyed)
    keep = largest_blob(a[..., 3] > 0)
    a[~keep] = 0
    keyed = Image.fromarray(a, "RGBA")
    box = keyed.getbbox()
    hero = keyed.crop(box)
    tx0, ty0, tx1, ty1 = target_box
    scale = (ty1 - ty0) / hero.height  # same height as Tate in the same pose
    size = (max(1, round(hero.width * scale)), (ty1 - ty0))
    small = hero.resize(size, Image.LANCZOS)
    arr = np.array(small)
    arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
    solid = Image.fromarray(arr, "RGBA")
    rgb = solid.convert("RGB").quantize(COLOURS, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    out = np.array(rgb)
    mask = arr[..., 3] > 0
    final = np.dstack([out, np.where(mask, 255, 0)]).astype(np.uint8)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    # Centre on the Tate frame's box (the same pose), feet on its bottom row.
    cx = (tx0 + tx1) // 2
    cell.alpha_composite(Image.fromarray(final, "RGBA"), (max(0, min(CELL_W - size[0], cx - size[0] // 2)), ty0))
    return cell


def build(skin: str, out_dir: Path) -> None:
    raw_dir = RUNS / "outfits-agy" / skin
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in ("action", "hurt"):
        ref = Image.open(RUNS / "codex3" / f"{key}-sheet.png").convert("RGBA")
        sheet = Image.new("RGBA", (CELL_W * 4, CELL_H), (0, 0, 0, 0))
        for i in range(4):
            path = find_frame(raw_dir, f"{key}_{i + 1}")
            if path is None:
                raise SystemExit(f"{skin}: missing {key}_{i + 1}")
            box = ref.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H)).getbbox()
            sheet.alpha_composite(clean(Image.open(path), box), (i * CELL_W, 0))
        sheet.save(out_dir / f"{key}-sheet.png")
    print(skin, "->", out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("skin")
    parser.add_argument("--out")
    args = parser.parse_args()
    build(args.skin, Path(args.out) if args.out else RUNS / "outfits" / args.skin)
