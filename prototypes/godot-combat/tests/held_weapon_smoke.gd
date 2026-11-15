extends SceneTree
## Held-weapon overlays: the weapon-less base plus a per-weapon strip must follow the hunter, and anything
## without a complete set of strips must keep its baked weapon.

var failures := 0

func _initialize() -> void:
	call_deferred("run_checks")

func require(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1

func overlay_path(scene: Node) -> String:
	scene._sync_held()
	return scene.held.texture.resource_path if scene.held.visible and scene.held.texture else ""

func run_checks() -> void:
	var scene: Node = load("res://main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.embedded = true
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	await process_frame
	require(scene.skin_id == "tate", "Classic look should be Tate")
	require(scene.body.texture.resource_path.contains("art/held/base-tate-sword-idle"), "Overlay weapon should use the weapon-less idle base: " + scene.body.texture.resource_path)
	var cutter := overlay_path(scene)
	require(cutter.ends_with("bj-the-house-cutter-tate-sword-idle.png"), "House Cutter idle strip missing: " + cutter)
	require(scene.held.texture.get_size() == scene.body.texture.get_size(), "Strip must match the base sheet size")
	require(scene.held.frame == scene.body.frame and scene.held.offset == scene.body.offset and scene.held.scale == scene.body.scale, "Strip must mirror the hunter's frame, offset and scale")

	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "lv-01"})
	var other := overlay_path(scene)
	require(other.ends_with("lv-01-tate-sword-idle.png") and other != cutter, "Different weapons must show different strips")

	# The strip follows every sheet the sword style uses during a swing and a hurt.
	var seen := {}
	scene._attack()
	for step in range(30):
		await create_timer(0.04).timeout
		var path := overlay_path(scene)
		require(path != "", "Overlay vanished mid-attack at step %d (body %s)" % [step, scene.body.texture.resource_path])
		var key: String = scene.body.texture.resource_path.get_file().replace("base-tate-sword-", "").replace("-sheet.png", "")
		require(path.ends_with("-tate-sword-%s.png" % key), "Strip %s does not match body sheet %s" % [path, key])
		require(scene.held.frame == scene.body.frame, "Strip frame lags the body")
		seen[key] = true
	require(seen.has("action") and seen.has("follow"), "Attack should have used both the action and follow sheets: " + str(seen.keys()))
	await create_timer(1.0).timeout
	scene._miss()
	var hurt_seen := false
	for step in range(60):
		await create_timer(0.04).timeout
		var path := overlay_path(scene)
		if scene.body.texture.resource_path.contains("-hurt-"):
			hurt_seen = true
			require(path.ends_with("-tate-sword-hurt.png"), "Hurt pose should carry the strip: " + path)
			break
	require(hurt_seen, "The counterattack never showed the hurt sheet")
	await create_timer(1.2).timeout

	# Fallbacks keep the baked weapon and hide the overlay.
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "not-a-weapon"})
	require(overlay_path(scene) == "" and scene.body.texture.resource_path.ends_with("tate-idle-sheet.png"), "Unknown weapon should keep the baked sheet")
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	require(overlay_path(scene) == "" and scene.body.texture.resource_path.ends_with("tate-greatsword-sheet.png"), "A weapon with no greatsword strips should keep the baked greatsword")
	# Every outfit carries every sword-style weapon as an overlay on its own weapon-less base.
	var looks := {"classic": "tate", "ivory": "ivory", "spectral": "warden", "harvest": "harvest", "oracle": "oracle", "patchwork": "patchwork", "pilgrim": "pilgrim", "wayfarer": "wayfarer", "debugger": "debugger", "merchant-oracle": "merchant-oracle", "norse": "norse", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate"}
	var swords := ["lv-01", "lv-02", "lv-05", "bj-card-edge-dagger", "bj-ace-of-spades-blade", "bj-the-house-cutter", "dc-lantern-lit-shortsword", "merchant-vigil-sabre", "campaign-dungeon-syntax-sabre", "campaign-dungeon-loopblade", "campaign-dungeon-hollow-fang"]
	for look in looks:
		for weapon in swords:
			scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": look, "weaponId": weapon})
			var shown := overlay_path(scene)
			require(scene.skin_id == looks[look] and shown.ends_with("%s-%s-sword-idle.png" % [weapon, looks[look]]), "%s / %s should draw its overlay, got '%s' on skin %s" % [look, weapon, shown, scene.skin_id])
			require(scene.body.texture.resource_path.contains("base-%s-sword-idle" % looks[look]), "%s should stand on its weapon-less base" % look)
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "ivory", "weaponId": "not-a-weapon"})
	require(overlay_path(scene) == "" and scene.skin_id == "ivory", "An unknown weapon should keep the baked sword on any outfit")
	scene._apply_live_state({"simulated": true, "style": "staff", "armorLook": "classic", "weaponId": "bj-the-house-cutter", "weaponVariant": "dawn-lantern"})
	require(overlay_path(scene) == "", "Dawn Lantern must never stack an overlay on its baked art")
	scene._apply_live_state({"simulated": true, "style": "unarmed", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	require(overlay_path(scene) == "", "Bare hands must not draw a weapon")
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic"})
	require(overlay_path(scene) == "", "No weapon id means the baked sword")

	print("held_weapon_smoke: %d failure(s)" % failures)
	quit(1 if failures > 0 else 0)
