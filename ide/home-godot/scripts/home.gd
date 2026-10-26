extends Node2D
## DiddyDungeon Home: the walkable base. This scene only draws and walks.
## The app owns every rule: it sends the save's state in (window.diddyHomeReceive)
## and gets "use this station" events back (window.parent.postMessage).

const T := 16
const COLS := 20
const ROWS := 13
const WORLD := Vector2(COLS * T, ROWS * T)
const SPEED := 62.0
const FEET := Vector2(8, 4)

const TILES: Texture2D = preload("res://art/tiles.png")
const HUNTER: Texture2D = preload("res://art/hunter.png")
var FONT_FILE: FontFile = preload("res://art/PressStart2P.woff2")
const CRT_SHADER: Shader = preload("res://shaders/crt.gdshader")

const FACING_ROW := {"down": 0, "left": 1, "right": 2, "up": 3}
const WALK_CYCLE := [0, 1, 0, 2]

# What the app can tell us (all optional; these are the defaults for a standalone run).
var state := {
	"hp": 100, "max_hp": 100, "embers": 0,
	"fire_lit": true, "crt": true,
	"tiers": {"hearth": 0, "armory": 0, "map": 0},
	"max_tiers": {"hearth": 3, "armory": 3, "map": 3},
}

var blockers: Array[Rect2] = []
var stations: Array[Dictionary] = []
var background := Node2D.new()
var world := Node2D.new()
var pips := Node2D.new()
var hunter := Node2D.new()
var hunter_sprite := Sprite2D.new()
var pyr := Sprite2D.new()
var hearth_sprite: Sprite2D
var torches: Array[Sprite2D] = []
var candle: Sprite2D
var camera := Camera2D.new()
var hud := CanvasLayer.new()
var hp_label := Label.new()
var prompt_box := ColorRect.new()
var prompt_label := Label.new()
var toast_label := Label.new()
var crt_rect := ColorRect.new()

var pos := Vector2(160, 132)   # the hunter's feet, in float
var facing := "down"
var anim_t := 0.0
var clock := 0.0
var pyr_pos := Vector2(146, 128)
var near: Dictionary = {}
var toast_time := 0.0
var hint_time := 7.0
# Testing only: `godot --path . -- --shot=/tmp/a.png --pos=160,90 --face=up` saves a frame and quits.
var shot_path := ""
var shot_frames := 0


func _ready() -> void:
	FONT_FILE.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	FONT_FILE.hinting = TextServer.HINTING_NONE
	FONT_FILE.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	background.name = "Background"
	world.name = "World"
	world.y_sort_enabled = true
	add_child(background)
	add_child(world)
	pips.name = "Pips"
	pips.z_index = 20
	pips.draw.connect(_draw_pips)
	add_child(pips)
	_build_room()
	_build_hunter()
	_build_hud()
	camera.position_smoothing_enabled = false
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = int(WORLD.x)
	camera.limit_bottom = int(WORLD.y)
	hunter.add_child(camera)
	camera.position = Vector2(0, -16)
	camera.make_current()
	_connect_app()
	_apply_state()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			shot_path = arg.trim_prefix("--shot=")
		elif arg.begins_with("--pos="):
			var xy := arg.trim_prefix("--pos=").split(",")
			pos = Vector2(float(xy[0]), float(xy[1]))
		elif arg.begins_with("--face="):
			facing = arg.trim_prefix("--face=")
		elif arg == "--unlit":
			state["fire_lit"] = false
		elif arg == "--tiers":
			state["tiers"] = {"hearth": 2, "armory": 1, "map": 3}
			_apply_state()


# ── The room ────────────────────────────────────────────────────────────────
func _piece(parent: Node, piece: String, at: Vector2, from_feet := false) -> Sprite2D:
	var r: Rect2 = TilesData.REGIONS[piece]
	var s := Sprite2D.new()
	s.texture = TILES
	s.region_enabled = true
	s.region_rect = r
	s.centered = false
	if from_feet:
		s.offset = Vector2(-r.size.x / 2.0, -r.size.y)   # `at` is the bottom-centre
		s.position = at
	else:
		s.position = at                                    # `at` is the top-left
	parent.add_child(s)
	return s


func _set_piece(s: Sprite2D, piece: String) -> void:
	s.region_rect = TilesData.REGIONS[piece]


func _block(rect: Rect2) -> void:
	blockers.append(rect)


func _station(id: String, label: String, area: Rect2, pip_at: Vector2) -> void:
	stations.append({"id": id, "label": label, "area": area, "pip": pip_at})


