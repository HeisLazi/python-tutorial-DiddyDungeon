export const POIS = [
  {
    id: 'home',
    icon: '⌂',
    label: 'Home',
    kicker: 'REST · LOADOUT · PROGRESS',
    summary: 'Recover, tune your kit, grow Pyr, and spend the upgrade tokens you earn from village work.',
  },
  {
    id: 'market',
    icon: '◇',
    label: 'Market',
    kicker: 'ROTATING STOCK · COINS',
    summary: 'Meet the Merchant, then browse armor, trinkets, and supplies before you take another contract.',
  },
  {
    id: 'office',
    icon: '✦',
    label: 'Bounty Office',
    kicker: 'MAIN BOUNTIES',
    summary: 'Choose the next learning contract. Village work will live on its own board later.',
  },
]

export const ARMOR = [
  { id: 'scout-mail', name: 'Scout Mail', detail: 'Softens the first failure of an encounter.', price: 0, owned: true },
  { id: 'debugger-plate', name: 'Debugger Plate', detail: 'Makes the next mechanic hit less punishing.', price: 72, owned: false },
  { id: 'keeper-mail', name: 'Keeper Mail', detail: 'Boss set armor with a stronger guard against final-phase damage.', price: 0, owned: false },
]

export const TRINKETS = [
  { id: 'syntax-ward', name: 'Syntax Ward', kind: 'Ward', detail: 'Reduces syntax-error retaliation.', price: 48, owned: false },
  { id: 'siphon-scythe', name: 'Siphon Scythe', kind: 'Sustain', detail: 'Restores HP after a verified Guard Break.', price: 86, owned: false },
  { id: 'old-greatsword', name: 'Old Warrior’s Greatsword', kind: 'Guard', detail: 'Adds extra protection after clean learning work.', price: 92, owned: false },
  { id: 'scimitar-of-momentum', name: 'Scimitar of Momentum', kind: 'Breaker', detail: 'Improves Resolve impact against an authored weakness.', price: 110, owned: false },
]

export const BOUNTY_BOARD_SIZE = 7

// Pyr is a companion loop for the Home interior. Bond milestones are
// deliberately presentation-first in this prototype: feeding and training
// change Pyr's state and evolution, but never secretly change a learner's
// coding result.
export const PYR_STAGES = [
  { id: 'spark', label: 'Tiny Code-Flame', threshold: 0, detail: 'A curious little watcher that keeps the hearth bright.' },
  { id: 'ember', label: 'Emberling', threshold: 3, detail: 'A warmer companion with a steadier glow.' },
  { id: 'flare', label: 'Flarekin', threshold: 6, detail: 'A bright companion ready for a bigger homestead.' },
]

// Home upgrades are deliberately small, authored modifiers. They turn the
// homestead into a place the learner can improve without replacing the room
// with a static illustration or changing the coding requirement.
export const ROOM_UPGRADES = [
  { id: 'reinforced-hearth', name: 'Reinforced Hearth', kind: 'STAT', cost: 1, effect: 'MAX HP +10', detail: 'A stronger hearth gives you ten more maximum HP.', maxHpDelta: 10 },
  { id: 'warding-loom', name: 'Warding Loom', kind: 'TRINKET', cost: 2, effect: 'RETALIATION −2', detail: 'Threaded syntax wards soften each failed submission by 2 HP.', failureDamageReduction: 2 },
  { id: 'breaker-workbench', name: 'Breaker Workbench', kind: 'STAT', cost: 2, effect: 'BREAK +1', detail: 'Tune your kit to break Guard one Resolve point faster.', resolveImpactDelta: 1 },
  { id: 'siphon-basin', name: 'Siphon Basin', kind: 'TRINKET', cost: 3, effect: 'BREAK HEAL +4', detail: 'A clean Guard Break restores 4 HP before the final submit.', guardBreakHeal: 4 },
  { id: 'field-kitchen', name: 'Field Kitchen', kind: 'STAT', cost: 2, effect: 'MEALS +5', detail: 'Packed meals restore 5 extra HP when eaten at Home.', mealHealDelta: 5 },
]

