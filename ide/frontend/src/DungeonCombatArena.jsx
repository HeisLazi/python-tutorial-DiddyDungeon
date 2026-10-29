import { useEffect, useRef, useState } from 'react'
import { combatEnemyArt } from './combatEnemyArt.js'
import './dungeonCombat.css'

const percent = (value, max) => `${Math.max(0, Math.min(100, 100 * value / Math.max(1, max)))}%`
// Only map named combat styles; existing lantern and compass equipment still
// keeps its gameplay effects and uses the default sword visual until its art exists.
const combatStyle = (name = '') => {
  if (/hand\s*magic/i.test(name)) return 'handmagic'
  if (/greatsword|two.hand/i.test(name)) return 'greatsword'
  if (/whip/i.test(name)) return 'whip'
  if (/staff/i.test(name)) return 'staff'
  return 'sword'
}

export default function DungeonCombatArena({ run, loadout, turn, simulated = false }) {
  const arenaRef = useRef(null)
  const frameRef = useRef(null)
  const readyRef = useRef(false)
  const payloadRef = useRef(null)
  const pendingRef = useRef([])
  const [ready, setReady] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const [landed, setLanded] = useState(false)
  const encounter = run.encounter || {}
  const result = turn?.result
  const fight = result?.fight || {}
  const isCorrect = result?.outcome === 'correct'
  useEffect(() => {
    setLanded(false)
    if (!result) return undefined
    if (!simulated) arenaRef.current?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    const timer = setTimeout(() => setLanded(true), 350)
    return () => clearTimeout(timer)
  }, [result?.evidence_id, simulated])
  const hp = Number(landed && turn ? turn.hpAfter : loadout.hp) || 0
  const maxHp = Number(loadout.max_hp) || 1
  const maxResolve = Number(fight.max_resolve ?? encounter.max_resolve) || 1
  const resolve = Number(landed && isCorrect ? fight.resolve_after : (fight.resolve_before ?? encounter.resolve)) || 0
  const damage = Number(result?.damage) || 0
  const blast = Number(fight.blast) || 0
  const summary = !result ? 'Awaiting your answer' : isCorrect
    ? `Tate strikes for ${Number(fight.chip) || 0} Resolve${blast ? `; blast costs ${blast} HP` : ''}.`
    : damage ? `${encounter.name || 'Enemy'} strikes for ${damage} ${simulated ? 'practice HP' : 'HP'}${blast ? `; blast costs ${blast} more` : ''}.`
      : `The attack is guarded${blast ? `; blast costs ${blast} HP` : ''}.`
  payloadRef.current = { simulated, enemy: combatEnemyArt(encounter.name), style: combatStyle(loadout.weapon), turn_id: result?.evidence_id || '', outcome: result?.outcome || '' }
  const send = () => {
    if (!readyRef.current) return
    try { frameRef.current?.contentWindow?.diddyCombatReceive?.(JSON.stringify(payloadRef.current)) } catch { /* scene is still loading */ }
  }
  useEffect(() => {
    const timeout = setTimeout(() => setTimedOut(true), 20000)
    const onMessage = (event) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow || event.data?.source !== 'diddy-combat' || event.data?.type !== 'ready') return
      readyRef.current = true
      setReady(true)
      for (const payload of pendingRef.current) {
        try { frameRef.current?.contentWindow?.diddyCombatReceive?.(JSON.stringify(payload)) } catch { /* scene is reloading */ }
      }
      pendingRef.current = []
      send()
    }
    window.addEventListener('message', onMessage)
    return () => { clearTimeout(timeout); window.removeEventListener('message', onMessage) }
  }, [])
  useEffect(() => {
    if (!readyRef.current && payloadRef.current.turn_id && !pendingRef.current.some((item) => item.turn_id === payloadRef.current.turn_id)) {
      pendingRef.current.push({ ...payloadRef.current })
    }
    send()
  }, [simulated, encounter.name, loadout.weapon, result?.evidence_id, result?.outcome])

  return <section ref={arenaRef} className="dungeon-combat-panel" aria-label="Combat scene">
    <div className="combat-panel-title"><span>{simulated ? 'SPARRING · SIMULATED' : 'COMBAT'}</span><span>{simulated ? 'PRACTICE ONLY' : 'YOUR HP / ENEMY RESOLVE'}</span></div>
    <div className="combat-scene combat-godot-scene">
      <iframe ref={frameRef} title={simulated ? 'Simulated combat scene' : 'Dungeon combat scene'} src="/combat/index.html?embed=1" tabIndex={-1} onLoad={() => { readyRef.current = false; setReady(false) }} />
      {!ready && <div className="combat-loading" role="status">{timedOut ? 'Combat scene unavailable. You can continue answering.' : 'Preparing the combat scene…'}</div>}
      <div className="combat-vitals hunter-vitals"><div><span>TATE BUTI</span><b>{hp} / {maxHp}</b></div><div className="combat-bar"><i style={{ width: percent(hp, maxHp) }} /></div><small>{simulated ? 'PRACTICE HP' : 'HP'}</small></div>
      <div className="combat-vitals enemy-vitals"><div><span>{simulated ? 'HOLLOW' : encounter.name || 'ENEMY'}</span><b>{resolve} / {maxResolve}</b></div><div className="combat-bar enemy-bar"><i style={{ width: percent(resolve, maxResolve) }} /></div><small>RESOLVE</small></div>
      <div className="combat-scene-footer"><span>{result ? isCorrect ? 'TATE ATTACKS' : 'ENEMY ATTACKS' : 'AWAITING YOUR ANSWER'}</span><span>{simulated ? 'PRACTICE BOUT' : `FLOOR ${run.floor ?? 1}`}</span></div>
    </div>
    <div className="combat-equipment"><span>{simulated ? 'TRAINING WEAPON' : 'EQUIPPED'}</span><strong>{loadout.weapon || 'Unarmed'}</strong><small>{simulated ? 'Practice HP and Resolve reset after this bout.' : [run.class?.name, loadout.armor, loadout.trinket].filter(Boolean).join(' · ')}</small></div>
    <p className="combat-status" role="status">{summary}</p>
  </section>
}
