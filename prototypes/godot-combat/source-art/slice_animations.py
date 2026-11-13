#!/usr/bin/env python3
"""Slice the animated study into fixed cells while preserving each full pose.

Use system Python with Pillow. The single scale and common foot baseline keep
characters grounded, and connected masks separate overlapping source bounds.
"""
from collections import deque
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
# A horizontal anchor near the hips for each pose. Relative to 96x72 cells,
# Tate's anchor is at x=35; the left-facing hollow's anchor is at x=55.
SHEETS = {
    # Basics elder variants: candidate art, awaiting in-game review.
    'elder-wraith': ((270, 765, 1280, 1840), 83, 128, -15),
    'elder-wraith-hurt': ((277, 801, 1310, 1843), 83, 128, -37),
    'elder-mimic-action': ((300, 835, 1350, 1890), 55, 96, -70),
    'elder-mimic-hurt': ((300, 840, 1405, 1900), 55, 96, -80),
    'elder-forked-path': ((277, 809, 1320, 1880), 83, 128, -67),
    'elder-forked-path-hurt': ((271, 832, 1351, 1908), 83, 128, -54),
    # Lanternkeeper candidates: review slices only; the skin is not registered.
    'tate-lanternkeeper-sword': ((240, 755, 1830, 1255), 35, 96, -10),
    'tate-lanternkeeper-sword-idle': ((240, 785, 1300, 1870), 35, 96, -10),
    'tate-lanternkeeper-sword-follow': ((240, 755, 1255, 1900), 35, 96, -23),
    'tate-lanternkeeper-sword-hurt': ((240, 740, 1305, 1760), 35, 96, -10),
    'tate-lanternkeeper-staff': ((230, 790, 1250, 1900), 45, 128, -5),
    'tate-lanternkeeper-staff-hurt': ((245, 800, 1300, 1900), 45, 128, -35),
    'tate-lanternkeeper-whip': ((220, 685, 1140, 1945), 45, 128, -40),
    'tate-lanternkeeper-whip-hurt': ((250, 800, 1300, 1900), 45, 128, -45),
    'tate-lanternkeeper-greatsword': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-lanternkeeper-greatsword-hurt': ((260, 780, 1290, 1870), 45, 128, 0),
    'tate-lanternkeeper-handmagic': ((220, 765, 1280, 1930), 45, 128, -35),
    'tate-lanternkeeper-handmagic-hurt': ((250, 780, 1320, 1920), 45, 128, -12),
    'tate-lanternkeeper-scythe': ((272, 805, 1300, 1930), 45, 128, -3),
    'tate-lanternkeeper-scythe-hurt': ((267, 796, 1327, 1930), 45, 128, -1),
    'tate-lanternkeeper-oil': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-lanternkeeper-oil-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-wardplate-sword': ((240, 755, 1830, 1255), 35, 96, -10),
    'tate-wardplate-sword-hurt': ((240, 740, 1305, 1900), 35, 96, -10),
    'tate-wardplate-sword-idle': ((240, 785, 1255, 1775), 35, 96, -10),
    'tate-wardplate-sword-follow': ((240, 755, 1255, 1900), 35, 96, -23),
    'tate-wardplate-staff': ((230, 790, 1250, 1900), 45, 128, -5),
    'tate-wardplate-staff-hurt': ((245, 800, 1300, 1900), 45, 128, -35),
    'tate-wardplate-whip': ((220, 685, 1140, 1945), 45, 128, -40),
    'tate-wardplate-whip-hurt': ((250, 800, 1300, 1900), 45, 128, -45),
    'tate-wardplate-greatsword': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-wardplate-greatsword-hurt': ((260, 780, 1290, 1870), 45, 128, -15),
    'tate-wardplate-handmagic': ((220, 765, 1280, 1930), 45, 128, -35),
    'tate-wardplate-handmagic-hurt': ((250, 780, 1320, 1920), 45, 128, -12),
    'tate-wardplate-scythe': ((272, 805, 1300, 1840), 45, 128, -3),
    'tate-wardplate-scythe-hurt': ((267, 796, 1327, 1930), 45, 128, -1),
    'tate-wardplate-oil': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-wardplate-oil-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-norse-sword-follow': ((240, 755, 1300, 1900), 35, 96, -23),
    'tate-norse-oil-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-norse-oil': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-norse-scythe': ((272, 805, 1300, 1930), 45, 128, -3),
    'tate-norse-scythe-hurt': ((267, 796, 1327, 1930), 45, 128, -1),
    'tate-norse-handmagic-hurt': ((250, 780, 1320, 1920), 45, 128, -12),
    'tate-norse-handmagic': ((220, 765, 1280, 1930), 45, 128, -35),
    'tate-norse-greatsword-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-norse-greatsword': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-norse-whip-hurt': ((250, 800, 1300, 1900), 45, 128, -45),
    'tate-norse-whip': ((220, 685, 1140, 1945), 45, 128, -40),
    'tate-norse-staff-hurt': ((250, 780, 1300, 1900), 45, 128, -35),
    'tate-norse-staff': ((230, 790, 1250, 1900), 45, 128, -5),
    'tate-norse-sword-hurt': ((240, 740, 1305, 1900), 35),
    'tate-norse-sword-idle': ((240, 785, 1300, 1870), 35),
    'tate-norse-sword': ((240, 755, 1300, 1870), 35, 96, -10),
    'tate-ivory-sword': ((240, 755, 1830, 1255), 35, 96, -10),
    'tate-ivory-sword-idle': ((240, 785, 1300, 1870), 35),
    'tate-ivory-sword-hurt': ((240, 740, 1305, 1900), 35),
    'tate-ivory-sword-follow': ((240, 755, 1255, 1900), 35, 96, -23),
    'tate-harvest-scythe': ((272, 805, 1300, 1930), 45, 128, -3),
    'tate-harvest-scythe-hurt': ((267, 796, 1327, 1930), 45, 128, -1),
    'tate-warden-greatsword': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-warden-greatsword-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-oil-pink': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-oil-pink-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-ivory-oil': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-ivory-oil-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-oil': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-oil-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'wraith-v2-hurt': ((277, 801, 1310, 1843), 83, 128, -37),
    'drowner-hurt': ((293, 765, 1305, 1887), 83, 128, -16),
    'ghoul-hurt': ((315, 866, 1370, 1896), 83, 128, -31),
    'loaded-die-hurt': ((273, 815, 1332, 1880), 83, 128, -44),
    'forked-path-hurt': ((271, 832, 1351, 1908), 83, 128, -54),
    'matriarch-hurt': ((293, 809, 1335, 1904), 83, 128, -33),
    'drowned-hoard-hurt': ((284, 840, 1332, 1897), 83, 128, -30),
    'wraith-v2': ((270, 765, 1280, 1840), 83, 128, -15),
    'drowner': ((250, 735, 1200, 1840), 83, 128, -23),
    'ghoul': ((285, 785, 1260, 1840), 83, 128, -17),
    'loaded-die': ((282, 830, 1350, 1900), 83, 128, -53),
    'forked-path': ((277, 809, 1320, 1880), 83, 128, -67),
    'matriarch': ((290, 820, 1330, 1870), 83, 128, -22),
    'drowned-hoard': ((270, 790, 1284, 1870), 83, 128, -10),
    'tate-scythe': ((272, 805, 1300, 1930), 45, 128, -3),
    'tate-scythe-hurt': ((267, 796, 1327, 1930), 45, 128, -1),
    'tate-handmagic': ((220, 765, 1280, 1930), 45, 128, -35),
    'tate-handmagic-hurt': ((250, 780, 1320, 1920), 45, 128, -12),
    'tate-staff': ((230, 790, 1250, 1900), 45, 128, -5),
    'tate-staff-hurt': ((245, 800, 1300, 1900), 45, 128, -35),
    'tate-whip': ((220, 685, 1140, 1945), 45, 128, -40),
    'tate-whip-hurt': ((250, 800, 1300, 1900), 45, 128, -45),
    'tate-greatsword': ((215, 745, 1200, 1860), 45, 128, -20),
    'tate-greatsword-hurt': ((260, 780, 1290, 1870), 45, 128, -35),
    'tate-idle': ((240, 785, 1300, 1870), 35),
    'tate-hurt': ((240, 740, 1305, 1900), 35),
    'tate-followthrough': ((240, 755, 1255, 1900), 35),
    'hollow-action': ((300, 805, 1300, 1900), 55),
    'hollow-hurt': ((300, 845, 1370, 1900), 55),
    'mimic-action': ((300, 835, 1350, 1890), 55),
    'mimic-hurt': ((300, 840, 1405, 1900), 55),
}

