extends Node2D
## DiddyDungeon Home: a castle of small rooms you walk through. This scene only draws and walks.
## The app owns every rule: it sends the save's state in (window.diddyHomeReceive)
## and gets "use this station" events back (window.parent.postMessage).
## Rooms are built in code by rooms.gd from the tileset (art/tiles.png), lit with
## pixel-banded 2D lights, one screen each (320x180). See docs/HOME_AND_ART.md.

const T := 16
const COLS := 20
const ROWS := 12
const VIEW := Vector2(320, 180)
const SPEED := 62.0
const FEET := Vector2(8, 4)
const FRAME := Vector2i(48, 46)   # one hunter frame (tools/home_art/from_sheets.py), feet on the bottom row

const TILES: Texture2D = preload("res://art/tiles.png")
var FONT_FILE: FontFile = preload("res://art/PressStart2P.woff2")
const CRT_SHADER: Shader = preload("res://shaders/crt.gdshader")

# The hunter: one sheet per facing, 8 walk frames then 4 idle frames. Right is the side sheet flipped.
const SHEET_FRONT: Texture2D = preload("res://art/hunter_front.png")
const SHEET_SIDE: Texture2D = preload("res://art/hunter_side.png")
const SHEET_BACK: Texture2D = preload("res://art/hunter_back.png")
const WALK_FRAMES := 8
const WALK_FPS := 10.0
const IDLE_FRAMES := 4
const IDLE_FPS := 1.6

# Which save tier drives which room (the app only sends the ones it has).
const ROOM_TIER_KEY := {
	"great_hall": "hearth", "library": "study", "armory": "armory", "pantry": "pantry",
	"gallery": "trophy", "war_room": "map", "den": "perch",
}

# What the app can tell us (all optional; these are the defaults for a standalone run).
var state := {
	"hp": 100, "max_hp": 100, "embers": 0,
	"fire_lit": true, "crt": true, "look": "alucard",
	"tiers": {"hearth": 0, "armory": 0, "map": 0},
	"max_tiers": {"hearth": 3, "armory": 3, "map": 3},
}

var room_id := "great_hall"
var built_tier := -1                    # the tier the current room was built at
var cli_tier := -1                      # testing: force every room to this tier
var blockers: Array[Rect2] = []
var stations: Array[Dictionary] = []
var doors: Array[Dictionary] = []       # {rect, to, spawn}: walk into the rect to change rooms
var background := Node2D.new()
var world := Node2D.new()
var light_layer := Node2D.new()
var pips := Node2D.new()
var ambient := CanvasModulate.new()
var room_nodes: Array[Node] = []        # things in `world` that belong to the room (freed on change)
var animated: Array[Dictionary] = []    # {sprite, base, frames, phase}
var lights: Array[Dictionary] = []      # {node, base, flicker}
var hearth_sprite: Sprite2D
var hearth_base := "fire"
var hunter := Node2D.new()
var body_sprite := Sprite2D.new()
var pyr := Sprite2D.new()
var pyr_light: PointLight2D
var hud := CanvasLayer.new()
var prompt_box := ColorRect.new()
var prompt_label := Label.new()
var toast_label := Label.new()
var fade := ColorRect.new()
var crt_rect := ColorRect.new()
var light_tex: ImageTexture

var pos := Vector2(160, 150)   # the hunter's feet, in float
var facing := "up"
var anim_t := 0.0
var clock := 0.0
var pyr_pos := Vector2(142, 136)
var near: Dictionary = {}
var toast_time := 0.0
var hint_time := 7.0
var changing := false
var flicker_t := 0.0
var lights_on := true
# Keys are tracked from events (not polled) so even a very short tap moves the hunter a few pixels.
var held := {}
var tap_ttl := {}
const MOVE_KEYS := [KEY_W, KEY_A, KEY_S, KEY_D, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT]
# Testing only: `godot --path . -- --shot=/tmp/a.png --room=great_hall --tier=3 --pos=160,150 --face=up` saves a frame and quits.
var shot_path := ""
var shot_frames := 0
var start_pos := Vector2.ZERO


