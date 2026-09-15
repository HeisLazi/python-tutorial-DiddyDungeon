import { useEffect, useState } from 'react'

export const viewItems = [
  { id: 'forge', icon: '⌘', label: 'Forge' },
  { id: 'quests', icon: '⚔', label: 'Quest Journal' },
  { id: 'codex', icon: '▤', label: 'Codex' },
  { id: 'character', icon: '♙', label: 'Character' },
  { id: 'homestead', icon: '⌂', label: 'Homestead' },
  { id: 'dungeon', icon: '♜', label: 'Infinite Dungeon' },
  { id: 'practice', icon: '✦', label: 'Practice' },
  { id: 'settings', icon: '⚙', label: 'Settings' },
]

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))
const isMobDefeated = (status) => status === 'defeated' || status === 'cleared'

export function RewardQueue({ items = [] }) {
  if (!items.length) return null
  return (
    <div className="reward-queue" aria-live="polite" aria-label="Recent campaign rewards">
      {items.map((item) => (
        <article className={`reward-toast ${item.kind || ''}`} key={item.id}>
          <span className="reward-toast-kicker">{item.title}</span>
          <strong>{item.body}</strong>
          {item.detail && <small>{item.detail}</small>}
        </article>
      ))}
    </div>
  )
}

export function ActivityRail({ activeView, setActiveView, player }) {
  return (
    <nav className="activity-rail" aria-label="Quest Lab destinations">
      <div className="activity-mark">🔥</div>
      <div className="activity-stack">
        {viewItems.map((item) => (
          <button
            key={item.id}
            className={`activity-button ${activeView === item.id ? 'active' : ''}`}
            onClick={() => setActiveView(item.id)}
            title={item.label}
            aria-label={item.label}
          >
            <span>{item.icon}</span>
          </button>
        ))}
      </div>
      <button
        className={`activity-avatar ${activeView === 'character' ? 'active' : ''}`}
        onClick={() => setActiveView('character')}
        title={`${player.name || 'Player'} · Level ${player.level ?? 1}`}
      >
        <span>{(player.name || 'L').slice(0, 1).toUpperCase()}</span>
        <b>{player.level ?? 1}</b>
      </button>
    </nav>
  )
}

