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
const FRAME := Vector2i(38, 38)   # the unarmed 32px Home hunter, feet on the bottom row

const TILES: Texture2D = preload("res://art/tiles.png")
var FONT_FILE: FontFile = preload("res://art/PressStart2P.woff2")
const CRT_SHADER: Shader = preload("res://shaders/crt.gdshader")
const SWAY_SHADER: Shader = preload("res://shaders/sway.gdshader")
const LOOK_SHADER: Shader = preload("res://shaders/hunter_look.gdshader")
const OIL_PET: Texture2D = preload("res://art/oil-pet.png")
const SIR_GETRICH_HOME: Texture2D = preload("res://art/sir-getrich-home.png")
const ONLINE_HOUSE_BACKGROUND: Texture2D = preload("res://art/online/house_background_v2.png")
const ONLINE_LEADERBOARD: Texture2D = preload("res://art/online/leaderboard_stand.png")
const ONLINE_STALL: Texture2D = preload("res://art/online/getrich_stall_v2.png")
const ONLINE_GOLD_HOARD: Texture2D = preload("res://art/online/gold_hoard.png")
const ONLINE_GOTHIC_GATE: Texture2D = preload("res://art/online/gothic_gate.png")
const ONLINE_FERRYMAN: Texture2D = preload("res://art/online/ferryman.png")
const ONLINE_SKIFF: Texture2D = preload("res://art/online/skiff.png")
const ONLINE_FERRY_LANDING: Texture2D = preload("res://art/online/ferryman_landing.png")
const CHARMS := {"pink-cap": preload("res://art/charm-pink-cap.png"), "soul-lantern": preload("res://art/charm-soul-lantern.png"), "jacklight": preload("res://art/charm-jacklight.png"), "generic": preload("res://art/charm-generic.png")}

# The hunter: one sheet per facing, 8 walk frames then 4 idle frames. Right is the side sheet flipped.
const SHEET_FRONT: Texture2D = preload("res://art/hunter_front.png")
const SHEET_SIDE: Texture2D = preload("res://art/hunter_side.png")
const SHEET_BACK: Texture2D = preload("res://art/hunter_back.png")
const OUTFIT_SHEETS := {
	"debugger": {"front": preload("res://art/hunter_debugger_front.png"), "side": preload("res://art/hunter_debugger_side.png"), "back": preload("res://art/hunter_debugger_back.png")},
	"merchant-oracle": {"front": preload("res://art/hunter_merchant_oracle_front.png"), "side": preload("res://art/hunter_merchant_oracle_side.png"), "back": preload("res://art/hunter_merchant_oracle_back.png")},
	"ivory": {"front": preload("res://art/hunter_ivory_front.png"), "side": preload("res://art/hunter_ivory_side.png"), "back": preload("res://art/hunter_ivory_back.png")},
	"spectral": {"front": preload("res://art/hunter_warden_heavy_front.png"), "side": preload("res://art/hunter_warden_heavy_side.png"), "back": preload("res://art/hunter_warden_heavy_back.png")},
	"harvest": {"front": preload("res://art/hunter_harvest_scout_front.png"), "side": preload("res://art/hunter_harvest_scout_side.png"), "back": preload("res://art/hunter_harvest_scout_back.png")},
	"oracle": {"front": preload("res://art/hunter_arcane_front.png"), "side": preload("res://art/hunter_arcane_side.png"), "back": preload("res://art/hunter_arcane_back.png")},
	"patchwork": {"front": preload("res://art/hunter_patchwork_front.png"), "side": preload("res://art/hunter_patchwork_side.png"), "back": preload("res://art/hunter_patchwork_back.png")},
	"pilgrim": {"front": preload("res://art/hunter_pilgrim_front.png"), "side": preload("res://art/hunter_pilgrim_side.png"), "back": preload("res://art/hunter_pilgrim_back.png")},
	"wayfarer": {"front": preload("res://art/hunter_wayfarer_front.png"), "side": preload("res://art/hunter_wayfarer_side.png"), "back": preload("res://art/hunter_wayfarer_back.png")},
	"norse": {"front": preload("res://art/hunter_norse_front.png"), "side": preload("res://art/hunter_norse_side.png"), "back": preload("res://art/hunter_norse_back.png")},
	"lanternkeeper": {"front": preload("res://art/hunter_lanternkeeper_front.png"), "side": preload("res://art/hunter_lanternkeeper_side.png"), "back": preload("res://art/hunter_lanternkeeper_back.png")},
	"wardplate": {"front": preload("res://art/hunter_wardplate_front.png"), "side": preload("res://art/hunter_wardplate_side.png"), "back": preload("res://art/hunter_wardplate_back.png")},
}
const WALK_FRAMES := 8
const WALK_FPS := 10.0
const IDLE_FRAMES := 4
const IDLE_FPS := 1.6
const PYR_CELL := 32
const PYR_FRAMES := 6  # idle x2, following x2, perch, feed

