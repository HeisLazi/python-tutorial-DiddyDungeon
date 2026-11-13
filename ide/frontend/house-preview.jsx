import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import DungeonCombatArena from './src/DungeonCombatArena.jsx'
import '@fontsource/press-start-2p/400.css'
import '@fontsource/vt323/400.css'
import './src/housePreview.css'

const bosses = [
  { project: '00-lantern-vale', name: 'Lord Twang III', campaign: 'Mysterys in Shandumballa' },
  { project: '01-blackjack', name: 'The House', campaign: 'Blackjack' },
  { project: '04-casino-slots', name: 'Ekse Ouens P Diddy', campaign: 'Silver Reels' },
  { project: '05-dungeon-crawler', name: 'Die Tozza van Zamalek', campaign: 'Deep Crawler' },
  { project: '00-lantern-vale', name: 'The Endless Echo', campaign: 'Mysterys in Shandumballa', elite: true },
  { project: '00-lantern-vale', name: 'The Delivery Beast', campaign: 'Mysterys in Shandumballa', elite: true },
  { project: '00-lantern-vale', name: 'The Clockwork Caravan', campaign: 'Mysterys in Shandumballa', elite: true },
  { project: '00-lantern-vale', name: 'The Unwritten Road', campaign: 'Mysterys in Shandumballa', elite: true },
  { project: '01-blackjack', name: 'The Empty Table', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: "The Dealer's Hand", campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The Count Keeper', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The Hitman', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The Bust Hound', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The House Clerk', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The Judge', campaign: 'Blackjack', mob: true },
  { project: '01-blackjack', name: 'The Rematch Shade', campaign: 'Blackjack', mob: true },
]
const phases = [
  { id: 'required_behavior', label: 'Build the game' },
  { id: 'explanation', label: 'Explain the rules' },
  { id: 'edge_cases', label: 'The rules change' },
  { id: 'interview', label: 'Final interview' },
]
function Preview() {
  const [bossIndex, setBossIndex] = useState(1)
  const boss = bosses[bossIndex]
  const [phase, setPhase] = useState(0)
  const [mechanic, setMechanic] = useState(false)
  const [hp, setHp] = useState(100)
  const [resolve, setResolve] = useState(12)
  const [turn, setTurn] = useState(null)
  const act = (success) => {
    const next = success ? Math.max(0, resolve - 1) : resolve
    const nextHp = success ? hp : Math.max(0, hp - 5)
    setTurn({ hpAfter: nextHp, result: { evidence_id: `${Date.now()}`, outcome: success ? 'correct' : 'incorrect', damage: success ? 0 : 5, fight: { max_resolve: 12, resolve_before: resolve, resolve_after: next, chip: success ? 1 : 0 } } })
    setHp(nextHp); setResolve(next)
  }
  return <main className="house-preview">
    <header><span>QUEST LAB · COMBAT ART PREVIEW</span><h1>{boss.name}</h1><p>{boss.campaign} campaign {boss.elite ? 'elite' : boss.mob ? 'mob' : 'boss'} · isolated visual preview</p></header>
    <div className="house-preview-layout"><section className="house-preview-arena"><DungeonCombatArena campaign run={{ project_id: boss.project, room_type: boss.elite ? 'elite' : boss.mob ? 'mob' : 'boss', region: {}, encounter: { name: boss.name, resolve, max_resolve: 12, phase: boss.elite || boss.mob ? undefined : phases[phase].id, phase_label: boss.elite || boss.mob ? undefined : phases[phase].label, special_mechanic: { label: 'Boss mechanic', triggered: mechanic } } }} loadout={{ hp, max_hp: 100, weapon: 'Loopblade', weapon_style: 'sword' }} turn={turn} /></section>
    <aside><h2>Review the fight</h2><label htmlFor="boss-preview-select">Choose a fight</label><select id="boss-preview-select" value={bossIndex} onChange={(event) => { setBossIndex(Number(event.target.value)); setTurn(null) }}>{bosses.map((item, i) => <option key={item.name} value={i}>{item.name}</option>)}</select><p>Change the phase, trigger the mechanic and play both attacks.</p><div className="preview-phase">{phases.map((item, i) => <button key={item.id} className={phase === i ? 'selected' : ''} onClick={() => setPhase(i)}>{i + 1}. {item.label}</button>)}</div><button className={mechanic ? 'selected' : ''} onClick={() => setMechanic(!mechanic)}>{mechanic ? 'Mechanic active' : 'Activate mechanic'}</button><div className="preview-actions"><button onClick={() => act(true)}>Hunter attacks</button><button onClick={() => act(false)}>Enemy attacks</button><button onClick={() => { setHp(100); setResolve(12); setTurn(null) }}>Reset</button></div><small>Artwork and phase visuals only. These buttons do not affect your save.</small></aside></div>
  </main>
}
createRoot(document.getElementById('root')).render(<Preview />)
