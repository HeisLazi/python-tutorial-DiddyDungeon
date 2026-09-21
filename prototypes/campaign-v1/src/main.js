import './styles.css?campaign-v1-20260921-home-upgrades-v1'
import { merchantPixelSprite } from './pixelArt.js?campaign-v1-merchant-v3-sheet'
import {
  ARMOR,
  BOUNTY_BOARD_SIZE,
  CONTRACTS,
  MARKET_STOCK,
  POIS,
  PYR_STAGES,
  ROOM_UPGRADES,
  HOME_ACHIEVEMENTS,
  TRINKETS,
  buyItem,
  mainBountyBoards,
  claimReward,
  createInitialState,
  equipArmor,
  equipTrinket,
  feedPyr,
  isContractUnlocked,
  openPreparation,
  prerequisiteFor,
  recoverAtHome,
  runSelfCheck,
  selectContract,
  selectPlace,
  setOfficeBoard,
  spendUpgradeToken,
  purchaseRoomUpgrade,
  startEncounter,
  submitFailure,
  submitSuccess,
  useBandage,
  useMeal,
  useTonic,
  trainPyr,
  verifyGuardCheckpoint,
} from './campaignState.js?campaign-v1-20260920-home-market-pyr3'

const state = createInitialState()
const app = document.querySelector('#app')

const ENCOUNTER_LAYOUT_KEY = 'questlab-campaign-v1-encounter-layout'
const MAP_RAIL_KEY = 'questlab-campaign-v1-map-rail-collapsed'
const encounterLayout = {
  left: 300,
  right: 355,
  leftCollapsed: false,
  rightCollapsed: false,
}

let mapRailCollapsed = false

try {
  const savedLayout = JSON.parse(localStorage.getItem(ENCOUNTER_LAYOUT_KEY) || '{}')
  if (Number.isFinite(savedLayout.left)) encounterLayout.left = Math.max(220, Math.min(440, savedLayout.left))
  if (Number.isFinite(savedLayout.right)) encounterLayout.right = Math.max(260, Math.min(480, savedLayout.right))
  if (typeof savedLayout.leftCollapsed === 'boolean') encounterLayout.leftCollapsed = savedLayout.leftCollapsed
  if (typeof savedLayout.rightCollapsed === 'boolean') encounterLayout.rightCollapsed = savedLayout.rightCollapsed
  mapRailCollapsed = localStorage.getItem(MAP_RAIL_KEY) === 'true'
} catch {
  // A blocked localStorage should never stop the design-lab prototype.
}

let railDrag = null

function saveEncounterLayout() {
  try { localStorage.setItem(ENCOUNTER_LAYOUT_KEY, JSON.stringify(encounterLayout)) } catch {
    // Layout preferences are best effort in the isolated prototype.
  }
}

function encounterLayoutStyle() {
  const left = encounterLayout.leftCollapsed ? 58 : encounterLayout.left
  const right = encounterLayout.rightCollapsed ? 58 : encounterLayout.right
  return `--encounter-left:${left}px;--encounter-right:${right}px;`
}

function updateEncounterLayoutWidths() {
  const layout = document.querySelector('.encounter-layout')
  if (!layout) return
  layout.style.cssText = `${encounterLayoutStyle()}${layout.style.cssText.replace(/--encounter-(left|right):[^;]+;?/g, '')}`
}

function beginRailDrag(event, rail) {
  if (event.button !== 0) return
  event.preventDefault()
  railDrag = { rail, startX: event.clientX, startWidth: encounterLayout[rail] }
  document.body.classList.add('is-resizing-rail')
}

function moveRailDrag(event) {
  if (!railDrag) return
  const direction = railDrag.rail === 'left' ? 1 : -1
  const bounds = railDrag.rail === 'left' ? [220, 440] : [260, 480]
  encounterLayout[railDrag.rail] = Math.round(Math.max(bounds[0], Math.min(bounds[1], railDrag.startWidth + ((event.clientX - railDrag.startX) * direction))))
  updateEncounterLayoutWidths()
}

function endRailDrag() {
  if (!railDrag) return
  railDrag = null
  document.body.classList.remove('is-resizing-rail')
  saveEncounterLayout()
}

const escapeHtml = (value = '') => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

const selectedContract = () => CONTRACTS.find((entry) => entry.id === state.selectedContractId) || CONTRACTS[0]
const activeContract = () => CONTRACTS.find((entry) => entry.id === state.activeContractId) || selectedContract()
const itemById = (id) => [...ARMOR, ...TRINKETS, ...MARKET_STOCK].find((item) => item.id === id)
const AI_PROVIDERS = ['Codex', 'Claude', 'AGY', 'Copilot']

let terminalLineId = 0

const makeTerminalLine = (kind, text) => ({ id: `terminal-${++terminalLineId}`, kind, text })

function ensureTerminalState() {
  if (!state.terminal) {
    state.terminal = {
      selfCheck: [makeTerminalLine('system', 'Forge shell connected. Type help for bounded commands.')],
      pyr: Object.fromEntries(AI_PROVIDERS.map((provider) => [provider, [makeTerminalLine('system', `${provider} channel ready. Select an event stream.`)]])),
      connections: Object.fromEntries(['selfCheck', ...AI_PROVIDERS].map((channel) => [channel, 'connected'])),
      commandHistory: [],
    }
  }
  state.terminal.selfCheck ||= [makeTerminalLine('system', 'Forge shell connected. Type help for bounded commands.')]
  state.terminal.pyr ||= Object.fromEntries(AI_PROVIDERS.map((provider) => [provider, [makeTerminalLine('system', `${provider} channel ready. Select an event stream.`)]]))
  state.terminal.connections ||= Object.fromEntries(['selfCheck', ...AI_PROVIDERS].map((channel) => [channel, 'connected']))
  state.terminal.commandHistory ||= []
  for (const provider of AI_PROVIDERS) state.terminal.pyr[provider] ||= [makeTerminalLine('system', `${provider} channel ready. Select an event stream.`)]
  return state.terminal
}

function appendTerminal(channel, kind, text) {
  const terminal = ensureTerminalState()
  const lines = channel === 'selfCheck' ? terminal.selfCheck : terminal.pyr[channel]
  const next = [...(lines || []), makeTerminalLine(kind, text)].slice(-200)
  if (channel === 'selfCheck') terminal.selfCheck = next
  else terminal.pyr[channel] = next
}

function resetTerminalChannel(channel) {
  const terminal = ensureTerminalState()
  if (channel === 'selfCheck') terminal.selfCheck = [makeTerminalLine('system', 'Forge shell connected. Type help for bounded commands.')]
  else terminal.pyr[channel] = [makeTerminalLine('system', `${channel} channel ready. Select an event stream.`)]
}

function terminalLines(channel) {
  const terminal = ensureTerminalState()
  return channel === 'selfCheck' ? terminal.selfCheck : terminal.pyr[channel]
}

function recordStateEvent(next, channel = 'selfCheck', command = '') {
  const event = next?.lastEvent || 'No new event.'
  if (command) appendTerminal(channel, 'prompt', command)
  appendTerminal(channel, event.startsWith('Submission rejected') ? 'error' : 'output', event)
}

function seedEncounterTerminal() {
  const terminal = ensureTerminalState()
  const contract = activeContract()
  appendTerminal('selfCheck', 'system', `${contract.title} Forge loaded. Run is local; Submit is the validator boundary.`)
  appendTerminal(state.aiProvider || 'Codex', 'system', `PYR is watching ${contract.title}. Feedback stays bounded and answer-free.`)
  if (state.lastEvent) appendTerminal(state.aiProvider || 'Codex', 'output', state.lastEvent)
  terminal.connections.selfCheck = 'connected'
  terminal.connections[state.aiProvider || 'Codex'] = 'connected'
}

function runBoundedTerminalCommand(rawCommand) {
  const command = String(rawCommand || '').trim()
  if (!command) return
  const terminal = ensureTerminalState()
  terminal.commandHistory = [...terminal.commandHistory.filter((entry) => entry !== command), command].slice(-30)
  terminal.historyIndex = terminal.commandHistory.length
  appendTerminal('selfCheck', 'prompt', `forge@questlab:~$ ${command}`)
  const normalized = command.toLowerCase()
  if (normalized === 'help') {
    appendTerminal('selfCheck', 'output', 'bounded commands: help · run · clear · reconnect')
  } else if (normalized === 'clear') {
    resetTerminalChannel('selfCheck')
  } else if (normalized === 'reconnect') {
    terminal.connections.selfCheck = 'connected'
    appendTerminal('selfCheck', 'system', 'Forge shell reconnected. No campaign state changed.')
  } else if (normalized === 'run') {
    const next = runSelfCheck(state)
    recordStateEvent(next, 'selfCheck')
    Object.assign(state, next)
  } else {
    appendTerminal('selfCheck', 'error', `command not recognized: ${command}. Type help for the bounded command list.`)
  }
  render()
}

