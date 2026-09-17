const COMBAT_ICON = {
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z"/></svg>',
  relic: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 8 8l2 4-3 8h10l-3-8 2-4zM9 8h6"/></svg>',
  crown: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 7 4 4 4-7 4 7 4-4-2 11H6zM6 21h12"/></svg>',
  impact: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2 5 13h6l-1 9 9-13h-6z"/></svg>',
  raid: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M2 20a6 6 0 0 1 12 0M10 20a6 6 0 0 1 12 0"/></svg>',
  scythe: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 21 14 4M14 4c3 0 6 2 7 5-3-2-6-2-9 0"/></svg>',
  flame: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z"/></svg>',
  eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
}

const icon = (name, extra = '') => `<span class="combat-icon ${extra}">${COMBAT_ICON[name] || COMBAT_ICON.relic}</span>`
const gearIcon = (name) => `<div class="combat-gear-icon">${icon(name)}</div>`

const ARMOR = {
  'Apprentice Coat': { reduction: 10, tier: 'Starter' },
  'Leather Guard': { reduction: 20, tier: 'Uncommon' },
  'Runic Mail': { reduction: 30, tier: 'Rare' },
  'Emberplate': { reduction: 40, tier: 'Epic' },
  'Guardian Aegis': { reduction: 50, tier: 'Elite' },
  'Mythril Archive Plate': { reduction: 60, tier: 'Legendary' },
}

const TRINKETS = [
  {
    name: 'Ember Scythe',
    icon: 'scythe',
    rarity: 'Rare concept',
    effect: 'Weapon-shaped trinket. Proposed: +1 bonus Impact on the first verified Battle objective of an encounter.',
  },
  {
    name: 'Phoenix Ember',
    icon: 'flame',
    rarity: 'Legendary concept',
    effect: 'Proposed: once per day, revive at 1 HP when you would become Downed.',
  },
  {
    name: "Seer's Lens",
    icon: 'eye',
    rarity: 'Rare concept',
    effect: 'Proposed: reveal the concept category of one hidden encounter.',
  },
  {
    name: 'Bond of Embers',
    icon: 'raid',
    rarity: 'Raid relic concept',
    effect: 'Proposed multiplayer effect: once per weekly raid, revive one downed teammate.',
  },
]

const THREAT_PROFILES = [
  { threat: 'I', raw: '5–8' },
  { threat: 'I', raw: '5–8' },
  { threat: 'II', raw: '10–14' },
  { threat: 'II', raw: '10–14' },
  { threat: 'II', raw: '10–14' },
  { threat: 'III', raw: '15–20' },
  { threat: 'III', raw: '15–20' },
  { threat: 'III', raw: '15–20' },
]

let campaign = null
let revision = null

const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}[character]))

function activeProject(progress) {
  return (progress.projects || []).find((project) => project.status === 'active') || null
}

// Legacy snapshots used `cleared` while the state service now emits
// `defeated`. Treat both as terminal so the DOM combat shell cannot fall back
// to an already-cleared encounter when it receives an older projection.
const isMobDefeated = (mob) => mob?.status === 'defeated' || mob?.status === 'cleared'

function currentMob(project) {
  if (!project) return { mob: null, index: -1 }
  const mobs = project.mobs || []
  let index = mobs.findIndex((mob) => mob.status === 'available')
  if (index < 0) index = mobs.findIndex((mob) => !isMobDefeated(mob))
  if (index < 0 && mobs.length) index = mobs.length - 1
  return { mob: index >= 0 ? mobs[index] : null, index }
}

function armorState(progress) {
  const name = progress.equipment?.armor || 'None'
  return { name, ...(ARMOR[name] || { reduction: 0, tier: 'Unknown' }) }
}

function trinketState(progress) {
  const name = progress.equipment?.trinket || 'None'
  if (name === 'None') return { name, effect: 'No special effect equipped.' }
  const known = TRINKETS.find((item) => item.name === name)
  return { name, effect: known?.effect || 'Special effect recorded by the campaign.' }
}