// Achievement plaques are read-only proof of play. They never spend tokens;
// they simply turn memorable learner moments into visible room history.
export const HOME_ACHIEVEMENTS = [
  { id: 'first-mark', name: 'First Mark', icon: '✦', detail: 'Clear your first bounty.', unlock: (state) => state.completedContracts.length >= 1 },
  { id: 'clean-slate', name: 'Clean Slate', icon: '◇', detail: 'Finish an encounter without a rejected submit.', unlock: (state) => (state.stats?.cleanRuns || 0) >= 1 },
  { id: 'guardbreaker', name: 'Guardbreaker', icon: '◈', detail: 'Break a mob’s Guard before finishing it.', unlock: (state) => (state.stats?.guardBreaks || 0) >= 1 },
  { id: 'dealer-down', name: 'Dealer Down', icon: '♠', detail: 'Defeat The Dealer’s Hand.', unlock: (state) => state.completedContracts.includes('dealer-hand') },
]

const pyrStageForBond = (bond) => [...PYR_STAGES].reverse().find((stage) => bond >= stage.threshold) || PYR_STAGES[0]

export const CONTRACTS = [
  {
    id: 'count-keeper',
    type: 'main',
    label: 'Main bounty',
    title: 'The Count Keeper',
    npc: 'Ledger Hall · project chapter 01',
    concept: 'Loops and accumulators',
    objective: 'Count the odd cards without losing the running total.',
    brief: 'The keeper’s ledger is skipping entries. Build a small, readable loop that preserves its state and reports the result.',
    weakness: 'Guard weakness · a clear accumulator that is updated inside the loop.',
    mechanic: 'Scramble attempt · a failed submission can jumble one ordinary line.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible learning upgrade token',
    boardSignal: 'REWARD',
    boardValue: '+40 COINS',
    boardCopy: 'Restore the keeper’s running total and open the first safe mark.',
    boardIcon: 'spark',
    rank: 'mob',
    boardId: 0,
    chapter: 'Chapter 01 · State and repetition',
    guard: 10,
    phases: 1,
    prerequisiteId: null,
  },
  {
    id: 'loop-rehearsal',
    type: 'main',
    label: 'Main bounty',
    title: 'The Loop Rehearsal',
    npc: 'Practice yard · project chapter 01',
    concept: 'Loops and accumulators',
    objective: 'Repeat the check for every hand while keeping one total.',
    brief: 'The yard can repeat a move, but it loses the score between passes. Keep the accumulator alive as the loop does its work.',
    weakness: 'Guard weakness · initialise once, then update the same accumulator on each pass.',
    mechanic: 'Reset trap · a failed submission can clear one temporary attempt bonus.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible learning upgrade token',
    boardSignal: 'REWARD',
    boardValue: '+35 COINS',
    boardCopy: 'Keep a repeated check honest and open the second loop mark.',
    boardIcon: 'arrow',
    rank: 'mob',
    boardId: 0,
    chapter: 'Chapter 01 · State and repetition',
    guard: 10,
    phases: 1,
    prerequisiteId: 'count-keeper',
  },
  {
    id: 'accumulator-audit',
    type: 'main',
    label: 'Main bounty',
    title: 'The Accumulator Audit',
    npc: 'Ledger annex · project chapter 01',
    concept: 'Loops and accumulators',
    objective: 'Skip invalid cards without corrupting the running total.',
    brief: 'A second ledger is mixing valid and invalid entries. Filter the inputs without throwing away the state that the next pass needs.',
    weakness: 'Guard weakness · make the update rule visible at the point where the state changes.',
    mechanic: 'Lifesteal · a failed submission restores a little Guard.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible armor upgrade',
    boardSignal: 'WARNING',
    boardValue: 'LIFESTEAL',
    boardCopy: 'Audit the running total before the ledger pulls Guard back.',
    boardIcon: 'shield',
    rank: 'elite',
    boardId: 0,
    chapter: 'Chapter 01 · State and repetition',
    guard: 11,
    phases: 1,
    prerequisiteId: 'loop-rehearsal',
  },
  {
    id: 'house-ledger',
    type: 'main',
    label: 'Main bounty',
    title: 'The House Ledger',
    npc: 'Back room · project chapter 02',
    concept: 'Conditions and filtering',
    objective: 'Separate the hands that match the house rule.',
    brief: 'The house can read every card but cannot tell a match from a miss. Make the condition visible and testable.',
    weakness: 'Guard weakness · a condition that names the signal it is checking.',
    mechanic: 'Double strike · the next failed submission is harsher.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible rare trinket',
    boardSignal: 'WARNING',
    boardValue: 'DOUBLE STRIKE',
    boardCopy: 'A failed submission makes the house hit harder.',
    boardIcon: 'shield',
    rank: 'mob',
    boardId: 0,
    chapter: 'Chapter 02 · Decisions and filters',
    guard: 12,
    phases: 1,
    prerequisiteId: 'count-keeper',
  },
  {
    id: 'rule-sentinel',
    type: 'main',
    label: 'Main bounty',
    title: 'The Rule Sentinel',
    npc: 'Gatehouse · project chapter 02',
    concept: 'Conditions and filtering',
    objective: 'Route each card through a clear yes-or-no rule.',
    brief: 'The sentinel is guarding the right gate but cannot explain why. Turn the rule into a condition that can be checked one branch at a time.',
    weakness: 'Guard weakness · name the signal in the condition instead of hiding it in a shortcut.',
    mechanic: 'Double strike · the next failed submission is harsher.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible rare trinket',
    boardSignal: 'WARNING',
    boardValue: 'DOUBLE STRIKE',
    boardCopy: 'Make the gate’s decision readable before it hits twice.',
    boardIcon: 'shield',
    rank: 'elite',
    boardId: 0,
    chapter: 'Chapter 02 · Decisions and filters',
    guard: 12,
    phases: 1,
    prerequisiteId: 'house-ledger',
  },
  {
    id: 'filter-folio',
    type: 'main',
    label: 'Main bounty',
    title: 'The Filter Folio',
    npc: 'Archive desk · project chapter 02',
    concept: 'Conditions and filtering',
    objective: 'Keep only the hands that satisfy both clues.',
    brief: 'The archive has two clues for every hand, but the filter stops at the first one. Combine the checks without making the result mysterious.',
    weakness: 'Guard weakness · test the smallest condition first, then preserve the matching result.',
    mechanic: 'Scramble attempt · a failed submission can jumble one ordinary line.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible learning upgrade token',
    boardSignal: 'REWARD',
    boardValue: '+45 COINS',
    boardCopy: 'Sort two signals cleanly and open the function desk.',
    boardIcon: 'spark',
    rank: 'elite',
    boardId: 0,
    chapter: 'Chapter 02 · Decisions and filters',
    guard: 13,
    phases: 1,
    prerequisiteId: 'rule-sentinel',
  },
  {
    id: 'dealer-hand',
    type: 'main',
    label: 'Main bounty',
    title: 'The Dealer’s Hand',
    npc: 'Table seven · project chapter 03',
    concept: 'Functions and return values',
    objective: 'Give the dealer a reusable hand evaluator.',
    brief: 'The dealer keeps doing the same calculation by hand. Move the boundary into a function and return the result clearly.',
    weakness: 'Guard weakness · a function boundary with an explicit returned result.',
    mechanic: 'Lifesteal · a failed submission restores a little Guard.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible armor upgrade',
    boardSignal: 'REWARD',
    boardValue: '+40 COINS',
    boardCopy: 'Give the dealer a reusable evaluator and claim the next mark.',
    boardIcon: 'arrow',
    rank: 'boss',
    boardId: 1,
    chapter: 'Chapter 03 · Reusable logic',
    guard: 14,
    phases: 1,
    prerequisiteId: 'house-ledger',
  },
  {
    id: 'payout-function',
    type: 'main',
    label: 'Main bounty',
    title: 'The Payout Function',
    npc: 'Cashier booth · project chapter 03',
    concept: 'Functions and return values',
    objective: 'Return one reliable payout from a reusable helper.',
    brief: 'The cashier has copied the same calculation into three places. Give the logic one home and return the value every caller needs.',
    weakness: 'Guard weakness · define the input boundary and return the result explicitly.',
    mechanic: 'Lifesteal · a failed submission restores a little Guard.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible rare trinket',
    boardSignal: 'REWARD',
    boardValue: '+45 COINS',
    boardCopy: 'Give the payout one dependable home and claim a larger purse.',
    boardIcon: 'arrow',
    rank: 'mob',
    boardId: 1,
    chapter: 'Chapter 03 · Reusable logic',
    guard: 14,
    phases: 1,
    prerequisiteId: 'dealer-hand',
  },
  {
    id: 'shoe-shuffler',
    type: 'main',
    label: 'Main bounty',
    title: 'The Shoe Shuffler',
    npc: 'Shoe room · project chapter 03',
    concept: 'Functions and return values',
    objective: 'Compose small helpers to deal and score a hand.',
    brief: 'The shoe room is full of repeated work. Split the job into small functions that pass values back without losing the story of the hand.',
    weakness: 'Guard weakness · keep each helper focused and return the value the next helper needs.',
    mechanic: 'Double strike · the next failed submission is harsher.',
    reward: 'Coins + project progress',
    rewardRare: 'Possible armor upgrade',
    boardSignal: 'WARNING',
    boardValue: 'DOUBLE STRIKE',
    boardCopy: 'Compose the full hand cleanly before the shoe strikes back.',
    boardIcon: 'shield',
    rank: 'elite',
    boardId: 1,
    chapter: 'Chapter 03 · Reusable logic',
    guard: 16,
    phases: 1,
    prerequisiteId: 'payout-function',
  },
  {
    id: 'bakery-counter',
    type: 'side',
    label: 'Village task',
    title: 'The Bakery Counter',
    npc: 'Mara · east village',
    concept: 'Predict the output',
    objective: 'Work out how many loaves the counter prints.',
    brief: 'Mara’s counter is showing a strange total. Trace the values, then fix the tiny display routine.',
    weakness: 'Guard weakness · name the changing value before you follow it.',
    mechanic: 'No combat mechanic · this task is a safe learning errand.',
    reward: 'Coins',
    rewardRare: 'Occasional upgrade token',
    chapter: 'Village task · output tracing',
    guard: 6,
    phases: 1,
  },
  {
    id: 'courier-route',
    type: 'side',
    label: 'Village task',
    title: 'The Courier’s Route',
    npc: 'Tavi · south road',
    concept: 'Find a bug',
    objective: 'Find why one parcel is counted twice.',
    brief: 'Tavi has a short loop that almost works. Find the signal that makes one parcel appear twice.',
    weakness: 'Guard weakness · follow the state change that repeats unexpectedly.',
    mechanic: 'No combat mechanic · the danger is only losing the delivery bonus.',
    reward: 'Coins',
    rewardRare: 'Occasional trinket',
    chapter: 'Village task · bug hunting',
    guard: 5,
    phases: 1,
  },
  {
    id: 'watch-lanterns',
    type: 'side',
    label: 'Village task',
    title: 'The Watch Lanterns',
    npc: 'Ivo · north gate',
    concept: 'Tiny transfer challenge',
    objective: 'Make the lantern check work for a new patrol size.',
    brief: 'The watch has one working example but needs a small transfer to a different input without copying the whole answer.',
    weakness: 'Guard weakness · preserve the idea while changing only the input boundary.',
    mechanic: 'No combat mechanic · a clean solution earns the full tip.',
    reward: 'Coins',
    rewardRare: 'Occasional upgrade token',
    chapter: 'Village task · transfer practice',
    guard: 5,
    phases: 1,
  },
]

