import { useEffect, useState } from 'react'

export const viewItems = [
  { id: 'forge', icon: '⌘', label: 'Forge' },
  { id: 'tutor', icon: '🧪', label: 'Tutor Notebook' },
  { id: 'quests', icon: '⚔', label: 'Quest Journal' },
  { id: 'codex', icon: '▤', label: 'Codex' },
  { id: 'character', icon: '♙', label: 'Character' },
  { id: 'homestead', icon: '⌂', label: 'Homestead' },
  { id: 'settings', icon: '⚙', label: 'Settings' },
]

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

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
                  <span>{mob.status === 'available' ? '◆' : mob.status === 'defeated' ? '✓' : '◇'}</span>
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

function QuestJournal({ progress }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const mobs = activeProject.mobs || []
  const firstAvailable = mobs.findIndex((mob) => mob.status === 'available')
  const currentIndex = firstAvailable >= 0 ? firstAvailable : Math.max(0, mobs.length - 1)
  const currentMob = mobs[currentIndex]
  const goals = progress.goals || {}

  return (
    <div className="game-screen-scroll">
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
          <div className="mob-path">
            {mobs.map((mob, index) => (
              <div key={mob.name} className={`mob-node ${mob.status} ${index === currentIndex ? 'current' : ''}`}>
                <span>{mob.status === 'defeated' ? '✓' : index + 1}</span>
                <div><strong>{mob.name}</strong><small>{mob.concept || 'Encounter hidden'}</small></div>
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

function Codex({ progress }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const skills = progress.skills || []
  const mobs = activeProject.mobs || []

  return (
    <div className="game-screen-scroll">
      <div className="screen-hero">
        <div>
          <span className="screen-kicker">CODEX</span>
          <h2>What you have faced becomes knowledge.</h2>
          <p>Concepts, mastery evidence and encounter styles. Exact hidden answers stay hidden.</p>
        </div>
        <div className="codex-count"><strong>{skills.length + mobs.length}</strong><span>entries indexed</span></div>
      </div>

      <section className="game-card">
        <div className="card-heading"><span>CONCEPT MASTERY</span></div>
        <div className="skill-grid">
          {skills.map((skill) => (
            <article key={skill.name} className={`skill-card ${skill.status}`}>
              <div className="skill-icon">{skill.shield?.tier !== 'none' ? '🛡' : '◇'}</div>
              <div><small>{skill.name}</small><h3>{skill.concept}</h3></div>
              <div className="skill-meta"><span>Evidence {skill.evidence ?? 0}</span><span>Interviews {skill.interview_passes ?? 0}</span></div>
              <div className="shield-line"><span>{skill.shield?.tier || 'none'} shield</span><b>{skill.shield?.charges ?? 0}/{skill.shield?.max_charges ?? 0}</b></div>
            </article>
          ))}
        </div>
      </section>

      <section className="game-card">
        <div className="card-heading"><span>{activeProject.name || 'PROJECT'} ENCOUNTERS</span><b>{mobs.length}</b></div>
        <div className="encounter-grid">
          {mobs.map((mob, index) => (
            <article key={mob.name} className={`encounter-card ${mob.status}`}>
              <div className="encounter-number">{String(index + 1).padStart(2, '0')}</div>
              <small>{mob.status.toUpperCase()}</small>
              <h3>{mob.name}</h3>
              <strong>{mob.concept || 'Unknown concept'}</strong>
              <p>{mob.encounter || 'This encounter has not revealed its nature yet.'}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function CharacterSheet({ progress }) {
  const player = progress.player || {}
  const stats = progress.stats || {}
  const equipment = progress.equipment || {}
  const companion = progress.companion || {}
  const achievements = progress.achievements || []

  return (
    <div className="game-screen-scroll">
      <div className="character-layout">
        <section className="character-card game-card">
          <div className="character-banner">
            <div className="character-sigil">{(player.name || 'L').slice(0, 1)}</div>
            <div><span className="screen-kicker">RANK {player.rank || 'F'}</span><h2>{player.name || 'Player'}</h2><p>{player.title || 'Apprentice Coder'}</p></div>
            <div className="level-medallion"><small>LV</small><strong>{player.level ?? 1}</strong></div>
          </div>
          <ProgressBar value={player.hp ?? 0} max={player.max_hp ?? 100} label="HP" className="hp" />
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

function Homestead({ progress, purchaseCosmetic, equipCosmetic, busy }) {
  const player = progress.player || {}
  const homestead = progress.homestead || {}
  const catalog = homestead.catalog || []
  const owned = new Set(homestead.owned_cosmetics || [])
  const equipped = homestead.equipped || {}
  const grouped = ['theme', 'cursor', 'hud', 'terminal']

  return (
    <div className="game-screen-scroll">
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

function AccountPanel({ account, busy, notice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave }) {
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
        <b className={`account-state ${account.error ? 'error' : signedIn ? 'signed-in' : 'local'}`}>{account.label}</b>
      </div>

      {!configured && (
        <div className="account-local-state">
          <strong>Offline / Local Mode</strong>
          <p>{account.detail || 'Add the public Supabase values to enable account sign-in. Your local Forge is unaffected.'}</p>
        </div>
      )}

      {configured && !signedIn && (
        <>
          <p className="settings-note">Sign in on each device to share your Quest Lab identity. Progress remains local until Sync Engine v1.</p>
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

function SettingsScreen({ preferences, setters, resetLayout, equipped, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave }) {
  const { editorFontSize, terminalFontSize, hudDensity, animations } = preferences
  return (
    <div className="game-screen-scroll settings-screen">
      <div className="screen-hero">
        <div><span className="screen-kicker">SETTINGS</span><h2>Make the Forge fit you.</h2><p>Usability and accessibility settings are free forever. Homestead coins only unlock cosmetic presentation.</p></div>
      </div>

      <div className="screen-grid two">
        <AccountPanel account={account} busy={accountBusy} notice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} />
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

export function GameScreen({ activeView, progress, purchaseCosmetic, equipCosmetic, busy, preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave }) {
  if (activeView === 'quests') return <QuestJournal progress={progress} />
  if (activeView === 'codex') return <Codex progress={progress} />
  if (activeView === 'character') return <CharacterSheet progress={progress} />
  if (activeView === 'homestead') return <Homestead progress={progress} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} busy={busy} />
  if (activeView === 'settings') return <SettingsScreen preferences={preferences} setters={setters} resetLayout={resetLayout} equipped={progress.homestead?.equipped || {}} account={account} accountBusy={accountBusy} accountNotice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} />
  return null
}
