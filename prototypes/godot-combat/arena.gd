extends Node2D

const HOLLOW_SHADER = preload("res://hollow.gdshader")
const ATLAS: Texture2D = preload("res://art/tiles.png")
const HUNTER_SWORD: Texture2D = preload("res://art/tate-sword-v2-sheet.png")
const HUNTER_IDLE: Texture2D = preload("res://art/tate-idle-sheet.png")
const HUNTER_FOLLOW: Texture2D = preload("res://art/tate-followthrough-sheet.png")
const HUNTER_HURT: Texture2D = preload("res://art/tate-hurt-sheet.png")
const STAFF: Texture2D = preload("res://art/tate-staff-sheet.png")
const STAFF_HURT: Texture2D = preload("res://art/tate-staff-hurt-sheet.png")
const WHIP: Texture2D = preload("res://art/tate-whip-sheet.png")
const WHIP_HURT: Texture2D = preload("res://art/tate-whip-hurt-sheet.png")
const GREATSWORD: Texture2D = preload("res://art/tate-greatsword-sheet.png")
const GREATSWORD_HURT: Texture2D = preload("res://art/tate-greatsword-hurt-sheet.png")
const HANDMAGIC: Texture2D = preload("res://art/tate-handmagic-sheet.png")
const HANDMAGIC_HURT: Texture2D = preload("res://art/tate-handmagic-hurt-sheet.png")
const CRYPT: Texture2D = preload("res://art/crypt.png")
const MIMIC: Texture2D = preload("res://art/mimic-action-sheet.png")
const MIMIC_HURT: Texture2D = preload("res://art/mimic-hurt-sheet.png")
const HOLLOW: Texture2D = preload("res://art/hollow-action-sheet.png")
const HOLLOW_HURT: Texture2D = preload("res://art/hollow-hurt-sheet.png")

var hunter: Node2D
var body: Sprite2D
var enemy: Sprite2D
var hp_bar: ColorRect
var resolve_bar: ColorRect
var status_label: Label
var mode_label: Label
var enemy_label: Label
var health_label: Label
var weapon_label: Label
var weapon_index := 0
var weapons := [
	{"name": "SWORD", "action": HUNTER_SWORD, "hurt": HUNTER_HURT},
	{"name": "STAFF", "action": STAFF, "hurt": STAFF_HURT},
	{"name": "WHIP", "action": WHIP, "hurt": WHIP_HURT},
	{"name": "GREATSWORD", "action": GREATSWORD, "hurt": GREATSWORD_HURT},
	{"name": "HAND MAGIC", "action": HANDMAGIC, "hurt": HANDMAGIC_HURT},
]
var hp := 5
var resolve := 5
var simulated := true
var acting := false
var elapsed := 0.0
var shot_path := ""
var shot_pose := -1

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			shot_path = arg.trim_prefix("--shot=")
		if arg.begins_with("--pose="):
			shot_pose = int(arg.trim_prefix("--pose="))
	build_scene()
	if not shot_path.is_empty():
		if shot_pose >= 0:
			body.texture = HUNTER_SWORD
			body.frame = clampi(shot_pose, 0, 3)
		await get_tree().create_timer(0.8).timeout
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(shot_path)
		get_tree().quit()

func tile(rect: Rect2, at: Vector2, scale_value := 1.0) -> Sprite2D:
	var texture := AtlasTexture.new()
	texture.atlas = ATLAS
	texture.region = rect
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.centered = false
	sprite.position = at
	sprite.scale = Vector2.ONE * scale_value
	add_child(sprite)
	return sprite

