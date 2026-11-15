"""Build weapon-less hunter bases and per-weapon held-weapon overlay strips.

Contract (also the brief for any artist-made replacement strips):
  * A base sheet is the hunter sheet with the weapon's blade and guard removed. The glove and grip stay.
  * An overlay strip has exactly the same pixel size and cell layout as its base sheet. It is
    transparent except for the weapon, drawn in place for every pose, and Godot draws it above the
    hunter with the same frame index, offset and scale.
  * Strips are generated from the 128px item icon (grip bottom-left, tip top-right). A strip that
    already exists is left alone, so a hand-made one survives; pass --force to regenerate it.

Usage (system python3 with Pillow and numpy):
    python3 held_weapons.py                                   # rebuild the bases, add any missing strips
    python3 held_weapons.py --force --only campaign-dungeon-loopblade   # regenerate one weapon after its icon changed
After either, run `godot --headless --path prototypes/godot-combat --import`.
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

# Arena skin id -> file prefix of its sheets (`tate-<prefix>-sword-sheet.png`). Tate's own files predate that naming.
OUTFITS = {
    "tate": None, "ivory": "ivory", "warden": "warden-heavy", "harvest": "harvest-scout", "oracle": "arcane",
    "patchwork": "patchwork", "pilgrim": "pilgrim", "wayfarer": "wayfarer", "norse": "norse",
    "lanternkeeper": "lanternkeeper", "wardplate": "wardplate", "debugger": "debugger-v2", "merchant-oracle": "merchant-oracle",
}
# Outfits whose coat is as pale as the blade, so steel detection fails. They borrow Tate's blade geometry
# (their poses match it closely), shifted to wherever their own crossguard is.
LIGHT_OUTFITS = {"ivory", "merchant-oracle"}
# (skin, sheet, frame) -> blade start and end measured by hand, where borrowing Tate's geometry misses.
MANUAL_BLADE = {("ivory", "sword", "idle", 2): ((54.4, 48.4), (67.0, 62.0))}


def style_sheets(skin: str, style: str) -> dict:
    """sheet key -> (file name, cell width) for one combat style. Tate's own files predate the `tate-<prefix>-` naming."""
    prefix = OUTFITS[skin]
    if style == "sword":
        if prefix is None:
            return {"idle": ("tate-idle-sheet.png", 96), "action": ("tate-sword-v2-sheet.png", 96),
                    "follow": ("tate-followthrough-sheet.png", 96), "hurt": ("tate-hurt-sheet.png", 96)}
        return {key: (f"tate-{prefix}-sword{suffix}-sheet.png", 96)
                for key, suffix in (("idle", "-idle"), ("action", ""), ("follow", "-follow"), ("hurt", "-hurt"))}
    if style == "greatsword":
        head = "tate" if prefix is None else f"tate-{prefix}"
        return {"action": (f"{head}-greatsword-sheet.png", 128), "hurt": (f"{head}-greatsword-hurt-sheet.png", 128)}
    raise KeyError(style)


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
# Greatsword-style weapons: the blade is longer, hammers and clubs have a short grip and a heavy head. The
# Gravebound Greatblade is left out because the game already plays it from its own baked variant sheets.
GREATSWORD_WEAPONS = {
    "lv-03": {"grip": 0.20, "reach": 0.65},
    "bj-the-shoe-splitter": {"grip": 0.30, "reach": 0.7},
    "cas-coin-roll-club": {"grip": 0.25, "reach": 0.7},
    "cas-lever-arm-mace": {"grip": 0.25, "reach": 0.7},
    "cas-jackpot-hammer": {"grip": 0.20, "reach": 0.7},
    "dc-deepvein-warhammer": {"grip": 0.20, "reach": 0.7},
    "dc-the-core-breaker": {"grip": 0.22, "reach": 1.0},
    "hunter-sparring-greatsword": {"grip": 0.22, "reach": 1.0},
    "merchant-nightfall-greatsword": {"grip": 0.22, "reach": 1.05},
    "campaign-dungeon-iron-greatsword": {"grip": 0.22, "reach": 1.0},
    "campaign-dungeon-minotaur-edge": {"grip": 0.25, "reach": 0.9},
    "campaign-dungeon-clockwork-greatblade": {"grip": 0.22, "reach": 1.0},
}
GREATSWORD_WEAPONS = {k: {**v, "back": v["grip"]} for k, v in GREATSWORD_WEAPONS.items()}  # keep the whole handle so it meets the fists
STYLE_WEAPONS = {"sword": SWORD_WEAPONS, "greatsword": GREATSWORD_WEAPONS}
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