func _build_room() -> void:
	for y in ROWS:
		for x in COLS:
			var piece := "floor_%d" % ((x + y) % 2)
			if y == 0 or y == ROWS - 1:
				piece = "wall_top"
			elif y == 1 or y == 2:
				piece = "wall_face_%d" % (x % 2)
			elif y == 3:
				piece = "skirting"
			_piece(background, piece, Vector2(x * T, y * T))
	_piece(background, "rug_big", Vector2(120, 100))
	for wx in [3, 16]:
		_piece(background, "window", Vector2(wx * T, T))
	for tx in [7, 12]:
		torches.append(_piece(background, "torch_0", Vector2(tx * T, T + 2)))
	# Wall pieces: the bookshelves, the Hearth and the Armory rack.
	_piece(background, "bookshelf", Vector2(24, 48), true)
	_piece(background, "bookshelf", Vector2(296, 48), true)
	hearth_sprite = _piece(background, "fire_0", Vector2(160, 54), true)
	_piece(background, "armory", Vector2(64, 52), true)
	_piece(background, "door", Vector2(152, 200), true)
	# The world's walls and edges.
	_block(Rect2(0, 0, WORLD.x, 64))
	_block(Rect2(0, 192, WORLD.x, 16))
	_block(Rect2(-16, 0, 24, WORLD.y))
	_block(Rect2(WORLD.x - 8, 0, 24, WORLD.y))
	# Things you can walk around: the Map table, barrels, crates and plants.
	_piece(world, "shadow", Vector2(240, 114), true).z_index = -1
	var table := _piece(world, "candle_0", Vector2(240, 112), true)
	candle = table
	_block(Rect2(224, 98, 32, 14))
	for item in [["barrel", Vector2(302, 84)], ["barrel", Vector2(302, 100)], ["crate", Vector2(284, 86)], ["plant", Vector2(14, 82)], ["plant", Vector2(306, 182)], ["plant", Vector2(14, 182)]]:
		_piece(world, item[0], item[1], true)
		_block(Rect2(item[1].x - 6, item[1].y - 6, 12, 6))
	# The stations you use. Each area is where the hunter stands to use it.
	_station("hearth", "Rest at the Hearth", Rect2(140, 62, 40, 24), Vector2(160, 14))
	_station("armory", "Open the Armory", Rect2(44, 62, 40, 24), Vector2(64, 18))
	_station("map", "Plan a Dungeon run", Rect2(214, 112, 52, 24), Vector2(240, 80))
	_station("door", "Go to the Forge", Rect2(134, 168, 36, 24), Vector2(152, 172))


func _build_hunter() -> void:
	hunter.name = "Hunter"
	var shadow := _piece(hunter, "shadow", Vector2(0, 2), true)
	shadow.z_index = -1
	hunter_sprite.texture = HUNTER
	hunter_sprite.region_enabled = true
	hunter_sprite.centered = false
	hunter_sprite.offset = Vector2(-8, -30)
	hunter.add_child(hunter_sprite)
	world.add_child(hunter)
	# Pyr, the little code-flame, follows along.
	pyr.texture = TILES
	pyr.region_enabled = true
	pyr.region_rect = TilesData.REGIONS["pyr_0"]
	pyr.centered = false
	pyr.offset = Vector2(-8, -16)
	world.add_child(pyr)
	_refresh_hunter()


# ── The HUD (drawn above the room, under the CRT) ───────────────────────────
func _style(label: Label, size := 8, color := Color("f2efe6")) -> void:
	label.add_theme_font_override("font", FONT_FILE)
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color("14101f"))
	label.add_theme_constant_override("outline_size", 2)


func _build_hud() -> void:
	hud.layer = 10
	add_child(hud)
	_style(hp_label, 8, Color("f5c542"))
	hp_label.position = Vector2(4, 3)
	hud.add_child(hp_label)
	prompt_box.color = Color(0.08, 0.06, 0.12, 0.92)
	prompt_box.position = Vector2(8, 138)
	prompt_box.size = Vector2(224, 18)
	prompt_box.visible = false
	hud.add_child(prompt_box)
	var edge := ColorRect.new()
	edge.color = Color("f5c542")
	edge.position = Vector2(0, 0)
	edge.size = Vector2(224, 1)
	prompt_box.add_child(edge)
	_style(prompt_label)
	prompt_label.position = Vector2(6, 5)
	prompt_box.add_child(prompt_label)
	_style(toast_label, 8, Color("ffd166"))
	toast_label.position = Vector2(4, 14)
	hud.add_child(toast_label)
	var crt_layer := CanvasLayer.new()
	crt_layer.layer = 100
	add_child(crt_layer)
	crt_rect.size = Vector2(240, 160)
	var mat := ShaderMaterial.new()
	mat.shader = CRT_SHADER
	crt_rect.material = mat
	crt_layer.add_child(crt_rect)


# ── The app bridge (web build only) ─────────────────────────────────────────
var _receive_callback: JavaScriptObject


func _connect_app() -> void:
	if not OS.has_feature("web"):
		return
	_receive_callback = JavaScriptBridge.create_callback(_on_app_state)
	var window := JavaScriptBridge.get_interface("window")
	window.diddyHomeReceive = _receive_callback
	_send_app({"type": "ready"})


func _on_app_state(args: Array) -> void:
	if args.is_empty():
		return
	var parsed: Variant = JSON.parse_string(str(args[0]))
	if parsed is Dictionary:
		state.merge(parsed, true)
		_apply_state()


