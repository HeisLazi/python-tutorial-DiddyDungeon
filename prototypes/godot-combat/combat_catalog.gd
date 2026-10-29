extends RefCounted
## Combat style timing is shared; each skin supplies its own complete poses.
const STYLES := [
	{"id": "sword", "name": "SWORD", "kind": "sword"},
	{"id": "staff", "name": "STAFF", "kind": "projectile", "color": Color("8ceeff")},
	{"id": "whip", "name": "WHIP", "kind": "whip"},
	{"id": "greatsword", "name": "GREATSWORD", "kind": "heavy"},
	{"id": "handmagic", "name": "HAND MAGIC", "kind": "projectile", "color": Color("d188ff")},
]

static func tate() -> Dictionary:
	return {"id": "tate", "name": "TATE", "styles": {
		"sword": {"idle": preload("res://art/tate-idle-sheet.png"), "action": preload("res://art/tate-sword-v2-sheet.png"), "follow": preload("res://art/tate-followthrough-sheet.png"), "hurt": preload("res://art/tate-hurt-sheet.png"), "offset": Vector2(13, 0), "idle_frames": [0, 1, 2, 3, 2, 1]},
		"staff": {"cast_origin": Vector2(42, -52), "action": preload("res://art/tate-staff-sheet.png"), "hurt": preload("res://art/tate-staff-hurt-sheet.png"), "offset": Vector2(19, 0)},
		"whip": {"action": preload("res://art/tate-whip-sheet.png"), "hurt": preload("res://art/tate-whip-hurt-sheet.png"), "offset": Vector2(19, 0)},
		"greatsword": {"action": preload("res://art/tate-greatsword-sheet.png"), "hurt": preload("res://art/tate-greatsword-hurt-sheet.png"), "offset": Vector2(19, 0)},
		"handmagic": {"cast_origin": Vector2(42, -52), "action": preload("res://art/tate-handmagic-sheet.png"), "hurt": preload("res://art/tate-handmagic-hurt-sheet.png"), "offset": Vector2(19, 0)},
	}}

static func validate_skin(skin: Dictionary) -> String:
	if not skin.get("id", "") is String or skin.get("id", "").is_empty(): return "Skin needs an id"
	if not skin.get("name", "") is String or skin.get("name", "").is_empty(): return "Skin needs a name"
	if not skin.get("styles") is Dictionary: return "Skin needs a styles dictionary"
	for style in STYLES:
		var id: String = style.id
		if not skin.styles.get(id) is Dictionary: return "Missing style: " + id
		var poses: Dictionary = skin.styles[id]
		for key in ["action", "hurt"]:
			if not poses.get(key) is Texture2D: return id + " needs " + key + " texture"
		if not poses.get("offset") is Vector2: return id + " needs an offset"
		if style.kind == "projectile" and not poses.get("cast_origin") is Vector2: return id + " needs a cast_origin"
		if poses.has("idle") and not poses.idle is Texture2D: return id + " idle must be a texture"
		if id == "sword" and (not poses.get("follow") is Texture2D or not poses.get("idle") is Texture2D): return "Sword needs idle and follow textures"
		var reference: Texture2D = poses.action
		if reference.get_width() == 0 or reference.get_width() % 4 != 0 or reference.get_height() != 72: return id + " sheets must contain four equal 72px-high cells"
		for key in ["action", "hurt", "idle", "follow"]:
			if poses.has(key):
				if not poses[key] is Texture2D: return id + " has invalid " + key
				var texture: Texture2D = poses[key]
				if texture.get_size() != reference.get_size(): return id + " sheets must share cell dimensions"
		if poses.has("idle_frames"):
			if not poses.idle_frames is Array or poses.idle_frames.is_empty(): return id + " idle_frames must be a nonempty array"
			for frame in poses.idle_frames:
				if not frame is int or frame < 0 or frame > 3: return id + " idle frame must be 0..3"
	return ""
