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
	root.add_child(scene)
	await process_frame
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
	scene._attack()
	var mimic_hit: Dictionary = await sample(scene, 1.2)
	require(mimic_hit.enemy.has("mimic-hurt-sheet.png:2"), "Mimic hit reaction missing")
	scene._miss()
	var mimic_miss: Dictionary = await sample(scene, 1.4)
	require(mimic_miss.enemy.has("mimic-action-sheet.png:3"), "Mimic attack pose missing")
	for weapon in ["staff", "whip", "greatsword"]:
		scene._reset()
		scene._next_weapon()
		require(scene.weapon_label.text.to_lower() == weapon, "Weapon selection failed: " + weapon)
		scene._attack()
		var action: Dictionary = await sample(scene, 1.4)
		require(scene.resolve == 4 and not scene.acting, weapon + " attack did not complete")
		require(action.hunter.has("tate-" + weapon + "-sheet.png:1") and action.hunter.has("tate-" + weapon + "-sheet.png:2"), weapon + " attack poses missing")
		scene._miss()
		var reaction: Dictionary = await sample(scene, 1.4)
		require(scene.hp == 4 and not scene.acting, weapon + " counter did not complete")
		require(reaction.hunter.has("tate-" + weapon + "-hurt-sheet.png:2"), weapon + " hurt pose missing")
	print("PASS: idle, four weapons, hit reactions, counters and both modes")
	quit(0)