export const MARKET_STOCK = [
  { id: 'field-bandage', name: 'Field bandage', kind: 'Supply', detail: 'Recover during Home preparation.', price: 18, icon: '＋' },
  { id: 'ember-tonic', name: 'Ember tonic', kind: 'Supply', detail: 'A one-use buffer for the next encounter.', price: 32, icon: '✦' },
  { id: 'camp-meal', name: 'Camp meal', kind: 'Supply', detail: 'Restore a small amount of HP from the encounter kit.', price: 26, icon: '◇' },
  { id: 'debugger-plate', name: 'Debugger Plate', kind: 'Armor', detail: 'Makes the next mechanic hit less punishing.', price: 72, icon: '⬡' },
  { id: 'ledgerguard-coat', name: 'Ledgerguard Coat', kind: 'Armor', detail: 'A steadier guard against repeated failed submissions.', price: 118, icon: '▣' },
  { id: 'emberweave-mantle', name: 'Emberweave Mantle', kind: 'Armor', detail: 'Softens one heavy mechanic hit each encounter.', price: 146, icon: '◈' },
  { id: 'syntax-ward', name: 'Syntax Ward', kind: 'Trinket', detail: 'Reduces syntax-error retaliation.', price: 48, icon: '◈' },
  { id: 'loop-lens', name: 'Loop Lens', kind: 'Trinket', detail: 'Adds a little Guard Break impact when the weakness is a loop.', price: 64, icon: '◎' },
  { id: 'guard-bell', name: 'Guard Bell', kind: 'Trinket', detail: 'Telegraphs the first mechanic before it fires.', price: 78, icon: '◌' },
  { id: 'scimitar-of-momentum', name: 'Scimitar of Momentum', kind: 'Trinket', detail: 'Improves Guard Break impact.', price: 110, icon: '⚔' },
  { id: 'vision-scroll', name: 'Vision Scroll', kind: 'Trinket', detail: 'Reveal one hidden risk-room identity on the dungeon map.', price: 125, icon: '▤' },
]

