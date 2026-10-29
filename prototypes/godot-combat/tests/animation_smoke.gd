extends SceneTree

func _initialize() -> void:
	call_deferred("run_checks")

func sample(scene: Node, duration: float) -> Dictionary:
	var seen := {"hunter": {}, "enemy": {}}
	var steps := int(duration / 0.04)
	for i in range(steps):
		await create_timer(0.04).timeout
		var hunter_key: String = scene.body.texture.resource_path.get_file() + ":" + str(scene.body.frame)
		var enemy_key: String = scene.enemy.texture.resource_path.get_file() + ":" + str(scene.enemy.frame)
		seen.hunter[hunter_key] = true
		seen.enemy[enemy_key] = true
	return seen

func require(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		quit(1)
		assert(condition, message)

func run_checks() -> void:
	var scene: Node = load("res://main.tscn").instantiate()
	var early: Dictionary = scene.CATALOG.tate().duplicate(true)
	early.id = "early"
	early.name = "EARLY"
	early.styles.sword.offset = Vector2(8, 0)
	early.styles.handmagic.cast_origin = Vector2(25, -36)
	require(scene.register_skin(early) and scene.select_skin("early"), "Pre-ready selection failed")
	root.add_child(scene)
	await process_frame
	require(scene.health_label.text.begins_with("EARLY") and scene.body.offset == Vector2(8, 0), "Pre-ready skin visuals not applied")
	# Casting origin belongs to the selected skin and style, measured from hunter root.
	scene.weapon_index = 4
	scene._set_idle()
	scene._magic_projectile()
	var bolt: Node2D = scene.get_node("SpellBolt")
	require(bolt.position == scene.hunter.position + Vector2(25, -36), "Projectile did not use skin cast origin")
	await create_timer(0.4).timeout
	scene._reset()
	scene.weapon_index = 0
	require(scene.select_skin("tate"), "Could not select Tate after initialization")
	require(scene.backdrop.texture.resource_path.ends_with("simulation.png"), "Simulation backdrop missing")
	for decor in scene.dungeon_decor:
		require(not decor.visible, "Dungeon lighting leaked into simulation")
	var idle: Dictionary = await sample(scene, 1.0)
	require(idle.hunter.size() >= 3, "Tate idle poses did not advance")
	require(idle.enemy.size() >= 2, "Hollow idle poses did not advance")
	scene._attack()
	var hit: Dictionary = await sample(scene, 1.2)
	require(scene.resolve == 4 and not scene.acting, "Sword hit did not complete")
	require(hit.hunter.has("tate-sword-v2-sheet.png:1") and hit.hunter.has("tate-followthrough-sheet.png:2"), "Sword poses missing")
	require(hit.enemy.has("hollow-hurt-sheet.png:2"), "Hollow hit reaction missing")
	scene._miss()
	var miss: Dictionary = await sample(scene, 1.4)
	require(scene.hp == 4 and not scene.acting, "Hollow counterattack did not complete")
	require(miss.hunter.has("tate-hurt-sheet.png:2"), "Tate hit reaction missing")
	require(miss.enemy.has("hollow-action-sheet.png:3"), "Hollow strike missing")
	scene._toggle_mode()
	require(not scene.simulated and scene.hp == 5 and scene.resolve == 5, "Dungeon mode did not reset")
	require(scene.backdrop.texture.resource_path.ends_with("crypt.png"), "Dungeon backdrop missing")
	for decor in scene.dungeon_decor:
		require(decor.visible, "Dungeon decor not restored")
	scene._attack()
	var mimic_hit: Dictionary = await sample(scene, 1.2)
	require(mimic_hit.enemy.has("mimic-hurt-sheet.png:2"), "Mimic hit reaction missing")
	scene._miss()
	var mimic_miss: Dictionary = await sample(scene, 1.4)
	require(mimic_miss.enemy.has("mimic-action-sheet.png:3"), "Mimic attack pose missing")
	for weapon in ["staff", "whip", "greatsword", "handmagic"]:
		scene._reset()
		scene._next_weapon()
		require(scene.weapon_label.text.to_lower().replace(" ", "") == weapon, "Weapon selection failed: " + weapon)
		scene._attack()
		var action: Dictionary = await sample(scene, 1.4)
		require(scene.resolve == 4 and not scene.acting, weapon + " attack did not complete")
		require(action.hunter.has("tate-" + weapon + "-sheet.png:1") and action.hunter.has("tate-" + weapon + "-sheet.png:2"), weapon + " attack poses missing")
		scene._miss()
		var reaction: Dictionary = await sample(scene, 1.4)
		require(scene.hp == 4 and not scene.acting, weapon + " counter did not complete")
		require(reaction.hunter.has("tate-" + weapon + "-hurt-sheet.png:2"), weapon + " hurt pose missing")
	# A second skin uses distinct texture objects so this verifies actual skin
	# lookup through both attack and hurt, not merely the label change.
	var fixture: Dictionary = scene.CATALOG.tate().duplicate(true)
	fixture.id = "fixture"
	fixture.name = "FIXTURE"
	for id in fixture.styles:
		for key in ["action", "hurt", "idle", "follow"]:
			if fixture.styles[id].has(key):
				var source: Texture2D = fixture.styles[id][key]
				fixture.styles[id][key] = ImageTexture.create_from_image(source.get_image())
	var missing_origin: Dictionary = fixture.duplicate(true)
	missing_origin.id = "missing_origin"
	missing_origin.styles.staff.erase("cast_origin")
	require(not scene.register_skin(missing_origin), "Projectile style requires a cast origin")
	var invalid: Dictionary = fixture.duplicate(true)
	invalid.id = "invalid"
	invalid.styles.erase("whip")
	require(not scene.register_skin(invalid), "Incomplete skin should be rejected")
	require(scene.register_skin(fixture) and not scene.register_skin(fixture), "Skin registration/duplicate check failed")
	require(scene.select_skin("fixture") and scene.health_label.text.begins_with("FIXTURE"), "Skin switch failed")
	require(not scene.select_skin("missing") and scene.skin_id == "fixture", "Unknown skin changed selection")
	scene._reset()
	scene._next_weapon() # sword
	scene._next_weapon() # staff
	require(scene.body.texture == scene.skins.fixture.styles.staff.action, "Selected skin idle missing")
	scene._attack()
	require(not scene.select_skin("tate"), "Skin must not change mid-turn")
	require(scene.body.texture == scene.skins.fixture.styles.staff.action, "Selected skin attack missing")
	await sample(scene, 1.4)
	scene._miss()
	await create_timer(0.43).timeout
	require(scene.body.texture == scene.skins.fixture.styles.staff.hurt, "Selected skin hurt missing")
	await sample(scene, 1.0)
	require(scene.select_skin("tate"), "Could not restore Tate")
	print("PASS: idle, five weapons, skin selection, hit reactions, counters and both modes")
	quit(0)
