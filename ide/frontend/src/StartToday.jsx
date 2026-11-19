import { useEffect, useRef, useState } from 'react'
import './startToday.css'

// "Start Today": a calm primer, then the bounty with only the hint ladder.
// Primers are static teaching cards from /api/today. Nothing here is saved,
// scored or timed; a wrong answer just explains and lets you try again.

async function getJson(url, options) {
  const response = await fetch(url, options)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return response.json()
}

export default function StartToday({ onClose, onBegin, onRecorded, focusName = '' }) {
  const [plan, setPlan] = useState(null)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState(0)
  const [step, setStep] = useState(0)
  const [choice, setChoice] = useState(null)
  const [verdict, setVerdict] = useState(null)
  const dialogRef = useRef(null)

  useEffect(() => {
    let live = true
    getJson('/api/today')
      .then((data) => {
        if (!live) return
        setPlan(data)
        const at = (data.bounties || []).findIndex((item) => item.name === focusName)
        if (at > 0) setPicked(at)
      })
      .catch((reason) => { if (live) setError(reason.message) })
    return () => { live = false }
  }, [])

  useEffect(() => {
    dialogRef.current?.focus()
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const bounties = plan?.bounties || []
  const bounty = bounties[picked]
  const primer = bounty?.primer
  const steps = primer?.steps || []
  const onCheck = primer && step >= steps.length

  const pick = (index) => { setPicked(index); setStep(0); setChoice(null); setVerdict(null) }

  const submit = async () => {
    if (choice === null || !primer) return
    try {
      const result = await getJson('/api/today/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sign: primer.sign, choice }),
      })
      setVerdict(result)
      if (result.recorded) onRecorded?.(result)
    } catch (reason) {
      setError(reason.message)
    }
  }

  let body
  if (error) {
    body = <p className="today-note">Could not load today's plan ({error}). You can still open the bounty from Campaign.</p>
  } else if (!plan) {
    body = <p className="today-note">Loading today…</p>
  } else if (!bounty) {
    body = <p className="today-note">No open bounty right now. Pick a campaign to begin.</p>
  } else {
    body = (
      <>
        <p className="today-task"><b>Today's bounty:</b> {bounty.name}. {bounty.task}</p>
        {!primer && <p className="today-note">No primer for this one yet, so it is straight to the work. You can do it.</p>}
        {primer && !onCheck && (
          <section className="today-card" aria-live="polite">
            <small>{primer.title} · {step + 1} of {steps.length}</small>
            <h3>{steps[step].heading}</h3>
            <p>{steps[step].body}</p>
            {steps[step].code && <pre><code>{steps[step].code}</code></pre>}
            <div className="today-actions">
              <button type="button" className="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</button>
              <button type="button" onClick={() => setStep(step + 1)}>{step + 1 < steps.length ? 'Next' : 'Quick check'}</button>
            </div>
          </section>
        )}
        {primer && onCheck && (
          <section className="today-card" aria-live="polite">
            <small>Quick check · no penalty, try as often as you like</small>
            <h3>{primer.check.question}</h3>
            <pre><code>{primer.check.code}</code></pre>
            <div className="today-options" role="radiogroup" aria-label="Choose what it prints">
              {primer.check.options.map((option, index) => (
                <label key={index} className={choice === index ? 'chosen' : ''}>
                  <input type="radio" name="today-check" checked={choice === index} onChange={() => { setChoice(index); setVerdict(null) }} />
                  <pre><code>{option}</code></pre>
                </label>
              ))}
            </div>
            {verdict && <p className={`today-verdict ${verdict.correct ? 'good' : ''}`}>{verdict.correct ? 'Right. ' : 'Not quite. '}{verdict.explain}</p>}
            {verdict?.recorded && (
              <p className="today-verdict good">
                Day logged: streak {verdict.streak}{verdict.streak_ward_used ? ' (a Streak Ward covered a missed day)' : ''}.
                {verdict.contract_completed && ` Daily contract done: +${verdict.reward?.reward_xp ?? 0} XP, +${verdict.reward?.reward_coins ?? 0}c.`}
              </p>
            )}
            <div className="today-actions">
              <button type="button" className="ghost" onClick={() => { setStep(0); setVerdict(null) }}>Re-read</button>
              {verdict?.correct
                ? <button type="button" onClick={() => onBegin(bounty)}>Start the bounty</button>
                : <button type="button" disabled={choice === null} onClick={submit}>Check</button>}
            </div>
          </section>
        )}
        {bounties.length > 1 && (
          <div className="today-upnext">
            <small>Up next</small>
            {bounties.map((item, index) => (
              <button key={item.name} type="button" className={index === picked ? 'chosen' : 'ghost'} onClick={() => pick(index)}>{item.name}</button>
            ))}
          </div>
        )}
      </>
    )
  }

  return (
    <div className="today-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <div className="today-dialog" role="dialog" aria-modal="true" aria-label="Start today" tabIndex={-1} ref={dialogRef}>
        <header>
          <div>
            <small>START TODAY</small>
            <h2>{plan?.project?.name || 'Today'}</h2>
          </div>
          <button type="button" className="ghost" onClick={onClose} aria-label="Close">Close</button>
        </header>
        {body}
        <footer>
          <button type="button" className="ghost" disabled={!bounty} onClick={() => bounty && onBegin(bounty)}>Skip the primer, take the bounty</button>
        </footer>
      </div>
    </div>
  )
}