const icon = (name) => {
  const paths = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-6h6v6"/>',
    market: '<path d="M4 8h16l-1 12H5z"/><path d="M8 8V6a4 4 0 0 1 8 0v2M8 12h8"/>',
    office: '<path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h5M7 3v4M17 3v4"/>',
    coin: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9 9.5c.6-.8 1.4-1.2 2.6-1.2 1.5 0 2.4.7 2.4 1.7 0 2.8-5.1 1-5.1 3.7 0 1 .9 1.7 2.5 1.7 1.2 0 2.2-.4 2.8-1.2"/>',
    heart: '<path d="M20.8 8.8c0 5-8.8 10.2-8.8 10.2S3.2 13.8 3.2 8.8A4.3 4.3 0 0 1 12 6.5a4.3 4.3 0 0 1 8.8 2.3Z"/>',
    shield: '<path d="m12 3 7 3v5c0 4.8-3 8.2-7 10-4-1.8-7-5.2-7-10V6z"/><path d="m9 12 2 2 4-4"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    spark: '<path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8z"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    lock: '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  }
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.spark}</svg>`
}

function apply(next) {
  if (!next || next === state) return
  const event = next.lastEvent && next.lastEvent !== state.lastEvent ? next.lastEvent : ''
  Object.assign(state, next)
  if (event) state.events = [event, ...(state.events || [])].slice(0, 5)
  render()
}

function button(label, action, options = {}) {
  const kind = options.kind || 'button'
  const disabled = options.disabled ? ' disabled' : ''
  const classes = ['button', kind === 'ghost' ? 'button-ghost' : '', kind === 'quiet' ? 'button-quiet' : '', options.className || ''].filter(Boolean).join(' ')
  const itemAttribute = options.itemId ? ` data-item-id="${escapeHtml(options.itemId)}"` : ''
  return `<button class="${classes}" type="button" data-action="${escapeHtml(action)}"${itemAttribute}${disabled}>${options.icon ? icon(options.icon) : ''}<span>${escapeHtml(label)}</span></button>`
}

function renderHeader() {
  return `
    <header class="topbar">
      <div class="brand-lockup">
        <span class="brand-mark">✦</span>
        <div><span class="eyebrow">QUEST LAB · DESIGN LAB</span><strong>Campaign v1</strong></div>
      </div>
      <div class="header-context"><span class="status-dot"></span><span>LOCAL PROTOTYPE · NO CANONICAL STATE</span></div>
      <div class="run-stats" aria-label="Prototype stats">
        <div class="stat"><small>HP</small><strong>${state.hp}/${state.maxHp}</strong><i style="width:${Math.max(0, Math.min(100, state.hp / state.maxHp * 100))}%"></i></div>
        <div class="stat"><small>COINS</small><strong>${state.coins}</strong></div>
        <div class="stat"><small>TOKENS</small><strong>${state.upgradeTokens}</strong></div>
      </div>
    </header>`
}

function renderPoiRail() {
  const mainBounties = CONTRACTS.filter((entry) => entry.type === 'main')
  const completedMain = mainBounties.filter((entry) => state.completedContracts.includes(entry.id)).length
  return `
    <aside class="poi-rail panel ${mapRailCollapsed ? 'map-rail-collapsed' : ''}">
      <div class="panel-heading">
        <div><span class="eyebrow">PROJECT MAP</span><h1>Blackjack</h1></div>
        <span class="panel-tag">3 POIs</span>
        <button type="button" class="map-rail-toggle" data-action="toggle-map-rail" aria-label="${mapRailCollapsed ? 'Expand project map' : 'Collapse project map'}">${mapRailCollapsed ? '›' : '‹'}</button>
      </div>
      <p class="panel-copy">A small campaign board. Choose where to prepare or which work to take next; there is no route tree to decode.</p>
      <div class="poi-list">
        ${POIS.map((poi) => `
          <button class="poi-card ${state.place === poi.id && state.screen === 'map' ? 'active' : ''}" type="button" data-action="select-place" data-place="${poi.id}">
            <span class="poi-icon poi-${poi.id}">${poi.icon}</span>
            <span class="poi-copy"><strong>${poi.label}</strong><small>${poi.kicker}</small><em>${poi.summary}</em></span>
            <span class="poi-arrow">${icon('arrow')}</span>
          </button>`).join('')}
      </div>
      <div class="project-progress">
        <div class="section-label"><span>PROJECT PROGRESS</span><strong>Chapter 01</strong></div>
        <div class="progress-track"><i style="width:${Math.min(100, completedMain * 24)}%"></i></div>
        <p>Boss remains locked until the project bounties are cleared.</p>
      </div>
      <div class="prototype-note village-teaser"><span>${icon('spark')}</span><div><strong>VILLAGE BOARD · NEXT</strong><p>NPC walks, side quests, and the arena belong to the next prototype slice.</p></div></div>
      <div class="map-rail-collapsed-summary" aria-hidden="${!mapRailCollapsed}"><span>✦</span><strong>MAP</strong><small>OPEN</small></div>
    </aside>`
}

function renderMapShell(content) {
  return `<div class="campaign-layout ${mapRailCollapsed ? 'map-rail-is-collapsed' : ''}">${renderPoiRail()}<main class="place-panel panel">${content}</main></div>`
}

function renderHome() {
  const armor = ARMOR.filter((item) => state.ownedArmor.includes(item.id))
  const trinkets = TRINKETS.filter((item) => state.ownedTrinkets.includes(item.id))
  const focus = state.homeFocus || 'hearth'
  const pyr = state.pyr || { stage: 'spark', bond: 0, energy: 2, maxEnergy: 2, fedCount: 0, trainingCount: 0 }
  const pyrStage = PYR_STAGES.find((entry) => entry.id === pyr.stage) || PYR_STAGES[0]
  const nextPyrStage = PYR_STAGES.find((entry) => entry.threshold > pyr.bond)
  const roomUpgrades = state.roomUpgrades || []
  const roomUpgradePanelOpen = Boolean(state.roomUpgradePanelOpen)
  const builtRoomUpgrades = ROOM_UPGRADES.filter((entry) => roomUpgrades.includes(entry.id))
  const roomUpgradeCopy = ROOM_UPGRADES.map((entry) => {
    const built = roomUpgrades.includes(entry.id)
    const canBuild = !built && state.upgradeTokens >= entry.cost
    return `<article class="room-upgrade-card ${built ? 'built' : ''}"><div class="room-upgrade-card-head"><span class="room-upgrade-kind">${entry.kind}</span><strong>${entry.name}</strong><span class="room-upgrade-effect">${entry.effect}</span></div><p>${entry.detail}</p>${built ? `<span class="room-upgrade-status">BUILT · ACTIVE</span>` : button(`Build · ${entry.cost} token${entry.cost === 1 ? '' : 's'}`, 'buy-room-upgrade', { icon: 'spark', itemId: entry.id, className: 'room-upgrade-build', disabled: !canBuild })}</article>`
  }).join('')
  const achievementCopy = HOME_ACHIEVEMENTS.map((entry) => {
    const unlocked = entry.unlock(state)
    return `<article class="home-achievement ${unlocked ? 'unlocked' : 'locked'}"><span class="home-achievement-icon">${unlocked ? entry.icon : '·'}</span><div><strong>${unlocked ? entry.name : 'HIDDEN PLAQUE'}</strong><p>${unlocked ? entry.detail : 'Keep learning to reveal this room history.'}</p></div><small>${unlocked ? 'UNLOCKED' : 'LOCKED'}</small></article>`
  }).join('')
  const focusIcon = focus === 'hearth' ? icon('heart') : focus === 'armory' ? icon('shield') : focus === 'study' ? icon('spark') : focus === 'pyr' ? '✦' : '＋'
  const focusCopy = {
    hearth: ['Hearth', 'Warm up before the next job.', 'The house is safe. Recover fully here, or eat a packed meal for a smaller top-up without changing the coding requirement.', `<div class="home-context-actions">${button('Recover fully', 'recover', { icon: 'heart', disabled: state.hp === state.maxHp })}${button('Eat a meal', 'use-meal', { kind: 'ghost', disabled: !state.supplies?.meals || state.hp === state.maxHp })}</div>`],
    armory: ['Armory chest', 'Tune the kit you will carry.', 'Armor softens retaliation. Trinkets shape Guard Breaks and protection. Equip what fits the next contract, then return to the Forge.', `<div class="home-context-actions">${button('Browse more gear', 'go-market', { icon: 'arrow' })}${button('Spend upgrade token', 'spend-token', { icon: 'spark', kind: 'ghost', disabled: state.upgradeTokens < 1 })}</div>`],
    pantry: ['Pantry', 'Pack a useful encounter kit.', 'Field bandages restore HP at Home. Ember tonics can be primed during an encounter to soften one failed submission. Meals can also keep Pyr growing.', `<div class="home-context-actions">${button('Use bandage', 'use-bandage', { icon: 'heart', disabled: !state.supplies?.bandages || state.hp === state.maxHp })}${button('Eat a meal', 'use-meal', { kind: 'ghost', disabled: !state.supplies?.meals || state.hp === state.maxHp })}</div>`],
    study: ['Study desk', 'Turn learning into a stronger home.', 'Validated work earns upgrade tokens. Build five authored room upgrades here, then let the achievement plaques record the moments you earned them.', `<div class="home-context-actions">${button('Open room upgrades', 'toggle-room-upgrades', { icon: 'spark' })}${button('Spend one legacy token', 'spend-token', { icon: 'spark', kind: 'ghost', disabled: state.upgradeTokens < 1 })}</div>`],
    pyr: [pyrStage.label, 'Spend time with your code-flame.', `${pyrStage.detail} Feed Pyr with a camp meal to restore training energy, or train to grow bond. The next evolution is ${nextPyrStage ? `${nextPyrStage.label} at bond ${nextPyrStage.threshold}` : 'already reached'}.`, `<div class="pyr-activity-actions">${button('Feed Pyr', 'feed-pyr', { icon: 'heart', disabled: !state.supplies?.meals })}${button('Train with Pyr', 'train-pyr', { icon: 'spark', kind: 'ghost', disabled: pyr.energy < 1 })}</div>`],
  }[focus] || []
  return `
    <div class="place-heading">
      <div class="place-heading-copy home-place-heading"><span class="eyebrow">HOME · HOMESTEAD</span><h2>Your homestead.</h2><p>Recover, prepare, and grow Pyr before the next bounty.</p></div>
      <span class="place-seal place-seal-home">⌂</span>
    </div>
    <div class="home-interior-layout">
      <section class="home-room-scene" aria-label="Homestead interior with selectable stations">
        <div class="room-topline"><span>THE HOMESTEAD</span><small>SAFE ROOM · PREPARE · GROW</small></div>
        <div class="room-plaque"><span>BLACKJACK</span><small>CHAPTER 01 · HOME BASE</small></div>
        <div class="room-window"><i></i><b>✦</b></div>
        <div class="room-shelf"><span>✦</span><span>◇</span><span>▣</span><small>TROPHIES</small></div>
        <div class="room-chest-art"><span>▣</span><small>ARMORY</small></div>
        <div class="room-plant-art" aria-hidden="true"><i></i><b></b><em></em><small>GROW</small></div>
        <div class="room-pantry-art" aria-hidden="true"><i></i><b></b><small>PANTRY</small></div>
        <div class="room-hearth-art"><i></i><b>⌂</b><small>HEARTH</small></div>
        <div class="room-desk-art"><span>▤</span><i></i><small>STUDY</small></div>
        <div class="room-door-art" aria-hidden="true"><span>⌄</span><small>ENTRY</small></div>
        <div class="room-rug"></div>
        <button type="button" class="room-upgrade-niche ${roomUpgradePanelOpen ? 'active' : ''}" data-action="toggle-room-upgrades" aria-expanded="${roomUpgradePanelOpen}"><span>${roomUpgradePanelOpen ? '×' : '＋'}</span><strong>ROOM UPGRADES</strong><small>${builtRoomUpgrades.length}/${ROOM_UPGRADES.length} stations built · ${roomUpgradePanelOpen ? 'close list' : 'open list'}</small></button>
        <button type="button" class="room-hotspot hearth ${focus === 'hearth' ? 'active' : ''}" data-action="home-focus" data-focus="hearth"><span>${icon('heart')}</span><strong>Hearth</strong><small>Recover HP</small></button>
        <button type="button" class="room-hotspot armory ${focus === 'armory' ? 'active' : ''}" data-action="home-focus" data-focus="armory"><span>${icon('shield')}</span><strong>Armory</strong><small>Equip kit</small></button>
        <button type="button" class="room-hotspot pantry ${focus === 'pantry' ? 'active' : ''}" data-action="home-focus" data-focus="pantry"><span>＋</span><strong>Pantry</strong><small>Pack supplies</small></button>
        <button type="button" class="room-hotspot study ${focus === 'study' ? 'active' : ''}" data-action="home-focus" data-focus="study"><span>${icon('spark')}</span><strong>Study desk</strong><small>Spend tokens</small></button>
        <button type="button" class="room-hotspot pyr ${focus === 'pyr' ? 'active' : ''}" data-action="home-focus" data-focus="pyr"><span>✦</span><strong>Pyr’s perch</strong><small>${pyrStage.label}</small></button>
        <div class="room-pyr-sprite ${pyrStage.id}" aria-hidden="true"><span>✦</span><i></i></div>
        <div class="room-pyr-label"><strong>PYR</strong><small>${pyrStage.label} · bond ${pyr.bond}</small></div>
      </section>
      <section class="home-context-panel"><div class="home-context-mark">${focusIcon}</div><span class="eyebrow">${focusCopy[0].toUpperCase()}</span><h3>${focusCopy[1]}</h3><p>${focusCopy[2]}</p>${focusCopy[3]}${focus === 'pyr' ? `<div class="pyr-bond-meter"><div><span>BOND</span><strong>${pyr.bond}${nextPyrStage ? ` / ${nextPyrStage.threshold}` : ' · MAX'}</strong></div><i><b style="width:${nextPyrStage ? Math.min(100, (pyr.bond / nextPyrStage.threshold) * 100) : 100}%"></b></i><small>Training energy ${pyr.energy}/${pyr.maxEnergy}. Evolution is a companion milestone, not a hidden answer bonus.</small></div>` : ''}<div class="home-resume"><span class="eyebrow">NEXT STEP</span><strong>${selectedContract().title}</strong>${button('Return to Bounty Office', 'go-office', { icon: 'arrow', kind: 'ghost' })}</div></section>
    </div>
    <section class="home-upgrade-drawer ${roomUpgradePanelOpen ? 'open' : ''}" aria-label="Homestead upgrades" ${roomUpgradePanelOpen ? '' : 'hidden'}><div class="home-upgrade-drawer-head"><div><span class="eyebrow">BUILD THE HOMESTEAD</span><h3>Room upgrades</h3><p>Spend upgrade tokens on small, authored stat and trinket effects. Nothing here changes the code you must write.</p></div><span class="home-upgrade-token-pill">${state.upgradeTokens} TOKENS</span></div><div class="room-upgrade-grid">${roomUpgradeCopy}</div><div class="home-achievement-heading"><span class="eyebrow">ROOM HISTORY</span><strong>Achievement plaques</strong><small>Proof of cool work, not another currency.</small></div><div class="home-achievement-grid">${achievementCopy}</div></section>
    <div class="home-status-row"><span><small>HP</small><strong>${state.hp}/${state.maxHp}</strong></span><span><small>UPGRADE TOKENS</small><strong>${state.upgradeTokens}</strong></span><span><small>SUPPLIES</small><strong>${state.supplies?.bandages || 0} bandages · ${state.supplies?.tonics || 0} tonics · ${state.supplies?.meals || 0} meals</strong></span></div>
    <section class="loadout-section">
      <div class="section-heading"><div><span class="eyebrow">LIVE LOADOUT</span><h3>Armor and trinkets</h3></div><span class="section-help">Buy in Market · equip here</span></div>
      <div class="loadout-grid">
        <div class="loadout-slot"><span class="eyebrow">ARMOR</span><div class="equip-list">${armor.length ? armor.map((item) => `<button type="button" class="equip-card ${state.selectedArmorId === item.id ? 'equipped' : ''}" data-action="equip-armor" data-item-id="${item.id}"><span class="equip-symbol">${icon('shield')}</span><span><strong>${item.name}</strong><small>${item.detail}</small></span><b>${state.selectedArmorId === item.id ? 'EQUIPPED' : 'EQUIP'}</b></button>`).join('') : '<p class="empty-copy">No armor owned yet.</p>'}</div></div>
        <div class="loadout-slot"><span class="eyebrow">TRINKET</span><div class="equip-list">${trinkets.length ? trinkets.map((item) => `<button type="button" class="equip-card ${state.selectedTrinketId === item.id ? 'equipped' : ''}" data-action="equip-trinket" data-item-id="${item.id}"><span class="equip-symbol">${icon('spark')}</span><span><strong>${item.name}</strong><small>${item.detail}</small></span><b>${state.selectedTrinketId === item.id ? 'EQUIPPED' : 'EQUIP'}</b></button>`).join('') : '<p class="empty-copy">Visit Market to find your first trinket.</p>'}</div></div>
      </div>
    </section>
    <section class="supply-strip"><span class="eyebrow">PACKED SUPPLIES</span><span>Bandages <strong>${state.supplies?.bandages || 0}</strong></span><span>Ember tonics <strong>${state.supplies?.tonics || 0}</strong></span><span>Meals <strong>${state.supplies?.meals || 0}</strong></span><small>Use supplies from the encounter kit.</small></section>
    <section class="progress-card"><div><span class="eyebrow">RECENTLY CLEARED</span><h3>${state.completedContracts.length ? `${state.completedContracts.length} task${state.completedContracts.length === 1 ? '' : 's'} recorded` : 'No cleared work yet'}</h3></div><p>${state.completedContracts.length ? 'Your rewards are part of the same local prototype state as Market and Bounty Office.' : 'Take a contract from the Bounty Office to start the loop.'}</p></section>`
}

function renderMarket() {
  const merchantName = state.merchantNameKnown ? 'Rook' : 'The Merchant'
  const merchantPossessive = state.merchantNameKnown ? 'Rook’s' : 'The Merchant’s'
  const category = state.marketCategory || 'All'
  const categories = ['All', 'Armor', 'Trinket', 'Supply']
  const visibleStock = category === 'All' ? MARKET_STOCK : MARKET_STOCK.filter((item) => item.kind === category)
  const selectedItem = visibleStock.find((item) => item.id === state.selectedMarketItemId) || visibleStock[0] || MARKET_STOCK[0]
  const selectedOwned = selectedItem && (state.ownedTrinkets.includes(selectedItem.id) || state.ownedArmor.includes(selectedItem.id))
  const selectedSupplyCount = selectedItem?.id === 'field-bandage' ? state.supplies?.bandages || 0 : selectedItem?.id === 'ember-tonic' ? state.supplies?.tonics || 0 : selectedItem?.id === 'camp-meal' ? state.supplies?.meals || 0 : 0
  const selectedRarity = selectedItem?.price >= 120 ? 'RARE' : selectedItem?.price >= 70 ? 'UNCOMMON' : 'COMMON'
  return `
    <div class="place-heading">
      <div><span class="eyebrow">MARKET · AUCTION HOUSE</span><h2>${state.marketOpen ? 'Browse today’s lots.' : `${merchantName} has a case for you.`}</h2><p>${merchantName} rotates useful armor, trinkets, and supplies. The market changes your preparation, never the answer you need to learn.</p></div>
      <span class="place-seal place-seal-market">◇</span>
    </div>
    ${state.marketOpen ? `<div class="market-browser"><div class="market-browser-head"><div><span class="eyebrow">${merchantName.toUpperCase()}’S OPEN LOTS</span><h3>Browse and choose your preparation.</h3></div><div class="market-browser-actions"><span class="market-purse-pill">${icon('coin')} ${state.coins} coins</span>${button(`Back to ${merchantName}`, 'toggle-market', { icon: 'back', kind: 'ghost' })}</div></div><div class="market-browser-grid"><nav class="market-category-rail" aria-label="Market categories"><span class="eyebrow">CATEGORIES</span>${categories.map((entry) => `<button type="button" class="market-category ${category === entry ? 'active' : ''}" data-action="market-category" data-category="${entry}">${entry === 'All' ? 'All lots' : entry === 'Supply' ? 'Supplies' : `${entry}s`}<small>${entry === 'All' ? MARKET_STOCK.length : MARKET_STOCK.filter((item) => item.kind === entry).length}</small></button>`).join('')}</nav><section class="market-lot-list" aria-label="Available market lots"><div class="market-list-head"><span>LOT</span><span>TYPE</span><span>PRICE</span></div>${visibleStock.map((item) => { const owned = state.ownedTrinkets.includes(item.id) || state.ownedArmor.includes(item.id); const supplyCount = item.id === 'field-bandage' ? state.supplies?.bandages || 0 : item.id === 'ember-tonic' ? state.supplies?.tonics || 0 : item.id === 'camp-meal' ? state.supplies?.meals || 0 : 0; const rarity = item.price >= 120 ? 'RARE' : item.price >= 70 ? 'UNCOMMON' : 'COMMON'; return `<button type="button" class="market-lot-row ${selectedItem?.id === item.id ? 'active' : ''} ${owned ? 'owned' : ''}" data-action="select-market-item" data-item-id="${item.id}"><span class="market-lot-icon">${item.icon}</span><span class="market-lot-copy"><strong>${item.name}</strong><small><b class="market-rarity rarity-${rarity.toLowerCase()}">${rarity}</b> · ${item.detail}${item.kind === 'Supply' ? ` · ${supplyCount} owned` : ''}</small></span><span class="market-lot-kind">${item.kind}</span><strong class="market-lot-price">${item.price}<small> coins</small></strong></button>` }).join('')}</section><aside class="market-item-detail">${selectedItem ? `<span class="eyebrow">SELECTED LOT · ${selectedItem.kind.toUpperCase()}</span><div class="market-detail-icon">${selectedItem.icon}</div><span class="market-rarity rarity-${selectedRarity.toLowerCase()}">${selectedRarity}</span><h3>${selectedItem.name}</h3><p>${selectedItem.detail}</p><div class="market-detail-facts"><span><small>PRICE</small><strong>${selectedItem.price} coins</strong></span><span><small>${selectedItem.kind === 'Supply' ? 'OWNED' : 'STATUS'}</small><strong>${selectedItem.kind === 'Supply' ? selectedSupplyCount : selectedOwned ? 'OWNED' : 'AVAILABLE'}</strong></span></div>${selectedOwned ? '<span class="market-owned-note">Already in your kit · equip it from Home.</span>' : button('Buy this lot', 'buy-item', { icon: 'coin', itemId: selectedItem.id, className: 'market-buy-button', disabled: state.coins < selectedItem.price })}</aside>` : '<p class="empty-copy">No lots in this category.</p>'}</div></div><div class="market-footer"><span>${icon('shield')}</span><p>Armor protects HP. Trinkets shape Guard Breaks and protection. Supplies are consumed from the encounter kit.</p></div>` : `<section class="market-greeting"><div class="market-vendor-scene"><div class="vendor-lantern">✦</div><div class="vendor-portrait merchant-pixel-sprite" aria-hidden="true">${merchantPixelSprite()}</div><div class="vendor-counter"></div><div class="vendor-nameplate"><span class="eyebrow">SHOPKEEPER NPC</span><strong>${merchantName}</strong></div></div><div class="market-greeting-copy"><span class="eyebrow">WELCOME, TRAVELLER</span><h3>“Coins open the case. Knowledge keeps you alive.”</h3><p>${merchantPossessive} shelf changes between expeditions. Browse the lots when you are ready to prepare, then equip your finds at Home.</p>${button('Browse today’s lots', 'toggle-market', { icon: 'arrow', className: 'market-browse-button' })}<small>Single-player market · no bidding · buy only what helps your next learning job.</small></div><aside class="market-greeting-purse"><span class="eyebrow">YOUR PURSE</span><strong>${icon('coin')} ${state.coins}</strong><small>${MARKET_STOCK.length} lots waiting in the case</small></aside></section>`}`
}

function contractCard(contract) {
  const done = state.completedContracts.includes(contract.id)
  const selected = state.selectedContractId === contract.id
  const unlocked = isContractUnlocked(state, contract)
  const prerequisite = prerequisiteFor(contract)
  const statusLabel = done ? 'CLEARED' : unlocked ? 'OPEN' : 'LOCKED'
  const lockCopy = prerequisite ? ` · COMPLETE ${prerequisite.title.toUpperCase()} TO UNLOCK` : ''
  return `<button type="button" class="contract-card ${selected ? 'active' : ''} ${done ? 'complete' : ''} ${!unlocked ? 'locked' : ''}" aria-label="${escapeHtml(`${contract.title} · ${statusLabel}${lockCopy}`)}" data-action="select-contract" data-contract-id="${contract.id}"><span class="contract-mark ${contract.type} ${!unlocked ? 'locked-mark' : ''}">${!unlocked ? icon('lock') : contract.type === 'main' ? '✦' : '＋'}</span><span class="contract-copy"><small>${contract.label.toUpperCase()} · ${contract.concept}</small><strong>${contract.title}</strong><em>${unlocked ? contract.npc : `Complete ${prerequisite?.title || 'the previous bounty'} to unlock`}</em></span><span class="contract-status">${done ? icon('check') : unlocked ? icon('arrow') : icon('lock')}<small>${statusLabel}</small></span></button>`
}

function renderOffice() {
  const visible = CONTRACTS.filter((entry) => entry.type === 'main')
  const contract = selectedContract()
  const done = state.completedContracts.includes(contract.id)
  const unlocked = isContractUnlocked(state, contract)
  const prerequisite = prerequisiteFor(contract)
  const mainBounties = CONTRACTS.filter((entry) => entry.type === 'main')
  const boards = mainBountyBoards()
  const boardIndex = Math.max(0, Math.min(boards.length - 1, Number(state.officeBoardIndex) || 0))
  const boardEntries = boards[boardIndex] || boards[0]
  const completedMain = mainBounties.filter((entry) => state.completedContracts.includes(entry.id)).length
  const nextBounty = mainBounties.find((entry) => !state.completedContracts.includes(entry.id))
  const unlockedMain = mainBounties.filter((entry) => isContractUnlocked(state, entry)).length
  return `
    <div class="place-heading office-heading">
      <div><span class="eyebrow">BOUNTY OFFICE · PROJECT BOARD</span><h2>Choose the work that moves you forward.</h2><p>Read the board like a chain of jobs: open marks can be taken now, while locked marks tell you exactly which lesson must come first.</p></div>
      <span class="place-seal place-seal-office">✦</span>
    </div>
    <div class="office-tabs office-tabs-single"><span class="office-tab-label active">MAIN BOUNTIES <span>${visible.length}</span></span><span class="office-tab-note">Village tasks move to the Village board in the next slice.</span></div>
      <section class="board-status office-board-status" aria-label="Bounty board status">
      <div class="section-label"><span>BOUNTY BOARD · ${mainBounties.length} MARKS</span><strong>${completedMain}/${mainBounties.length} CLEARED</strong></div>
      <div class="board-switcher" aria-label="Switch bounty board">
        <button type="button" class="board-switch" data-action="office-board" data-board-index="${boardIndex - 1}" ${boardIndex === 0 ? 'disabled' : ''}>← PREVIOUS BOARD</button>
        <span><strong>BOARD ${boardIndex + 1} / ${boards.length}</strong><small>${boardEntries.length} pinned ${boardEntries.length === 1 ? 'notice' : 'notices'} · max ${BOUNTY_BOARD_SIZE}</small></span>
        <button type="button" class="board-switch" data-action="office-board" data-board-index="${boardIndex + 1}" ${boardIndex === boards.length - 1 ? 'disabled' : ''}>NEXT BOARD →</button>
      </div>
      <div class="bounty-posters" aria-label="Main bounty posters on this board">
        ${boardEntries.map((entry, index) => {
          const complete = state.completedContracts.includes(entry.id)
          const entryUnlocked = isContractUnlocked(state, entry)
          const prerequisite = prerequisiteFor(entry)
          const rank = entry.rank || 'mob'
          return `<button type="button" class="bounty-poster pin-slot-${index + 1} poster-size-${rank} ${complete ? 'complete' : entryUnlocked ? 'open' : 'locked'}" data-action="select-contract" data-contract-id="${entry.id}" aria-label="${escapeHtml(entryUnlocked ? `${entry.title} · ${rank} · ${entry.concept} · ${entry.boardSignal} · ${entry.boardValue}` : `${entry.title} · hidden bounty · complete ${prerequisite?.title || 'the previous bounty'} to unlock`)}"><span class="poster-pin" aria-hidden="true"></span><span class="poster-art">${entryUnlocked ? `<span class="poster-threat">${rank.toUpperCase()}</span><span class="poster-icon">${icon(entry.boardIcon || 'spark')}</span>` : '<span class="poster-silhouette" aria-hidden="true"><i></i></span>'}</span><span class="poster-signal ${entry.boardSignal?.toLowerCase() || 'reward'}">${entryUnlocked ? entry.boardSignal : 'LOCKED'}<strong>${entryUnlocked ? entry.boardValue : 'UNKNOWN'}</strong></span><span class="poster-copy"><strong>${entryUnlocked ? entry.title : 'HIDDEN BOUNTY'}</strong><p>${entryUnlocked ? entry.boardCopy : `Complete ${prerequisite?.title || 'the previous bounty'} to reveal this mark.`}</p><small>${entryUnlocked ? `${entry.concept} · ${entry.npc}` : 'A sealed notice waits behind the next lesson.'}</small></span></button>`
        }).join('')}
      </div>
      <p>${nextBounty ? `${nextBounty.title} is the next board mark. ${unlockedMain} of ${mainBounties.length} bounties are open across ${boards.length} boards.` : 'All main bounties are cleared. The project boss can be unlocked in the next slice.'}</p>
    </section>
    <div class="office-grid office-detail-grid">
      <section class="contract-detail board-detail ${contract.type === 'side' ? 'side-detail' : ''} ${!unlocked ? 'locked-detail' : ''}">
        <div class="detail-top"><span class="detail-badge">${!unlocked ? 'Locked bounty' : contract.label}</span><span class="detail-chapter">${contract.chapter}</span></div>
        <h3>${contract.title}</h3><p class="detail-npc">${contract.npc}</p>
        <div class="detail-story"><span class="eyebrow">THE TASK</span><p>${contract.brief}</p></div>
        <div class="detail-grid"><div><span class="eyebrow">CONCEPT</span><strong>${contract.concept}</strong></div><div><span class="eyebrow">GUARD WEAKNESS</span><strong>${contract.weakness}</strong></div></div>
        <div class="detail-mechanic"><span>${icon('shield')}</span><div><span class="eyebrow">ENCOUNTER NOTE</span><p>${contract.mechanic}</p></div></div>
        <div class="reward-preview"><div><span class="eyebrow">REWARD</span><strong>${contract.reward}</strong></div><small>${contract.rewardRare}</small></div>
        ${done ? `<div class="complete-banner">${icon('check')} <span>Recorded in your campaign history.</span></div>` : unlocked ? button(contract.type === 'side' ? 'Help with this task' : 'Take this bounty', 'take-contract', { icon: 'arrow', className: 'primary-cta' }) : `<div class="unlock-banner">${icon('lock')}<div><strong>COMPLETE ${escapeHtml(prerequisite?.title || 'THE PREVIOUS BOUNTY')}</strong><p>This mark opens after its prerequisite is cleared. Nothing is lost by choosing it early.</p></div></div>${button(`Locked · complete ${prerequisite?.title || 'the previous bounty'}`, 'locked-contract', { icon: 'lock', className: 'primary-cta locked-cta', disabled: true })}`}
      </section>
    </div>`
}

function renderPrep() {
  const contract = activeContract()
  const armor = itemById(state.selectedArmorId)
  const trinket = itemById(state.selectedTrinketId)
  return `<div class="stage-shell prep-stage"><div class="stage-top"><button type="button" class="text-button" data-action="back-office">${icon('back')} Bounty Office</button><span class="stage-crumb">PREPARE · ${contract.title}</span></div><div class="stage-heading"><span class="eyebrow">BEFORE THE FORGE</span><h2>Study the target. Tune the kit.</h2><p>Preparation can protect you from the mob’s mechanic, but it never supplies the coding answer.</p></div><div class="prep-grid"><section class="dossier-card"><div class="dossier-crest">✦</div><span class="eyebrow">${contract.label}</span><h3>${contract.title}</h3><p>${contract.brief}</p><div class="dossier-line"><span>Concept</span><strong>${contract.concept}</strong></div><div class="dossier-line"><span>Weakness</span><strong>${contract.weakness}</strong></div><div class="dossier-line"><span>Mechanic</span><strong>${contract.mechanic}</strong></div></section><section class="prep-actions"><span class="eyebrow">YOUR PREP</span><h3>What are you bringing?</h3><div class="prep-choice"><span class="prep-choice-icon">${icon('shield')}</span><div><strong>${armor?.name || 'No armor selected'}</strong><small>${armor?.detail || 'Choose armor from Home.'}</small></div>${button('Change in Home', 'go-home', { kind: 'ghost', className: 'small-button' })}</div><div class="prep-choice"><span class="prep-choice-icon">${icon('spark')}</span><div><strong>${trinket?.name || 'No trinket selected'}</strong><small>${trinket?.detail || 'Buy a trinket in Market, then equip it from Home.'}</small></div>${button('Open Home', 'go-home', { kind: 'ghost', className: 'small-button' })}</div><div class="prep-rule"><span>${icon('check')}</span><p>One encounter. One objective. One validated submission decides the result.</p></div>${button('Enter Forge', 'start-encounter', { icon: 'arrow', className: 'primary-cta' })}</section></div></div>`
}

function renderTerminalLine(line) {
  return `<div class="raw-terminal-line" data-kind="${escapeHtml(line.kind)}">${escapeHtml(line.text)}</div>`
}

function renderRawTerminal({ channel, title, subtitle, prompt, provider = false }) {
  const terminal = ensureTerminalState()
  const connection = terminal.connections[channel] || 'connected'
  const lines = terminalLines(channel)
  const connectionLabel = connection === 'connecting' ? 'CONNECTING' : connection.toUpperCase()
  const heading = provider ? `${channel} · Tiny Code-Flame` : 'Terminal'
  return `<section class="raw-terminal terminal-window ${provider ? 'pyr-terminal' : 'self-check-terminal'}" data-terminal="${escapeHtml(channel)}" data-connection="${escapeHtml(connection)}"><header class="raw-terminal-head"><div><span class="eyebrow">${escapeHtml(title)}</span><h3>${escapeHtml(heading)}</h3><small>${escapeHtml(subtitle)}</small></div><span class="connection-badge"><i></i>${connectionLabel}</span></header>${provider ? `<div class="ai-provider-row raw-terminal-provider-row" role="tablist" aria-label="Choose which AI is PYR"><span class="ai-provider-label">PYR CHANNEL</span>${AI_PROVIDERS.map((entry) => `<button type="button" class="ai-provider ${channel === entry ? 'active' : ''}" data-action="select-ai" data-provider="${entry}" role="tab" aria-selected="${channel === entry}">${entry}</button>`).join('')}<button type="button" class="ai-provider ai-provider-clear" data-action="clear-ai">Clear</button></div>` : ''}<div class="raw-terminal-scrollback" aria-live="polite" data-autoscroll="true">${lines.map(renderTerminalLine).join('')}</div><div class="raw-terminal-input-line ${provider ? 'static-input-line' : ''}"><span class="terminal-prompt">${escapeHtml(prompt)}</span>${provider ? '<span class="terminal-static-text">channel output only · use the controls above</span><i class="cursor-block cursor-static" aria-hidden="true"></i>' : '<input class="terminal-input" data-terminal-input="selfCheck" aria-label="Bounded local command" autocomplete="off" spellcheck="false" placeholder="type help, run, clear, or reconnect"><i class="cursor-block" aria-hidden="true"></i>'}</div><footer class="raw-terminal-foot"><span>${icon(provider ? 'spark' : 'check')}</span><p>${provider ? 'PYR feedback is bounded to room events and submissions. It does not write the answer for you.' : 'Local self-check only. No campaign state changes.'}</p><button type="button" class="ai-reconnect" data-action="${provider ? 'reconnect-ai' : 'reconnect-terminal'}">Reconnect</button></footer></section>`
}

function renderEncounter() {
  ensureTerminalState()
  const contract = activeContract()
  const encounter = state.encounter
  const armor = itemById(state.selectedArmorId)
  const trinket = itemById(state.selectedTrinketId)
  const guardPercent = encounter ? Math.max(0, Math.min(100, encounter.guard / encounter.maxGuard * 100)) : 100
  const stunned = encounter?.status === 'stunned'
  const provider = state.aiProvider || 'Codex'
  return `<div class="stage-shell encounter-stage"><div class="stage-top"><span class="stage-crumb">FORGE · ACTIVE CONTRACT</span><span class="lock-pill">${icon('lock')} MAP LOCKED DURING SUBMISSION</span></div><div class="encounter-layout"><aside class="encounter-brief"><span class="eyebrow">CURRENT BOUNTY</span><h2>${contract.title}</h2><p>${contract.objective}</p><div class="brief-rule"></div><span class="eyebrow">WEAKNESS SIGNAL</span><strong>${contract.weakness}</strong><span class="eyebrow">WHY IT MATTERS</span><p class="muted-copy">Break the Guard to create a safe opening. The complete Forge solution is still the Finisher.</p><div class="encounter-kit"><div class="kit-heading"><span class="eyebrow">YOUR KIT</span><small>use during the encounter</small></div><div class="kit-row"><span class="kit-symbol">${icon('shield')}</span><div><strong>${armor?.name || 'No armor equipped'}</strong><small>${armor?.detail || 'Equip armor at Home.'}</small></div></div><div class="kit-row"><span class="kit-symbol">${icon('spark')}</span><div><strong>${trinket?.name || 'No trinket equipped'}</strong><small>${trinket?.detail || 'Equip a trinket at Home.'}</small></div></div><div class="kit-actions">${button(`Bandage · ${state.supplies?.bandages || 0}`, 'use-bandage', { icon: 'heart', kind: 'ghost', className: 'small-button', disabled: !state.supplies?.bandages || state.hp >= state.maxHp })}${button(`Meal · ${state.supplies?.meals || 0}`, 'use-meal', { icon: 'spark', kind: 'ghost', className: 'small-button', disabled: !state.supplies?.meals || state.hp >= state.maxHp })}${button(`Tonic · ${state.supplies?.tonics || 0}`, 'use-tonic', { icon: 'spark', kind: 'ghost', className: 'small-button', disabled: !state.supplies?.tonics || Boolean(encounter?.tonicActive) })}</div>${encounter?.tonicActive ? '<div class="tonic-primed">TONIC PRIMED · next failed submission is softened</div>' : ''}</div><div class="left-combat-card ${stunned ? 'stunned' : ''}"><div class="combat-card-top"><div><span class="eyebrow">${contract.type === 'side' ? 'VILLAGE TASK' : 'MOB PROFILE'}</span><h3>${contract.title}</h3></div><span class="phase-chip">${stunned ? 'STUNNED' : 'GUARDED'}</span></div><div class="guard-heading"><span>GUARD</span><strong>${encounter.guard}/${encounter.maxGuard}</strong></div><div class="guard-track"><i style="width:${guardPercent}%"></i></div><div class="resolve-readout"><span>YOUR RESOLVE IMPACT</span><strong>+${encounter.resolveImpact || 1}</strong></div><div class="mechanic-box"><span class="eyebrow">MOB MECHANIC</span><strong>${stunned ? 'Suppressed for this window' : contract.mechanic}</strong><p>${stunned ? 'A failed submission cannot trigger the primary mechanic during this safe opening.' : 'Break Guard to interrupt this mechanic before you commit.'}</p></div>${stunned ? `<div class="stun-banner">${icon('spark')} <span>SAFE WINDOW · one submission</span></div>` : ''}</div></aside><main class="forge-card"><div class="forge-toolbar"><div><span class="file-dot"></span><strong>blackjack.py</strong><small>active Forge file · local prototype</small></div><div class="forge-toolbar-actions">${button('Save', 'save-draft', { kind: 'ghost' })}${button('Run', 'run-check', { kind: 'ghost' })}${button('Submit', 'submit', { icon: 'arrow', className: 'primary-cta' })}</div></div><div class="fake-editor" contenteditable="true" role="textbox" aria-label="Prototype Forge editor" spellcheck="false"><span class="code-muted"># ${escapeHtml(contract.objective)}</span><br><br><span class="code-key">total</span> <span class="code-op">=</span> <span class="code-num">0</span><br><span class="code-key">for</span> card <span class="code-key">in</span> cards:<br>&nbsp;&nbsp;&nbsp;&nbsp;<span class="code-muted"># write your attempt here</span><br><br><span class="code-key">print</span>(total)</div><div class="prototype-validator"><div><span class="eyebrow">DESIGN LAB CONTROL</span><strong>Simulate validated weakness evidence</strong><small>This button stands in for the future AST/runtime validator so we can test the Guard Break presentation without inventing an answer.</small></div>${button(stunned ? 'Guard broken' : 'Verify checkpoint', 'verify-checkpoint', { kind: 'ghost', className: 'small-button', disabled: stunned })}</div>${renderRawTerminal({ channel: 'selfCheck', title: 'LOCAL TERMINAL', subtitle: 'bounded commands · no campaign state changed', prompt: 'forge@questlab:~$' })}</main><aside>${renderRawTerminal({ channel: provider, title: 'PYR / AI TERMINAL', subtitle: 'raw local channel · output only', prompt: `${provider.toLowerCase()}@questlab:~$`, provider })}</aside></div></div>`
}

