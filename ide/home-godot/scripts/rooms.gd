class_name Rooms
extends RefCounted
## The rooms of the castle, built in code from the tileset (art/tiles.png) and lit with
## pixel-banded 2D lights (home.gd). `build(h, id, level)` is called by the Home scene with
## itself as `h`. Every room has an upgrade LADDER: level 0 is the neglected base and each
## step up (bought with Embers) adds or changes ONE visible thing, up to the max level. You
## never jump from base to max: a room is about ten small, satisfying changes, each with a name
## and a cost (LADDERS below; the app can show them in the station panel).
## Layout: a 320x180 screen, 16px tiles, a back wall of 4 rows (cap, two faces, plinth) and
## floor below, top-down 3/4. Keep the station ids.
## Design targets: tools/home_art/concepts/*.png. Pieces: tools/home_art/hall_pieces.py.
##
## What makes a room "great" (the checklist every room follows, see docs/HOME_AND_ART.md):
##  1. Level 0 is a believable neglected room, the max level is the concept; each step in between is visible.
##  2. Depth: contact shadows under every prop, a shadow along the wall base, pillars/trim on the wall.
##  3. Light tells the story: warm pools, cold window beams, coloured glass patches on the floor.
##  4. Life: flames and lights flicker, embers and dust drift, cloth sways.
##  5. Wear and clutter at the start, polish at the top; nothing symmetrical by accident.
##  6. Scale: doors 48px, tables ~24px, the 40px hunter never dwarfs a prop that should be bigger.

# The upgrade ladders. cost = Embers for that step (a proposal: tune against the economy table in the README).
const LADDERS := {
	"great_hall": [
		{"name": "Clear and mend the hall", "cost": 18, "note": "rubble, puddles and cobwebs cleared, benches and barrels mended"},
		{"name": "Rebuild the hearth", "cost": 30, "note": "a proper fire, warmer light, and a second torch lit"},
		{"name": "Hang crest banners", "cost": 20, "note": "the torn rags are replaced"},
		{"name": "Lay the crimson runner", "cost": 24, "note": "a carpet from the door to the hearth"},
		{"name": "Reglaze the windows", "cost": 28, "note": "stained glass, coloured light on the floor"},
		{"name": "Floor the hall in marble", "cost": 68, "note": "polished marble over the whole floor, and columns on the walls"},
		{"name": "Hang the chandelier", "cost": 44, "note": "a chandelier and two guards"},
		{"name": "Set the banquet", "cost": 52, "note": "a long table, chairs and a rug"},
		{"name": "The grand finish", "cost": 60, "note": "blue-gold hearth, gold door, trim, urns, four guards"},
	],
	"library": [
		{"name": "Dust and sort", "cost": 16, "note": "cobwebs and scattered papers cleared, scrolls stacked"},
		{"name": "A proper desk", "cost": 20, "note": "a big oak desk, a quill and an open book"},
		{"name": "Fill the shelves", "cost": 24, "note": "two full bookcases"},
		{"name": "Light the reading lamps", "cost": 28, "note": "blue candelabra and wall sconces"},
		{"name": "Hang the star chart", "cost": 30, "note": "a constellation chart and navy banners"},
		{"name": "Lay the rugs", "cost": 34, "note": "a crimson rug under the desk"},
		{"name": "The globe and orrery", "cost": 40, "note": "a globe and a brass orrery"},
		{"name": "Enchant the shelves", "cost": 48, "note": "glowing tomes, crystals and a rolling ladder"},
		{"name": "Open the skylight", "cost": 56, "note": "a skylight, moonlight and floating pages"},
	],
	"armory": [
		{"name": "Sweep and clear", "cost": 16, "note": "cobwebs and rubble cleared"},
		{"name": "Stock the rack", "cost": 20, "note": "a few swords and spears on the rack, a barrel of spears"},
		{"name": "Mend the dummy", "cost": 24, "note": "a new wooden training dummy"},
		{"name": "Light the braziers", "cost": 28, "note": "two braziers and a second torch"},
		{"name": "Hang the banners", "cost": 30, "note": "crossed-sword banners and shields"},
		{"name": "Lay the ring in stone", "cost": 36, "note": "a stone-walled ring with a rope"},
		{"name": "The weapon wall", "cost": 42, "note": "a full rack of axes, swords and shields"},
		{"name": "Iron dummies", "cost": 48, "note": "armoured dummies and an archery target"},
		{"name": "Enchant the arms", "cost": 56, "note": "glowing runes and floating blades on stone pedestals"},
	],
}