export const createInitialState = () => ({
  screen: 'map',
  place: 'office',
  officeTab: 'main',
  officeBoardIndex: 0,
  selectedContractId: 'count-keeper',
  selectedArmorId: 'scout-mail',
  selectedTrinketId: null,
  ownedArmor: ['scout-mail'],
  ownedTrinkets: [],
  coins: 84,
  upgradeTokens: 1,
  hp: 84,
  maxHp: 100,
  supplies: { bandages: 1, tonics: 0, meals: 0 },
  aiProvider: 'Codex',
  marketCategory: 'All',
  activeContractId: null,
  encounter: null,
  homeFocus: 'hearth',
  marketOpen: false,
  roomUpgrades: [],
  roomUpgradePanelOpen: false,
  // The merchant's personal name is a lore unlock, not introductory UI copy.
  // Keeping the flag in prototype state lets the village discovery land later
  // without rewriting the market surface.
  merchantNameKnown: false,
  selectedMarketItemId: 'syntax-ward',
  pyr: { stage: 'spark', bond: 0, energy: 2, maxEnergy: 2, fedCount: 0, trainingCount: 0 },
  stats: { cleanRuns: 0, guardBreaks: 0, bossesDefeated: 0 },
  lastEvent: 'Choose a place. The map is a menu, not a route tree.',
  completedContracts: [],
  events: [],
})

