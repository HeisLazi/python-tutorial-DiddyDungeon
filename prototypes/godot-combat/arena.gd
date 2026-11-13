extends Node2D

const HOLLOW_SHADER = preload("res://hollow.gdshader")
const LOOK_SHADER = preload("res://hunter_look.gdshader")
const OIL_PET = preload("res://art/oil-pet.png")
const CHARMS := {"pink-cap": preload("res://art/charm-pink-cap.png"), "soul-lantern": preload("res://art/charm-soul-lantern.png"), "jacklight": preload("res://art/charm-jacklight.png"), "generic": preload("res://art/charm-generic.png")}
const ATLAS: Texture2D = preload("res://art/tiles.png")
const CATALOG = preload("res://combat_catalog.gd")
const SIMULATION: Texture2D = preload("res://art/simulation.png")
const LIVE_ENEMIES := {
 "wraith": preload("res://art/live-wraith.png"),
 "forked-path": preload("res://art/live-fork.png"),
 "mimic-matriarch": preload("res://art/live-matriarch.png"),
}
const CHOEF_THRONE_ROOM: Texture2D = preload("res://art/choef-throne-room.png")
const REGION_BACKDROPS := {
	"choef-chief-keep": CHOEF_THRONE_ROOM,
	"duel-colosseum": preload("res://art/colosseum-duel.png"),
	"elite-endless-echo": preload("res://art/elites/endless-echo-arena.png"),
	"elite-delivery-beast": preload("res://art/elites/delivery-beast-arena.png"),
	"elite-clockwork-caravan": preload("res://art/elites/clockwork-caravan-arena.png"),
	"elite-unwritten-road": preload("res://art/elites/unwritten-road-arena.png"),
	"unwritten-king": preload("res://art/unwritten-king-arena.png"),
	"silver-mogul": preload("res://art/silver-mogul-arena.png"),
	"tozza": preload("res://art/tozza-arena.png"),
	"blackjack-house": preload("res://art/the-house-arena.png"),
	"basics": preload("res://art/basics-village.png"),
	"collections": preload("res://art/collection-caves.png"),
}
const ANIMATED_ENEMIES := {
	"wraith": {"action": preload("res://art/wraith-v2-sheet.png"), "hurt": preload("res://art/wraith-v2-hurt-sheet.png"), "scale": 1.5},
	"drowner": {"action": preload("res://art/drowner-sheet.png"), "hurt": preload("res://art/drowner-hurt-sheet.png"), "scale": 1.5},
	"ghoul": {"action": preload("res://art/ghoul-sheet.png"), "hurt": preload("res://art/ghoul-hurt-sheet.png"), "scale": 1.5},
	"loaded-die": {"action": preload("res://art/loaded-die-sheet.png"), "hurt": preload("res://art/loaded-die-hurt-sheet.png"), "scale": 1.4},
	"forked-path": {"action": preload("res://art/forked-path-sheet.png"), "hurt": preload("res://art/forked-path-hurt-sheet.png"), "scale": 1.5},
	"mimic-matriarch": {"action": preload("res://art/matriarch-sheet.png"), "hurt": preload("res://art/matriarch-hurt-sheet.png"), "scale": 1.9},
	"drowned-hoard": {"action": preload("res://art/drowned-hoard-sheet.png"), "hurt": preload("res://art/drowned-hoard-hurt-sheet.png"), "scale": 1.9},
}
const LANTERN_ENEMIES := {
	"blackjack-bust-hound": {"action": preload("res://art/blackjack/bust-hound.png"), "scale": 1.5, "ground_offset": 21.0},
	"blackjack-house-clerk": {"action": preload("res://art/blackjack/house-clerk.png"), "scale": 1.5, "ground_offset": 9.0},
	"blackjack-judge": {"action": preload("res://art/blackjack/judge.png"), "scale": 1.5, "ground_offset": 0.0},
	"blackjack-rematch-shade": {"action": preload("res://art/blackjack/rematch-shade.png"), "scale": 1.5, "ground_offset": 6.0},
	"blackjack-empty-table": {"action": preload("res://art/blackjack/empty-table.png"), "scale": 1.5, "ground_offset": 15.0},
	"blackjack-dealers-hand": {"action": preload("res://art/blackjack/dealers-hand.png"), "scale": 1.5, "ground_offset": 0.0},
	"blackjack-count-keeper": {"action": preload("res://art/blackjack/count-keeper.png"), "scale": 1.5, "ground_offset": 7.5},
	"blackjack-hitman": {"action": preload("res://art/blackjack/hitman.png"), "scale": 1.5, "ground_offset": 7.5},
	"silver-mogul": {"action": preload("res://art/silver-mogul-sheet.png"), "scale": 1.9, "ground_offset": 2.0},
	"tozza": {"action": preload("res://art/tozza-sheet.png"), "scale": 1.9},
	"blackjack-house": {"action": preload("res://art/the-house-sheet.png"), "scale": 1.9, "ground_offset": 4.0},
	"lantern-broken-number": {"action": preload("res://art/lantern/broken-number.png"), "scale": 1.5, "ground_offset": 9.0},
	"lantern-clockwork-caravan": {"action": preload("res://art/lantern/clockwork-caravan.png"), "scale": 1.6, "ground_offset": 16.0},
	"lantern-counting-moth": {"action": preload("res://art/lantern/counting-moth.png"), "scale": 1.5},
	"lantern-delivery-beast": {"action": preload("res://art/lantern/delivery-beast.png"), "scale": 1.6, "ground_offset": 10.0},
	"lantern-endless-echo": {"action": preload("res://art/lantern/endless-echo.png"), "scale": 1.5, "ground_offset": 8.0},
	"lantern-first-spark": {"action": preload("res://art/lantern/first-spark.png"), "scale": 1.5, "ground_offset": 10.5},
	"lantern-inventory-drowner": {"action": preload("res://art/lantern/inventory-drowner.png"), "scale": 1.5, "ground_offset": 7.5},
	"lantern-little-lantern": {"action": preload("res://art/lantern/little-lantern.png"), "scale": 1.5, "ground_offset": 10.5},
	"lantern-mapkeeper": {"action": preload("res://art/lantern/mapkeeper.png"), "scale": 1.5, "ground_offset": 7.5},
	"lantern-memory-keeper": {"action": preload("res://art/lantern/memory-keeper.png"), "scale": 1.5, "ground_offset": 6.0},
	"lantern-module-mason": {"action": preload("res://art/lantern/module-mason.png"), "scale": 1.5, "ground_offset": 10.5},
	"lantern-quiet-flame": {"action": preload("res://art/lantern/quiet-flame.png"), "scale": 1.5},
	"lantern-remembering-shade": {"action": preload("res://art/lantern/remembering-shade.png"), "scale": 1.5},
	"lantern-selfless-golem": {"action": preload("res://art/lantern/selfless-golem.png"), "scale": 1.6, "ground_offset": 8.0},
	"lantern-test-lantern": {"action": preload("res://art/lantern/test-lantern.png"), "scale": 1.5, "ground_offset": 9.0},
	"lantern-transformation-sprite": {"action": preload("res://art/lantern/transformation-sprite.png"), "scale": 1.5},
	"lantern-unwritten-king": {"action": preload("res://art/lantern/unwritten-king.png"), "scale": 1.9, "ground_offset": 4.0},
	"lantern-unwritten-road": {"action": preload("res://art/lantern/unwritten-road.png"), "scale": 1.6, "ground_offset": 10.0},
	"lantern-whispering-gate": {"action": preload("res://art/lantern/whispering-gate.png"), "scale": 1.5, "ground_offset": 7.5},
}
const CRYPT: Texture2D = preload("res://art/crypt.png")
const MIMIC: Texture2D = preload("res://art/mimic-action-sheet.png")
const MIMIC_HURT: Texture2D = preload("res://art/mimic-hurt-sheet.png")
const HOLLOW: Texture2D = preload("res://art/hollow-action-sheet.png")
const HOLLOW_HURT: Texture2D = preload("res://art/hollow-hurt-sheet.png")
const CHOEF_IDLE_SHEET: Texture2D = preload("res://art/choef-chief-idle.png")

