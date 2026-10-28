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
	# A restrained prototype map, showing only doors which exist in this slice.
	draw_rect(Rect2(215, 5, 100, 54), Color(0.06, 0.06, 0.10, .93))
	draw_rect(Rect2(215, 5, 100, 54), Color("b99c6d"), false, 1.0)
	label("CASTLE", Vector2(222, 14), 6, Color("e6d09d"))
	draw_line(Vector2(240, 25), Vector2(240, 34), Color("bca77f"), 2)
	draw_line(Vector2(253, 40), Vector2(270, 40), Color("bca77f"), 2)
	map_room(Rect2(228, 17, 24, 11), "GAL", room == "gallery")
	map_room(Rect2(228, 34, 24, 11), "LIB", room == "library")
	map_room(Rect2(270, 34, 28, 11), "HALL", room == "hall")
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

func map_room(r: Rect2, s: String, active: bool) -> void:
	draw_rect(r, Color("805d35") if active else Color("39474b"))
	draw_rect(r, Color("f5d28e") if active else Color("9aaba5"), false, 1.0)
	label(s, r.position + Vector2(3, 8), 6, Color("fff1cf"))
