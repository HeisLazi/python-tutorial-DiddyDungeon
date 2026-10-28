extends Node2D

const Atlas = preload("res://art/tiles_data.gd")
const TILES = preload("res://art/tiles.png")
const FRONT = preload("res://art/hunter_front.png")
const SIDE = preload("res://art/hunter_side.png")
const BACK = preload("res://art/hunter_back.png")
const PYR = preload("res://art/pyr_stage_1.png")
const UNARMED = preload("res://art/home_unarmed.gdshader")

var room := "hall"
var pos := Vector2(160, 135)
var direction := "up"
var time := 0.0
var walking := false
var prompt := ""
var blocks: Array[Rect2] = []
var font: Font
var body := Sprite2D.new()
var pyr_pos := Vector2(145, 130)

func _ready() -> void:
	font = ThemeDB.fallback_font
	body.region_enabled = true
	body.centered = false
	body.offset = Vector2(-24, -46)
	body.scale = Vector2(0.58, 0.58)
	var material := ShaderMaterial.new()
	material.shader = UNARMED
	body.material = material
	add_child(body)
	_layout()

func _layout() -> void:
	pyr_pos = pos + Vector2(-17, -8)
	blocks.clear()
	# The door strips remain unobstructed; collision boxes are at furniture feet.
	if room == "hall":
		blocks.append_array([Rect2(133, 48, 54, 15), Rect2(68, 84, 32, 8), Rect2(220, 84, 32, 8)])
	elif room == "library":
		blocks.append_array([Rect2(55, 42, 32, 12), Rect2(233, 42, 32, 12), Rect2(92, 93, 36, 9), Rect2(210, 93, 28, 9)])
	else:
		blocks.append_array([Rect2(69, 63, 24, 10), Rect2(148, 63, 24, 10), Rect2(227, 63, 24, 10)])

func _process(delta: float) -> void:
	time += delta
	var d := Vector2(Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left"), Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up"))
	# WASD as well as arrow keys, without relying on project input mappings.
	d += Vector2(float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)), float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W)))
	walking = d.length() > 0.0
	if walking:
		d = d.normalized()
		direction = ("right" if d.x > 0 else "left") if absf(d.x) > absf(d.y) else ("down" if d.y > 0 else "up")
		move_axis(Vector2(d.x * 74.0 * delta, 0))
		move_axis(Vector2(0, d.y * 74.0 * delta))
		check_doors()
	pyr_pos = pyr_pos.lerp(pos + Vector2(-17, -8), minf(1.0, delta * 3.0))
	body.position = pos
	body.texture = BACK if direction == "up" else (FRONT if direction == "down" else SIDE)
	body.flip_h = direction == "right"
	var frame := int(time * 9.0) % 8 if walking else 8 + int(time * 1.6) % 4
	body.region_rect = Rect2(frame * 48, 0, 48, 46)
	(body.material as ShaderMaterial).set_shader_parameter("facing", 2 if direction == "up" else (0 if direction == "down" else 1))
	queue_redraw()

func move_axis(step: Vector2) -> void:
	var next := pos + step
	var feet := Rect2(next.x - 3, next.y - 4, 6, 4)
	if next.x < 4 or next.x > 316 or next.y < 22 or next.y > 174:
		return
	for b in blocks:
		if feet.intersects(b):
			return
	pos = next

func check_doors() -> void:
	if room == "hall" and pos.x < 10 and pos.y > 85 and pos.y < 145:
		room = "library"
		pos = Vector2(302, 116)
		_layout()
	elif room == "library" and pos.x > 310 and pos.y > 85 and pos.y < 145:
		room = "hall"
		pos = Vector2(18, 116)
		_layout()
	elif room == "library" and pos.y < 27 and pos.x > 137 and pos.x < 183:
		room = "gallery"
		pos = Vector2(160, 164)
		_layout()
	elif room == "gallery" and pos.y > 168 and pos.x > 137 and pos.x < 183:
		room = "library"
		pos = Vector2(160, 34)
		_layout()

