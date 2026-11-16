"""Turn raw generated frames (hero and weapon together on chroma green) into sheets registered to the outfit's original sheets.

Each raw frame is keyed out, then tried at a range of sizes and positions against the original frame; the size and place where the hero overlaps the
original best wins. So the hero lands on the original's pixels whatever framing the generator chose.

Usage:  python3 clean_whole_frames.py <skin>/<style>/<item id>
        reads  docs/review-art/whole/<skin>/<style>/<item>/raw/<key>_<n>.(png|jpg|webp)
        writes docs/review-art/whole/<skin>/<style>/<item>/<key>-sheet.png and preview.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from clean_agy_frames import key_out_green, largest_blob, find_frame  # noqa: E402

WHOLE = HERE.parents[2] / "docs" / "review-art" / "whole"
COLOURS = 30


def register(hero: Image.Image, ref: Image.Image) -> Image.Image:
    """The hero scaled and placed in a cell the size of `ref` where it best matches `ref`."""
    cw, ch = ref.size
    r = np.array(ref).astype(int)
    rmask = r[..., 3] > 0
    rbox = ref.getbbox()
    best, best_score = None, -1e9
    for h in range(max(12, int((rbox[3] - rbox[1]) * 0.7)), min(ch, int((rbox[3] - rbox[1]) * 1.35)) + 1):
        w = max(1, round(hero.width * h / hero.height))
        if w > cw + 20:
            continue
        small = np.array(hero.resize((w, h), Image.BOX))
        small[..., 3] = np.where(small[..., 3] >= 128, 255, 0)
        smask = small[..., 3] > 0
        for y in range(max(0, rbox[3] - h - 3), min(ch - h, rbox[3] - h + 3) + 1):  # feet near the original's baseline
            for x in range(-10, cw - w + 11):
                x0, x1 = max(0, x), min(cw, x + w)
                if x1 - x0 < w * 0.8:
                    continue
                sm = smask[:, x0 - x:x1 - x]
                rm = rmask[y:y + h, x0:x1]
                both = sm & rm
                if not both.any():
                    continue
                diff = np.abs(small[:, x0 - x:x1 - x, :3].astype(int) - r[y:y + h, x0:x1, :3]).sum(-1)
                score = (both & (diff < 90)).sum() - 0.35 * (sm ^ rm).sum()
                if score > best_score:
                    best_score, best = score, (small, x, y)
    small, x, y = best
    cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    img = Image.fromarray(small.astype(np.uint8), "RGBA")
    box = (max(0, -x), 0, min(img.width, cw - x), img.height)
    cell.alpha_composite(img.crop(box), (max(0, x), y))
    return cell


def quantize(cell: Image.Image) -> Image.Image:
    a = np.array(cell)
    rgb = np.array(cell.convert("RGB").quantize(COLOURS, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB"))
    out = np.dstack([rgb, a[..., 3]])
    out[a[..., 3] == 0] = 0
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def build(job: str) -> None:
    skin, style, item = job.split("/")
    d = WHOLE / job
    ref_dir = WHOLE / "_ref" / f"{skin}-{style}"
    rows = []
    for ref_path in sorted(ref_dir.glob("*-sheet.png")):
        key = ref_path.stem.removesuffix("-sheet")
        ref = Image.open(ref_path).convert("RGBA")
        cw = ref.width // 4
        sheet = Image.new("RGBA", ref.size, (0, 0, 0, 0))
        for i in range(4):
            raw = find_frame(d / "raw", f"{key}_{i + 1}")
            if raw is None:
                raise SystemExit(f"{job}: missing raw/{key}_{i + 1}")
            keyed = key_out_green(Image.open(raw))
            a = np.array(keyed)
            a[~largest_blob_fast(a[..., 3] > 0)] = 0
            hero = Image.fromarray(a, "RGBA")
            hero = hero.crop(hero.getbbox())
            sheet.alpha_composite(quantize(register(hero, ref.crop((i * cw, 0, (i + 1) * cw, ref.height)))), (i * cw, 0))
        sheet.save(d / f"{key}-sheet.png")
        rows += [ref, sheet]
    prev = Image.new("RGBA", (max(r.width for r in rows), 72 * len(rows)), (20, 28, 48, 255))
    for n, r in enumerate(rows):
        prev.alpha_composite(r, (0, 72 * n))
    prev.resize((prev.width * 4, prev.height * 4), Image.NEAREST).save(d / "preview.png")
    print(job, "sheets written")


def largest_blob_fast(mask: np.ndarray) -> np.ndarray:
    """Largest connected part, on a reduced copy (raw frames are about 1000 px a side), then grown back."""
    k = max(1, mask.shape[0] // 256)
    small = mask[::k, ::k]
    keep = largest_blob(small)
    big = np.repeat(np.repeat(keep, k, 0), k, 1)[:mask.shape[0], :mask.shape[1]]
    pad = np.zeros_like(mask)
    pad[:big.shape[0], :big.shape[1]] = big
    grown = pad.copy()
    for s in range(1, 2 * k + 1):
        grown |= np.roll(pad, s, 0) | np.roll(pad, -s, 0) | np.roll(pad, s, 1) | np.roll(pad, -s, 1)
    return mask & grown


if __name__ == "__main__":
    for job in sys.argv[1:]:
        build(job)
