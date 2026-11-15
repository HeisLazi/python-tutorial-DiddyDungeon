extends RefCounted
## Held weapons. A hunter sheet that has a weapon-less base (art/held/base-<skin>-<style>-<key>-sheet.png)
## can show any weapon of that style, using art/held/<weapon>-<skin>-<style>-<key>.png: a strip with the same size
## and cell layout as its base sheet that holds only the weapon.
## The strip is drawn into the base sheet once, in memory (see `compose`), so the hunter and the weapon are a single
## texture that animates, flips and tints as one. (A second sprite kept in step with the body drifted out of step in
## the web build.) Anything without a base and a strip keeps the weapon baked into the normal sheet.
const KEYS := ["idle", "action", "follow", "hurt"]
const FOLDER := "res://art/held/"

static var _exists := {}
static var _textures := {}
static var _bases := {}
static var _composed := {}

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

## A recoloured armour look draws its weapons from its parent outfit's strips (only the cloth differs).
const LOOKS := preload("res://looks_registry.gd")

static func strip_for(weapon_id: String, skin: String, style: String, key: String) -> Texture2D:
	if weapon_id.is_empty():
		return null
	return _load(FOLDER + "%s-%s-%s-%s.png" % [canonical(weapon_id), LOOKS.PARENTS.get(skin, skin), style, key])

## True when this weapon can be drawn as a held weapon for the skin and style.
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

## One sheet with the weapon drawn into the weapon-less base. Cached, and named `<weapon>-<skin>-<style>-<key>`.
static func compose(weapon_id: String, skin: String, style: String, key: String, base: Texture2D) -> Texture2D:
	var id := "%s-%s-%s-%s" % [canonical(weapon_id), skin, style, key]
	if _composed.has(id):
		return _composed[id]
	var strip := strip_for(weapon_id, skin, style, key)
	if strip == null:
		return base
	var image: Image = base.get_image()
	var weapon: Image = strip.get_image()
	if image == null or weapon == null:
		return base
	image.convert(Image.FORMAT_RGBA8)
	weapon.convert(Image.FORMAT_RGBA8)
	image.blend_rect(weapon, Rect2i(Vector2i.ZERO, weapon.get_size()), Vector2i.ZERO)
	var texture := ImageTexture.create_from_image(image)
	texture.resource_name = id
	_composed[id] = texture
	return texture

## The pose dictionary with each sheet swapped for the same sheet holding this weapon.
static func apply(poses: Dictionary, weapon_id: String, skin: String, style: String) -> Dictionary:
	if not covers(weapon_id, skin, style):
		return poses
	var merged: Dictionary = poses.duplicate()
	var bases := base_for(skin, style)
	for key in bases:
		merged[key] = compose(weapon_id, skin, style, key, bases[key])
	return merged