const contractFor = (state) => CONTRACTS.find((entry) => entry.id === state.selectedContractId) || CONTRACTS[0]
const roomUpgradeOwned = (state, id) => (state.roomUpgrades || []).includes(id)
const roomUpgradeValue = (state, key) => (state.roomUpgrades || []).reduce((total, id) => {
  const upgrade = ROOM_UPGRADES.find((entry) => entry.id === id)
  return total + (Number(upgrade?.[key]) || 0)
}, 0)

export function isContractUnlocked(state, contractOrId) {
  const contract = typeof contractOrId === 'string'
    ? CONTRACTS.find((entry) => entry.id === contractOrId)
    : contractOrId
  return Boolean(contract) && (!contract.prerequisiteId || state.completedContracts.includes(contract.prerequisiteId))
}

export function prerequisiteFor(contractOrId) {
  const contract = typeof contractOrId === 'string'
    ? CONTRACTS.find((entry) => entry.id === contractOrId)
    : contractOrId
  return contract?.prerequisiteId ? CONTRACTS.find((entry) => entry.id === contract.prerequisiteId) : null
}

export function mainBountyBoards() {
  const main = CONTRACTS.filter((entry) => entry.type === 'main')
  const grouped = new Map()
  main.forEach((entry, index) => {
    const boardId = Number.isInteger(entry.boardId) ? entry.boardId : Math.floor(index / BOUNTY_BOARD_SIZE)
    const board = grouped.get(boardId) || []
    board.push(entry)
    grouped.set(boardId, board)
  })
  const boards = [...grouped.entries()]
    .sort(([first], [second]) => first - second)
    .flatMap(([, entries]) => {
      const pages = []
      for (let index = 0; index < entries.length; index += BOUNTY_BOARD_SIZE) pages.push(entries.slice(index, index + BOUNTY_BOARD_SIZE))
      return pages
    })
  return boards.length ? boards : [[]]
}

export function bountyBoardIndexFor(contractOrId) {
  const id = typeof contractOrId === 'string' ? contractOrId : contractOrId?.id
  const boardIndex = mainBountyBoards().findIndex((entries) => entries.some((entry) => entry.id === id))
  return boardIndex < 0 ? 0 : boardIndex
}

export function setOfficeBoard(state, requestedIndex) {
  const boards = mainBountyBoards()
  const parsed = Number(requestedIndex)
  const index = Number.isFinite(parsed)
    ? Math.max(0, Math.min(boards.length - 1, Math.trunc(parsed)))
    : 0
  const boardEntries = boards[index] || []
  const selectedContractId = boardEntries.some((entry) => entry.id === state.selectedContractId)
    ? state.selectedContractId
    : boardEntries[0]?.id || state.selectedContractId
  return {
    ...state,
    officeBoardIndex: index,
    officeTab: 'main',
    selectedContractId,
    place: 'office',
    screen: 'map',
    lastEvent: `Bounty board ${index + 1} of ${boards.length} opened.`,
  }
}

