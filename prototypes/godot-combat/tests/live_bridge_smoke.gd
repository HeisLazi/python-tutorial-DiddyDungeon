extends SceneTree

func _initialize() -> void:
	call_deferred("run_checks")

func require(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		quit(1)
		assert(condition, message)

func run_checks() -> void:
	var scene: Node = load("res://main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.embedded = true
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword"})
	require(scene.enemy.hframes == 1 and scene.enemy.texture.resource_path.ends_with("live-wraith.png"), "Dungeon enemy identity missing")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "hit", "outcome": "correct"})
	require(scene.acting and scene.last_turn_id == "hit", "Live hit did not start")
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "miss", "outcome": "incorrect"})
	scene._apply_live_state({"simulated": false, "enemy": "wraith", "style": "sword", "turn_id": "miss", "outcome": "incorrect"})
	require(scene.pending_live_turns.size() == 1, "Repeated turn was not deduplicated")
	await create_timer(1.9).timeout
	require(not scene.acting and scene.last_turn_id == "miss", "Queued live counterattack did not complete")
	require(scene.hp == 5 and scene.resolve == 5, "Live scene changed demo health")
	scene._apply_live_state({"simulated": true, "enemy": "wraith", "style": "handmagic"})
	require(scene.enemy.hframes == 4 and scene.enemy.texture.resource_path.ends_with("hollow-action-sheet.png"), "Simulation did not restore hollow")
	require(scene.weapon_index == 4, "Live weapon style did not change")
	print("PASS: live enemy identity, turn queue, simulation and presentation-only state")
	quit(0)