# The Great Hall's steps by name (the level at which each thing appears).
const GH_CLEAN := 1
const GH_HEARTH := 2
const GH_BANNERS := 3
const GH_RUNNER := 4
const GH_GLASS := 5
const GH_MARBLE := 6
const GH_CHANDELIER := 7
const GH_BANQUET := 8
const GH_GRAND := 9

# The Hall of Arms' steps by name.
const HA_SWEEP := 1
const HA_RACK := 2
const HA_DUMMY := 3
const HA_BRAZIERS := 4
const HA_BANNERS := 5
const HA_RING := 6
const HA_WALL := 7
const HA_IRON := 8
const HA_ENCHANT := 9

# The Library's steps by name.
const LB_TIDY := 1
const LB_DESK := 2
const LB_SHELVES := 3
const LB_LAMPS := 4
const LB_CHART := 5
const LB_RUGS := 6
const LB_GLOBE := 7
const LB_ENCHANT := 8
const LB_SKY := 9


static func max_level(id: String) -> int:
	return (LADDERS.get(id, []) as Array).size()


static func tier_to_level(id: String, tier: int) -> int:
	## The app's older 0..3 tiers spread over the room's levels.
	return int(round(tier * max_level(id) / 3.0))


static func upgrade_name(id: String, level: int) -> String:
	## The name of the step that produced `level` (1-based).
	var ladder: Array = LADDERS.get(id, [])
	if level < 1 or level > ladder.size():
		return ""
	return str(ladder[level - 1]["name"])


static func spawn_default(_id: String) -> Vector2:
	return Vector2(160, 150)


static func build(h, id: String, level: int) -> void:
	match id:
		"great_hall":
			_great_hall(h, level)
		"library":
			_library(h, level)
		"armory":
			_armory(h, level)
		_:
			_great_hall(h, level)


## The shared shell: wall rows 0-3 and floor rows 4-11. `marble` is the range of columns paved in marble.
## `left`/`right` are optional exits ({"to": room, "spawn": feet position in that room}): a doorway in the side wall.
static func _shell(h, marble_from: int, marble_to: int, left := {}, right := {}, floor_kind := "stone") -> void:
	for y in range(h.ROWS):
		for x in range(h.COLS):
			var piece := ""
			if y == 0:
				piece = "wall_cap"
			elif y == 1 or y == 2:
				piece = "wall_s_%d" % ((x + y) % 2)
			elif y == 3:
				piece = "plinth_s"
			elif x >= marble_from and x <= marble_to:
				piece = "floor_chk_%d" % ((x + y) % 2)
			elif floor_kind == "wood":
				piece = "floor_wood_%d" % ((x * 5 + y * 3) % 3)
			else:
				piece = "floor_flag_%d" % ((x * 7 + y * 3) % 3)
			h.tile(piece, x, y)
	h.block(Rect2(0, 0, h.VIEW.x, 64))
	h.block(Rect2(0, 186, h.VIEW.x, 16))
	# The side walls, with a gap where there is a doorway.
	_side_wall(h, -16.0, left)
	_side_wall(h, h.VIEW.x - 4.0, right)
	# A shadow along the foot of the wall: it is what makes the wall feel upright.
	h.add_tint(Rect2(0, 64, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.34))
	h.add_tint(Rect2(0, 68, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.18))
	h.add_tint(Rect2(0, 72, h.VIEW.x, 4), Color(0.02, 0.02, 0.07, 0.08))