func build_scene() -> void:
	# A painted backdrop sits behind independent scene lights, props and actors.
	var backdrop := Sprite2D.new()
	backdrop.texture = CRYPT
	backdrop.centered = false
	add_child(backdrop)
	# Separate flames and light nodes let the environment move and react.
	for x in [32, 275]:
		tile(Rect2(70, 269, 13, 30), Vector2(x, 61), 0.8)
	# Light is an actual Godot canvas light, not baked into the tiles.
	for p in [Vector2(35, 76), Vector2(282, 76)]:
		var gradient := Gradient.new()
		gradient.set_color(0, Color(1.0, 0.62, 0.24, 0.6))
		gradient.set_color(1, Color(1.0, 0.35, 0.1, 0.0))
		var tex := GradientTexture2D.new()
		tex.width = 128
		tex.height = 128
		tex.fill = GradientTexture2D.FILL_RADIAL
		tex.fill_from = Vector2(0.5, 0.5)
		tex.fill_to = Vector2(1.0, 0.5)
		tex.gradient = gradient
		var light := PointLight2D.new()
		light.texture = tex
		light.position = p
		light.energy = 0.65
		add_child(light)
	# A drawn grid and particles are separate transparent geometry layers.
	var overlay := SimulationOverlay.new()
	overlay.owner_scene = self
	add_child(overlay)
	var hunter_shadow := Polygon2D.new()
	hunter_shadow.polygon = PackedVector2Array([Vector2(-20, 0), Vector2(-12, -3), Vector2(12, -3), Vector2(20, 0), Vector2(12, 3), Vector2(-12, 3)])
	hunter_shadow.color = Color(0.03, 0.02, 0.04, 0.65)
	hunter_shadow.position = Vector2(83, 146)
	add_child(hunter_shadow)
	hunter = Node2D.new()
	hunter.position = Vector2(83, 146)
	add_child(hunter)
	body = Sprite2D.new()
	body.texture = HUNTER_IDLE
	body.hframes = 4
	body.frame = 0
	body.scale = Vector2(1.5, 1.5)
	# Frame cells share a 35px foot anchor and a 68px baseline.
	body.offset = Vector2(13, 0)
	body.position = Vector2(0, -48)
	hunter.add_child(body)
	enemy = Sprite2D.new()
	enemy.texture = HOLLOW
	enemy.hframes = 4
	enemy.offset = Vector2(-7, 0)
	enemy.position = Vector2(237, 96)
	enemy.scale = Vector2(1.5, 1.5)
	add_child(enemy)
	set_mode(true)
	build_hud()

func build_hud() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)
	panel(ui, Rect2(5, 5, 137, 23), Color("101324"))
	panel(ui, Rect2(178, 5, 137, 23), Color("101324"))
	health_label = label(ui, "TATE  ·  PRACTICE HP", Vector2(9, 7), 8, Color("f5dfb8"))
	enemy_label = label(ui, "HOLLOW  ·  RESOLVE", Vector2(183, 7), 8, Color("b9eaff"))
	panel(ui, Rect2(9, 19, 128, 5), Color("382638"))
	panel(ui, Rect2(183, 19, 128, 5), Color("263044"))
	hp_bar = panel(ui, Rect2(9, 19, 128, 5), Color("e05e62"))
	resolve_bar = panel(ui, Rect2(183, 19, 128, 5), Color("69cdea"))
	mode_label = label(ui, "SPARRING  /  HOLLOW SIMULATION", Vector2(9, 31), 8, Color("7bd7ed"))
	weapon_label = label(ui, "SWORD", Vector2(240, 31), 8, Color("f6d287"))
	status_label = label(ui, "YOUR TURN", Vector2(9, 154), 7, Color("ead7b5"))
	button(ui, "HIT", Vector2(104, 151), Vector2(35, 22), _attack)
	button(ui, "MISS", Vector2(142, 151), Vector2(38, 22), _miss)
	button(ui, "RESET", Vector2(183, 151), Vector2(39, 22), _reset)
	button(ui, "MODE", Vector2(225, 151), Vector2(36, 22), _toggle_mode)
	button(ui, "WEAPON", Vector2(264, 151), Vector2(51, 22), _next_weapon)

func panel(parent: Node, rect: Rect2, color: Color) -> ColorRect:
	var item := ColorRect.new()
	item.position = rect.position
	item.size = rect.size
	item.color = color
	parent.add_child(item)
	return item

func label(parent: Node, text: String, at: Vector2, font_size: int, color: Color) -> Label:
	var item := Label.new()
	item.text = text
	item.position = at
	item.add_theme_font_size_override("font_size", font_size)
	item.add_theme_color_override("font_color", color)
	parent.add_child(item)
	return item

