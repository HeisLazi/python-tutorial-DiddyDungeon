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

const ENCOUNTER_PROFILES = [
  { resolve: 4, threat: 'I', raw: '5–8' },
  { resolve: 6, threat: 'I', raw: '5–8' },
  { resolve: 9, threat: 'II', raw: '10–14' },
  { resolve: 8, threat: 'II', raw: '10–14' },
  { resolve: 7, threat: 'II', raw: '10–14' },
  { resolve: 8, threat: 'III', raw: '15–20' },
  { resolve: 7, threat: 'III', raw: '15–20' },
  { resolve: 8, threat: 'III', raw: '15–20' },
]

let campaign = null
let loading = false

async function refreshCampaign() {
  if (loading) return
  loading = true
  try {
    const response = await fetch('/api/campaign')
    if (response.ok) campaign = await response.json()
  } catch {
    // The base UI already surfaces backend errors. Combat polish should not break Forge.
  } finally {
    loading = false
  }
}

function activeProject(progress) {
  return (progress.projects || []).find((project) => project.status === 'active') || null
}

function currentMob(project) {
  if (!project) return { mob: null, index: -1 }
  const mobs = project.mobs || []
  let index = mobs.findIndex((mob) => mob.status === 'available')
  if (index < 0) index = mobs.findIndex((mob) => mob.status !== 'defeated')
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
  if (!progress || !list || list.dataset.combatGear === 'true') return

  const armor = armorState(progress)
  const trinket = trinketState(progress)
  const title = progress.equipment?.title || progress.player?.title || 'None'

  list.dataset.combatGear = 'true'
  list.innerHTML = `
    <div class="combat-gear-row">
      ${gearIcon('shield')}
      <small>Armor</small>
      <strong>${armor.name}</strong>
      <em>${armor.tier} · ${armor.reduction}% Battle damage reduction</em>
    </div>
    <div class="combat-gear-row">
      ${gearIcon('relic')}
      <small>Trinket</small>
      <strong>${trinket.name}</strong>
      <em>${trinket.effect}</em>
    </div>
    <div class="combat-gear-row">
      ${gearIcon('crown')}
      <small>Title</small>
      <strong>${title}</strong>
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
        <div><strong>Defense</strong><span>${armor.name} currently blocks ${armor.reduction}% of Battle damage.</span></div>
      </div>
    `
    characterLayout.appendChild(card)
  }
}

function renderQuestBattleShell() {
  const progress = campaign?.progress
  const hero = document.querySelector('.quest-hero')
  if (!progress || !hero) return
  if (document.querySelector('[data-battle-shell]')) return

  const project = activeProject(progress)
  const { mob, index } = currentMob(project)
  const profile = ENCOUNTER_PROFILES[index] || { resolve: 6, threat: 'I', raw: '5–8' }
  const armor = armorState(progress)
  const trinket = trinketState(progress)

  const card = document.createElement('section')
  card.className = 'game-card battle-shell-card'
  card.dataset.battleShell = 'true'
  card.innerHTML = `
    <div class="battle-shell-head">
      <div>
        <span class="screen-kicker">BATTLE SHELL · SLICE 1</span>
        <h3>${mob?.name || project?.boss || 'Current Encounter'}</h3>
        <p>${mob?.encounter || 'Complete verified objectives to break the encounter.'}</p>
      </div>
      <div class="safe-mode-badge">SAFE MODE</div>
    </div>

    <div class="battle-meters">
      <div class="battle-meter resolve">
        <span>${icon('impact')} ENEMY RESOLVE</span>
        <strong>${profile.resolve} / ${profile.resolve}</strong>
        <small>Future verified objectives reduce this with Impact.</small>
      </div>
      <div class="battle-meter threat">
        <span>THREAT</span>
        <strong>${profile.threat}</strong>
        <small>Wrong submitted Battle action: ${profile.raw} raw HP before armor.</small>
      </div>
      <div class="battle-meter armor">
        <span>${icon('shield')} ARMOR</span>
        <strong>${armor.reduction}%</strong>
        <small>${armor.name} · percentage damage reduction.</small>
      </div>
      <div class="battle-meter trinket">
        <span>${icon('relic')} TRINKET</span>
        <strong>${trinket.name}</strong>
        <small>${trinket.effect}</small>
      </div>
    </div>

    <div class="impact-doctrine">
      <div><b>1–2 Impact</b><span>prediction / explanation / bug diagnosis</span></div>
      <div><b>3–4 Impact</b><span>independent code checkpoint</span></div>
      <div><b>4–8 Impact</b><span>major verified objective</span></div>
    </div>

    <div class="battle-shell-note">
      This first slice is display-only. <strong>Submit Run does not alter HP or Resolve yet.</strong>
      The next combat slice lets controlled PYR judge a submitted checkpoint before any state changes.
    </div>
  `
  hero.insertAdjacentElement('afterend', card)

  if (!document.querySelector('[data-raid-gate]')) {
    const raid = document.createElement('section')
    raid.className = 'game-card raid-gate-card'
    raid.dataset.raidGate = 'true'
    raid.innerHTML = `
      <div class="raid-gate-icon">${icon('raid')}</div>
      <div>
        <span class="screen-kicker">FUTURE PARTY CONTENT</span>
        <h3>Weekly Raids</h3>
        <p>Shared mini software projects where predefined objectives deal verified Impact to one party boss.</p>
        <div class="raid-example">
          <span>Core system <b>25</b></span>
          <span>Validation <b>20</b></span>
          <span>Tests / debugging <b>20</b></span>
          <span>Integration <b>20</b></span>
          <span>Party review <b>15</b></span>
        </div>
      </div>
      <div class="raid-locked">MULTIPLAYER LAYER NOT ENABLED</div>
    `
    card.insertAdjacentElement('afterend', raid)
  }
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
  renderCharacterGear()
  renderQuestBattleShell()
  renderTrinketVault()
}

const observer = new MutationObserver(render)
observer.observe(document.documentElement, { subtree: true, childList: true })

refreshCampaign().then(render)
setInterval(() => refreshCampaign().then(render), 6000)
window.addEventListener('load', () => refreshCampaign().then(render))