var embedded := false
var unarmed := false
var live_enemy_id := "string-mimic"
var live_region_id := ""
var region_lights: Array[PointLight2D] = []
var bridge_callback: JavaScriptObject
var last_turn_id := ""
var pending_live_turns: Array[Dictionary] = []
var pending_live_state: Dictionary = {}
var backdrop: Sprite2D
var dungeon_decor: Array[CanvasItem] = []
var hunter: Node2D
var body: Sprite2D
var oil_pet: Sprite2D
var trinket_gem: Sprite2D
var enemy: Sprite2D
var raid_status: Node2D
var hunter_shadow: Polygon2D
var raid_party_sprites: Array[Sprite2D] = []
var raid_party_shadows: Array[Polygon2D] = []
var raid_party_signature := ""
var raid_attack: Dictionary = {}
var raid_enemy_anchor := Vector2(258, 105)
var hunter_home_x := 83.0
var hp_bar: ColorRect
var resolve_bar: ColorRect
var status_label: Label
var mode_label: Label
var enemy_label: Label
var health_label: Label
var weapon_label: Label
var weapon_index := 0
var weapon_variant := ""
var variant_pose_cache := {}
var weapons: Array = CATALOG.STYLES
var skins: Dictionary = {"tate": CATALOG.tate(), "ivory": CATALOG.ivory(), "warden": CATALOG.warden(), "harvest": CATALOG.harvest(), "oracle": CATALOG.oracle(), "patchwork": CATALOG.patchwork(), "pilgrim": CATALOG.pilgrim(), "wayfarer": CATALOG.wayfarer(), "norse": CATALOG.norse(), "lanternkeeper": CATALOG.lanternkeeper(), "wardplate": CATALOG.wardplate(), "debugger": CATALOG.debugger(), "merchant-oracle": CATALOG.merchant_oracle()}
var skin_id := "tate"
var hp := 5
var resolve := 5
var simulated := true
var duel_mode := false
var raid_mode := false
var raid_seated := true
var duel_counterattack := false
var rival_skin_id := "wayfarer"
var rival_style := "sword"
var rival_variant := ""
var rival_unarmed := false
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
	if OS.has_feature("web"):
		embedded = bool(JavaScriptBridge.eval("new URLSearchParams(window.location.search).has('embed')", true))
	build_scene()
	if embedded:
		bridge_callback = JavaScriptBridge.create_callback(_receive_live_state)
		JavaScriptBridge.get_interface("window").diddyCombatReceive = bridge_callback
		JavaScriptBridge.eval("window.parent.postMessage({source:'diddy-combat',type:'ready'},window.location.origin)", true)
	if not shot_path.is_empty():
		if shot_pose >= 0:
			body.texture = _poses()["action"]
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
	backdrop = Sprite2D.new()
	backdrop.texture = CRYPT
	backdrop.centered = false
	add_child(backdrop)
	# Separate flames and light nodes let the environment move and react.
	for x in [32, 275]:
		dungeon_decor.append(tile(Rect2(70, 269, 13, 30), Vector2(x, 61), 0.8))
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
		dungeon_decor.append(light)
	# Location lights are separate Godot nodes, gently breathing over the art.
	for p in [Vector2(58, 70), Vector2(260, 70)]:
		var gradient := Gradient.new()
		gradient.set_color(0, Color(1.0, 0.65, 0.32, 0.6))
		gradient.set_color(1, Color(1.0, 0.4, 0.15, 0.0))
		var texture := GradientTexture2D.new()
		texture.width = 128
		texture.height = 128
		texture.fill = GradientTexture2D.FILL_RADIAL
		texture.fill_from = Vector2(0.5, 0.5)
		texture.fill_to = Vector2(1.0, 0.5)
		texture.gradient = gradient
		var light := PointLight2D.new()
		light.texture = texture
		light.position = p
		light.energy = 0.35
		add_child(light)
		region_lights.append(light)
	# A drawn grid and particles are separate transparent geometry layers.
	var overlay := SimulationOverlay.new()
	overlay.owner_scene = self
	add_child(overlay)
	hunter_shadow = Polygon2D.new()
	hunter_shadow.polygon = PackedVector2Array([Vector2(-20, 0), Vector2(-12, -3), Vector2(12, -3), Vector2(20, 0), Vector2(12, 3), Vector2(-12, 3)])
	hunter_shadow.color = Color(0.03, 0.02, 0.04, 0.65)
	hunter_shadow.position = Vector2(83, 146)
	add_child(hunter_shadow)
	hunter = Node2D.new()
	hunter.position = Vector2(83, 146)
	add_child(hunter)
	body = Sprite2D.new()
	body.texture = _idle_texture()
	body.hframes = 4
	body.frame = 0
	body.scale = Vector2(1.5, 1.5)
	# Each skin/style aligns its art to the shared foot baseline via its offset.
	body.offset = _poses()["offset"]
	body.position = Vector2(0, -48)
	hunter.add_child(body)
	trinket_gem = Sprite2D.new()
	trinket_gem.position = Vector2(5, -25)
	trinket_gem.visible = false
	hunter.add_child(trinket_gem)
	oil_pet = Sprite2D.new()
	oil_pet.texture = OIL_PET
	oil_pet.position = Vector2(-32, -8)
	oil_pet.visible = false
	hunter.add_child(oil_pet)
	enemy = Sprite2D.new()
	enemy.texture = HOLLOW
	enemy.hframes = 4
	enemy.offset = Vector2(-7, 0)
	enemy.position = Vector2(237, 96)
	enemy.scale = Vector2(1.5, 1.5)
	add_child(enemy)
	raid_status = RaidPartyStatus.new()
	add_child(raid_status)
	set_mode(true)
	if not embedded:
		build_hud()