function renderCharacterGear() {
  const progress = campaign?.progress
  const list = document.querySelector('.equipment-list')
  if (!progress || !list) return

  const armor = armorState(progress)
  const trinket = trinketState(progress)
  const title = progress.equipment?.title || progress.player?.title || 'None'
  const signature = JSON.stringify({ armor: armor.name, reduction: armor.reduction, tier: armor.tier, trinket: trinket.name, effect: trinket.effect, title })
  if (list.dataset.combatGearSignature === signature) return

  list.dataset.combatGear = 'true'
  list.dataset.combatGearSignature = signature
  list.innerHTML = `
    <div class="combat-gear-row">
      ${gearIcon('shield')}
      <small>Armor</small>
      <strong>${escapeHtml(armor.name)}</strong>
      <em>${escapeHtml(armor.tier)} · ${armor.reduction}% Battle damage reduction</em>
    </div>
    <div class="combat-gear-row">
      ${gearIcon('relic')}
      <small>Trinket</small>
      <strong>${escapeHtml(trinket.name)}</strong>
      <em>${escapeHtml(trinket.effect)}</em>
    </div>
    <div class="combat-gear-row">
      ${gearIcon('crown')}
      <small>Title</small>
      <strong>${escapeHtml(title)}</strong>
      <em>Identity / achievement slot. No combat power.</em>
    </div>
  `

  const characterLayout = document.querySelector('.character-layout')
  if (characterLayout && !characterLayout.querySelector('[data-combat-doctrine]')) {
    const card = document.createElement('section')
    card.className = 'game-card combat-doctrine-card'
    card.dataset.combatDoctrine = 'true'
    card.innerHTML = `
      <div class="card-heading"><span>COMBAT DOCTRINE</span><b>SAFE BY DEFAULT</b></div>
      <div class="combat-doctrine-grid">
        <div><strong>Safe Mode</strong><span>Code, debug, ask questions and learn with zero HP risk.</span></div>
        <div><strong>Battle submission</strong><span>Only an explicit submitted answer/checkpoint can trigger a counterattack.</span></div>
        <div><strong>Offense</strong><span>Verified work deals Impact. There is no weapon-damage stat.</span></div>
        <div><strong>Defense</strong><span data-combat-defense>${escapeHtml(armor.name)} currently blocks ${armor.reduction}% of Battle damage.</span></div>
      </div>
    `
    characterLayout.appendChild(card)
  } else {
    const defense = characterLayout?.querySelector('[data-combat-defense]')
    if (defense) defense.textContent = `${armor.name} currently blocks ${armor.reduction}% of Battle damage.`
  }
}

function renderQuestBattleShell() {
  const progress = campaign?.progress
  const hero = document.querySelector('.quest-hero')
  if (!progress || !hero) return
  const project = activeProject(progress)
  const { mob, index } = currentMob(project)
  const projected = campaign?.encounter && campaign.encounter.mob_name === mob?.name ? campaign.encounter : null
  const maxResolve = Number(projected?.max_resolve ?? mob?.max_resolve ?? mob?.resolve ?? 0)
  const resolve = Number(projected?.resolve ?? mob?.resolve ?? maxResolve)
  const availableObjectives = Array.isArray(projected?.available_objectives) ? projected.available_objectives : []
  const profile = THREAT_PROFILES[index] || { threat: 'I', raw: '5–8' }
  const armor = armorState(progress)
  const trinket = trinketState(progress)
  const existing = document.querySelector('[data-battle-shell]')
  const signature = JSON.stringify({ mob: mob?.name || project?.boss, resolve, maxResolve, status: projected?.status || mob?.status, objectives: availableObjectives, armor: armor.name, trinket: trinket.name })

  if (existing && existing.dataset.battleSignature === signature) return
  if (existing) {
    existing.dataset.battleSignature = signature
    const setText = (selector, value) => {
      const node = existing.querySelector(selector)
      if (node) node.textContent = value
    }
    setText('[data-battle-mob]', mob?.name || project?.boss || 'Current Encounter')
    setText('[data-battle-description]', mob?.encounter || 'Complete verified objectives to break the encounter.')
    setText('[data-battle-resolve]', `${Math.max(0, resolve)} / ${Math.max(0, maxResolve)}`)
    setText('[data-battle-armor]', `${armor.reduction}%`)
    setText('[data-battle-armor-copy]', `${armor.name} · percentage damage reduction.`)
    setText('[data-battle-trinket]', trinket.name)
    setText('[data-battle-trinket-copy]', trinket.effect)
    const objectiveList = existing.querySelector('[data-battle-objectives]')
    if (objectiveList) objectiveList.innerHTML = availableObjectives.map((objective) => `<span>${escapeHtml(objective.question_type || 'verified')} · ${escapeHtml(objective.impact)} Impact</span>`).join('') || '<span>Awaiting verified objective</span>'
    return
  }

  const card = document.createElement('section')
  card.className = 'game-card battle-shell-card'
  card.dataset.battleShell = 'true'
  card.dataset.battleSignature = signature
  card.innerHTML = `
    <div class="battle-shell-head">
      <div>
        <span class="screen-kicker">BATTLE SHELL · SLICE 1</span>
        <h3 data-battle-mob>${escapeHtml(mob?.name || project?.boss || 'Current Encounter')}</h3>
        <p data-battle-description>${escapeHtml(mob?.encounter || 'Complete verified objectives to break the encounter.')}</p>
      </div>
      <div class="safe-mode-badge">SAFE MODE</div>
    </div>

    <div class="battle-meters">
      <div class="battle-meter resolve">
        <span>${icon('impact')} ENEMY RESOLVE</span>
        <strong data-battle-resolve>${Math.max(0, resolve)} / ${Math.max(0, maxResolve)}</strong>
        <small>Verified state-service objectives reduce this with Impact.</small>
      </div>
      <div class="battle-meter threat">
        <span>THREAT</span>
        <strong>${profile.threat}</strong>
        <small>Wrong submitted Battle action: ${profile.raw} raw HP before armor.</small>
      </div>
      <div class="battle-meter armor">
        <span>${icon('shield')} ARMOR</span>
        <strong data-battle-armor>${armor.reduction}%</strong>
        <small data-battle-armor-copy>${escapeHtml(armor.name)} · percentage damage reduction.</small>
      </div>
      <div class="battle-meter trinket">
        <span>${icon('relic')} TRINKET</span>
        <strong data-battle-trinket>${escapeHtml(trinket.name)}</strong>
        <small data-battle-trinket-copy>${escapeHtml(trinket.effect)}</small>
      </div>
    </div>

    <div class="impact-doctrine">
      <div><b>1–2 Impact</b><span>prediction / explanation / bug diagnosis</span></div>
      <div><b>3–4 Impact</b><span>independent code checkpoint</span></div>
      <div><b>4–8 Impact</b><span>major verified objective</span></div>
    </div>

    <div class="impact-objectives" data-battle-objectives aria-label="Available verified objectives">
      ${availableObjectives.map((objective) => `<span>${escapeHtml(objective.question_type || 'verified')} · ${escapeHtml(objective.impact)} Impact</span>`).join('') || '<span>Awaiting verified objective</span>'}
    </div>

    <div class="battle-shell-note">
      <strong>Safe Mode:</strong> only a verified state-service result can change HP, Resolve, rewards or encounter progression.
    </div>
  `
  hero.insertAdjacentElement('afterend', card)

}