func _ready() -> void:
	FONT_FILE.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	FONT_FILE.hinting = TextServer.HINTING_NONE
	FONT_FILE.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	light_tex = _make_light_texture()
	background.name = "Background"
	world.name = "World"
	world.y_sort_enabled = true
	add_child(ambient)
	add_child(background)
	add_child(world)
	light_layer.name = "Lights"
	add_child(light_layer)
	pips.name = "Pips"
	pips.z_index = 20
	pips.draw.connect(_draw_pips)
	add_child(pips)
	_build_hunter()
	_build_hud()
	_connect_app()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			shot_path = arg.trim_prefix("--shot=")
		elif arg.begins_with("--room="):
			room_id = arg.trim_prefix("--room=")
		elif arg.begins_with("--tier="):
			cli_tier = int(arg.trim_prefix("--tier="))
		elif arg.begins_with("--pos="):
			var xy := arg.trim_prefix("--pos=").split(",")
			start_pos = Vector2(float(xy[0]), float(xy[1]))
		elif arg.begins_with("--face="):
			facing = arg.trim_prefix("--face=")
		elif arg == "--unlit":
			state["fire_lit"] = false
		elif arg == "--nolights":
			lights_on = false
		elif arg == "--tiers":
			state["tiers"] = {"hearth": 2, "armory": 1, "map": 3}
	go_room(room_id, start_pos if start_pos != Vector2.ZERO else Rooms.spawn_default(room_id), true)
	_apply_state()


# ── Rooms ───────────────────────────────────────────────────────────────────
func room_tier(id: String) -> int:
	if cli_tier >= 0:
		return cli_tier
	var key: String = ROOM_TIER_KEY.get(id, id)
	return int((state["tiers"] as Dictionary).get(key, 0))


func go_room(id: String, spawn: Vector2, instant := false) -> void:
	if changing:
		return
	changing = true
	if not instant:
		var out := create_tween()
		out.tween_property(fade, "color:a", 1.0, 0.12)
		await out.finished
	_clear_room()
	room_id = id
	built_tier = room_tier(id)
	Rooms.build(self, id, built_tier)
	pos = spawn
	pyr_pos = spawn + Vector2(-18, -14)
	held.clear()
	tap_ttl.clear()
	anim_t = 0.0
	_refresh_hunter()
	_apply_state()
	if not instant:
		var back := create_tween()
		back.tween_property(fade, "color:a", 0.0, 0.18)
		await back.finished
	changing = false


func _clear_room() -> void:
	for n in room_nodes:
		if is_instance_valid(n):
			n.queue_free()
	room_nodes.clear()
	for c in background.get_children():
		c.queue_free()
	for c in light_layer.get_children():
		c.queue_free()
	blockers.clear()
	stations.clear()
	doors.clear()
	animated.clear()
	lights.clear()
	hearth_sprite = null
	near = {}
	pips.queue_redraw()


# Helpers the room builders (rooms.gd) use.
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


func tile(piece: String, x: int, y: int) -> Sprite2D:
	return _piece(background, piece, Vector2(x * T, y * T))


func bg(piece: String, at: Vector2, from_feet := false) -> Sprite2D:
	return _piece(background, piece, at, from_feet)


func obj(piece: String, feet: Vector2, block: Rect2 = Rect2()) -> Sprite2D:
	var s := _piece(world, piece, feet, true)
	room_nodes.append(s)
	if block.size != Vector2.ZERO:
		blockers.append(block)
	return s


func anim(piece: String, feet: Vector2, block: Rect2 = Rect2(), from_bg := false) -> Sprite2D:
	## An object whose frames are `piece_0`, `piece_1` ...; toggled in _animate_room.
	var s := _piece(background if from_bg else world, piece + "_0", feet, true)
	if not from_bg:
		room_nodes.append(s)
	if block.size != Vector2.ZERO:
		blockers.append(block)
	animated.append({"sprite": s, "base": piece, "frames": 2, "phase": int(feet.x) % 2})
	return s


func block(rect: Rect2) -> void:
	blockers.append(rect)


func station(id: String, label: String, area: Rect2, pip_at: Vector2) -> void:
	stations.append({"id": id, "label": label, "area": area, "pip": pip_at})


func door(rect: Rect2, to: String, spawn: Vector2) -> void:
	doors.append({"rect": rect, "to": to, "spawn": spawn})


func set_ambient(c: Color) -> void:
	ambient.color = c if lights_on else Color.WHITE


func add_light(at: Vector2, radius: float, color: Color, energy := 1.0, flicker := 0.0) -> PointLight2D:
	var l := PointLight2D.new()
	l.texture = light_tex
	l.texture_scale = radius / 32.0
	l.color = color
	l.energy = energy
	l.position = at.round()
	l.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	l.enabled = lights_on
	light_layer.add_child(l)
	lights.append({"node": l, "base": energy, "flicker": flicker})
	return l


