extends SceneTree
## Held weapons: a weapon-less base plus a per-weapon strip are drawn into one sheet, and anything without a complete
## set of strips must keep its baked weapon. A composed sheet is an ImageTexture named `<weapon>-<skin>-<style>-<key>`
## with no resource path; a baked sheet has a path and no name.

var failures := 0

func _initialize() -> void:
	call_deferred("run_checks")

func require(condition: bool, message: String) -> void:
	if not condition:
		push_error(message)
		failures += 1

## The name of the held-weapon sheet the hunter is drawn from right now, or "" when the weapon is baked into the art.
func held_name(scene: Node) -> String:
	var texture: Texture2D = scene.body.texture
	return texture.resource_name if texture and texture.resource_path.is_empty() else ""

func rival_name(scene: Node) -> String:
	var texture: Texture2D = scene.enemy.texture
	return texture.resource_name if texture and texture.resource_path.is_empty() else ""

func run_checks() -> void:
	var scene: Node = load("res://main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.embedded = true
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	await process_frame
	require(scene.skin_id == "tate", "Classic look should be Tate")
	var cutter := held_name(scene)
	require(cutter == "bj-the-house-cutter-tate-sword-idle", "House Cutter should draw from its own idle sheet: '%s'" % cutter)

	# The composed sheet is the weapon-less base with the weapon drawn into it: same size, every weapon pixel present.
	var base: Texture2D = load("res://art/held/base-tate-sword-idle-sheet.png")
	var strip: Texture2D = load("res://art/held/bj-the-house-cutter-tate-sword-idle.png")
	var composed: Image = scene.body.texture.get_image()
	var base_image: Image = base.get_image()
	var strip_image: Image = strip.get_image()
	require(composed.get_size() == base_image.get_size(), "A composed sheet must keep the base sheet's size")
	var weapon_pixels := 0
	var missing := 0
	for y in range(strip_image.get_height()):
		for x in range(strip_image.get_width()):
			if strip_image.get_pixel(x, y).a > 0.9:
				weapon_pixels += 1
				if composed.get_pixel(x, y).a < 0.9:
					missing += 1
	require(weapon_pixels > 0, "The House Cutter strip should not be empty")
	require(missing == 0, "%d weapon pixels are missing from the composed sheet" % missing)

	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "lv-01"})
	var other := held_name(scene)
	require(other == "lv-01-tate-sword-idle" and other != cutter, "Different weapons must show different sheets: " + other)
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	require(scene.body.texture == scene._poses()["idle"], "The body should show the cached composed sheet, not a fresh copy")

	# The sheet follows every texture the sword style uses during a swing and a hurt. Because the weapon is in the
	# sheet, the hunter and the weapon cannot disagree about the frame.
	var seen := {}
	scene._attack()
	for step in range(30):
		await create_timer(0.04).timeout
		var shown := held_name(scene)
		require(shown.begins_with("bj-the-house-cutter-tate-sword-"), "The weapon vanished mid-attack at step %d (%s)" % [step, scene.body.texture.resource_path])
		seen[shown.trim_prefix("bj-the-house-cutter-tate-sword-")] = true
	require(seen.has("action") and seen.has("follow"), "Attack should have used both the action and follow sheets: " + str(seen.keys()))
	await create_timer(1.0).timeout
	scene._miss()
	var hurt_seen := false
	for step in range(60):
		await create_timer(0.04).timeout
		if held_name(scene).ends_with("-hurt"):
			hurt_seen = true
			break
	require(hurt_seen, "The counterattack never showed the held weapon's hurt sheet")
	await create_timer(1.2).timeout

	# Fallbacks keep the baked weapon.
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "not-a-weapon"})
	require(held_name(scene) == "" and scene.body.texture.resource_path.ends_with("tate-idle-sheet.png"), "Unknown weapon should keep the baked sheet")
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	require(held_name(scene) == "" and scene.body.texture.resource_path.ends_with("tate-greatsword-sheet.png"), "A weapon with no greatsword strips should keep the baked greatsword")
	# Every outfit carries every sword-style weapon on its own weapon-less base.
	var looks := {"classic": "tate", "ivory": "ivory", "spectral": "warden", "harvest": "harvest", "oracle": "oracle", "patchwork": "patchwork", "pilgrim": "pilgrim", "wayfarer": "wayfarer", "debugger": "debugger", "merchant-oracle": "merchant-oracle", "norse": "norse", "lanternkeeper": "lanternkeeper", "wardplate": "wardplate"}
	var swords := ["lv-01", "lv-02", "lv-05", "bj-card-edge-dagger", "bj-ace-of-spades-blade", "bj-the-house-cutter", "dc-lantern-lit-shortsword", "merchant-vigil-sabre", "campaign-dungeon-syntax-sabre", "campaign-dungeon-loopblade", "campaign-dungeon-hollow-fang"]
	for look in looks:
		for weapon in swords:
			scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": look, "weaponId": weapon})
			var shown := held_name(scene)
			require(scene.skin_id == looks[look] and shown == "%s-%s-sword-idle" % [weapon, looks[look]], "%s / %s should hold its weapon, got '%s' on skin %s" % [look, weapon, shown, scene.skin_id])
	# Greatsword-style weapons, on every outfit.
	var heavy := ["lv-03", "bj-the-shoe-splitter", "cas-coin-roll-club", "cas-lever-arm-mace", "cas-jackpot-hammer", "dc-deepvein-warhammer", "dc-the-core-breaker", "hunter-sparring-greatsword", "merchant-nightfall-greatsword", "campaign-dungeon-iron-greatsword", "campaign-dungeon-minotaur-edge", "campaign-dungeon-clockwork-greatblade"]
	for look in looks:
		for weapon in heavy:
			scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": look, "weaponId": weapon})
			var shown_heavy := held_name(scene)
			require(shown_heavy == "%s-%s-greatsword-action" % [weapon, looks[look]], "%s / %s should hold a greatsword-style weapon, got '%s'" % [look, weapon, shown_heavy])
	# Pole styles swap only the head, on every outfit; whips add a piece at the lash tip.
	var pole_styles := {
		"scythe": ["dc-miner-s-pickaxe", "hunter-sparring-scythe", "hunter-jack-scythe", "campaign-dungeon-grave-scythe", "campaign-dungeon-undertow-scythe"],
		"handmagic": ["cas-reel-spinner-chakram", "cas-lady-luck-s-sceptre", "hunter-sparring-focus", "campaign-dungeon-runic-casting", "campaign-dungeon-last-page"],
		"whip": ["bj-croupier-s-rake", "campaign-dungeon-warden-chain", "campaign-dungeon-pathfinder-whip"],
		"staff": ["lv-04", "dc-cartographer-s-spear", "hunter-sparring-staff", "merchant-moonlit-staff", "campaign-dungeon-aether-staff", "campaign-dungeon-oracle-staff"],
	}
	for pole in pole_styles:
		for look in looks:
			for weapon in pole_styles[pole]:
				scene._apply_live_state({"simulated": true, "style": pole, "armorLook": look, "weaponId": weapon})
				var shown_pole := held_name(scene)
				require(shown_pole == "%s-%s-%s-action" % [weapon, looks[look], pole], "%s / %s should hold a %s weapon, got '%s'" % [look, weapon, pole, shown_pole])
	scene._apply_live_state({"simulated": true, "style": "whip", "armorLook": "classic", "weaponId": "hunter-sparring-whip"})
	require(held_name(scene) == "", "The Hunter's Whip is the plain lash and keeps the baked sheet")
	scene._apply_live_state({"simulated": true, "style": "staff", "armorLook": "classic", "weaponId": "campaign-dungeon-dawn-lantern", "weaponVariant": "dawn-lantern"})
	require(held_name(scene) == "", "The Dawn Lantern keeps its own baked variant")
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "classic", "weaponId": "hunter-gravebound-greatblade", "weaponVariant": "graveblade"})
	require(held_name(scene) == "", "The Gravebound Greatblade keeps its own baked variant sheets")
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "ivory", "weaponId": "hunter-gravebound-greatblade", "weaponVariant": "graveblade"})
	require(held_name(scene) == "" and scene.body.texture.resource_path.contains("ivory-graveblade"), "Ivory has baked Graveblade sheets, so it keeps them")
	for look in ["norse", "lanternkeeper", "wardplate"]:
		scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": look, "weaponId": "hunter-gravebound-greatblade", "weaponVariant": "graveblade"})
		require(held_name(scene) == "hunter-gravebound-greatblade-%s-greatsword-action" % look, "%s has no baked Graveblade, so it should hold the weapon: '%s'" % [look, held_name(scene)])
	# Infinite Dungeon run weapons share the Journal echo's art.
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic", "weaponId": "dungeon-loopblade"})
	require(held_name(scene) == "campaign-dungeon-loopblade-tate-sword-idle", "dungeon-loopblade should use the loopblade sheets: " + held_name(scene))
	scene._apply_live_state({"simulated": true, "style": "greatsword", "armorLook": "classic", "weaponId": "dungeon-iron-greatsword"})
	require(held_name(scene) == "campaign-dungeon-iron-greatsword-tate-greatsword-action", "dungeon-iron-greatsword should use the faultbreaker sheets")

	# A duel rival holds a weapon too, drawn from the enemy sprite's own sheet.
	scene._apply_live_state({"simulated": false, "region": "duel-colosseum", "style": "sword", "armorLook": "classic", "weaponId": "lv-01", "rivalStyle": "sword", "rivalArmorLook": "wardplate", "rivalWeaponId": "bj-the-house-cutter"})
	await process_frame
	require(scene.duel_mode and scene.enemy.flip_h, "Duel mode should mirror the rival")
	require(rival_name(scene) == "bj-the-house-cutter-wardplate-sword-idle", "The rival should hold the House Cutter: '%s'" % rival_name(scene))
	require(held_name(scene) == "lv-01-tate-sword-idle", "The hunter keeps their own weapon in a duel")
	scene._apply_live_state({"simulated": false, "region": "duel-colosseum", "style": "sword", "armorLook": "classic", "rivalStyle": "greatsword", "rivalArmorLook": "ivory", "rivalWeaponId": "hunter-gravebound-greatblade", "rivalWeaponVariant": "graveblade"})
	await process_frame
	require(rival_name(scene) == "", "A rival with a baked variant keeps it")
	scene._apply_live_state({"simulated": false, "region": "duel-colosseum", "style": "sword", "armorLook": "classic", "rivalStyle": "greatsword", "rivalArmorLook": "wardplate", "rivalWeaponId": "hunter-gravebound-greatblade", "rivalWeaponVariant": "graveblade"})
	await process_frame
	require(rival_name(scene) == "hunter-gravebound-greatblade-wardplate-greatsword-action", "A rival whose outfit has no baked Graveblade holds the weapon: '%s'" % rival_name(scene))
	scene._apply_live_state({"simulated": false, "region": "duel-colosseum", "style": "unarmed", "armorLook": "classic", "rivalStyle": "unarmed", "rivalArmorLook": "wardplate", "rivalWeaponId": "bj-the-house-cutter"})
	await process_frame
	require(rival_name(scene) == "", "A bare-handed rival must not draw a weapon")
	scene._apply_live_state({"simulated": false, "region": "basics", "enemy": "wraith", "style": "sword", "armorLook": "classic", "rivalWeaponId": "bj-the-house-cutter"})
	await process_frame
	require(rival_name(scene) == "", "A monster must never carry the rival's weapon")

	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "ivory", "weaponId": "not-a-weapon"})
	require(held_name(scene) == "" and scene.skin_id == "ivory", "An unknown weapon should keep the baked sword on any outfit")
	scene._apply_live_state({"simulated": true, "style": "staff", "armorLook": "classic", "weaponId": "bj-the-house-cutter", "weaponVariant": "dawn-lantern"})
	require(held_name(scene) == "", "Dawn Lantern must never stack a weapon on its baked art")
	scene._apply_live_state({"simulated": true, "style": "unarmed", "armorLook": "classic", "weaponId": "bj-the-house-cutter"})
	require(held_name(scene) == "", "Bare hands must not draw a weapon")
	scene._apply_live_state({"simulated": true, "style": "sword", "armorLook": "classic"})
	require(held_name(scene) == "", "No weapon id means the baked sword")

	print("held_weapon_smoke: %d failure(s)" % failures)
	quit(1 if failures > 0 else 0)