func build_hud() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)
	panel(ui, Rect2(5, 5, 137, 23), Color("101324"))
	panel(ui, Rect2(178, 5, 137, 23), Color("101324"))
	health_label = label(ui, skins[skin_id]["name"] + ("  ·  PRACTICE HP" if simulated else "  ·  DEMO HP"), Vector2(9, 7), 8, Color("f5dfb8"))
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
	backdrop.texture = SIMULATION if simulated else REGION_BACKDROPS.get(live_region_id, CRYPT)
	backdrop.scale = Vector2(320.0 / backdrop.texture.get_width(), 180.0 / backdrop.texture.get_height())
	for decor in dungeon_decor:
		decor.visible = not simulated and not REGION_BACKDROPS.has(live_region_id)
	for light in region_lights:
		light.visible = not simulated and REGION_BACKDROPS.has(live_region_id)
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
		health_label.text = skins[skin_id]["name"] + ("  ·  PRACTICE HP" if simulated else "  ·  DEMO HP")

func _receive_live_state(args: Array) -> void:
	if args.is_empty(): return
	var payload: Variant = JSON.parse_string(str(args[0]))
	if not payload is Dictionary: return
	_apply_live_state(payload)

func _apply_live_state(payload: Dictionary) -> void:
	var incoming_id: String = str(payload.get("turn_id", ""))
	if acting:
		pending_live_state = payload.duplicate(true)
		if not incoming_id.is_empty() and incoming_id != last_turn_id:
			for queued in pending_live_turns:
				if str(queued.get("turn_id", "")) == incoming_id: return
			pending_live_turns.append(payload.duplicate(true))
		return
	var new_simulated: bool = payload.get("simulated", false)
	var new_enemy: String = payload.get("enemy", "wraith")
	var new_region: String = str(payload.get("region", ""))
	var new_raid: bool = bool(payload.get("raid", false))
	duel_mode = new_region == "duel-colosseum"
	if new_simulated != simulated or new_enemy != live_enemy_id or new_region != live_region_id or new_raid != raid_mode:
		live_region_id = new_region
		live_enemy_id = new_enemy
		raid_mode = new_raid
		set_mode(new_simulated)
		if not simulated and (ANIMATED_ENEMIES.has(live_enemy_id) or LANTERN_ENEMIES.has(live_enemy_id)):
			var visual: Dictionary = LANTERN_ENEMIES.get(live_enemy_id, ANIMATED_ENEMIES.get(live_enemy_id, {}))
			var size: float = visual["scale"]
			enemy.texture = visual["action"]
			enemy.hframes = 4
			enemy.vframes = 1
			enemy.offset = Vector2(-19, 0)
			enemy.scale = Vector2.ONE * size
			enemy.position = Vector2(237, 146 - 32 * size + float(visual.get("ground_offset", 0.0)))
		elif not simulated and LIVE_ENEMIES.has(live_enemy_id):
			enemy.texture = LIVE_ENEMIES[live_enemy_id]
			enemy.hframes = 1
			enemy.vframes = 1
			enemy.offset = Vector2.ZERO
			enemy.position = Vector2(237, 117)
		else:
			enemy.hframes = 4
			enemy.vframes = 1
			enemy.offset = Vector2(-7, 0)
			enemy.position = Vector2(237, 96)
		if duel_mode:
			var rival_poses: Dictionary = _rival_poses()
			enemy.texture = rival_poses["idle"]
			enemy.hframes = 4
			enemy.offset = rival_poses["offset"]
			enemy.flip_h = true
			# The mirrored hunter's artwork extends to the right of its origin.
			# Place its origin inward so both fighters face off near the centre.
			enemy.position = Vector2(200, 98)
		else:
			enemy.flip_h = false
		if raid_mode:
			raid_seated = bool(payload.get("seated", true))
			enemy.texture = CHOEF_IDLE_SHEET
			enemy.hframes = 4
			enemy.vframes = 2
			enemy.frame = 0 if raid_seated else 4
			enemy.offset = Vector2.ZERO
			enemy.scale = Vector2(0.16, 0.16)
			enemy.position = raid_enemy_anchor
			enemy.material = null
			enemy.flip_h = false
	var next_seated := bool(payload.get("seated", true))
	if raid_mode and raid_seated != next_seated:
		raid_seated = next_seated
		enemy.texture = CHOEF_IDLE_SHEET
		enemy.hframes = 4
		enemy.vframes = 2
		enemy.frame = 0 if raid_seated else 4
		if not raid_seated:
			var rise := create_tween().set_parallel(true)
			rise.tween_property(enemy, "position:y", raid_enemy_anchor.y - 5.0, 0.34).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			rise.tween_property(enemy, "scale", Vector2(0.16, 0.16), 0.34).set_trans(Tween.TRANS_QUAD)
		else:
			enemy.scale = Vector2(0.16, 0.16)
			enemy.position = raid_enemy_anchor
	if raid_mode:
		var attack_value: Variant = payload.get("attack", {})
		raid_attack = attack_value.duplicate(true) if attack_value is Dictionary else {}
		body.scale = Vector2(0.84, 0.84)
		body.position.y = -35.0
	else:
		body.scale = Vector2(1.5, 1.5)
		body.position.y = -48.0
	if raid_mode:
		_set_raid_party(payload.get("party", []))
	else:
		_clear_raid_party()
	var style: String = payload.get("style", "sword")
	weapon_variant = str(payload.get("weaponVariant", ""))
	var look: String = str(payload.get("armorLook", "classic"))
	skin_id = _skin_for_look(look)
	_set_look(look if skin_id == "tate" else "classic", str(payload.get("armorMastery", "")), str(payload.get("weaponMastery", "")))
	if duel_mode:
		var rival_look: String = str(payload.get("rivalArmorLook", "wayfarer"))
		rival_skin_id = _skin_for_look(rival_look)
		var requested_style: String = str(payload.get("rivalStyle", "sword"))
		rival_unarmed = requested_style == "unarmed"
		rival_style = "handmagic" if rival_unarmed else requested_style if skins[rival_skin_id]["styles"].has(requested_style) else "sword"
		rival_variant = str(payload.get("rivalWeaponVariant", ""))
		var rival_poses: Dictionary = _rival_poses()
		enemy.texture = rival_poses.get("idle", rival_poses["action"])
		enemy.offset = rival_poses["offset"]
		enemy.frame = 0
		_set_rival_look(rival_look if rival_skin_id == "tate" else "classic", str(payload.get("rivalArmorMastery", "")), str(payload.get("rivalWeaponMastery", "")))
	oil_pet.visible = str(payload.get("pet", "none")) == "oil"
	var charm: String = str(payload.get("trinketIcon", "none"))
	trinket_gem.visible = CHARMS.has(charm)
	if trinket_gem.visible: trinket_gem.texture = CHARMS[charm]
	if not acting:
		unarmed = style == "unarmed"
		if unarmed: style = "handmagic"
		for i in range(weapons.size()):
			if weapons[i].id == style:
				weapon_index = i
				_set_idle()
				break
	var turn_id: String = str(payload.get("turn_id", ""))
	if not turn_id.is_empty() and turn_id != last_turn_id:
		last_turn_id = turn_id
		if payload.get("outcome") == "both" and duel_mode:
			duel_counterattack = true
			_attack()
		elif payload.get("outcome") == "correct": _attack()
		elif payload.get("outcome") == "incorrect": _miss()

