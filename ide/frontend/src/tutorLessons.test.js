import test from 'node:test'
import assert from 'node:assert/strict'
import { TUTOR_LESSONS, TUTOR_TRUE_FALSE, lessonFor } from './tutorLessons.js'

test('introductory checks provide a single valid answer and useful feedback', () => {
  for (const id of ['input-output', 'variables', 'conditionals', 'loops', 'functions', 'lists', 'dictionaries', 'sets', 'classes', 'callbacks']) {
    const lesson = TUTOR_LESSONS[id]
    assert.ok(lesson.example && lesson.explain && lesson.try && lesson.teachback && lesson.transfer)
    assert.ok(lesson.options.length >= 2 && new Set(lesson.options).size === lesson.options.length)
    assert.ok(lesson.answer >= 0 && lesson.answer < lesson.options.length && lesson.why)
    const check = TUTOR_TRUE_FALSE[id]
    assert.ok(check.question && check.why && [0, 1].includes(check.answer))
  }
})

test('unwritten lessons fall back to their existing Codex material', () => {
  const page = { id: 'testing', title: 'Tests', definition: 'An ordered sequence.', examples: ['items = []'], common_mistakes: ['Check the index.'] }
  const lesson = lessonFor(page)
  assert.equal(lesson.title, page.title)
  assert.equal(lesson.example, page.examples[0])
  assert.equal(lesson.mistake, page.common_mistakes[0])
  assert.equal(lessonFor(null), null)
})