# Costume variants use the same frame geometry as their source weapon style.
for costume in ('ivory', 'warden', 'harvest', 'arcane', 'patchwork', 'pilgrim', 'wayfarer', 'debugger', 'debugger-v2', 'merchant-oracle', 'warden-heavy', 'harvest-scout'):
    for weapon in ('staff', 'whip', 'greatsword', 'handmagic', 'scythe'):
        for suffix in ('', '-hurt'):
            variant = f'tate-{costume}-{weapon}{suffix}'
            if (HERE / (variant + '-concept.png')).exists():
                SHEETS.setdefault(variant, SHEETS[f'tate-{weapon}{suffix}'])
    for weapon, config in {
        'sword': ((240, 755, 1830, 1255), 35, 96, -10),
        'sword-idle': SHEETS['tate-idle'],
        'sword-hurt': SHEETS['tate-hurt'],
        'sword-follow': ((240, 755, 1255, 1900), 35, 96, -23),
        'oil': SHEETS['tate-oil-pink'],
        'oil-hurt': SHEETS['tate-oil-pink-hurt'],
    }.items():
        variant = f'tate-{costume}-{weapon}'
        if (HERE / (variant + '-concept.png')).exists():
            SHEETS.setdefault(variant, config)

for prefix in ('tate', 'tate-ivory', 'tate-warden-heavy', 'tate-harvest-scout', 'tate-arcane', 'tate-patchwork', 'tate-pilgrim', 'tate-wayfarer', 'tate-debugger-v2', 'tate-merchant-oracle'):
    for suffix in ('', '-hurt'):
        SHEETS[f'{prefix}-graveblade{suffix}'] = SHEETS[f'tate-greatsword{suffix}']