function createRailSizeControls(rail) {
  const controls = document.createElement('div')
  controls.className = 'rail-size-controls'
  for (const [label, delta, title] of [['−', -24, 'Narrow rail'], ['＋', 24, 'Widen rail']]) {
    const control = document.createElement('button')
    control.type = 'button'
    control.className = 'rail-size-step'
    control.dataset.action = 'resize-step'
    control.dataset.rail = rail
    control.dataset.delta = String(delta)
    control.title = title
    control.setAttribute('aria-label', title)
    control.textContent = label
    controls.append(control)
  }
  return controls
}

function decorateEncounterRails() {
  const layout = document.querySelector('.encounter-layout')
  if (!layout) return
  layout.style.cssText = encounterLayoutStyle()
  const [left, , right] = [...layout.children]
  if (!left || !right) return
  if (!left.dataset.railDecorated) {
    const leftContent = document.createElement('div')
    leftContent.className = 'left-rail-content'
    while (left.firstChild) leftContent.append(left.firstChild)
    const leftCompact = document.createElement('div')
    leftCompact.className = 'collapsed-rail-summary'
    leftCompact.innerHTML = '<span class="collapsed-rail-glyph">✦</span><strong>BOUNTY</strong><small>RAIL</small>'
    const leftToggle = document.createElement('button')
    leftToggle.type = 'button'
    leftToggle.className = 'rail-toggle rail-toggle-left'
    leftToggle.dataset.action = 'toggle-left-rail'
    leftToggle.title = 'Collapse bounty rail'
    leftToggle.setAttribute('aria-label', 'Collapse bounty rail')
    const leftResizer = document.createElement('button')
    leftResizer.type = 'button'
    leftResizer.className = 'rail-resizer rail-resizer-left'
    leftResizer.dataset.action = 'resize-rail'
    leftResizer.dataset.rail = 'left'
    leftResizer.title = 'Drag to resize bounty rail'
    leftResizer.setAttribute('aria-label', 'Resize bounty rail')
    left.append(leftContent, leftCompact, createRailSizeControls('left'), leftToggle, leftResizer)
    left.dataset.railDecorated = 'true'

    right.classList.add('encounter-pyr-rail')
    const rightContent = document.createElement('div')
    rightContent.className = 'right-rail-content'
    while (right.firstChild) rightContent.append(right.firstChild)
    const rightCompact = document.createElement('div')
    rightCompact.className = 'collapsed-rail-summary'
    rightCompact.innerHTML = '<span class="collapsed-rail-glyph">✦</span><strong>PYR</strong><small>AI</small>'
    const rightToggle = document.createElement('button')
    rightToggle.type = 'button'
    rightToggle.className = 'rail-toggle rail-toggle-right'
    rightToggle.dataset.action = 'toggle-right-rail'
    rightToggle.title = 'Collapse PYR rail'
    rightToggle.setAttribute('aria-label', 'Collapse PYR rail')
    const rightResizer = document.createElement('button')
    rightResizer.type = 'button'
    rightResizer.className = 'rail-resizer rail-resizer-right'
    rightResizer.dataset.action = 'resize-rail'
    rightResizer.dataset.rail = 'right'
    rightResizer.title = 'Drag to resize PYR rail'
    rightResizer.setAttribute('aria-label', 'Resize PYR rail')
    right.append(rightContent, rightCompact, createRailSizeControls('right'), rightToggle, rightResizer)
    right.dataset.railDecorated = 'true'
  }
  const forge = layout.querySelector('.forge-card')
  const forgeToolbar = forge?.querySelector('.forge-toolbar')
  const forgeActions = forge?.querySelector('.forge-actions')
  const forgeToolbarMeta = forgeToolbar?.querySelector('small')
  if (forgeToolbarMeta) forgeToolbarMeta.textContent = 'local prototype · Shift+Enter run · Shift+S save'
  const localTerminal = forge?.querySelector('.self-check-terminal')
  const localTerminalEyebrow = localTerminal?.querySelector('.raw-terminal-head .eyebrow')
  const localTerminalHeading = localTerminal?.querySelector('.raw-terminal-head h3')
  const localTerminalSubtitle = localTerminal?.querySelector('.raw-terminal-head small')
  if (localTerminalEyebrow) localTerminalEyebrow.textContent = 'TERMINAL'
  if (localTerminalHeading) localTerminalHeading.textContent = 'Terminal'
  if (localTerminalSubtitle) localTerminalSubtitle.textContent = 'local shell · output and commands'
  // The local pane is intentionally a terminal, not a second explanatory
  // card.  Keep the prompt and scrollback, but remove the footer copy and
  // reconnect affordance that made the bottom pane feel crowded.
  localTerminal?.querySelector('.raw-terminal-foot')?.remove()
  if (forgeToolbar && forgeActions && !forgeToolbar.querySelector('.forge-toolbar-actions')) {
    const actionRow = forgeActions.querySelector('.action-row')
    const toolbarActions = document.createElement('div')
    toolbarActions.className = 'forge-toolbar-actions'
    if (actionRow) while (actionRow.firstChild) toolbarActions.append(actionRow.firstChild)
    const saveButton = document.createElement('button')
    saveButton.type = 'button'
    saveButton.className = 'button button-ghost toolbar-save'
    saveButton.dataset.action = 'save-draft'
    saveButton.title = 'Save local draft (Shift+S)'
    saveButton.innerHTML = '<span>Save</span>'
    toolbarActions.insertBefore(saveButton, toolbarActions.firstChild)
    forgeToolbar.append(toolbarActions)
    forgeActions.remove()
  }
  const toolbarActions = forgeToolbar?.querySelector('.forge-toolbar-actions')
  const runButton = toolbarActions?.querySelector('[data-action="run-check"]')
  const submitButton = toolbarActions?.querySelector('[data-action="submit"]')
  if (runButton) {
    runButton.title = 'Run self-check (Shift+Enter)'
    runButton.setAttribute('aria-label', 'Run self-check (Shift+Enter)')
    const label = runButton.querySelector('span')
    if (label) label.textContent = 'Run'
  }
  if (submitButton) {
    submitButton.title = 'Submit to PYR (Ctrl/Cmd+Shift+Enter)'
    submitButton.setAttribute('aria-label', 'Submit to PYR (Ctrl/Cmd+Shift+Enter)')
    const label = submitButton.querySelector('span')
    if (label) label.textContent = 'Submit'
  }
  forge?.querySelector('.forge-mode')?.remove()
  left.classList.toggle('rail-is-collapsed', encounterLayout.leftCollapsed)
  right.classList.toggle('rail-is-collapsed', encounterLayout.rightCollapsed)
  const leftToggle = left.querySelector('.rail-toggle')
  const rightToggle = right.querySelector('.rail-toggle')
  if (leftToggle) {
    leftToggle.textContent = encounterLayout.leftCollapsed ? '›' : '‹'
    leftToggle.title = encounterLayout.leftCollapsed ? 'Expand bounty rail' : 'Collapse bounty rail'
    leftToggle.setAttribute('aria-label', leftToggle.title)
  }
  if (rightToggle) {
    rightToggle.textContent = encounterLayout.rightCollapsed ? '‹' : '›'
    rightToggle.title = encounterLayout.rightCollapsed ? 'Expand PYR rail' : 'Collapse PYR rail'
    rightToggle.setAttribute('aria-label', rightToggle.title)
  }
}

