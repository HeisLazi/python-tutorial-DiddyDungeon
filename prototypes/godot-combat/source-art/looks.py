"""Armour looks made by recolouring an existing outfit.

Only 13 outfits have bespoke combat sheets, but 33 armours need a look of their own. A look here is a parent outfit's
silhouette with a different palette. The recolour works by colour band so the painted shading survives:

  rot   rotate (or set) the hue of one band, e.g. the gold trim, or the whole travel coat
  tint  give colour (`to_hue`, `sat_to`) to the neutral dark or light cloth; `dv`/`add_v` lift it so near-black can show colour

Two things are never recoloured: the hero's skin (found by position, from Tate's sheets: Tate's coat is black, so any
skin-toned pixel there really is skin) and, when a weapon-less base exists, the weapon (a baked sheet keeps the pixels
that differ from its base exactly as they were). Weapons held through held_weapon.gd come from the parent's strips, so
a look needs only its own sheets and bases (HELD.PARENT in held_weapon.gd points a look at its parent's strips).

Usage:  python3 looks.py [--only look-id,...] [--sheet]      (then `godot --headless --path .. --import`)
        --sheet writes shots/looks-preview.png, an idle and a strike frame of every look, for review
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ART = HERE.parent / "art"
HELD = ART / "held"
STYLES = ("sword", "greatsword", "scythe", "staff", "handmagic", "whip", "oil")
BASE_STYLES = ("sword", "greatsword", "scythe", "staff", "handmagic", "whip")  # styles that have weapon-less bases

# look id -> parent outfit file prefix ("" is Tate)
PARENT_PREFIX = {"tate": "", "ivory": "ivory", "warden": "warden-heavy", "harvest": "harvest-scout", "oracle": "arcane", "patchwork": "patchwork",
                 "pilgrim": "pilgrim", "wayfarer": "wayfarer", "norse": "norse", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate",
                 "debugger": "debugger-v2", "merchant-oracle": "merchant-oracle"}
# held-weapon skin name used in art/held/ for each parent
PARENT_HELD = {"tate": "tate", "ivory": "ivory", "warden": "warden", "harvest": "harvest", "oracle": "oracle", "patchwork": "patchwork", "pilgrim": "pilgrim",
               "wayfarer": "wayfarer", "norse": "norse", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate", "debugger": "debugger",
               "merchant-oracle": "merchant-oracle"}


def rgb_to_hsv(a: np.ndarray):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    rc = nz & (mx == r)
    gc = nz & (mx == g) & ~rc
    bc = nz & ~rc & ~gc
    h[rc] = ((g - b)[rc] / d[rc]) % 6
    h[gc] = (b - r)[gc] / d[gc] + 2
    h[bc] = (r - g)[bc] / d[bc] + 4
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h * 60.0, s, mx


def hsv_to_rgb(h, s, v):
    h = (h % 360.0) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,))
    for k, (rr, gg, bb) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        out[m, 0], out[m, 1], out[m, 2] = rr[m], gg[m], bb[m]
    return out


def band(h, s, v, hue=None, sat=(0, 1), val=(0, 1)):
    m = (s >= sat[0]) & (s <= sat[1]) & (v >= val[0]) & (v <= val[1])
    if hue is not None:
        lo, hi = hue
        m &= ((h - lo) % 360.0) <= ((hi - lo) % 360.0)
    return m


def dilate(mask: np.ndarray, n: int = 1) -> np.ndarray:
    out = mask.copy()
    for _ in range(n):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return out


def skin_mask(tate: Image.Image) -> np.ndarray:
    """Where the hero's skin and hair are, taken from Tate's sheet (black coat: a skin-toned pixel there is skin).

    Skin is found by colour. Hair is near-black like the coat, so it is found by position: the face's bounding box in
    the top of each cell, grown upward and sideways to take in the hair."""
    a = np.array(tate.convert("RGBA")).astype(float) / 255.0
    h, s, v = rgb_to_hsv(a[..., :3])
    skin = (a[..., 3] > 0.5) & band(h, s, v, hue=(8, 40), sat=(0.25, 0.85), val=(0.18, 0.85))
    out = dilate(skin, 1)
    cell = a.shape[1] // 4
    for i in range(4):
        opaque = a[:, i * cell:(i + 1) * cell, 3] > 0.5
        rows = np.nonzero(opaque.any(axis=1))[0]
        if not len(rows):
            continue
        top, height = rows.min(), rows.max() - rows.min() + 1
        face = skin[:, i * cell:(i + 1) * cell].copy()
        face[int(top + height * 0.28):, :] = False  # the head only, not the hands
        ys, xs = np.nonzero(face)
        if not len(ys):
            continue
        y0, y1, x0, x1 = max(0, ys.min() - 9), min(a.shape[0], ys.max() + 4), max(0, xs.min() - 5), min(cell, xs.max() + 6)
        out[y0:y1, i * cell + x0:i * cell + x1] = True
    return out


def recolor(img: Image.Image, rules: list, protect: np.ndarray | None, keep: np.ndarray | None = None) -> Image.Image:
    """Apply the band rules. `protect` pixels (skin) and `keep` pixels (weapon) are left exactly as they were."""
    a = np.array(img.convert("RGBA")).astype(float) / 255.0
    h, s, v = rgb_to_hsv(a[..., :3])
    nh, ns, nv = h.copy(), s.copy(), v.copy()
    touched = np.zeros(h.shape, bool)
    opaque = a[..., 3] > 0.5
    for kind, p in rules:
        m = band(h, s, v, p.get("hue"), p.get("sat", (0, 1)), p.get("val", (0, 1))) & opaque & ~touched
        if protect is not None and p.get("skin", True):
            m &= ~protect
        if keep is not None:
            m &= ~keep
        if kind == "rot":
            nh[m] = p["set"] if "set" in p else (h[m] + p.get("dh", 0.0))
            ns[m] = np.clip(s[m] * p.get("ds", 1.0) + p.get("add_s", 0.0), 0, 1)
            nv[m] = np.clip(v[m] * p.get("dv", 1.0) + p.get("add_v", 0.0), 0, 1)
        elif kind == "tint":
            nh[m] = p["to_hue"] if "to_hue" in p else h[m]
            ns[m] = np.maximum(s[m], p.get("sat_to", 0.3))
            nv[m] = np.clip(v[m] * p.get("dv", 1.0) + p.get("add_v", 0.0), 0, 1)
        touched |= m
    rgb = hsv_to_rgb(nh, ns, nv)
    out = a.copy()
    out[..., :3] = np.where(touched[..., None], rgb, a[..., :3])
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def source_stem(style: str, key: str, prefix: str) -> str:
    """The file stem of an outfit's sheet. Tate's own sheets predate the naming scheme the outfits follow."""
    if prefix:
        base = f"tate-{prefix}-{style}"
        return {"action": f"{base}-sheet", "hurt": f"{base}-hurt-sheet", "idle": f"{base}-idle-sheet", "follow": f"{base}-follow-sheet"}[key]
    tate = {("sword", "action"): "tate-sword-v2-sheet", ("sword", "hurt"): "tate-hurt-sheet", ("sword", "idle"): "tate-idle-sheet",
            ("sword", "follow"): "tate-followthrough-sheet", ("oil", "action"): "tate-oil-pink-sheet", ("oil", "hurt"): "tate-oil-pink-hurt-sheet"}
    return tate.get((style, key)) or (f"tate-{style}-sheet" if key == "action" else f"tate-{style}-hurt-sheet")


def output_stem(look_id: str, style: str, key: str) -> str:
    base = f"tate-{look_id}-{style}"
    return {"action": f"{base}-sheet", "hurt": f"{base}-hurt-sheet", "idle": f"{base}-idle-sheet", "follow": f"{base}-follow-sheet"}[key]


def sheet_keys(style: str):
    return ("action", "hurt", "idle", "follow") if style == "sword" else ("action", "hurt")


def build(look_id: str, spec: dict, force: bool = True) -> int:
    parent = spec["parent"]
    prefix = PARENT_PREFIX[parent]
    held_parent = PARENT_HELD[parent]
    rules = spec["rules"]
    written = 0
    for style in STYLES:
        for key in sheet_keys(style):
            src = ART / f"{source_stem(style, key, prefix)}.png"
            if not src.exists():
                print(f"  missing {src.name}", file=sys.stderr)
                continue
            sheet = Image.open(src).convert("RGBA")
            # Mask from Tate's weapon-less base when there is one: a raised sword would otherwise count as the top of the figure.
            tate_path = HELD / f"base-tate-{style}-{key}-sheet.png"
            if not (style in BASE_STYLES and tate_path.exists()):
                tate_path = ART / f"{source_stem(style, key, '')}.png"
            protect = skin_mask(Image.open(tate_path)) if tate_path.exists() and Image.open(tate_path).size == sheet.size else None
            keep = None
            base_path = HELD / f"base-{held_parent}-{style}-{key}-sheet.png"
            has_base = style in BASE_STYLES and base_path.exists()
            if has_base:
                base = np.array(Image.open(base_path).convert("RGBA"))
                cur = np.array(sheet)
                if base.shape == cur.shape:
                    keep = (cur[..., 3] > 0) & ~((base[..., 3] > 0) & (np.abs(cur.astype(int) - base.astype(int)).sum(-1) < 12))  # baked weapon pixels
            recolor(sheet, rules, protect, keep).save(ART / f"{output_stem(look_id, style, key)}.png")
            written += 1
            if has_base:
                base_img = Image.open(base_path)
                tate_base = HELD / f"base-tate-{style}-{key}-sheet.png"
                base_protect = skin_mask(Image.open(tate_base)) if tate_base.exists() and Image.open(tate_base).size == base_img.size else None
                recolor(base_img, rules, base_protect, None).save(HELD / f"base-{look_id}-{style}-{key}-sheet.png")
                written += 1
    written += copy_previews(look_id)
    return written


FRONTEND = HERE.parents[2] / "ide" / "frontend" / "public" / "campaign-art"


def copy_previews(look_id: str) -> int:
    """The Market's weapon preview and the idle pose read the same sheets from the frontend's public folder."""
    (FRONTEND / "weapon-preview").mkdir(exist_ok=True)
    (FRONTEND / "hunter-idle").mkdir(exist_ok=True)
    count = 0
    for style in STYLES:
        src = ART / f"{output_stem(look_id, style, 'action')}.png"
        if src.exists():
            (FRONTEND / "weapon-preview" / f"tate-{look_id}-{style}-sheet.png").write_bytes(src.read_bytes())
            count += 1
    idle = ART / f"{output_stem(look_id, 'sword', 'idle')}.png"
    if idle.exists():
        (FRONTEND / "hunter-idle" / f"tate-{look_id}-sword-idle-sheet.png").write_bytes(idle.read_bytes())
        count += 1
    return count


LOOKS: dict[str, dict] = {}  # filled by looks_data.py


def main() -> None:
    sys.path.insert(0, str(HERE))
    from looks_data import LOOKS as table  # noqa: WPS433

    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--sheet", action="store_true")
    args = parser.parse_args()
    write_registry(table)
    chosen = [k for k in table if not args.only or k in args.only.split(",")]
    for look_id in chosen:
        print(look_id, build(look_id, table[look_id]))
    if args.sheet:
        preview(chosen, table)


def write_registry(table) -> None:
    """looks_registry.gd: each recoloured look and the outfit whose weapon strips it shares. Generated, do not edit."""
    rows = ",\n".join(f'\t"{look}": "{spec["parent"]}"' for look, spec in table.items())
    (HERE.parent / "looks_registry.gd").write_text(
        "extends RefCounted\n## Generated by source-art/looks.py. Each recoloured armour look and the outfit whose held-weapon strips it shares.\n"
        f"const PARENTS := {{\n{rows},\n}}\n"
    )


def preview(chosen, table):
    from PIL import ImageDraw

    tiles = []
    for look_id in chosen:
        row = []
        for stem in (f"tate-{look_id}-sword-idle-sheet", f"tate-{look_id}-sword-sheet"):
            sheet = Image.open(ART / f"{stem}.png").convert("RGBA")
            cw = sheet.width // 4
            for f in ((0,) if "idle" in stem else (2,)):
                cell = sheet.crop((f * cw, 0, (f + 1) * cw, 72))
                bg = Image.new("RGBA", cell.size, (30, 40, 80, 255))
                bg.alpha_composite(cell)
                row.append(bg.resize((cw * 3, 216), Image.NEAREST))
        tile = Image.new("RGB", (sum(t.width for t in row), 216))
        x = 0
        for t in row:
            tile.paste(t.convert("RGB"), (x, 0))
            x += t.width
        ImageDraw.Draw(tile).text((4, 2), f"{look_id}  <-  {table[look_id]['parent']}", fill=(255, 255, 255))
        tiles.append(tile)
    cols = 2
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * cols, h * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    (HERE.parent / "shots").mkdir(exist_ok=True)
    sheet.save(HERE.parent / "shots" / "looks-preview.png")
    print("shots/looks-preview.png", sheet.size)


if __name__ == "__main__":
    main()