# Which save tier drives which room (the app only sends the ones it has).
const ROOM_TIER_KEY := {
	"great_hall": "hearth", "library": "study", "armory": "armory", "pantry": "pantry",
	"gallery": "trophy", "war_room": "map", "den": "perch",
}

# What the app can tell us (all optional; these are the defaults for a standalone run).
var state := {
	"hp": 100, "max_hp": 100, "embers": 0,
	"fire_lit": true, "crt": true, "look": "alucard", "pyr_stage": 1,
	"tiers": {"hearth": 0, "armory": 0, "map": 0},
	"max_tiers": {"hearth": 3, "armory": 3, "map": 3},
}

var room_id := "great_hall"
var built_level := -1                   # the level the current room was built at
var cli_level := -1                     # testing: force every room to this level
var flash := ColorRect.new()            # a quick glow when something is built
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
var sheet_animated: Array[Dictionary] = [] # {sprite, frames, fps, phase}
var bobbing: Array[Dictionary] = []     # {sprite, base_y, amplitude, speed, phase}
var lights: Array[Dictionary] = []      # {node, base, flicker}
var hearth_sprite: Sprite2D
var hearth_base := "fire"
var hunter := Node2D.new()
var visitors := {}
var body_sprite := Sprite2D.new()
var oil_pet := Sprite2D.new()
var trinket_gem := Sprite2D.new()
var pyr := Sprite2D.new()
var pyr_light: PointLight2D
var pyr_sheet_stage := -1
var pyr_custom_sheet := false
var pyr_pose := 0
var pyr_pose_time := 0.0
var hud := CanvasLayer.new()
var prompt_box := ColorRect.new()
var prompt_label := Label.new()
var toast_label := Label.new()
var online_minimap := Node2D.new()
var fade := ColorRect.new()
var crt_rect := ColorRect.new()
var light_tex: ImageTexture

var pos := Vector2(160, 150)   # the hunter's feet, in float
var facing := "up"
var anim_t := 0.0
var clock := 0.0
var map_update_time := 0.0
var map_last_pos := Vector2.INF
var pyr_pos := Vector2(142, 136)
var pyr_target := Vector2(142, 136)
var pyr_wander_wait := 1.0
var pyr_facing_left := false
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
# Testing only: `godot --path . -- --shot=/tmp/a.png --room=great_hall --level=12 --pos=160,150 --face=up` saves a frame and quits.
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
	if OS.has_feature("web") and bool(JavaScriptBridge.eval("new URLSearchParams(window.location.search).get('online') === '1'", true)):
		room_id = "online_hideout"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			shot_path = arg.trim_prefix("--shot=")
		elif arg.begins_with("--room="):
			room_id = arg.trim_prefix("--room=")
		elif arg.begins_with("--level="):
			cli_level = int(arg.trim_prefix("--level="))
		elif arg.begins_with("--tier="):
			cli_level = Rooms.tier_to_level(room_id, int(arg.trim_prefix("--tier=")))     # the old four tiers
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
func room_level(id: String) -> int:
	## Upgrade level of a room, 0 .. Rooms.max_level(id). The app can send `levels: {room: n}`; the older
	## `tiers` (0..3 per station) still work, spread over the room's levels.
	if cli_level >= 0:
		return mini(cli_level, Rooms.max_level(id))
	var levels: Dictionary = state.get("levels", {})
	if levels.has(id):
		return mini(int(levels[id]), Rooms.max_level(id))
	var key: String = ROOM_TIER_KEY.get(id, id)
	return mini(Rooms.tier_to_level(id, int((state["tiers"] as Dictionary).get(key, 0))), Rooms.max_level(id))


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
	online_minimap.visible = id.begins_with("online_")
	online_minimap.queue_redraw()
	pyr.visible = id == "den"
	pyr_light.enabled = id == "den"
	built_level = room_level(id)
	Rooms.build(self, id, built_level)
	pos = spawn
	pyr_pos = spawn + Vector2(-18, -14)
	for candidate in [Vector2(235, 148), Vector2(75, 148), Vector2(160, 110)]:
		if not _hits(candidate) and candidate.distance_to(spawn) > 40.0:
			pyr_pos = candidate
			break
	pyr_target = pyr_pos
	pyr_wander_wait = 0.7
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
	_send_app({"type": "room", "room": room_id, "x": pos.x, "y": pos.y})