def shrink(crop, size, name):
    """Scale a 10x crop to its cell. Hand-gridded sources use nearest-neighbour.

    The Wardplate's fine bead and check detail is not pixel-gridded, so nearest-neighbour turns it
    into white salt-and-pepper speckle. Area-average it in premultiplied alpha (no dark fringe),
    then snap alpha so edges stay crisp like the other outfits.
    """
    if '-wardplate-' not in name:
        return crop.resize(size, Image.Resampling.NEAREST)
    small = crop.convert('RGBa').resize(size, Image.Resampling.BOX).convert('RGBA')
    small.putalpha(small.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    return small

def components_of(source):
    w, h = source.size
    alpha = source.getchannel('A').load()
    seen = bytearray(w * h)
    components = []
    for y in range(h):
        for x in range(w):
            index = y * w + x
            if seen[index] or alpha[x, y] <= 128:
                continue
            seen[index] = 1
            queue = deque([(x, y)])
            points = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            ni = ny * w + nx
                            if not seen[ni] and alpha[nx, ny] > 128:
                                seen[ni] = 1
                                queue.append((nx, ny))
            if len(points) > 20_000:
                components.append(points)
    return sorted(components, key=lambda points: min(x for x, _ in points))

for name, config in SHEETS.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    anchors, target_x = config[:2]
    cell_width = config[2] if len(config) > 2 else 96
    configured_top = config[3] if len(config) > 3 else None
    source = Image.open(HERE / (name + '-concept.png')).convert('RGBA')
    w, h = source.size
    components = components_of(source)
    if len(components) != 4:
        raise RuntimeError(f'{name}: expected 4 main poses, found {len(components)}')
    if name in ('tate-lanternkeeper-sword', 'tate-wardplate-sword', 'tate-ivory-sword', 'tate-warden-sword', 'tate-harvest-sword', 'tate-arcane-sword', 'tate-patchwork-sword', 'tate-pilgrim-sword', 'tate-wayfarer-sword', 'tate-debugger-sword', 'tate-debugger-v2-sword', 'tate-merchant-oracle-sword', 'tate-warden-heavy-sword', 'tate-harvest-scout-sword'):
        components = [components[i] for i in (0, 1, 3, 2)]
    sheet = Image.new('RGBA', (cell_width * 4, 72))
    for frame, (points, anchor) in enumerate(zip(components, anchors)):
        mask = Image.new('L', (w, h))
        pix = mask.load()
        for x, y in points:
            pix[x, y] = 255
        clean = Image.new('RGBA', (w, h))
        clean.paste(source, (0, 0), mask)
        left = anchor - target_x * 10
        top = configured_top if configured_top is not None else {'tate-followthrough': -23, 'mimic-action': -70, 'mimic-hurt': -80}.get(name, -10)
        crop = clean.crop((left, top, left + cell_width * 10, top + 720))
        sheet.alpha_composite(shrink(crop, (cell_width, 72), name), (frame * cell_width, 0))
    if name == 'tate-norse-scythe':
        # Replace the clipped source recovery with the separately authored pose.
        recovery = Image.open(HERE / 'tate-norse-scythe-recovery-concept.png').convert('RGBA')
        recovery.putalpha(recovery.getchannel('A').point(lambda a: 255 if a > 128 else 0))
        recovery = recovery.crop((200, 180, 1460, 1000)).resize((76, 49), Image.Resampling.NEAREST)
        sheet.paste((0, 0, 0, 0), (cell_width * 3, 0, cell_width * 4, 72))
        sheet.alpha_composite(recovery, (cell_width * 3 + 18, 20))
    elif name in {f'tate-{costume}-scythe{suffix}' for costume in ('ivory', 'warden', 'harvest', 'arcane', 'patchwork', 'pilgrim', 'wayfarer') for suffix in ('', '-hurt')}:
        # The generated four-pose source clips the fourth scythe tip. Use a
        # separately authored complete recovery, replacing the whole cell.
        suffix = 'hurt-recovery' if name.endswith('-hurt') else 'recovery'
        base = name.removesuffix('-hurt')
        recovery = Image.open(HERE / f'{base}-{suffix}-concept.png').convert('RGBA')
        recovery.putalpha(recovery.getchannel('A').point(lambda a: 255 if a > 128 else 0))
        if suffix == 'recovery':
            recovery = recovery.crop((200, 180, 1460, 1000)).resize((76, 49), Image.Resampling.NEAREST)
            location = (cell_width * 3 + 18, 20)
        else:
            recovery = recovery.crop((250, 160, 1450, 960)).resize((76, 51), Image.Resampling.NEAREST)
            location = (cell_width * 3 + 16, 19)
        sheet.paste((0, 0, 0, 0), (cell_width * 3, 0, cell_width * 4, 72))
        sheet.alpha_composite(recovery, location)
    elif name == 'tate-scythe':
        # Separately authored recovery keeps the scythe tip inside the frame.
        recovery = Image.open(HERE / 'tate-scythe-recovery-concept.png').convert('RGBA')
        recovery = recovery.crop((200, 180, 1460, 1000)).resize((76, 49), Image.Resampling.NEAREST)
        sheet.alpha_composite(recovery, (cell_width * 3 + 18, 20))
    elif name == 'tate-scythe-hurt':
        # A complete separately authored recovery replaces the clipped final pose.
        recovery = Image.open(HERE / 'tate-scythe-hurt-recovery-concept.png').convert('RGBA')
        recovery = recovery.crop((250, 160, 1450, 960)).resize((76, 51), Image.Resampling.NEAREST)
        sheet.alpha_composite(recovery, (cell_width * 3 + 16, 19))
    sheet.save(HERE.parent / 'art' / (name + '-sheet.png'))
