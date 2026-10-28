import { useState } from 'react'
import { lessonFor } from './tutorLessons.js'

export default function TutorLearningPath({ pages, selectedPage, onSelect, onPractice, onResume, encounter, studyObjective, reference }) {
  const [attempts, setAttempts] = useState({})
  const [search, setSearch] = useState('')
  const visiblePages = pages.filter((page) => `${page.title} ${page.definition || ''}`.toLowerCase().includes(search.trim().toLowerCase()))
  const lesson = lessonFor(selectedPage)
  if (!lesson) return <p>Concepts are loading…</p>
  const picked = attempts[selectedPage.id]
  const objective = studyObjective || encounter?.current_quest || encounter?.available_objectives?.[0]
  return <div className="tutor-path">
    <aside className="tutor-path-index" aria-label="Choose a learning topic">
      <span className="screen-kicker">YOUR FIELD GUIDE</span><h3>Choose a topic</h3>
      <p>Start with the idea, then try it somewhere new.</p>
      <label className="tutor-topic-search">Search topics<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search concepts" /></label>
      <div className="tutor-path-list">{visiblePages.map((page) => <button type="button" key={page.id} className={page.id === selectedPage.id ? 'active' : ''} aria-current={page.id === selectedPage.id ? 'true' : undefined} onClick={() => onSelect(page.id)}>{page.title}</button>)}</div>{visiblePages.length === 0 && <p>No matching topics.</p>}
    </aside>
    <main className="tutor-path-main">
      {objective && <div className="tutor-current-task"><span>YOUR CURRENT BOUNTY</span><strong>{objective.label || encounter?.mob_name}</strong><button type="button" onClick={onResume}>Return to Forge →</button></div>}
      <div className="tutor-lesson-heading"><div><span className="screen-kicker">LEARN · {selectedPage.title.toUpperCase()}</span><h3>{lesson.title}</h3><p>{lesson.intro}</p></div></div>
      <section className="tutor-lesson-section"><span className="tutor-step">01 <b>READ</b></span><div><h4>See it in action</h4><pre><code>{lesson.example}</code></pre><p>{lesson.explain}</p></div></section>
      {lesson.options && <section className="tutor-lesson-section"><span className="tutor-step">02 <b>PREDICT</b></span><div><h4>{lesson.question}</h4><div className="tutor-lesson-options">{lesson.options.map((option, index) => <button type="button" key={option} className={picked === index ? 'selected' : ''} onClick={() => setAttempts((current) => ({ ...current, [selectedPage.id]: index }))}>{option}</button>)}</div>{picked !== undefined && <p className={`tutor-answer ${picked === lesson.answer ? 'correct' : 'incorrect'}`} role="status"><strong>{picked === lesson.answer ? 'That’s right. ' : 'Not quite. '}</strong>{picked === lesson.answer ? lesson.why : 'Look at the example again and try another answer.'}</p>}</div></section>}
      <section className="tutor-lesson-section"><span className="tutor-step">03 <b>TRY</b></span><div><h4>Make your own example</h4><p>{lesson.try}</p><button type="button" className="tutor-primary" onClick={() => onPractice('predict')}>Open practice →</button></div></section>
      <details className="tutor-deeper"><summary>More examples, mistakes and your encounter notes</summary><div>{reference}</div></details>
      <div className="tutor-reflection"><section><span className="screen-kicker">EXPLAIN IT</span><p>{lesson.teachback}</p></section><section><span className="screen-kicker">TAKE IT FURTHER</span><p>{lesson.transfer}</p></section><section><span className="screen-kicker">WATCH OUT FOR</span><p>{lesson.mistake}</p></section></div>
    </main>
  </div>
}
