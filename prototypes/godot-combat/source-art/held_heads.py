"""Head-swap held weapons for the pole styles (scythe, staff).

The scythe and staff are two-handed poles: the shaft passes through the hunter's hands, so redrawing the whole
weapon would need a rebuilt pole. What tells those weapons apart is the head (scythe blade, pick, crystal,
spear point), so only the head is replaced: the baked head is erased and the weapon's own head is drawn on the
end of the baked shaft. Output files follow the same contract as held_weapons.py (base sheets plus strips).

Geometry comes from Tate's sheets: the head is found by colour (steel blade and gold ornament for a scythe, the
blue crystal for a staff) and the shaft direction by casting rays along thin edge pixels. Every other outfit
reuses Tate's head by template matching, because all outfits share the same weapon art.

Usage:  python3 held_heads.py --style scythe          (then `godot --headless --path .. --import`)
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
from PIL import Image

import held_weapons as hw
from held_weapons import ART, HELD, OUTFITS, capsule, components, draw_overlay, gold_mask, load_icon, steel_mask

# style -> sheet key -> (Tate file, outfit file suffix) ; every cell is 128px wide
SHEETS = {
    "scythe": {"action": ("tate-scythe-sheet.png", "scythe-sheet.png"), "hurt": ("tate-scythe-hurt-sheet.png", "scythe-hurt-sheet.png")},
    "staff": {"action": ("tate-staff-sheet.png", "staff-sheet.png"), "hurt": ("tate-staff-hurt-sheet.png", "staff-hurt-sheet.png")},
}
# head_from: share of the icon (pommel to tip) before the head starts; reach: head size relative to the baked head.
SCYTHE_WEAPONS = {
    "dc-miner-s-pickaxe": {"grip": 0.55, "reach": 1.0},
    "hunter-sparring-scythe": {"grip": 0.45, "reach": 1.0},
    "hunter-jack-scythe": {"grip": 0.45, "reach": 1.05},
    "campaign-dungeon-grave-scythe": {"grip": 0.45, "reach": 1.0},
    "campaign-dungeon-undertow-scythe": {"grip": 0.45, "reach": 1.0},
}
STAFF_WEAPONS = {
    "lv-04": {"grip": 0.65, "reach": 1.2},
    "dc-cartographer-s-spear": {"grip": 0.65, "reach": 1.2},
    "hunter-sparring-staff": {"grip": 0.70, "reach": 1.1},
    "merchant-moonlit-staff": {"grip": 0.70, "reach": 1.1},
    "campaign-dungeon-aether-staff": {"grip": 0.70, "reach": 1.1},
    "campaign-dungeon-oracle-staff": {"grip": 0.70, "reach": 1.1},
}
STYLE_WEAPONS = {"scythe": SCYTHE_WEAPONS, "staff": STAFF_WEAPONS}
# Outfits whose head could not be matched cleanly keep their baked weapon (no files means no overlay in the game).
SKIP_OUTFITS = {"scythe": set(), "staff": set()}
# Outfits whose weapon art is recoloured, so the exact-colour match fails: match the head's shape instead.
# (skin, style, sheet, frame) -> Tate frame whose head pose this frame shares (the outfit poses it differently).
POSE_ALIAS = {
    ("debugger", "scythe", "action", 3): 1, ("debugger", "scythe", "hurt", 3): 1,
    ("merchant-oracle", "scythe", "action", 3): 1, ("merchant-oracle", "scythe", "hurt", 3): 1,
}
SHAPE_MATCH = {"scythe": {"debugger", "merchant-oracle"}, "staff": {"warden"}}


def blue_mask(cell: np.ndarray) -> np.ndarray:
    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]
    return (cell[:, :, 3] > 0) & (b > 110) & (b > r + 40)


def edge_pixels(cell: np.ndarray) -> np.ndarray:
    """Opaque pixels with at least two transparent neighbours: thin lines and silhouette edges."""
    opaque = cell[:, :, 3] > 0
    h, w = opaque.shape
    pad = np.pad(~opaque, 1, constant_values=True)
    clear = np.zeros(opaque.shape, int)
    for dy in range(3):
        for dx in range(3):
            if (dy, dx) != (1, 1):
                clear += pad[dy : dy + h, dx : dx + w]
    return opaque & (clear >= 2)


def head_core(cell: np.ndarray, style: str) -> np.ndarray | None:
    """Pixels of the baked head in a Tate frame, or None when it is not visible."""
    if style == "scythe":
        parts = [p for p in components(steel_mask(cell)) if len(p) >= 8]
        if not parts:
            return None
        # The blade is long and thin; the white collar is a compact blob, so rank by extent rather than area.
        blade = max(parts, key=lambda p: math.hypot(*(p.max(0) - p.min(0))))
        centre = blade.mean(0)
        pieces = [blade]
        for part in components(gold_mask(cell)):
            if np.hypot(*(part.mean(0) - centre)) <= 16:
                pieces.append(part)
        pts = np.concatenate(pieces)
    else:
        blue = np.argwhere(blue_mask(cell))[:, ::-1]  # x, y; side views split the crystal into 1-2px pieces
        if len(blue) < 3:
            return None
        centre = np.median(blue, axis=0)
        crystal = blue[np.hypot(*(blue - centre).T) <= 10]
        centre = crystal.mean(0)
        pieces = [crystal]
        for part in components(gold_mask(cell)):
            if np.hypot(*(part.mean(0) - centre)) <= 8:
                pieces.append(part)
        pts = np.concatenate(pieces)
    mask = np.zeros(cell.shape[:2], bool)
    mask[pts[:, 1], pts[:, 0]] = True
    # Take the head's dark outline with it.
    lum = cell[:, :, :3].mean(2)
    near = np.zeros_like(mask)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return mask | (near & (cell[:, :, 3] > 0) & (lum < 90))


def thick_body(cell: np.ndarray) -> np.ndarray:
    """Opaque pixels that survive a 5x5 opening: the torso, head and limbs, not the pole."""
    opaque = cell[:, :, 3] > 0
    h, w = opaque.shape
    pad = np.pad(opaque, 2)
    eroded = np.ones_like(opaque)
    for dy in range(5):
        for dx in range(5):
            eroded &= pad[dy : dy + h, dx : dx + w]
    pad = np.pad(eroded, 2)
    out = np.zeros_like(opaque)
    for dy in range(5):
        for dx in range(5):
            out |= pad[dy : dy + h, dx : dx + w]
    return out


def shaft_direction(cell: np.ndarray, mask: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    """Unit vector from the hands toward the head: the pole runs from the head to the nearest part of the body."""
    opaque = cell[:, :, 3] > 0
    body = thick_body(cell)
    h, w = body.shape
    ys, xs = np.mgrid[0:h, 0:w]
    head_y, head_x = np.where(mask)
    near_head = np.zeros_like(body)
    for hy, hx in zip(head_y, head_x):  # keep the crescent and ornament out of the "body"
        near_head[max(0, hy - 7) : hy + 8, max(0, hx - 7) : hx + 8] = True
    far_from_head = ~near_head
    candidates = np.argwhere(body & far_from_head)
    if len(candidates) == 0:
        return np.array([1.0, -1.0]) / math.sqrt(2)
    dist = np.hypot(candidates[:, 1] - anchor[0], candidates[:, 0] - anchor[1])
    order = np.argsort(dist)
    first = None
    for idx in order[:400]:
        y, x = candidates[idx]
        steps = max(2, int(dist[idx] * 2))
        along = [(anchor[0] + (x - anchor[0]) * t / steps, anchor[1] + (y - anchor[1]) * t / steps) for t in range(1, steps)]
        solid = sum(opaque[int(round(py)), int(round(px))] for px, py in along)
        if first is None:
            first = (x, y)
        if solid >= 0.9 * len(along):
            return (anchor - np.array([x, y], float)) / max(1e-6, float(np.hypot(*(anchor - np.array([x, y], float)))))
    vec = anchor - np.array(first, float)
    return vec / max(1e-6, float(np.hypot(*vec)))


def tate_frame(cell: np.ndarray, style: str):
    mask = head_core(cell, style)
    if mask is None:
        return None
    # The shaft meets the head at its gold ornament (scythe) or just under the crystal (staff).
    gold = mask & gold_mask(cell.astype(int))
    pick = gold if gold.sum() >= 3 else mask & (cell[:, :, :3].mean(2) >= 90)
    ys, xs = np.where(pick)
    anchor = np.array([xs.mean(), ys.mean()])
    fwd = shaft_direction(cell, mask, anchor)
    # Head size: the farthest head pixel from the anchor.
    my, mx = np.where(mask)
    size = float(np.hypot(mx - anchor[0], my - anchor[1]).max())
    return {"mask": mask, "anchor": anchor, "fwd": fwd, "size": size, "cell": cell}


def match_shift(cell: np.ndarray, ref: dict, search: int = 12):
    """Translation (dx, dy) that lays Tate's head over this outfit's, with the share of matching pixels."""
    mask = ref["mask"] & (ref["cell"][:, :, :3].mean(2) >= 90)
    ys, xs = np.where(mask)
    colours = ref["cell"][ys, xs, :3]
    h, w = cell.shape[:2]
    best = (-1, 0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            ty, tx = ys + dy, xs + dx
            ok = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
            if not ok.any():
                continue
            target = cell[ty[ok], tx[ok]]
            hit = ((target[:, 3] > 0) & (np.abs(target[:, :3] - colours[ok]).max(1) <= 48)).sum()
            if hit > best[0]:
                best = (hit, dx, dy)
    return best[1], best[2], best[0] / max(1, len(ys))


def match_shape(cell: np.ndarray, ref: dict, search: int = 14):
    """Colour-blind match for recoloured heads: the head's silhouette should be solid and sit alone in open air.

    Score = share of the head mask that is opaque minus share of a ring just outside it that is opaque."""
    mask = ref["mask"]
    ring = np.zeros_like(mask)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            ring |= np.roll(np.roll(mask, dy, 0), dx, 1)
    ring &= ~mask
    opaque = cell[:, :, 3] > 0
    h, w = opaque.shape
    my, mx = np.where(mask)
    ry, rx = np.where(ring)
    best = (-9.0, 0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            ty, tx = my + dy, mx + dx
            ok = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
            inside = opaque[ty[ok], tx[ok]].sum() / len(my)
            qy, qx = ry + dy, rx + dx
            ok2 = (qy >= 0) & (qy < h) & (qx >= 0) & (qx < w)
            around = opaque[qy[ok2], qx[ok2]].sum() / max(1, len(ry))
            score = inside - around
            if score > best[0]:
                best = (score, dx, dy)
    return best[1], best[2], best[0]


def shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    out = np.zeros_like(mask)
    h, w = mask.shape
    ys, xs = np.where(mask)
    ty, tx = ys + dy, xs + dx
    ok = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
    out[ty[ok], tx[ok]] = True
    return out


def erase_heads(sheet: Image.Image, frames: list[dict]) -> Image.Image:
    arr = np.array(sheet.convert("RGBA"))
    for i, f in enumerate(frames):
        cell = arr[:, i * 128 : (i + 1) * 128]
        if f is None:
            continue
        cell[f["mask"]] = (0, 0, 0, 0)
        # Peel leftover outline and sweep specks near where the head was.
        zone = np.zeros_like(f["mask"])  # only the few pixels around the head: the shaft must survive
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                zone |= np.roll(np.roll(f["mask"], dy, 0), dx, 1)
        for _ in range(3):
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
        for part in components(cell[:, :, 3] > 0):
            if len(part) <= 5 and zone[part[:, 1], part[:, 0]].any():
                cell[part[:, 1], part[:, 0]] = (0, 0, 0, 0)
    return Image.fromarray(arr, "RGBA")


def add_join(f: dict) -> None:
    """Where the new head starts (the back edge of the erased head, on the shaft) and how far it reaches."""
    ys, xs = np.where(f["mask"])
    along = (xs - f["anchor"][0]) * f["fwd"][0] + (ys - f["anchor"][1]) * f["fwd"][1]
    f["join"] = f["anchor"] + f["fwd"] * float(along.min())
    f["reach"] = float(np.hypot(xs - f["join"][0], ys - f["join"][1]).max())


def build(skin: str, style: str, weapons: dict, force: bool, tate: dict | None):
    HELD.mkdir(exist_ok=True)
    report, out_frames = {}, {}
    for key, (tate_file, outfit_suffix) in SHEETS[style].items():
        prefix = OUTFITS[skin]
        name = tate_file if prefix is None else f"tate-{prefix}-{outfit_suffix}"
        sheet = Image.open(ART / name).convert("RGBA")
        arr = np.array(sheet).astype(int)
        frames = []
        for i in range(4):
            cell = arr[:, i * 128 : (i + 1) * 128]
            if tate is None or prefix is None:
                f = tate_frame(cell, style)
            else:
                alias = POSE_ALIAS.get((skin, style, key, i))
                ref = tate[key][alias if alias is not None else i]
                dx, dy, score = match_shift(cell, ref) if ref is not None and alias is None else (0, 0, 0.0)
                if ref is None or score < 0.6:
                    print(f"  {skin}/{style}/{key} frame {i}: head match {score:.2f}", file=sys.stderr)
                    f = None
                    if ref is not None and skin in SHAPE_MATCH.get(style, set()):
                        sx, sy, shape = match_shape(cell, ref, 26 if alias is not None else 14)
                        print(f"    shape match {shape:.2f} at ({sx},{sy})", file=sys.stderr)
                        if shape >= 0.45:
                            f = {"mask": shift_mask(ref["mask"], sx, sy), "anchor": ref["anchor"] + [sx, sy], "fwd": ref["fwd"], "size": ref["size"], "cell": cell}
                    if f is None and skin not in hw.LIGHT_OUTFITS and skin not in SHAPE_MATCH.get(style, set()):
                        f = tate_frame(cell, style)  # colour detection works on dark outfits
                    if f is None and ref is not None:
                        f = {"mask": shift_mask(ref["mask"], dx, dy), "anchor": ref["anchor"] + [dx, dy], "fwd": ref["fwd"], "size": ref["size"], "cell": cell}
                else:
                    f = {"mask": shift_mask(ref["mask"], dx, dy), "anchor": ref["anchor"] + [dx, dy], "fwd": ref["fwd"], "size": ref["size"], "cell": cell}
            frames.append(f)
        for f in frames:
            if f is not None:
                add_join(f)
        out_frames[key] = frames
        report[key] = [None if f is None else {"anchor": [round(float(v), 1) for v in f["anchor"]], "fwd": [round(float(v), 2) for v in f["fwd"]], "size": round(f["size"], 1)} for f in frames]
        erase_heads(sheet, frames).save(HELD / f"base-{skin}-{style}-{key}-sheet.png")
        # draw_overlay() expects blade-style frames; a head is a short "blade" starting at the anchor with no lead-in.
        blade = [{"start": f["join"], "dir": f["fwd"], "len": f["reach"]} if f is not None else {"start": np.array([-99.0, -99.0]), "dir": np.array([1.0, 0.0]), "len": 1.0} for f in frames]
        for item_id, spec in weapons.items():
            target = HELD / f"{item_id}-{skin}-{style}-{key}.png"
            if target.exists() and not force:
                continue
            icon = load_icon(item_id)
            if icon is None:
                print(f"skip {item_id}: no icon", file=sys.stderr)
                continue
            draw_overlay(blade, 128, sheet.height, icon, {**spec, "back": spec.get("back", 0.14)}, lead=0.0).save(target)
    return report, out_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True, choices=sorted(STYLE_WEAPONS))
    parser.add_argument("--only")
    parser.add_argument("--skins")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    weapons = STYLE_WEAPONS[args.style]
    if args.only:
        weapons = {k: v for k, v in weapons.items() if k in args.only.split(",")}
    skins = args.skins.split(",") if args.skins else [k for k in OUTFITS if k not in SKIP_OUTFITS[args.style]]
    tate = None
    if "tate" not in skins:
        _, tate = build("tate", args.style, {}, args.force, None)
    for skin in skins:
        report, frames = build(skin, args.style, weapons, args.force, tate)
        if skin == "tate":
            tate = frames
        (HELD / f"keypoints-{skin}-{args.style}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(skin, "ok")
    print("built", len(weapons), args.style, "weapons for", len(skins), "outfits")


if __name__ == "__main__":
    main()
