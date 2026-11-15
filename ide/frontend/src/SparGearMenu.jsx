import { useState } from 'react'
import { merchantItemArt } from './merchantItemArt.js'
import { SPAR_SLOTS, hasPicks, sparGearBySlot } from './sparLoadout.js'

const SLOT_LABEL = { weapon: 'Weapon', armor: 'Armour', trinket: 'Trinket' }
const EMPTY_LABEL = { weapon: 'Bare hands', armor: 'Apprentice Coat', trinket: 'None' }

// The Sparring Ring's "try it on" menu: laid out like the Home Armory, but every item is unlocked.
// It only chooses what the combat scene shows; the hunter's real equipment and the save are never touched.
export default function SparGearMenu({ gear, loadError, armory, picks, onPick, onReset, onSwing }) {
  const [slot, setSlot] = useState('weapon')
  const [query, setQuery] = useState('')
  const grouped = sparGearBySlot(gear || [])
  const needle = query.trim().toLowerCase()
  const shown = grouped[slot].filter((item) => !needle || item.name.toLowerCase().includes(needle) || String(item.combat_style || '').includes(needle))
  const equippedName = { weapon: armory?.weapon?.name, armor: armory?.equipped?.armor, trinket: armory?.equipped?.trinket }
  // What each slot is showing right now: the pick, else the hunter's own gear.
  const current = (name) => {
    const pick = picks[name]
    if (pick === undefined) return equippedName[name] && equippedName[name] !== 'None' ? equippedName[name] : EMPTY_LABEL[name]
    return pick ? pick.name : EMPTY_LABEL[name]
  }
  const isCurrent = (item) => {
    const pick = picks[item.slot]
    return pick === undefined ? false : pick?.id === item.id
  }
  const isWorn = (item) => picks[item.slot] === undefined && (item.slot === 'weapon' ? armory?.weapon?.id === item.id : equippedName[item.slot] === item.name)
  return (
    <section className="character-panel armory-panel spar-gear" aria-label="Try gear in the Sparring Ring">
      <header><h3>Try gear</h3><small>SPARRING ONLY · EVERYTHING UNLOCKED</small></header>
      <p className="spar-gear-note">Pick any weapon, armour or trinket to see it in the ring. Nothing is equipped, bought or changed on your hunter.</p>
      <div className="armory-slots spar-gear-slots">
        {SPAR_SLOTS.map((name) => (
          <div key={name} className={picks[name] !== undefined ? 'trying' : ''}>
            <small>{SLOT_LABEL[name].toUpperCase()}{picks[name] !== undefined ? ' · TRYING' : ''}</small>
            <strong>{current(name)}</strong>
            <button type="button" onClick={() => onPick(name, null)} disabled={picks[name] === null}>{name === 'weapon' ? 'Bare hands' : name === 'armor' ? 'No armour' : 'No trinket'}</button>
            {picks[name] !== undefined && <button type="button" onClick={() => onPick(name, undefined)}>Back to mine</button>}
          </div>
        ))}
      </div>
      <div className="spar-gear-actions" role="group" aria-label="Test your gear">
        <button type="button" className="campaign-button" onClick={() => onSwing(true)}>Test swing</button>
        <button type="button" className="campaign-button ghost" onClick={() => onSwing(false)}>Take a hit</button>
        <button type="button" className="campaign-button ghost" onClick={onReset} disabled={!hasPicks(picks)}>Use my own gear</button>
      </div>
      <div className="bench-tabs" role="tablist" aria-label="Gear slot">
        {SPAR_SLOTS.map((name) => <button key={name} type="button" role="tab" aria-selected={slot === name} className={slot === name ? 'active' : ''} onClick={() => setSlot(name)}>{SLOT_LABEL[name]}s <small>{grouped[name].length}</small></button>)}
      </div>
      <label className="spar-gear-search">Search<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={slot === 'weapon' ? 'Name or style, e.g. whip' : 'Name'} /></label>
      {loadError ? <p role="alert">{loadError}</p>
        : !gear ? <p className="alchemy-empty">Loading the armoury…</p>
        : shown.length ? (
          <div className="armory-grid">{shown.map((item) => {
            const art = merchantItemArt(item)
            const trying = isCurrent(item)
            return (
              <article key={item.id} className={`armory-item tier-${item.tier} ${trying || isWorn(item) ? 'equipped' : ''}`}>
                <div className="armory-item-head">{art && <img className="armory-item-icon" src={art} alt="" />}<strong>{item.name}</strong><small>{String(item.tier).toUpperCase()} {SLOT_LABEL[item.slot]}{item.combat_style ? ` · ${item.combat_style}` : ''}</small></div>
                <p className="armory-effect">{item.effect}</p>
                {item.flavour && <small className="armory-flavour">{item.flavour}</small>}
                <small className={`spar-gear-owned ${item.owned ? 'owned' : ''}`}>{item.owned ? 'In your armory' : 'Not owned yet'}</small>
                <button type="button" className="campaign-button" onClick={() => onPick(item.slot, item)} disabled={trying} aria-pressed={trying}>{trying ? 'Trying' : isWorn(item) ? 'Wearing' : 'Try it on'}</button>
              </article>
            )
          })}</div>
        ) : <p className="alchemy-empty">{needle ? 'Nothing matches that search.' : 'Nothing here.'}</p>}
    </section>
  )
}
