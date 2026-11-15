extends RefCounted
## Held-weapon overlays. A hunter sheet that has a weapon-less base (art/held/base-<skin>-<style>-<key>-sheet.png)
## can show any weapon of that style as a second sprite on top, using art/held/<weapon>-<skin>-<style>-<key>.png.
## A strip has the same size and cell layout as its base sheet, so it follows the hunter's frame, offset and scale.
## Anything without a base and a strip keeps the weapon baked into the normal sheet.
const KEYS := ["idle", "action", "follow", "hurt"]
const FOLDER := "res://art/held/"

static var _exists := {}
static var _textures := {}
static var _bases := {}

static func _load(path: String) -> Texture2D:
	if not _exists.has(path):
		_exists[path] = ResourceLoader.exists(path)
		if _exists[path]:
			_textures[path] = load(path)
	return _textures.get(path)

## Weapon-less sheets for this skin and style, or an empty dictionary when none exist.
static func base_for(skin: String, style: String) -> Dictionary:
	var id := skin + "|" + style
	if not _bases.has(id):
		var found := {}
		for key in KEYS:
			var texture := _load(FOLDER + "base-%s-%s-%s-sheet.png" % [skin, style, key])
			if texture:
				found[key] = texture
		_bases[id] = found
	return _bases[id]

## Infinite Dungeon run weapons (`dungeon-loopblade`) share their art with the Journal echo (`campaign-dungeon-loopblade`).
static func canonical(weapon_id: String) -> String:
	return "campaign-" + weapon_id if weapon_id.begins_with("dungeon-") else weapon_id

static func strip_for(weapon_id: String, skin: String, style: String, key: String) -> Texture2D:
	if weapon_id.is_empty():
		return null
	return _load(FOLDER + "%s-%s-%s-%s.png" % [canonical(weapon_id), skin, style, key])

## True when this weapon can be drawn as an overlay for the skin and style.
static func covers(weapon_id: String, skin: String, style: String) -> bool:
	if weapon_id.is_empty():
		return false
	var base := base_for(skin, style)
	if base.is_empty():
		return false
	for key in base:
		if strip_for(weapon_id, skin, style, key) == null:
			return false
	return true

## The pose dictionary with its sheets swapped for the weapon-less bases.
static func apply(poses: Dictionary, weapon_id: String, skin: String, style: String) -> Dictionary:
	if not covers(weapon_id, skin, style):
		return poses
	var merged: Dictionary = poses.duplicate()
	merged.merge(base_for(skin, style), true)
	return merged

## Which sheet key the hunter sprite is showing right now, or "" if it is none of the bases.
static func key_of(poses: Dictionary, texture: Texture2D) -> String:
	for key in KEYS:
		if poses.get(key) == texture:
			return key
	return ""
