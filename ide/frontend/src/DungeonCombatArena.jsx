import { useEffect, useRef, useState } from 'react'
import crypt from './assets/dungeon-combat/crypt-v2.png'
import wraith from './assets/dungeon-combat/wraith-pixel.png'
import tate from './assets/dungeon-combat/tate-side.png'
import './dungeonCombat.css'

const percent = (value, max) => `${Math.max(0, Math.min(100, 100 * value / Math.max(1, max)))}%`

function EquippedWeapon({ name }) {
  const kind = /lantern/i.test(name) ? 'lantern' : /compass/i.test(name) ? 'compass' : 'blade'
  return <svg className={`combat-weapon ${kind}`} viewBox="0 0 22 52" shapeRendering="crispEdges" aria-hidden="true">
    {kind === 'lantern' ? <><path fill="#161321" d="M8 13h6v4h3v16h-3v3H7v-3H5V17h3zm2-5h2v5h-2z"/><path fill="#be9051" d="M7 17h10v16H7z"/><path fill="#ffdc7b" d="M9 19h6v11H9z"/><path fill="#fff1bd" d="M11 21h2v7h-2z"/></> : kind === 'compass' ? <><path fill="#171320" d="M11 17l9 9-9 9-9-9z"/><path fill="#b69055" d="M11 20l6 6-6 6-6-6z"/><path fill="#b8dbea" d="M11 22l3 4-3 4-3-4z"/><path fill="#ac513e" d="M11 23l2 3-2 1z"/></> : <><path fill="#171320" d="M9 0h4v35h5v4h-5v9H9v-9H4v-4h5z"/><path fill="#e1e6e8" d="M10 2h2v33h-2z"/><path fill="#8da6be" d="M12 6h1v28h-1z"/><path fill="#e9b75f" d="M5 35h12v3H5z"/><path fill="#744a30" d="M10 39h2v9h-2z"/></>}
  </svg>
}

export default function DungeonCombatArena({ run, loadout, turn, simulated = false }) {
  const arenaRef = useRef(null)
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
  }, [result?.evidence_id])
  const hp = Number(landed ? turn?.hpAfter : loadout.hp) || 0
  const maxHp = Number(loadout.max_hp) || 1
  const maxResolve = Number(fight.max_resolve ?? encounter.max_resolve) || 1
  const resolve = Number(landed && isCorrect ? fight.resolve_after : (fight.resolve_before ?? encounter.resolve)) || 0
  const damage = Number(result?.damage) || 0
  const blast = Number(fight.blast) || 0
  const summary = !result ? 'Awaiting your answer' : isCorrect
    ? `Tate strikes for ${Number(fight.chip) || 0} Resolve${blast ? `; blast costs ${blast} HP` : ''}.`
    : damage ? `${encounter.name || 'Enemy'} strikes for ${damage} ${simulated ? 'practice HP' : 'HP'}${blast ? `; blast costs ${blast} more` : ''}.`
      : `The attack is guarded${blast ? `; blast costs ${blast} HP` : ''}.`
  return <section ref={arenaRef} className="dungeon-combat-panel" aria-label="Combat scene">
    <div className="combat-panel-title"><span>{simulated ? 'SPARRING · SIMULATED' : 'COMBAT'}</span><span>{simulated ? 'PRACTICE ONLY' : 'YOUR HP / ENEMY RESOLVE'}</span></div>
    <div className={`combat-scene ${result ? isCorrect ? 'attack' : 'retaliate' : ''}`} data-kind={run.room_type} style={{ backgroundImage: `url(${crypt})` }}>
      <div className="combat-scene-shade" />
      <div className="combat-vitals hunter-vitals"><div><span>TATE BUTI</span><b>{hp} / {maxHp}</b></div><div className="combat-bar"><i style={{ width: percent(hp, maxHp) }} /></div><small>{simulated ? 'PRACTICE HP' : 'HP'}</small></div>
      <div className="combat-vitals enemy-vitals"><div><span>{encounter.name || 'ENEMY'}</span><b>{resolve} / {maxResolve}</b></div><div className="combat-bar enemy-bar"><i style={{ width: percent(resolve, maxResolve) }} /></div><small>RESOLVE</small></div>
      <div className="combat-shadow hunter-shadow"/><div className="combat-shadow enemy-shadow"/>
      <div className="combat-fighter combat-hunter"><div className="combat-hunter-sprite" style={{ backgroundImage: `url(${tate})` }} /><EquippedWeapon name={loadout.weapon || ''} /></div>
      <div className="combat-fighter combat-enemy"><img src={wraith} alt="" draggable="false" /></div>
      {result && <><div className="combat-strike"/><span className={`combat-damage ${isCorrect ? 'enemy-hit' : 'hunter-hit'}`} aria-hidden="true">{isCorrect ? `−${Number(fight.chip) || 0}` : damage ? `−${damage}` : 'GUARD'}</span></>}
      <div className="combat-scene-footer"><span>{result ? isCorrect ? 'TATE ATTACKS' : 'ENEMY ATTACKS' : 'AWAITING YOUR ANSWER'}</span><span>{simulated ? 'PRACTICE BOUT' : `FLOOR ${run.floor ?? 1}`}</span></div>
    </div>
    <div className="combat-equipment"><span>{simulated ? 'TRAINING WEAPON' : 'EQUIPPED'}</span><strong>{loadout.weapon || 'Unarmed'}</strong><small>{simulated ? 'Practice HP and Resolve reset after this bout.' : [run.class?.name, loadout.armor, loadout.trinket].filter(Boolean).join(' · ')}</small></div>
    <p className="combat-status" role="status">{summary}</p>
  </section>
}