func _send_app(message: Dictionary) -> void:
	message["source"] = "diddy-home"
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.parent.postMessage(%s, window.location.origin)" % JSON.stringify(message), true)
	else:
		print("home -> app: ", message)


func _apply_state() -> void:
	var said := str(state.get("toast", ""))
	if said != "":
		toast(said)
		state["toast"] = ""
	hp_label.text = "HP %d/%d   EMBERS %d" % [int(state["hp"]), int(state["max_hp"]), int(state["embers"])]
	crt_rect.visible = bool(state["crt"])
	pips.queue_redraw()


func _draw_pips() -> void:
	for st in stations:
		var id: String = st["id"]
		if not state["tiers"].has(id):
			continue
		var count := int(state["max_tiers"].get(id, 3))
		var have := int(state["tiers"][id])
		var origin: Vector2 = st["pip"] - Vector2(count * 4 - 1, 0)
		for i in count:
			var rect := Rect2(origin + Vector2(i * 4, 0), Vector2(3, 3))
			pips.draw_rect(Rect2(rect.position - Vector2.ONE, rect.size + Vector2(2, 2)), Color("14101f"))
			pips.draw_rect(rect, Color("f5c542") if i < have else Color("3a3358"))


# ── Each frame ──────────────────────────────────────────────────────────────
func _process(delta: float) -> void:
	clock += delta
	if shot_path != "":
		shot_frames += 1
		if shot_frames == 20:
			get_viewport().get_texture().get_image().save_png(shot_path)
			get_tree().quit()
	var dir := Vector2(
		float(Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT)) - float(Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT)),
		float(Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN)) - float(Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP)))
	if dir != Vector2.ZERO:
		dir = dir.normalized()
		if absf(dir.x) > absf(dir.y):
			facing = "right" if dir.x > 0 else "left"
		else:
			facing = "down" if dir.y > 0 else "up"
		anim_t += delta * 7.0
		_move(dir * SPEED * delta)
	else:
		anim_t = 0.0
	_refresh_hunter()
	_follow_pyr(delta)
	_animate_room()
	_update_prompt(delta)


func _move(step: Vector2) -> void:
	if not _hits(Vector2(pos.x + step.x, pos.y)):
		pos.x += step.x
	if not _hits(Vector2(pos.x, pos.y + step.y)):
		pos.y += step.y


func _hits(feet: Vector2) -> bool:
	var r := Rect2(feet.x - FEET.x / 2.0, feet.y - FEET.y, FEET.x, FEET.y)
	for b in blockers:
		if b.intersects(r):
			return true
	return false


func _refresh_hunter() -> void:
	hunter.position = pos.round()
	var col: int = WALK_CYCLE[int(anim_t) % 4] if anim_t > 0.0 else 0
	hunter_sprite.region_rect = Rect2(col * 16, FACING_ROW[facing] * 32, 16, 32)


func _follow_pyr(delta: float) -> void:
	var behind := {"down": Vector2(-14, -10), "up": Vector2(14, -6), "left": Vector2(12, -10), "right": Vector2(-12, -10)}[facing] as Vector2
	var target := pos + behind
	pyr_pos = pyr_pos.lerp(target, 1.0 - exp(-5.0 * delta))
	var bob := sin(clock * 3.0) * 1.5
	pyr.position = (pyr_pos + Vector2(0, bob)).round()
	var flame := "pyr_%d" % (int(clock * 3.0) % 2)
	pyr.region_rect = TilesData.REGIONS[flame]


func _animate_room() -> void:
	var beat := int(clock * 4.0) % 2
	for torch in torches:
		_set_piece(torch, "torch_%d" % beat)
	_set_piece(hearth_sprite, ("fire_%d" % beat) if bool(state["fire_lit"]) else "fire_out")
	_set_piece(candle, "candle_%d" % beat)


func _update_prompt(delta: float) -> void:
	var feet := Rect2(pos.x - 4, pos.y - 4, 8, 4)
	near = {}
	for st in stations:
		if (st["area"] as Rect2).intersects(feet):
			near = st
			break
	if near.is_empty() and hint_time > 0.0:
		hint_time -= delta
		prompt_label.text = "WASD / ARROWS WALK     E USE"
		prompt_box.visible = true
	elif not near.is_empty():
		prompt_label.text = "E  " + str(near["label"]).to_upper()
		prompt_box.visible = true
		hint_time = 0.0
	else:
		prompt_box.visible = false
	if toast_time > 0.0:
		toast_time -= delta
		if toast_time <= 0.0:
			toast_label.text = ""


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_E, KEY_SPACE, KEY_ENTER, KEY_Z]:
		if not near.is_empty():
			use_station(str(near["id"]))


func use_station(id: String) -> void:
	_send_app({"type": "use", "station": id})
	if not OS.has_feature("web"):
		toast_label.text = "(standalone) used " + id
		toast_time = 2.0


func toast(text: String) -> void:
	toast_label.text = text.to_upper()
	toast_time = 3.0
