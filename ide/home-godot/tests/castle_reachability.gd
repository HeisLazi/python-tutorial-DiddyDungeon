extends SceneTree

const Rooms = preload("res://scripts/rooms.gd")
const Home = preload("res://scenes/main.tscn")
const IDS := ["great_hall", "library", "pantry", "gallery", "armory", "war_room", "den"]
const ARRIVALS := {
 "great_hall": [Vector2(30, 142), Vector2(290, 142)],
 "library": [Vector2(30, 142), Vector2(160, 170), Vector2(220, 80)],
 "gallery": [Vector2(160, 170)], "pantry": [Vector2(192, 80)],
 "armory": [Vector2(30, 142), Vector2(190, 80)],
 "war_room": [Vector2(160, 170), Vector2(290, 142)], "den": [Vector2(30, 142)]
}

func _initialize() -> void:
 call_deferred("run_checks")

func run_checks() -> void:
 var home = Home.instantiate()
 root.add_child(home)
 await process_frame
 var failures: Array[String] = []
 var checks := 0
 for id in IDS:
  for level in range(Rooms.max_level(id) + 1):
   home.cli_level = level
   home.go_room(id, Vector2(160, 150), true)
   await process_frame
   var starts: Array = ARRIVALS[id].duplicate()
   starts.append(Vector2(160, 150))
   for start: Vector2 in starts:
    checks += 1
    if home._hits(start):
     failures.append("%s level %d: blocked arrival %s" % [id, level, start])
     continue
    var visited := {}
    var queue: Array[Vector2i] = [Vector2i(start)]
    visited[queue[0]] = true
    var doors_reached := {}
    var stations_reached := {}
    var cursor := 0
    while cursor < queue.size():
     var p := queue[cursor]
     cursor += 1
     var door_feet := Rect2(p.x - 2, p.y - 2, 4, 2)
     var station_feet := Rect2(p.x - 4, p.y - 4, 8, 4)
     for door in home.doors:
      if (door.rect as Rect2).intersects(door_feet): doors_reached[door.to] = true
     for station in home.stations:
      if (station.area as Rect2).intersects(station_feet): stations_reached[station.id] = true
     for step in [Vector2i(2, 0), Vector2i(-2, 0), Vector2i(0, 2), Vector2i(0, -2)]:
      var n: Vector2i = p + step
      if n.x < 0 or n.x > 320 or n.y < 64 or n.y > 186 or visited.has(n): continue
      if not home._hits(Vector2(n)):
       visited[n] = true
       queue.append(n)
    for door in home.doors:
     if not doors_reached.has(door.to): failures.append("%s level %d from %s: exit %s unreachable" % [id, level, start, door.to])
    for station in home.stations:
     if not stations_reached.has(station.id): failures.append("%s level %d from %s: station %s unreachable" % [id, level, start, station.id])
 print("Castle reachability: %d arrival/upgrade combinations, %d failures" % [checks, failures.size()])
 for failure in failures: print(failure)
 quit(1 if failures.size() else 0)