func tile(name: String, at: Vector2, size := Vector2.ZERO) -> void:
	var region: Rect2 = Atlas.REGIONS[name]
	draw_texture_rect_region(TILES, Rect2(at, region.size if size == Vector2.ZERO else size), region)

func _draw() -> void:
	# A more overhead room: narrow wall bands and a broad, walkable floor.
	for y in range(12):
		for x in range(20):
			var name := "floor_flag_%d" % ((x * 7 + y * 3) % 3)
			if room == "library": name = "floor_wood_%d" % ((x * 5 + y * 3) % 3)
			tile(name, Vector2(x * 16, y * 16))
	draw_rect(Rect2(0, 0, 320, 20), Color("242039"))
	draw_rect(Rect2(0, 19, 320, 5), Color("6a6175"))
	draw_rect(Rect2(0, 24, 320, 3), Color(0, 0, 0, .32))
	# Side doorway markings are inset into the room boundary.
	if room == "hall":
		side_door(true)
		tile("hearthm_0" if int(time * 2) % 2 == 0 else "hearthm_1", Vector2(138, 23), Vector2(44, 40))
		tile("bench", Vector2(68, 64), Vector2(32, 28))
		tile("bench", Vector2(220, 64), Vector2(32, 28))
		tile("carpet", Vector2(144, 97), Vector2(32, 60))
		label("HEARTH", Vector2(142, 77), 6, Color("f5d39c"))
	elif room == "library":
		side_door(false)
		vertical_door(true)
		tile("bookshelf_full", Vector2(52, 19), Vector2(38, 35))
		tile("bookshelf_full", Vector2(230, 19), Vector2(38, 35))
		tile("desk_big", Vector2(87, 70), Vector2(45, 32))
		tile("globe", Vector2(214, 76), Vector2(22, 26))
		label("STUDY", Vector2(100, 112), 6, Color("f5d39c"))
	else:
		vertical_door(false)
		tile("plinth_plain", Vector2(65, 38), Vector2(32, 35))
		tile("plinth_plain", Vector2(144, 38), Vector2(32, 35))
		tile("plinth_plain", Vector2(223, 38), Vector2(32, 35))
		label("TROPHIES", Vector2(142, 85), 6, Color("f5d39c"))
	# Shadow and a temporarily scaled existing animated hunter, anchored at feet.
	draw_ellipse(pos + Vector2(0, 1), 7.0, 3.0, Color(0, 0, 0, .45))
	var pyr_frame := int(time * 2.0) % 2
	draw_texture_rect_region(PYR, Rect2(pyr_pos.x - 9, pyr_pos.y - 18, 18, 18), Rect2(pyr_frame * 32, 0, 32, 32))
	# Miniature floor plan: only the three walkable rooms are shown here.
	draw_castle_map()
	label("prototype · arrows / WASD", Vector2(9, 174), 7, Color("ece3ca"))
	label(("GREAT HALL" if room == "hall" else "LIBRARY" if room == "library" else "GALLERY"), Vector2(9, 13), 8, Color("ece3ca"))

func side_door(left: bool) -> void:
	var x := 0.0 if left else 312.0
	draw_rect(Rect2(x, 87, 8, 55), Color("120e1a"))
	draw_rect(Rect2(x, 85, 8, 3), Color("b29a71"))
	draw_rect(Rect2(x, 142, 8, 3), Color("b29a71"))

func vertical_door(north: bool) -> void:
	var y := 19.0 if north else 168.0
	draw_rect(Rect2(137, y, 46, 10), Color("15121d"))
	draw_rect(Rect2(135, y, 2, 10), Color("ae9a78"))
	draw_rect(Rect2(183, y, 2, 10), Color("ae9a78"))

func label(s: String, at: Vector2, size: int, color: Color) -> void:
	draw_string(font, at, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)