func _celebrate(what: String) -> void:
	## A quick warm flash and a toast when something new is built.
	toast("BUILT: " + what)
	flash.color = Color(1.0, 0.85, 0.5, 0.45)
	var tw := create_tween()
	tw.tween_property(flash, "color:a", 0.0, 0.5)


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
	sheet_animated.clear()
	bobbing.clear()
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


func asset_back(texture: Texture2D, feet: Vector2, scale_factor := Vector2.ONE) -> Sprite2D:
	## Place an imported transparent prop behind actors. `feet` is its bottom centre.
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sprite.offset = Vector2(-texture.get_width() / 2.0, -texture.get_height())
	sprite.position = feet
	sprite.scale = scale_factor
	background.add_child(sprite)
	return sprite


func asset_obj(texture: Texture2D, feet: Vector2, block: Rect2 = Rect2(), scale_factor := Vector2.ONE) -> Sprite2D:
	## Place an imported transparent prop in the y-sorted world.
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sprite.offset = Vector2(-texture.get_width() / 2.0, -texture.get_height())
	sprite.position = feet
	sprite.scale = scale_factor
	world.add_child(sprite)
	room_nodes.append(sprite)
	if block.size != Vector2.ZERO:
		blockers.append(block)
	return sprite


func character(texture: Texture2D, feet: Vector2) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.offset = Vector2(-texture.get_width() / 2.0, -texture.get_height())
	sprite.position = feet
	world.add_child(sprite)
	room_nodes.append(sprite)
	return sprite


func sir_getrich(feet: Vector2) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = SIR_GETRICH_HOME
	sprite.hframes = 4
	sprite.frame = 0
	sprite.centered = false
	sprite.offset = Vector2(-14, -48)
	sprite.position = feet
	world.add_child(sprite)
	room_nodes.append(sprite)
	sheet_animated.append({"sprite":sprite, "frames":4, "fps":2.2, "phase":0.0})
	return sprite


func idle_bob(sprite: Sprite2D, amplitude := 0.7, speed := 2.2) -> void:
	bobbing.append({"sprite": sprite, "base_y": sprite.position.y, "amplitude": amplitude,
		"speed": speed, "phase": float(int(sprite.position.x) % 9)})


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


func add_embers(rect: Rect2, color: Color, amount := 10, rise := 14.0, life := 2.2, size := 1.0) -> CPUParticles2D:
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
	p.scale_amount_min = size
	p.scale_amount_max = size
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


func add_shadow(feet: Vector2, w := 14.0, h := 5.0, alpha := 0.38) -> Polygon2D:
	## A soft dark ellipse on the floor under a prop, so it sits in the room instead of floating.
	var pts := PackedVector2Array()
	for i in 14:
		var a := TAU * i / 14.0
		pts.append(Vector2(cos(a) * w / 2.0, sin(a) * h / 2.0))
	var poly := Polygon2D.new()
	poly.polygon = pts
	poly.color = Color(0.02, 0.02, 0.07, alpha)
	poly.position = feet.round() - Vector2(0, 1)
	background.add_child(poly)
	return poly


func add_tint(rect: Rect2, color: Color) -> Polygon2D:
	## A flat dark (or coloured) rectangle under the props: wall-base shadow, floor tint.
	var poly := Polygon2D.new()
	poly.polygon = PackedVector2Array([rect.position, rect.position + Vector2(rect.size.x, 0), rect.position + rect.size, rect.position + Vector2(0, rect.size.y)])
	poly.color = color
	background.add_child(poly)
	return poly


func add_shape(points: PackedVector2Array, color: Color) -> Polygon2D:
	## A flat pixel-art silhouette or perspective plane beneath the room props.
	var poly := Polygon2D.new()
	poly.polygon = points
	poly.color = color
	background.add_child(poly)
	return poly


