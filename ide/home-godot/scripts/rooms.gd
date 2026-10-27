class_name Rooms
extends RefCounted
## The rooms of the castle, built in code from the tileset (art/tiles.png) and lit with
## pixel-banded 2D lights (home.gd). `build(h, id, tier)` is called by the Home scene with
## itself as `h`; each room reads its tier (0 = base .. 3 = max) to decide what exists and
## how bright it is. Layout: a 320x180 screen, 16px tiles, a back wall of 4 rows (cap, two
## faces, plinth) and floor below, top-down 3/4 like the old hall. Keep the station ids.
## Design targets: tools/home_art/concepts/*.png. Pieces: tools/home_art/hall_pieces.py.
##
## What makes a room "great" (the checklist every room follows, see docs/HOME_AND_ART.md):
##  1. Tier 0 is a believable neglected room, max is the concept: change props, light AND motion.
##  2. Depth: contact shadows under every prop, a shadow along the wall base, pillars/trim on the wall.
##  3. Light tells the story: warm pools, cold window beams, coloured glass patches on the floor.
##  4. Life: flames and lights flicker, embers and dust drift, cloth sways.
##  5. Wear and clutter at the start, polish at the top; nothing symmetrical by accident.
##  6. Scale: doors 48px, tables ~24px, the 40px hunter never dwarfs a prop that should be bigger.

static func spawn_default(_id: String) -> Vector2:
	return Vector2(160, 150)


static func build(h, id: String, tier: int) -> void:
	match id:
		"great_hall":
			_great_hall(h, tier)
		_:
			_great_hall(h, tier)


## The shared shell: wall rows 0-3 and floor rows 4-11, with the room's own floor style.
static func _shell(h, floor_style: String) -> void:
	for y in range(h.ROWS):
		for x in range(h.COLS):
			var piece := ""
			if y == 0:
				piece = "wall_cap"
			elif y == 1 or y == 2:
				piece = "wall_s_%d" % ((x + y) % 2)
			elif y == 3:
				piece = "plinth_s"
			elif floor_style == "flag":
				piece = "floor_flag_%d" % ((x * 7 + y * 3) % 3)
			else:
				piece = "floor_chk_%d" % ((x + y) % 2)
			h.tile(piece, x, y)
	h.block(Rect2(0, 0, h.VIEW.x, 64))
	h.block(Rect2(-16, 0, 20, 200))
	h.block(Rect2(h.VIEW.x - 4, 0, 20, 200))
	h.block(Rect2(0, 186, h.VIEW.x, 16))
	# A shadow along the foot of the wall: it is what makes the wall feel upright.
	h.add_tint(Rect2(0, 64, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.34))
	h.add_tint(Rect2(0, 68, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.18))
	h.add_tint(Rect2(0, 72, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.08))


## A prop with a contact shadow and a feet blocker.
static func _prop(h, piece: String, feet: Vector2, w: float, d: float, shadow_w := 0.0) -> Sprite2D:
	h.add_shadow(feet, shadow_w if shadow_w > 0.0 else w, maxf(4.0, d + 1.0))
	return h.obj(piece, feet, Rect2(feet.x - w / 2.0, feet.y - d, w, d))