func button(parent: Node, text: String, at: Vector2, dimensions: Vector2, action: Callable) -> void:
	var item := Button.new()
	item.text = text
	item.position = at
	item.size = dimensions
	item.focus_mode = Control.FOCUS_NONE
	item.add_theme_font_size_override("font_size", 7)
	item.pressed.connect(action)
	parent.add_child(item)

func set_mode(is_simulated: bool) -> void:
	simulated = is_simulated
	if simulated:
		enemy.texture = HOLLOW
		enemy.scale = Vector2(1.5, 1.5)
		enemy.position = Vector2(237, 96)
		var material := ShaderMaterial.new()
		material.shader = HOLLOW_SHADER
		enemy.material = material
	else:
		enemy.texture = MIMIC
		enemy.material = null
		enemy.scale = Vector2(1.5, 1.5)
		enemy.position = Vector2(237, 96)
	enemy.frame = 0
	if mode_label:
		mode_label.text = "SPARRING  /  HOLLOW SIMULATION" if simulated else "DUNGEON  /  STRING MIMIC"
		enemy_label.text = "HOLLOW  ·  RESOLVE" if simulated else "MIMIC  ·  RESOLVE"
		health_label.text = "TATE  ·  PRACTICE HP" if simulated else "TATE  ·  DEMO HP"

func _toggle_mode() -> void:
	if acting: return
	set_mode(not simulated)
	_reset()

func _idle_texture() -> Texture2D:
	return HUNTER_IDLE if weapon_index == 0 else weapons[weapon_index]["action"]

func _set_idle() -> void:
	body.texture = _idle_texture()
	body.offset = Vector2(13, 0) if weapon_index == 0 else Vector2(19, 0)
	body.frame = 0

func _next_weapon() -> void:
	if acting: return
	weapon_index = (weapon_index + 1) % weapons.size()
	weapon_label.text = weapons[weapon_index]["name"]
	_set_idle()

func _magic_projectile() -> void:
	var bolt := Polygon2D.new()
	bolt.polygon = PackedVector2Array([Vector2(-6, 0), Vector2(-2, -4), Vector2(4, -3), Vector2(7, 0), Vector2(4, 3), Vector2(-2, 4)])
	bolt.color = Color("d188ff") if weapon_index == 4 else Color("8ceeff")
	if weapon_index == 4:
		bolt.scale = Vector2(1.6, 1.6)
		var core := Polygon2D.new()
		core.polygon = PackedVector2Array([Vector2(-2, 0), Vector2(0, -2), Vector2(3, 0), Vector2(0, 2)])
		core.color = Color("fff2ff")
		bolt.add_child(core)
	bolt.position = Vector2(125, 94)
	add_child(bolt)
	var t := create_tween()
	t.tween_property(bolt, "position:x", 222.0, 0.22)
	t.tween_callback(bolt.queue_free)
	t.tween_callback(_enemy_hit)

func _attack() -> void:
	if acting or resolve <= 0 or hp <= 0: return
	acting = true
	status_label.text = "TATE ATTACKS"
	if weapon_index != 0:
		_weapon_attack()
		return
	body.texture = HUNTER_SWORD
	var t := create_tween()
	t.tween_callback(func(): body.frame = 1)
	t.tween_interval(0.12)
	t.tween_callback(func(): body.frame = 2)
	t.tween_interval(0.08)
	t.tween_callback(func(): body.texture = HUNTER_FOLLOW; body.frame = 0)
	t.tween_interval(0.08)
	t.tween_callback(func(): body.frame = 1)
	t.tween_property(hunter, "position:x", 140.0, 0.14).set_trans(Tween.TRANS_QUAD)
	t.tween_callback(func(): body.frame = 2)
	t.tween_callback(_enemy_hit)
	t.tween_interval(0.13)
	t.tween_callback(func(): body.frame = 3)
	t.tween_property(hunter, "position:x", 83.0, 0.20)
	t.tween_callback(_finish_turn)