func add_patch(points: PackedVector2Array, color: Color) -> Polygon2D:
	## An additive patch of coloured light on the floor (stained glass, moonlight).
	var poly := Polygon2D.new()
	poly.polygon = points
	poly.color = color
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	mat.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
	poly.material = mat
	background.add_child(poly)
	return poly


func add_chain(x: float, y_top: float, y_bottom: float) -> Line2D:
	## A hanging chain (for the chandelier) drawn as a dotted dark line from the ceiling.
	var line := Line2D.new()
	line.points = PackedVector2Array([Vector2(x, y_top), Vector2(x, y_bottom)])
	line.width = 2.0
	line.default_color = Color("3c4058")
	line.texture_mode = Line2D.LINE_TEXTURE_NONE
	line.z_index = 3
	world.add_child(line)
	room_nodes.append(line)
	return line


func sway(sprite: Sprite2D, amp := 0.9, speed := 1.8, height := 36.0) -> void:
	## Cloth that moves: banners and tapestries sway at the hem.
	var mat := ShaderMaterial.new()
	mat.shader = SWAY_SHADER
	mat.set_shader_parameter("amp", amp)
	mat.set_shader_parameter("speed", speed)
	mat.set_shader_parameter("height", height)
	mat.set_shader_parameter("phase", float(int(sprite.position.x) % 7))
	sprite.material = mat


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
	body_sprite.self_modulate = Color(1.18, 1.18, 1.18, 1.0)
	body_sprite.region_enabled = true
	body_sprite.centered = false
	body_sprite.offset = Vector2(-FRAME.x / 2.0, -FRAME.y + 1)
	hunter.add_child(body_sprite)
	trinket_gem.position = Vector2(5, -16)
	trinket_gem.visible = false
	hunter.add_child(trinket_gem)
	world.add_child(hunter)
	oil_pet.texture = OIL_PET
	oil_pet.visible = false
	oil_pet.position = pos + Vector2(-18, -7)
	world.add_child(oil_pet)
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
	online_minimap.name = "OnlineRoomMap"
	online_minimap.visible = false
	online_minimap.draw.connect(_draw_online_minimap)
	hud.add_child(online_minimap)
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
	flash.color = Color(1.0, 0.85, 0.5, 0.0)
	flash.size = VIEW
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade_layer.add_child(flash)
	var crt_layer := CanvasLayer.new()
	crt_layer.layer = 100
	add_child(crt_layer)
	crt_rect.size = VIEW
	var mat := ShaderMaterial.new()
	mat.shader = CRT_SHADER
	crt_rect.material = mat
	crt_layer.add_child(crt_rect)


