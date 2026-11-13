export function makeRaidCombatTurn(boss, raidId, userId) {
  if (!boss) return null
  const sequence = Math.max(0, Number(boss.attack_sequence) || 0)
  const attack = boss.last_attack || {}
  const passed = attack.type === 'hunter'
  const amount = Math.max(0, Number(attack.damage) || 0)
  const hpAfter = Math.max(0, Number(boss.hunter_hp?.[userId]) || 0)
  const maxResolve = Math.max(1, Number(boss.max_hp) || 1)
  const resolveAfter = Math.max(0, Math.min(maxResolve, Number(boss.hp) || 0))

  return {
    hpAfter,
    attack,
    result: {
      outcome: passed ? 'correct' : 'incorrect',
      damage: passed ? 0 : amount,
      evidence_id: `${raidId}-attack-${sequence}`,
      fight: {
        max_resolve: maxResolve,
        resolve_after: resolveAfter,
        resolve_before: passed ? Math.min(maxResolve, resolveAfter + amount) : resolveAfter,
        chip: passed ? amount : 0,
      },
    },
  }
}

export function raidCombatSummary({ result, fight = {}, turn, encounter = {}, damage = 0, blast = 0, simulated = false, raidMode = false }) {
  if (!result) return 'Awaiting your answer'
  if (result.outcome === 'correct') {
    const amount = Number(fight.chip ?? turn?.attack?.damage) || 0
    const actor = raidMode ? 'The hunters strike' : 'Tate strikes'
    return `${actor} for ${amount} Resolve${blast ? `; blast costs ${blast} HP` : ''}.`
  }
  if (raidMode && Number(damage) > 0 && turn?.attack?.type === 'aoe') {
    return `${encounter.name || 'The Chief'} hits the whole party for ${damage} HP each.`
  }
  if (raidMode && Number(damage) > 0) {
    return `${encounter.name || 'The Chief'} hits the submitting hunter for ${damage} HP.`
  }
  if (Number(damage) > 0) {
    return `${encounter.name || 'Enemy'} strikes for ${damage} ${simulated ? 'practice HP' : 'HP'}${blast ? `; blast costs ${blast} more` : ''}.`
  }
  return `The attack is guarded${blast ? `; blast costs ${blast} HP` : ''}.`
}