function renderResult() {
  const contract = activeContract()
  const alreadyDone = state.completedContracts.includes(contract.id)
  return `<div class="stage-shell result-stage"><div class="result-card"><span class="result-sigil">${icon('check')}</span><span class="eyebrow">VALIDATED FINISHER</span><h2>${contract.title} cleared.</h2><p>The full Forge submission passed. The mob’s Guard state mattered for the fight, but correctness remained the only way to finish it.</p><div class="reward-stack"><div><span class="eyebrow">GUARANTEED</span><strong>+${contract.type === 'side' ? 24 : 40} coins</strong></div><div><span class="eyebrow">POSSIBLE RARE REWARD</span><strong>${contract.rewardRare}</strong></div></div>${alreadyDone ? '<p class="muted-copy">This reward has already been claimed.</p>' : button('Claim reward and return to office', 'claim-reward', { icon: 'arrow', className: 'primary-cta' })}</div></div>`
}

function renderMapView() {
  const content = state.place === 'home' ? renderHome() : state.place === 'market' ? renderMarket() : renderOffice()
  return renderMapShell(content)
}

function render() {
  const body = state.screen === 'map' ? renderMapView() : state.screen === 'prep' ? renderPrep() : state.screen === 'encounter' ? renderEncounter() : renderResult()
  app.innerHTML = `${renderHeader()}${body}<div class="toast pyr-toast ${state.lastEvent ? 'visible' : ''}" role="status">${icon('spark')}<span class="pyr-toast-label">PYR</span><span>${escapeHtml(state.lastEvent)}</span></div>`
  decorateEncounterRails()
}

