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
        sheet.alpha_composite(crop.resize((cell_width, 72), Image.Resampling.NEAREST), (frame * cell_width, 0))
    if name == 'tate-scythe':
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
