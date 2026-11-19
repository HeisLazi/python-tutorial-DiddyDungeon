extends SceneTree
## Windowed probe (needs a display): plays a real attack and saves frames, reporting what the held overlay does.
func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	var style := "scythe"
	var weapon := "hunter-sparring-scythe"
	var look := "classic"
	for a in args:
		if a.begins_with("--style="): style = a.trim_prefix("--style=")
		if a.begins_with("--weapon="): weapon = a.trim_prefix("--weapon=")
		if a.begins_with("--look="): look = a.trim_prefix("--look=")
	var scene: Node = load("res://main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.embedded = true
	scene._apply_live_state({"simulated": true, "style": style, "armorLook": look, "weaponId": weapon})
	for i in range(6): await process_frame
	scene._attack()
	var step := 0
	for i in range(70):
		await RenderingServer.frame_post_draw
		if i % 5 == 0:
			var shown: String = scene.held.texture.resource_path.get_file() if scene.held.texture else "-"
			print("f%02d body=%s fr=%d | held vis=%s fr=%d tex=%s pos=%s/%s" % [i, scene.body.texture.resource_path.get_file(), scene.body.frame, str(scene.held.visible), scene.held.frame, shown, str(scene.held.position), str(scene.body.position)])
			root.get_viewport().get_texture().get_image().save_png("res://shots/probe-%s-%02d.png" % [style, step])
			step += 1
	quit(0)
