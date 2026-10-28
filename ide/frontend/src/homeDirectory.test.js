import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { HOME_DIRECTORY } from './homeDirectory.js'

test('the floor plan has reciprocal, geometrically consistent room connections', () => {
  const byId = new Map(HOME_DIRECTORY.map((room) => [room.id, room]))
  assert.equal(byId.size, HOME_DIRECTORY.length)
  const inverse = { north: 'south', south: 'north', east: 'west', west: 'east' }
  const delta = { north: [0, -45], south: [0, 45], east: [55, 0], west: [-55, 0] }
  for (const room of HOME_DIRECTORY) {
    assert.ok(room.name && room.short && room.places)
    for (const [direction, destination] of Object.entries(room.exits)) {
      const other = byId.get(destination)
      assert.ok(other, `${room.id}: missing ${destination}`)
      assert.equal(other.exits[inverse[direction]], room.id, `${room.id}: non-reciprocal ${direction}`)
      assert.deepEqual([other.x - room.x, other.y - room.y], delta[direction], `${room.id}: misplaced ${direction}`)
    }
  }
})

test('the map destinations match the actual Godot doorways', () => {
  const source = readFileSync(new URL('../../home-godot/scripts/rooms.gd', import.meta.url), 'utf8')
  for (const room of HOME_DIRECTORY) {
    const match = source.match(new RegExp(`static func _${room.id}\\(h, lv: int\\)[\\s\\S]*?(?=\\n\\nstatic func |$)`))
    assert.ok(match, `missing room ${room.id}`)
    const side = [...match[0].matchAll(/\{"to": "([^"]+)"/g)].map((result) => result[1])
    const vertical = [...match[0].matchAll(/_(?:vertical_door\(h, (?:true|false),|front_door\(h,) [^,]+, "([^"]+)"/g)].map((result) => result[1])
    assert.deepEqual([...side, ...vertical].sort(), Object.values(room.exits).sort(), room.id)
  }
})