export function ContextPanel({ activeView, campaign, files, activePath, openFile, newFile, setActiveView }) {
  const progress = campaign?.progress || {}
  const player = progress.player || {}
  const activeProject = (progress.projects || []).find((project) => project.status === 'active')
  const skills = progress.skills || []
  const homestead = progress.homestead || {}
  const owned = homestead.owned_cosmetics || []

  if (activeView === 'forge') {
    return (
      <>
        <div className="panel-title">
          <span>FILES</span>
          <button onClick={newFile}>+</button>
        </div>
        <div className="workspace-label">{campaign?.workspace || 'loading workspace…'}</div>
        <div className="file-list">
          {files.map((item) => (
            <button
              key={item.path}
              className={`file-row ${activePath === item.path ? 'active' : ''} ${item.type}`}
              style={{ paddingLeft: `${10 + item.depth * 14}px` }}
              onClick={() => item.type === 'file' && openFile(item.path)}
              disabled={item.type !== 'file'}
            >
              <span>{item.type === 'dir' ? '▾' : '·'}</span>
              <span>{item.name}</span>
            </button>
          ))}
        </div>
      </>
    )
  }

  if (activeView === 'tutor') {
    return (
      <>
        <div className="panel-title">
          <span>TUTOR NOTEBOOK</span>
          <button onClick={() => setActiveView('forge')} title="Return to Forge">⌘</button>
        </div>
        <div className="context-scroll">
          <div className="context-kicker">COLLABORATIVE SCRATCH SPACE</div>
          <h3>tutor.py</h3>
          <p>PYR may write examples here. Your real project file stays player-authored.</p>
          <div className="boundary-card safe">
            <strong>PYR CAN WRITE</strong>
            <span>tutor.py</span>
          </div>
          <div className="boundary-card locked">
            <strong>PYR READ-ONLY</strong>
            <span>blackjack.py and other required project source</span>
          </div>
          <p className="context-note">The raw AI terminal is still a real shell, so this guarantee applies to the future controlled PYR toolset—not arbitrary CLI commands.</p>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="panel-title">
        <span>{viewItems.find((item) => item.id === activeView)?.label?.toUpperCase()}</span>
        <button onClick={() => setActiveView('forge')} title="Return to Forge">⌘</button>
      </div>
      <div className="context-scroll">
        {activeView === 'quests' && (
          <>
            <div className="context-kicker">ACTIVE CHAPTER</div>
            <h3>{activeProject?.name || 'No active quest'}</h3>
            <p>{progress.current_quest}</p>
            <div className="context-list">
              {(activeProject?.mobs || []).map((mob) => (
                <div key={mob.name} className={`context-row ${mob.status}`}>
                  <span>{mob.status === 'available' ? '◆' : isMobDefeated(mob.status) ? '✓' : '◇'}</span>
                  <span>{mob.name}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {activeView === 'codex' && (
          <>
            <div className="context-kicker">MASTERY INDEX</div>
            <div className="context-list">
              {skills.map((skill) => (
                <div key={skill.name} className="context-row stacked">
                  <strong>{skill.name}</strong>
                  <span>{skill.concept}</span>
                  <small>{skill.shield?.tier || 'no shield'}</small>
                </div>
              ))}
            </div>
          </>
        )}

        {activeView === 'character' && (
          <>
            <div className="context-kicker">CHARACTER SHEET</div>
            <h3>{player.name || 'Player'}</h3>
            <p>{player.title || 'Apprentice Coder'}</p>
            <div className="context-stat"><span>Rank</span><b>{player.rank || 'F'}</b></div>
            <div className="context-stat"><span>Level</span><b>{player.level ?? 1}</b></div>
            <div className="context-stat"><span>Coins</span><b>{player.coins ?? 0}c</b></div>
            <div className="context-stat"><span>HP</span><b>{player.hp ?? 100}/{player.max_hp ?? 100}</b></div>
          </>
        )}

        {activeView === 'homestead' && (
          <>
            <div className="context-kicker">YOUR PLACE</div>
            <h3>{homestead.name || 'The Forge'}</h3>
            <p>Build your coding home with cosmetics earned from real learning.</p>
            <div className="context-stat"><span>Coins</span><b>{player.coins ?? 0}c</b></div>
            <div className="context-stat"><span>Owned</span><b>{owned.length}</b></div>
          </>
        )}

        {activeView === 'dungeon' && (
          <>
            <div className="context-kicker">RUN CHECKPOINT</div>
            <h3>Infinite Dungeon</h3>
            <p>Each run starts with the starter armor, one heal and no trinket. The active checkpoint survives a restart.</p>
            <div className="context-row stacked">
              <strong>{campaign?.dungeon?.active ? `Floor ${campaign.dungeon.floor} · Room ${campaign.dungeon.room}` : 'No active run'}</strong>
              <span>{campaign?.dungeon?.active ? campaign.dungeon.question?.concept_id || 'Adaptive concept' : 'Start a run from the Dungeon screen.'}</span>
            </div>
            <div className="boundary-card locked">
              <strong>STATE GATEWAY</strong>
              <span>dungeon.py is a controlled projection, never a second save.</span>
            </div>
          </>
        )}

        {activeView === 'practice' && (
          <>
            <div className="context-kicker">OPEN PRACTICE</div>
            <h3>Choose what to strengthen</h3>
            <p>Practice is unlimited and separate from Campaign and Dungeon runs. Provider help uses the same bounded context bridge.</p>
            <div className="boundary-card safe">
              <strong>NO CAMPAIGN COST</strong>
              <span>No Dungeon score, run currency or permanent reward is changed here.</span>
            </div>
          </>
        )}

        {activeView === 'settings' && (
          <>
            <div className="context-kicker">IDE SETTINGS</div>
            <p>Layout and accessibility are always free. Homestead coins only gate cosmetics.</p>
            <div className="context-row stacked">
              <strong>Cosmetics</strong>
              <span>Equip purchased themes from Homestead.</span>
            </div>
            <div className="context-row stacked">
              <strong>Layout</strong>
              <span>Resize everything like a normal IDE.</span>
            </div>
          </>
        )}
      </div>
    </>
  )
}

function ProgressBar({ value, max, label, className = '' }) {
  const safeMax = Math.max(1, Number(max) || 1)
  const percent = clamp(((Number(value) || 0) / safeMax) * 100, 0, 100)
  return (
    <div className={`meter ${className}`}>
      <div className="meter-label"><span>{label}</span><b>{value}/{max}</b></div>
      <div className="meter-track"><span style={{ width: `${percent}%` }} /></div>
    </div>
  )
}

function BattleSubmission({ availableObjectives, onSubmit, busy }) {
  const [objectiveId, setObjectiveId] = useState(availableObjectives[0]?.id || '')
  const [answer, setAnswer] = useState('')
  const [status, setStatus] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!availableObjectives.some((objective) => objective.id === objectiveId)) {
      setObjectiveId(availableObjectives[0]?.id || '')
    }
  }, [availableObjectives, objectiveId])

  if (!availableObjectives.length) return null

  const submit = async (event) => {
    event.preventDefault()
    if (!objectiveId || !answer.trim() || !onSubmit || submitting) return
    setSubmitting(true)
    setStatus('Sending answer to the selected provider…')
    try {
      await onSubmit({ objectiveId, answer })
      setAnswer('')
      setStatus('Answer sent. Resolve and rewards change only after the provider returns a validated verdict.')
    } catch (error) {
      setStatus(error?.message || 'Battle submission failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="battle-submit-card" data-testid="battle-submission">
      <div className="card-heading"><span>BATTLE SUBMISSION</span><b>OPTIONAL</b></div>
      <p className="context-note">Choose one currently available objective and explain your answer. PYR receives the answer for adjudication; this form cannot award Impact or damage on its own.</p>
      <form onSubmit={submit}>
        <label className="battle-field">
          <span>Objective</span>
          <select value={objectiveId} onChange={(event) => setObjectiveId(event.target.value)} disabled={busy || submitting}>
            {availableObjectives.map((objective) => (
              <option key={objective.id} value={objective.id}>{objective.question_type} · {objective.impact} Impact</option>
            ))}
          </select>
        </label>
        <label className="battle-field">
          <span>Your answer</span>
          <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={20_000} rows={7} placeholder="Explain the idea or show the checkpoint you completed…" disabled={busy || submitting} />
        </label>
        <button className="primary" type="submit" disabled={busy || submitting || !answer.trim() || !onSubmit}>{submitting ? 'Sending…' : 'Send to PYR'}</button>
      </form>
      {status && <small className="battle-submit-status" role="status">{status}</small>}
    </section>
  )
}

function QuestJournal({ progress, revision, encounter, submitBattle, busy }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const mobs = activeProject.mobs || []
  const projectedIndex = encounter?.mob_name ? mobs.findIndex((mob) => mob.name === encounter.mob_name) : -1
  const firstAvailable = mobs.findIndex((mob) => mob.status === 'available')
  const currentIndex = projectedIndex >= 0 ? projectedIndex : firstAvailable >= 0 ? firstAvailable : Math.max(0, mobs.length - 1)
  const currentMob = mobs[currentIndex]
  const goals = progress.goals || {}
  const resolve = encounter?.resolve ?? currentMob?.resolve ?? currentMob?.max_resolve ?? 0
  const maxResolve = encounter?.max_resolve ?? currentMob?.max_resolve ?? resolve
  const availableObjectives = encounter?.available_objectives || []

  return (
    <div className="game-screen-scroll" data-testid="quest-journal" data-campaign-revision={revision}>
      <div className="screen-hero quest-hero">
        <div>
          <span className="screen-kicker">CURRENT CHAPTER</span>
          <h2>{activeProject.name || 'Choose a quest'}</h2>
          <p>{progress.current_quest}</p>
        </div>
        <div className="boss-seal">
          <small>BOSS</small>
          <strong>{activeProject.boss || 'Unknown'}</strong>
          <span>{activeProject.clean_clear_eligible ? 'Clean Clear eligible' : 'Assisted clear'}</span>
        </div>
      </div>

      <div className="screen-grid two">
        <section className="game-card">
          <div className="card-heading"><span>MAIN QUEST</span><b>{activeProject.progress ?? 0}%</b></div>
          <h3>{currentMob ? currentMob.name : `Face ${activeProject.boss || 'the boss'}`}</h3>
          <p>{currentMob?.concept || 'Complete the remaining chapter objectives.'}</p>
          <div className="encounter-resolve-panel" data-testid="encounter-resolve">
            <div className="card-heading"><span>ENEMY RESOLVE</span><b>{resolve}/{maxResolve}</b></div>
            <ProgressBar value={resolve} max={maxResolve} label="Resolve" className="resolve" />
            {availableObjectives.length > 0 && (
              <div className="impact-objectives" aria-label="Available verified objectives">
                {availableObjectives.map((objective) => (
                  <span key={objective.id}>{objective.question_type} · {objective.impact} Impact</span>
                ))}
              </div>
            )}
          </div>
          <BattleSubmission availableObjectives={availableObjectives} onSubmit={submitBattle} busy={busy} />
          <div className="mob-path">
            {mobs.map((mob, index) => (
              <div key={mob.name} className={`mob-node ${mob.status} ${index === currentIndex ? 'current' : ''}`}>
                <span>{isMobDefeated(mob.status) ? '✓' : index + 1}</span>
                <div><strong>{mob.name}</strong><small>{mob.status === 'locked' ? 'Encounter hidden' : mob.concept || 'Encounter details pending'}</small></div>
              </div>
            ))}
          </div>
        </section>

        <section className="game-card">
          <div className="card-heading"><span>TODAY'S CONTRACTS</span><b>{(goals.daily || []).filter((goal) => goal.done).length}/{(goals.daily || []).length}</b></div>
          <div className="quest-list">
            {(goals.daily || []).map((goal) => (
              <div key={goal.id} className={`quest-item ${goal.done ? 'done' : ''}`}>
                <span>{goal.done ? '✓' : '○'}</span>
                <div><strong>{goal.text}</strong><small>+{goal.reward_xp ?? 0} XP · +{goal.reward_coins ?? 0}c</small></div>
              </div>
            ))}
          </div>
          <div className="card-heading secondary"><span>WEEKLY</span></div>
          <div className="quest-list compact">
            {(goals.weekly || []).map((goal) => (
              <div key={goal.id} className={`quest-item ${goal.done ? 'done' : ''}`}>
                <span>{goal.done ? '✓' : '○'}</span>
                <div><strong>{goal.text}</strong><small>{goal.progress ?? 0}/{goal.target ?? 1}</small></div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

function Codex({ progress, revision }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const skills = progress.skills || []
  const entries = progress.codex?.encounters || []

  return (
    <div className="game-screen-scroll" data-testid="codex" data-campaign-revision={revision}>
      <div className="screen-hero">
        <div>
          <span className="screen-kicker">CODEX</span>
          <h2>What you have faced becomes knowledge.</h2>
          <p>Concepts, mastery evidence and encounter styles. Exact hidden answers stay hidden.</p>
        </div>
        <div className="codex-count"><strong>{skills.length + entries.length}</strong><span>entries indexed</span></div>
      </div>

      <section className="game-card">
        <div className="card-heading"><span>CONCEPT MASTERY</span></div>
        <div className="skill-grid">
          {skills.map((skill) => (
            <article key={skill.name} className={`skill-card ${skill.status}`}>
              <div className="skill-icon" data-skill-shield={skill.shield?.tier || 'none'}>{skill.shield?.tier !== 'none' ? '🛡' : '◇'}</div>
              <div><small>{skill.name}</small><h3>{skill.concept}</h3></div>
              <div className="skill-meta"><span>Evidence {skill.evidence ?? 0}</span><span>Interviews {skill.interview_passes ?? 0}</span></div>
              <div className="shield-line"><span>{skill.shield?.tier || 'none'} shield</span><b>{skill.shield?.charges ?? 0}/{skill.shield?.max_charges ?? 0}</b></div>
            </article>
          ))}
        </div>
      </section>

      <section className="game-card">
        <div className="card-heading"><span>{activeProject.name || 'PROJECT'} ENCOUNTERS</span><b>{entries.length}</b></div>
        <div className="encounter-grid">
          {entries.map((entry, index) => {
            const mastery = entry.mastery || {}
            const results = entry.results || []
            return (
            <article key={entry.id || entry.mob_name} className={`encounter-card ${entry.status || 'observed'}`}>
              <div className="encounter-number">{String(index + 1).padStart(2, '0')}</div>
              <small>{String(entry.status || 'observed').toUpperCase()}</small>
              <h3>{entry.mob_name || 'Encounter'}</h3>
              <strong>{entry.concept || 'Concept recorded by campaign'}</strong>
              <p>{entry.notes?.at(-1) || 'The encounter has been observed through verified learning evidence.'}</p>
              <div className="codex-entry-meta">
                <span>{entry.attempts ?? 0} attempts</span>
                <span>{(entry.question_types || []).join(' · ') || 'type pending'}</span>
                <span>Mastery {mastery.evidence ?? 0}</span>
                <span>{(entry.weaknesses || []).length} weaknesses recorded</span>
                <span>{(entry.interview_history || []).length + (mastery.interview_passes ?? 0)} interviews</span>
              </div>
              {results.length > 0 && <small className="codex-last-result">Last result: {results.at(-1).outcome || 'recorded'}</small>}
            </article>
            )
          })}
          {!entries.length && <div className="empty-state">Complete a verified encounter objective to grow the Codex.</div>}
        </div>
      </section>
    </div>
  )
}

function CharacterSheet({ progress, revision }) {
  const player = progress.player || {}
  const stats = progress.stats || {}
  const equipment = progress.equipment || {}
  const companion = progress.companion || {}
  const achievements = progress.achievements || []

  return (
    <div className="game-screen-scroll" data-testid="character" data-campaign-revision={revision}>
      <div className="character-layout">
        <section className="character-card game-card">
          <div className="character-banner">
            <div className="character-sigil">{(player.name || 'L').slice(0, 1)}</div>
            <div><span className="screen-kicker">RANK {player.rank || 'F'}</span><h2>{player.name || 'Player'}</h2><p>{player.title || 'Apprentice Coder'}</p></div>
            <div className="level-medallion"><small>LV</small><strong>{player.level ?? 1}</strong></div>
          </div>
          <ProgressBar value={player.xp ?? 0} max={player.xp_next ?? 100} label="XP" className="xp" />
          <div className="character-stat-grid">
            <div><small>COINS</small><strong>{player.coins ?? 0}c</strong></div>
            <div><small>STREAK</small><strong>{progress.streak?.current ?? 0}</strong></div>
            <div><small>BOSSES</small><strong>{stats.bosses_defeated ?? 0}</strong></div>
            <div><small>CLEAN CLEARS</small><strong>{stats.clean_clears ?? 0}</strong></div>
          </div>
        </section>

        <section className="game-card">
          <div className="card-heading"><span>EQUIPMENT</span></div>
          <div className="equipment-list">
            <div><span>◈</span><small>Armor</small><strong>{equipment.armor || 'None'}</strong></div>
            <div><span>✦</span><small>Trinket</small><strong>{equipment.trinket || 'None'}</strong></div>
            <div><span>♛</span><small>Title</small><strong>{equipment.title || player.title || 'None'}</strong></div>
          </div>
        </section>

        <section className="game-card companion-card">
          <div className="pyr-orb">🔥</div>
          <div><span className="screen-kicker">COMPANION</span><h3>{companion.name || 'PYR'} · {companion.form || 'Tiny Code-Flame'}</h3><p>Bond {companion.bond ?? 0} · Level {companion.level ?? 1}</p><small>Next form: {companion.next_form || '???'} — {companion.next_form_requirement || 'keep learning'}</small></div>
        </section>
      </div>

      <section className="game-card">
        <div className="card-heading"><span>ACHIEVEMENTS</span><b>{achievements.filter((item) => item.unlocked).length}/{achievements.length}</b></div>
        <div className="achievement-grid">
          {achievements.map((achievement) => (
            <article key={achievement.name} className={achievement.unlocked ? 'unlocked' : 'locked'}>
              <span>{achievement.unlocked ? '◆' : '◇'}</span>
              <div><strong>{achievement.name}</strong><p>{achievement.description}</p></div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function Homestead({ progress, revision, purchaseCosmetic, equipCosmetic, busy }) {
  const player = progress.player || {}
  const homestead = progress.homestead || {}
  const catalog = homestead.catalog || []
  const owned = new Set(homestead.owned_cosmetics || [])
  const equipped = homestead.equipped || {}
  const grouped = ['theme', 'cursor', 'hud', 'terminal']

  return (
    <div className="game-screen-scroll" data-testid="homestead" data-campaign-revision={revision}>
      <div className="homestead-scene">
        <div className="homestead-window">✦</div>
        <div className="homestead-desk"><span>⌨</span><small>FORGE DESK</small></div>
        <div className="homestead-hearth"><span>🔥</span><small>PYR'S HEARTH</small></div>
        <div className="homestead-shelf"><span>◇ ◇ ◇</span><small>TROPHY SHELF</small></div>
        <div className="homestead-title"><span className="screen-kicker">HOMESTEAD</span><h2>{homestead.name || 'Your Forge'}</h2><p>Your environment grows with the things you earn while learning.</p></div>
        <div className="coin-purse"><small>PURSE</small><strong>{player.coins ?? 0}c</strong></div>
      </div>

      {grouped.map((kind) => (
        <section className="game-card" key={kind}>
          <div className="card-heading"><span>{kind.toUpperCase()}S</span><b>{catalog.filter((item) => item.kind === kind && owned.has(item.id)).length}/{catalog.filter((item) => item.kind === kind).length}</b></div>
          <div className="shop-grid">
            {catalog.filter((item) => item.kind === kind).map((item) => {
              const isOwned = owned.has(item.id)
              const isEquipped = equipped[kind] === item.id
              const canAfford = (player.coins ?? 0) >= (item.price ?? 0)
              return (
                <article key={item.id} className={`shop-card ${isEquipped ? 'equipped' : ''}`}>
                  <div className={`shop-swatch ${item.id}`}><span>{kind === 'theme' ? '◫' : kind === 'cursor' ? '│' : kind === 'hud' ? '▣' : '>_'}</span></div>
                  <div className="shop-copy"><small>{item.rarity || 'common'}</small><h3>{item.name}</h3><p>{item.description}</p></div>
                  <div className="shop-actions">
                    <strong>{isOwned ? (isEquipped ? 'EQUIPPED' : 'OWNED') : `${item.price ?? 0}c`}</strong>
                    {!isOwned && <button disabled={busy || !canAfford} onClick={() => purchaseCosmetic(item.id)}>{canAfford ? 'Buy' : 'Need coins'}</button>}
                    {isOwned && !isEquipped && <button disabled={busy} onClick={() => equipCosmetic(item.id)}>Equip</button>}
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}

function DungeonScreen({ dungeon, revision, onStart, busy, editorContent, onEditorChange, onSave }) {
  const [concept, setConcept] = useState('')
  const run = dungeon || { active: false, status: 'idle' }
  const question = run.question || {}
  const loadout = run.loadout || {}

  const start = async (event) => {
    event.preventDefault()
    if (!onStart || busy) return
    await onStart(concept.trim() || undefined)
  }

  return (
    <div className="game-screen-scroll" data-testid="dungeon" data-campaign-revision={revision}>
      <div className="screen-hero dungeon-hero">
        <div>
          <span className="screen-kicker">INFINITE DUNGEON</span>
          <h2>{run.active ? `Floor ${run.floor} · Room ${run.room}` : 'Enter the endless run.'}</h2>
          <p>{run.active ? 'Your checkpoint is safe. Keep solving to go deeper.' : 'A fresh loadout, adaptive questions and a score that belongs to this run.'}</p>
        </div>
        <div className="dungeon-score"><small>{run.active ? 'RUN SCORE' : 'LAST RUN'}</small><strong>{run.score ?? 0}</strong><span>{run.status === 'dead' ? 'run ended' : run.active ? `${run.run_coins ?? 0} run coins` : 'ready'}</span></div>
      </div>

      {!run.active ? (
        <section className="game-card dungeon-start-card">
          <div className="card-heading"><span>{run.status === 'dead' ? 'RUN RECOVERED' : 'NEW RUN'}</span><b>FRESH LOADOUT</b></div>
          <p>{run.status === 'dead' ? `That run ended on floor ${run.floor ?? 0}. Start again when you are ready.` : 'Campaign gear never leaks into the Dungeon.'}</p>
          <div className="dungeon-starter-loadout"><span>Apprentice Coat</span><span>No trinket</span><span>1 heal</span><span>0 run coins</span></div>
          <form className="dungeon-start-form" onSubmit={start}>
            <label><span>Optional focus concept</span><input value={concept} onChange={(event) => setConcept(event.target.value)} maxLength={120} placeholder="e.g. lists, loops, debugging" disabled={busy} /></label>
            <button className="primary" type="submit" disabled={busy}>{busy ? 'Starting…' : 'Enter Dungeon'}</button>
          </form>
        </section>
      ) : (
        <>
          <div className="screen-grid two">
            <section className="game-card">
              <div className="card-heading"><span>CURRENT ROOM</span><b>{String(run.room_type || 'encounter').toUpperCase()}</b></div>
              <h3>{question.concept_id || 'Adaptive encounter'}</h3>
              <p>{question.prompt || 'The next question will be issued by the state service.'}</p>
              {Array.isArray(question.options) && question.options.length > 0 && (
                <div className="impact-objectives" aria-label="Question options">
                  {question.options.map((option) => <span key={option}>{option}</span>)}
                </div>
              )}
              <div className="dungeon-question-meta"><span>{question.question_type || 'question'}</span><span>Difficulty {question.difficulty ?? 1}</span><span>Write in dungeon.py</span></div>
              <label className="dungeon-editor-field"><span>dungeon.py · current room buffer</span><textarea value={editorContent || ''} onChange={(event) => onEditorChange?.(event.target.value)} maxLength={120_000} rows={10} placeholder="Write your answer here. This buffer is checkpointed through the state gateway." disabled={busy} /></label>
              <button type="button" onClick={onSave} disabled={busy || !onSave}>{busy ? 'Saving…' : 'Save checkpoint'}</button>
            </section>
            <section className="game-card">
              <div className="card-heading"><span>RUN LOADOUT</span><b>{loadout.hp ?? 0}/{loadout.max_hp ?? 0} HP</b></div>
              <div className="dungeon-loadout-list"><div><small>ARMOR</small><strong>{loadout.armor || 'Apprentice Coat'}</strong></div><div><small>TRINKET</small><strong>{loadout.trinket || 'None'}</strong></div><div><small>HEALS</small><strong>{loadout.heals ?? 0}</strong></div><div><small>RUN COINS</small><strong>{run.run_coins ?? 0}</strong></div></div>
              <p className="context-note">The editor buffer autosaves through the state gateway. A new question clears it before the next prompt.</p>
            </section>
          </div>
          <section className="game-card dungeon-checkpoint-card">
            <div className="card-heading"><span>CHECKPOINT</span><b>{run.updated_at ? 'SAVED' : 'PENDING'}</b></div>
            <p>Run <code>{run.run_id}</code> will resume at this room after a Forge or workstation restart. Death is the only reset.</p>
          </section>
        </>
      )}
    </div>
  )
}

function PracticeScreen({ progress, revision, onPracticePrompt, busy }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const concepts = Array.from(new Set([
    ...(progress.skills || []).map((skill) => skill.concept).filter(Boolean),
    ...(activeProject.mobs || []).map((mob) => mob.concept).filter(Boolean),
    progress.learning_state?.concept,
  ].filter(Boolean)))
  const [concept, setConcept] = useState(concepts[0] || 'python-basics')
  const [questionType, setQuestionType] = useState('multiple_choice')
  const [difficulty, setDifficulty] = useState('1')
  const [answer, setAnswer] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!concepts.includes(concept)) setConcept(concepts[0] || 'python-basics')
  }, [concepts.join('|'), concept])

  const ask = async (event) => {
    event.preventDefault()
    if (!onPracticePrompt || busy) return
    setStatus(answer.trim() ? 'Sending your answer for feedback…' : 'Asking the provider for one practice question…')
    try {
      await onPracticePrompt({ concept, questionType, difficulty: Number(difficulty), answer })
      setStatus(answer.trim() ? 'Feedback requested. Practice never changes Dungeon or Campaign state.' : 'Question requested. Answer it in the provider conversation, then ask for feedback.')
      if (answer.trim()) setAnswer('')
    } catch (error) {
      setStatus(error?.message || 'Practice request failed.')
    }
  }

  return (
    <div className="game-screen-scroll" data-testid="practice" data-campaign-revision={revision}>
      <div className="screen-hero practice-hero">
        <div><span className="screen-kicker">PRACTICE MODE</span><h2>Train any concept, anytime.</h2><p>Pick the concept and question style. PYR can teach, challenge and explain without consuming a run or Campaign reward.</p></div>
        <div className="dungeon-score"><small>STAKES</small><strong>NONE</strong><span>unlimited attempts</span></div>
      </div>
      <section className="game-card practice-card">
        <div className="card-heading"><span>BUILD A DRILL</span><b>AI ASSISTED</b></div>
        <form className="practice-form" onSubmit={ask}>
          <label><span>Concept</span><select value={concept} onChange={(event) => setConcept(event.target.value)} disabled={busy}>{concepts.map((item) => <option key={item} value={item}>{item}</option>)}<option value="python-basics">python-basics</option></select></label>
          <label><span>Question type</span><select value={questionType} onChange={(event) => setQuestionType(event.target.value)} disabled={busy}><option value="true_false">True / False</option><option value="multiple_choice">Multiple choice</option><option value="short_explanation">Short explanation</option><option value="code_trace">Code trace</option><option value="bug_hunt">Bug hunt</option></select></label>
          <label><span>Difficulty</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} disabled={busy}>{[1, 2, 3, 4, 5].map((level) => <option key={level} value={level}>Tier {level}</option>)}</select></label>
          <label className="practice-answer"><span>Answer or ask for feedback</span><textarea value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={20_000} rows={5} placeholder="Leave blank for a new question, or paste your answer here…" disabled={busy} /></label>
          <button className="primary" type="submit" disabled={busy}>{busy ? 'Sending…' : answer.trim() ? 'Ask for feedback' : 'Ask PYR for a drill'}</button>
        </form>
        {status && <small className="battle-submit-status" role="status">{status}</small>}
      </section>
      <section className="game-card">
        <div className="card-heading"><span>PRACTICE BOUNDARY</span><b>SEPARATE MODE</b></div>
        <p className="context-note">Practice uses the same bounded provider context as Campaign, but it never creates a leaderboard run, copies Campaign gear, or writes tutor.py.</p>
      </section>
    </div>
  )
}

function AccountPanel({ account, busy, notice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict }) {
  const [formMode, setFormMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [deviceLabel, setDeviceLabel] = useState(account.device?.display_name || 'Quest Lab device')
  const configured = account.configured && account.configurationValid
  const signedIn = account.authStatus === 'signed-in' && account.user

  useEffect(() => {
    if (account.device?.display_name) setDeviceLabel(account.device.display_name)
  }, [account.device?.display_name])

  const submit = async (event) => {
    event.preventDefault()
    if (!email.trim() || !password) return
    try {
      if (formMode === 'signup') await onSignUp({ email, password, displayName })
      else await onSignIn({ email, password })
      setPassword('')
    } catch {
      // The service exposes a safe, user-facing error in account.detail.
    }
  }

  return (
    <section className="game-card settings-card account-card">
      <div className="card-heading">
        <span>ACCOUNT &amp; DEVICE</span>
        <b className={`account-state ${account.error || account.syncStatus === 'conflict' ? 'error' : signedIn ? 'signed-in' : 'local'}`}>{account.label}</b>
      </div>

      {!configured && (
        <div className="account-local-state">
          <strong>Offline / Local Mode</strong>
          <p>{account.detail || 'Add the public Supabase values to enable account sign-in. Your local Forge is unaffected.'}</p>
        </div>
      )}

      {configured && !signedIn && (
        <>
          <p className="settings-note">Sign in on each device to share your Quest Lab identity. Campaign fields sync through the controlled state gateway.</p>
          <form className="account-form" onSubmit={submit}>
            {formMode === 'signup' && (
              <label><span>Display name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={80} placeholder="Lazi" autoComplete="nickname" /></label>
            )}
            <label><span>Email</span><input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
            <label><span>Password</span><input type="password" required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={formMode === 'signup' ? 'new-password' : 'current-password'} /></label>
            <div className="account-actions">
              <button className="primary" type="submit" disabled={busy}>{formMode === 'signup' ? 'Create account' : 'Sign in'}</button>
              <button type="button" disabled={busy} onClick={() => setFormMode(formMode === 'signup' ? 'signin' : 'signup')}>{formMode === 'signup' ? 'I already have an account' : 'Create an account'}</button>
            </div>
          </form>
        </>
      )}

      {configured && signedIn && (
        <div className="account-signed-in">
          <div className="account-identity"><strong>{account.profile?.display_name || account.user.email}</strong><span>{account.user.email}</span></div>
          <p className="settings-note">Campaign sync: <strong>{account.label}</strong>{account.pendingChanges ? ` · ${account.pendingChanges} queued change${account.pendingChanges === 1 ? '' : 's'}` : ''}</p>
          {account.conflict && (
            <div className="cloud-conflict-banner" role="alert">
              <strong>Campaign sync needs a choice.</strong>
              <span>Local revision {account.conflict.localRevision ?? '—'} and cloud revision {account.conflict.cloudRevision ?? '—'} differ.</span>
              {account.conflict.localPlayer?.level !== null && account.conflict.cloudPlayer?.level !== null && (
                <span>This device: Level {account.conflict.localPlayer.level} · {account.conflict.localPlayer.xp ?? 0}/{account.conflict.localPlayer.xpNext ?? 100} XP · {account.conflict.localPlayer.coins ?? 0} coins. Cloud: Level {account.conflict.cloudPlayer.level} · {account.conflict.cloudPlayer.xp ?? 0}/{account.conflict.cloudPlayer.xpNext ?? 100} XP · {account.conflict.cloudPlayer.coins ?? 0} coins.</span>
              )}
              <div className="account-actions">
                <button type="button" disabled={busy} onClick={async () => { try { await onResolveConflict('cloud') } catch {} }}>Use cloud copy</button>
                <button type="button" disabled={busy} onClick={async () => { try { await onResolveConflict('local') } catch {} }}>Keep this device</button>
              </div>
            </div>
          )}
          <form className="device-form" onSubmit={async (event) => { event.preventDefault(); try { await onDeviceLabelSave(deviceLabel) } catch {} }}>
            <label><span>This device</span><input value={deviceLabel} onChange={(event) => setDeviceLabel(event.target.value)} maxLength={80} /></label>
            <button type="submit" disabled={busy}>Save device name</button>
          </form>
          <button type="button" disabled={busy} onClick={async () => { try { await onSignOut() } catch {} }}>Sign out</button>
        </div>
      )}

      {(notice || account.error) && <p className={`account-message ${account.error ? 'error' : ''}`}>{notice || account.error}</p>}
    </section>
  )
}

function SettingsScreen({ preferences, setters, resetLayout, equipped, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict, revision }) {
  const { editorFontSize, terminalFontSize, hudDensity, animations } = preferences
  return (
    <div className="game-screen-scroll settings-screen" data-campaign-revision={revision}>
      <div className="screen-hero">
        <div><span className="screen-kicker">SETTINGS</span><h2>Make the Forge fit you.</h2><p>Usability and accessibility settings are free forever. Homestead coins only unlock cosmetic presentation.</p></div>
      </div>

      <div className="screen-grid two">
        <AccountPanel account={account} busy={accountBusy} notice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onResolveConflict={onResolveConflict} />
        <section className="game-card settings-card">
          <div className="card-heading"><span>EDITOR</span></div>
          <label><span>Editor font size</span><b>{editorFontSize}px</b><input type="range" min="11" max="22" value={editorFontSize} onChange={(event) => setters.setEditorFontSize(Number(event.target.value))} /></label>
          <label><span>Terminal font size</span><b>{terminalFontSize}px</b><input type="range" min="10" max="20" value={terminalFontSize} onChange={(event) => setters.setTerminalFontSize(Number(event.target.value))} /></label>
          <label><span>HUD density</span><select value={hudDensity} onChange={(event) => setters.setHudDensity(event.target.value)}><option value="full">Full</option><option value="compact">Compact</option></select></label>
          <label className="toggle-row"><span>Animations</span><input type="checkbox" checked={animations} onChange={(event) => setters.setAnimations(event.target.checked)} /></label>
        </section>

        <section className="game-card settings-card">
          <div className="card-heading"><span>HOMESTEAD LOADOUT</span></div>
          <div className="loadout-list">
            <div><span>Theme</span><b>{equipped.theme || 'theme-ember-forge'}</b></div>
            <div><span>Cursor</span><b>{equipped.cursor || 'cursor-basic'}</b></div>
            <div><span>HUD</span><b>{equipped.hud || 'hud-forge'}</b></div>
            <div><span>Terminal</span><b>{equipped.terminal || 'terminal-charcoal'}</b></div>
          </div>
          <p className="settings-note">Buy and equip cosmetic loadouts from the Homestead. These never change learning difficulty or rewards.</p>
          <button onClick={resetLayout}>Reset panel layout</button>
        </section>
      </div>
    </div>
  )
}

export function GameScreen({ activeView, progress, revision, encounter, dungeon, dungeonEditorContent, onDungeonEditorChange, onSaveDungeon, purchaseCosmetic, equipCosmetic, busy, submitBattle, onStartDungeon, onPracticePrompt, preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict }) {
  if (activeView === 'quests') return <QuestJournal progress={progress} revision={revision} encounter={encounter} submitBattle={submitBattle} busy={busy} />
  if (activeView === 'codex') return <Codex progress={progress} revision={revision} />
  if (activeView === 'character') return <CharacterSheet progress={progress} revision={revision} />
  if (activeView === 'homestead') return <Homestead progress={progress} revision={revision} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} busy={busy} />
  if (activeView === 'dungeon') return <DungeonScreen dungeon={dungeon} revision={revision} onStart={onStartDungeon} busy={busy} editorContent={dungeonEditorContent} onEditorChange={onDungeonEditorChange} onSave={onSaveDungeon} />
  if (activeView === 'practice') return <PracticeScreen progress={progress} revision={revision} onPracticePrompt={onPracticePrompt} busy={busy} />
  if (activeView === 'settings') return <SettingsScreen preferences={preferences} setters={setters} resetLayout={resetLayout} equipped={progress.homestead?.equipped || {}} account={account} accountBusy={accountBusy} accountNotice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onResolveConflict={onResolveConflict} revision={revision} />
  return null
}