func draw_castle_map() -> void:
	# Keep the floor plan compact in the upper-right corner.
	draw_set_transform(Vector2(75, 0), 0.0, Vector2(0.76, 0.76))
	# Dark frame and inset stone trim evoke an in-world map rather than a menu.
	draw_rect(Rect2(205, 4, 111, 78), Color(0.04, 0.04, 0.07, .94))
	draw_rect(Rect2(205, 4, 111, 78), Color("8e795a"), false, 1.0)
	draw_rect(Rect2(207, 6, 107, 74), Color("423a3a"), false, 1.0)
	label("CASTLE", Vector2(211, 14), 6, Color("e6d09d"))
	label("GALLERY" if room == "gallery" else "LIBRARY" if room == "library" else "GREAT HALL", Vector2(252, 14), 6, Color("e6d09d"))

	var gallery := Rect2(218, 19, 34, 21)
	var library := Rect2(218, 48, 34, 23)
	var hall := Rect2(268, 48, 38, 23)
	# Corridors are drawn before walls; thresholds below cut through the walls.
	draw_rect(Rect2(232, 39, 6, 10), Color("8e806a"))
	draw_rect(Rect2(251, 56, 18, 6), Color("8e806a"))
	map_chamber(gallery, Color("353e4b"))
	map_chamber(library, Color("624734"))
	map_chamber(hall, Color("3d444f"))
	# Visible door gaps match the real exits.
	draw_rect(Rect2(232, 38, 6, 3), Color("cbb69a"))
	draw_rect(Rect2(232, 47, 6, 3), Color("cbb69a"))
	draw_rect(Rect2(250, 56, 3, 6), Color("cbb69a"))
	draw_rect(Rect2(267, 56, 3, 6), Color("cbb69a"))

	# Tiny furniture gives each room an immediately recognizable purpose.
	for x in [224, 235, 246]:
		draw_rect(Rect2(x, 24, 3, 3), Color("bfc5c5"))
		draw_rect(Rect2(x - 1, 27, 5, 2), Color("777c85"))
	draw_rect(Rect2(221, 51, 7, 3), Color("b69a6d"))
	draw_rect(Rect2(242, 51, 7, 3), Color("b69a6d"))
	draw_rect(Rect2(226, 59, 8, 4), Color("b78658"))
	draw_rect(Rect2(243, 59, 3, 3), Color("6bb2ba"))
	draw_rect(Rect2(282, 50, 10, 4), Color("ac8d6b"))
	draw_rect(Rect2(285, 52, 4, 2), Color("f7a54c"))
	draw_rect(Rect2(284, 57, 6, 11), Color("9a3540"))
	draw_rect(Rect2(273, 57, 6, 3), Color("aa8660"))
	draw_rect(Rect2(295, 57, 6, 3), Color("aa8660"))

	# The marker moves within the current room, so it is a map of your position.
	var active := hall if room == "hall" else library if room == "library" else gallery
	var marker := Vector2(active.position.x + 4.0 + clampf(pos.x / 320.0, 0.0, 1.0) * (active.size.x - 8.0), active.position.y + 4.0 + clampf((pos.y - 20.0) / 155.0, 0.0, 1.0) * (active.size.y - 8.0))
	draw_circle(marker, 3.0, Color("33200e"))
	draw_circle(marker, 2.0, Color("ffe287"))
	draw_circle(marker + Vector2(-0.5, -0.5), 0.7, Color("fffbe6"))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func map_chamber(r: Rect2, floor_color: Color) -> void:
	draw_rect(r.grow(2), Color("1b1923"))
	draw_rect(r, Color("a19784"))
	draw_rect(r.grow(-2), floor_color)
	# Sparse seams suggest a miniature room surface without filling it with noise.
	for y in range(int(r.position.y + 5), int(r.end.y - 2), 5):
		draw_line(Vector2(r.position.x + 2, y), Vector2(r.end.x - 2, y), Color(1, 1, 1, .06))