func _draw_online_minimap() -> void:
	## Unlabelled floor plan: the current room glows, and the Ferryman route is visible.
	var frame := Rect2(250, 5, 64, 42)
	online_minimap.draw_rect(frame, Color("171522"))
	online_minimap.draw_rect(frame, Color("b98d52"), false, 1.0)
	online_minimap.draw_rect(Rect2(252, 7, 60, 38), Color("2d2435"), false, 1.0)
	# Corridors connect the hub's landmarks; the left branch leads toward the Ferryman room and raid.
	online_minimap.draw_rect(Rect2(262, 19, 37, 2), Color("92724d"))
	online_minimap.draw_rect(Rect2(280, 12, 2, 20), Color("92724d"))
	online_minimap.draw_rect(Rect2(264, 19, 2, 18), Color("92724d"))
	var nodes := {
		"board": Rect2(255, 17, 10, 8),
		"hub": Rect2(270, 15, 21, 14),
		"shop": Rect2(296, 17, 13, 8),
		"arena": Rect2(276, 8, 10, 6),
		"ferryman": Rect2(254, 33, 12, 8),
	}
	var colors := {"board": Color("b3a0a0"), "hub": Color("9a6471"), "shop": Color("d6ad5e"), "arena": Color("bd7851"), "ferryman": Color("64c5ce")}
	for key in nodes:
		var box: Rect2 = nodes[key]
		online_minimap.draw_rect(box, Color("16131d"))
		online_minimap.draw_rect(box.grow(-1), colors[key])
	var active := Rect2(270, 15, 21, 14) if room_id == "online_hideout" else Rect2(254, 33, 12, 8)
	online_minimap.draw_rect(active.grow(1), Color("f3d27c"), false, 1.0)


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
	if state.has("visitors"):
		_update_visitors(state["visitors"])
	if state.has("leaderboard"):
		_update_online_leaderboard()
	var look: String = str(state.get("armorLook", "classic"))
	var colors := {"ivory": Color(1.8, 1.7, 1.6), "spectral": Color(0.55, 1.2, 1.05), "harvest": Color(1.35, 0.65, 0.35), "arcane": Color(0.75, 0.65, 1.25), "steel": Color(0.85, 1.0, 1.12), "ember": Color(1.25, 0.8, 0.48)}
	if colors.has(look) and not OUTFIT_SHEETS.has(look):
		var material := ShaderMaterial.new()
		material.shader = LOOK_SHADER
		material.set_shader_parameter("tint", colors[look])
		material.set_shader_parameter("strength", 0.8)
		material.set_shader_parameter("ivory", look == "ivory")
		body_sprite.material = material
	else:
		body_sprite.material = null
	oil_pet.visible = str(state.get("pet", "none")) == "oil"
	var charm: String = str(state.get("trinketIcon", "none"))
	trinket_gem.visible = CHARMS.has(charm)
	if trinket_gem.visible: trinket_gem.texture = CHARMS[charm]
	_configure_pyr_sheet(clampi(int(state.get("pyr_stage", 1)), 1, 4))
	if str(state.get("pyr_action", "")) == "feed":
		pyr_pose = 3
		pyr_pose_time = 2.5
		state["pyr_action"] = ""
	var said := str(state.get("toast", ""))
	if said != "":
		toast(said)
		state["toast"] = ""
	crt_rect.visible = bool(state["crt"])
	pips.queue_redraw()
	if not changing and built_level >= 0 and room_level(room_id) != built_level:
		var gained: bool = room_level(room_id) > built_level
		go_room(room_id, pos, true)     # an upgrade was bought: rebuild this room at its new level
		if gained:
			_celebrate(Rooms.upgrade_name(room_id, built_level))


func _update_online_leaderboard() -> void:
	var labels := world.find_children("*", "Label", true, false)
	var rows: Array = state.get("leaderboard", []) if state.get("leaderboard", []) is Array else []
	for label in labels:
		if not label.has_meta("online_leaderboard_row"):
			continue
		var index := int(label.get_meta("online_leaderboard_row"))
		if rows.is_empty():
			label.text = "NO MATCH" if index == 0 else ""
		elif index < rows.size():
			var entry: Dictionary = rows[index] if rows[index] is Dictionary else {}
			var display_name := str(entry.get("name", "Hunter")).strip_edges()
			if display_name.length() > 8:
				display_name = display_name.substr(0, 7) + "."
			label.text = "%d %s" % [index + 1, display_name]
		else:
			label.text = ""


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
	if oil_pet.visible:
		var target: Vector2 = pos + Vector2(-18, -7 + sin(clock * 3.0))
		if oil_pet.position.distance_to(target) > 90.0:
			oil_pet.position = target
		else:
			oil_pet.position = oil_pet.position.lerp(target, minf(1.0, delta * 5.0))
	pyr_pose_time = maxf(0.0, pyr_pose_time - delta)
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
			_move(dir * SPEED * (1.45 if Input.is_key_pressed(KEY_SHIFT) else 1.0) * delta)
		else:
			anim_t = 0.0
		_check_doors()
	_refresh_hunter()
	_animate_visitors(delta)
	if OS.has_feature("web") and not changing:
		map_update_time -= delta
		if map_update_time <= 0.0:
			map_update_time = 0.15
			if pos.distance_to(map_last_pos) > 0.5:
				map_last_pos = pos
				_send_app({"type": "position", "room": room_id, "x": pos.x, "y": pos.y, "facing": facing})
	if room_id == "den":
		_wander_pyr(delta)
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
	var look: String = str(state.get("armorLook", "classic"))
	var sheets: Dictionary = OUTFIT_SHEETS.get(look, {"front": SHEET_FRONT, "side": SHEET_SIDE, "back": SHEET_BACK})
	match facing:
		"up":
			body_sprite.texture = sheets["back"]
		"down":
			body_sprite.texture = sheets["front"]
		_:
			body_sprite.texture = sheets["side"]
	body_sprite.flip_h = facing == "right"
	var col: int
	if anim_t > 0.0:
		col = int(anim_t) % WALK_FRAMES
	else:
		col = WALK_FRAMES + int(clock * IDLE_FPS) % IDLE_FRAMES   # breathing, after the walk frames
	body_sprite.region_rect = Rect2(col * FRAME.x, 0, FRAME.x, FRAME.y)