app.addEventListener('pointerdown', (event) => {
  const handle = event.target.closest?.('[data-action="resize-rail"]')
  if (handle) beginRailDrag(event, handle.dataset.rail)
})

window.addEventListener('pointermove', moveRailDrag)
window.addEventListener('pointerup', endRailDrag)

app.addEventListener('click', (event) => {
  const target = event.target.closest('[data-action]')
  if (!target || target.disabled) return
  const action = target.dataset.action
  if (action === 'toggle-left-rail') {
    encounterLayout.leftCollapsed = !encounterLayout.leftCollapsed
    saveEncounterLayout()
    render()
  } else if (action === 'toggle-map-rail') {
    mapRailCollapsed = !mapRailCollapsed
    try { localStorage.setItem(MAP_RAIL_KEY, String(mapRailCollapsed)) } catch {
      // Map rail preference is best effort in the isolated prototype.
    }
    render()
  } else if (action === 'toggle-right-rail') {
    encounterLayout.rightCollapsed = !encounterLayout.rightCollapsed
    saveEncounterLayout()
    render()
  } else if (action === 'resize-step') {
    const rail = target.dataset.rail === 'right' ? 'right' : 'left'
    const delta = Number(target.dataset.delta) || 0
    const bounds = rail === 'left' ? [220, 440] : [260, 480]
    encounterLayout[rail] = Math.round(Math.max(bounds[0], Math.min(bounds[1], encounterLayout[rail] + delta)))
    saveEncounterLayout()
    updateEncounterLayoutWidths()
  } else if (action === 'select-place') apply(selectPlace(state, target.dataset.place))
  else if (action === 'home-focus') {
    state.homeFocus = target.dataset.focus || 'hearth'
    state.lastEvent = `${state.homeFocus[0].toUpperCase()}${state.homeFocus.slice(1)} selected.`
    render()
  } else if (action === 'toggle-room-upgrades') {
    state.roomUpgradePanelOpen = !state.roomUpgradePanelOpen
    state.homeFocus = 'study'
    state.lastEvent = state.roomUpgradePanelOpen ? 'Room upgrades opened.' : 'Room upgrades closed.'
    render()
  } else if (action === 'toggle-market') {
    state.marketOpen = !state.marketOpen
    if (state.marketOpen) {
      const firstVisible = (state.marketCategory === 'All' ? MARKET_STOCK : MARKET_STOCK.filter((item) => item.kind === state.marketCategory))[0]
      if (firstVisible) state.selectedMarketItemId = firstVisible.id
    }
    const merchantName = state.merchantNameKnown ? 'Rook' : 'The Merchant'
    state.lastEvent = state.marketOpen ? `${merchantName} opened today’s auction lots.` : `${merchantName} closed the auction case.`
    render()
  } else if (action === 'market-category') {
    state.marketCategory = target.dataset.category || 'All'
    const firstVisible = (state.marketCategory === 'All' ? MARKET_STOCK : MARKET_STOCK.filter((item) => item.kind === state.marketCategory))[0]
    if (firstVisible) state.selectedMarketItemId = firstVisible.id
    state.lastEvent = `${state.marketCategory === 'All' ? 'All lots' : `${state.marketCategory}s`} shown.`
    render()
  } else if (action === 'select-market-item') {
    state.selectedMarketItemId = target.dataset.itemId || state.selectedMarketItemId
    const item = MARKET_STOCK.find((entry) => entry.id === state.selectedMarketItemId)
    state.lastEvent = item ? `${item.name} selected.` : state.lastEvent
    render()
  }
  else if (action === 'office-tab') {
    state.officeTab = target.dataset.tab
    const first = CONTRACTS.find((entry) => entry.type === state.officeTab)
    if (first) state.selectedContractId = first.id
    state.lastEvent = `${state.officeTab === 'main' ? 'Main bounty' : 'Village task'} board opened.`
    render()
  } else if (action === 'select-contract') apply(selectContract(state, target.dataset.contractId))
  else if (action === 'office-board') apply(setOfficeBoard(state, target.dataset.boardIndex))
  else if (action === 'take-contract') apply(openPreparation(state))
  else if (action === 'back-office' || action === 'back-map') {
    state.screen = 'map'
    state.place = 'office'
    state.lastEvent = 'Bounty Office opened.'
    render()
  } else if (action === 'go-home') {
    state.screen = 'map'
    state.place = 'home'
    state.lastEvent = 'Home opened. Your active contract is waiting.'
    render()
  } else if (action === 'go-market') {
    state.screen = 'map'
    state.place = 'market'
    state.marketOpen = false
    state.lastEvent = `Market opened. ${state.merchantNameKnown ? 'Rook' : 'The Merchant'} is waiting at the case.`
    render()
  } else if (action === 'go-office') {
    state.screen = 'map'
    state.place = 'office'
    state.lastEvent = 'Bounty Office opened. Choose the next learning job.'
    render()
  } else if (action === 'start-encounter') {
    ensureTerminalState()
    apply(startEncounter(state))
    seedEncounterTerminal()
    render()
  }
  else if (action === 'run-check') {
    const next = runSelfCheck(state)
    recordStateEvent(next, 'selfCheck', 'forge@questlab:~$ python blackjack.py --check')
    apply(next)
  }
  else if (action === 'save-draft') {
    ensureTerminalState()
    appendTerminal('selfCheck', 'prompt', 'forge@questlab:~$ save')
    appendTerminal('selfCheck', 'output', 'Draft saved locally. No combat state changed.')
    state.lastEvent = 'Forge draft saved locally.'
    render()
  }
  else if (action === 'verify-checkpoint') {
    const next = verifyGuardCheckpoint(state)
    recordStateEvent(next, 'selfCheck', 'forge@questlab:~$ verify checkpoint')
    appendTerminal(state.aiProvider || 'Codex', 'output', next.lastEvent)
    apply(next)
  }
  else if (action === 'submit') {
    const next = state.encounter?.status === 'stunned' ? submitSuccess(state) : submitFailure(state)
    recordStateEvent(next, state.aiProvider || 'Codex', `${(state.aiProvider || 'Codex').toLowerCase()}@questlab:~$ submit`)
    apply(next)
  }
  else if (action === 'claim-reward') apply(claimReward(state))
  else if (action === 'recover') apply(recoverAtHome(state))
  else if (action === 'spend-token') apply(spendUpgradeToken(state))
  else if (action === 'buy-room-upgrade') apply(purchaseRoomUpgrade(state, target.dataset.itemId))
  else if (action === 'use-bandage') apply(useBandage(state))
  else if (action === 'use-meal') apply(useMeal(state))
  else if (action === 'use-tonic') apply(useTonic(state))
  else if (action === 'feed-pyr') apply(feedPyr(state))
  else if (action === 'train-pyr') apply(trainPyr(state))
  else if (action === 'select-ai') {
    const nextProvider = AI_PROVIDERS.includes(target.dataset.provider) ? target.dataset.provider : 'Codex'
    ensureTerminalState()
    state.aiProvider = nextProvider
    state.lastEvent = `${nextProvider} selected as PYR's terminal channel.`
    appendTerminal(nextProvider, 'system', `${nextProvider} channel selected as PYR.`)
    appendTerminal(nextProvider, 'output', state.lastEvent)
    render()
  } else if (action === 'clear-ai') {
    ensureTerminalState()
    resetTerminalChannel(state.aiProvider || 'Codex')
    state.events = []
    state.lastEvent = `${state.aiProvider || 'Codex'} channel cleared.`
    appendTerminal(state.aiProvider || 'Codex', 'system', state.lastEvent)
    render()
  } else if (action === 'reconnect-ai') {
    ensureTerminalState()
    const channel = state.aiProvider || 'Codex'
    state.terminal.connections[channel] = 'connecting'
    appendTerminal(channel, 'system', `${channel} channel reconnecting...`)
    state.terminal.connections[channel] = 'connected'
    appendTerminal(channel, 'system', `${channel} channel reconnected in the design lab.`)
    state.lastEvent = `${channel} channel reconnected in the design lab.`
    render()
  } else if (action === 'reconnect-terminal') {
    ensureTerminalState()
    state.terminal.connections.selfCheck = 'connected'
    appendTerminal('selfCheck', 'system', 'Forge shell reconnected. No campaign state changed.')
    state.lastEvent = 'Forge shell reconnected. No campaign state changed.'
    render()
  }
  else if (action === 'buy-item') apply(buyItem(state, target.dataset.itemId))
  else if (action === 'equip-armor') apply(equipArmor(state, target.dataset.itemId))
  else if (action === 'equip-trinket') apply(equipTrinket(state, target.dataset.itemId))
})

