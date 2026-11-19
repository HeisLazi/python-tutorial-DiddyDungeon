extends SceneTree

func _initialize() -> void:
	call_deferred("run_checks")

func check(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		quit(1)
		assert(condition, message)

func run_checks() -> void:
	var scene: Node = load("res://scenes/main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	for look in {"ivory": "ivory", "spectral": "warden", "harvest": "harvest"}:
		var costume: String = {"ivory": "ivory", "spectral": "warden", "harvest": "harvest"}[look]
		scene.state["armorLook"] = look
		scene.state["pet"] = "oil" if look == "ivory" else "none"
		scene._apply_state()
		for direction in {"up": "back", "down": "front", "left": "side", "right": "side"}:
			scene.facing = direction
			scene.anim_t = 2.0
			scene._refresh_hunter()
			var expected: String = "hunter_%s_%s.png" % [costume, {"up": "back", "down": "front", "left": "side", "right": "side"}[direction]]
			check(scene.body_sprite.texture.resource_path.ends_with(expected), "Wrong Home outfit: " + look + "/" + direction)
			check(scene.body_sprite.region_rect.position.x == 76.0, "Walk frame did not advance")
			check(scene.body_sprite.flip_h == (direction == "right"), "Side direction was not mirrored")
		check(scene.oil_pet.visible == (look == "ivory"), "Companion visibility did not follow outfit")
	scene.state["armorLook"] = "classic"
	scene.state["pet"] = "none"
	scene._apply_state()
	scene.facing = "down"
	scene._refresh_hunter()
	check(scene.body_sprite.texture.resource_path.ends_with("hunter_front.png") and not scene.oil_pet.visible, "Classic outfit was not restored")
	print("PASS: Home outfit directions, walking, companion and classic restoration")
	quit(0)