func _update_visitors(incoming: Variant) -> void:
	# Presence is presentation only. The app authenticates membership and never
	# sends player inventory, credentials, or save state through this bridge.
	if not incoming is Array:
		return
	var retained := {}
	for item in incoming.slice(0, 3):
		if not item is Dictionary:
			continue
		var id := str(item.get("id", ""))
		if id.is_empty() or id.length() > 128:
			continue
		var x: Variant = item.get("x")
		var y: Variant = item.get("y")
		if not (x is int or x is float) or not (y is int or y is float):
			continue
		if not is_finite(float(x)) or not is_finite(float(y)):
			continue
		retained[id] = true
		if not visitors.has(id):
			var node := Node2D.new()
			node.name = "GuestHunter"
			var sprite := Sprite2D.new()
			sprite.name = "Body"
			sprite.region_enabled = true
			sprite.centered = false
			sprite.offset = Vector2(-FRAME.x / 2.0, -FRAME.y + 1)
			sprite.self_modulate = Color(1.18, 1.18, 1.18, 1.0)
			node.add_child(sprite)
			var name_label := Label.new()
			name_label.name = "Name"
			_style(name_label, 5, Color("f8dfa6"))
			name_label.position = Vector2(-40, -48)
			name_label.size = Vector2(80, 10)
			name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			name_label.clip_text = true
			node.add_child(name_label)
			world.add_child(node)
			node.position = Vector2(clampf(float(x), 0, VIEW.x), clampf(float(y), 0, VIEW.y))
			visitors[id] = {"node": node, "sprite": sprite, "label": name_label, "target": node.position, "moving": 0.0}
		var guest: Dictionary = visitors[id]
		var target := Vector2(clampf(float(x), 0, VIEW.x), clampf(float(y), 0, VIEW.y))
		if (guest["target"] as Vector2).distance_to(target) > 0.5:
			guest["moving"] = 0.4
		guest["target"] = target
		guest["facing"] = str(item.get("facing", "down"))
		var look := str(item.get("look", "classic"))
		if str(guest.get("look", "")) != look:
			var sprite: Sprite2D = guest["sprite"]
			var colors := {"arcane": Color(0.75, 0.65, 1.25), "steel": Color(0.85, 1.0, 1.12), "ember": Color(1.25, 0.8, 0.48)}
			if colors.has(look):
				var material := ShaderMaterial.new()
				material.shader = LOOK_SHADER
				material.set_shader_parameter("tint", colors[look])
				material.set_shader_parameter("strength", 0.8)
				sprite.material = material
			else:
				sprite.material = null
		guest["look"] = look
		guest["room"] = str(item.get("room", "great_hall"))
		var label: Label = guest["label"]
		var display_name := str(item.get("name", "Hunter")).strip_edges()
		if display_name.length() > 12:
			display_name = display_name.substr(0, 10) + ".."
		label.text = display_name
	for id in visitors.keys():
		if not retained.has(id):
			var node: Node2D = visitors[id]["node"]
			node.queue_free()
			visitors.erase(id)


func _animate_visitors(delta: float) -> void:
	for guest in visitors.values():
		var node: Node2D = guest["node"]
		var sprite: Sprite2D = guest["sprite"]
		node.visible = str(guest.get("room", "")) == room_id
		if not node.visible:
			continue
		var target: Vector2 = guest["target"]
		node.position = node.position.lerp(target, minf(1.0, delta * 12.0))
		guest["moving"] = maxf(0.0, float(guest["moving"]) - delta)
		var sheets: Dictionary = OUTFIT_SHEETS.get(str(guest.get("look", "classic")), {"front": SHEET_FRONT, "side": SHEET_SIDE, "back": SHEET_BACK})
		var direction := str(guest.get("facing", "down"))
		sprite.texture = sheets["back"] if direction == "up" else sheets["front"] if direction == "down" else sheets["side"]
		sprite.flip_h = direction == "right"
		var col := int(clock * WALK_FPS) % WALK_FRAMES if float(guest["moving"]) > 0.0 else WALK_FRAMES + int(clock * IDLE_FPS) % IDLE_FRAMES
		sprite.region_rect = Rect2(col * FRAME.x, 0, FRAME.x, FRAME.y)


