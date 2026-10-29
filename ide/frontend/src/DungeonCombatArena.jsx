import { useEffect, useRef, useState } from 'react'
import crypt from './assets/dungeon-combat/crypt-v2.png'
import simulation from './assets/dungeon-combat/spar-simulation.png'
import wraith from './assets/dungeon-combat/wraith-pixel.png'
import mimic from './assets/dungeon-combat/string-mimic.png'
import fork from './assets/dungeon-combat/forked-path.png'
import matriarch from './assets/dungeon-combat/mimic-matriarch.png'
import tate from './assets/dungeon-combat/tate-side.png'
import { combatEnemyArt } from './combatEnemyArt.js'
import './dungeonCombat.css'

const percent = (value, max) => `${Math.max(0, Math.min(100, 100 * value / Math.max(1, max)))}%`
const weaponKind = (name) => /lantern/i.test(name) ? 'lantern' : /compass/i.test(name) ? 'compass' : 'blade'
const ENEMY_SPRITES = { wraith, 'string-mimic': mimic, 'forked-path': fork, 'mimic-matriarch': matriarch }

function EquippedWeapon({ name }) {
  const kind = weaponKind(name)
  // Match Tate's 38×38 sprite coordinates: grip and pivot meet his hand.
  return <svg className={`combat-weapon ${kind}`} viewBox="0 0 38 38" preserveAspectRatio="none" shapeRendering="crispEdges" aria-hidden="true">
    {kind === 'lantern' ? <><path fill="#161321" d="M22 20h4v4h2v7h-8v-7h2zm1 1v3h2v-3z"/><path fill="#be9051" d="M21 25h6v5h-6z"/><path fill="#ffdc7b" d="M23 25h3v4h-3z"/></> : kind === 'compass' ? <><path fill="#171320" d="M27 18l5 5-5 5-5-5z"/><path fill="#b69055" d="M27 19l4 4-4 4-4-4z"/><path fill="#b8dbea" d="M27 20l3 3-3 3-3-3z"/><path fill="#ac513e" d="M27 21l1 2-1 1z"/></> : <><path fill="#161321" d="M33 10h3v3L26 23l-2-2zM22 20l5 5-2 2-5-5zM21 23l3 2-3 4-3-2z"/><path fill="#e1e6e8" d="M34 11h1v2L25 23l-1-1z"/><path fill="#8da6be" d="M33 13h1l-9 10-1-1z"/><path fill="#e9b75f" d="M22 20l5 5-1 1-5-5z"/><path fill="#a5743a" d="M21 24l2 1-2 3-2-1z"/></>}
  </svg>
}

export default function DungeonCombatArena({ run, loadout, turn, simulated = false }) {
  const arenaRef = useRef(null)
  const [landed, setLanded] = useState(false)
  const encounter = run.encounter || {}
  const enemyArt = combatEnemyArt(encounter.name)
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
    <div className={`combat-scene ${result ? isCorrect ? 'attack' : 'retaliate' : ''}`} data-kind={run.room_type} data-enemy={enemyArt} data-weapon={weaponKind(loadout.weapon || '')} data-simulated={simulated || undefined} style={{ backgroundImage: `url(${simulated ? simulation : crypt})` }}>
      <div className="combat-scene-shade" />
      <div className="combat-vitals hunter-vitals"><div><span>TATE BUTI</span><b>{hp} / {maxHp}</b></div><div className="combat-bar"><i style={{ width: percent(hp, maxHp) }} /></div><small>{simulated ? 'PRACTICE HP' : 'HP'}</small></div>
      <div className="combat-vitals enemy-vitals"><div><span>{encounter.name || 'ENEMY'}</span><b>{resolve} / {maxResolve}</b></div><div className="combat-bar enemy-bar"><i style={{ width: percent(resolve, maxResolve) }} /></div><small>RESOLVE</small></div>
      <div className="combat-shadow hunter-shadow"/><div className="combat-shadow enemy-shadow"/>
      <div className="combat-fighter combat-hunter"><div className="combat-hunter-sprite" style={{ backgroundImage: `url(${tate})` }} /><EquippedWeapon name={loadout.weapon || ''} /></div>
      <div className="combat-fighter combat-enemy"><img src={ENEMY_SPRITES[enemyArt]} alt="" draggable="false" /></div>
      {result && <><div className="combat-strike"/><div className="combat-projectile"/><span className={`combat-damage ${isCorrect ? 'enemy-hit' : 'hunter-hit'}`} aria-hidden="true">{isCorrect ? `−${Number(fight.chip) || 0}` : damage ? `−${damage}` : 'GUARD'}</span></>}
      <div className="combat-scene-footer"><span>{result ? isCorrect ? 'TATE ATTACKS' : 'ENEMY ATTACKS' : 'AWAITING YOUR ANSWER'}</span><span>{simulated ? 'PRACTICE BOUT' : `FLOOR ${run.floor ?? 1}`}</span></div>
    </div>
    <div className="combat-equipment"><span>{simulated ? 'TRAINING WEAPON' : 'EQUIPPED'}</span><strong>{loadout.weapon || 'Unarmed'}</strong><small>{simulated ? 'Practice HP and Resolve reset after this bout.' : [run.class?.name, loadout.armor, loadout.trinket].filter(Boolean).join(' · ')}</small></div>
    <p className="combat-status" role="status">{summary}</p>
  </section>
}
