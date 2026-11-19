// Reuse the existing Home bond thresholds and the existing mastery milestone.
// No separate companion progression counter is introduced.
export function homePyrStage(progress = {}) {
  const bond = Number(progress?.companion?.bond ?? 0)
  const shields = Number(progress?.stats?.mastery_shields_earned ?? 0)
  if (Number.isFinite(bond) && bond >= 6 && Number.isFinite(shields) && shields >= 3) return 4
  if (Number.isFinite(bond) && bond >= 6) return 3
  if (Number.isFinite(bond) && bond >= 3) return 2
  return 1
}