export function selectPlace(state, place) {
  if (!POIS.some((entry) => entry.id === place)) return state
  const selected = CONTRACTS.find((entry) => entry.id === state.selectedContractId)
  const officeReset = place === 'office' && selected?.type === 'side'
    ? { officeTab: 'main', selectedContractId: 'count-keeper' }
    : place === 'office'
      ? { officeTab: 'main' }
      : {}
  return { ...state, ...officeReset, place, screen: 'map', lastEvent: `${POIS.find((entry) => entry.id === place).label} opened.` }
}

export function selectContract(state, id) {
  if (!CONTRACTS.some((entry) => entry.id === id)) return state
  const contract = CONTRACTS.find((entry) => entry.id === id)
  const prerequisite = prerequisiteFor(contract)
  const unlocked = isContractUnlocked(state, contract)
  return {
    ...state,
    selectedContractId: id,
    officeTab: contract.type === 'side' ? 'side' : 'main',
    officeBoardIndex: contract.type === 'main' ? bountyBoardIndexFor(contract) : 0,
    lastEvent: unlocked
      ? `${contract.title} selected.`
      : `${contract.title} is locked. Complete ${prerequisite?.title || 'the previous bounty'} to unlock it.`,
  }
}

export function openPreparation(state) {
  const contract = contractFor(state)
  if (!isContractUnlocked(state, contract)) {
    const prerequisite = prerequisiteFor(contract)
    return {
      ...state,
      screen: 'map',
      place: 'office',
      activeContractId: null,
      encounter: null,
      lastEvent: `${contract.title} is locked. Complete ${prerequisite?.title || 'the previous bounty'} to unlock it.`,
    }
  }
  return {
    ...state,
    screen: 'prep',
    activeContractId: contract.id,
    encounter: null,
    lastEvent: `Prepare for ${contract.title}. Your equipment changes consequences, not the coding requirement.`,
  }
}

export function startEncounter(state) {
  const contract = CONTRACTS.find((entry) => entry.id === state.activeContractId) || contractFor(state)
  return {
    ...state,
    screen: 'encounter',
    activeContractId: contract.id,
    encounter: {
      guard: contract.guard,
      maxGuard: contract.guard,
      phase: 1,
      status: 'guarded',
      mechanicStatus: 'active',
      safeAttemptAvailable: false,
      resolveImpact: (state.selectedTrinketId === 'scimitar-of-momentum' ? 2 : 1) + roomUpgradeValue(state, 'resolveImpactDelta'),
      finalVerified: false,
      runCount: 0,
      submitCount: 0,
      failureCount: 0,
      guardBreakUsed: false,
      tonicActive: false,
    },
    lastEvent: `${contract.title} entered. Run is a self-check; Submit is the validator boundary.`,
  }
}

export function runSelfCheck(state) {
  if (!state.encounter) return state
  return {
    ...state,
    encounter: { ...state.encounter, runCount: state.encounter.runCount + 1 },
    lastEvent: 'Self-check complete. No Guard, HP, or rewards changed.',
  }
}

export function verifyGuardCheckpoint(state) {
  if (!state.encounter || state.encounter.status === 'defeated') return state
  if (state.encounter.status === 'stunned' || state.encounter.guard <= 0) return { ...state, lastEvent: 'Guard is already broken. Finish the active submission window.' }
  const breakHeal = roomUpgradeValue(state, 'guardBreakHeal')
  return {
    ...state,
    hp: Math.min(state.maxHp, state.hp + breakHeal),
    encounter: {
      ...state.encounter,
      guard: 0,
      status: 'stunned',
      mechanicStatus: 'suppressed',
      safeAttemptAvailable: true,
      guardBreakUsed: true,
    },
    lastEvent: `GUARD BROKEN · +${state.encounter.resolveImpact || 1} Resolve impact opened a safe submission window${breakHeal ? ` · +${breakHeal} HP from Siphon Basin` : ''}.`,
  }
}

export function submitFailure(state) {
  if (!state.encounter || state.encounter.status === 'defeated') return state
  const safe = state.encounter.status === 'stunned' && state.encounter.safeAttemptAvailable
  const tonicActive = Boolean(state.encounter.tonicActive)
  const retaliationReduction = roomUpgradeValue(state, 'failureDamageReduction')
  const damage = safe ? 0 : Math.max(1, (tonicActive ? 4 : 8) - retaliationReduction)
  const nextHp = Math.max(0, state.hp - damage)
  return {
    ...state,
    hp: nextHp,
    encounter: {
      ...state.encounter,
      submitCount: state.encounter.submitCount + 1,
      status: safe ? 'guarded' : state.encounter.status,
      mechanicStatus: safe ? 'active' : state.encounter.mechanicStatus,
      safeAttemptAvailable: false,
      tonicActive: false,
      failureCount: (state.encounter.failureCount || 0) + (safe ? 0 : 1),
    },
    lastEvent: safe
      ? 'Submission rejected, but the stunned mob could not retaliate. The safe window is spent.'
      : tonicActive
        ? `Submission rejected · Ember tonic softened the retaliation to ${damage} HP.`
        : `Submission rejected · the mob retaliates for ${damage} HP and the active mechanic fires.`,
  }
}