func _set_raid_party(party: Array) -> void:
	var signature := JSON.stringify(party)
	if signature == raid_party_signature:
		return
	raid_party_signature = signature
	_clear_raid_party()
	var positions := [Vector2(34, 146), Vector2(70, 146), Vector2(106, 146), Vector2(142, 146)]
	var index := 0
	for member_value in party:
		if not member_value is Dictionary:
			continue
		if index >= positions.size():
			break
		var member: Dictionary = member_value
		if bool(member.get("is_you", false)):
			hunter.position = positions[index]
			# The sprites' opaque boot pixels land several canvas pixels above
			# their origin, so put the contact shadow on the boot baseline rather
			# than at the lower origin used for combat movement.
			hunter_shadow.position = positions[index] + Vector2(0, -7)
			hunter.set_meta("raid_member_id", str(member.get("id", "")))
			hunter_home_x = positions[index].x
			index += 1
			continue
		var look := str(member.get("look", "classic"))
		var member_skin := _skin_for_look(look)
		var member_style := str(member.get("style", "sword"))
		var poses := _poses_for(member_skin, member_style if skins[member_skin]["styles"].has(member_style) else "sword", "")
		var shadow := Polygon2D.new()
		shadow.name = "RaidPartyShadow%d" % index
		# A broad, low ellipse sits directly beneath the boot pixels. The old
		# narrow, opaque lozenge was far below the feet and read as a floating
		# puddle instead of a floor contact shadow.
		shadow.polygon = PackedVector2Array([Vector2(-14, 0), Vector2(-10, -1.5), Vector2(10, -1.5), Vector2(14, 0), Vector2(10, 1.5), Vector2(-10, 1.5)])
		shadow.color = Color(0.025, 0.018, 0.028, 0.5)
		shadow.position = positions[index] + Vector2(0, -7)
		add_child(shadow)
		raid_party_shadows.append(shadow)
		var sprite := Sprite2D.new()
		sprite.name = "RaidPartyHunter%d" % index
		sprite.texture = poses.get("idle", poses["action"])
		sprite.hframes = 4
		sprite.offset = poses["offset"]
		sprite.position = positions[index] + Vector2(0, -35)
		sprite.scale = Vector2.ONE * 0.84
		sprite.set_meta("raid_member_id", str(member.get("id", "")))
		sprite.set_meta("idle_anchor", sprite.position)
		sprite.set_meta("idle_frames", poses.get("idle_frames", [0]))
		add_child(sprite)
		raid_party_sprites.append(sprite)
		index += 1
	raid_status.set_party(party)

