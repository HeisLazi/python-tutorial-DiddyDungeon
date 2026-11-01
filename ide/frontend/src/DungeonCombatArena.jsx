import { useEffect, useRef, useState } from 'react'
import { combatEnemyArt } from './combatEnemyArt.js'
import './dungeonCombat.css'

function SegmentedBar({ value, max, count, label, tone }) {
  const safeMax = Math.max(1, max)
  const current = Math.max(0, Math.min(safeMax, value))
  return <div className={`combat-segments ${tone}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={safeMax} aria-valuenow={current}>
    {Array.from({ length: count }, (_, index) => {
      const fill = Math.max(0, Math.min(1, current / safeMax * count - index))
      return <span key={index}><i style={{ width: `${fill * 100}%` }} /></span>
    })}
  </div>
}
// Saved runs predating weapon_style use their known equipment name.
const combatStyle = (name = '') => {
  if (/hand\s*magic|runic casting/i.test(name)) return 'handmagic'
  if (/greatsword|two.hand/i.test(name)) return 'greatsword'
  if (/scythe/i.test(name)) return 'scythe'
  if (/whip/i.test(name)) return 'whip'
  if (/staff/i.test(name)) return 'staff'
  return 'sword'
}

export default function DungeonCombatArena({ run, loadout, turn, simulated = false, campaign = false, children }) {
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
    if (!simulated && !campaign) arenaRef.current?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    const timer = setTimeout(() => setLanded(true), 350)
    return () => clearTimeout(timer)
  }, [result?.evidence_id, simulated])
  const hp = Number(landed && turn ? turn.hpAfter : loadout.hp) || 0
  const maxHp = Number(loadout.max_hp) || 1
  const maxResolve = Number(fight.max_resolve ?? encounter.max_resolve) || 1
  const resolve = Number(landed && isCorrect ? fight.resolve_after : (fight.resolve_before ?? encounter.resolve)) || 0
  const resolveSegments = Math.min(48, Math.max(1, Math.ceil(maxResolve)))
  const damage = Number(result?.damage) || 0
  const blast = Number(fight.blast) || 0
  const summary = !result ? 'Awaiting your answer' : isCorrect
    ? `Tate strikes for ${Number(fight.chip) || 0} Resolve${blast ? `; blast costs ${blast} HP` : ''}.`
    : damage ? `${encounter.name || 'Enemy'} strikes for ${damage} ${simulated ? 'practice HP' : 'HP'}${blast ? `; blast costs ${blast} more` : ''}.`
      : `The attack is guarded${blast ? `; blast costs ${blast} HP` : ''}.`
  payloadRef.current = { simulated, region: run.region?.id || "", enemy: combatEnemyArt(encounter.name), style: loadout.weapon_style || combatStyle(loadout.weapon), turn_id: result?.evidence_id || '', outcome: result?.outcome || '' }
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
  }, [simulated, run.region?.id, encounter.name, loadout.weapon, loadout.weapon_style, result?.evidence_id, result?.outcome])

  return <section ref={arenaRef} className="dungeon-combat-panel" aria-label="Combat scene">
    <div className="combat-panel-title"><span>{simulated ? 'SPARRING · SIMULATED' : `${campaign ? 'HUNT' : run.room_type === 'boss' ? 'BOSS' : run.room_type === 'elite' ? 'ELITE' : 'MOB'}${encounter.phase ? ` · PHASE ${encounter.phase}` : ''}`}</span><span>{simulated ? 'PRACTICE ONLY' : 'YOUR HP / ENEMY RESOLVE'}</span></div>
    <div className="combat-scene combat-godot-scene">
      <iframe ref={frameRef} title={simulated ? 'Simulated combat scene' : 'Dungeon combat scene'} src="/combat/index.html?embed=1" tabIndex={-1} onLoad={() => { readyRef.current = false; setReady(false) }} />
      {!ready && <div className="combat-loading" role="status">{timedOut ? 'Combat scene unavailable. You can continue answering.' : 'Preparing the combat scene…'}</div>}
      <div className="combat-vitals hunter-vitals"><div><span>TATE BUTI</span><b>{hp} / {maxHp}</b></div><SegmentedBar value={hp} max={maxHp} count={Math.min(10, Math.max(1, Math.ceil(maxHp)))} label={simulated ? "Practice HP" : "Hunter HP"} tone="hp" /><small>{simulated ? 'PRACTICE HP' : 'HP'}</small></div>
      <div className="combat-vitals enemy-vitals"><div><span>{simulated ? 'HOLLOW' : encounter.name || 'ENEMY'}</span><b>{resolve} / {maxResolve}</b></div><SegmentedBar value={resolve} max={maxResolve} count={resolveSegments} label="Enemy Resolve" tone="resolve" /><small>RESOLVE</small></div>
      <div className="combat-scene-footer"><span>{result ? isCorrect ? 'TATE ATTACKS' : 'ENEMY ATTACKS' : 'AWAITING YOUR ANSWER'}</span><span>{simulated ? 'PRACTICE BOUT' : campaign ? 'CAMPAIGN' : `FLOOR ${run.floor ?? 1}`}</span></div>
    </div>
    {children && <div className="combat-encounter-info">{children}</div>}
    {!campaign && <div className="combat-equipment"><span>{simulated ? 'EQUIPPED AT HOME' : 'EQUIPPED'}</span><strong>{loadout.weapon || 'Unarmed'}</strong><small>{simulated ? (loadout.visual_unavailable ? 'Weapon animation not yet available; showing bare hands. Practice HP and Resolve reset after this bout.' : 'Equipped in Prepare. Practice HP and Resolve reset after this bout.') : [run.class?.name, loadout.armor, loadout.trinket].filter(Boolean).join(' · ')}</small></div>}
    {!campaign && <p className="combat-status" role="status">{summary}{fight.weapon_effect && <> · {fight.weapon_effect}</>}</p>}
  </section>
}