export function submitSuccess(state) {
  if (!state.encounter || state.encounter.status === 'defeated') return state
  return {
    ...state,
    encounter: { ...state.encounter, submitCount: state.encounter.submitCount + 1, finalVerified: true, status: 'defeated', mechanicStatus: 'disabled', safeAttemptAvailable: false },
    screen: 'result',
    lastEvent: 'FINISHER · the validator accepted the complete solution. The mob is defeated.',
  }
}

export function claimReward(state) {
  const contract = CONTRACTS.find((entry) => entry.id === state.activeContractId) || contractFor(state)
  const alreadyDone = state.completedContracts.includes(contract.id)
  if (alreadyDone) return { ...state, screen: 'map', place: 'office', lastEvent: `${contract.title} is already recorded.` }
  const coinReward = contract.type === 'side' ? 24 : 40
  const tokenReward = contract.type === 'side' && contract.id === 'bakery-counter' ? 1 : 0
  const encounter = state.encounter || {}
  const previousStats = state.stats || { cleanRuns: 0, guardBreaks: 0, bossesDefeated: 0 }
  const stats = {
    ...previousStats,
    cleanRuns: previousStats.cleanRuns + (encounter.failureCount === 0 ? 1 : 0),
    guardBreaks: previousStats.guardBreaks + (encounter.guardBreakUsed ? 1 : 0),
    bossesDefeated: previousStats.bossesDefeated + (contract.rank === 'boss' ? 1 : 0),
  }
  return {
    ...state,
    screen: 'map',
    place: 'office',
    coins: state.coins + coinReward,
    upgradeTokens: state.upgradeTokens + tokenReward,
    completedContracts: [...state.completedContracts, contract.id],
    stats,
    activeContractId: null,
    encounter: null,
    lastEvent: `${contract.title} cleared · +${coinReward} coins${tokenReward ? ' · +1 upgrade token' : ''}.`,
  }
}

export function buyItem(state, itemId) {
  const item = MARKET_STOCK.find((entry) => entry.id === itemId)
  if (!item || state.coins < item.price) return { ...state, lastEvent: item ? `Not enough coins for ${item.name}.` : 'That item is no longer on the shelf.' }
  const next = { ...state, coins: state.coins - item.price, lastEvent: `${item.name} purchased. Equip it from Home.` }
  if (item.kind === 'Trinket') return { ...next, ownedTrinkets: [...new Set([...state.ownedTrinkets, item.id])] }
  if (item.kind === 'Armor') return { ...next, ownedArmor: [...new Set([...state.ownedArmor, item.id])] }
  const inventoryKey = item.id === 'field-bandage' ? 'bandages' : item.id === 'ember-tonic' ? 'tonics' : 'meals'
  return { ...next, supplies: { ...state.supplies, [inventoryKey]: (state.supplies?.[inventoryKey] || 0) + 1 } }
}

export function equipArmor(state, id) {
  if (!state.ownedArmor.includes(id)) return state
  const armor = ARMOR.find((entry) => entry.id === id)
  return { ...state, selectedArmorId: id, lastEvent: `${armor?.name || 'Armor'} equipped.` }
}

export function equipTrinket(state, id) {
  if (!state.ownedTrinkets.includes(id)) return state
  const trinket = TRINKETS.find((entry) => entry.id === id) || MARKET_STOCK.find((entry) => entry.id === id)
  return { ...state, selectedTrinketId: id, lastEvent: `${trinket?.name || 'Trinket'} equipped.` }
}

export function recoverAtHome(state) {
  return { ...state, hp: state.maxHp, lastEvent: 'Home recovery complete. You are ready for the next contract.' }
}

export function useBandage(state) {
  const available = state.supplies?.bandages || 0
  if (!available) return { ...state, lastEvent: 'No field bandages left.' }
  if (state.hp >= state.maxHp) return { ...state, lastEvent: 'HP is already full.' }
  return {
    ...state,
    hp: Math.min(state.maxHp, state.hp + 20),
    supplies: { ...state.supplies, bandages: available - 1 },
    lastEvent: 'Field bandage used · +20 HP.',
  }
}

