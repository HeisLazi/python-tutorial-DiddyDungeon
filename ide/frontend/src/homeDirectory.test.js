import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { HOME_DIRECTORY } from './homeDirectory.js'

test('the Home directory follows the actual west-to-east room exits', () => {
  const source = readFileSync(new URL('../../home-godot/scripts/rooms.gd', import.meta.url), 'utf8')
  assert.equal(new Set(HOME_DIRECTORY.map((room) => room.id)).size, HOME_DIRECTORY.length)
  HOME_DIRECTORY.forEach((room, index) => {
    const match = source.match(new RegExp(`static func _${room.id}\\(h, lv: int\\)[\\s\\S]*?\\n\\s*_shell\\(([^\\n]+)`))
    assert.ok(match, `missing room shell for ${room.id}`)
    const exits = [...match[1].matchAll(/\{"to": "([^"]+)"/g)].map((result) => result[1])
    assert.deepEqual(exits, [HOME_DIRECTORY[index - 1]?.id, HOME_DIRECTORY[index + 1]?.id].filter(Boolean), room.id)
    assert.ok(room.name && room.short && room.places)
  })
})
