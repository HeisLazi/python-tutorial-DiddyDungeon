class_name Rooms
extends RefCounted
## The rooms of the castle, built in code from the tileset (art/tiles.png) and lit with
## pixel-banded 2D lights (home.gd). `build(h, id, tier)` is called by the Home scene with
## itself as `h`; each room reads its tier (0 = base .. 3 = max) to decide what exists and
## how bright it is. Layout: a 320x180 screen, 16px tiles, a back wall of 4 rows (cap, two
## faces, plinth) and floor below, top-down 3/4 like the old hall. Keep the station ids.
## Design targets: tools/home_art/concepts/*.png. Pieces: tools/home_art/hall_pieces.py.

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


static func _foot_block(h, at: Vector2, w := 12.0, d := 6.0) -> void:
	h.block(Rect2(at.x - w / 2.0, at.y - d, w, d))


static func _great_hall(h, tier: int) -> void:
	_shell(h, "flag" if tier < 2 else "marble")
	var ambient := [Color(0.40, 0.41, 0.56), Color(0.44, 0.44, 0.60), Color(0.44, 0.44, 0.64), Color(0.48, 0.48, 0.72)]
	h.set_ambient(ambient[tier])

	# Cobwebs in the corners of a neglected hall.
	if tier == 0:
		h.bg("cobweb_l", Vector2(2, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 16))
		h.bg("cobweb_r", Vector2(h.VIEW.x - 16, 120))

	# The runner leads from the door to the hearth once you have repaired the hall.
	if tier >= 1:
		for row in range(5, 12):
			h.bg("carpet", Vector2(144, row * 16))

	# Windows: plain and cold at first, stained glass from tier 2, with beams of moonlight.
	var window_kind := "window_plain" if tier < 2 else "window_glass"
	var beam := Color(0.50, 0.60, 0.95, 0.10 + 0.07 * tier)
	for x in [84.0, 236.0]:
		h.bg(window_kind, Vector2(x, 60), true)
		h.add_shaft(Vector2(x - 12, 40), 24.0, 96.0, 30.0 if x < 160.0 else -30.0, beam)
		h.add_light(Vector2(x, 66), 56.0, Color(0.45, 0.58, 0.95), 0.35 + 0.1 * tier, 0.0)

	# Banners: torn rags at the start, crimson crests after.
	for x in [122.0, 198.0]:
		h.bg("banner_torn" if tier == 0 else "banner_crest", Vector2(x, 56), true)

	# The hearth in the middle of the back wall: a small fire, a good fire, then blue-gold.
	h.hearth_base = ["hearthb", "hearthm", "hearthm", "hearthg"][tier]
	h.hearth_sprite = h.bg(h.hearth_base + "_0", Vector2(160, 76), true)
	var hearth_color := Color("ff9a4a") if tier < 3 else Color(0.55, 0.72, 1.0)
	h.add_light(Vector2(160, 66), [108.0, 100.0, 104.0, 112.0][tier], hearth_color, [1.25, 1.15, 1.2, 1.3][tier], 0.22)
	h.block(Rect2(136, 66, 48, 12))
	h.station("hearth", "Rest at the Hearth", Rect2(136, 78, 48, 22), Vector2(160, 8))
	h.add_embers(Rect2(150, 60, 20, 6), Color("ffb347") if tier < 3 else Color("8cc8ff"), 6 + tier * 3, 16.0)

	# Wall torches: one at the start, more as the hall is repaired.
	var torch_x: Array = [[40.0], [40.0, 280.0], [40.0, 280.0], [40.0, 280.0]][tier]
	for x in torch_x:
		h.anim("torch", Vector2(x, 52), Rect2(), true)
		h.add_light(Vector2(x, 38), 52.0, Color("ffb36b"), 0.85, 0.3)

	# Furniture: broken benches and a table at the start, then knights, a chandelier, a banquet.
	if tier <= 1:
		var kind := "bench_broken" if tier == 0 else "bench"
		for at in [Vector2(104, 112), Vector2(74, 140), Vector2(232, 150)]:
			h.obj(kind, at, Rect2(at.x - 15, at.y - 8, 30, 8))
		h.obj("table_small", Vector2(238, 118), Rect2(226, 108, 24, 10))
	if tier >= 2:
		for at in [Vector2(24, 100), Vector2(296, 100)]:
			h.obj("knight", at, Rect2(at.x - 7, at.y - 6, 14, 6))
	if tier >= 3:
		for at in [Vector2(58, 88), Vector2(262, 88)]:
			h.obj("knight", at, Rect2(at.x - 7, at.y - 6, 14, 6))
		# A banquet table with four chairs on the right.
		var table: Sprite2D = h.obj("table_long", Vector2(252, 128), Rect2(222, 112, 64, 14))
		table.z_index = 0
		for cx in [236.0, 268.0]:
			h.obj("chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 108), Rect2(cx - 6, 102, 12, 6))
		for cx in [236.0, 268.0]:
			h.obj("chair_l" if cx < 252.0 else "chair_r", Vector2(cx, 152), Rect2(cx - 6, 146, 12, 6))
		h.add_light(Vector2(252, 118), 48.0, Color("ffd27a"), 0.7, 0.2)
		h.add_embers(Rect2(40, 90, 240, 80), Color("ffd27a"), 14, 6.0, 4.5)
	if tier >= 2:
		h.anim("chandelier", Vector2(92, 130))
		h.add_light(Vector2(92, 108), 92.0, Color("ffcf8a"), 0.8 + 0.15 * (tier - 2), 0.2)

	# The great door: a plain oak door at first, carved gold at the top.
	h.bg("door_gold" if tier >= 3 else "door_wood", Vector2(160, 186), true)
	h.station("door", "Go to the Forge", Rect2(138, 158, 44, 24), Vector2(160, 134))