export function useTonic(state) {
  const available = state.supplies?.tonics || 0
  if (!available) return { ...state, lastEvent: 'No Ember tonics left.' }
  if (!state.encounter) return { ...state, lastEvent: 'Ember tonic can only be primed during an encounter.' }
  if (state.encounter.tonicActive) return { ...state, lastEvent: 'Ember tonic is already primed.' }
  return {
    ...state,
    supplies: { ...state.supplies, tonics: available - 1 },
    encounter: { ...state.encounter, tonicActive: true },
    lastEvent: 'Ember tonic primed · the next failed submission takes 4 HP instead of 8.',
  }
}

export function useMeal(state) {
  const available = state.supplies?.meals || 0
  if (!available) return { ...state, lastEvent: 'No camp meals left.' }
  if (state.hp >= state.maxHp) return { ...state, lastEvent: 'HP is already full.' }
  const heal = 10 + roomUpgradeValue(state, 'mealHealDelta')
  return {
    ...state,
    hp: Math.min(state.maxHp, state.hp + heal),
    supplies: { ...state.supplies, meals: available - 1 },
    lastEvent: `Camp meal eaten · +${heal} HP.`,
  }
}

export function spendUpgradeToken(state) {
  if (state.upgradeTokens < 1) return { ...state, lastEvent: 'No upgrade tokens available yet.' }
  return { ...state, upgradeTokens: state.upgradeTokens - 1, maxHp: state.maxHp + 5, hp: state.hp + 5, lastEvent: 'Upgrade token spent · your maximum HP improved for this prototype.' }
}

export function purchaseRoomUpgrade(state, id) {
  const upgrade = ROOM_UPGRADES.find((entry) => entry.id === id)
  if (!upgrade) return { ...state, lastEvent: 'That room upgrade is not available.' }
  if (roomUpgradeOwned(state, upgrade.id)) return { ...state, lastEvent: `${upgrade.name} is already built.` }
  if (state.upgradeTokens < upgrade.cost) return { ...state, lastEvent: `${upgrade.name} needs ${upgrade.cost} upgrade token${upgrade.cost === 1 ? '' : 's'}.` }
  const next = {
    ...state,
    upgradeTokens: state.upgradeTokens - upgrade.cost,
    roomUpgrades: [...(state.roomUpgrades || []), upgrade.id],
    roomUpgradePanelOpen: true,
    lastEvent: `${upgrade.name} built · ${upgrade.effect}.`,
  }
  if (upgrade.maxHpDelta) next.maxHp = state.maxHp + upgrade.maxHpDelta
  if (upgrade.maxHpDelta) next.hp = Math.min(next.maxHp, state.hp + upgrade.maxHpDelta)
  return next
}

export function feedPyr(state) {
  const available = state.supplies?.meals || 0
  if (!available) return { ...state, lastEvent: 'Pyr is hungry, but you have no camp meals packed.' }
  const current = state.pyr || { stage: 'spark', bond: 0, energy: 2, maxEnergy: 2, fedCount: 0, trainingCount: 0 }
  const bond = current.bond + 1
  const stage = pyrStageForBond(bond)
  const evolved = stage.id !== current.stage
  return {
    ...state,
    supplies: { ...state.supplies, meals: available - 1 },
    pyr: { ...current, bond, stage: stage.id, energy: Math.min(current.maxEnergy || 2, current.energy + 1), fedCount: (current.fedCount || 0) + 1 },
    lastEvent: evolved ? `Pyr evolved into ${stage.label} · bond ${bond}.` : 'Pyr enjoyed a meal · bond grew and energy returned.',
  }
}

export function trainPyr(state) {
  const current = state.pyr || { stage: 'spark', bond: 0, energy: 2, maxEnergy: 2, fedCount: 0, trainingCount: 0 }
  if (current.energy < 1) return { ...state, lastEvent: 'Pyr needs a meal before another training session.' }
  const bond = current.bond + 1
  const stage = pyrStageForBond(bond)
  const evolved = stage.id !== current.stage
  return {
    ...state,
    pyr: { ...current, bond, stage: stage.id, energy: current.energy - 1, trainingCount: (current.trainingCount || 0) + 1 },
    lastEvent: evolved ? `Pyr evolved into ${stage.label} · bond ${bond}.` : 'Training complete · Pyr is learning your rhythm.',
  }
}