const DOOR_Y := 112.0
const DOOR_H := 60.0


static func _side_wall(h, x: float, exit: Dictionary) -> void:
	if exit.is_empty():
		h.block(Rect2(x, 0, 20, 200))
		return
	h.block(Rect2(x, 0, 20, DOOR_Y))
	h.block(Rect2(x, DOOR_Y + DOOR_H, 20, 200.0 - DOOR_Y - DOOR_H))
	var left: bool = x < 100.0
	var edge: float = 0.0 if left else h.VIEW.x
	# The doorway: a dark opening framed in stone, with a little light spilling out.
	var open := Rect2(edge - (0.0 if left else 12.0), DOOR_Y, 12.0, DOOR_H)
	h.add_tint(open, Color(0.02, 0.02, 0.06, 0.96))
	h.add_tint(Rect2(open.position.x, DOOR_Y - 6.0, 12.0, 6.0), Color(0.34, 0.36, 0.48, 1.0))
	h.add_tint(Rect2(open.position.x, DOOR_Y - 6.0, 12.0, 1.0), Color(0.55, 0.57, 0.7, 1.0))
	h.add_tint(Rect2(edge + (12.0 if left else -14.0), DOOR_Y, 2.0, DOOR_H), Color(0.2, 0.2, 0.3, 1.0))
	h.add_light(Vector2(edge + (14.0 if left else -14.0), DOOR_Y + 30.0), 40.0, Color(0.7, 0.8, 1.0), 0.35, 0.0)
	var trigger := Rect2(-40.0, DOOR_Y, 44.0, DOOR_H) if left else Rect2(h.VIEW.x - 4.0, DOOR_Y, 44.0, DOOR_H)
	h.door(trigger, str(exit["to"]), exit["spawn"])


## A prop with a contact shadow and a feet blocker.
static func _prop(h, piece: String, feet: Vector2, w: float, d: float, shadow_w := 0.0) -> Sprite2D:
	h.add_shadow(feet, shadow_w if shadow_w > 0.0 else w, maxf(4.0, d + 1.0))
	return h.obj(piece, feet, Rect2(feet.x - w / 2.0, feet.y - d, w, d))