func add_embers(rect: Rect2, color: Color, amount := 10, rise := 14.0, life := 2.2) -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.position = rect.get_center()
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = rect.size / 2.0
	p.amount = amount
	p.lifetime = life
	p.direction = Vector2(0, -1)
	p.spread = 22.0
	p.gravity = Vector2.ZERO
	p.initial_velocity_min = rise * 0.5
	p.initial_velocity_max = rise
	p.scale_amount_min = 1.0
	p.scale_amount_max = 1.0
	p.color = color
	var ramp := Gradient.new()
	ramp.set_color(0, Color(color, 1.0))
	ramp.set_color(1, Color(color, 0.0))
	p.color_ramp = ramp
	p.z_index = 6
	world.add_child(p)
	room_nodes.append(p)
	return p


func add_shaft(top_left: Vector2, width: float, height: float, slant: float, color: Color) -> Polygon2D:
	## A slanted additive beam of light (window moonbeams), brightest at the top.
	var poly := Polygon2D.new()
	poly.polygon = PackedVector2Array([
		top_left, top_left + Vector2(width, 0),
		top_left + Vector2(width + slant, height), top_left + Vector2(slant, height)])
	poly.vertex_colors = PackedColorArray([color, color, Color(color, 0.0), Color(color, 0.0)])
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	mat.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
	poly.material = mat
	poly.z_index = 4
	world.add_child(poly)
	room_nodes.append(poly)
	return poly


func _make_light_texture() -> ImageTexture:
	## A radial light in hard bands (4 steps), so it reads as pixel art, not a soft glow.
	var size := 64
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var d := Vector2(x - 31.5, y - 31.5).length() / 32.0
			var lvl := 0.0
			if d < 1.0:
				lvl = ceilf((1.0 - d) * 4.0) / 4.0
			img.set_pixel(x, y, Color(lvl, lvl, lvl, 1.0))
	return ImageTexture.create_from_image(img)


# ── The hunter: one animated sprite ─────────────────────────────────────────
func _build_hunter() -> void:
	hunter.name = "Hunter"
	var shadow := _piece(hunter, "shadow", Vector2(0, 2), true)
	shadow.name = "Shadow"
	body_sprite.name = "Body"
	body_sprite.region_enabled = true
	body_sprite.centered = false
	body_sprite.offset = Vector2(-FRAME.x / 2.0, -FRAME.y + 1)
	hunter.add_child(body_sprite)
	world.add_child(hunter)
	# Pyr, the little code-flame, follows along (and lights the way).
	pyr.texture = TILES
	pyr.region_enabled = true
	pyr.region_rect = TilesData.REGIONS["pyr_0"]
	pyr.centered = false
	pyr.offset = Vector2(-8, -16)
	world.add_child(pyr)
	pyr_light = PointLight2D.new()
	pyr_light.texture = light_tex
	pyr_light.texture_scale = 26.0 / 32.0
	pyr_light.color = Color("ff9a4a")
	pyr_light.energy = 0.55
	pyr_light.position = Vector2(0, -8)
	pyr_light.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	pyr.add_child(pyr_light)
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
	prompt_box.color = Color(0.08, 0.06, 0.12, 0.92)
	prompt_box.position = Vector2(8, 156)
	prompt_box.size = Vector2(304, 18)
	prompt_box.visible = false
	hud.add_child(prompt_box)
	var edge := ColorRect.new()
	edge.color = Color("f5c542")
	edge.position = Vector2(0, 0)
	edge.size = Vector2(304, 1)
	prompt_box.add_child(edge)
	_style(prompt_label)
	prompt_label.position = Vector2(6, 5)
	prompt_box.add_child(prompt_label)
	_style(toast_label, 8, Color("ffd166"))
	toast_label.position = Vector2(4, 3)
	hud.add_child(toast_label)
	var fade_layer := CanvasLayer.new()
	fade_layer.layer = 50
	add_child(fade_layer)
	fade.color = Color(0, 0, 0, 0)
	fade.size = VIEW
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade_layer.add_child(fade)
	var crt_layer := CanvasLayer.new()
	crt_layer.layer = 100
	add_child(crt_layer)
	crt_rect.size = VIEW
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
	crt_rect.visible = bool(state["crt"])
	pips.queue_redraw()
	if not changing and built_tier >= 0 and room_tier(room_id) != built_tier:
		go_room(room_id, pos, true)     # an upgrade was bought: rebuild this room at its new tier


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
	for key in tap_ttl.keys():
		tap_ttl[key] = maxf(0.0, float(tap_ttl[key]) - delta)
	if not changing:
		var dir := Vector2(
			float(_down(KEY_D) or _down(KEY_RIGHT)) - float(_down(KEY_A) or _down(KEY_LEFT)),
			float(_down(KEY_S) or _down(KEY_DOWN)) - float(_down(KEY_W) or _down(KEY_UP)))
		if dir != Vector2.ZERO:
			dir = dir.normalized()
			if absf(dir.x) > absf(dir.y):
				facing = "right" if dir.x > 0 else "left"
			else:
				facing = "down" if dir.y > 0 else "up"
			anim_t += delta * WALK_FPS
			_move(dir * SPEED * delta)
		else:
			anim_t = 0.0
		_check_doors()
	_refresh_hunter()
	_follow_pyr(delta)
	_animate_room(delta)
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