func _clear_raid_party() -> void:
	for shadow in raid_party_shadows:
		if is_instance_valid(shadow): shadow.queue_free()
	raid_party_shadows.clear()
	for sprite in raid_party_sprites:
		if is_instance_valid(sprite):
			sprite.queue_free()
	raid_party_sprites.clear()
	if not raid_mode:
		raid_party_signature = ""
		hunter_home_x = 83.0
		hunter.position = Vector2(83, 146)
		hunter_shadow.position = Vector2(83, 146)
		hunter.remove_meta("raid_member_id")

func _skin_for_look(look: String) -> String:
	if look == "norse" or look == "lanternkeeper" or look == "wardplate": return look
	return "ivory" if look == "ivory" else "warden" if look == "spectral" else "harvest" if look == "harvest" else "oracle" if look == "oracle" else "patchwork" if look == "patchwork" else "pilgrim" if look == "pilgrim" else "wayfarer" if look == "wayfarer" else "debugger" if look == "debugger" else "merchant-oracle" if look == "merchant-oracle" else "tate"

func _set_rival_look(look: String, armor_tier: String = "", weapon_tier: String = "") -> void:
	var colors := {"arcane": Color(0.75, 0.65, 1.25), "steel": Color(0.85, 1.0, 1.12), "ember": Color(1.25, 0.8, 0.48)}
	var armor_mastery := _mastery_color(armor_tier)
	var weapon_mastery := _mastery_color(weapon_tier)
	if not colors.has(look) and armor_mastery.a <= 0.0 and weapon_mastery.a <= 0.0:
		enemy.material = null
		return
	var material := ShaderMaterial.new()
	material.shader = LOOK_SHADER
	material.set_shader_parameter("tint", colors.get(look, Color.WHITE))
	material.set_shader_parameter("strength", 0.8 if colors.has(look) else 0.0)
	material.set_shader_parameter("armor_mastery_tint", armor_mastery)
	material.set_shader_parameter("weapon_mastery_tint", weapon_mastery)
	enemy.material = material

func _set_look(look: String, armor_tier: String = "", weapon_tier: String = "") -> void:
	var colors := {"ivory": Color(1.8, 1.7, 1.6), "spectral": Color(0.55, 1.2, 1.05), "harvest": Color(1.35, 0.65, 0.35), "arcane": Color(0.75, 0.65, 1.25), "steel": Color(0.85, 1.0, 1.12), "ember": Color(1.25, 0.8, 0.48)}
	var armor_mastery := _mastery_color(armor_tier)
	var weapon_mastery := _mastery_color(weapon_tier)
	if not colors.has(look) and armor_mastery.a <= 0.0 and weapon_mastery.a <= 0.0:
		body.material = null
		return
	var material := ShaderMaterial.new()
	material.shader = LOOK_SHADER
	material.set_shader_parameter("tint", colors.get(look, Color.WHITE))
	material.set_shader_parameter("strength", 0.8 if colors.has(look) else 0.0)
	material.set_shader_parameter("ivory", look == "ivory")
	material.set_shader_parameter("armor_mastery_tint", armor_mastery)
	material.set_shader_parameter("weapon_mastery_tint", weapon_mastery)
	body.material = material

func _mastery_color(tier: String) -> Color:
	match tier:
		"rare": return Color("bd8dff")
		"legendary": return Color("ffd765")
		"ethereal": return Color("77eaff")
		_: return Color(1, 1, 1, 0)

func _toggle_mode() -> void:
	if acting: return
	set_mode(not simulated)
	_reset()