static func _great_hall(h, lv: int) -> void:
	var marble_from := -1
	var marble_to := -1
	if lv >= GH_MARBLE:
		marble_from = 0
		marble_to = 19
	_shell(h, marble_from, marble_to, {"to": "library", "spawn": Vector2(290, 142)}, {"to": "armory", "spawn": Vector2(30, 142)})
	var marble := lv >= GH_MARBLE
	var glass := lv >= GH_GLASS
	# The ambient light brightens a little with every step.
	h.set_ambient(Color(0.40, 0.41, 0.56).lerp(Color(0.52, 0.50, 0.66), lv / float(GH_GRAND)))

	# ── The wall: columns, damp stains, cobwebs ──
	if lv < GH_CLEAN:
		h.bg("cobweb_l", Vector2(2, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 120))
	if lv < GH_BANNERS:
		for x in [26.0, 104.0, 250.0]:
			h.bg("stain", Vector2(x, 18))
	var pillar_piece := "pillar_g" if lv >= GH_GRAND else "pillar_s"
	var pillar_xs: Array = [10.0, 310.0]
	if lv >= GH_MARBLE:
		pillar_xs = [10.0, 60.0, 260.0, 310.0]
	for x in pillar_xs:
		h.bg(pillar_piece, Vector2(x, 66), true)
	if lv >= GH_GRAND:
		h.add_tint(Rect2(0, 62, h.VIEW.x, 2), Color(0.95, 0.74, 0.25, 0.9))     # gold trim along the wall base

	# ── Floor: wear at the start, a runner once laid, a rug under the banquet ──
	if lv < GH_CLEAN:
		h.bg("rubble_1", Vector2(56, 152), true)
		h.bg("rubble_0", Vector2(250, 104), true)
		h.bg("rubble_0", Vector2(124, 170), true)
		h.bg("puddle", Vector2(214, 156), true)
	if lv >= GH_RUNNER:
		for row in range(5, 12):
			h.bg("carpet", Vector2(144, row * 16))
	if lv >= GH_BANQUET:
		h.bg("rug_table", Vector2(210, 82))

	# ── Windows: plain and cold, then stained glass throwing coloured light on the floor ──
	var window_kind := "window_glass" if glass else "window_plain"
	var beam := Color(0.50, 0.60, 0.95, 0.10 + (0.19 if glass else 0.0) * minf(1.0, (lv - GH_GLASS) / float(GH_GRAND - GH_GLASS)))
	var panes: Array = [Color(0.95, 0.25, 0.30, 0.30), Color(0.30, 0.45, 1.0, 0.32), Color(1.0, 0.78, 0.28, 0.30),
		Color(0.65, 0.35, 0.95, 0.30), Color(0.35, 0.65, 1.0, 0.30), Color(0.95, 0.35, 0.40, 0.28)]
	for x in [84.0, 236.0]:
		var dir := 1.0 if x < 160.0 else -1.0
		h.bg(window_kind, Vector2(x, 60), true)
		h.add_shaft(Vector2(x - 12, 40), 24.0, 96.0, 30.0 * dir, beam)
		h.add_light(Vector2(x, 66), 56.0, Color(0.45, 0.58, 0.95), 0.35 + 0.015 * lv, 0.0)
		# The patch of window-light on the floor, shaped like the panes.
		var fx: float = x + 34.0 * dir
		var k := 0
		for row in 3:
			for col in 2:
				var c: Color = panes[k % panes.size()] if glass else Color(0.5, 0.6, 0.95, 0.15)
				var x0: float = fx - 9.0 + col * 9.0 + row * 2.0 * dir
				var y0: float = 100.0 + row * 9.0
				h.add_patch(PackedVector2Array([Vector2(x0, y0), Vector2(x0 + 8, y0), Vector2(x0 + 9, y0 + 8), Vector2(x0 + 1, y0 + 8)]), c)
				k += 1

	# ── Banners: torn rags at the start, crimson crests after (they sway) ──
	for x in [122.0, 198.0]:
		var banner: Sprite2D = h.bg("banner_crest" if lv >= GH_BANNERS else "banner_torn", Vector2(x, 56), true)
		h.sway(banner, 0.9, 1.7, 36.0)

	# ── The hearth: a small fire, a good fire, then blue-gold with a reflection on the floor ──
	h.hearth_base = "hearthg" if lv >= GH_GRAND else ("hearthm" if lv >= GH_HEARTH else "hearthb")
	h.hearth_sprite = h.bg(h.hearth_base + "_0", Vector2(160, 76), true)
	var blue := lv >= GH_GRAND
	var hearth_color := Color(0.55, 0.72, 1.0) if blue else Color("ff9a4a")
	h.add_light(Vector2(160, 66), 100.0 + 1.2 * lv, hearth_color, (0.8 if blue else 1.1 + 0.015 * lv + (0.1 if lv >= GH_HEARTH else 0.0)), 0.22)
	h.add_shadow(Vector2(160, 78), 52.0, 6.0, 0.3)
	h.block(Rect2(136, 66, 48, 12))
	h.station("hearth", "Rest at the Hearth", Rect2(136, 78, 48, 22), Vector2(160, 8))
	h.add_embers(Rect2(150, 60, 20, 6), Color("8cc8ff") if blue else Color("ffb347"), 6 + int(lv * 0.5), 16.0)
	if marble:
		var glow := Color(0.4, 0.6, 1.0, 0.14) if blue else Color(1.0, 0.6, 0.3, 0.09)
		h.add_shaft(Vector2(146, 82), 28.0, 44.0, 0.0, glow)       # the fire reflected in the polished floor

	# ── Wall torches: one, then a second ──
	var torch_x: Array = [40.0]
	if lv >= GH_HEARTH:
		torch_x = [40.0, 280.0]
	for x in torch_x:
		h.anim("torch", Vector2(x, 52), Rect2(), true)
		h.add_light(Vector2(x, 38), 52.0, Color("ffb36b"), 0.8 + 0.03 * lv, 0.3)

	# ── Furniture and clutter ──
	var benches_fixed := lv >= GH_CLEAN
	var bench_kind := "bench" if benches_fixed else "bench_broken"
	var bench_spots: Array = [Vector2(108, 112), Vector2(74, 142)]
	if lv < GH_BANQUET:
		bench_spots.append_array([Vector2(212, 112), Vector2(246, 142)])
	if not benches_fixed:
		bench_spots = [Vector2(104, 112), Vector2(74, 140), Vector2(232, 150)]
	for at in bench_spots:
		_prop(h, bench_kind, at, 30.0, 8.0)
	if lv < GH_BANQUET:
		_prop(h, "table_small", Vector2(238, 118) if lv < GH_CLEAN else Vector2(238, 96), 24.0, 10.0)
	if lv < GH_CLEAN:
		_prop(h, "crate_broken", Vector2(34, 100), 18.0, 8.0)
		_prop(h, "barrel", Vector2(288, 96), 14.0, 7.0)
	elif lv < GH_CHANDELIER:
		_prop(h, "barrel", Vector2(30, 98), 14.0, 7.0)
		_prop(h, "barrel", Vector2(48, 102), 14.0, 7.0)
		_prop(h, "crate", Vector2(292, 100), 18.0, 8.0)
	if lv >= GH_CHANDELIER:
		for at in [Vector2(32, 100), Vector2(288, 100)]:
			_prop(h, "knight", at, 14.0, 6.0, 16.0)
		for x in [124.0, 196.0]:
			_prop(h, "urn_gold" if lv >= GH_GRAND else "urn", Vector2(x, 178), 12.0, 6.0)
		h.add_chain(92.0, 2.0, 96.0)
		h.add_shadow(Vector2(92, 160), 40.0, 10.0, 0.22)
		h.anim("chandelier", Vector2(92, 132))
		h.add_light(Vector2(92, 110), 92.0, Color("ffcf8a"), 0.8 + 0.08 * (lv - GH_CHANDELIER), 0.2)
	if lv >= GH_BANQUET:
		_prop(h, "table_long", Vector2(252, 112), 64.0, 14.0)
		for cx in [236.0, 268.0]:
			_prop(h, "chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 92), 12.0, 6.0)
			_prop(h, "chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 136), 12.0, 6.0)
		h.add_light(Vector2(252, 102), 48.0, Color("ffd27a"), 0.7, 0.2)
	if lv >= GH_GRAND:
		for at in [Vector2(108, 86), Vector2(212, 86)]:
			_prop(h, "knight", at, 14.0, 6.0, 16.0)
		h.add_embers(Rect2(40, 90, 240, 80), Color("ffd27a"), 14, 6.0, 4.5)

	# ── Dust drifting in the beams: thick in a neglected hall, thin in a kept one ──
	h.add_embers(Rect2(40, 74, 240, 90), Color(0.75, 0.80, 1.0, 0.55), maxi(4, 16 - lv), 3.0, 5.0)

	# ── The great door: a plain oak door until the grand finish ──
	h.bg("door_gold" if lv >= GH_GRAND else "door_wood", Vector2(160, 186), true)
	h.station("door", "Go to the Forge", Rect2(138, 158, 44, 24), Vector2(160, 134))


static func _library(h, lv: int) -> void:
	_shell(h, -1, -1, {}, {"to": "great_hall", "spawn": Vector2(30, 142)}, "wood")
	h.set_ambient(Color(0.34, 0.37, 0.52).lerp(Color(0.46, 0.50, 0.72), lv / float(LB_SKY)))
	h.add_tint(Rect2(0, 0, h.VIEW.x, 64), Color(0.10, 0.18, 0.45, 0.10))      # a cooler wall than the hall

	# ── The wall: neglect, then a window, banners and the chart ──
	if lv < LB_TIDY:
		h.bg("cobweb_l", Vector2(2, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 16))
		for x in [150.0, 210.0]:
			h.bg("stain", Vector2(x, 18))
	h.bg("window_lib", Vector2(100, 60), true)
	h.add_shaft(Vector2(88, 40), 24.0, 90.0, 26.0, Color(0.5, 0.6, 0.95, 0.12 + 0.01 * lv))
	h.add_light(Vector2(100, 66), 56.0, Color(0.45, 0.58, 0.95), 0.35 + 0.02 * lv, 0.0)
	if lv >= LB_CHART:
		h.bg("star_chart", Vector2(222, 60), true)
		for x in [132.0, 188.0]:
			var banner: Sprite2D = h.bg("banner_blue", Vector2(x, 56), true)
			h.sway(banner, 0.8, 1.6, 36.0)

	# ── Shelves: one half-empty case at first, two full cases, then enchanted ──
	var shelf := "bookshelf_glow" if lv >= LB_ENCHANT else ("bookshelf_full" if lv >= LB_SHELVES else "bookshelf_sparse")
	var shelf_spots: Array = [Vector2(272, 74)]
	if lv >= LB_SHELVES:
		shelf_spots = [Vector2(40, 74), Vector2(272, 74)]
	for at in shelf_spots:
		h.add_shadow(at, 38.0, 5.0, 0.3)
		h.bg(shelf, at, true)
		h.block(Rect2(at.x - 20, 66, 40, 8))
		if lv >= LB_ENCHANT:
			h.add_light(Vector2(at.x, 48), 40.0, Color(1.0, 0.45, 0.5), 0.5, 0.25)

	# ── The rug under the desk: a worn grey one, then crimson ──
	if lv >= LB_RUGS:
		h.bg("rug_crimson", Vector2(86, 104))
	else:
		h.add_tint(Rect2(94, 110, 68, 28), Color(0.30, 0.29, 0.33, 1.0))
		h.add_tint(Rect2(96, 112, 64, 24), Color(0.22, 0.21, 0.26, 1.0))

	# ── The desk and the study station ──
	if lv >= LB_DESK:
		_prop(h, "desk_big", Vector2(128, 120), 40.0, 10.0)
	else:
		_prop(h, "desk_small", Vector2(128, 114), 24.0, 8.0)
		_prop(h, "chair_lib", Vector2(128, 132), 12.0, 6.0)
	h.add_light(Vector2(128, 100), 44.0, Color("ffcf8a"), 0.7, 0.25)
	h.station("study", "Study at the desk", Rect2(98, 126, 64, 28), Vector2(128, 82))

	# ── Papers: scattered at first, stacked once the room is sorted ──
	if lv < LB_TIDY:
		for at in [Vector2(70, 140), Vector2(210, 150), Vector2(180, 122), Vector2(40, 112)]:
			h.bg("scrolls", at, true)
	else:
		_prop(h, "scrolls", Vector2(168, 118), 14.0, 5.0)

	# ── Reading lamps: blue candelabra and sconces ──
	if lv >= LB_LAMPS:
		for at in [Vector2(76, 104), Vector2(232, 104)]:
			h.add_shadow(at, 14.0, 4.0)
			h.anim("candelabra_lib", at, Rect2(at.x - 6, at.y - 5, 12, 5))
			h.add_light(at + Vector2(0, -22), 58.0, Color(0.5, 0.7, 1.0), 0.85, 0.3)
		for x in [66.0, 304.0]:
			h.anim("sconce_blue", Vector2(x, 54), Rect2(), true)
			h.add_light(Vector2(x, 40), 44.0, Color(0.5, 0.7, 1.0), 0.7, 0.3)

	# ── The globe and the orrery ──
	if lv >= LB_GLOBE:
		_prop(h, "globe", Vector2(184, 112), 14.0, 6.0)
		_prop(h, "orrery", Vector2(214, 118), 18.0, 7.0)

	# ── Enchanted: crystals and a rolling ladder ──
	if lv >= LB_ENCHANT:
		for at in [Vector2(52, 138), Vector2(256, 146)]:
			_prop(h, "crystals", at, 14.0, 6.0)
			h.add_light(at + Vector2(0, -10), 44.0, Color(0.5, 0.6, 1.0), 0.8, 0.3)
		_prop(h, "ladder", Vector2(246, 92), 20.0, 6.0)

	# ── The skylight: moonlight falls in a column, pages float up ──
	if lv >= LB_SKY:
		h.bg("skylight", Vector2(160, 46), true)
		h.add_shaft(Vector2(146, 44), 28.0, 110.0, 0.0, Color(0.7, 0.85, 1.0, 0.30))
		h.add_light(Vector2(160, 70), 90.0, Color(0.7, 0.85, 1.0), 0.9, 0.05)
		h.add_patch(PackedVector2Array([Vector2(138, 150), Vector2(182, 150), Vector2(188, 160), Vector2(132, 160)]), Color(0.7, 0.85, 1.0, 0.18))
		h.add_embers(Rect2(140, 60, 40, 80), Color(1.0, 1.0, 0.92, 0.95), 7, 5.0, 4.5, 2.0)
		h.add_embers(Rect2(20, 70, 280, 100), Color(0.6, 0.8, 1.0, 0.8), 14, 4.0, 5.0)

	# ── Dust in the beams ──
	h.add_embers(Rect2(40, 74, 240, 90), Color(0.75, 0.80, 1.0, 0.5), maxi(4, 14 - lv), 3.0, 5.0)


static func _ellipse(cx: float, cy: float, rx: float, ry: float, n := 28) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in n:
		var a := TAU * i / float(n)
		pts.append(Vector2(cx + cos(a) * rx, cy + sin(a) * ry))
	return pts


static func _armory(h, lv: int) -> void:
	_shell(h, -1, -1, {"to": "great_hall", "spawn": Vector2(290, 142)}, {}, "stone")
	h.set_ambient(Color(0.48, 0.44, 0.50).lerp(Color(0.56, 0.49, 0.48), lv / float(HA_ENCHANT)))
	h.add_tint(Rect2(0, 0, h.VIEW.x, 64), Color(0.35, 0.18, 0.10, 0.08))      # warm stone: torchlit

	# ── The wall: cobwebs, barred windows, torn banner, shields ──
	if lv < HA_SWEEP:
		h.bg("cobweb_l", Vector2(2, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 16))
		h.bg("rubble_1", Vector2(150, 176), true)
		h.bg("rubble_0", Vector2(60, 168), true)
		h.bg("rubble_0", Vector2(270, 98), true)
	for x in [60.0, 150.0, 250.0]:
		h.bg("window_arms", Vector2(x, 60), true)
		h.add_shaft(Vector2(x - 12, 40), 24.0, 80.0, 20.0, Color(0.55, 0.6, 0.85, 0.08))
	if lv >= HA_BANNERS:
		for x in [105.0, 205.0]:
			var banner: Sprite2D = h.bg("banner_swords", Vector2(x, 56), true)
			h.sway(banner, 0.8, 1.6, 38.0)
		for x in [128.0, 178.0]:
			h.bg("shield_wall", Vector2(x, 50), true)
	else:
		var torn: Sprite2D = h.bg("banner_torn_red", Vector2(205, 56), true)
		h.sway(torn, 0.8, 1.6, 38.0)

	# ── Torches and braziers ──
	var torch_x: Array = [40.0]
	if lv >= HA_BRAZIERS:
		torch_x = [40.0, 290.0]
	for x in torch_x:
		h.anim("torch_arms", Vector2(x, 54), Rect2(), true)
		h.add_light(Vector2(x, 38), 64.0, Color("ff9a4a"), 0.95, 0.3)
	var brazier_spots: Array = []
	if lv >= HA_BRAZIERS:
		brazier_spots = [Vector2(26, 138), Vector2(298, 138)]
	if lv >= HA_ENCHANT:
		brazier_spots.append_array([Vector2(26, 96), Vector2(298, 96)])
	for at in brazier_spots:
		h.add_shadow(at, 16.0, 5.0)
		h.anim("brazier_img", at, Rect2(at.x - 7, at.y - 6, 14, 6))
		h.add_light(at + Vector2(0, -16), 70.0, Color("ff8a3a"), 1.0, 0.3)

	# ── The weapon rack and the armory station ──
	var rack := "rack_empty"
	if lv >= HA_WALL:
		rack = "rack_full"
	elif lv >= HA_RACK:
		rack = "rack_few"
	_prop(h, rack, Vector2(104, 80), 36.0 if lv >= HA_WALL else 26.0, 8.0)
	h.station("armory", "Open the Armory", Rect2(78, 84, 52, 28), Vector2(104, 14))
	if lv >= HA_RACK:
		_prop(h, "barrel_spears", Vector2(140, 80), 12.0, 6.0)

	# ── The sparring ring and its dummy ──
	var ring_center := Vector2(240, 128)
	if lv >= HA_RING:
		h.add_shadow(Vector2(240, 150), 80.0, 8.0, 0.3)
		h.bg("ring_stone", Vector2(240, 152), true)
	else:
		var dirt := Polygon2D.new()
		dirt.polygon = _ellipse(ring_center.x, ring_center.y + 4.0, 38.0, 20.0)
		dirt.color = Color(0.30, 0.21, 0.15, 1.0)
		h.background.add_child(dirt)
		var rope := Line2D.new()
		rope.points = _ellipse(ring_center.x, ring_center.y + 4.0, 38.0, 20.0)
		rope.closed = true
		rope.width = 1.0
		rope.default_color = Color(0.62, 0.5, 0.3, 1.0)
		h.background.add_child(rope)
	var dummy_piece := "dummy"
	if lv >= HA_IRON:
		dummy_piece = "dummy_iron"
	elif lv >= HA_DUMMY:
		dummy_piece = "dummy_wood"
	h.add_shadow(Vector2(240, 134), 14.0, 5.0)
	h.obj(dummy_piece, Vector2(240, 134), Rect2(234, 130, 12, 5))
	h.station("training", "Train in the ring", Rect2(204, 108, 72, 44), Vector2(240, 82))
	if lv >= HA_IRON:
		_prop(h, "dummy_iron", Vector2(70, 152), 14.0, 6.0)
		_prop(h, "target", Vector2(296, 108), 16.0, 6.0)

	# ── Enchanted: glowing runes on the ring, blades floating over stone pedestals ──
	if lv >= HA_ENCHANT:
		h.add_patch(_ellipse(240.0, 132.0, 40.0, 21.0), Color(1.0, 0.55, 0.2, 0.12))
		h.add_embers(Rect2(210, 120, 60, 20), Color("ffb347"), 10, 10.0, 2.5)
		for at in [Vector2(54, 108), Vector2(54, 136), Vector2(86, 122)]:
			_prop(h, "pedestal_glow", at, 12.0, 6.0)
			h.add_light(at + Vector2(0, -26), 34.0, Color(0.55, 0.75, 1.0), 0.45, 0.2)
		h.add_embers(Rect2(40, 90, 60, 60), Color(0.7, 0.85, 1.0, 0.9), 8, 6.0, 3.5)

	# ── Dust and smoke in the torchlight ──
	h.add_embers(Rect2(40, 74, 240, 90), Color(0.9, 0.8, 0.7, 0.45), maxi(4, 14 - lv), 3.0, 5.0)