func _configure_pyr_sheet(stage: int) -> void:
	## Optional imported six-frame strips. Missing or malformed art keeps the current flame.
	if stage == pyr_sheet_stage:
		return
	pyr_sheet_stage = stage
	var path := "res://art/pyr_stage_%d.png" % stage
	var sheet: Texture2D = null
	if ResourceLoader.exists(path):
		sheet = load(path) as Texture2D
	pyr_custom_sheet = sheet != null and sheet.get_width() == PYR_CELL * PYR_FRAMES and sheet.get_height() == PYR_CELL
	if pyr_custom_sheet:
		pyr.texture = sheet
		pyr.offset = Vector2(-PYR_CELL / 2.0, -PYR_CELL)
	else:
		pyr.texture = TILES
		pyr.offset = Vector2(-8, -16)
		pyr.region_rect = TilesData.REGIONS["pyr_0"]


func _wander_pyr(delta: float) -> void:
	# Pyr explores the current room independently, pausing between short flights.
	pyr_wander_wait -= delta
	if pyr_pose_time <= 0.0 and pyr_wander_wait <= 0.0 and pyr_pos.distance_to(pyr_target) < 3.0:
		for attempt in 12:
			var candidate := Vector2(randf_range(38.0, VIEW.x - 38.0), randf_range(92.0, 164.0))
			if not _hits(candidate) and candidate.distance_to(pyr_pos) > 25.0:
				pyr_target = candidate
				break
		pyr_wander_wait = randf_range(2.5, 5.0)
	var moving := pyr_pose_time <= 0.0 and pyr_pos.distance_to(pyr_target) > 2.0
	if moving:
		var step := (pyr_target - pyr_pos).limit_length(24.0 * delta)
		if _hits(pyr_pos + step):
			pyr_target = pyr_pos
			pyr_wander_wait = 0.3
		else:
			if absf(step.x) > 0.01: pyr_facing_left = step.x < 0.0
			pyr_pos += step
			if pyr_pos.distance_to(pyr_target) < 3.0:
				pyr_wander_wait = randf_range(1.0, 3.0)
	var bob := sin(clock * 3.0) * 1.5
	pyr.position = (pyr_pos + Vector2(0, bob)).round()
	if pyr_custom_sheet:
		pyr.flip_h = pyr_facing_left if pyr_sheet_stage == 1 else not pyr_facing_left
		var frame: int
		if pyr_pose_time > 0.0:
			frame = 5 if pyr_pose == 3 else 4
		elif moving:
			frame = 2 + int(clock * 6.0) % 2
		else:
			frame = int(clock * 2.0) % 2
		pyr.region_rect = Rect2(frame * PYR_CELL, 0, PYR_CELL, PYR_CELL)
	else:
		pyr.flip_h = false
		_set_piece(pyr, "pyr_%d" % (int(clock * 3.0) % 2))


func _animate_room(delta: float) -> void:
	var beat := int(clock * 4.0) % 2
	for a in animated:
		_set_piece(a["sprite"], "%s_%d" % [a["base"], (beat + int(a["phase"])) % int(a["frames"])])
	for a in sheet_animated:
		var sprite: Sprite2D = a["sprite"]
		if is_instance_valid(sprite):
			sprite.frame = (int(clock * float(a["fps"])) + int(a["phase"])) % int(a["frames"])
	for b in bobbing:
		var sprite: Sprite2D = b["sprite"]
		if is_instance_valid(sprite):
			sprite.position.y = float(b["base_y"]) + sin(clock * float(b["speed"]) + float(b["phase"])) * float(b["amplitude"])
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
	if room_id == "den" and near.is_empty() and pos.distance_to(pyr_pos) < 25.0:
		near = {"id": "pyr", "label": "Visit Pyr"}
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
	if id == "perch":
		pyr_pose = 2
		pyr_pose_time = 2.5
	_send_app({"type": "use", "station": id})
	if not OS.has_feature("web"):
		toast_label.text = "(standalone) used " + id
		toast_time = 2.0


func toast(text: String) -> void:
	toast_label.text = text.to_upper()
	toast_time = 3.0