# Skins are registered separately from reusable combat styles. Reject incomplete
# sets rather than silently rendering a different character for some attacks.
func register_skin(skin: Dictionary) -> bool:
	var error: String = CATALOG.validate_skin(skin)
	if not error.is_empty() or skins.has(skin.get("id")):
		return false
	skins[skin.id] = skin.duplicate(true)
	return true

func select_skin(id: String) -> bool:
	if acting or not skins.has(id): return false
	skin_id = id
	if body:
		_set_idle()
	if health_label:
		health_label.text = skins[id]["name"] + ("  ·  PRACTICE HP" if simulated else "  ·  DEMO HP")
	return true

func _poses() -> Dictionary:
	return _poses_for(skin_id, str(weapons[weapon_index]["id"]), weapon_variant)

func _rival_poses() -> Dictionary:
	return _poses_for(rival_skin_id, rival_style, rival_variant)

func _poses_for(skin: String, style: String, variant_name: String) -> Dictionary:
	var poses: Dictionary = skins[skin]["styles"][style]
	if variant_name == "graveblade" and style == "greatsword" and skin != "norse" and skin != "lanternkeeper" and skin != "wardplate":
		if not variant_pose_cache.has(skin):
			var suffixes := {"tate": "", "ivory": "-ivory", "warden": "-warden-heavy", "harvest": "-harvest-scout", "oracle": "-arcane", "patchwork": "-patchwork", "pilgrim": "-pilgrim", "wayfarer": "-wayfarer", "debugger": "-debugger-v2", "merchant-oracle": "-merchant-oracle"}
			var prefix: String = "res://art/tate%s-graveblade" % suffixes.get(skin, "")
			var action: Texture2D = load(prefix + "-sheet.png")
			var hurt: Texture2D = load(prefix + "-hurt-sheet.png")
			var variant: Dictionary = poses.duplicate()
			if action and hurt:
				variant["action"] = action
				variant["hurt"] = hurt
			variant_pose_cache[skin] = variant
		return variant_pose_cache[skin]
	return poses

func _idle_texture() -> Texture2D:
	var poses := _poses()
	return poses.get("idle", poses["action"])

func _set_idle() -> void:
	body.texture = _idle_texture()
	body.offset = _poses()["offset"]
	body.frame = 0

func _next_weapon() -> void:
	if acting: return
	weapon_index = (weapon_index + 1) % weapons.size()
	weapon_label.text = weapons[weapon_index]["name"]
	_set_idle()

func _magic_projectile() -> void:
	var bolt := Polygon2D.new()
	bolt.name = "SpellBolt"
	bolt.polygon = PackedVector2Array([Vector2(-6, 0), Vector2(-2, -4), Vector2(4, -3), Vector2(7, 0), Vector2(4, 3), Vector2(-2, 4)])
	bolt.color = weapons[weapon_index]["color"]
	if weapons[weapon_index]["id"] == "handmagic":
		bolt.scale = Vector2(1.6, 1.6)
		var core := Polygon2D.new()
		core.polygon = PackedVector2Array([Vector2(-2, 0), Vector2(0, -2), Vector2(3, 0), Vector2(0, 2)])
		core.color = Color("fff2ff")
		bolt.add_child(core)
	bolt.position = hunter.position + _poses()["cast_origin"]
	add_child(bolt)
	var t := create_tween()
	t.tween_property(bolt, "position:x", 222.0, 0.22)
	t.tween_callback(bolt.queue_free)
	t.tween_callback(_enemy_hit)

func _attack() -> void:
	if acting or (not embedded and (resolve <= 0 or hp <= 0)): return
	acting = true
	if status_label: status_label.text = skins[skin_id]["name"] + " ATTACKS"
	if weapons[weapon_index]["kind"] != "sword":
		_weapon_attack()
		return
	body.texture = _poses()["action"]
	var t := create_tween()
	t.tween_callback(func(): body.frame = 1)
	t.tween_interval(0.12)
	t.tween_callback(func(): body.frame = 2)
	t.tween_interval(0.08)
	t.tween_callback(func(): body.texture = _poses()["follow"]; body.frame = 0)
	t.tween_interval(0.08)
	t.tween_callback(func(): body.frame = 1)
	t.tween_property(hunter, "position:x", 140.0, 0.14).set_trans(Tween.TRANS_QUAD)
	t.tween_callback(func(): body.frame = 2)
	t.tween_callback(_enemy_hit)
	t.tween_interval(0.13)
	t.tween_callback(func(): body.frame = 3)
	t.tween_property(hunter, "position:x", hunter_home_x, 0.20)
	t.tween_callback(_finish_turn)

func _weapon_attack() -> void:
	if unarmed:
		# Use empty-handed poses; do not fire a spell or draw a weapon.
		body.texture = _poses()["hurt"]
		body.frame = 3
		var unarmed_tween := create_tween()
		unarmed_tween.tween_interval(0.12)
		unarmed_tween.tween_callback(func(): body.frame = 2)
		unarmed_tween.tween_property(hunter, "position:x", 140.0, 0.18)
		unarmed_tween.tween_callback(_enemy_hit)
		unarmed_tween.tween_interval(0.12)
		unarmed_tween.tween_callback(func(): body.frame = 3)
		unarmed_tween.tween_property(hunter, "position:x", hunter_home_x, 0.2)
		unarmed_tween.tween_callback(_finish_turn)
		return
	body.texture = _poses()["action"]
	body.frame = 1
	var t := create_tween()
	var kind: String = weapons[weapon_index]["kind"]
	var windup := 0.25 if kind == "heavy" else 0.16
	t.tween_interval(windup)
	t.tween_callback(func(): body.frame = 2)
	if kind == "projectile":
		t.tween_callback(_magic_projectile)
		t.tween_interval(0.32)
	else:
		var reach := 105.0 if kind == "whip" else 128.0
		t.tween_property(hunter, "position:x", reach, 0.13 if kind == "whip" else 0.20).set_trans(Tween.TRANS_QUAD)
		t.tween_callback(_enemy_hit)
		t.tween_interval(0.16)
	t.tween_callback(func(): body.frame = 3)
	t.tween_property(hunter, "position:x", hunter_home_x, 0.22)
	t.tween_callback(_finish_turn)