def guard_centre(cell: np.ndarray, near: np.ndarray, radius: float = 9.0):
    """Centroid of the gold crossguard blob closest to `near`, or None."""
    best = None
    for part in components(gold_mask(cell)):
        c = part.mean(0)
        dist = float(np.hypot(*(c - near)))
        if dist <= radius and (best is None or dist < best[0]):
            best = (dist, c)
    return None if best is None else best[1]


def blade_frames(sheet: Image.Image, cell_w: int, reference=None, reference_sheet=None, manual=None, borrow: bool = False, label: str = ""):
    """Blade start/end per frame. With `borrow`, when colour detection finds nothing, or when what it finds disagrees
    with the reference pose (angle off by more than 20 degrees or a very different length), the geometry is taken
    from the reference frames (Tate's), shifted to this outfit's crossguard."""
    arr = np.array(sheet.convert("RGBA")).astype(int)
    ref_arr = None if reference is None else np.array(reference_sheet.convert("RGBA")).astype(int)
    frames = []
    for i in range(sheet.width // cell_w):
        cell = arr[:, i * cell_w : (i + 1) * cell_w]
        borrowed = None
        if reference is not None:
            ref = reference[i]
            anchor = ref["start"] - ref["dir"] * 3.5
            mine = guard_centre(cell, anchor)
            theirs = guard_centre(ref_arr[:, i * cell_w : (i + 1) * cell_w], anchor)
            shift = (mine - theirs) if mine is not None and theirs is not None else np.zeros(2)
            borrowed = (ref["start"] + shift, ref["end"] + shift)
        a = b = None
        if not borrow:
            try:
                a, b = detect_blade(cell)
            except ValueError:
                if borrowed is None:
                    raise
                print(f"  {label} frame {i}: no steel found, borrowing Tate's blade", file=sys.stderr)
            if a is not None and borrowed is not None:
                d1, d2 = (b - a) / np.hypot(*(b - a)), (borrowed[1] - borrowed[0]) / np.hypot(*(borrowed[1] - borrowed[0]))
                angle = math.degrees(math.acos(float(np.clip(d1 @ d2, -1, 1))))
                ratio = np.hypot(*(b - a)) / np.hypot(*(borrowed[1] - borrowed[0]))
                if angle > 20 or not 0.6 <= ratio <= 1.6:
                    print(f"  {label} frame {i}: detected blade disagrees with Tate's ({angle:.0f} deg, x{ratio:.1f}), borrowing", file=sys.stderr)
                    a = b = None
        if a is None:
            a, b = borrowed
        if i in (manual or {}):
            a, b = (np.array(point, float) for point in manual[i])
        d = (b - a) / np.hypot(*(b - a))
        frames.append({"cell": cell, "start": a, "end": b, "dir": d, "len": float(np.hypot(*(b - a)))})
    return frames


def fill_body(cell: np.ndarray, erased: np.ndarray, d: np.ndarray) -> None:
    """Where the blade crossed the body, repaint the hole from the body on either side of it.

    A pixel is repainted only if there is body on both sides across the blade's axis; pixels in open air stay clear."""
    normal = np.array([-d[1], d[0]])
    h, w = erased.shape
    for y, x in zip(*np.where(erased)):
        found = []
        for sign in (1, -1):
            for k in range(1, 6):
                qx, qy = int(round(x + sign * normal[0] * k)), int(round(y + sign * normal[1] * k))
                if 0 <= qx < w and 0 <= qy < h and not erased[qy, qx] and cell[qy, qx, 3] > 0:
                    found.append((k, cell[qy, qx].copy()))
                    break
        if len(found) == 2:
            cell[y, x] = min(found, key=lambda item: item[0])[1]


def strip_weapon(sheet: Image.Image, cell_w: int, frames, light: bool = False, wide: bool = False) -> Image.Image:
    """Erase the blade and crossguard, keep the glove. `light` outfits cannot tell the blade from the coat by
    colour, so everything inside a thin capsule around the blade is erased and the body is repainted."""
    arr = np.array(sheet.convert("RGBA"))
    for i, f in enumerate(frames):
        cell = arr[:, i * cell_w : (i + 1) * cell_w]
        d = f["dir"]
        reach = (8.0, 4.0) if light else (6.0, 3.2)  # light outfits borrow keypoints, so allow for a few pixels of drift
        if wide:  # the greatsword's blade is thicker and its guard longer
            reach = (10.0, 5.0)
        guard = capsule(cell.shape[:2], f["start"] - d * reach[0], f["start"] + d * 1.5, reach[1]) & gold_mask(cell.astype(int))
        if light:
            blade = capsule(cell.shape[:2], f["start"] - d * 1.0, f["end"] + d * 1.5, 3.6 if wide else 2.6) & (cell[:, :, 3] > 0)
        else:
            blade = capsule(cell.shape[:2], f["start"] - d * 1.0, f["end"] + d * 1.5, 4.0 if wide else 2.6) & steel_mask(cell.astype(int))
        erased = blade | guard
        cell[erased] = (0, 0, 0, 0)
        fill_body(cell, erased, d)
        # The blade's dark outline is left behind; peel it away from the outside in, but only near the blade.
        zone = capsule(cell.shape[:2], f["start"] - d * 1.0, f["end"] + d * (14.0 if light else 3.0), 4.5 if wide else 3.2 if light else 2.8)
        for _ in range(6 if light else 4):
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
        # Thin leftovers (a 1px blade edge, a guard arm) vanish under a morphological opening; thick body parts survive it.
        opaque = cell[:, :, 3] > 0
        for _ in range(2):
            pad = np.pad(opaque, 1)
            eroded = np.ones_like(opaque)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    eroded &= pad[dy : dy + opaque.shape[0], dx : dx + opaque.shape[1]]
            pad = np.pad(eroded, 1)
            opened = np.zeros_like(opaque)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    opened |= pad[dy : dy + opaque.shape[0], dx : dx + opaque.shape[1]]
            thin = opaque & ~opened & capsule(cell.shape[:2], f["start"] - d * 5.0, f["end"] + d * 8.0, 5.0 if wide else 3.0)
            if not thin.any():
                break
            cell[thin] = (0, 0, 0, 0)
            opaque = cell[:, :, 3] > 0
        # Sweep up isolated specks (bits of guard or outline) left floating near where the weapon was.
        near_weapon = capsule(cell.shape[:2], f["start"] - d * 8.0, f["end"] + d * 14.0, 6.0)
        for part in components(cell[:, :, 3] > 0):
            if len(part) <= 5 and near_weapon[part[:, 1], part[:, 0]].any():
                cell[part[:, 1], part[:, 0]] = (0, 0, 0, 0)
    return Image.fromarray(arr, "RGBA")


# Weapons whose menu icon is an older shared file rather than weapon-<id>.png.
ICON_FILES = {"hunter-jack-scythe": "hunter-fashion/scythe.png"}


def load_icon(item_id: str):
    path = ICONS / ICON_FILES.get(item_id, ICON_NAME(item_id))
    if not path.is_file():
        return None
    return Image.open(path).convert("RGBA")


def horizontal_weapon(icon: Image.Image, grip: float, back: float = 0.0):
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
    start_x = int(guard_x - back * length)  # `back` keeps a little of the handle behind the guard so it meets the fist
    keep = xs >= start_x - 2
    ys, xs = ys[keep], xs[keep]
    box = (start_x, int(ys.min()) - 1, int(xs.max()) + 2, int(ys.max()) + 2)
    crop = rotated.crop(box)
    return crop, (guard_x - start_x if back else 0.0), (centre[1] - box[1])


def draw_overlay(base_frames, cell_w: int, height: int, icon: Image.Image, spec, lead: float = 3.5) -> Image.Image:
    weapon, px, py = horizontal_weapon(icon, spec["grip"], spec.get("back", 0.0))
    out = Image.new("RGBA", (cell_w * len(base_frames), height), (0, 0, 0, 0))
    for i, f in enumerate(base_frames):
        reach = spec["reach"] * (f["len"] + lead)
        scale = reach / (weapon.width - px)
        big_w = max(2, round(weapon.width * scale * SS))
        big_h = max(2, round(weapon.height * scale * SS))
        sprite = weapon.resize((big_w, big_h), Image.LANCZOS)
        angle = math.degrees(math.atan2(f["dir"][1], f["dir"][0]))  # image-space (y down)
        pad = max(big_w, big_h) + 8
        canvas = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
        # The weapon's axis sits on y=pad and its guard on x=pad, so rotating about (pad, pad) swings it from the guard.
        canvas.alpha_composite(sprite, (int(pad - px * scale * SS), int(pad - py * scale * SS)))
        turned = canvas.rotate(-angle, resample=Image.BICUBIC, center=(pad, pad))
        anchor = f["start"] - f["dir"] * lead
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


def build(skin: str, style: str, weapons: dict, force: bool = False, reference: dict | None = None):
    """Build one outfit's bases and strips for a style. Returns (report, frames by sheet key)."""
    HELD.mkdir(exist_ok=True)
    report, all_frames = {}, {}
    for key, (name, cell_w) in style_sheets(skin, style).items():
        sheet = Image.open(ART / name).convert("RGBA")
        light = skin in LIGHT_OUTFITS
        manual = {f: points for (s, st, k, f), points in MANUAL_BLADE.items() if s == skin and st == style and k == key}
        if reference is not None:
            tate_name = style_sheets("tate", style)[key][0]
            frames = blade_frames(sheet, cell_w, reference[key], Image.open(ART / tate_name), manual, borrow=light, label=f"{skin}/{style}/{key}")
        else:
            frames = blade_frames(sheet, cell_w, manual=manual)
        all_frames[key] = frames
        report[key] = [
            {"start": [round(v, 1) for v in f["start"]], "end": [round(v, 1) for v in f["end"]], "len": round(f["len"], 1)}
            for f in frames
        ]
        strip_weapon(sheet, cell_w, frames, light, wide=(style == "greatsword")).save(HELD / f"base-{skin}-{style}-{key}-sheet.png")
        for item_id, spec in weapons.items():
            target = HELD / f"{item_id}-{skin}-{style}-{key}.png"
            if target.exists() and not force:
                continue
            icon = load_icon(item_id)
            if icon is None:
                print(f"skip {item_id}: no icon", file=sys.stderr)
                continue
            draw_overlay(frames, cell_w, sheet.height, icon, spec).save(target)
    return report, all_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="sword", choices=sorted(STYLE_WEAPONS))
    parser.add_argument("--only", help="comma separated item ids")
    parser.add_argument("--skins", help="comma separated skin ids (default: every outfit)")
    parser.add_argument("--force", action="store_true", help="overwrite strips that already exist")
    args = parser.parse_args()
    weapons = STYLE_WEAPONS[args.style]
    if args.only:
        weapons = {k: v for k, v in weapons.items() if k in args.only.split(",")}
    skins = args.skins.split(",") if args.skins else list(OUTFITS)
    tate_frames = None
    if "tate" not in skins:
        _, tate_frames = build("tate", args.style, {}, args.force)
    for skin in skins:
        report, frames = build(skin, args.style, weapons, args.force, tate_frames)
        if skin == "tate":
            tate_frames = frames
        (HELD / f"keypoints-{skin}-{args.style}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(skin, "ok")
    print("built", len(weapons), args.style, "weapons for", len(skins), "outfits")


if __name__ == "__main__":
    main()
