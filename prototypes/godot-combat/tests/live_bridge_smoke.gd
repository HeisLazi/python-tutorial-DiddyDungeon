extends SceneTree

var failures := 0

func _initialize() -> void:
	call_deferred("run_checks")

func require(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1

func run_checks() -> void:
	var scene: Node = load("res://main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.embedded = true
	scene._apply_live_state({"simulated": false, "region": "basics", "enemy": "wraith", "style": "sword"})
	require(scene.backdrop.texture.resource_path.ends_with("basics-village.png"), "Basics Village backdrop missing")
	scene._apply_live_state({"simulated": false, "region": "collections", "enemy": "wraith", "style": "sword"})
	require(scene.backdrop.texture.resource_path.ends_with("collection-caves.png"), "Collection Caves backdrop missing")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword"})
	require(scene.enemy.hframes == 4 and scene.enemy.texture.resource_path.ends_with("wraith-v2-sheet.png"), "Dungeon enemy identity missing")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "hit", "outcome": "correct"})
	require(scene.acting and scene.last_turn_id == "hit", "Live hit did not start")
	await create_timer(0.43).timeout
	require(scene.enemy.texture.resource_path.ends_with("wraith-v2-hurt-sheet.png"), "Wraith hurt animation missing")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "miss", "outcome": "incorrect"})
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "miss", "outcome": "incorrect"})
	require(scene.pending_live_turns.size() == 1, "Repeated turn was not deduplicated")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "whip"})
	await create_timer(1.9).timeout
	require(not scene.acting and scene.last_turn_id == "miss", "Queued live counterattack did not complete")
	require(scene.hp == 5 and scene.resolve == 5, "Live scene changed demo health")
	require(scene.weapons[scene.weapon_index].id == "whip", "Style change during an action was lost")
	scene._apply_live_state({"simulated": true, "enemy": "wraith", "style": "handmagic"})
	require(scene.enemy.hframes == 4 and scene.enemy.texture.resource_path.ends_with("hollow-action-sheet.png"), "Simulation did not restore hollow")
	require(scene.weapon_index == 4, "Live weapon style did not change")
	scene._apply_live_state({"simulated": true, "enemy": "wraith", "style": "unarmed", "turn_id": "bare-hit", "outcome": "correct"})
	require(scene.unarmed and scene.acting, "Unarmed attack did not begin")
	require(scene.body.texture.resource_path.ends_with("tate-handmagic-hurt-sheet.png"), "Unarmed pose missing")
	await create_timer(1.0).timeout
	require(not scene.acting and not scene.has_node("SpellBolt"), "Unarmed attack fired a spell or did not finish")
	scene._apply_live_state({"simulated": true, "style": "oil", "armorLook": "ivory", "pet": "oil"})
	require(scene.skin_id == "ivory" and scene.oil_pet.visible and scene.body.texture.resource_path.ends_with("tate-ivory-oil-sheet.png"), "Ivory suit and companion missing")
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "spectral", "pet": "none"})
	require(scene.skin_id == "warden" and not scene.oil_pet.visible and scene.body.texture.resource_path.ends_with("tate-warden-heavy-greatsword-sheet.png"), "Warden armour or pet removal missing")
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "pet": "none"})
	require(scene.skin_id == "tate" and scene.body.material == null, "Classic appearance was not restored")
	for look in {"ivory": "ivory", "spectral": "warden", "harvest": "harvest"}:
		var skin: String = {"ivory": "ivory", "spectral": "warden", "harvest": "harvest"}[look]
		var prefix: String = {"ivory": "ivory", "spectral": "warden-heavy", "harvest": "harvest-scout"}[look]
		require(scene.CATALOG.validate_skin(scene.skins[skin]).is_empty(), "Invalid outfit: " + skin)
		for style in scene.CATALOG.STYLES:
			scene._apply_live_state({"simulated": true, "style": style.id, "armorLook": look, "trinketIcon": "pink-cap"})
			require(scene.skin_id == skin and not scene.trinket_gem.visible, "Outfit not selected or a trinket is drawn: " + skin + "/" + style.id)
			require(scene._poses().action.resource_path.contains("tate-" + prefix + "-" + style.id) and scene._poses().hurt.resource_path.contains("tate-" + prefix + "-" + style.id), "Wrong outfit frames: " + skin + "/" + style.id)
	for look in {"debugger": "debugger-v2", "merchant-oracle": "merchant-oracle", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate"}:
		var prefix: String = {"debugger": "debugger-v2", "merchant-oracle": "merchant-oracle", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate"}[look]
		require(scene.CATALOG.validate_skin(scene.skins[look]).is_empty(), "Invalid outfit: " + look)
		for style in scene.CATALOG.STYLES:
			scene._apply_live_state({"simulated": true, "style": style.id, "armorLook": look})
			require(scene.skin_id == look, "Outfit not selected: " + look)
			require(scene._poses().action.resource_path.contains("tate-" + prefix + "-" + style.id) and scene._poses().hurt.resource_path.contains("tate-" + prefix + "-" + style.id), "Wrong outfit frames: " + look + "/" + style.id)
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "trinketIcon": "none"})
	require(not scene.trinket_gem.visible, "Unequipped trinket still visible")
	# No trinket is ever drawn in the scene, whatever the save says is equipped.
	for slug in scene.CHARM_REGISTRY.SLUGS:
		scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "trinketIcon": slug})
		require(not scene.trinket_gem.visible, "Trinket %s is drawn in the combat scene" % slug)
	if failures:
		quit(1)
	else:
		print("PASS: live enemy identity, turn queue, simulation, unarmed and presentation-only state")
		quit(0)
