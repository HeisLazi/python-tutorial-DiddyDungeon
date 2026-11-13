import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { HOME_DIRECTORY } from './homeDirectory.js'

test('the floor plan has reciprocal, geometrically consistent room connections', () => {
  const byId = new Map(HOME_DIRECTORY.map((room) => [room.id, room]))
  assert.equal(byId.size, HOME_DIRECTORY.length)
  const inverse = { north: ['south'], south: ['north', 'northwest', 'northeast'], east: ['west'], west: ['east'], northwest: ['south'], northeast: ['south'] }
  for (const room of HOME_DIRECTORY) {
    assert.ok(room.name && room.short && room.places)
    for (const [direction, destination] of Object.entries(room.exits)) {
      const other = byId.get(destination)
      assert.ok(other, `${room.id}: missing ${destination}`)
      assert.ok(inverse[direction]?.some((back) => other.exits[back] === room.id), `${room.id}: non-reciprocal ${direction}`)
      if (direction.includes('north')) assert.ok(other.y < room.y, `${room.id}: misplaced ${direction}`)
      if (direction === 'south') assert.ok(other.y > room.y, `${room.id}: misplaced ${direction}`)
      if (direction.includes('west')) assert.ok(other.x < room.x, `${room.id}: misplaced ${direction}`)
      if (direction.includes('east')) assert.ok(other.x > room.x, `${room.id}: misplaced ${direction}`)
    }
  }
})

test('the map destinations match the actual Godot doorways', () => {
  const source = readFileSync(new URL('../../home-godot/scripts/rooms.gd', import.meta.url), 'utf8')
  for (const room of HOME_DIRECTORY) {
    const match = source.match(new RegExp(`static func _${room.id}\\(h, _?lv: int\\)[\\s\\S]*?(?=\\n\\nstatic func |$)`))
    assert.ok(match, `missing room ${room.id}`)
    const side = [...match[0].matchAll(/\{"to": "([^"]+)"/g)].map((result) => result[1])
    const vertical = [...match[0].matchAll(/_(?:vertical_door\(h, (?:true|false),|front_door\(h,) [^,]+, "([^"]+)"/g)].map((result) => result[1])
    assert.deepEqual([...side, ...vertical].sort(), Object.values(room.exits).sort(), room.id)
  }
})