static func _great_hall(h, tier: int) -> void:
	_shell(h, "flag" if tier < 2 else "marble")
	var ambient := [Color(0.40, 0.41, 0.56), Color(0.44, 0.44, 0.60), Color(0.44, 0.44, 0.64), Color(0.48, 0.48, 0.72)]
	h.set_ambient(ambient[tier])

	# ── The wall: columns, damp stains, cobwebs ──
	if tier == 0:
		h.bg("cobweb_l", Vector2(2, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 120))
		for x in [26.0, 104.0, 250.0]:
			h.bg("stain", Vector2(x, 18))
	var pillar_piece := "pillar_g" if tier >= 3 else "pillar_s"
	var pillar_xs: Array = [[10.0, 310.0], [10.0, 310.0], [10.0, 60.0, 260.0, 310.0], [10.0, 60.0, 260.0, 310.0]][tier]
	for x in pillar_xs:
		h.bg(pillar_piece, Vector2(x, 66), true)

	# ── Floor: wear at the start, a runner once repaired, a rug under the banquet ──
	if tier == 0:
		h.bg("rubble_1", Vector2(56, 152), true)
		h.bg("rubble_0", Vector2(250, 104), true)
		h.bg("rubble_0", Vector2(124, 170), true)
		h.bg("puddle", Vector2(214, 156), true)
	if tier >= 1:
		for row in range(5, 12):
			h.bg("carpet", Vector2(144, row * 16))
	if tier >= 3:
		h.bg("rug_table", Vector2(210, 104))

	# ── Windows: plain and cold, then stained glass throwing coloured light on the floor ──
	var window_kind := "window_plain" if tier < 2 else "window_glass"
	var beam := Color(0.50, 0.60, 0.95, 0.10 + 0.07 * tier)
	var panes: Array = [Color(0.95, 0.25, 0.30, 0.30), Color(0.30, 0.45, 1.0, 0.32), Color(1.0, 0.78, 0.28, 0.30),
		Color(0.65, 0.35, 0.95, 0.30), Color(0.35, 0.65, 1.0, 0.30), Color(0.95, 0.35, 0.40, 0.28)]
	for x in [84.0, 236.0]:
		var dir := 1.0 if x < 160.0 else -1.0
		h.bg(window_kind, Vector2(x, 60), true)
		h.add_shaft(Vector2(x - 12, 40), 24.0, 96.0, 30.0 * dir, beam)
		h.add_light(Vector2(x, 66), 56.0, Color(0.45, 0.58, 0.95), 0.35 + 0.1 * tier, 0.0)
		# The patch of window-light on the floor, shaped like the panes.
		var fx: float = x + 34.0 * dir
		var k := 0
		for row in 3:
			for col in 2:
				var c: Color = panes[k % panes.size()] if tier >= 2 else Color(0.5, 0.6, 0.95, 0.15)
				var x0: float = fx - 9.0 + col * 9.0 + row * 2.0 * dir
				var y0: float = 100.0 + row * 9.0
				h.add_patch(PackedVector2Array([Vector2(x0, y0), Vector2(x0 + 8, y0), Vector2(x0 + 9, y0 + 8), Vector2(x0 + 1, y0 + 8)]), c)
				k += 1

	# ── Banners: torn rags at the start, crimson crests after (they sway) ──
	for x in [122.0, 198.0]:
		var banner: Sprite2D = h.bg("banner_torn" if tier == 0 else "banner_crest", Vector2(x, 56), true)
		h.sway(banner, 0.9, 1.7, 36.0)

	# ── The hearth: a small fire, a good fire, then blue-gold with a reflection on the floor ──
	h.hearth_base = ["hearthb", "hearthm", "hearthm", "hearthg"][tier]
	h.hearth_sprite = h.bg(h.hearth_base + "_0", Vector2(160, 76), true)
	var hearth_color := Color("ff9a4a") if tier < 3 else Color(0.55, 0.72, 1.0)
	h.add_light(Vector2(160, 66), [108.0, 100.0, 104.0, 112.0][tier], hearth_color, [1.25, 1.15, 1.2, 1.3][tier], 0.22)
	h.add_shadow(Vector2(160, 78), 52.0, 6.0, 0.3)
	h.block(Rect2(136, 66, 48, 12))
	h.station("hearth", "Rest at the Hearth", Rect2(136, 78, 48, 22), Vector2(160, 8))
	h.add_embers(Rect2(150, 60, 20, 6), Color("ffb347") if tier < 3 else Color("8cc8ff"), 6 + tier * 3, 16.0)
	if tier >= 2:
		var glow := Color(0.4, 0.6, 1.0, 0.14) if tier >= 3 else Color(1.0, 0.6, 0.3, 0.09)
		h.add_shaft(Vector2(146, 82), 28.0, 44.0, 0.0, glow)       # the fire reflected in the polished floor

	if tier >= 3:
		h.add_tint(Rect2(0, 62, h.VIEW.x, 2), Color(0.95, 0.74, 0.25, 0.9))     # gold trim along the wall base

	# ── Wall torches ──
	var torch_x: Array = [[40.0], [40.0, 280.0], [40.0, 280.0], [40.0, 280.0]][tier]
	for x in torch_x:
		h.anim("torch", Vector2(x, 52), Rect2(), true)
		h.add_light(Vector2(x, 38), 52.0, Color("ffb36b"), 0.85, 0.3)

	# ── Furniture and clutter ──
	if tier == 0:
		for at in [Vector2(104, 112), Vector2(74, 140), Vector2(232, 150)]:
			_prop(h, "bench_broken", at, 30.0, 8.0)
		_prop(h, "table_small", Vector2(238, 118), 24.0, 10.0)
		_prop(h, "crate_broken", Vector2(34, 100), 18.0, 8.0)
		_prop(h, "barrel", Vector2(288, 96), 14.0, 7.0)
	elif tier == 1:
		for at in [Vector2(108, 112), Vector2(212, 112), Vector2(74, 142), Vector2(246, 142)]:
			_prop(h, "bench", at, 30.0, 8.0)
		_prop(h, "table_small", Vector2(238, 96), 24.0, 10.0)
		_prop(h, "barrel", Vector2(30, 98), 14.0, 7.0)
		_prop(h, "barrel", Vector2(48, 102), 14.0, 7.0)
		_prop(h, "crate", Vector2(292, 100), 18.0, 8.0)
	if tier >= 2:
		for at in [Vector2(32, 100), Vector2(288, 100)]:
			_prop(h, "knight", at, 14.0, 6.0, 16.0)
	if tier >= 3:
		for at in [Vector2(108, 86), Vector2(212, 86)]:
			_prop(h, "knight", at, 14.0, 6.0, 16.0)
		_prop(h, "table_long", Vector2(252, 130), 64.0, 14.0)
		for cx in [236.0, 268.0]:
			_prop(h, "chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 110), 12.0, 6.0)
			_prop(h, "chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 154), 12.0, 6.0)
		for x in [124.0, 196.0]:
			_prop(h, "urn_gold", Vector2(x, 178), 12.0, 6.0)
		h.add_light(Vector2(252, 120), 48.0, Color("ffd27a"), 0.7, 0.2)
		h.add_embers(Rect2(40, 90, 240, 80), Color("ffd27a"), 14, 6.0, 4.5)
	elif tier == 2:
		for x in [124.0, 196.0]:
			_prop(h, "urn", Vector2(x, 178), 12.0, 6.0)
	if tier >= 2:
		h.add_chain(92.0, 2.0, 96.0)
		h.add_shadow(Vector2(92, 160), 40.0, 10.0, 0.22)
		h.anim("chandelier", Vector2(92, 132))
		h.add_light(Vector2(92, 110), 92.0, Color("ffcf8a"), 0.8 + 0.15 * (tier - 2), 0.2)

	# ── Dust drifting in the beams (all tiers, more at the start) ──
	h.add_embers(Rect2(40, 74, 240, 90), Color(0.75, 0.80, 1.0, 0.55), 10 if tier > 0 else 16, 3.0, 5.0)

	# ── The great door: a plain oak door at first, carved gold at the top ──
	h.bg("door_gold" if tier >= 3 else "door_wood", Vector2(160, 186), true)
	h.station("door", "Go to the Forge", Rect2(138, 158, 44, 24), Vector2(160, 134))