func _enemy_hit() -> void:
	if duel_mode:
		var rival_poses: Dictionary = _rival_poses()
		enemy.texture = rival_poses["hurt"]
		enemy.frame = 0
		var reaction := create_tween()
		for frame in [1, 2, 3]:
			reaction.tween_interval(0.09)
			reaction.tween_callback(func(): enemy.frame = frame)
		reaction.tween_callback(func(): enemy.texture = rival_poses.get("idle", rival_poses["action"]); enemy.frame = 0)
		return
	if raid_mode:
		var original := enemy.position
		var hit := create_tween().set_parallel(true)
		hit.tween_property(enemy, "modulate", Color(2.2, 1.7, 1.2), 0.07)
		hit.tween_property(enemy, "position:x", original.x + 4.0, 0.07)
		hit.chain().tween_property(enemy, "modulate", Color.WHITE, 0.2)
		hit.parallel().tween_property(enemy, "position", original, 0.2)
		return
	if embedded:
		if not simulated and LANTERN_ENEMIES.has(live_enemy_id):
			# These studies have idle and attack poses, not dedicated hurt art.
			# Keep the correct enemy visible and use a short recoil/flash instead.
			var original := enemy.position
			var reaction := create_tween().set_parallel(true)
			reaction.tween_property(enemy, "modulate", Color(2, 2, 2), 0.06)
			reaction.tween_property(enemy, "position:x", original.x + 5.0, 0.06)
			reaction.chain().tween_property(enemy, "modulate", Color.WHITE, 0.22)
			reaction.parallel().tween_property(enemy, "position", original, 0.22)
			return
		if not simulated and ANIMATED_ENEMIES.has(live_enemy_id):
			var visual: Dictionary = ANIMATED_ENEMIES[live_enemy_id]
			enemy.texture = visual["hurt"]
			enemy.frame = 0
			var reaction := create_tween()
			reaction.tween_interval(0.07)
			reaction.tween_callback(func(): enemy.frame = 1)
			reaction.tween_interval(0.09)
			reaction.tween_callback(func(): enemy.frame = 2)
			reaction.tween_interval(0.09)
			reaction.tween_callback(func(): enemy.frame = 3)
			reaction.tween_interval(0.08)
			reaction.tween_callback(func(): enemy.texture = visual["action"]; enemy.frame = 0)
			return
		if not simulated and LIVE_ENEMIES.has(live_enemy_id):
			var flash := create_tween()
			flash.tween_property(enemy, "modulate", Color(2, 2, 2), 0.05)
			flash.tween_property(enemy, "modulate", Color.WHITE, 0.25)
			return
	else:
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
	if acting or (not embedded and (resolve <= 0 or hp <= 0)): return
	acting = true
	if raid_mode:
		var original := raid_enemy_anchor
		var attack_type := str(raid_attack.get("type", "single"))
		var strike_x := 185.0 if attack_type == "aoe" else _raid_target_x() + 20.0
		var t := create_tween().set_parallel(true)
		t.tween_property(enemy, "position:x", strike_x, 0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		if attack_type == "aoe":
			t.tween_property(enemy, "modulate", Color(1.55, 0.72, 0.9), 0.14)
		t.chain().tween_callback(_raid_hunter_hit)
		t.tween_property(enemy, "position", original, 0.27).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(enemy, "modulate", Color.WHITE, 0.24)
		t.tween_callback(_finish_turn)
		return
	if duel_mode:
		enemy.texture = _rival_poses()["hurt"] if rival_unarmed else _rival_poses()["action"]
		if not rival_unarmed and rival_style in ["staff", "handmagic"]:
			_rival_cast()
			return
	if status_label: status_label.text = "HOLLOW STRIKES" if simulated else "MIMIC STRIKES"
	var original := enemy.position
	var t := create_tween()
	t.tween_callback(func(): enemy.frame = 2 if enemy.hframes > 1 else 0)
	t.tween_interval(0.15)
	t.tween_callback(func(): enemy.frame = 3 if enemy.hframes > 1 else 0)
	t.tween_property(enemy, "position:x", 150.0 if duel_mode else 196.0, 0.25)
	t.tween_callback(_hunter_hit)
	t.tween_property(enemy, "position", original, 0.25)
	t.tween_callback(func():
		enemy.frame = 0
		if duel_mode:
			var rival_poses: Dictionary = _rival_poses()
			enemy.texture = rival_poses.get("idle", rival_poses["action"])
	)
	t.tween_interval(0.2)
	t.tween_callback(_finish_turn)

func _rival_cast() -> void:
	var bolt := Polygon2D.new()
	bolt.polygon = PackedVector2Array([Vector2(-7, 0), Vector2(-3, -4), Vector2(3, -3), Vector2(6, 0), Vector2(3, 3), Vector2(-3, 4)])
	bolt.color = Color("8ceeff") if rival_style == "staff" else Color("d188ff")
	bolt.position = enemy.position + Vector2(-30, 0)
	bolt.visible = false
	add_child(bolt)
	var t := create_tween()
	t.tween_callback(func(): enemy.frame = 1)
	t.tween_interval(0.15)
	t.tween_callback(func(): enemy.frame = 2; bolt.visible = true)
	t.tween_property(bolt, "position:x", 110.0, 0.25)
	t.tween_callback(bolt.queue_free)
	t.tween_callback(_hunter_hit)
	t.tween_interval(0.25)
	t.tween_callback(func():
		var rival_poses: Dictionary = _rival_poses()
		enemy.texture = rival_poses.get("idle", rival_poses["action"])
		enemy.frame = 0
	)
	t.tween_interval(0.2)
	t.tween_callback(_finish_turn)

func _hunter_hit() -> void:
	if not embedded:
		hp = maxi(0, hp - 1)
		hp_bar.size.x = 128.0 * hp / 5.0
	body.texture = _poses()["hurt"]
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
	if duel_mode and duel_counterattack:
		duel_counterattack = false
		_miss()
		return
	if status_label: status_label.text = "FOE BROKEN" if resolve == 0 else ("HUNTER DOWN" if hp == 0 else "YOUR TURN")
	if embedded and not pending_live_turns.is_empty():
		_apply_live_state(pending_live_turns.pop_front())
	elif embedded and not pending_live_state.is_empty():
		var latest := pending_live_state
		pending_live_state = {}
		_apply_live_state(latest)

func _reset() -> void:
	if acting: return
	hp = 5
	resolve = 5
	hp_bar.size.x = 128
	resolve_bar.size.x = 128
	status_label.text = "YOUR TURN"

func _process(delta: float) -> void:
	elapsed += delta
	if oil_pet and oil_pet.visible:
		oil_pet.position.y = -8.0 + sin(elapsed * 3.0) * 1.5
	for light in region_lights:
		light.energy = 0.32 + 0.04 * sin(elapsed * 2.4 + light.position.x)
	if not acting and body and enemy and shot_pose < 0:
		var idle_cycle: Array = _poses().get("idle_frames", [0])
		body.frame = idle_cycle[int(elapsed * 4.0) % idle_cycle.size()]
		if raid_mode:
			body.position.y = -35.0 + sin(elapsed * 3.0) * 0.7
		elif idle_cycle.size() == 1:
			body.position.y = -48.0 + sin(elapsed * 3.0) * 0.7
		else:
			body.position.y = -48.0
		if duel_mode:
			var rival_cycle: Array = _rival_poses().get("idle_frames", [0])
			enemy.frame = rival_cycle[int(elapsed * 4.0) % rival_cycle.size()]
		elif raid_mode:
			var boss_idle_frame: int = int(elapsed * 3.2) % 4
			enemy.frame = (0 if raid_seated else 4) + boss_idle_frame
			enemy.position.y = raid_enemy_anchor.y + (sin(elapsed * 2.2) * 0.75 if not acting else 0.0)
		else:
			enemy.frame = int(elapsed * 3.0) % 2 if enemy.hframes > 1 else 0
		for sprite_index in range(raid_party_sprites.size()):
			var sprite: Sprite2D = raid_party_sprites[sprite_index]
			var party_idle: Array = sprite.get_meta("idle_frames", [0])
			sprite.frame = party_idle[int(elapsed * 3.5) % party_idle.size()]
			var anchor: Vector2 = sprite.get_meta("idle_anchor", sprite.position)
			sprite.position.y = anchor.y + sin(elapsed * 3.1 + float(sprite_index) * 0.8) * 0.65
	queue_redraw()

func _raid_target_x() -> float:
	var targets: Array = raid_attack.get("target_players", [])
	if targets.is_empty():
		return hunter_home_x
	for member_index in range(mini(raid_status.party.size(), 4)):
		var member: Dictionary = raid_status.party[member_index]
		if str(member.get("id", "")) == str(targets[0]):
			return [34.0, 70.0, 106.0, 142.0][member_index]
	return hunter_home_x

func _raid_hunter_hit() -> void:
	var targets: Array = raid_attack.get("target_players", [])
	for sprite in raid_party_sprites:
		if not targets.has(str(sprite.get_meta("raid_member_id", ""))):
			continue
		var original := sprite.position
		var hit := create_tween().set_parallel(true)
		hit.tween_property(sprite, "modulate", Color(2.0, 0.72, 0.72), 0.08)
		hit.tween_property(sprite, "position:x", original.x - 3.0, 0.08)
		hit.chain().tween_property(sprite, "modulate", Color.WHITE, 0.2)
		hit.parallel().tween_property(sprite, "position", original, 0.2)
	if targets.has(str(hunter.get_meta("raid_member_id", ""))):
		var original_hunter := hunter.position
		var hit_hunter := create_tween().set_parallel(true)
		hit_hunter.tween_property(body, "modulate", Color(2.0, 0.72, 0.72), 0.08)
		hit_hunter.tween_property(hunter, "position:x", original_hunter.x - 3.0, 0.08)
		hit_hunter.chain().tween_property(body, "modulate", Color.WHITE, 0.2)
		hit_hunter.parallel().tween_property(hunter, "position", original_hunter, 0.2)

class RaidPartyStatus extends Node2D:
	var party: Array = []
	func set_party(next_party: Array) -> void:
		party = next_party.duplicate(true)

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
