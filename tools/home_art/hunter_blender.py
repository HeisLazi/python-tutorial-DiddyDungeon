"""Blender (headless) -> raw renders of the hunter for the Home room.

Builds a chunky low-poly hunter from primitives (no add-ons, no armature),
poses it (stand / step A / step B), and renders 4 facings from a top-down 3/4
camera with a transparent background and no anti-aliasing.

    blender -b -P tools/home_art/hunter_blender.py -- <out_dir> [--skin umber] [--scale 4]

Output: <out_dir>/<facing>_<pose>.png at (16*scale x 32*scale).
make_hunter.py then shrinks, palette-maps and outlines them into the sheet.
"""

import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_dir = argv[0] if argv else "/tmp/hunter"
SCALE = 4
LOOK = {"skin": (0.58, 0.36, 0.22), "hair": (0.07, 0.06, 0.09), "cloth": (0.30, 0.27, 0.50), "cloak": (0.38, 0.24, 0.66),
        "accent": (0.92, 0.92, 0.92), "trim": (0.96, 0.77, 0.26), "boots": (0.10, 0.09, 0.13)}
for flag, key in (("--skin", "skin"),):
    if flag in argv:
        name = argv[argv.index(flag) + 1]
        LOOK[key] = {"umber": (0.58, 0.36, 0.22), "tan": (0.74, 0.55, 0.40), "pale": (0.90, 0.74, 0.64),
                     "deep": (0.22, 0.13, 0.09)}.get(name, LOOK[key])
if "--scale" in argv:
    SCALE = int(argv[argv.index("--scale") + 1])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.0)
    return mat


MATS = {key: material(key, rgb) for key, rgb in LOOK.items()}


def box(name, size, loc, mat, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.data.materials.append(MATS[mat])
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def pivot(name, loc, parent=None):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.location = loc
    if parent:
        obj.parent = parent
    return obj


root = pivot("root", (0, 0, 0))
# Proportions for a 16x32 sprite (FireRed's player is 16x32): legs, torso and head ~1/3 each.
LEG, TORSO, HEADH = 0.95, 0.95, 0.95
hips = pivot("hips", (0, 0, LEG), root)
box("torso", (1.0, 0.66, TORSO), (0, 0, LEG + TORSO / 2), "cloth", root)
box("belt", (1.04, 0.70, 0.14), (0, 0, LEG + 0.10), "trim", root)
box("scarf", (1.04, 0.72, 0.18), (0, 0, LEG + TORSO - 0.06), "accent", root)
box("chest_accent", (0.30, 0.04, 0.46), (0, -0.35, LEG + 0.42), "accent", root)
box("cloak_back", (1.04, 0.14, 0.95), (0, 0.38, LEG + 0.40), "cloak", root)
top = LEG + TORSO
head = pivot("head", (0, 0, top), root)
box("skull", (1.08, 0.96, HEADH), (0, 0, top + HEADH / 2), "skin", root)
box("hair_cap", (1.14, 1.0, 0.30), (0, 0.02, top + HEADH - 0.12), "hair", root)
box("hair_back", (1.12, 0.34, 0.80), (0, 0.46, top + HEADH / 2 - 0.02), "hair", root)
box("hair_side_l", (0.14, 0.7, 0.55), (-0.56, 0.10, top + HEADH / 2 + 0.10), "hair", root)
box("hair_side_r", (0.14, 0.7, 0.55), (0.56, 0.10, top + HEADH / 2 + 0.10), "hair", root)
for dx in (-0.42, -0.14, 0.14, 0.42):  # the locs, falling past the collar
    box(f"loc{dx}", (0.18, 0.18, 0.34), (dx, 0.52, top + 0.10), "hair", root)
box("goatee", (0.26, 0.10, 0.20), (0, -0.50, top + 0.12), "hair", root)
box("eye_l", (0.16, 0.05, 0.18), (-0.26, -0.50, top + 0.52), "boots", root)
box("eye_r", (0.16, 0.05, 0.18), (0.26, -0.50, top + 0.52), "boots", root)

legs = {}
arms = {}
for side, sx in (("l", -0.27), ("r", 0.27)):
    leg = pivot(f"leg_{side}", (sx, 0, LEG), root)
    box(f"thigh_{side}", (0.42, 0.46, 0.38), (sx, 0, LEG - 0.19), "cloth", leg)
    box(f"boot_{side}", (0.46, 0.60, 0.32), (sx, -0.05, 0.16), "boots", leg)
    legs[side] = leg
    arm = pivot(f"arm_{side}", (sx * 2.1, 0, top - 0.1), root)
    box(f"sleeve_{side}", (0.30, 0.34, 0.50), (sx * 2.1, 0, top - 0.35), "cloth", arm)
    box(f"hand_{side}", (0.30, 0.30, 0.18), (sx * 2.1, 0, top - 0.68), "skin", arm)
    arms[side] = arm

# Camera: orthographic, looking down at ~50 degrees, centred on the character.
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 3.4
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
tilt = math.radians(50)  # below horizontal
direction = (0, math.cos(tilt), -math.sin(tilt))
target = (0, 0, 1.45)
cam.location = (target[0] - direction[0] * 12, target[1] - direction[1] * 12, target[2] - direction[2] * 12)
cam.rotation_euler = (math.radians(90) - tilt, 0, 0)
scene.camera = cam

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_specular_highlight = False
scene.display.shading.show_object_outline = False
scene.render.film_transparent = True
scene.render.resolution_x = 16 * SCALE
scene.render.resolution_y = 32 * SCALE
scene.render.resolution_percentage = 100
scene.display.render_aa = "OFF"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"

POSES = {  # leg swing (radians, + = forward), arm swing is the opposite leg, vertical bob
    "stand": (0.0, 0.0),
    "stepa": (0.55, 0.04),
    "stepb": (-0.55, 0.04),
}
FACINGS = {"down": 0, "right": 90, "up": 180, "left": 270}  # degrees the body turns about Z


def pose(name):
    swing, bob = POSES[name]
    legs["l"].rotation_euler = (swing, 0, 0)
    legs["r"].rotation_euler = (-swing, 0, 0)
    arms["l"].rotation_euler = (-swing * 0.8, 0, 0)
    arms["r"].rotation_euler = (swing * 0.8, 0, 0)
    root.location = (0, 0, bob)


for facing, degrees in FACINGS.items():
    root.rotation_euler = (0, 0, math.radians(degrees))
    for name in POSES:
        pose(name)
        scene.render.filepath = f"{out_dir}/{facing}_{name}.png"
        bpy.ops.render.render(write_still=True)
print("done", out_dir)