func _check_doors() -> void:
	var feet := Rect2(pos.x - 2, pos.y - 2, 4, 2)
	for d in doors:
		if (d["rect"] as Rect2).intersects(feet):
			go_room(str(d["to"]), d["spawn"])
			return


func _refresh_hunter() -> void:
	hunter.position = pos.round()
	match facing:
		"up":
			body_sprite.texture = SHEET_BACK
		"down":
			body_sprite.texture = SHEET_FRONT
		_:
			body_sprite.texture = SHEET_SIDE
	body_sprite.flip_h = facing == "right"
	var col: int
	if anim_t > 0.0:
		col = int(anim_t) % WALK_FRAMES
	else:
		col = WALK_FRAMES + int(clock * IDLE_FPS) % IDLE_FRAMES   # breathing, after the walk frames
	body_sprite.region_rect = Rect2(col * FRAME.x, 0, FRAME.x, FRAME.y)


func _follow_pyr(delta: float) -> void:
	var behind := {"down": Vector2(-18, -14), "up": Vector2(18, -10), "left": Vector2(16, -14), "right": Vector2(-16, -14)}[facing] as Vector2
	var target := pos + behind
	pyr_pos = pyr_pos.lerp(target, 1.0 - exp(-5.0 * delta))
	var bob := sin(clock * 3.0) * 1.5
	pyr.position = (pyr_pos + Vector2(0, bob)).round()
	var flame := "pyr_%d" % (int(clock * 3.0) % 2)
	pyr.region_rect = TilesData.REGIONS[flame]


func _animate_room(delta: float) -> void:
	var beat := int(clock * 4.0) % 2
	for a in animated:
		_set_piece(a["sprite"], "%s_%d" % [a["base"], (beat + int(a["phase"])) % int(a["frames"])])
	if hearth_sprite != null:
		_set_piece(hearth_sprite, ("%s_%d" % [hearth_base, beat]) if bool(state["fire_lit"]) else (hearth_base + "_out"))
	flicker_t += delta
	if flicker_t >= 0.09:
		flicker_t = 0.0
		for l in lights:
			var f := float(l["flicker"])
			if f > 0.0:
				(l["node"] as PointLight2D).energy = float(l["base"]) * (1.0 + f * (randf() * 2.0 - 1.0))
	pyr_light.energy = 0.5 + 0.12 * sin(clock * 9.0)


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


func _down(key: int) -> bool:
	return bool(held.get(key, false)) or float(tap_ttl.get(key, 0.0)) > 0.0


func _input(event: InputEvent) -> void:
	if event is InputEventKey and not event.echo:
		var key: int = event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode
		if key in MOVE_KEYS:
			held[key] = event.pressed
			if event.pressed:
				tap_ttl[key] = 0.09


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_E, KEY_SPACE, KEY_ENTER, KEY_Z]:
		if not near.is_empty() and not changing:
			use_station(str(near["id"]))


func use_station(id: String) -> void:
	_send_app({"type": "use", "station": id})
	if not OS.has_feature("web"):
		toast_label.text = "(standalone) used " + id
		toast_time = 2.0


func toast(text: String) -> void:
	toast_label.text = text.to_upper()
	toast_time = 3.0
