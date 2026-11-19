"""Isolate and centre inventory icons from the generated 6×4 source atlases."""
from collections import deque
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'prototypes/godot-combat/source-art'
DEST = ROOT / 'ide/frontend/public/campaign-art/items/merchant'
SHEETS = {
    'merchant-inventory-atlas.png': 'leather-coat blue-coat breastplate brigandine hunter-coat chainmail pickaxe shortsword hammer spear ornate-sword dagger compass key green-tonic red-tonic bread soup shield flame-charm bell gemstone scroll bandage'.split(),
    'merchant-casino-atlas.png': 'dealer-waistcoat velvet-jacket pit-coat doorman-coat sequin-vest auditor-vest card-dagger croupier-rake ace-blade coin-club lever-mace chakram poker-chip playing-card abacus silver-coin dice ledger peanuts coffee sandwich steak fortune-cookie shrimp'.split(),
}

def isolate(tile):
    alpha = tile.getchannel('A').point(lambda v: 255 if v >= 32 else 0)
    expanded = alpha.filter(ImageFilter.MaxFilter(11))
    w, h = tile.size
    mask = expanded.load()
    visited = bytearray(w * h)
    components = []
    for y in range(h):
        for x in range(w):
            index = y * w + x
            if not mask[x, y] or visited[index]:
                continue
            queue = deque([(x, y)])
            visited[index] = 1
            component = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[nx, ny] and not visited[ny*w+nx]:
                        visited[ny*w+nx] = 1
                        queue.append((nx, ny))
            components.append(component)
    if not components:
        raise ValueError('Empty atlas cell')
    # Real item occupies most of its cell; fragments from adjacent cells do not.
    component = max(components, key=len)
    keep = Image.new('L', (w, h))
    pixels = keep.load()
    for x, y in component:
        pixels[x, y] = 255
    original_alpha = tile.getchannel('A')
    from PIL import ImageChops
    tile.putalpha(ImageChops.multiply(original_alpha, keep))
    bounds = tile.getchannel('A').getbbox()
    icon = tile.crop(bounds)
    icon.thumbnail((80, 80), Image.Resampling.NEAREST)
    result = Image.new('RGBA', (96, 96))
    result.alpha_composite(icon, ((96-icon.width)//2, (96-icon.height)//2))
    return result

DEST.mkdir(parents=True, exist_ok=True)
for filename, names in SHEETS.items():
    sheet = Image.open(SOURCE / filename).convert('RGBA')
    if sheet.size != (1536, 1024):
        raise ValueError(f'Unexpected dimensions for {filename}: {sheet.size}')
    for i, name in enumerate(names):
        x, y = (i % 6) * 256, (i // 6) * 256
        isolate(sheet.crop((x, y, x+256, y+256))).save(DEST / f'{name}.png', optimize=True)
