extends Node2D

# One continuous articulated limb, with the glove and weapon drawn in the
# same local coordinates. All weapons turn with the arm from the shoulder.
var weapon_kind := "sword":
	set(value):
		weapon_kind = value
		queue_redraw()
var whip_extension := 0.0:
	set(value):
		whip_extension = value
		queue_redraw()

func _draw() -> void:
	var ink := Color("11111c")
	var coat := Color("292933")
	var light := Color("56545a")
	var gold := Color("d1a257")
	var leather := Color("66452c")
	draw_line(Vector2(0, 0), Vector2(2, 4), ink, 5.0, false)
	draw_line(Vector2(2, 4), Vector2(5, 8), ink, 5.0, false)
	draw_line(Vector2(0, 0), Vector2(2, 4), coat, 3.0, false)
	draw_line(Vector2(2, 4), Vector2(5, 8), light, 2.0, false)
	if weapon_kind == "sword" or weapon_kind == "greatsword":
		var heavy := weapon_kind == "greatsword"
		var tip := Vector2(25, 1) if heavy else Vector2(18, 4)
		draw_line(Vector2(4, 9), Vector2(7, 8), ink, 4.0, false)
		draw_line(Vector2(4, 9), Vector2(7, 8), leather, 2.0, false)
		var width := 2.5 if heavy else 1.5
		var blade := PackedVector2Array([Vector2(7, 8 - width), tip + Vector2(-2, -width), tip + Vector2(2, 0), tip + Vector2(-1, width), Vector2(8, 8 + width)])
		draw_colored_polygon(blade, ink)
		var steel := PackedVector2Array([Vector2(8, 8 - width + 1), tip + Vector2(-2, -width + 1), tip + Vector2(1, 0), tip + Vector2(-2, width - 1), Vector2(8, 8 + width - 1)])
		draw_colored_polygon(steel, Color("a9bac6"))
		draw_line(Vector2(8, 8), tip, Color("eef2e4"), 1.0, false)
		draw_line(Vector2(6, 6), Vector2(8, 10), ink, 3.0, false)
		draw_line(Vector2(6, 6), Vector2(8, 10), gold, 1.5, false)
		if heavy:
			# Supporting forearm and glove share the hilt during the heavy swing.
			draw_line(Vector2(-3, 5), Vector2(2, 11), ink, 4.0, false)
			draw_line(Vector2(-3, 5), Vector2(2, 11), coat, 2.0, false)
			draw_rect(Rect2(1, 9, 3, 3), Color("917654"))
	elif weapon_kind == "magic":
		draw_line(Vector2(5, 12), Vector2(8, -7), ink, 4.0, false)
		draw_line(Vector2(5, 12), Vector2(8, -7), leather, 2.0, false)
		draw_rect(Rect2(6, -10, 5, 5), ink)
		draw_rect(Rect2(7, -9, 3, 3), Color("80ddf5"))
	else:
		draw_line(Vector2(4, 9), Vector2(8, 8), ink, 3.0, false)
		draw_line(Vector2(4, 9), Vector2(8, 8), leather, 2.0, false)
		# Uncoils into a wider lash during the attack; otherwise hangs down.
		var prev := Vector2(8, 8)
		for i in range(1, 11):
			var next := Vector2(8 + i * (0.5 + whip_extension * 2.0), 8 + i * (1.0 - whip_extension * 1.0) + sin(i * 0.9) * (2.5 - whip_extension))
			draw_line(prev, next, ink, 3.0, false)
			draw_line(prev, next, Color("bd7950"), 1.0, false)
			prev = next
	# Glove overlaps the grip so it does not look like a floating attachment.
	draw_rect(Rect2(3, 7, 3, 3), ink)
	draw_rect(Rect2(4, 7, 2, 2), Color("917654"))
