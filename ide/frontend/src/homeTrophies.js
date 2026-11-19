// A named boss trophy requires evidence on the campaign project itself.
// Aggregate counters and run records cannot identify a particular boss.
export function campaignBossTrophies(progress) {
  if (!Array.isArray(progress?.projects)) return []
  return progress.projects
    .filter((project) => project && (project.boss_status === 'defeated' || project.completed === true) && typeof project.boss === 'string' && project.boss.trim())
    .map((project, index) => ({
      id: String(project.branch || project.id || `${project.boss}-${index}`),
      boss: project.boss.trim(),
      campaign: project.name || project.branch || 'Campaign',
      date: project.completed_at || project.boss_clear?.recorded_at || null,
    }))
}