func _weapon_attack() -> void:
	body.texture = weapons[weapon_index]["action"]
	body.frame = 1
	var t := create_tween()
	var windup := 0.25 if weapon_index == 3 else 0.16
	t.tween_interval(windup)
	t.tween_callback(func(): body.frame = 2)
	if weapon_index == 1 or weapon_index == 4:
		t.tween_callback(_magic_projectile)
		t.tween_interval(0.32)
	else:
		var reach := 105.0 if weapon_index == 2 else 128.0
		t.tween_property(hunter, "position:x", reach, 0.13 if weapon_index == 2 else 0.20).set_trans(Tween.TRANS_QUAD)
		t.tween_callback(_enemy_hit)
		t.tween_interval(0.16)
	t.tween_callback(func(): body.frame = 3)
	t.tween_property(hunter, "position:x", 83.0, 0.22)
	t.tween_callback(_finish_turn)

func _enemy_hit() -> void:
	resolve = maxi(0, resolve - 1)
	resolve_bar.size.x = 128.0 * resolve / 5.0
	enemy.texture = HOLLOW_HURT if simulated else MIMIC_HURT
	enemy.frame = 0
	var t := create_tween()
	t.tween_interval(0.07)
	t.tween_callback(func(): enemy.frame = 1)
	t.tween_interval(0.09)
	t.tween_callback(func(): enemy.frame = 2)
	t.tween_interval(0.09)
	t.tween_callback(func(): enemy.frame = 3)
	t.tween_interval(0.08)
	t.tween_callback(func(): enemy.texture = HOLLOW if simulated else MIMIC; enemy.frame = 0)

func _miss() -> void:
	if acting or resolve <= 0 or hp <= 0: return
	acting = true
	status_label.text = "HOLLOW STRIKES" if simulated else "MIMIC STRIKES"
	var original := enemy.position
	var t := create_tween()
	t.tween_callback(func(): enemy.frame = 2)
	t.tween_interval(0.15)
	t.tween_callback(func(): enemy.frame = 3)
	t.tween_property(enemy, "position:x", 196.0, 0.25)
	t.tween_callback(_hunter_hit)
	t.tween_property(enemy, "position", original, 0.25)
	t.tween_callback(func(): enemy.frame = 0)
	t.tween_interval(0.2)
	t.tween_callback(_finish_turn)

func _hunter_hit() -> void:
	hp = maxi(0, hp - 1)
	hp_bar.size.x = 128.0 * hp / 5.0
	body.texture = weapons[weapon_index]["hurt"]
	body.frame = 0
	var t := create_tween()
	t.tween_interval(0.08)
	t.tween_callback(func(): body.frame = 1)
	t.tween_interval(0.1)
	t.tween_callback(func(): body.frame = 2)
	t.tween_interval(0.1)
	t.tween_callback(func(): body.frame = 3)
	t.tween_interval(0.1)
	t.tween_callback(_set_idle)

func _finish_turn() -> void:
	acting = false
	_set_idle()
	status_label.text = "FOE BROKEN" if resolve == 0 else ("HUNTER DOWN" if hp == 0 else "YOUR TURN")

func _reset() -> void:
	if acting: return
	hp = 5
	resolve = 5
	hp_bar.size.x = 128
	resolve_bar.size.x = 128
	status_label.text = "YOUR TURN"

func _process(delta: float) -> void:
	elapsed += delta
	if not acting and body and enemy and shot_pose < 0:
		var idle_cycle := [0, 1, 2, 3, 2, 1]
		body.frame = idle_cycle[int(elapsed * 4.0) % idle_cycle.size()] if weapon_index == 0 else 0
		if weapon_index != 0:
			body.position.y = -48.0 + sin(elapsed * 3.0) * 0.7
		else:
			body.position.y = -48.0
		enemy.frame = int(elapsed * 3.0) % 2
	queue_redraw()

class SimulationOverlay extends Node2D:
	var owner_scene: Node2D
	func _process(_delta: float) -> void:
		queue_redraw()
	func _draw() -> void:
		if not owner_scene.simulated: return
		var blue := Color(0.23, 0.72, 0.94, 0.28)
		# Perspective projection grid distinguishes a simulated training room.
		for x in range(-160, 481, 40):
			draw_line(Vector2(160 + (x - 160) * 0.25, 112), Vector2(x, 180), blue, 1.0)
		for y in [119, 128, 142, 162, 179]:
			draw_line(Vector2(0, y), Vector2(320, y), blue, 1.0)
		for x in [55, 160, 265]:
			draw_line(Vector2(x, 30), Vector2(x, 100), Color(0.25, 0.8, 1, 0.18), 1.0)
