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
		home._configure_pyr_sheet(2)
		assert(home.pyr_custom_sheet)
		assert(home.pyr.texture.get_width() == 192)
	else:
		var image := Image.create_empty(192, 32, false, Image.FORMAT_RGBA8)
		home.pyr.texture = ImageTexture.create_from_image(image)
		home.pyr_custom_sheet = true
	home.clock = 0.0
	home.pyr_pos = home.pos + Vector2(18, -10)
	home.pyr_pose = 2
	home.pyr_pose_time = 1.0
	home._follow_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(128, 0, 32, 32))
	home.pyr_pose = 3
	home._follow_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(160, 0, 32, 32))
	home.pyr_pose_time = 0.0
	home.pyr_pos = Vector2.ZERO
	home._follow_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(64, 0, 32, 32))
	home.pyr_pos = home.pos + Vector2(18, -10)
	home._follow_pyr(0.0)
	assert(home.pyr.region_rect == Rect2(0, 0, 32, 32))
	home.free()
	print("Pyr fallback and six-frame pose contract passed")
	quit()
