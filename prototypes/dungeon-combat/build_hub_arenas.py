#!/usr/bin/env python3
"""Compose prototype side-view arenas from the same atlas used by Home.

Run with system Python and Pillow from anywhere. Outputs are 320x180 pixels.
"""
from pathlib import Path
import math
import random
import re
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = ROOT / 'ide/home-godot/art'
ATLAS = Image.open(ART / 'tiles.png').convert('RGBA')
REGIONS = {name: tuple(map(int, (x, y, w, h))) for name, x, y, w, h in re.findall(
    r'"([^\"]+)": Rect2\((\d+), (\d+), (\d+), (\d+)\)', (ART / 'tiles_data.gd').read_text())}
W, H = 320, 180

def piece(name):
    x, y, w, h = REGIONS[name]
    return ATLAS.crop((x, y, x + w, y + h))

def paste(canvas, name, x, y, scale=1):
    im = piece(name)
    if scale != 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.NEAREST)
    canvas.alpha_composite(im, (x, y))

def glow(canvas, x, y, color, radius, strength):
    # Draw at native pixel resolution, as the Home Godot scene does.
    light = Image.new('RGBA', (W, H))
    pixels = light.load()
    for py in range(max(0, y-radius), min(H, y+radius)):
        for px in range(max(0, x-radius), min(W, x+radius)):
            t = max(0, 1 - math.hypot(px-x, py-y) / radius)
            pixels[px, py] = (*color, round(strength * t * t))
    canvas.alpha_composite(light)

def build(kind):
    rng = random.Random(47)
    im = Image.new('RGBA', (W, H), (14, 13, 25, 255))
    # Wall and floor come directly from the hub atlas, with a low dividing ledge.
    for y in range(0, 128, 16):
        for x in range(0, W, 16):
            paste(im, 'wall_s_%d' % ((x//16 + y//16) % 2), x, y)
    for y in range(128, H, 16):
        for x in range(0, W, 16):
            paste(im, 'floor_flag_%d' % rng.randrange(3), x, y)
    for x in range(0, W, 16):
        paste(im, 'plinth_s', x, 112)
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 127, W, 130), fill=(13, 12, 23, 175))
    if kind == 'crypt':
        for x in (6, 298): paste(im, 'pillar_s', x, 50, 1.35)
        for x in (80, 204): paste(im, 'window_plain', x, 32, 1.25)
        paste(im, 'banner_torn', 153, 42, 1.25)
        for x in (43, 266): paste(im, 'torch_0', x, 76, 1.2)
        glow(im, 50, 84, (255, 151, 74), 48, 65)
        glow(im, 273, 84, (255, 151, 74), 48, 65)
        glow(im, 101, 55, (100, 132, 204), 48, 24)
        glow(im, 222, 55, (100, 132, 204), 48, 24)
    elif kind == 'caves':
        # Den pieces tie the deeper, rougher space back to Pyr's room.
        for x in (-30, 250): paste(im, 'cave_arch', x, 23, 1.5)
        for x, y in ((0, 100), (277, 96), (144, 115)): paste(im, 'boulder', x, y, 1.1)
        paste(im, 'window_den', 143, 40, 1.15)
        for x in (48, 254): paste(im, 'lantern_blue', x, 76, 1.15)
        glow(im, 53, 88, (89, 146, 225), 49, 55)
        glow(im, 259, 88, (89, 146, 225), 49, 55)
        glow(im, 156, 61, (100, 150, 210), 38, 32)
    else:
        for x in (7, 278): paste(im, 'bookshelf_sparse', x, 55, 1.15)
        for x in (54, 231): paste(im, 'bookshelf_full', x, 55, 1.15)
        paste(im, 'window_moon', 145, 38, 1.2)
        for x in (116, 192): paste(im, 'torch_0', x, 77, 1.1)
        glow(im, 122, 84, (255, 151, 74), 45, 62)
        glow(im, 198, 84, (255, 151, 74), 45, 62)
        glow(im, 160, 58, (113, 130, 207), 45, 35)
    im.convert('RGB').save(HERE / 'assets' / ('hub-' + kind + '.png'), optimize=True)

for location in ('crypt', 'caves', 'archive'):
    build(location)