function renderTrinketVault() {
  const root = document.querySelector('.homestead-scene')
  if (!root || document.querySelector('[data-trinket-vault]')) return

  const section = document.createElement('section')
  section.className = 'game-card trinket-vault'
  section.dataset.trinketVault = 'true'
  section.innerHTML = `
    <div class="card-heading"><span>TRINKET VAULT</span><b>FUTURE LOOT</b></div>
    <p class="vault-copy">Weapon fantasy lives here too. A scythe or sword can be a trinket with a special effect instead of creating a separate weapon-damage system.</p>
    <div class="trinket-concept-grid">
      ${TRINKETS.map((item) => `
        <article>
          ${icon(item.icon, 'large')}
          <small>${item.rarity}</small>
          <h3>${item.name}</h3>
          <p>${item.effect}</p>
          <span>Not yet discovered</span>
        </article>
      `).join('')}
    </div>
  `
  root.insertAdjacentElement('afterend', section)
}

function render() {
  // React owns the Character, Homestead and Quest Journal surfaces now. The
  // original combat polish layer used DOM mutation to append a second Battle
  // Shell and replace the React equipment list, which made the Journal appear
  // to jump between layouts and left duplicate shells after a revision poll.
  // Keep this module as a compatibility listener for older markup, but clean
  // stale legacy nodes instead of injecting new UI into the React tree.
  document.querySelectorAll('[data-battle-shell], [data-trinket-vault], [data-combat-doctrine]').forEach((node) => node.remove())
}

let renderFrame = 0
const observer = new MutationObserver(() => {
  if (renderFrame) return
  renderFrame = requestAnimationFrame(() => {
    renderFrame = 0
    render()
  })
})
observer.observe(document.documentElement, { subtree: true, childList: true })

// AppV2 owns the single revision poll and publishes the committed projection.
// This legacy DOM polish layer only consumes that event; a second timer here
// would refetch the campaign, duplicate git work and make the HUD appear to
// jump during an otherwise ordinary state update.
window.addEventListener('questlab:campaign-updated', (event) => {
  if (event.detail && typeof event.detail === 'object') {
    campaign = event.detail
    revision = Number(campaign.revision ?? campaign.progress?.meta?.revision ?? 0)
    render()
  }
})