app.addEventListener('keydown', (event) => {
  const editor = event.target.closest?.('.fake-editor')
  if (editor) {
    const key = event.key.toLowerCase()
    const invoke = (action) => app.querySelector(`[data-action="${action}"]`)?.click()
    const submitShortcut = key === 'enter' && event.ctrlKey && event.shiftKey
    const runShortcut = key === 'enter' && (event.shiftKey || (event.ctrlKey && !event.shiftKey))
    const saveShortcut = key === 's' && (event.shiftKey || event.ctrlKey) && !event.altKey
    const formatShortcut = key === 'f' && event.shiftKey && event.altKey
    if (submitShortcut) {
      event.preventDefault()
      invoke('submit')
    } else if (runShortcut) {
      event.preventDefault()
      invoke('run-check')
    } else if (saveShortcut) {
      event.preventDefault()
      invoke('save-draft')
    } else if (formatShortcut) {
      event.preventDefault()
      ensureTerminalState()
      appendTerminal('selfCheck', 'prompt', 'forge@questlab:~$ format')
      appendTerminal('selfCheck', 'output', 'Format preview ready. The design-lab editor keeps your draft unchanged.')
      state.lastEvent = 'Format preview ready; draft unchanged.'
      render()
    }
    return
  }
  const input = event.target.closest?.('[data-terminal-input="selfCheck"]')
  if (!input) return
  const terminal = ensureTerminalState()
  if (event.key === 'Enter') {
    event.preventDefault()
    runBoundedTerminalCommand(input.value)
    input.value = ''
    return
  }
  if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
  event.preventDefault()
  const history = terminal.commandHistory || []
  if (!history.length) return
  const current = Number.isInteger(terminal.historyIndex) ? terminal.historyIndex : history.length
  terminal.historyIndex = event.key === 'ArrowUp' ? Math.max(0, current - 1) : Math.min(history.length, current + 1)
  input.value = history[terminal.historyIndex] || ''
})

render()
