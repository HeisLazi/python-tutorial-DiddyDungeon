import { useEffect, useRef, useState } from 'react'
import { combatEnemyArt } from './combatEnemyArt.js'
import { combatStyle, combatWeaponVariant } from './combatWeaponArt.js'
import { raidCombatSummary } from './raidCombatUi.js'
import './dungeonCombat.css'
import { hunterAppearance } from './hunterEquipment.js'

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
export default function DungeonCombatArena({ run, loadout, turn, simulated = false, campaign = false, children, raidMode = false, raidParty = [], raidSeated = true }) {
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
  const summary = raidCombatSummary({ result, fight, turn, encounter, damage, blast, simulated, raidMode })
  const isBoss = !simulated && (run.room_type === 'boss' || raidMode)
  const phase = String(encounter.phase || '')
  const phaseTone = raidMode ? (Number(encounter.phase) >= 2 ? 'ember' : Number(encounter.phase) === 1 ? 'arcane' : 'steel') : (({ required_behavior: 'steel', explanation: 'arcane', edge_cases: 'ember', interview: 'crown', ready_to_clear: 'crown', complete: 'crown', I: 'steel', II: 'arcane', III: 'ember', IV: 'crown' })[phase] || 'steel')
  const appearance = hunterAppearance(loadout.armor, loadout.trinket)
  const enemyArt = combatEnemyArt(encounter.name, run.project_id)
  const bossArenas = { 'blackjack-house': 'blackjack-house', 'lantern-unwritten-king': 'unwritten-king', 'silver-mogul': 'silver-mogul', tozza: 'tozza' }
  const eliteArenas = { 'lantern-endless-echo': 'elite-endless-echo', 'lantern-delivery-beast': 'elite-delivery-beast', 'lantern-clockwork-caravan': 'elite-clockwork-caravan', 'lantern-unwritten-road': 'elite-unwritten-road' }
  const locationArt = isBoss && bossArenas[enemyArt] ? bossArenas[enemyArt] : campaign && eliteArenas[enemyArt] ? eliteArenas[enemyArt] : (run.region?.id || '')
  payloadRef.current = { ...appearance, simulated, armorMastery: campaign || simulated ? (loadout.armor_mastery || '') : '', weaponMastery: campaign || simulated ? (loadout.weapon_mastery || '') : '', region: raidMode ? 'choef-chief-keep' : locationArt, enemy: raidMode ? 'the-choef-chief' : enemyArt, style: loadout.weapon_style || combatStyle(loadout.weapon), weaponVariant: combatWeaponVariant(loadout.weapon), weaponId: loadout.weapon_id || '', raid: raidMode, party: raidParty, seated: raidSeated, attack: turn?.attack || {}, turn_id: result?.evidence_id || '', outcome: result?.outcome || '' }
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
  }, [simulated, campaign, run.region?.id, run.room_type, run.project_id, encounter.name, loadout.weapon, loadout.weapon_id, loadout.weapon_style, loadout.armor, loadout.trinket, loadout.armor_mastery, loadout.weapon_mastery, result?.evidence_id, result?.outcome, raidMode, raidParty, raidSeated])

  return <section ref={arenaRef} className={`dungeon-combat-panel ${isBoss ? `boss-scene phase-${phaseTone}` : ''}`} aria-label="Combat scene">
    <div className="combat-panel-title"><span>{raidMode ? `CO-OP RAID · PHASE ${Number(encounter.phase || 0) + 1}` : simulated ? 'SPARRING · SIMULATED' : `${campaign ? 'HUNT' : run.room_type === 'boss' ? 'BOSS' : run.room_type === 'elite' ? 'ELITE' : 'MOB'}${!isBoss && encounter.phase ? ` · PHASE ${encounter.phase}` : ''}`}</span><span>{raidMode ? 'THE HUNTERS VS THE CHOEF CHIEF' : simulated ? 'PRACTICE ONLY' : 'YOUR HP / ENEMY RESOLVE'}</span></div>
    <div className="combat-scene combat-godot-scene">
      <iframe ref={frameRef} title={simulated ? 'Simulated combat scene' : 'Dungeon combat scene'} src="/combat/index.html?embed=1" tabIndex={-1} onLoad={() => { readyRef.current = false; setReady(false) }} />
      {!ready && <div className="combat-loading" role="status">{timedOut ? 'Combat scene unavailable. You can continue answering.' : 'Preparing the combat scene…'}</div>}
      {!raidMode && <div className="combat-vitals hunter-vitals"><div><span>TATE BUTI</span><b>{hp} / {maxHp}</b></div><SegmentedBar value={hp} max={maxHp} count={Math.min(10, Math.max(1, Math.ceil(maxHp)))} label={simulated ? "Practice HP" : "Hunter HP"} tone="hp" /><small>{simulated ? 'PRACTICE HP' : 'HP'}</small></div>}
      <div className={`combat-vitals enemy-vitals ${isBoss ? 'boss-vitals' : ''} ${raidMode ? 'raid-boss-vitals' : ''}`}><div><span>{simulated ? 'HOLLOW' : raidMode ? 'THE CHOEF CHIEF' : encounter.name || 'ENEMY'}</span><b>{resolve} / {maxResolve}</b></div><SegmentedBar value={resolve} max={maxResolve} count={resolveSegments} label="Enemy Resolve" tone="resolve" /><small>RESOLVE</small></div>
      {raidMode && raidParty.map((member, index) => {
        const centers = [10.625, 21.875, 33.125, 44.375]
        const memberHp = Math.max(0, Math.min(5, Number(member.hp) || 0))
        return <div className={`raid-character-vitals ${member.hp <= 0 ? 'down' : ''} ${member.is_you ? 'you' : ''}`} style={{ left: `${centers[index] ?? centers[centers.length - 1]}%` }} key={member.id}>
          <span>{member.name}{member.is_you ? ' · YOU' : ''}</span>
          <SegmentedBar value={memberHp} max={5} count={5} label={`${member.name} health`} tone="hp" />
        </div>
      })}
      <div className="combat-scene-footer">{campaign
        ? <span>Submit a correct answer to strike · mistakes cost HP.</span>
        : <><span>{raidMode ? result ? isCorrect ? 'PARTY STRIKES' : turn?.attack?.type === 'aoe' ? 'CHIEF · TEAM AOE' : 'CHIEF · SINGLE STRIKE' : 'THE CHIEF WAITS' : result ? isCorrect ? 'TATE ATTACKS' : 'ENEMY ATTACKS' : 'AWAITING YOUR ANSWER'}</span><span>{raidMode ? 'CHOEF CHIEF’S KEEP' : simulated ? 'PRACTICE BOUT' : `FLOOR ${run.floor ?? 1}`}</span></>}
      </div>
    </div>
    {raidMode && <>
      <div className="combat-raid-taunt" aria-live="polite"><b>{raidSeated ? 'UNBOTHERED ON THE THRONE' : 'KEEPER OF THE CHOEFS'}</b><span>{raidSeated ? '“I was comfortable. You had to make this a whole thing?”' : '“Show me the code. I promise I’ll only make one joke about it.”'}</span><small>THE CHOEF GT ’83 · MOUNTED ABOVE THE THRONE</small></div>
    </>}
    {children && <div className="combat-encounter-info">{children}</div>}
    {!campaign && <div className="combat-equipment"><span>{simulated ? 'EQUIPPED AT HOME' : 'EQUIPPED'}</span><strong>{loadout.weapon || 'Unarmed'}</strong><small>{simulated ? (loadout.visual_unavailable ? 'Weapon animation not yet available; showing bare hands. Practice HP and Resolve reset after this bout.' : 'Equipped in Prepare. Practice HP and Resolve reset after this bout.') : [run.class?.name, loadout.armor, loadout.trinket].filter(Boolean).join(' · ')}</small></div>}
    {!campaign && <p className="combat-status" role="status">{summary}{fight.weapon_effect && <> · {fight.weapon_effect}</>}</p>}
  </section>
}
