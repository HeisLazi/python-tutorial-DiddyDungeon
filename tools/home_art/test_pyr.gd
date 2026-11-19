extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var home: Node2D = load("res://scripts/home.gd").new()
	root.add_child(home)
	home._configure_pyr_sheet(99)
	assert(not home.pyr_custom_sheet)
	assert(home.pyr.texture == home.TILES)
	if ResourceLoader.exists("res://art/pyr_stage_2.png"):
		for stage in range(1, 5):
			home._configure_pyr_sheet(stage)
			assert(home.pyr_custom_sheet)
			assert(home.pyr.texture.get_width() == 192)
		home._configure_pyr_sheet(2)
	else:
		var image := Image.create_empty(192, 32, false, Image.FORMAT_RGBA8)
		home.pyr.texture = ImageTexture.create_from_image(image)
		home.pyr_custom_sheet = true
	home.clock = 0.0
	home.pyr_pos = home.pos + Vector2(28, -10)
	home.pyr_pose = 2
	home.pyr_pose_time = 1.0
	home._wander_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(128, 0, 32, 32))
	home.pyr_pose = 3
	home._wander_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(160, 0, 32, 32))
	home.pyr_pose_time = 0.0
	home.pyr_pos = Vector2.ZERO
	home.pyr_target = Vector2(100, 100)
	home.pyr_wander_wait = 10.0
	home._wander_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(64, 0, 32, 32))
	home.pyr_target = home.pyr_pos
	home.pyr_wander_wait = 10.0
	home._wander_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(0, 0, 32, 32))
	# Pyr is a room character: moving the hunter does not drag Pyr along.
	home.pyr_pose_time = 0.0
	home.pyr_pos = Vector2(210, 150)
	home.pyr_target = home.pyr_pos
	home.pyr_wander_wait = 10.0
	home.pos = Vector2(30, 140)
	home._wander_pyr(0.1)
	assert(home.pyr_pos == Vector2(210, 150))
	# The interaction prompt targets Pyr directly inside the den.
	home.room_id = "den"
	home.pos = home.pyr_pos + Vector2(10, 0)
	home._update_prompt(0.0)
	assert(home.near.get("id") == "pyr")
	home.free()
	print("Pyr fallback, pose and independent interaction contract passed")
	quit()
