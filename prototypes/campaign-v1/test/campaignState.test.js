import test from 'node:test'
import assert from 'node:assert/strict'
import {
  BOUNTY_BOARD_SIZE,
  CONTRACTS,
  HOME_ACHIEVEMENTS,
  ROOM_UPGRADES,
  bountyBoardIndexFor,
  createInitialState,
  isContractUnlocked,
  mainBountyBoards,
  selectPlace,
  selectContract,
  setOfficeBoard,
  openPreparation,
  prerequisiteFor,
  startEncounter,
  runSelfCheck,
  verifyGuardCheckpoint,
  submitFailure,
  submitSuccess,
  claimReward,
  purchaseRoomUpgrade,
  buyItem,
  useBandage,
  useMeal,
  useTonic,
  feedPyr,
  trainPyr,
} from '../src/campaignState.js'
import { merchantPixelSprite } from '../src/pixelArt.js'

test('merchant presentation uses a swappable pixel-frame contract', () => {
  const markup = merchantPixelSprite()
  assert.equal((markup.match(/pixel-sprite-frame/g) || []).length, 6)
  assert.equal((markup.match(/pixel-frame-grid/g) || []).length, 3)
  assert.equal((markup.match(/data-frame-width="24"/g) || []).length, 3)
  assert.equal((markup.match(/data-frame-height="32"/g) || []).length, 3)
  assert.equal((markup.match(/class="pixel-cell"/g) || []).length, 24 * 32 * 3)
  assert.doesNotMatch(markup, /<img\b/)
  assert.match(markup, /--pixel-color:#ffd15b/)
  assert.match(markup, /--pixel-color:#8f5a43/)
  assert.match(markup, /--pixel-color:#281c1d/)
  assert.match(markup, /--pixel-color:#e6a83c/)
})

test('the map is a three-POI menu, not a route graph', () => {
  const initial = createInitialState()
  assert.equal(initial.merchantNameKnown, false)
  const state = selectPlace(initial, 'home')
  assert.equal(state.place, 'home')
  assert.equal(state.screen, 'map')
})

test('the main bounty board opens in sequence and exposes its prerequisite', () => {
  const initial = createInitialState()
  assert.equal(isContractUnlocked(initial, 'count-keeper'), true)
  assert.equal(isContractUnlocked(initial, 'house-ledger'), false)
  assert.equal(prerequisiteFor('house-ledger')?.id, 'count-keeper')

  const selected = selectContract(initial, 'house-ledger')
  assert.equal(selected.selectedContractId, 'house-ledger')
  assert.match(selected.lastEvent, /Complete The Count Keeper to unlock/)

  const blocked = openPreparation(selected)
  assert.equal(blocked.screen, 'map')
  assert.equal(blocked.activeContractId, null)
  assert.match(blocked.lastEvent, /Complete The Count Keeper to unlock/)

  const afterFirst = { ...initial, completedContracts: ['count-keeper'] }
  assert.equal(isContractUnlocked(afterFirst, 'house-ledger'), true)
  assert.equal(isContractUnlocked(afterFirst, 'dealer-hand'), false)
})

test('the main board carries three examples for each core concept', () => {
  const main = CONTRACTS.filter((entry) => entry.type === 'main')
  assert.equal(main.length, 9)
  for (const concept of ['Loops and accumulators', 'Conditions and filtering', 'Functions and return values']) {
    assert.equal(main.filter((entry) => entry.concept === concept).length, 3)
  }
  assert.ok(main.every((entry) => Object.hasOwn(entry, 'boardCopy') && Object.hasOwn(entry, 'boardIcon')))
})

test('main bounty posters stay on switchable boards of at most seven marks', () => {
  const boards = mainBountyBoards()
  assert.equal(boards.length, 2)
  assert.ok(boards.every((board) => board.length <= BOUNTY_BOARD_SIZE))
  assert.equal(boards[0].length, 6)
  assert.equal(boards[1][0].id, 'dealer-hand')
  assert.equal(bountyBoardIndexFor('dealer-hand'), 1)
  const secondBoard = setOfficeBoard(createInitialState(), 99)
  assert.equal(secondBoard.officeBoardIndex, 1)
  assert.equal(secondBoard.selectedContractId, 'dealer-hand')
  assert.equal(setOfficeBoard(createInitialState(), -1).officeBoardIndex, 0)
})

test('Run is self-check only and does not mutate combat state', () => {
  let state = startEncounter(openPreparation(selectContract(createInitialState(), 'count-keeper')))
  const before = { hp: state.hp, guard: state.encounter.guard }
  state = runSelfCheck(state)
  assert.deepEqual({ hp: state.hp, guard: state.encounter.guard }, before)
})

test('Guard Break stuns and suppresses the mechanic without defeating the mob', () => {
  let state = startEncounter(openPreparation(selectContract(createInitialState(), 'count-keeper')))
  state = verifyGuardCheckpoint(state)
  assert.equal(state.encounter.status, 'stunned')
  assert.equal(state.encounter.mechanicStatus, 'suppressed')
  assert.equal(state.encounter.guard, 0)
  assert.equal(state.screen, 'encounter')
})

test('a failed submission during the safe window spends it without HP damage', () => {
  let state = startEncounter(openPreparation(selectContract(createInitialState(), 'count-keeper')))
  state = verifyGuardCheckpoint(state)
  state = submitFailure(state)
  assert.equal(state.hp, 84)
  assert.equal(state.encounter.safeAttemptAvailable, false)
  assert.equal(state.encounter.status, 'guarded')
})

test('the final correct submission is mandatory even after Guard Break', () => {
  let state = startEncounter(openPreparation(selectContract(createInitialState(), 'count-keeper')))
  state = verifyGuardCheckpoint(state)
  assert.equal(state.encounter.status, 'stunned')
  state = submitSuccess(state)
  assert.equal(state.encounter.status, 'defeated')
  assert.equal(state.screen, 'result')
})

test('rewards are awarded only after a defeated encounter', () => {
  let state = startEncounter(openPreparation(selectContract(createInitialState(), 'bakery-counter')))
  state = submitSuccess(state)
  state = claimReward(state)
  assert.equal(state.coins, 108)
  assert.equal(state.upgradeTokens, 2)
  assert.ok(state.completedContracts.includes('bakery-counter'))
})

test('the homestead exposes five authored room upgrades and builds a stat upgrade', () => {
  assert.equal(ROOM_UPGRADES.length, 5)
  assert.deepEqual(ROOM_UPGRADES.map((entry) => entry.kind), ['STAT', 'TRINKET', 'STAT', 'TRINKET', 'STAT'])
  const state = purchaseRoomUpgrade(createInitialState(), 'reinforced-hearth')
  assert.equal(state.upgradeTokens, 0)
  assert.equal(state.maxHp, 110)
  assert.equal(state.hp, 94)
  assert.deepEqual(state.roomUpgrades, ['reinforced-hearth'])
})

test('room upgrade modifiers are applied to encounter and home actions', () => {
  const built = ROOM_UPGRADES.map((entry) => entry.id)
  let state = { ...createInitialState(), roomUpgrades: built, hp: 70, supplies: { bandages: 0, tonics: 0, meals: 1 } }
  state = startEncounter(openPreparation(selectContract(state, 'count-keeper')))
  assert.equal(state.encounter.resolveImpact, 2)
  state = submitFailure(state)
  assert.equal(state.hp, 64)
  state = verifyGuardCheckpoint(state)
  assert.equal(state.hp, 68)
  state = useMeal({ ...state, encounter: null })
  assert.equal(state.hp, 83)
})

test('achievement plaques are read-only and unlock from campaign milestones', () => {
  const initial = createInitialState()
  assert.equal(HOME_ACHIEVEMENTS.filter((entry) => entry.unlock(initial)).length, 0)
  let state = startEncounter(openPreparation(selectContract(initial, 'count-keeper')))
  state = verifyGuardCheckpoint(state)
  state = submitSuccess(state)
  state = claimReward(state)
  const unlocked = HOME_ACHIEVEMENTS.filter((entry) => entry.unlock(state)).map((entry) => entry.id)
  assert.deepEqual(unlocked, ['first-mark', 'clean-slate', 'guardbreaker'])
  assert.equal(state.upgradeTokens, initial.upgradeTokens)
})

test('market purchases use the same purse that Home can see', () => {
  const state = buyItem(createInitialState(), 'syntax-ward')
  assert.equal(state.coins, 36)
  assert.ok(state.ownedTrinkets.includes('syntax-ward'))
})

test('encounter kit can consume a bandage and prime a one-use tonic', () => {
  let state = createInitialState()
  state = { ...state, hp: 60, supplies: { bandages: 1, tonics: 1 } }
  state = useBandage(state)
  assert.equal(state.hp, 80)
  assert.equal(state.supplies.bandages, 0)
  state = startEncounter(openPreparation(selectContract(state, 'count-keeper')))
  state = useTonic(state)
  assert.equal(state.supplies.tonics, 0)
  assert.equal(state.encounter.tonicActive, true)
  state = submitFailure(state)
  assert.equal(state.hp, 76)
  assert.equal(state.encounter.tonicActive, false)
})

test('the encounter kit can consume a meal without changing Guard', () => {
  const before = createInitialState()
  const state = useMeal({ ...before, hp: 70, supplies: { ...before.supplies, meals: 1 } })
  assert.equal(state.hp, 80)
  assert.equal(state.supplies.meals, 0)
  assert.equal(state.encounter, null)
})

test('Pyr can be fed and trained at Home without changing combat state', () => {
  let state = { ...createInitialState(), supplies: { bandages: 1, tonics: 0, meals: 1 } }
  const beforeCombat = state.encounter
  state = feedPyr(state)
  assert.equal(state.supplies.meals, 0)
  assert.equal(state.pyr.bond, 1)
  assert.equal(state.pyr.energy, 2)
  assert.equal(state.encounter, beforeCombat)
  state = trainPyr(state)
  assert.equal(state.pyr.bond, 2)
  assert.equal(state.pyr.energy, 1)
  assert.equal(state.screen, 'map')
})

test('Pyr evolves at a bond milestone and does not invent a combat reward', () => {
  let state = { ...createInitialState(), supplies: { bandages: 0, tonics: 0, meals: 3 } }
  state = feedPyr(state)
  state = trainPyr(state)
  state = trainPyr(state)
  assert.equal(state.pyr.stage, 'ember')
  assert.equal(state.pyr.bond, 3)
  assert.equal(state.coins, 84)
  assert.equal(state.upgradeTokens, 1)
})
