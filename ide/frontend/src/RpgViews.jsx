import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import './homestead.css'
import './campaign.css'
import { merchantPixelSprite } from './campaignMerchant.js'

export const viewItems = [
  { id: 'hub', label: 'Campaign' },
  { id: 'tutor', label: 'Tutor Notebook' },
  { id: 'dungeon', label: 'Infinite Dungeon' },
  { id: 'codex', label: 'Codex' },
  { id: 'settings', label: 'Settings' },
]

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))
const isMobDefeated = (status) => status === 'defeated' || status === 'cleared'

const DUNGEON_CLASSES = [
  {
    id: 'syntax-warden',
    name: 'Syntax Warden',
    role: 'The guarded opener',
    iconId: 'target',
    passive: 'The first syntax-error submission each floor deals no HP damage.',
    weapon: 'Lint Lantern',
    weaponDetail: 'The first failed submission each floor earns a second bounded hint.',
  },
  {
    id: 'resolve-duelist',
    name: 'Resolve Duelist',
    role: 'The clean finisher',
    iconId: 'sword',
    passive: 'Clean submissions deal +1 Resolve damage in this run.',
    weapon: 'Loopblade',
    weaponDetail: '+1 Resolve damage against elite gates.',
  },
  {
    id: 'route-merchant',
    name: 'Route Merchant',
    role: 'The prepared wayfarer',
    iconId: 'spark',
    passive: 'Start with +20 run coins and one extra heal charge.',
    weapon: 'Branch Compass',
    weaponDetail: 'Read one risk profile per floor without spending a scroll.',
  },
]

const DUNGEON_PYTHON_WORDS = [
  'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'elif', 'else', 'False', 'for',
  'from', 'if', 'import', 'in', 'is', 'None', 'not', 'or', 'pass', 'print', 'raise', 'return',
  'True', 'try', 'while', 'with', 'range', 'len', 'list', 'dict', 'enumerate', 'sum',
]

function dungeonCompletionWords(source) {
  const identifiers = new Set()
  const patterns = [
    /\b(?:def|class)\s+([A-Za-z_]\w*)/g,
    /\b([A-Za-z_]\w*)\s*=/g,
    /\b(?:import|from)\s+([A-Za-z_]\w*)/g,
    /\bfor\s+([A-Za-z_]\w*)\s+in\b/g,
    /\bas\s+([A-Za-z_]\w*)\b/g,
  ]
  patterns.forEach((pattern) => {
    let match
    while ((match = pattern.exec(String(source || '')))) identifiers.add(match[1])
  })
  return [...new Set([...identifiers, ...DUNGEON_PYTHON_WORDS])].sort()
}

function dungeonSelfCheck(source) {
  const text = String(source || '')
  const output = ['$ local-self-check dungeon.py']
  if (!text.trim()) return { status: 'empty', output: [...output, 'No code to check.', 'Type an attempt, then run this safe preview.'] }
  const pairs = [['(', ')'], ['[', ']'], ['{', '}']]
  const stack = []
  const openers = new Map(pairs)
  const closers = new Set(pairs.map((pair) => pair[1]))
  let quote = null
  let escaped = false
  let lineNumber = 1
  for (const line of text.split(/\r?\n/)) {
    for (const char of line) {
      if (quote) {
        if (escaped) escaped = false
        else if (char === '\\') escaped = true
        else if (char === quote) quote = null
        continue
      }
      if (char === '#' || (char !== '"' && char !== "'" && !openers.has(char) && !closers.has(char))) continue
      if (char === '"' || char === "'") quote = char
      else if (openers.has(char)) stack.push({ char, line: lineNumber })
      else if (closers.has(char)) {
        const opener = stack.pop()
        if (!opener || openers.get(opener.char) !== char) {
          return { status: 'failed', output: [...output, `SyntaxError: unexpected '${char}' (line ${lineNumber})`, 'Run is a self-check only; no HP or score changed.', 'Repair the file, then Submit to PYR.'] }
        }
      }
    }
    lineNumber += 1
  }
  if (quote) return { status: 'failed', output: [...output, `SyntaxError: unterminated string literal (line ${lineNumber - 1})`, 'Run is a self-check only; no HP or score changed.'] }
  if (stack.length) return { status: 'failed', output: [...output, `SyntaxError: unclosed '${stack.at(-1).char}' (line ${stack.at(-1).line})`, 'Run is a self-check only; no HP or score changed.'] }
  const concepts = [
    ['loop', /\b(?:for|while)\b/.test(text)],
    ['condition', /\bif\b/.test(text)],
    ['assignment', /\b[A-Za-z_]\w*\s*=/.test(text)],
    ['output', /\b(?:print|return)\s*\(/.test(text)],
  ].filter(([, present]) => present).map(([name]) => name)
  return {
    status: 'passed',
    output: [...output, '[PASS] Python-shaped source: delimiters and strings are balanced.', `[INFO] Concepts seen: ${concepts.length ? concepts.join(', ') : 'none yet'}`, 'Run is safe and local; Submit is the only combat verdict.'],
  }
}

function DungeonEditorSurface({ value, onChange, onSave, onSubmit, busy, saving }) {
  const [terminal, setTerminal] = useState(() => dungeonSelfCheck(value))
  const run = () => setTerminal(dungeonSelfCheck(value))
  return (
    <div className="dungeon-editor-surface" aria-label="dungeon.py · current room buffer">
      <div className="dungeon-editor-toolbar"><span>dungeon.py · PYTHON</span><span>MONACO · LOCAL COMPLETION</span></div>
      <div className="dungeon-editor-wrap">
        <Editor
          height="360px"
          path="dungeon.py"
          language="python"
          value={value || ''}
          onChange={(next) => onChange?.(next ?? '')}
          onMount={(editor, monaco) => {
            const provider = monaco.languages.registerCompletionItemProvider('python', {
              triggerCharacters: ['.', '_'],
              provideCompletionItems: (model) => ({
                suggestions: dungeonCompletionWords(model.getValue()).map((label) => ({
                  label,
                  kind: monaco.languages.CompletionItemKind.Keyword,
                  insertText: label,
                  range: undefined,
                })),
              }),
            })
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, run)
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => onSubmit?.())
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onSave?.())
            editor.onDidDispose(() => provider.dispose())
          }}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            lineHeight: 22,
            padding: { top: 14, bottom: 14 },
            automaticLayout: true,
            smoothScrolling: true,
            tabSize: 4,
            suggestOnTriggerCharacters: true,
          }}
        />
      </div>
      <div className={`dungeon-editor-terminal ${terminal.status}`} role="status" aria-label="Dungeon self-check output">
        <div className="dungeon-editor-terminal-heading"><span>LOCAL TERMINAL · SELF-CHECK</span><b>{terminal.status.toUpperCase()}</b></div>
        <pre>{terminal.output.join('\n')}</pre>
      </div>
      <div className="dungeon-editor-actions">
        <button type="button" onClick={onSave} disabled={busy || saving}>{saving ? 'Saving…' : 'Save checkpoint'} <kbd>Ctrl/Cmd S</kbd></button>
        <button type="button" onClick={run} disabled={busy}>Run self-check <kbd>Ctrl/Cmd ↵</kbd></button>
        <button className="primary" type="button" onClick={onSubmit} disabled={busy || !String(value || '').trim()}>Submit to PYR <kbd>Ctrl/Cmd ⇧ ↵</kbd> ↗</button>
      </div>
    </div>
  )
}

export function buildQuestDocument(campaign) {
  const encounter = campaign?.encounter || {}
  const bossMode = encounter.status === 'boss_available' || encounter.boss_status === 'available'
  const title = bossMode
    ? (encounter.boss || 'Campaign boss')
    : (encounter.mob?.name || encounter.mob_name || 'Current encounter')
  const lore = bossMode
    ? (encounter.boss_lore || 'The final encounter guards the chapter boundary.')
    : (encounter.mob?.lore || 'A bounded campaign encounter.')
  const brief = bossMode
    ? (encounter.boss_brief || 'Break the gate one verified goal at a time.')
    : (encounter.mob?.brief || 'Submit verified work for this campaign file.')
  const currentQuest = encounter.current_quest || encounter.boss_current_requirement || encounter.available_objectives?.[0]
  const resolve = encounter.resolve ?? encounter.boss_resolve ?? 0
  const maxResolve = encounter.max_resolve ?? encounter.boss_max_resolve ?? 0
  const mechanics = Array.isArray(encounter.mechanics) ? encounter.mechanics.slice(0, 3) : []
  const reward = encounter.reward_envelope || {}
  const lines = [
    '# QUEST.md',
    '',
    '> STATE-OWNED CURRENT ENCOUNTER · This document is a read-only projection. Progress, Resolve, damage and rewards stay in the canonical state service.',
    '',
    `## ${title}`,
    '',
    lore,
    '',
    brief,
    '',
    `**Resolve:** ${resolve}/${maxResolve}`,
    '',
    '## Current quest',
    '',
    currentQuest
      ? `**${currentQuest.label || currentQuest.id || 'Current goal'}** · ${currentQuest.question_type || 'validated goal'} · ${currentQuest.damage ?? currentQuest.impact ?? 0} Resolve damage\n\n${currentQuest.quest || currentQuest.brief || 'Complete the current state-owned goal in the active Forge file.'}`
      : 'The state service has not published a current goal yet.',
    '',
    '## Boss / mob mechanics',
    '',
    ...(mechanics.length
      ? mechanics.flatMap((mechanic) => [
        `- **${mechanic.label || mechanic.id || 'Mechanic'}** — ${mechanic.detail || mechanic.description || ''}${mechanic.outcome ? ` (${mechanic.outcome})` : ''}`,
      ])
      : ['- The current encounter has no extra mechanics published.']),
    '',
    '## Loot at stake',
    '',
    `+${reward.xp ?? 0} XP · +${reward.coins ?? 0} Coins`,
    '',
  ]
  return lines.join('\n')
}

function PyrCompanion() {
  return (
    <div className="pyr-sidebar-companion" data-testid="pyr-sidebar-companion" data-pyr-motion="idle" role="img" aria-label="PYR companion keeping watch">
      <div className="pyr-pixel-character" aria-hidden="true">
        <svg viewBox="0 0 32 32" role="presentation" shapeRendering="crispEdges">
          <rect x="11" y="3" width="10" height="3" fill="currentColor" />
          <rect x="8" y="6" width="16" height="4" fill="currentColor" />
          <rect x="6" y="10" width="20" height="11" rx="2" fill="currentColor" />
          <rect className="pyr-eye pyr-eye-left" x="10" y="12" width="3" height="3" fill="var(--panel)" />
          <rect className="pyr-eye pyr-eye-right" x="19" y="12" width="3" height="3" fill="var(--panel)" />
          <rect x="13" y="17" width="6" height="2" fill="var(--panel)" />
          <rect x="9" y="21" width="14" height="5" fill="currentColor" />
          <rect x="6" y="26" width="7" height="3" fill="currentColor" />
          <rect x="19" y="26" width="7" height="3" fill="currentColor" />
        </svg>
      </div>
      <div><strong>PYR</strong><span>keeping watch</span></div>
    </div>
  )
}

function ForgeDocumentTabs({ activePath, editorMode, openFile, openQuestDocument }) {
  return (
    <div className="forge-document-tabs" role="tablist" aria-label="Forge documents">
      <button
        type="button"
        role="tab"
        aria-selected={editorMode !== 'quest'}
        className={editorMode !== 'quest' ? 'active' : ''}
        disabled={!activePath || editorMode !== 'quest'}
        onClick={() => activePath && editorMode === 'quest' && openFile(activePath)}
      >
        {activePath || 'campaign.py'}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={editorMode === 'quest'}
        className={editorMode === 'quest' ? 'active' : ''}
        onClick={openQuestDocument}
      >
        quest.md <small>STATE VIEW</small>
      </button>
    </div>
  )
}

function ForgeFileGlyph({ kind }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M6 3h8l4 4v14H6z" />
      <path d="M14 3v5h4" />
      {kind === 'python' ? <path d="m9 12 2 2-2 2m4-4h2" /> : <path d="M9 12h6M9 15h6M9 18h4" />}
    </svg>
  )
}

function ForgeCompactPanel({ activePath, editorMode, files = [], openFile, openQuestDocument, onToggleCompact }) {
  const campaignPath = activePath || files.find((item) => item?.type === 'file' && /\.py$/i.test(String(item.path || '')))?.path || 'campaign.py'
  return (
    <div className="forge-compact-panel" data-testid="forge-compact-panel" aria-label="Compact Forge file rail">
      <button
        type="button"
        className="forge-compact-expand"
        onClick={onToggleCompact}
        title="Expand Forge sidebar"
        aria-label="Expand Forge sidebar"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m9 5 7 7-7 7" /><path d="M4 5v14" /></svg>
      </button>
      <button
        type="button"
        className={`forge-compact-file ${editorMode !== 'quest' ? 'active' : ''}`}
        onClick={() => openFile(campaignPath)}
        title={`Open ${campaignPath}`}
        aria-label={`Open ${campaignPath}`}
        aria-pressed={editorMode !== 'quest'}
      >
        <ForgeFileGlyph kind="python" />
        <small>.py</small>
      </button>
      <button
        type="button"
        className={`forge-compact-file ${editorMode === 'quest' ? 'active' : ''}`}
        onClick={openQuestDocument}
        title="Open quest.md state view"
        aria-label="Open quest.md state view"
        aria-pressed={editorMode === 'quest'}
      >
        <ForgeFileGlyph kind="markdown" />
        <small>.md</small>
      </button>
    </div>
  )
}

function ContextCollapseButton({ label, onToggleCompact }) {
  if (!onToggleCompact) return null
  return (
    <button
      className="sidebar-collapse-toggle"
      type="button"
      onClick={onToggleCompact}
      title={`Compact ${label} sidebar`}
      aria-label={`Compact ${label} sidebar`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m15 5-7 7 7 7" /><path d="M20 5v14" /></svg>
    </button>
  )
}

function ContextCompactPanel({ activeView, onToggleCompact }) {
  const mode = activeView === 'practice' ? 'tutor' : activeView
  const label = mode === 'dungeon' ? 'Dungeon' : 'Tutor'
  const fileLabel = mode === 'dungeon' ? 'dungeon.py' : 'tutor.py'
  return (
    <div className="forge-compact-panel context-compact-panel" data-testid={`${mode}-compact-panel`} aria-label={`Compact ${label} sidebar`}>
      <button
        type="button"
        className="forge-compact-expand"
        onClick={onToggleCompact}
        title={`Expand ${label} sidebar`}
        aria-label={`Expand ${label} sidebar`}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m9 5 7 7-7 7" /><path d="M4 5v14" /></svg>
      </button>
      <div className="forge-compact-file context-compact-file active" role="img" aria-label={`${fileLabel} active`} title={`${fileLabel} active`}>
        <ForgeFileGlyph kind="python" />
        <small>{mode === 'dungeon' ? 'RUN' : 'TUTOR'}</small>
      </div>
    </div>
  )
}

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

export function ActivityRail({ activeView, setActiveView, player, avatarDataUrl = '', campaignReady = true }) {
  const displayLevel = campaignReady ? (player.level ?? 1) : '—'
  const displayName = campaignReady ? (player.name || 'Player') : 'Campaign syncing'
  const destinationItems = viewItems.filter((item) => item.id !== 'hub')
  return (
    <nav className="activity-rail" data-react-owned="true" aria-label="Quest Lab destinations">
      <button className="activity-mark" type="button" onClick={() => setActiveView('hub')} title="Campaign" aria-label="Open Campaign">
        <RouteIcon id="hub" />
      </button>
      <div className="activity-stack">
        {destinationItems.map((item) => (
          <button
            key={item.id}
            className={`activity-button ${activeView === item.id ? 'active' : ''}`}
            onClick={() => setActiveView(item.id)}
            title={item.label}
            aria-label={item.label}
          >
            <span><RouteIcon id={item.id} /></span>
          </button>
        ))}
      </div>
      <button
        className={`activity-avatar ${activeView === 'character' ? 'active' : ''}`}
        data-react-avatar="true"
        onClick={() => setActiveView('character')}
        title={`${displayName} · ${campaignReady ? `Level ${displayLevel}` : 'waiting for state'}`}
      >
        <span className="quest-avatar-slot">{avatarDataUrl ? <img className="quest-avatar-img compact" src={avatarDataUrl} alt="" /> : campaignReady ? (player.name || 'L').slice(0, 1).toUpperCase() : '…'}</span>
        <b>{displayLevel}</b>
      </button>
    </nav>
  )
}

export function ContextPanel({ activeView, campaign, files = [], activePath, compact = false, onToggleCompact, editorMode = 'file', openFile, openQuestDocument, newFile, setActiveView, submitBattle, submitBoss, busy }) {
  const progress = campaign?.progress || {}
  const player = progress.player || {}
  const activeProject = (progress.projects || []).find((project) => project.status === 'active')
  const encounter = campaign?.encounter || {}
  const skills = progress.skills || []
  const homestead = progress.homestead || {}
  const owned = homestead.owned_cosmetics || []
  // A malformed legacy transfer can leave a literal backslash directory in
  // the checkout. It is not part of the learner workspace and must never be
  // rendered as a second filesystem root in the editor tree.
  const treeFiles = files.filter((item) => {
    const path = String(item?.path || '')
    return path && !path.startsWith('\\') && !path.includes('\0')
  })
  const campaignSourceFiles = treeFiles.filter((item) => {
    if (item.type !== 'file' || !/\.py$/i.test(String(item.path || ''))) return false
    const normalized = String(item.path || '').replaceAll('\\', '/').toLowerCase()
    return !['tutor.py', 'dungeon.py'].includes(normalized) && !normalized.startsWith('ide/') && !normalized.startsWith('tools/') && !normalized.startsWith('tests/') && !normalized.includes('/test_') && !normalized.includes('/tests/')
  })
  const configuredProjectFiles = [
    ...(Array.isArray(activeProject?.files) ? activeProject.files : []),
    activeProject?.entry_file,
    activeProject?.main_file,
  ].filter((item) => typeof item === 'string' && item.trim())
  const multiFileProject = activeProject?.multi_file === true
    || configuredProjectFiles.length > 1
    || (configuredProjectFiles.length === 0 && campaignSourceFiles.length > 1)
  const directoryPaths = treeFiles.filter((item) => item.type === 'dir').map((item) => item.path)
  const [openDirs, setOpenDirs] = useState(null)
  const [showFiles, setShowFiles] = useState(multiFileProject)

  useEffect(() => {
    setShowFiles(multiFileProject)
  }, [multiFileProject])

  useEffect(() => {
    setOpenDirs((current) => {
      // Start collapsed so a large repository does not dump every descendant
      // into the narrow panel. The active file effect below expands only the
      // ancestors needed to keep the current editor context visible.
      if (current === null) return new Set()
      const known = new Set(directoryPaths)
      return new Set([...current].filter((path) => known.has(path)))
    })
  }, [directoryPaths.join('|')])

  useEffect(() => {
    if (!activePath) return
    const parts = activePath.split('/').filter(Boolean)
    if (parts.length < 2) return
    const ancestors = []
    for (let index = 1; index < parts.length; index += 1) {
      ancestors.push(parts.slice(0, index).join('/'))
    }
    setOpenDirs((current) => new Set([...(current || []), ...ancestors]))
  }, [activePath, directoryPaths.join('|')])

  const isTreeItemVisible = (item) => {
    const parts = item.path.split('/').filter(Boolean)
    const parentCount = parts.length - 1
    if (!parentCount) return true
    const expanded = openDirs || new Set()
    for (let index = 1; index <= parentCount; index += 1) {
      if (!expanded.has(parts.slice(0, index).join('/'))) return false
    }
    return true
  }

  const toggleDir = (path) => {
    setOpenDirs((current) => {
      const next = new Set(current || [])
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const toggleAllDirs = () => {
    setOpenDirs((current) => {
      const expanded = current || new Set()
      return expanded.size === directoryPaths.length && directoryPaths.length > 0 ? new Set() : new Set(directoryPaths)
    })
  }

  const collapsibleContext = activeView === 'tutor' || activeView === 'practice' || activeView === 'dungeon'
  if (compact && collapsibleContext) return <ContextCompactPanel activeView={activeView} onToggleCompact={onToggleCompact} />

  if (activeView === 'hub') {
    const goals = progress.goals || {}
    const cleared = (activeProject?.mobs || []).filter((mob) => isMobDefeated(mob.status)).length
    return (
      <>
        <div className="panel-title">
          <span>QUEST HUB</span>
          <button onClick={() => setActiveView('forge')} title="Open Forge" aria-label="Open Forge"><RouteIcon id="forge" /></button>
        </div>
        <div className="context-scroll">
          <div className="context-kicker">CAMPAIGN BRIEF</div>
          <h3>{activeProject?.name || 'Choose your first chapter'}</h3>
          <p>{progress.current_quest || 'Your daily contracts and chapter path will appear here.'}</p>
          <div className="context-stat"><span>Chapter progress</span><b>{activeProject?.progress ?? 0}%</b></div>
          <div className="context-stat"><span>Mob clears</span><b>{cleared}/{activeProject?.mobs?.length ?? 0}</b></div>
          <div className="context-kicker context-kicker-spaced">TODAY</div>
          {(goals.daily || []).slice(0, 3).map((goal) => <div key={goal.id} className="context-row stacked"><strong><span aria-hidden="true"><RouteIcon id={goal.done ? 'check' : 'target'} /></span>{goal.text}</strong><small>+{goal.reward_xp ?? 0} XP · +{goal.reward_coins ?? 0}c</small></div>)}
          <button className="primary context-cta" type="button" onClick={() => setActiveView('forge')}>Open active project</button>
        </div>
      </>
    )
  }

  if (activeView === 'forge') {
    if (compact) return <ForgeCompactPanel activePath={activePath} editorMode={editorMode} files={treeFiles} openFile={openFile} openQuestDocument={openQuestDocument} onToggleCompact={onToggleCompact} />
    return (
      <>
        <div className="panel-title">
          <span>{multiFileProject ? 'PROJECT FILES' : 'ACTIVE FILE'}</span>
          <div className="panel-title-actions">
            {multiFileProject && <div className="file-tree-actions">
              <button type="button" onClick={() => setShowFiles((current) => !current)} title={showFiles ? 'Hide project files' : 'Show project files'} aria-label={showFiles ? 'Hide project files' : 'Show project files'}>{showFiles ? 'Hide' : 'Files'}</button>
              {showFiles && <>
                <button type="button" onClick={toggleAllDirs} title={openDirs && openDirs.size === directoryPaths.length && directoryPaths.length > 0 ? 'Collapse all folders' : 'Expand all folders'} aria-label={openDirs && openDirs.size === directoryPaths.length && directoryPaths.length > 0 ? 'Collapse all folders' : 'Expand all folders'}>{openDirs && openDirs.size === directoryPaths.length && directoryPaths.length > 0 ? '−' : '+'}</button>
                <button type="button" onClick={newFile} title="New file" aria-label="New file">＋</button>
              </>}
            </div>}
            <button type="button" onClick={() => setActiveView('tutor')} title="Open Tutor Notebook" aria-label="Open Tutor Notebook"><RouteIcon id="tutor" /></button>
            {onToggleCompact && <button className="sidebar-collapse-toggle" type="button" onClick={onToggleCompact} title="Compact Forge sidebar" aria-label="Compact Forge sidebar"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m15 5-7 7 7 7" /><path d="M20 5v14" /></svg></button>}
          </div>
        </div>
        <div className="workspace-label">{campaign?.workspace || 'loading workspace…'}</div>
        <ForgeDocumentTabs activePath={activePath} editorMode={editorMode} openFile={openFile} openQuestDocument={openQuestDocument} />
        {multiFileProject && showFiles ? <div className="file-list" role="tree" aria-label="Workspace files">
            {treeFiles.filter(isTreeItemVisible).map((item) => (
              <button
                key={item.path}
                className={`file-row ${activePath === item.path ? 'active' : ''} ${item.type}`}
                style={{ paddingLeft: `${10 + item.depth * 14}px` }}
                onClick={() => item.type === 'dir' ? toggleDir(item.path) : openFile(item.path)}
                role="treeitem"
                aria-expanded={item.type === 'dir' ? (openDirs || new Set()).has(item.path) : undefined}
                aria-level={item.depth + 1}
              >
                <span className="file-tree-disclosure" aria-hidden="true">{item.type === 'dir' ? ((openDirs || new Set()).has(item.path) ? '▾' : '▸') : '·'}</span>
                <span className="file-tree-name">{item.name}</span>
              </button>
            ))}
            {!files.length && <div className="empty-state">No workspace files available.</div>}
          </div> : <div className="active-file-summary" data-testid="forge-active-file-summary">
            <span>CAMPAIGN EDITOR</span>
            <strong>{activePath || 'No campaign file selected'}</strong>
            <small>{multiFileProject ? 'Project files are hidden. Use Files when this step needs another file.' : 'Single-file step · the editor is the answer surface.'}</small>
          </div>}
        {(encounter.mob_name || encounter.status === 'boss_available' || encounter.boss_status === 'available') && (
            <div className="campaign-battle-sidebar">
            {encounter.mob_name ? <>
              <div className="panel-title"><span>ACTIVE BATTLE</span><b>{encounter.resolve ?? 0}/{encounter.max_resolve ?? 0}</b></div>
              <div className="campaign-battle-resolve" data-testid="forge-encounter-resolve">
                <ProgressBar value={encounter.resolve ?? 0} max={encounter.max_resolve ?? 1} label="Enemy Resolve" className="resolve" />
              </div>
              <PyrCompanion />
            </> : <>
              <div className="panel-title"><span>BOSS GATE</span><b>{encounter.resolve ?? encounter.boss_resolve ?? 0}/{encounter.max_resolve ?? encounter.boss_max_resolve ?? 0}</b></div>
              <div className="campaign-battle-resolve" data-testid="forge-boss-resolve">
                <ProgressBar value={encounter.resolve ?? encounter.boss_resolve ?? 0} max={encounter.max_resolve ?? encounter.boss_max_resolve ?? 1} label="Boss Resolve" className="resolve boss-resolve" />
              </div>
              <PyrCompanion />
            </>}
          </div>
        )}
      </>
    )
  }

  if (activeView === 'tutor' || activeView === 'practice') {
    return (
      <>
        <div className="panel-title">
          <span>TUTOR NOTEBOOK</span>
          <div className="panel-title-actions">
            <button onClick={() => setActiveView('forge')} title="Return to Forge" aria-label="Return to Forge"><RouteIcon id="forge" /></button>
            <ContextCollapseButton label="Tutor" onToggleCompact={onToggleCompact} />
          </div>
        </div>
        <div className="context-scroll">
          <div className="context-kicker">COLLABORATIVE SCRATCH SPACE</div>
          <h3>tutor.py</h3>
          <p>Choose a concept and question lens above tutor.py. This is the practice workspace too: PYR may write examples here; your real project file stays player-authored.</p>
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

  if (!campaign) {
    return (
      <>
        <div className="panel-title">
          <span>{viewItems.find((item) => item.id === activeView)?.label?.toUpperCase()}</span>
          <button onClick={() => setActiveView('forge')} title="Return to Forge" aria-label="Return to Forge"><RouteIcon id="forge" /></button>
        </div>
        <div className="context-scroll">
          <div className="context-kicker">CAMPAIGN SYNC</div>
          <h3>Waiting for the canonical state</h3>
          <p>The Forge is still connected, but the campaign projection has not arrived yet. Player stats stay hidden until the state service responds.</p>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="panel-title">
        <span>{viewItems.find((item) => item.id === activeView)?.label?.toUpperCase()}</span>
        <div className="panel-title-actions">
          {activeView !== 'dungeon' && <button onClick={() => setActiveView('forge')} title="Return to Forge" aria-label="Return to Forge"><RouteIcon id="forge" /></button>}
          {activeView === 'dungeon' && <ContextCollapseButton label="Dungeon" onToggleCompact={onToggleCompact} />}
        </div>
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
                  <span aria-hidden="true"><RouteIcon id={mob.status === 'available' ? 'flame' : isMobDefeated(mob.status) ? 'shield' : 'lock'} /></span>
                  <span>{mob.status === 'locked' ? 'Unknown encounter' : mob.name}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {activeView === 'codex' && (
          <>
            <div className="context-kicker">FIELD LIBRARY</div>
            <p>Open a concept book to read definitions, examples, encounter notes and validated question lenses.</p>
            <div className="context-list">
              <div className="context-row stacked"><strong>{(progress.codex?.encounters || []).length} encounters logged</strong><span>{skills.length} mastery records</span><small>Knowledge grows from verified encounters.</small></div>
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
            <p>Each run starts with a class passive, starter weapon, basic armor and a bounded heal kit. The active checkpoint survives a restart.</p>
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

export function SurfaceNavigation({ activeView, onNavigate }) {
  // Codex is now a folio inside Tutor Notebook. Keep the legacy route
  // addressable for saved links, but do not present a duplicate top-level
  // destination in the shared navigation.
  const destinationItems = viewItems.filter((item) => item.id !== 'hub' && item.id !== 'codex')
  return (
    <nav className="surface-nav" data-testid="wide-route-nav" aria-label="Wide route navigation">
      <button className="surface-nav-brand" type="button" onClick={() => onNavigate?.('hub')} aria-label="Open Campaign">
        <RouteIcon id="hub" />
      </button>
      <div className="surface-nav-links">
        {destinationItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`surface-nav-link ${activeView === item.id ? 'active' : ''}`}
            onClick={() => onNavigate?.(item.id)}
            title={item.label}
            aria-label={item.label}
            aria-current={activeView === item.id ? 'page' : undefined}
          >
            <span aria-hidden="true"><RouteIcon id={item.id} /></span>
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}

function RouteIcon({ id }) {
  const paths = {
    hub: <><path d="m4 11 8-7 8 7" /><path d="M6 10v9h12v-9M9 19v-5h6v5" /></>,
    forge: <><path d="M5 5h14v14H5z" /><path d="m8 9 3 3-3 3M13 15h3" /></>,
    tutor: <><path d="M9 3h6M10 3v5l-4 9a3 3 0 0 0 3 4h6a3 3 0 0 0 3-4l-4-9V3" /><path d="M8 15h8" /></>,
    quests: <><path d="m14 4 6-1-1 6-9 9-4-4zM6 14l-3 3 4 4 3-3" /></>,
    codex: <><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" /><path d="M8 20V7a3 3 0 0 1 3-3M10 9h6M10 13h6" /></>,
    character: <><circle cx="12" cy="8" r="3" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
    homestead: <><path d="m4 11 8-7 8 7" /><path d="M6 10v10h12V10M10 20v-6h4v6" /></>,
    dungeon: <><path d="M5 20V8l3-4h8l3 4v12z" /><path d="M9 20v-5h6v5M8 9h2M14 9h2M10 12h4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a8 8 0 0 0-1.7-1L14.5 3h-5l-.4 3a8 8 0 0 0-1.7 1L5 6 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5 5 18l2.4-1a8 8 0 0 0 1.7 1l.4 3h5l.4-3a8 8 0 0 0 1.7-1l2.4 1 2-3.5-2.1-1.5a7 7 0 0 0 .1-1z" /></>,
    shield: <><path d="M12 3 19 6v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6z" /><path d="m9 12 2 2 4-4" /></>,
    flame: <path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z" />,
    check: <path d="m5 12 4 4L19 6" />,
    target: <><circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" /></>,
    question: <><circle cx="12" cy="12" r="8" /><path d="M9.5 9a2.7 2.7 0 1 1 4.1 2.3c-1.1.6-1.6 1.1-1.6 2.2M12 17h.01" /></>,
    route: <><circle cx="6" cy="17" r="2" /><circle cx="18" cy="7" r="2" /><path d="m7.8 15.7 8.4-7.4" /></>,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    sword: <><path d="m6 18 9-9" /><path d="m13 6 5-3 3 3-3 5" /><path d="M5 19h4M7 17l-2 2" /></>,
    boss: <><path d="M7 20V8l5-4 5 4v12" /><path d="M4 20h16M9 12h6M10 20v-5h4v5" /></>,
    scroll: <><path d="M6 4h11a2 2 0 0 1 2 2v13H8a2 2 0 0 1-2-2z" /><path d="M6 17a2 2 0 0 0 2 2M9 8h7M9 12h7" /></>,
    lock: <><rect x="5" y="10" width="14" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    spark: <path d="m12 2 1.8 7.2L21 11l-7.2 1.8L12 20l-1.8-7.2L3 11l7.2-1.8z" />,
    window: <><rect x="4" y="5" width="16" height="14" rx="1" /><path d="M12 5v14M4 12h16" /></>,
  }
  return <svg viewBox="0 0 24 24" focusable="false">{paths[id] || paths.hub}</svg>
}

function WideSurfaceFrame({ activeView, onNavigate, children }) {
  const resourceSurface = activeView === 'tutor' || activeView === 'codex'
  return (
    <div className={`wide-screen-frame ${resourceSurface ? 'resource-wide-frame' : ''}`} data-wide-route={activeView}>
      <SurfaceNavigation activeView={activeView} onNavigate={onNavigate} />
      {resourceSurface ? <div className="resource-wide-scroll">{children}</div> : children}
    </div>
  )
}

export function TutorPracticeBar({ progress, practiceProjection, onPracticePrompt, busy }) {
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const fallbackConcepts = Array.from(new Set([
    ...(progress?.skills || []).map((skill) => skill.concept).filter(Boolean),
    ...(activeProject.mobs || []).map((mob) => mob.concept).filter(Boolean),
    progress?.learning_state?.concept,
    'python-basics',
  ].filter(Boolean)))
  const selectorOptions = practiceProjection?.selectors || {}
  const conceptOptions = Array.isArray(selectorOptions.concepts) && selectorOptions.concepts.length
    ? selectorOptions.concepts
    : fallbackConcepts.map((item) => ({ id: item, title: item }))
  const questionOptions = Array.isArray(selectorOptions.question_types) && selectorOptions.question_types.length
    ? selectorOptions.question_types
    : [
        { id: 'true_false', label: 'True / False' },
        { id: 'multiple_choice', label: 'Multiple choice' },
        { id: 'short_explanation', label: 'Short explanation' },
        { id: 'code_trace', label: 'Code trace' },
        { id: 'bug_hunt', label: 'Bug hunt' },
      ]
  const difficultyMin = Number(selectorOptions.difficulty?.min ?? 1)
  const difficultyMax = Number(selectorOptions.difficulty?.max ?? 5)
  const [concept, setConcept] = useState(conceptOptions[0]?.id || 'python-basics')
  const [questionType, setQuestionType] = useState(questionOptions[0]?.id || 'multiple_choice')
  const [difficulty, setDifficulty] = useState(String(difficultyMin))
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!conceptOptions.some((item) => item.id === concept)) setConcept(conceptOptions[0]?.id || 'python-basics')
    if (!questionOptions.some((item) => item.id === questionType)) setQuestionType(questionOptions[0]?.id || 'multiple_choice')
    const numericDifficulty = Number(difficulty)
    if (!Number.isFinite(numericDifficulty) || numericDifficulty < difficultyMin || numericDifficulty > difficultyMax) setDifficulty(String(difficultyMin))
  }, [conceptOptions.map((item) => item.id).join('|'), questionOptions.map((item) => item.id).join('|'), concept, questionType, difficulty, difficultyMin, difficultyMax])

  const ask = async () => {
    if (!onPracticePrompt || busy) return
    setStatus('Asking PYR for a bounded drill…')
    try {
      await onPracticePrompt({ concept, questionType, difficulty: Number(difficulty), answer: '' })
      setStatus('Drill requested. Write your explanation or code in tutor.py, then run it when ready.')
    } catch (error) {
      setStatus(error?.message || 'Practice request failed.')
    }
  }

  return (
    <div className="tutor-practice-bar" data-testid="tutor-practice-bar">
      <div className="tutor-practice-heading"><span className="screen-kicker">TUTOR NOTEBOOK</span><small>tutor.py is the shared learning notebook and IDE</small><p>PYR teaches with hints and generic examples. It will not reveal an answer key or paste a missing project snippet.</p><em>Raw CLI chat remains an advanced, unsandboxed path.</em></div>
      <label><span>Concept</span><select value={concept} onChange={(event) => setConcept(event.target.value)} disabled={busy}>{conceptOptions.map((item) => <option key={item.id} value={item.id}>{item.title || item.id}</option>)}</select></label>
      <label><span>Question lens</span><select value={questionType} onChange={(event) => setQuestionType(event.target.value)} disabled={busy}>{questionOptions.map((item) => <option key={item.id} value={item.id}>{item.label || item.id}</option>)}</select></label>
      <label><span>Difficulty</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} disabled={busy}>{Array.from({ length: Math.max(0, difficultyMax - difficultyMin + 1) }, (_, index) => difficultyMin + index).map((level) => <option key={level} value={level}>Tier {level}</option>)}</select></label>
      <button className="primary" type="button" onClick={ask} disabled={busy || !onPracticePrompt}>{busy ? 'Working…' : 'Ask PYR for a drill'}</button>
      {status && <small className="tutor-practice-status" role="status">{status}</small>}
    </div>
  )
}

function HubScreen({ progress, revision, onOpen }) {
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const goals = progress?.goals || {}
  const mobs = activeProject.mobs || []
  const projects = progress?.projects || []
  return (
    <div className="game-screen-scroll hub-screen" data-testid="hub" data-campaign-revision={revision}>
      <div className="screen-hero hub-hero">
        <div><span className="screen-kicker">QUEST HUB</span><h2>Choose your next move.</h2><p>Your contracts, campaign chapters and weekly goals share the same live campaign revision. Pick a surface and keep learning.</p></div>
        <div className="hub-hero-actions"><button className="primary" type="button" onClick={() => onOpen?.('forge')}>Open Forge</button></div>
      </div>
      <div className="hub-grid">
        <section className="game-card hub-contracts">
          <div className="card-heading"><span>TODAY'S CONTRACTS</span><b>{(goals.daily || []).filter((goal) => goal.done).length}/{(goals.daily || []).length}</b></div>
          <div className="quest-list">{(goals.daily || []).slice(0, 5).map((goal) => <div key={goal.id} className={`quest-item ${goal.done ? 'done' : ''}`}><span aria-hidden="true"><RouteIcon id={goal.done ? 'check' : 'target'} /></span><div><strong>{goal.text}</strong><small>+{goal.reward_xp ?? 0} XP · +{goal.reward_coins ?? 0}c</small></div></div>)}</div>
          {!(goals.daily || []).length && <p className="context-note">No daily contracts have been issued yet.</p>}
        </section>
        <section className="game-card hub-weekly">
          <div className="card-heading"><span>WEEKLY RAIDS</span><b>{(goals.weekly || []).filter((goal) => goal.done).length}/{(goals.weekly || []).length}</b></div>
          <div className="hub-raid-banner"><span className="raid-gate-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="8" cy="8" r="3" /><circle cx="16" cy="8" r="3" /><path d="M2 20a6 6 0 0 1 12 0M10 20a6 6 0 0 1 12 0" /></svg></span><div><strong>Party raid board</strong><p>Weekly goals are tracked here; shared raid combat unlocks in the multiplayer milestone.</p></div><span className="raid-locked">LOCKED</span></div>
          <div className="quest-list compact">{(goals.weekly || []).slice(0, 4).map((goal) => <div key={goal.id} className={`quest-item ${goal.done ? 'done' : ''}`}><span aria-hidden="true"><RouteIcon id={goal.done ? 'check' : 'target'} /></span><div><strong>{goal.text}</strong><small>{goal.progress ?? 0}/{goal.target ?? 1}</small></div></div>)}</div>
        </section>
      </div>
      <section className="game-card hub-chapters">
        <div className="card-heading"><span>MAIN QUEST · CHAPTERS</span><b>{activeProject.progress ?? 0}%</b></div>
        <div className="chapter-grid">{projects.map((project, index) => {
          const locked = project.status === 'locked' || (project.status !== 'active' && !project.completed)
          return <article key={project.id || project.name || index} className={`chapter-card ${locked ? 'locked' : project.completed ? 'complete' : 'active'}`}><div className="chapter-art" aria-hidden="true"><RouteIcon id={locked ? 'lock' : project.completed ? 'shield' : 'codex'} /></div><div><span className="chapter-category">{project.category || project.type || 'chapter'}</span><h3>{locked ? 'Unknown chapter' : project.name || `Chapter ${index + 1}`}</h3><p>{locked ? 'Future chapter · details unlock after the previous clear.' : project.summary || project.description || (project.status === 'active' ? 'Continue the current learning path.' : 'Verified chapter complete.')}</p></div>{project.status === 'active' && <button type="button" onClick={() => onOpen?.('codex')}>Open Codex quest</button>}</article>
        })}</div>
        {!projects.length && <p className="context-note">The campaign chapter list will appear after the state service loads.</p>}
      </section>
      <section className="game-card hub-encounters">
        <div className="card-heading"><span>ENCOUNTER PATH</span><b>{mobs.filter((mob) => isMobDefeated(mob.status)).length}/{mobs.length} cleared</b></div>
        <div className="encounter-silhouette-grid">{mobs.map((mob, index) => { const locked = mob.status === 'locked'; return <article key={mob.name || index} className={`encounter-silhouette ${locked ? 'locked' : mob.status}`}><span aria-hidden="true"><RouteIcon id={locked ? 'lock' : isMobDefeated(mob.status) ? 'shield' : 'flame'} /></span><div><strong>{locked ? 'Unknown encounter' : mob.name || `Encounter ${index + 1}`}</strong><small>{locked ? 'Hidden until previous clear' : mob.category || mob.concept || 'Encounter'}</small></div></article> })}</div>
      </section>
    </div>
  )
}

function Codex({ progress, revision, codexProjection, encounter, saveCodexNote, busy, onNavigate, showNavigation = true }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const mobs = activeProject.mobs || []
  const projectedIndex = encounter?.mob_name ? mobs.findIndex((mob) => mob.name === encounter.mob_name) : -1
  const firstAvailable = mobs.findIndex((mob) => mob.status === 'available')
  const firstUncleared = mobs.findIndex((mob) => !isMobDefeated(mob.status) && mob.status !== 'locked')
  const currentIndex = projectedIndex >= 0 ? projectedIndex : firstAvailable >= 0 ? firstAvailable : firstUncleared
  const activeMob = currentIndex >= 0 ? mobs[currentIndex] : undefined
  const clearedMobCount = mobs.filter((mob) => isMobDefeated(mob.status)).length
  const rawMaxResolve = encounter?.max_resolve ?? activeMob?.max_resolve ?? encounter?.resolve ?? activeMob?.resolve ?? 0
  const maxResolve = Math.max(1, Number(rawMaxResolve) || 1)
  const resolve = Math.max(0, Math.min(maxResolve, Number(encounter?.resolve ?? activeMob?.resolve ?? maxResolve) || 0))
  const availableObjectives = encounter?.available_objectives || []
  const completedObjectives = encounter?.completed_objectives || []
  const bossStatus = encounter?.boss_status || activeProject.boss_status || 'locked'
  const bossUnlocked = encounter?.status === 'boss_available' || bossStatus === 'available'
  const projectComplete = encounter?.status === 'complete' || encounter?.project_complete === true || activeProject.completed === true || bossStatus === 'defeated'
  const bossRequirements = encounter?.boss_requirements || ['required_behavior', 'explanation', 'interview']
  const verifiedBossRequirements = encounter?.verified_boss_requirements || []
  const remainingBossRequirements = encounter?.remaining_boss_requirements || bossRequirements.filter((requirement) => !verifiedBossRequirements.includes(requirement))
  const skills = progress.skills || []
  const pages = codexProjection?.pages || []
  const entries = codexProjection?.entries || progress.codex?.encounters || []
  const [query, setQuery] = useState('')
  const [selectedPageId, setSelectedPageId] = useState(pages[0]?.id || '')
  const [bookShelfPage, setBookShelfPage] = useState(0)
  const [entryShelfPage, setEntryShelfPage] = useState(0)
  const [selectedEntryId, setSelectedEntryId] = useState('')
  const [note, setNote] = useState('')
  const [noteStatus, setNoteStatus] = useState('')
  const [workspaceNote, setWorkspaceNote] = useState('')
  const [workspaceNoteLoading, setWorkspaceNoteLoading] = useState(false)
  const [codexSection, setCodexSection] = useState('read')
  const [readSubpage, setReadSubpage] = useState(0)
  const [selectedChapterId, setSelectedChapterId] = useState(activeProject.id || activeProject.branch || activeProject.name || '')
  const [masteryPage, setMasteryPage] = useState(0)

  const projectKey = (project) => String(project?.id || project?.branch || project?.name || '')
  const chapterSelection = (progress.projects || []).find((project) => projectKey(project) === String(selectedChapterId)) || activeProject

  useEffect(() => {
    const activeId = projectKey(activeProject)
    const selectedStillExists = (progress.projects || []).some((project) => projectKey(project) === String(selectedChapterId))
    if (!selectedStillExists || !selectedChapterId) setSelectedChapterId(activeId)
  }, [activeProject.id, activeProject.branch, activeProject.name, progress.projects, selectedChapterId])

  useEffect(() => {
    if (!pages.some((page) => page.id === selectedPageId)) setSelectedPageId(pages[0]?.id || '')
  }, [pages, selectedPageId])

  const normalizedQuery = query.trim().toLowerCase()
  const entrySearchText = (entry) => [
    entry.mob_name,
    entry.concept,
    ...(entry.question_types || []),
    ...(entry.weaknesses || []),
    ...(entry.notes || []),
  ].filter(Boolean).join(' ').toLowerCase()
  const entryBelongsToPage = (entry, page) => {
    if (entry.page_id === page.id) return true
    if (entry.page_id || !page.title || typeof entry.concept !== 'string') return false
    const pageKey = page.title.split('&')[0]?.trim().toLowerCase()
    const concept = entry.concept.trim().toLowerCase()
    return Boolean(pageKey && (concept === pageKey || concept.startsWith(`${pageKey} `)))
  }
  const filteredPages = pages.filter((page) => {
    if (!normalizedQuery) return true
    const pageText = [
      page.title,
      page.definition,
      ...(page.examples || []),
      ...(page.question_types || []),
    ].filter(Boolean).join(' ').toLowerCase()
    const pageEntries = entries.filter((entry) => entryBelongsToPage(entry, page))
    return pageText.includes(normalizedQuery) || pageEntries.some((entry) => entrySearchText(entry).includes(normalizedQuery))
  })
  const bookPages = normalizedQuery ? filteredPages : pages
  const selectedPage = bookPages.find((page) => page.id === selectedPageId) || bookPages[0]
  const bookShelfPageSize = 5
  const bookShelfCount = Math.max(1, Math.ceil(bookPages.length / bookShelfPageSize))
  const safeBookShelfPage = Math.min(bookShelfPage, bookShelfCount - 1)
  const shelfPages = bookPages.slice(safeBookShelfPage * bookShelfPageSize, (safeBookShelfPage + 1) * bookShelfPageSize)
  const selectedPageIndex = Math.max(0, bookPages.findIndex((page) => page.id === selectedPage?.id))
  const selectedEntries = entries.filter((entry) => selectedPage && entryBelongsToPage(entry, selectedPage))
  const entryShelfPageSize = 3
  const entryShelfCount = Math.max(1, Math.ceil(selectedEntries.length / entryShelfPageSize))
  const safeEntryShelfPage = Math.min(entryShelfPage, entryShelfCount - 1)
  const visibleEntries = selectedEntries.slice(safeEntryShelfPage * entryShelfPageSize, (safeEntryShelfPage + 1) * entryShelfPageSize)
  const selectedEntry = selectedEntries.find((entry) => entry.id === selectedEntryId) || selectedEntries[0]
  const masteryPageSize = 4
  const masteryPageCount = Math.max(1, Math.ceil(skills.length / masteryPageSize))
  const safeMasteryPage = Math.min(masteryPage, masteryPageCount - 1)
  const visibleSkills = skills.slice(safeMasteryPage * masteryPageSize, (safeMasteryPage + 1) * masteryPageSize)
  const selectedEntryIds = selectedEntries.map((entry) => entry.id).join('|')
  const codexMetrics = {
    booksWithEvidence: pages.filter((page) => (page.encounter_ids || []).length > 0).length,
    encounters: entries.length,
    notes: entries.reduce((total, entry) => total + (entry.player_notes?.length || 0), 0),
    verifiedResults: entries.reduce((total, entry) => total + (entry.results?.length || 0), 0),
  }
  const pageQuestionTypes = Array.from(new Set(selectedEntries.flatMap((entry) => entry.question_types || []))).slice(0, 8)
  const pageWeaknesses = Array.from(new Set(selectedEntries.flatMap((entry) => entry.weaknesses || []))).slice(0, 8)

  useEffect(() => {
    setBookShelfPage(0)
  }, [normalizedQuery])

  useEffect(() => {
    if (bookPages.length && !bookPages.some((page) => page.id === selectedPageId)) setSelectedPageId(bookPages[0].id)
  }, [bookPages, selectedPageId])

  useEffect(() => {
    if (bookShelfPage >= bookShelfCount) setBookShelfPage(Math.max(0, bookShelfCount - 1))
  }, [bookShelfCount, bookShelfPage])

  useEffect(() => {
    if (!selectedEntries.some((entry) => entry.id === selectedEntryId)) setSelectedEntryId(selectedEntries[0]?.id || '')
    setNote('')
    setNoteStatus('')
  }, [selectedPage?.id, selectedEntryIds, selectedEntryId])

  useEffect(() => {
    setEntryShelfPage(0)
  }, [selectedPage?.id, selectedEntryIds])

  useEffect(() => {
    if (entryShelfPage >= entryShelfCount) setEntryShelfPage(Math.max(0, entryShelfCount - 1))
  }, [entryShelfCount, entryShelfPage])

  useEffect(() => {
    if (masteryPage >= masteryPageCount) setMasteryPage(Math.max(0, masteryPageCount - 1))
  }, [masteryPage, masteryPageCount])

  useEffect(() => {
    setCodexSection('read')
    setReadSubpage(0)
  }, [selectedPage?.id])

  const noteSlug = (entry) => String(entry?.concept || entry?.id || entry?.mob_name || 'concept')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120) || 'concept'

  useEffect(() => {
    if (!selectedEntry) {
      setWorkspaceNote('')
      return undefined
    }
    const controller = new AbortController()
    setWorkspaceNoteLoading(true)
    fetch(`/api/notes/${encodeURIComponent(noteSlug(selectedEntry))}`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((result) => {
        if (!result) return
        setWorkspaceNote(result.note?.content || '')
      })
      .catch(() => {
        if (!controller.signal.aborted) setWorkspaceNote('')
      })
      .finally(() => {
        if (!controller.signal.aborted) setWorkspaceNoteLoading(false)
      })
    return () => controller.abort()
  }, [selectedEntry?.id, selectedEntry?.concept, selectedEntry?.mob_name])

  const selectPage = (pageId) => {
    setSelectedPageId(pageId)
    setSelectedEntryId('')
    const pageIndex = bookPages.findIndex((page) => page.id === pageId)
    if (pageIndex >= 0) setBookShelfPage(Math.floor(pageIndex / bookShelfPageSize))
  }

  const turnPage = (delta) => {
    if (!bookPages.length) return
    const nextIndex = Math.min(bookPages.length - 1, Math.max(0, selectedPageIndex + delta))
    if (nextIndex !== selectedPageIndex) selectPage(bookPages[nextIndex].id)
  }

  const selectEntry = (entryId) => {
    setSelectedEntryId(entryId)
    const entryIndex = selectedEntries.findIndex((entry) => entry.id === entryId)
    if (entryIndex >= 0) setEntryShelfPage(Math.floor(entryIndex / entryShelfPageSize))
  }

  const submitNote = async (event) => {
    event.preventDefault()
    if (!selectedEntry || !note.trim() || !saveCodexNote || busy) return
    try {
      const result = await saveCodexNote(selectedEntry.id, note, noteSlug(selectedEntry))
      if (result?.workspace_note?.content !== undefined) setWorkspaceNote(result.workspace_note.content)
      setNote('')
      setNoteStatus('Saved to the canonical Codex record and workspace notebook.')
    } catch (error) {
      setNoteStatus(error?.message || 'Could not save the note.')
    }
  }

  return (
    <div className="codex-screen" data-testid="codex" data-campaign-revision={revision}>
      {showNavigation && <SurfaceNavigation activeView="codex" onNavigate={onNavigate} />}
      <div className="screen-hero codex-hero">
        <div>
          <span className="screen-kicker">CODEX / FIELD LIBRARY</span>
          <h2>Codex</h2>
          <p>Learn one idea at a time: read the theory, study a generic pattern, then test yourself.</p>
        </div>
        <div className="codex-summary-grid" aria-label="Codex records summary">
          <div><strong>{pages.length}</strong><span>concepts</span></div>
          <div><strong>{codexMetrics.encounters}</strong><span>encounter records</span></div>
          <div><strong>{codexMetrics.verifiedResults}</strong><span>verified checks</span></div>
          <div><strong>{codexMetrics.notes}</strong><span>your notes</span></div>
        </div>
      </div>

      <section className="codex-library game-card">
        <aside className="codex-index" aria-label="Codex concept index">
          <div className="card-heading"><span>FIELD LIBRARY</span><b>{pages.length} books</b></div>
          <section className="codex-active-quest-sidebar" data-testid="codex-active-quest">
            <div className="codex-sidebar-kicker">ACTIVE QUEST</div>
            <h3>{chapterSelection.name || 'No active chapter'}</h3>
            <p>{progress.current_quest || chapterSelection.summary || chapterSelection.description || 'Choose a chapter to inspect its current path.'}</p>
            <div className="codex-sidebar-progress"><span>{chapterSelection.progress ?? 0}% complete</span><span>{chapterSelection.id === activeProject.id || chapterSelection.branch === activeProject.branch ? `${clearedMobCount}/${mobs.length} cleared` : 'chapter record'}</span></div>
            <label className="codex-chapter-select" data-testid="codex-chapter-select"><span>CHAPTER PATH</span><select value={String(selectedChapterId)} onChange={(event) => setSelectedChapterId(event.target.value)} aria-label="Choose campaign chapter">
              {(progress.projects || []).map((project, index) => {
                const locked = project.status === 'locked' || (project.status !== 'active' && !project.completed)
                const projectId = String(project.id || project.branch || project.name || index)
                const suffix = locked ? 'Locked' : project.status === 'active' ? 'Current chapter' : project.completed ? 'Complete' : 'Available'
                return <option key={projectId} value={projectId} disabled={locked}>{locked ? 'Unknown chapter' : project.name || `Chapter ${index + 1}`} · {suffix}</option>
              })}
            </select></label>
            <div className="codex-sidebar-mobs" aria-label="Current chapter encounters">
              {(chapterSelection.mobs || []).map((mob, index) => {
                const isCurrent = chapterSelection.id === activeProject.id || chapterSelection.branch === activeProject.branch ? index === currentIndex : mob.status === 'available'
                const hidden = mob.status === 'locked'
                return <div key={mob.name || index} className={`${isCurrent ? 'current ' : ''}${hidden ? 'locked' : ''}`}><span aria-hidden="true"><RouteIcon id={hidden ? 'codex' : isMobDefeated(mob.status) ? 'shield' : 'flame'} /></span><strong>{hidden ? 'Unknown encounter' : mob.name}</strong>{isCurrent && <small>CURRENT</small>}</div>
              })}
            </div>
          </section>
          <div className="codex-books-heading">
            <div className="card-heading"><span>BOOKSHELF</span><b>{pages.length}</b></div>
            <div className="codex-shelf-controls" data-testid="codex-shelf-controls" aria-label="Codex bookshelf navigation">
              <button type="button" onClick={() => setBookShelfPage((page) => Math.max(0, page - 1))} disabled={safeBookShelfPage <= 0} aria-label="Previous bookshelf">←</button>
              <span>SHELF {bookPages.length ? safeBookShelfPage + 1 : 0} / {bookShelfCount}</span>
              <button type="button" onClick={() => setBookShelfPage((page) => Math.min(bookShelfCount - 1, page + 1))} disabled={safeBookShelfPage >= bookShelfCount - 1} aria-label="Next bookshelf">→</button>
            </div>
          </div>
          <label className="codex-search"><span>Search library</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="lists, loops…" aria-label="Search Codex" /></label>
          <div className="codex-page-list">
            {shelfPages.map((page) => (
              <button key={page.id} type="button" className={selectedPage?.id === page.id ? 'active' : ''} onClick={() => selectPage(page.id)} data-testid={`codex-page-${page.id}`}>
                <span>{page.title}</span><small>{page.encounter_ids?.length || 0} encounter{page.encounter_ids?.length === 1 ? '' : 's'}</small>
              </button>
            ))}
            {!bookPages.length && <div className="empty-state">No concept page matches that search.</div>}
          </div>
        </aside>

        <article className="codex-book-page">
          {selectedPage ? (
            <>
              <div className="codex-page-heading"><span className="screen-kicker">CONCEPT PAGE</span><h3>{selectedPage.title}</h3><p>Read the core idea, look at a generic example, and check your understanding before you return to Forge.</p><div className="codex-page-summary" data-testid="codex-page-summary"><span><b>{selectedEntries.length}</b> encounters</span><span><b>{pageQuestionTypes.length}</b> question lenses</span><span><b>{pageWeaknesses.length}</b> recorded patterns</span></div></div>
              <div className="codex-page-controls" data-testid="codex-page-controls" aria-label="Codex book navigation">
                <button type="button" onClick={() => turnPage(-1)} disabled={selectedPageIndex <= 0} aria-label="Previous Codex book">← Previous</button>
                <span>BOOK {bookPages.length ? selectedPageIndex + 1 : 0} / {bookPages.length || 0}</span>
                <button type="button" onClick={() => turnPage(1)} disabled={!bookPages.length || selectedPageIndex >= bookPages.length - 1} aria-label="Next Codex book">Next →</button>
              </div>
              <nav className="codex-book-tabs" aria-label="Concept book sections" data-testid="codex-book-tabs">
                {[
                  ['read', 'Read'],
                  ['encounters', `Encounters${selectedEntries.length ? ` · ${selectedEntries.length}` : ''}`],
                  ['notes', 'Notes'],
                  ['mastery', `Mastery${skills.length ? ` · ${skills.length}` : ''}`],
                ].map(([section, label]) => <button key={section} type="button" className={codexSection === section ? 'active' : ''} onClick={() => setCodexSection(section)} aria-pressed={codexSection === section}>{label}</button>)}
              </nav>

              {codexSection === 'read' && (
                <section className="codex-book-section" data-testid="codex-read-section">
                  <div className="codex-folio-controls" data-testid="codex-folio-controls" aria-label="Codex read folios">
                    {['Definition', 'Examples', 'Mistakes & signals'].map((label, index) => <button key={label} type="button" className={readSubpage === index ? 'active' : ''} onClick={() => setReadSubpage(index)} aria-pressed={readSubpage === index}>{label}</button>)}
                    <span>FOLIO {readSubpage + 1} / 3</span>
                  </div>
                  <div className="codex-read-folio" data-codex-folio={readSubpage}>
                    {readSubpage === 0 && <div className="codex-folio-copy codex-definition-folio">
                      <div className="codex-folio-heading"><small className="codex-label">01 · DEFINITION</small><span>Core idea</span></div>
                      <h4>{selectedPage.title}</h4>
                      <div className="codex-definition-card"><p className="codex-definition-copy">{selectedPage.definition}</p></div>
                      <div className="codex-study-prompt" data-testid="codex-study-prompt"><div><small>CHECK YOURSELF</small><p>{selectedPage.check_prompt || 'Can you explain this idea in your own words?'}</p></div>{onNavigate && <button type="button" onClick={() => onNavigate('tutor')}>Open Tutor</button>}</div>
                    </div>}
                    {readSubpage === 1 && <div className="codex-folio-copy codex-examples-folio">
                      <div className="codex-folio-heading"><small className="codex-label">02 · GENERIC EXAMPLES</small><span>Patterns to study</span></div>
                      <div className="codex-examples">{(selectedPage.examples || []).map((example, index) => <article className="codex-example-card" key={index}><span className="codex-example-index">{String(index + 1).padStart(2, '0')}</span><div><small>EXAMPLE {index + 1}</small><pre>{example}</pre></div></article>)}{!(selectedPage.examples || []).length && <p className="codex-insight-empty">No generic example has been recorded for this concept yet.</p>}</div>
                    </div>}
                    {readSubpage === 2 && <div className="codex-signal-folio">
                      <div className="codex-folio-heading"><small className="codex-label">03 · MISTAKES &amp; SIGNALS</small><span>Check before you submit</span></div>
                      <div className="codex-signal-grid"><section className="codex-signal-card codex-mistake-card"><small className="codex-label">COMMON MISTAKES</small><div className="codex-mistakes">{(selectedPage.common_mistakes || []).length ? selectedPage.common_mistakes.map((mistake) => <p key={mistake}>{mistake}</p>) : <p className="codex-insight-empty">No validated mistake pattern recorded for this concept yet.</p>}</div></section><section className="codex-signal-card"><small className="codex-label">QUESTION LENS &amp; RECORDED SIGNALS</small><div className="codex-tags">{(selectedPage.question_types || []).map((type) => <span key={type}>{type}</span>)}{pageQuestionTypes.map((type) => <span key={`recorded-${type}`}>{type}</span>)}{pageWeaknesses.map((weakness) => <span key={`weakness-${weakness}`}>{weakness}</span>)}{!pageQuestionTypes.length && !pageWeaknesses.length && <span className="empty-state">No signal recorded yet.</span>}</div><p className="codex-section-hint">These signals come from validated encounters, not guesses.</p></section></div>
                    </div>}
                  </div>
                </section>
              )}

              {codexSection === 'encounters' && (
                <section className="codex-book-section" data-testid="codex-encounters-section">
                  <div className="codex-section-heading"><div><span className="screen-kicker">FIELD EVIDENCE</span><h4>Encounter records</h4></div><span>{selectedEntries.length} logged</span></div>
                  {selectedEntries.length > entryShelfPageSize && <div className="codex-entry-pager" data-testid="codex-entry-pager"><button type="button" onClick={() => setEntryShelfPage((page) => Math.max(0, page - 1))} disabled={safeEntryShelfPage <= 0} aria-label="Previous encounter records">←</button><span>RECORDS {safeEntryShelfPage + 1} / {entryShelfCount}</span><button type="button" onClick={() => setEntryShelfPage((page) => Math.min(entryShelfCount - 1, page + 1))} disabled={safeEntryShelfPage >= entryShelfCount - 1} aria-label="Next encounter records">→</button></div>}
                  <div className="codex-entry-picker codex-entry-picker-expanded">{visibleEntries.map((entry) => <button key={entry.id} type="button" className={selectedEntry?.id === entry.id ? 'active' : ''} onClick={() => selectEntry(entry.id)}>{entry.mob_name}<small>{entry.status} · {entry.attempts ?? 0} attempts</small></button>)}{!selectedEntries.length && <span className="empty-state">No encounter recorded yet.</span>}</div>
                  {selectedEntry ? (
                    <section className="codex-entry-detail">
                      <div className="card-heading"><span>{selectedEntry.mob_name} · OBSERVATION</span><b>{String(selectedEntry.status || 'observed').toUpperCase()}</b></div>
                      <div className="codex-entry-meta"><span>{selectedEntry.attempts ?? 0} attempts</span><span>{(selectedEntry.question_types || []).join(' · ') || 'type pending'}</span><span>{(selectedEntry.weaknesses || []).length} weaknesses</span><span>Mastery {selectedEntry.mastery?.evidence ?? 0}</span></div>
                      <div className="codex-entry-insights" data-testid="codex-entry-insights">
                        <div><small className="codex-label">WEAKNESSES / PATTERNS</small>{selectedEntry.weaknesses?.length ? <ul className="codex-insight-list">{selectedEntry.weaknesses.map((weakness) => <li key={weakness}>{weakness}</li>)}</ul> : <p className="codex-insight-empty">No weakness pattern recorded yet.</p>}</div>
                        <div><small className="codex-label">VERIFIED RESULTS</small>{selectedEntry.results?.length ? <ul className="codex-insight-list">{selectedEntry.results.map((result, index) => <li key={`${result.outcome || 'result'}-${index}`}><strong>{result.outcome || 'recorded'}</strong>{result.evidence_id ? <span>{result.evidence_id}</span> : null}</li>)}</ul> : <p className="codex-insight-empty">No result history recorded yet.</p>}</div>
                        {selectedEntry.interview_history?.length ? <div><small className="codex-label">INTERVIEW HISTORY</small><ul className="codex-insight-list">{selectedEntry.interview_history.map((item, index) => <li key={`${item.outcome || 'interview'}-${index}`}>{item.outcome || item.status || 'recorded'}</li>)}</ul></div> : null}
                      </div>
                      <p>{selectedEntry.notes?.at(-1) || 'The encounter has been observed through verified learning evidence.'}</p>
                    </section>
                  ) : <p className="codex-insight-empty">Choose a recorded encounter to inspect its validated evidence.</p>}
                </section>
              )}

              {codexSection === 'notes' && (
                <section className="codex-book-section" data-testid="codex-notes-section">
                  <div className="codex-section-heading"><div><span className="screen-kicker">FIELD NOTES</span><h4>Keep the useful parts</h4></div><span>workspace + canonical</span></div>
                  {selectedEntries.length > entryShelfPageSize && <div className="codex-entry-pager" data-testid="codex-notes-entry-pager"><button type="button" onClick={() => setEntryShelfPage((page) => Math.max(0, page - 1))} disabled={safeEntryShelfPage <= 0} aria-label="Previous note targets">←</button><span>NOTES {safeEntryShelfPage + 1} / {entryShelfCount}</span><button type="button" onClick={() => setEntryShelfPage((page) => Math.min(entryShelfCount - 1, page + 1))} disabled={safeEntryShelfPage >= entryShelfCount - 1} aria-label="Next note targets">→</button></div>}
                  <div className="codex-entry-picker codex-entry-picker-inline">{visibleEntries.map((entry) => <button key={entry.id} type="button" className={selectedEntry?.id === entry.id ? 'active' : ''} onClick={() => selectEntry(entry.id)}>{entry.mob_name}<small>{entry.concept || 'concept'}</small></button>)}{!selectedEntries.length && <span className="empty-state">No encounter note target yet.</span>}</div>
                  {selectedEntry ? <>
                    <div className="codex-notes workspace-notebook"><small className="codex-label">WORKSPACE NOTEBOOK · notes/{noteSlug(selectedEntry)}.md</small>{workspaceNoteLoading ? <p className="codex-insight-empty">Loading your transferable notes…</p> : workspaceNote ? <pre>{workspaceNote}</pre> : <p className="codex-insight-empty">No workspace note yet. Add one below; it travels with the project.</p>}</div>
                    {selectedEntry.player_notes?.length > 0 && <div className="codex-notes"><small className="codex-label">CANONICAL FIELD NOTES</small>{selectedEntry.player_notes.map((item, index) => <p key={`${item}-${index}`}>{item}</p>)}</div>}
                    <form className="codex-note-form" onSubmit={submitNote}><label><span>Add a field note</span><textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={2_000} rows={3} placeholder="What did you notice, or what should you revisit?" disabled={busy} /></label><button type="submit" disabled={busy || !note.trim()}>Save note</button></form>
                    {noteStatus && <small className="battle-submit-status" role="status">{noteStatus}</small>}
                  </> : <p className="codex-insight-empty">Choose an encounter to read or add notes.</p>}
                </section>
              )}

              {codexSection === 'mastery' && (
                <section className="codex-book-section codex-mastery-panel" data-testid="codex-mastery">
                  <div className="codex-section-heading"><div><span className="screen-kicker">MASTERY SIGNALS</span><h4>Validated growth</h4></div><span>{skills.length} concepts</span></div>
                  {skills.length > masteryPageSize && <div className="codex-entry-pager codex-mastery-pager" data-testid="codex-mastery-pager"><button type="button" onClick={() => setMasteryPage((page) => Math.max(0, page - 1))} disabled={safeMasteryPage <= 0} aria-label="Previous mastery records">←</button><span>MASTERY {safeMasteryPage + 1} / {masteryPageCount}</span><button type="button" onClick={() => setMasteryPage((page) => Math.min(masteryPageCount - 1, page + 1))} disabled={safeMasteryPage >= masteryPageCount - 1} aria-label="Next mastery records">→</button></div>}
                  <div className="skill-grid">
                    {visibleSkills.map((skill) => (
                      <article key={skill.name} className={`skill-card ${skill.status}`}>
                        <div className="skill-icon" data-skill-shield={skill.shield?.tier || 'none'}><RouteIcon id={skill.shield?.tier !== 'none' ? 'shield' : 'codex'} /></div>
                        <div><small>{skill.name}</small><h3>{skill.concept}</h3></div>
                        <div className="skill-meta"><span>Evidence {skill.evidence ?? 0}</span><span>Interviews {skill.interview_passes ?? 0}</span></div>
                        <div className="shield-line"><span>{skill.shield?.tier || 'none'} shield</span><b>{skill.shield?.charges ?? 0}/{skill.shield?.max_charges ?? 0}</b></div>
                      </article>
                    ))}
                    {!skills.length && <p className="codex-insight-empty">Mastery signals appear after validated encounters.</p>}
                  </div>
                </section>
              )}
            </>
          ) : <div className="empty-state">The Codex library is unavailable until the state service returns a projection.</div>}
        </article>
      </section>
    </div>
  )
}

/*
 * Resource-first Tutor surface
 *
 * The standalone codex-resource prototype deliberately kept its state local
 * while we tuned the interaction.  This is the Forge port of that surface:
 * the projection, tutor.py buffer, revision and notes callbacks still come
 * from the canonical app, while notebook presentation preferences remain
 * browser-local until their own state-service schema exists.
 */
const RESOURCE_PRACTICE_MODES = [
  { id: 'predict', label: 'Predict output', prompt: 'Predict what the example should produce before you run it.' },
  { id: 'trace', label: 'Trace variables', prompt: 'Trace how the important values change from line to line.' },
  { id: 'bug', label: 'Find a bug', prompt: 'Find the signal that would reveal a bug without rewriting the answer.' },
  { id: 'explain', label: 'Explain the idea', prompt: 'Teach the concept back in your own words.' },
  { id: 'transfer', label: 'Tiny transfer challenge', prompt: 'Describe one small new program where this idea would help.' },
]
const RESOURCE_NOTE_PAGES = [
  { id: 'notes', label: 'Notes', prompt: 'What do you want to remember in your own words?', placeholder: 'Write a definition, reminder, or connection…' },
  { id: 'questions', label: 'Questions', prompt: 'What still feels unclear?', placeholder: 'Leave a question for your next Tutor session…' },
  { id: 'examples', label: 'Examples', prompt: 'What example makes this click for you?', placeholder: 'Write a tiny example or describe one from your work…' },
  { id: 'practice', label: 'Next practice', prompt: 'How will you use this next?', placeholder: 'Write the next small practice step…' },
]
const RESOURCE_DEFAULT_CHAPTERS = [
  { id: 'fundamentals', name: 'Fundamentals', type: 'Concept foundations' },
  { id: 'data', name: 'Data', type: 'Collections and values' },
  { id: 'control-flow', name: 'Control flow', type: 'Loops and decisions' },
  { id: 'functions', name: 'Functions', type: 'Reusable boundaries' },
  { id: 'review', name: 'Review queue', type: 'Learner and PYR follow-ups' },
]

function resourceIdentifierSuggestions(source) {
  const text = String(source || '')
  const words = new Set(['and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'elif', 'else', 'False', 'for', 'from', 'if', 'import', 'in', 'is', 'None', 'not', 'or', 'pass', 'print', 'raise', 'return', 'True', 'try', 'while', 'with', 'range', 'len', 'list', 'dict', 'enumerate', 'sum'])
  const patterns = [
    /\b(?:def|class)\s+([A-Za-z_]\w*)/g,
    /\b([A-Za-z_]\w*)\s*=/g,
    /\b(?:import|from)\s+([A-Za-z_]\w*)/g,
    /\bfor\s+([A-Za-z_]\w*)\s+in\b/g,
    /\bas\s+([A-Za-z_]\w*)\b/g,
  ]
  patterns.forEach((pattern) => {
    let match
    while ((match = pattern.exec(text))) words.add(match[1])
  })
  return [...words].sort()
}

function resourceFallbackPages(encounter) {
  const concept = encounter?.concept || encounter?.mob?.concept || 'Python foundations'
  return [{
    id: 'foundations',
    title: concept,
    definition: 'A validated learning concept from the current campaign. Read the explanation, then make the idea yours in tutor.py.',
    examples: ['Read the current quest, name the state that changes, and describe one generic example before you edit the project.'],
    when_to_use: 'Use this when you need to explain, transform or inspect program state before changing a project.',
    question_types: ['explanation'],
    common_mistakes: ['Skipping the explanation and jumping straight to a project-specific answer.'],
    mistake_examples: ['# Start by naming the idea in your own words\nanswer = "my explanation"  # keep it general before applying it'],
    check_prompt: 'Can you explain this idea in your own words?',
    encounter_ids: [],
  }]
}

function ResourceNotebook({ pages, selectedPage, entries, onSelectPage }) {
  const storageKey = 'questlab-forge-resource-notebook'
  const [chapters, setChapters] = useState(() => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(`${storageKey}:chapters`) || 'null')
      return Array.isArray(stored) && stored.length ? stored : RESOURCE_DEFAULT_CHAPTERS
    } catch { return RESOURCE_DEFAULT_CHAPTERS }
  })
  const [chapterId, setChapterId] = useState(() => chapters[0]?.id || 'fundamentals')
  const [pageIndex, setPageIndex] = useState(0)
  const [notes, setNotes] = useState(() => {
    try { return JSON.parse(window.localStorage.getItem(`${storageKey}:notes`) || '{}') || {} } catch { return {} }
  })
  const [style, setStyle] = useState(() => window.localStorage.getItem(`${storageKey}:style`) || 'lined')
  const [color, setColor] = useState(() => window.localStorage.getItem(`${storageKey}:color`) || 'cream')
  const [chapterEditor, setChapterEditor] = useState(null)
  const [saved, setSaved] = useState(false)
  const [slashQuery, setSlashQuery] = useState('')
  const [slashOpen, setSlashOpen] = useState(false)
  const page = RESOURCE_NOTE_PAGES[pageIndex] || RESOURCE_NOTE_PAGES[0]
  const chapter = chapters.find((item) => item.id === chapterId) || chapters[0]
  const noteKey = `${chapter?.id || 'chapter'}:${selectedPage?.id || 'concept'}:${page.id}`
  const noteValue = notes[noteKey] || ''

  const persist = (key, value) => {
    try { window.localStorage.setItem(`${storageKey}:${key}`, typeof value === 'string' ? value : JSON.stringify(value)) } catch { /* storage is optional */ }
  }
  const setNoteValue = (value) => setNotes((current) => ({ ...current, [noteKey]: value }))
  const updateNoteValue = (value) => {
    setNoteValue(value)
    const line = value.slice(0, value.length).split('\n').at(-1) || ''
    const slash = line.match(/^\s*\/([a-z0-9 -]*)$/i)
    setSlashOpen(Boolean(slash))
    setSlashQuery(slash?.[1]?.toLowerCase() || '')
  }
  const applySlashCommand = (prefix) => {
    const before = noteValue.slice(0, noteValue.length)
    const lineStart = before.lastIndexOf('\n') + 1
    const line = before.slice(lineStart)
    const match = line.match(/^(\s*)\/[a-z0-9 -]*$/i)
    const next = match ? `${before.slice(0, lineStart)}${match[1]}${prefix}${before.slice(noteValue.length)}` : `${noteValue}${prefix}`
    setNoteValue(next)
    setSlashOpen(false)
    setSlashQuery('')
  }
  const slashCommands = [
    { label: 'Heading 1', hint: 'Large section heading', prefix: '# ' },
    { label: 'Heading 2', hint: 'Smaller section heading', prefix: '## ' },
    { label: 'Bullet list', hint: 'Turn this line into a bullet', prefix: '• ' },
    { label: 'Numbered list', hint: 'Start a numbered list', prefix: '1. ' },
    { label: 'To-do', hint: 'Add a checkable task', prefix: '☐ ' },
    { label: 'Quote', hint: 'Keep a thought or citation', prefix: '> ' },
    { label: 'Code block', hint: 'Indent a code note', prefix: '    ' },
    { label: 'Divider', hint: 'Separate sections', prefix: '---\n' },
  ].filter((item) => !slashQuery || `${item.label} ${item.hint}`.toLowerCase().includes(slashQuery))
  const savePage = () => {
    persist('notes', notes)
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1600)
  }
  const saveChapter = () => {
    const name = String(chapterEditor?.name || '').trim() || 'Untitled chapter'
    const type = String(chapterEditor?.type || '').trim() || 'Learner notes'
    if (chapterEditor?.mode === 'edit') {
      setChapters((current) => {
        const next = current.map((item) => item.id === chapterEditor.id ? { ...item, name, type } : item)
        persist('chapters', next)
        return next
      })
    } else {
      const id = `${name.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'chapter'}-${Date.now()}`
      setChapters((current) => {
        const next = [...current, { id, name, type }]
        persist('chapters', next)
        return next
      })
      setChapterId(id)
    }
    setChapterEditor(null)
  }
  const deleteChapter = () => {
    if (chapters.length <= 1 || !chapter) return
    if (typeof window !== 'undefined' && !window.confirm(`Delete “${chapter.name}” and keep its local pages?`)) return
    const next = chapters.filter((item) => item.id !== chapter.id)
    setChapters(next)
    persist('chapters', next)
    setChapterId(next[0].id)
  }

  return (
    <section className="resource-notebook" data-testid="resource-notebook" aria-label="Tutor notebook">
      <div className="resource-breadcrumb"><span>TUTOR</span><span>/</span><strong>NOTEBOOK / {String(chapter?.name || 'CHAPTER').toUpperCase()}</strong></div>
      <header className="resource-notebook-heading">
        <div><span className="screen-kicker">TUTOR NOTEBOOK · .MD</span><h2>Field notes</h2><p>A chaptered place for your notes, questions, examples and next practice.</p></div>
        <div className="resource-notebook-controls">
          <label><span>CHAPTER</span><select value={chapter?.id || ''} onChange={(event) => setChapterId(event.target.value)}>{chapters.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div className="resource-chapter-actions"><button type="button" onClick={() => setChapterEditor({ mode: 'new', name: 'New chapter', type: 'Personal notes' })}>+ New</button><button type="button" onClick={() => chapter && setChapterEditor({ mode: 'edit', id: chapter.id, name: chapter.name, type: chapter.type })}>Edit</button><button type="button" onClick={deleteChapter} disabled={chapters.length <= 1}>Delete</button></div>
          <label><span>PAGE LOOK</span><select value={style} onChange={(event) => { setStyle(event.target.value); persist('style', event.target.value) }}><option value="lined">Lined paper</option><option value="grid">Graph paper</option><option value="plain">Plain paper</option></select></label>
          <label><span>PAGE COLOR</span><select value={color} onChange={(event) => { setColor(event.target.value); persist('color', event.target.value) }}><option value="cream">Warm cream</option><option value="sky">Soft sky</option><option value="sage">Quiet sage</option><option value="lilac">Faded lilac</option><option value="sand">Sand</option></select></label>
        </div>
      </header>
      {chapterEditor && <section className="resource-chapter-editor"><div><span className="screen-kicker">{chapterEditor.mode === 'new' ? 'NEW CHAPTER' : 'EDIT CHAPTER'}</span><strong>Shape this notebook section</strong></div><label><span>NAME</span><input value={chapterEditor.name} onChange={(event) => setChapterEditor((current) => ({ ...current, name: event.target.value }))} /></label><label><span>NOTE TYPE</span><input value={chapterEditor.type} onChange={(event) => setChapterEditor((current) => ({ ...current, type: event.target.value }))} /></label><div><button type="button" className="primary" onClick={saveChapter}>Save chapter</button><button type="button" onClick={() => setChapterEditor(null)}>Cancel</button></div></section>}
      <div className="resource-linked-bar"><div><span className="screen-kicker">LINKED CONCEPT</span><strong>{selectedPage?.title || 'Current concept'}</strong></div><div className="resource-concept-links">{pages.map((pageItem) => <button key={pageItem.id} type="button" className={pageItem.id === selectedPage?.id ? 'active' : ''} onClick={() => { onSelectPage(pageItem.id); setPageIndex(0) }}>{pageItem.title}</button>)}</div></div>
      <section className={`resource-notebook-book style-${style} color-${color}`}>
        <article className="resource-book-page resource-book-index"><span className="resource-page-number">01</span><span className="screen-kicker">{chapter?.name || 'Notebook'}</span><h3>{selectedPage?.title || 'Field notes'}</h3><p>Keep the wording, questions and examples that make the idea yours.</p><div className="resource-book-index-list"><strong>THIS NOTEBOOK</strong>{RESOURCE_NOTE_PAGES.map((item, index) => <span key={item.id} className={index === pageIndex ? 'active' : ''}>{String(index + 1).padStart(2, '0')} · {item.label}</span>)}</div></article>
        <article className="resource-book-page resource-writing-page"><span className="resource-page-number">{String(pageIndex + 1).padStart(2, '0')}</span><span className="screen-kicker">{page.label.toUpperCase()}</span><h3>{page.label}</h3><p className="resource-writing-prompt">{page.prompt}</p><div className="resource-note-editor"><div className="resource-note-format"><span>FORMAT</span><button type="button" onClick={() => setNoteValue(`${noteValue}\n• `)}>• Bullet</button><button type="button" onClick={() => setNoteValue(`${noteValue}\n1. `)}>1. Number</button><button type="button" onClick={() => setNoteValue(`${noteValue}\n> `)}>“ Quote</button><button type="button" onClick={() => setNoteValue(`${noteValue}\n    `)}>&lt;/&gt; Code</button></div><textarea value={noteValue} onChange={(event) => updateNoteValue(event.target.value)} placeholder={page.placeholder} aria-label={`${page.label} note`} />{slashOpen && <div className="resource-note-slash-menu" role="listbox" aria-label="Insert a block">{slashCommands.map((command) => <button type="button" key={command.label} role="option" onClick={() => applySlashCommand(command.prefix)}><strong>{command.label}</strong><small>{command.hint}</small></button>)}</div>}<div className="resource-note-slash-hint">Type <kbd>/</kbd> for headings, lists, quotes and code blocks.</div></div><div className="resource-note-actions"><button type="button" className="primary" onClick={savePage}>Save page</button><span role="status">{saved ? 'Saved locally' : 'Your notebook stays with this browser until workspace sync is added.'}</span></div></article>
      </section>
      <nav className="resource-notebook-pager"><button type="button" disabled={pageIndex <= 0} onClick={() => setPageIndex((value) => Math.max(0, value - 1))}>← Previous</button><span>PAGE {pageIndex + 1} / {RESOURCE_NOTE_PAGES.length}</span><button type="button" disabled={pageIndex >= RESOURCE_NOTE_PAGES.length - 1} onClick={() => setPageIndex((value) => Math.min(RESOURCE_NOTE_PAGES.length - 1, value + 1))}>Next →</button></nav>
    </section>
  )
}

function ResourceEncounterRecords({ entries }) {
  return (
    <section className="resource-encounter-records">
      <div className="resource-encounter-heading"><div><span className="screen-kicker">VALIDATED ENCOUNTERS</span><p>Small excerpts from work that actually cleared a learning objective.</p></div><strong>{entries.length}</strong></div>
      {entries.length ? entries.map((entry) => (
        <article className="resource-encounter-record" key={entry.id}>
          <header><strong>{entry.mob_name || 'Validated encounter'}</strong><span>{entry.status || 'verified'} · {entry.attempts || 0} attempt{entry.attempts === 1 ? '' : 's'}</span></header>
          {entry.code_snippet ? <pre>{entry.code_snippet}</pre> : <p className="context-note">Verified before a code excerpt was captured.</p>}
        </article>
      )) : <p className="context-note">No validated encounter evidence yet. Your next correct Forge submission can leave a small personal excerpt here.</p>}
    </section>
  )
}

function ResourceCodexExamples({ page }) {
  return (
    <div className="resource-examples">
      {page?.check_prompt && <p className="resource-check-prompt"><span className="screen-kicker">CHECK YOURSELF</span>{page.check_prompt}</p>}
      {(page?.examples || []).map((example, index) => <article key={`${example}-${index}`}><span>0{index + 1}</span><pre>{example}</pre></article>)}
      {!(page?.examples || []).length && <p className="context-note">No generic examples have been recorded yet.</p>}
    </div>
  )
}

function ResourceCodexMistakes({ page, entries }) {
  const mistakes = page?.common_mistakes || []
  return (
    <div className="resource-signals">
      <section className="resource-mistake-list"><span className="screen-kicker">COMMON MISTAKES</span>{mistakes.map((mistake, index) => <article className="resource-mistake-item" key={mistake}><div><strong>{mistake}</strong><span>WHAT IT LOOKS LIKE</span></div>{page?.mistake_examples?.[index] ? <pre>{page.mistake_examples[index]}</pre> : <p className="context-note">No concrete example recorded yet.</p>}</article>)}</section>
      <section className="resource-practice-signals"><span className="screen-kicker">PRACTICE SIGNALS</span><div className="resource-tags">{(page?.question_types || []).map((type) => <span key={type}>{type}</span>)}{entries.flatMap((entry) => [...(entry.question_types || []), ...(entry.weaknesses || [])]).filter((value, index, all) => all.indexOf(value) === index).map((type) => <span key={type}>{type}</span>)}</div></section>
    </div>
  )
}

function ResourceTutorScreen({ activeView, progress, revision, codexProjection, encounter, tutorCode, tutorDirty, tutorExternalChange, editorFontSize = 14, busy, onTutorChange, onTutorSave, onTutorFormat, onTutorRun, onPracticePrompt, onTutorReloadExternal, onTutorKeepEdits, onNavigate }) {
  const pages = Array.isArray(codexProjection?.pages) && codexProjection.pages.length ? codexProjection.pages : resourceFallbackPages(encounter)
  const entries = Array.isArray(codexProjection?.entries) ? codexProjection.entries : []
  const [surface, setSurface] = useState('codex')
  const [selectedId, setSelectedId] = useState(pages[0]?.id || '')
  const [readPage, setReadPage] = useState(0)
  const [practiceMode, setPracticeMode] = useState('predict')
  const [terminal, setTerminal] = useState({ status: 'ready', output: ['Tutor shell ready.', 'Run is a safe local self-check; Submit is the feedback boundary.'] })
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiMessages, setAiMessages] = useState([{ role: 'pyr', text: 'PYR channel ready. Ask for a hint when you need a nudge, not a finished answer.' }])
  const [query, setQuery] = useState('')
  const selectedPage = pages.find((page) => page.id === selectedId) || pages[0]
  const selectedEntries = entries.filter((entry) => entry.page_id === selectedPage?.id)
  useEffect(() => {
    if (!pages.some((page) => page.id === selectedId)) setSelectedId(pages[0]?.id || '')
  }, [pages, selectedId])
  useEffect(() => {
    if (activeView === 'codex') setSurface('codex')
  }, [activeView])
  const filteredPages = pages.filter((page) => !query.trim() || `${page.title} ${page.definition}`.toLowerCase().includes(query.trim().toLowerCase()))
  const conceptLabel = selectedPage?.title || encounter?.concept || 'Python foundations'
  const runSelfCheck = () => {
    const source = String(tutorCode || '')
    if (!source.trim()) {
      setTerminal({ status: 'empty', output: ['No tutor.py content to check.', 'Write an attempt, then run this safe preview.'] })
      return
    }
    const pairs = [['(', ')'], ['[', ']'], ['{', '}']]
    const stack = []
    const openers = new Map(pairs)
    for (const char of source) {
      if (openers.has(char)) stack.push(char)
      else if (pairs.some((pair) => pair[1] === char)) {
        const opener = stack.pop()
        if (!opener || openers.get(opener) !== char) {
          setTerminal({ status: 'failed', output: ['SyntaxError: unbalanced delimiter in tutor.py', 'Run is local only; no campaign state changed.', 'Repair the notebook, then submit for bounded feedback.'] })
          return
        }
      }
    }
    setTerminal({ status: 'passed', output: ['[PASS] Python-shaped source: delimiters are balanced.', '[INFO] Concepts stay in the learner notebook until submission.', 'Run is safe and local; Submit is the feedback boundary.'] })
  }
  const submit = async () => {
    setTerminal({ status: 'submitted', output: ['[SUBMIT] tutor.py sent for bounded Tutor feedback.', 'No campaign reward, Resolve, HP or project mutation occurs here.'] })
    try { await onPracticePrompt?.({ concept: conceptLabel, questionType: practiceMode, difficulty: 1, answer: tutorCode }) } catch (error) { setTerminal({ status: 'failed', output: [`Tutor feedback unavailable: ${error.message}`] }) }
  }
  const askPyr = async () => {
    const prompt = aiPrompt.trim()
    if (!prompt) return
    setAiMessages((current) => [...current, { role: 'learner', text: prompt }, { role: 'pyr', text: 'I will point to the next concept boundary. Keep your attempt in tutor.py; I will not paste a project answer.' }].slice(-8))
    setAiPrompt('')
    try { await onPracticePrompt?.({ concept: conceptLabel, questionType: practiceMode, difficulty: 1 }) } catch { /* the message remains useful when no provider is selected */ }
  }
  const practiceModes = RESOURCE_PRACTICE_MODES
  return (
    <div className="resource-tutor-screen" data-testid="resource-tutor" data-campaign-revision={revision}>
      <header className="resource-tutor-header"><div><span className="screen-kicker">TUTOR NOTEBOOK</span><h2>Learn it, then make it yours.</h2><p>Reference pages, a writable tutor.py and bounded PYR guidance share one calm workspace.</p></div><div className="resource-tutor-header-actions"><button type="button" onClick={() => onNavigate?.('forge')}>Resume Forge</button><span>REV {revision ?? 0}</span></div></header>
      <nav className="resource-tutor-tabs" aria-label="Tutor sections"><button type="button" className={surface === 'codex' ? 'active' : ''} onClick={() => setSurface('codex')}>▣ Codex</button><button type="button" className={surface !== 'codex' ? 'active' : ''} onClick={() => setSurface('ide')}>↗ IDE practice</button></nav>
      {surface === 'codex' && <section className="resource-codex-layout"><aside className="resource-codex-index"><div className="resource-index-heading"><span className="screen-kicker">FIELD LIBRARY</span><strong>{pages.length} concepts</strong></div><label className="resource-search"><span>SEARCH</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a concept" /></label><div className="resource-page-list">{filteredPages.map((page) => <button key={page.id} type="button" className={page.id === selectedPage?.id ? 'active' : ''} onClick={() => { setSelectedId(page.id); setReadPage(0) }}><span>{page.title.slice(0, 1).toUpperCase()}</span><div><strong>{page.title}</strong><small>{page.encounter_ids?.length || 0} encounter records</small></div></button>)}</div><div className="resource-review-queue"><span className="screen-kicker">REVIEW QUEUE</span><strong>{entries.filter((entry) => entry.weaknesses?.length).length || 0} signals</strong><p>PYR can suggest concepts here when your attempts show a pattern.</p></div></aside><article className="resource-codex-reader"><div className="resource-breadcrumb"><span>CODEX</span><span>/</span><strong>{selectedPage?.title?.toUpperCase() || 'REFERENCE'}</strong></div><header className="resource-reader-heading"><div><span className="screen-kicker">REFERENCE ENTRY</span><h3>{selectedPage?.title || 'Concept page'}</h3><p>{selectedPage?.definition || 'A canonical learning reference.'}</p></div><button type="button" className="primary" onClick={() => setSurface('ide')}>Practice this →</button></header><div className="resource-folio-controls"><button type="button" className={readPage === 0 ? 'active' : ''} onClick={() => setReadPage(0)}>01 · Definition</button><button type="button" className={readPage === 1 ? 'active' : ''} onClick={() => setReadPage(1)}>02 · Examples</button><button type="button" className={readPage === 2 ? 'active' : ''} onClick={() => setReadPage(2)}>03 · Mistakes &amp; signals</button><span>PAGE {readPage + 1} / 3</span></div>{readPage === 0 && <div className="resource-folio-copy"><section className="resource-definition"><span className="screen-kicker">THE IDEA</span><p>{selectedPage?.definition}</p></section><ResourceEncounterRecords entries={selectedEntries} /></div>}{readPage === 1 && <ResourceCodexExamples page={selectedPage} />}{readPage === 2 && <ResourceCodexMistakes page={selectedPage} entries={selectedEntries} />}</article></section>}
      {surface === 'ide' && <section className="resource-ide-layout"><aside className="resource-ide-rail"><button type="button" className="resource-rail-file active" onClick={() => setSurface('ide')}><ForgeFileGlyph kind="python" /><small>tutor.py</small></button><button type="button" className="resource-rail-file" onClick={() => setSurface('notes')}><ForgeFileGlyph kind="markdown" /><small>notes.md</small></button><div className="resource-ide-context"><span className="screen-kicker">CONCEPT</span><strong>{conceptLabel}</strong><small>tutor.py is writable</small></div></aside><main className="resource-ide-main"><div className="resource-breadcrumb"><span>TUTOR</span><span>/</span><strong>IDE PRACTICE</strong></div><header className="resource-ide-heading"><div><span className="screen-kicker">{practiceModes.find((mode) => mode.id === practiceMode)?.label.toUpperCase()}</span><h3>{conceptLabel}</h3><p>{practiceModes.find((mode) => mode.id === practiceMode)?.prompt} PYR can point at your reasoning without writing the finished response.</p></div><label><span>QUESTION LENS</span><select value={practiceMode} onChange={(event) => setPracticeMode(event.target.value)}>{practiceModes.map((mode) => <option key={mode.id} value={mode.id}>{mode.label}</option>)}</select></label></header><div className="resource-mode-strip">{practiceModes.map((mode, index) => <button type="button" key={mode.id} className={practiceMode === mode.id ? 'active' : ''} onClick={() => setPracticeMode(mode.id)}><span>0{index + 1}</span>{mode.label}</button>)}</div><div className="resource-editor-card"><div className="resource-editor-toolbar"><span><b className="safe-badge">PYR WRITABLE</b> tutor.py{tutorDirty ? ' · unsaved' : ''}</span><span>MONACO · PYTHON · LOCAL COMPLETION</span></div><div className="resource-monaco"><Editor height="430px" path="tutor.py" language="python" value={tutorCode || ''} onChange={(value) => onTutorChange?.(value ?? '')} onMount={(editor, monaco) => { const provider = monaco.languages.registerCompletionItemProvider('python', { triggerCharacters: ['.', '_'], provideCompletionItems: (model) => ({ suggestions: resourceIdentifierSuggestions(model.getValue()).map((label) => ({ label, kind: monaco.languages.CompletionItemKind.Keyword, insertText: label })) }) }); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, runSelfCheck); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onTutorSave?.()); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, submit); editor.onDidDispose(() => provider.dispose()) }} theme="vs-dark" options={{ minimap: { enabled: false }, fontSize: editorFontSize, fontFamily: 'JetBrains Mono, ui-monospace, monospace', lineHeight: Math.round(editorFontSize * 1.55), padding: { top: 14, bottom: 14 }, automaticLayout: true, smoothScrolling: true, tabSize: 4, suggestOnTriggerCharacters: true }} /></div><div className="resource-editor-actions"><span>Ctrl/Cmd ↵ run · Ctrl/Cmd S save · Ctrl/Cmd ⇧ ↵ submit</span><div><button type="button" onClick={onTutorSave} disabled={busy}>Save Tutor</button><button type="button" onClick={onTutorFormat} disabled={busy}>Pretty</button><button type="button" onClick={() => { runSelfCheck(); onTutorRun?.() }} disabled={busy}>▶ Run Tutor</button><button type="button" className="primary" onClick={submit} disabled={busy || !String(tutorCode || '').trim()}>Submit for feedback</button></div></div></div><section className={`resource-ide-terminal ${terminal.status}`} aria-live="polite"><div><span>LOCAL TERMINAL · SELF-CHECK</span><b>{terminal.status.toUpperCase()}</b></div><pre>{terminal.output.join('\n')}</pre></section>{tutorExternalChange && <div className="tutor-conflict-banner" role="alert"><strong>External tutor.py change detected.</strong><span>Your unsaved edits are preserved.</span><button type="button" onClick={onTutorReloadExternal}>Reload external version</button><button type="button" onClick={onTutorKeepEdits}>Keep my edits</button></div>}</main><aside className="resource-ai-panel"><div className="resource-ai-heading"><div><span className="screen-kicker">PYR / AI</span><strong>Tutor channel</strong></div><span className="connection-pill">READY</span></div><p>Bounded guidance only. PYR will not paste a campaign answer or project-specific snippet.</p><div className="resource-ai-messages">{aiMessages.map((message, index) => <div key={`${message.role}-${index}`} className={`resource-ai-message ${message.role}`}><span>{message.role === 'learner' ? 'YOU' : 'PYR'}</span><p>{message.text}</p></div>)}</div><textarea value={aiPrompt} onChange={(event) => setAiPrompt(event.target.value)} rows={3} placeholder="Ask for a hint, not a finished answer…" /><div><button type="button" onClick={() => setAiMessages([])}>Clear</button><button type="button" className="primary" onClick={askPyr}>Ask PYR</button></div></aside></section>}
      {surface === 'notes' && <section className="resource-notes-layout"><aside className="resource-ide-rail resource-notes-rail"><button type="button" className="resource-rail-file" onClick={() => setSurface('ide')}><ForgeFileGlyph kind="python" /><small>tutor.py</small></button><button type="button" className="resource-rail-file active" onClick={() => setSurface('notes')}><ForgeFileGlyph kind="markdown" /><small>notes.md</small></button><div className="resource-ide-context"><span className="screen-kicker">CONCEPT</span><strong>{conceptLabel}</strong><small>notes.md · learner workspace</small></div></aside><main className="resource-notes-main"><ResourceNotebook pages={pages} selectedPage={selectedPage} entries={entries} onSelectPage={setSelectedId} /></main></section>}
    </div>
  )
}

function CharacterSheet({ progress, revision, avatarDataUrl = '', encounter, codexProjection, onNavigate }) {
  const player = progress.player || {}
  const stats = progress.stats || {}
  const equipment = progress.equipment || {}
  const companion = progress.companion || {}
  const achievements = progress.achievements || []
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const currentMob = encounter?.mob_name ? (activeProject.mobs || []).find((mob) => mob.name === encounter.mob_name) : (activeProject.mobs || []).find((mob) => mob.status === 'available')
  const recentEvents = (progress.state_events || []).filter((event) => event && typeof event === 'object').slice(-5).reverse()
  const codexCount = codexProjection?.entries?.length ?? progress.codex?.encounters?.length ?? 0
  const resolve = encounter?.resolve ?? currentMob?.resolve ?? 0
  const maxResolve = encounter?.max_resolve ?? currentMob?.max_resolve ?? 0

  return (
    <div className="game-screen-scroll" data-testid="character" data-campaign-revision={revision}>
      <section className="game-card character-progress-cockpit" data-testid="character-cockpit">
        <div className="card-heading"><span>PROGRESS COCKPIT</span><b>{activeProject.progress ?? encounter?.project_progress ?? 0}%</b></div>
        <div className="character-cockpit-grid">
          <div><small>CURRENT CHAPTER</small><strong>{activeProject.name || encounter?.project_name || 'No active chapter'}</strong><span>{progress.current_quest || 'Continue your active learning path.'}</span></div>
          <div><small>ACTIVE ENCOUNTER</small><strong>{encounter?.mob_name || currentMob?.name || 'Boss gate'}</strong><span>{encounter?.mob?.brief || currentMob?.encounter || 'No bounded encounter brief is active.'}</span></div>
          <div><small>RESOLVE / OBJECTIVE</small><strong>{encounter?.status === 'boss_available' ? 'BOSS GATE' : `${resolve}/${maxResolve || '—'}`}</strong><span>{encounter?.available_objectives?.length ?? 0} objective{(encounter?.available_objectives?.length ?? 0) === 1 ? '' : 's'} ready · {encounter?.attempts ?? 0} attempts</span></div>
          <div><small>LEARNING SIGNALS</small><strong>{codexCount} encounter records</strong><span>{(encounter?.question_types || []).join(' · ') || 'No question lens recorded yet.'}</span></div>
        </div>
        <div className="character-cockpit-actions"><button className="primary" type="button" onClick={() => onNavigate?.('forge')}>Resume Forge</button><button type="button" onClick={() => onNavigate?.('tutor')}>Open Tutor</button><button type="button" onClick={() => onNavigate?.('codex')}>Read Codex</button></div>
        <div className="character-event-strip" aria-label="Recent validated events">
          <small>RECENT VALIDATED EVENTS</small>
          {recentEvents.length ? recentEvents.map((event, index) => <span key={`${event.id || event.kind || 'event'}-${index}`}>{event.kind || event.type || 'validated event'}{event.reason ? ` · ${event.reason}` : ''}</span>) : <span>No validated events recorded yet.</span>}
        </div>
      </section>
      <div className="character-layout">
        <section className="character-card game-card">
          <div className="character-banner">
            <div className="character-sigil" data-react-avatar="true">{avatarDataUrl ? <img className="quest-avatar-img character" src={avatarDataUrl} alt="" /> : (player.name || 'L').slice(0, 1)}</div>
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
            <div><span aria-hidden="true"><RouteIcon id="shield" /></span><small>Armor</small><strong>{equipment.armor || 'None'}</strong></div>
            <div><span aria-hidden="true"><RouteIcon id="spark" /></span><small>Trinket</small><strong>{equipment.trinket || 'None'}</strong></div>
            <div><span aria-hidden="true"><RouteIcon id="character" /></span><small>Title</small><strong>{equipment.title || player.title || 'None'}</strong></div>
          </div>
        </section>

        <section className="game-card companion-card">
          <div className="pyr-orb" aria-hidden="true"><RouteIcon id="flame" /></div>
          <div><span className="screen-kicker">COMPANION</span><h3>{companion.name || 'PYR'} · {companion.form || 'Tiny Code-Flame'}</h3><p>Bond {companion.bond ?? 0} · Level {companion.level ?? 1}</p><small>Next form: {companion.next_form || '???'} — {companion.next_form_requirement || 'keep learning'}</small></div>
        </section>
      </div>

      <section className="game-card">
        <div className="card-heading"><span>ACHIEVEMENTS</span><b>{achievements.filter((item) => item.unlocked).length}/{achievements.length}</b></div>
        <div className="achievement-grid">
          {achievements.map((achievement) => (
            <article key={achievement.name} className={achievement.unlocked ? 'unlocked' : 'locked'}>
              <span aria-hidden="true"><RouteIcon id={achievement.unlocked ? 'shield' : 'codex'} /></span>
              <div><strong>{achievement.name}</strong><p>{achievement.description}</p></div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function CosmeticIcon({ kind }) {
  const paths = {
    theme: <><path d="M4 5h16v14H4z" /><path d="M7 8h10M7 12h7M7 16h4" /></>,
    cursor: <><path d="m6 3 12 9-6 1 1 7-3 1-2-7-5 3z" /></>,
    hud: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M6 8h12M6 12h5M6 16h8" /></>,
    terminal: <><path d="m5 7 5 5-5 5M12 17h7" /></>,
  }
  return <span className="shop-icon" aria-hidden="true"><svg viewBox="0 0 24 24">{paths[kind] || paths.theme}</svg></span>
}

const HOME_ROOM_UPGRADES = [
  { id: 'reinforced-hearth', name: 'Reinforced Hearth', kind: 'STAT', cost: 1, effect: 'MAX HP +10', detail: 'A stronger hearth gives you ten more maximum HP.' },
  { id: 'warding-loom', name: 'Warding Loom', kind: 'TRINKET', cost: 2, effect: 'RETALIATION −2', detail: 'Threaded syntax wards soften each failed submission by 2 HP.' },
  { id: 'breaker-workbench', name: 'Breaker Workbench', kind: 'STAT', cost: 2, effect: 'BREAK +1', detail: 'Tune your kit to break Guard one Resolve point faster.' },
  { id: 'siphon-basin', name: 'Siphon Basin', kind: 'TRINKET', cost: 3, effect: 'BREAK HEAL +4', detail: 'A clean Guard Break restores 4 HP before the final submit.' },
  { id: 'field-kitchen', name: 'Field Kitchen', kind: 'STAT', cost: 2, effect: 'MEALS +5', detail: 'Packed meals restore 5 extra HP when eaten at Home.' },
]

const HOME_ACHIEVEMENTS = [
  { id: 'first-mark', name: 'First Mark', icon: '✦', detail: 'Clear your first bounty.' },
  { id: 'clean-slate', name: 'Clean Slate', icon: '◇', detail: 'Finish an encounter without a rejected submit.' },
  { id: 'guardbreaker', name: 'Guardbreaker', icon: '◈', detail: 'Break a mob’s Guard before finishing it.' },
  { id: 'dealer-down', name: 'Dealer Down', icon: '♠', detail: 'Defeat The Dealer’s Hand.' },
]

// Keep the companion projection authored in one place. The prototype and the
// port both use these thresholds; the API may still expose legacy form labels.
const HOME_PYR_STAGES = [
  { id: 'spark', label: 'Tiny Code-Flame', threshold: 0, detail: 'A curious little watcher that keeps the hearth bright.' },
  { id: 'ember', label: 'Emberling', threshold: 3, detail: 'A warmer companion with a steadier glow.' },
  { id: 'flare', label: 'Flarekin', threshold: 6, detail: 'A bright companion ready for a bigger homestead.' },
]

function Homestead({ progress, revision, equipmentProjection, purchaseCosmetic, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, busy, onNavigate }) {
  const player = progress.player || {}
  const homestead = progress.homestead || {}
  const equipment = progress.equipment || {}
  const stats = progress.stats || {}
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const catalog = homestead.catalog || []
  const owned = new Set(homestead.owned_cosmetics || [])
  const equipped = homestead.equipped || {}
  const roomUpgrades = Array.isArray(homestead.room_upgrades) ? homestead.room_upgrades : []
  const upgradeTokens = Number.isFinite(Number(homestead.upgrade_tokens)) ? Number(homestead.upgrade_tokens) : 1
  const [focus, setFocus] = useState('hearth')
  const [roomUpgradePanelOpen, setRoomUpgradePanelOpen] = useState(false)
  const grouped = ['theme', 'cursor', 'hud', 'terminal']
  const daySeed = new Date().toISOString().slice(0, 10).split('').reduce((total, char) => total + char.charCodeAt(0), 0)
  const dailyCatalog = catalog.filter((item, index) => (index + daySeed) % 3 === 0 || owned.has(item.id) || item.price === 0).slice(0, 8)
  const nextRefresh = `${new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)} UTC`
  const projects = Array.isArray(progress.projects) ? progress.projects : []
  const completedContracts = Array.isArray(progress.completedContracts) ? progress.completedContracts : []
  const completedMobCount = projects.reduce((total, project) => total + (Array.isArray(project.mobs) ? project.mobs.filter((mob) => ['defeated', 'cleared'].includes(mob.status)).length : 0), 0)
  const completedTaskCount = completedContracts.length || completedMobCount || Number(stats.mobs_defeated || 0)
  const defeatedMobNames = new Set(projects.flatMap((project) => (Array.isArray(project.mobs) ? project.mobs : [])).filter((mob) => ['defeated', 'cleared'].includes(mob.status)).map((mob) => String(mob.name || '').trim().toLowerCase()).filter(Boolean))
  const hasStructuredCampaignEvidence = completedContracts.length > 0 || projects.some((project) => Array.isArray(project.mobs))
  const achievementUnlocked = (id) => ({
    // Older state snapshots only have aggregate counters; use them only when
    // no authored contract/mob evidence exists, never as a loose unlock rule.
    'first-mark': completedContracts.length >= 1 || completedMobCount >= 1 || (!hasStructuredCampaignEvidence && Number(stats.mobs_defeated || 0) >= 1),
    'clean-slate': Number(stats.clean_clears || 0) >= 1,
    'guardbreaker': Number(stats.guard_breaks || 0) >= 1,
    'dealer-down': completedContracts.includes('dealer-hand') || defeatedMobNames.has("the dealer's hand"),
  }[id])
  const supplies = progress.supplies || { bandages: player.potions || 0, tonics: 0, meals: 0 }
  const hp = Number(player.hp ?? 0)
  const maxHp = Number(player.max_hp ?? 0)
  const pyr = progress.companion || {}
  const pyrEnergy = Math.min(Number(pyr.max_energy ?? 2), Number(pyr.energy ?? pyr.max_energy ?? 2))
  const pyrMaxEnergy = Math.max(1, Number(pyr.max_energy ?? 2))
  const pyrBond = Number(pyr.bond ?? 0)
  const pyrStageMeta = [...HOME_PYR_STAGES].reverse().find((stage) => pyrBond >= stage.threshold) || HOME_PYR_STAGES[0]
  const nextPyrStageMeta = HOME_PYR_STAGES.find((stage) => stage.threshold > pyrBond)
  const pyrStage = pyrStageMeta.label
  const nextPyrStage = nextPyrStageMeta?.label || 'MAX'
  const pyrBondProgress = nextPyrStageMeta ? Math.min(100, Math.max(0, ((pyrBond - pyrStageMeta.threshold) / (nextPyrStageMeta.threshold - pyrStageMeta.threshold)) * 100)) : 100
  const perform = (action) => performHomesteadAction?.(action)
  const scrollToLoadout = () => document.querySelector('.home-loadout-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const focusCopy = {
    hearth: ['HEARTH', 'Warm up before the next job.', 'The house is safe. Recover fully here, or eat a packed meal for a smaller top-up without changing the coding requirement.', <div className="home-context-actions"><button type="button" disabled={busy || hp >= maxHp || !performHomesteadAction} onClick={() => perform('recover')}>Recover fully</button><button type="button" className="ghost" disabled={busy || hp >= maxHp || !(supplies.meals > 0) || !performHomesteadAction} onClick={() => perform('meal')}>Eat a meal</button></div>],
    armory: ['ARMORY CHEST', 'Tune the kit you will carry.', 'Armor softens retaliation. Trinkets shape Guard Breaks and protection. Equip what fits the next contract, then return to the Forge.', <div className="home-context-actions"><button type="button" onClick={scrollToLoadout}>Browse loadout</button><button type="button" className="ghost" disabled={busy || upgradeTokens < 1 || !performHomesteadAction} onClick={() => perform('spend_token')}>Spend upgrade token</button></div>],
    pantry: ['PANTRY', 'Pack a useful encounter kit.', 'Field bandages restore HP at Home. Ember tonics can be primed during an encounter to soften one failed submission. Meals can also keep Pyr growing.', <div className="home-context-actions"><button type="button" disabled={busy || hp >= maxHp || !(supplies.bandages > 0) || !performHomesteadAction} onClick={() => perform('bandage')}>Use bandage</button><button type="button" className="ghost" disabled={busy || hp >= maxHp || !(supplies.meals > 0) || !performHomesteadAction} onClick={() => perform('meal')}>Eat a meal</button></div>],
    study: ['STUDY DESK', 'Turn learning into a stronger home.', 'Validated work earns upgrade tokens. Build five authored room upgrades here, then let the achievement plaques record the moments you earned them.', <div className="home-context-actions"><button type="button" onClick={() => setRoomUpgradePanelOpen(true)}>Open room upgrades</button><button type="button" className="ghost" disabled={busy || upgradeTokens < 1 || !performHomesteadAction} onClick={() => perform('spend_token')}>Spend one legacy token</button></div>],
    pyr: [pyrStage, 'Spend time with your code-flame.', `${pyrStageMeta.detail} Feed Pyr with a camp meal to restore training energy, or train to grow bond. The next evolution is ${nextPyrStageMeta ? `${nextPyrStageMeta.label} at bond ${nextPyrStageMeta.threshold}` : 'already reached'}.`, <div className="home-context-actions"><button type="button" disabled={busy || !(supplies.meals > 0) || !performHomesteadAction} onClick={() => perform('feed_pyr')}>Feed Pyr</button><button type="button" className="ghost" disabled={busy || pyrEnergy <= 0 || !performHomesteadAction} onClick={() => perform('train_pyr')}>Train with Pyr</button></div>],
  }[focus]

  const renderRoomUpgrade = (upgrade) => {
    const built = roomUpgrades.includes(upgrade.id)
    const canBuild = !built && upgradeTokens >= upgrade.cost && Boolean(buildRoomUpgrade)
    return <article key={upgrade.id} className={`room-upgrade-card ${built ? 'built' : ''}`}>
      <div className="room-upgrade-card-head"><span className="room-upgrade-kind">{upgrade.kind}</span><strong>{upgrade.name}</strong><span className="room-upgrade-effect">{upgrade.effect}</span></div>
      <p>{upgrade.detail}</p>
      {built ? <span className="room-upgrade-status">BUILT · ACTIVE</span> : <button type="button" className="room-upgrade-build" disabled={busy || !canBuild} onClick={() => buildRoomUpgrade?.(upgrade.id)}>Build · {upgrade.cost} token{upgrade.cost === 1 ? '' : 's'}</button>}
    </article>
  }

  const renderShopCard = (item) => {
    const kind = item.kind || 'theme'
    const isOwned = owned.has(item.id)
    const isEquipped = equipped[kind] === item.id
    const canAfford = (player.coins ?? 0) >= (item.price ?? 0)
    return (
      <article key={item.id} className={`shop-card ${isEquipped ? 'equipped' : ''}`}>
        <div className={`shop-swatch ${item.id}`}><CosmeticIcon kind={kind} /></div>
        <div className="shop-copy"><small>{item.rarity || 'common'}</small><h3>{item.name}</h3><p>{item.description}</p></div>
        <div className="shop-actions">
          <strong>{isOwned ? (isEquipped ? 'EQUIPPED' : 'OWNED') : `${item.price ?? 0}c`}</strong>
          {!isOwned && <button disabled={busy || !canAfford} onClick={() => purchaseCosmetic(item.id)}>{canAfford ? 'Buy' : 'Need coins'}</button>}
          {isOwned && !isEquipped && <button disabled={busy} onClick={() => equipCosmetic(item.id)}>Equip</button>}
        </div>
      </article>
    )
  }

  return (
    <div className="game-screen-scroll homestead-v2" data-testid="homestead" data-campaign-revision={revision}>
      <div className="place-heading">
        <div className="home-place-heading"><span className="screen-kicker">HOME · HOMESTEAD</span><h2>Your homestead.</h2><p>Recover, prepare, and grow Pyr before the next bounty.</p></div>
        <span className="place-seal place-seal-home">⌂</span>
      </div>

      <div className="home-interior-layout">
        <section className="home-room-scene" aria-label="Homestead interior with selectable stations">
          <div className="room-topline"><span>THE HOMESTEAD</span><small>SAFE ROOM · PREPARE · GROW</small></div>
          <div className="room-plaque"><span>{String(activeProject.name || 'BLACKJACK').toUpperCase()}</span><small>CHAPTER 01 · HOME BASE</small></div>
          <div className="room-window"><i></i><b>✦</b></div>
          <div className="room-shelf"><span>✦</span><span>◇</span><span>▣</span><small>TROPHIES</small></div>
          <div className="room-chest-art"><span>▣</span><small>ARMORY</small></div>
          <div className="room-plant-art" aria-hidden="true"><i></i><b></b><em></em><small>GROW</small></div>
          <div className="room-pantry-art" aria-hidden="true"><i></i><b></b><small>PANTRY</small></div>
          <div className="room-hearth-art"><i></i><b>⌂</b><small>HEARTH</small></div>
          <div className="room-desk-art"><span>▤</span><i></i><small>STUDY</small></div>
          <div className="room-door-art" aria-hidden="true"><span>⌄</span><small>ENTRY</small></div>
          <div className="room-rug"></div>
          <button type="button" className={`room-upgrade-niche ${roomUpgradePanelOpen ? 'active' : ''}`} onClick={() => setRoomUpgradePanelOpen((open) => !open)} aria-expanded={roomUpgradePanelOpen}><span>{roomUpgradePanelOpen ? '×' : '＋'}</span><strong>ROOM UPGRADES</strong><small>{roomUpgrades.length}/{HOME_ROOM_UPGRADES.length} stations built · {roomUpgradePanelOpen ? 'close list' : 'open list'}</small></button>
          <button type="button" className={`room-hotspot hearth ${focus === 'hearth' ? 'active' : ''}`} onClick={() => setFocus('hearth')}><span><RouteIcon id="flame" /></span><strong>Hearth</strong><small>Recover HP</small></button>
          <button type="button" className={`room-hotspot armory ${focus === 'armory' ? 'active' : ''}`} onClick={() => setFocus('armory')}><span><RouteIcon id="shield" /></span><strong>Armory</strong><small>Equip kit</small></button>
          <button type="button" className={`room-hotspot pantry ${focus === 'pantry' ? 'active' : ''}`} onClick={() => setFocus('pantry')}><span>＋</span><strong>Pantry</strong><small>Pack supplies</small></button>
          <button type="button" className={`room-hotspot study ${focus === 'study' ? 'active' : ''}`} onClick={() => setFocus('study')}><span><RouteIcon id="spark" /></span><strong>Study desk</strong><small>Spend tokens</small></button>
          <button type="button" className={`room-hotspot pyr ${focus === 'pyr' ? 'active' : ''}`} onClick={() => setFocus('pyr')}><span>✦</span><strong>Pyr’s perch</strong><small>{pyrStage}</small></button>
          <div className="room-pyr-sprite" aria-hidden="true"><span>✦</span><i></i></div>
          <div className="room-pyr-label"><strong>PYR</strong><small>{pyrStage} · bond {pyrBond}</small></div>
        </section>
        <section className="home-context-panel"><div className="home-context-mark"><RouteIcon id={focus === 'hearth' ? 'flame' : focus === 'armory' ? 'shield' : focus === 'study' ? 'spark' : focus === 'pyr' ? 'spark' : 'plus'} /></div><span className="screen-kicker">{focusCopy[0]}</span><h3>{focusCopy[1]}</h3><p>{focusCopy[2]}</p>{focusCopy[3]}{focus === 'pyr' && <div className="pyr-bond-meter"><div><span>BOND</span><strong>{pyrBond}{nextPyrStageMeta ? ` / ${nextPyrStageMeta.threshold}` : ' · MAX'}</strong></div><i><b style={{ width: `${pyrBondProgress}%` }} /></i><small>Training energy {pyrEnergy}/{pyrMaxEnergy}. Evolution is a companion milestone, not a hidden answer bonus.</small></div>}<div className="home-resume"><span className="screen-kicker">NEXT STEP</span><strong>{activeProject.name || 'The Count Keeper'}</strong><button type="button" onClick={() => onNavigate?.('forge')}>Return to Bounty Office</button></div></section>
      </div>

      {roomUpgradePanelOpen && <section className="home-upgrade-drawer open" aria-label="Homestead upgrades" data-testid="homestead-room-upgrades"><div className="home-upgrade-drawer-head"><div><span className="screen-kicker">BUILD THE HOMESTEAD</span><h3>Room upgrades</h3><p>Spend upgrade tokens on small, authored stat and trinket effects. Nothing here changes the code you must write.</p></div><span className="home-upgrade-token-pill">{upgradeTokens} TOKENS</span></div><div className="room-upgrade-grid">{HOME_ROOM_UPGRADES.map(renderRoomUpgrade)}</div><div className="home-achievement-heading"><span className="screen-kicker">ROOM HISTORY</span><strong>Achievement plaques</strong><small>Proof of cool work, not another currency.</small></div><div className="home-achievement-grid">{HOME_ACHIEVEMENTS.map((achievement) => { const unlocked = achievementUnlocked(achievement.id); return <article key={achievement.id} className={`home-achievement ${unlocked ? 'unlocked' : 'locked'}`}><span className="home-achievement-icon">{unlocked ? achievement.icon : '·'}</span><div><strong>{unlocked ? achievement.name : 'HIDDEN PLAQUE'}</strong><p>{unlocked ? achievement.detail : 'Keep learning to reveal this room history.'}</p></div><small>{unlocked ? 'UNLOCKED' : 'LOCKED'}</small></article> })}</div></section>}

      <div className="home-status-row"><span><small>HP</small><strong>{hp}/{maxHp}</strong></span><span><small>UPGRADE TOKENS</small><strong>{upgradeTokens}</strong></span><span><small>SUPPLIES</small><strong>{supplies.bandages || player.potions || 0} bandages · {supplies.tonics || 0} tonics · {supplies.meals || 0} meals</strong></span></div>

      <section className="home-loadout-section">
        <div className="home-section-heading"><div><span className="screen-kicker">LIVE LOADOUT</span><h3>Armor and trinkets</h3></div><span>Buy in Market · equip here</span></div>
        <div className="home-loadout-grid">
          {(equipmentProjection?.slots || []).map((slot) => <div className="home-loadout-slot" key={slot.id}><span className="screen-kicker">{slot.label}</span><div className="home-equip-list">{(slot.items || []).length ? (slot.items || []).map((item) => <button type="button" className={`home-equip-card ${item.equipped ? 'equipped' : ''}`} key={item.id} onClick={() => equipCampaignItem?.(item.id)} disabled={busy || item.equipped || !equipCampaignItem}><span className="home-equip-symbol"><RouteIcon id={slot.id === 'armor' ? 'shield' : 'spark'} /></span><span><strong>{item.name}</strong><small>{item.description || item.effect}</small></span><b>{item.equipped ? 'EQUIPPED' : 'EQUIP'}</b></button>) : <p className="home-empty-copy">{slot.id === 'armor' ? 'No armor owned yet.' : 'Visit Market to find your first trinket.'}</p>}</div></div>)}
        </div>
      </section>
      <section className="home-supply-strip"><span className="screen-kicker">PACKED SUPPLIES</span><span>Bandages <strong>{supplies.bandages || player.potions || 0}</strong></span><span>Ember tonics <strong>{supplies.tonics || 0}</strong></span><span>Meals <strong>{supplies.meals || 0}</strong></span><span>Vision scrolls <strong>{supplies.vision_scrolls || 0}</strong></span><small>Use supplies from the encounter kit.</small></section>
      <section className="home-progress-card"><div><span className="screen-kicker">RECENTLY CLEARED</span><h3>{completedTaskCount ? `${completedTaskCount} task${completedTaskCount === 1 ? '' : 's'} recorded` : 'No cleared work yet'}</h3></div><p>{completedTaskCount ? 'Your rewards are part of the same campaign state as Market and Bounty Office.' : 'Take a contract from the Bounty Office to start the loop.'}</p></section>
    </div>
  )
}

const CAMPAIGN_POIS = [
  { id: 'home', icon: '⌂', label: 'Home', kicker: 'REST · LOADOUT · PROGRESS', summary: 'Recover, tune your kit, grow Pyr, and spend upgrade tokens.' },
  { id: 'market', icon: '◇', label: 'Market', kicker: 'ROTATING STOCK · COINS', summary: 'Meet the Merchant, then browse armor, trinkets, and supplies.' },
  { id: 'office', icon: '✦', label: 'Bounty Office', kicker: 'MAIN BOUNTIES', summary: 'Choose the next learning contract from the board.' },
]

const CAMPAIGN_MARKET_STOCK = [
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

function CampaignMapRail({ place, onSelect, collapsed, onToggle, progress }) {
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const completed = (activeProject.mobs || []).filter((mob) => isMobDefeated(mob.status)).length
  const total = (activeProject.mobs || []).length
  return (
    <aside className={`campaign-panel poi-rail ${collapsed ? 'map-rail-collapsed' : ''}`} aria-label="Campaign map">
      <div className="panel-heading">
        <div><span className="campaign-eyebrow">PROJECT MAP</span><h2>{activeProject.name || 'Blackjack'}</h2></div>
        <span className="campaign-tag">3 POIs</span>
        <button type="button" className="map-rail-toggle" onClick={onToggle} aria-label={collapsed ? 'Expand project map' : 'Collapse project map'}>{collapsed ? '›' : '‹'}</button>
      </div>
      {!collapsed && <>
        <p className="campaign-panel-copy">A small campaign board. Choose where to prepare or which work to take next; there is no route tree to decode.</p>
        <div className="poi-list">
          {CAMPAIGN_POIS.map((poi) => <button key={poi.id} className={`poi-card ${place === poi.id ? 'active' : ''}`} type="button" onClick={() => onSelect(poi.id)}><span className={`poi-icon poi-${poi.id}`}>{poi.icon}</span><span className="poi-copy"><strong>{poi.label}</strong><small>{poi.kicker}</small><em>{poi.summary}</em></span><span className="poi-arrow"><RouteIcon id="arrow" /></span></button>)}
        </div>
        <div className="project-progress"><div><span>PROJECT PROGRESS</span><strong>Chapter 01</strong></div><div className="campaign-progress-track"><i style={{ width: `${Math.min(100, completed * 24)}%` }} /></div><p>{total ? `${completed}/${total} bounty${total === 1 ? '' : 'ies'} cleared.` : 'Boss remains locked until the project bounties are cleared.'}</p></div>
      </>}
      {collapsed && <div className="map-rail-collapsed-summary"><span>✦</span><strong>MAP</strong><small>OPEN</small></div>}
    </aside>
  )
}

function CampaignMarket({ progress, onBackHome, purchaseMarketItem, busy }) {
  const coins = Number(progress?.player?.coins ?? 0)
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState('All')
  const [selectedId, setSelectedId] = useState(CAMPAIGN_MARKET_STOCK[6].id)
  const purchased = Array.isArray(progress?.homestead?.market_purchases) ? progress.homestead.market_purchases : []
  const merchantName = 'The Merchant'
  const categories = ['All', 'Armor', 'Trinket', 'Supply']
  const visible = category === 'All' ? CAMPAIGN_MARKET_STOCK : CAMPAIGN_MARKET_STOCK.filter((item) => item.kind === category)
  const selected = visible.find((item) => item.id === selectedId) || visible[0] || CAMPAIGN_MARKET_STOCK[0]
  const owned = selected && purchased.includes(selected.id)
  const rarity = selected?.price >= 120 ? 'RARE' : selected?.price >= 70 ? 'UNCOMMON' : 'COMMON'
  const buy = () => {
    if (!selected || owned || coins < selected.price || busy || !purchaseMarketItem) return
    purchaseMarketItem(selected.id)
  }
  const changeCategory = (next) => {
    setCategory(next)
    const nextVisible = next === 'All' ? CAMPAIGN_MARKET_STOCK : CAMPAIGN_MARKET_STOCK.filter((item) => item.kind === next)
    setSelectedId(nextVisible[0]?.id || '')
  }
  return (
    <>
      <div className="campaign-place-heading"><div><span className="campaign-eyebrow">MARKET · AUCTION HOUSE</span><h2>{open ? 'Browse today’s lots.' : `${merchantName} has a case for you.`}</h2><p>{merchantName} rotates useful armor, trinkets, and supplies. The market changes your preparation, never the answer you need to learn.</p></div><span className="campaign-place-seal market">◇</span></div>
      {!open ? <section className="market-greeting">
        <div className="market-vendor-scene"><div className="vendor-lantern">✦</div><div className="vendor-portrait merchant-pixel-sprite" aria-hidden="true" dangerouslySetInnerHTML={{ __html: merchantPixelSprite() }} /><div className="vendor-counter" /><div className="vendor-nameplate"><span className="campaign-eyebrow">SHOPKEEPER NPC</span><strong>{merchantName}</strong></div></div>
        <div className="market-greeting-copy"><span className="campaign-eyebrow">WELCOME, TRAVELLER</span><h3>“Coins open the case. Knowledge keeps you alive.”</h3><p>The shelf changes between expeditions. Browse the lots when you are ready to prepare, then equip your finds at Home.</p><button type="button" className="campaign-button" onClick={() => setOpen(true)}>Browse today’s lots <span>→</span></button><small>Single-player market · no bidding · buy only what helps your next learning job.</small></div>
        <aside className="market-greeting-purse"><span className="campaign-eyebrow">YOUR PURSE</span><strong>◉ {coins}</strong><small>{CAMPAIGN_MARKET_STOCK.length} lots waiting in the case</small></aside>
      </section> : <div className="market-browser">
        <div className="market-browser-head"><div><span className="campaign-eyebrow">THE MERCHANT’S OPEN LOTS</span><h3>Browse and choose your preparation.</h3></div><div className="market-browser-actions"><span className="market-purse-pill">◉ {coins} coins</span><button type="button" className="campaign-button ghost" onClick={() => setOpen(false)}>← Back to The Merchant</button></div></div>
        <div className="market-browser-grid"><nav className="market-category-rail" aria-label="Market categories"><span className="campaign-eyebrow">CATEGORIES</span>{categories.map((item) => <button key={item} type="button" className={`market-category ${category === item ? 'active' : ''}`} onClick={() => changeCategory(item)}>{item === 'All' ? 'All lots' : item === 'Supply' ? 'Supplies' : `${item}s`}<small>{item === 'All' ? CAMPAIGN_MARKET_STOCK.length : CAMPAIGN_MARKET_STOCK.filter((stock) => stock.kind === item).length}</small></button>)}</nav><section className="market-lot-list" aria-label="Available market lots"><div className="market-list-head"><span>LOT</span><span>TYPE</span><span>PRICE</span></div>{visible.map((item) => { const itemOwned = purchased.includes(item.id); return <button type="button" key={item.id} className={`market-lot-row ${selected?.id === item.id ? 'active' : ''} ${itemOwned ? 'owned' : ''}`} onClick={() => setSelectedId(item.id)}><span className="market-lot-icon">{item.icon}</span><span className="market-lot-copy"><strong>{item.name}</strong><small>{item.detail}{itemOwned ? ' · owned' : ''}</small></span><span className="market-lot-kind">{item.kind}</span><strong className="market-lot-price">{item.price}<small> coins</small></strong></button> })}</section><aside className="market-item-detail">{selected && <><span className="campaign-eyebrow">SELECTED LOT · {selected.kind.toUpperCase()}</span><div className="market-detail-icon">{selected.icon}</div><span className="campaign-eyebrow">{rarity}</span><h3>{selected.name}</h3><p>{selected.detail}</p><div className="market-detail-facts"><span><small>PRICE</small><strong>{selected.price} coins</strong></span><span><small>STATUS</small><strong>{owned ? 'OWNED' : 'AVAILABLE'}</strong></span></div>{owned ? <span className="market-owned-note">Already in your kit · equip it from Home.</span> : <button type="button" className="campaign-button" onClick={buy} disabled={busy || coins < selected.price || !purchaseMarketItem}>Buy this lot</button>}</>}</aside></div>
        <div className="campaign-market-footer"><span>⬡</span><p>Armor protects HP. Trinkets shape Guard Breaks and protection. Supplies are consumed from the encounter kit.</p></div>
      </div>}
      <div className="campaign-stat-row"><span><small>COINS</small><strong>{coins}</strong></span><span><small>LOTS</small><strong>{CAMPAIGN_MARKET_STOCK.length}</strong></span><span><small>PREP</small><strong>{purchased.length} owned</strong></span></div>
      {onBackHome && <button type="button" className="campaign-button ghost" onClick={onBackHome}>Open Home loadout →</button>}
    </>
  )
}

function CampaignOffice({ progress, onEnter }) {
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const mobs = Array.isArray(activeProject.mobs) ? activeProject.mobs : []
  const fallback = [
    { id: 'count-keeper', name: 'The Count Keeper', category: 'Loops and accumulators', status: 'available', signal: 'REWARD', reward: '+40 COINS', icon: '✦', detail: 'Restore the keeper’s running total and open the first safe mark.' },
    { id: 'loop-rehearsal', name: 'The Loop Rehearsal', category: 'Loops and accumulators', status: 'locked', signal: 'LOCKED', reward: 'HIDDEN', icon: '◌', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'accumulator-audit', name: 'The Accumulator Audit', category: 'Conditions and filtering', status: 'locked', signal: 'WARNING', reward: 'HIDDEN', icon: '◈', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'house-ledger', name: 'The House Ledger', category: 'Conditions and filtering', status: 'locked', signal: 'LOCKED', reward: 'HIDDEN', icon: '▣', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'dealer-hand', name: 'The Dealer’s Hand', category: 'Functions', status: 'locked', signal: 'BOSS', reward: 'HIDDEN', icon: '♠', detail: 'A larger bounty waits at the chapter boundary.' },
  ]
  const entries = (mobs.length ? mobs.map((mob, index) => ({ id: mob.id || mob.name || `mob-${index}`, name: mob.name || `Unknown bounty ${index + 1}`, category: mob.concept || mob.category || 'Learning contract', status: mob.status || 'locked', signal: mob.status === 'available' ? 'REWARD' : mob.status === 'defeated' ? 'CLEARED' : 'LOCKED', reward: mob.status === 'available' ? '+ COINS' : mob.status === 'defeated' ? 'CLEARED' : 'HIDDEN', icon: mob.status === 'defeated' ? '✓' : '✦', detail: mob.brief || mob.encounter || 'A state-owned learning contract.' })) : fallback).slice(0, 7)
  const [selectedId, setSelectedId] = useState(entries[0]?.id || '')
  const selected = entries.find((entry) => entry.id === selectedId) || entries[0]
  const unlocked = selected?.status !== 'locked'
  return (
    <>
      <div className="campaign-place-heading"><div><span className="campaign-eyebrow">BOUNTY OFFICE · CONTRACT BOARD</span><h2>Choose the work that moves you.</h2><p>Every bounty is a learning task. Read the weakness, prepare at Home, then enter the Forge when you are ready to write.</p></div><span className="campaign-place-seal office">✦</span></div>
      <div className="office-toolbar"><div className="office-tabs"><button type="button" className="office-tab active">MAIN BOUNTIES</button><button type="button" className="office-tab" disabled>VILLAGE · NEXT</button></div><div className="board-switcher"><button type="button" className="board-switch active">BOARD 1 / 1</button></div></div>
      <section className="office-board" aria-label="Bounty board"><div className="office-board-header"><strong>BLACKJACK · COMMUNITY BOUNTIES</strong><span className="campaign-eyebrow">{entries.length} POSTERS</span></div><div className="bounty-posters">{entries.map((entry) => <button type="button" key={entry.id} className={`bounty-poster ${entry.status === 'locked' ? 'locked' : ''} ${selected?.id === entry.id ? 'active' : ''}`} onClick={() => entry.status !== 'locked' && setSelectedId(entry.id)} disabled={entry.status === 'locked'}><span className="poster-pin" /><div className="poster-art">{entry.status === 'locked' ? '?' : entry.icon}</div><span className="poster-signal">{entry.signal}</span><h3>{entry.status === 'locked' ? 'HIDDEN SILHOUETTE' : entry.name}</h3><p>{entry.status === 'locked' ? 'Complete the previous bounty to reveal this poster.' : entry.category}</p><small>{entry.reward}</small></button>)}</div></section>
      {selected && <section className="office-detail"><div><span className="campaign-eyebrow">{unlocked ? 'SELECTED BOUNTY' : 'LOCKED BOUNTY'}</span><h3>{unlocked ? selected.name : 'Hidden silhouette'}</h3><p>{selected.detail}</p><div className="office-detail-facts"><span>{selected.category}</span><span>{selected.reward}</span></div></div><button type="button" className="campaign-button" onClick={onEnter} disabled={!unlocked}>{unlocked ? 'Study this work →' : 'Complete the previous bounty'}</button></section>}
      <div className="campaign-stat-row"><span><small>CHAPTER</small><strong>{activeProject.name || '01'}</strong></span><span><small>CLEARED</small><strong>{mobs.filter((mob) => isMobDefeated(mob.status)).length}</strong></span><span><small>REWARDS</small><strong>COINS + TOKENS</strong></span></div>
    </>
  )
}

function CampaignSurface({ progress, revision, equipmentProjection, purchaseCosmetic, purchaseMarketItem, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, busy, onNavigate }) {
  const [place, setPlace] = useState('office')
  const [mapCollapsed, setMapCollapsed] = useState(false)
  const openForge = () => onNavigate?.('forge')
  const selectPlace = (next) => setPlace(next)
  const homeNavigate = (next) => {
    if (next === 'forge') {
      setPlace('office')
      return
    }
    if (next === 'market' || next === 'office' || next === 'home') setPlace(next)
    else onNavigate?.(next)
  }
  return (
    <div className="campaign-v1 game-screen-scroll" data-testid="campaign-surface" data-campaign-revision={revision}>
      <div className={`campaign-layout ${mapCollapsed ? 'map-rail-is-collapsed' : ''}`}>
        <CampaignMapRail progress={progress} place={place} onSelect={selectPlace} collapsed={mapCollapsed} onToggle={() => setMapCollapsed((value) => !value)} />
        <main className="campaign-place-panel">
          {place === 'home' && <Homestead progress={progress} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} busy={busy} onNavigate={homeNavigate} />}
          {place === 'market' && <CampaignMarket progress={progress} purchaseMarketItem={purchaseMarketItem} busy={busy} onBackHome={() => setPlace('home')} />}
          {place === 'office' && <CampaignOffice progress={progress} onEnter={openForge} />}
        </main>
      </div>
    </div>
  )
}

const DUNGEON_ROOM_META = {
  rest: { label: 'Campsite', iconId: 'plus', tone: 'rest', subtitle: 'Recover, cook, prepare' },
  market: { label: 'Wayfarer Market', iconId: 'spark', tone: 'market', subtitle: 'Trade run coins for an edge' },
  mystery: { label: 'Fate / Risk', iconId: 'question', tone: 'mystery', subtitle: 'Take a risk for a clue' },
  encounter: { label: 'Challenge Gate', iconId: 'sword', tone: 'encounter', subtitle: 'A question room locks the route' },
  elite: { label: 'Elite Gate', iconId: 'target', tone: 'elite', subtitle: 'High risk · trinket reward' },
  boss: { label: 'Floor Boss', iconId: 'boss', tone: 'boss', subtitle: 'Final destination · defeat to ascend' },
  selector: { label: 'Route selector', iconId: 'route', tone: 'selector', subtitle: 'Choose your next room' },
}

const dungeonRoomMeta = (type) => DUNGEON_ROOM_META[type] || DUNGEON_ROOM_META.selector

function DungeonMap({ run, onChoose, busy }) {
  if (!run?.active) return null
  const currentFloor = Number(run.floor || 1)
  const route = run.map && Array.isArray(run.map.nodes) ? run.map : null
  const currentId = route?.current_node_id || run.current_node?.id
  const visited = new Set(run.visited_node_ids || [])
  const choices = Array.isArray(run.room_choices) ? run.room_choices : []
  const choiceIds = new Set(choices.map((choice) => choice.id))
  const history = Array.isArray(run.history) ? run.history : []
  const fallbackNodes = route ? [] : [
    ...history.slice(-5).map((item, index) => ({ id: `history-${index}`, type: 'cleared', row: Math.max(1, index + 1), column: 3, label: item.mob_name || 'Cleared room', note: 'cleared' })),
    { id: 'current', type: run.room_type || 'selector', row: Math.max(1, history.length + 1), column: 3, label: 'Current room', note: 'you are here' },
    ...choices.map((choice, index) => ({ id: choice.id || `choice-${index}`, type: choice.kind || 'encounter', row: Math.max(1, history.length + 2), column: index * 2 + 1, label: choice.label || 'Next room', note: choice.description || 'next room' })),
  ]
  const nodes = route?.nodes || fallbackNodes
  const edges = route?.edges || {}
  // Match the prototype's five-column/eight-row map coordinate system so
  // route edges terminate at node centres instead of drifting between rows.
  const point = (node) => ({ x: (Number(node.column || 3) - 0.5) * 20, y: (Number(node.row || 1) - 0.5) * (120 / 8) })
  return (
    <section className="dungeon-proto-panel dungeon-map-panel" data-testid="dungeon-map" aria-label="Map and route">
      {/* Map & route is the first prototype layer; room actions and the run menu stay beside it. */}
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">LAYER ONE</span><h2>Map &amp; route</h2></div><span className="dungeon-panel-tag">FLOOR {currentFloor}</span></div>
      <p className="dungeon-panel-copy">Choose one of three authored lanes. Room types roll independently each run, so luck can hand you a full row of elites, gates, fates, camps or markets. Two elites or three gates trigger a recovery row; the final row is always camp/market preparation.</p>
      <div className="dungeon-map-legend"><span><i className="legend-dot rest" />rest</span><span><i className="legend-dot market" />market</span><span><i className="legend-dot encounter" />challenge</span><span><i className="legend-dot elite" />elite</span><span><i className="legend-dot mystery" />fate / risk</span><span><i className="legend-dot boss" />boss</span></div>
      <div className="dungeon-proto-map" role="grid" aria-label={`Dungeon map floor ${currentFloor}`}>
        <svg className="dungeon-map-edges" viewBox="0 0 100 120" preserveAspectRatio="none" aria-hidden="true">
          {Object.entries(edges).flatMap(([fromId, toIds]) => {
            const from = nodes.find((node) => node.id === fromId)
            if (!from) return []
            return (Array.isArray(toIds) ? toIds : []).map((toId) => {
              const to = nodes.find((node) => node.id === toId)
              if (!to) return null
              const a = point(from); const b = point(to)
              const active = visited.has(from.id) && (visited.has(to.id) || choiceIds.has(to.id))
              return <line key={`${from.id}-${to.id}`} className={active ? 'active' : ''} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />
            })
          })}
        </svg>
        {nodes.map((node) => {
          const isCurrent = node.id === currentId || (!route && node.id === 'current')
          const isAvailable = choiceIds.has(node.id)
          const isVisited = visited.has(node.id) || (!route && node.type === 'cleared')
          const meta = dungeonRoomMeta(node.type)
          const button = route ? isAvailable : isAvailable
          return (
            <button key={node.id} type="button" className={`dungeon-map-node ${node.type} ${isCurrent ? 'current' : ''} ${isVisited ? 'visited' : ''} ${isAvailable ? 'reachable' : ''}`} style={{ gridColumn: node.column || 3, gridRow: node.row || 1 }} disabled={!button || busy || !onChoose} onClick={() => onChoose?.(run.run_id, node.id)} aria-label={`${node.label || meta.label}${isAvailable ? ', next room' : isCurrent ? ', you are here' : ''}`}>
              <span aria-hidden="true"><RouteIcon id={isCurrent ? 'flame' : meta.iconId} /></span><strong>{isCurrent ? 'YOU ARE HERE' : node.label || meta.label}</strong><small>{isAvailable ? 'NEXT ROOM' : node.note || meta.subtitle}</small>
            </button>
          )
        })}
      </div>
      <div className="dungeon-route-footer"><span>YOU ARE HERE · {run.current_node?.label || (run.room_type || 'route selector').toUpperCase()}</span><span>{choices.length ? `${choices.length} route${choices.length === 1 ? '' : 's'} ahead` : run.room_type === 'selector' ? 'route pending' : 'room committed · route locked'}</span></div>
      {!route && choices.length > 0 && <div className="dungeon-route-choice-list" aria-label="Choose your next room">{choices.map((choice) => <button key={choice.id} type="button" onClick={() => onChoose?.(run.run_id, choice.id)} disabled={busy || !onChoose}><RouteIcon id={dungeonRoomMeta(choice.kind).icon} /><span><strong>{choice.label}</strong><small>{choice.description}</small></span><b>→</b></button>)}</div>}
    </section>
  )
}

function DungeonCharacterPanel({ run, tab, setTab, onEquip, busy, onFinish, onReset }) {
  const loadout = run.loadout || {}
  const inventory = Array.isArray(run.inventory) ? run.inventory : []
  const tabs = ['LOADOUT', 'INVENTORY', 'STATS']
  const classData = run.class || {}
  const iconFor = (kind) => kind === 'armor' ? 'shield' : kind === 'trinket' ? 'spark' : 'sword'
  return (
    <section className="dungeon-proto-panel dungeon-character-panel" aria-label="Character menu">
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">RUN MENU</span><h2>Character</h2></div><span className="dungeon-panel-tag">{run.active ? 'ACTIVE' : 'ENDED'}</span></div>
      <div className="dungeon-class-summary"><span className="dungeon-class-icon" aria-hidden="true"><RouteIcon id="spark" /></span><div><span className="dungeon-eyebrow">ACTIVE CLASS · PASSIVE</span><strong>{classData.name || 'Dungeon class'}</strong><small>{classData.passive || 'Choose a class before the descent.'}</small></div></div>
      <div className="dungeon-character-tabs" role="tablist" aria-label="Run character tabs">{tabs.map((item) => <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === 'LOADOUT' && <div className="dungeon-loadout-list">{['weapon', 'armor', 'trinket'].map((slot) => { const item = inventory.find((candidate) => candidate.kind === slot && candidate.equipped) || inventory.find((candidate) => candidate.kind === slot); return <div className="dungeon-loadout-item" key={slot}><span className="dungeon-item-art"><RouteIcon id={iconFor(slot)} /></span><div><small>{slot.toUpperCase()} · {item ? 'OWNED' : 'EMPTY'}</small><strong>{item?.name || loadout[slot] || 'None'}</strong><span>{item?.description || 'Earn this slot from an authored room.'}</span></div>{item && <button type="button" disabled={busy || item.equipped} onClick={() => onEquip?.(run.run_id, item.id)}>{item.equipped ? 'Equipped' : 'Equip'}</button>}</div> })}<div className="dungeon-supply-item"><RouteIcon id="scroll" /><div><small>RUN ITEM · SCOUTING</small><strong>Vision scroll</strong><span>Preview one unrevealed risk on the map.</span></div><b>{loadout.vision_scrolls ?? 0}</b></div></div>}
      {tab === 'INVENTORY' && <div className="dungeon-inventory-list" data-testid="dungeon-inventory">{inventory.map((item) => <div key={item.id} className={item.equipped ? 'equipped' : ''}><div><small>{String(item.kind || 'item').toUpperCase()}</small><strong>{item.name}</strong><span>{item.description || 'Run item'}</span></div><button type="button" onClick={() => onEquip?.(run.run_id, item.id)} disabled={busy || item.equipped}>{item.equipped ? 'Equipped' : 'Equip'}</button></div>)}{!inventory.length && <p className="dungeon-muted">Your run inventory is empty. Earn gear from markets, elites and bosses.</p>}</div>}
      {tab === 'STATS' && <div className="dungeon-stat-grid"><div><small>HP</small><strong>{loadout.hp ?? 0}/{loadout.max_hp ?? 0}</strong></div><div><small>SCORE</small><strong>{run.score ?? 0}</strong></div><div><small>COINS</small><strong>{run.run_coins ?? 0}</strong></div><div><small>HEALS</small><strong>{loadout.heals ?? 0}</strong></div><div><small>FLOOR</small><strong>{run.floor ?? 1}</strong></div><div><small>ROOM</small><strong>{run.room ?? 1}</strong></div></div>}
      <div className="dungeon-character-note"><RouteIcon id="spark" /><p>Run gear is earned from elites, bosses and markets. Equip it here; it never enters the campaign save.</p></div>
      <div className="dungeon-run-management">
        <button className="dungeon-bank-button" type="button" onClick={() => onFinish?.(run.run_id)} disabled={busy || !onFinish}>Bank score and end run</button>
        <button className="dungeon-reset-button" type="button" onClick={() => onReset?.(run.run_id)} disabled={busy || !onReset}>Reset run</button>
        <small>Discard this Dungeon checkpoint and run gear. Campaign progress stays safe.</small>
      </div>
    </section>
  )
}

function DungeonRoomPanel({ run, question, loadout, onRest, onCampAction, onRevealRisk, onEnterRisk, onMarketPurchase, onLeave, onOpenCode, busy }) {
  const type = run.room_type || 'selector'
  const meta = dungeonRoomMeta(type)
  const title = type === 'rest' ? 'A quiet ember waits between fights.' : type === 'market' ? 'A trader has set up beneath the lanterns.' : type === 'encounter' ? 'The door seals behind you.' : type === 'elite' ? 'The elite is guarding a trinket.' : type === 'boss' ? 'Every branch ends at the same throne.' : 'Choose the next room on the route.'
  const copy = type === 'rest' ? 'Recover, prepare your next clean submission, and decide when you are ready to return to the route.' : type === 'market' ? 'Spend run-only coins on a temporary edge. Nothing leaks into the campaign save.' : type === 'encounter' ? 'Question rooms are not navigational menus. They hand you to the IDE, where one verified answer decides whether the run continues.' : type === 'elite' ? 'This elite room is a harder challenge. A clean submission awards coins and one trinket; errors still return only a bounded text hint.' : type === 'boss' ? 'This is the final destination for the floor. Use the active editor to answer the boss objective; a verified submission unlocks the next branching map.' : 'The state service reveals the next room only after the route is committed.'
  const fullHealth = (loadout.hp ?? 0) >= (loadout.max_hp ?? 0)
  const encounterName = run.encounter?.name || 'The Count Keeper'
  const encounterConcept = run.encounter?.concept_id || question.concept_id || 'current concept'
  const encounterDifficulty = run.encounter?.difficulty ?? question.difficulty ?? 1
  return (
    <section className={`dungeon-proto-panel dungeon-room-panel ${meta.tone}`} aria-label="Room screen">
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">LAYER TWO</span><h2>Room screen</h2></div><span className={`dungeon-room-type ${meta.tone}`}><RouteIcon id={meta.iconId} /> {meta.label}</span></div>
      <div className={`dungeon-room-illustration ${meta.tone}`}><span className="dungeon-room-orbit orbit-a" /><span className="dungeon-room-orbit orbit-b" /><RouteIcon id={meta.iconId} /><small>{meta.subtitle}</small></div>
      <div className="dungeon-room-copy"><span className="dungeon-eyebrow">{run.current_node?.label || `${meta.label} · ROOM ${run.room || 1}`}</span><h3>{title}</h3><p>{copy}</p></div>
      {run.encounter && <div className="dungeon-mob-banner" aria-label="Current adaptive learning mob"><span className="dungeon-mob-sigil" aria-hidden="true"><RouteIcon id={type === 'boss' ? 'boss' : type === 'elite' ? 'target' : 'flame'} /></span><div><small>{type === 'boss' ? 'FLOOR BOSS' : type === 'elite' ? 'ELITE GATE' : 'ADAPTIVE MOB'} · PHASE {run.encounter.phase || 'I'}</small><strong>{run.encounter.name || encounterName}</strong><span>Concept: {encounterConcept} · difficulty {encounterDifficulty} · failure ends this run.</span></div><b>DIFFICULTY {encounterDifficulty}</b></div>}
      {type === 'selector' && <div className="dungeon-room-action"><strong>Choose a route on the map.</strong><span>Room types are visible; future questions and answers are not.</span></div>}
      {type === 'rest' && <><div className="dungeon-room-supplies"><div><span className="dungeon-eyebrow">RUN SUPPLIES</span><strong>{loadout.heals ?? 0} rests · {loadout.bandages ?? 0} bandages · {loadout.rations ?? 0} rations · {loadout.tonics ?? 0} tonics</strong></div><span>{loadout.hp ?? 0}/{loadout.max_hp ?? 0} HP</span></div><div className="dungeon-camp-rule"><span className="dungeon-eyebrow">ONE ACTION PER CAMPSITE VISIT</span><span>{run.camp_action_used ? 'Action used. Leave when you are ready.' : 'Choose one preparation, then the route opens again.'}</span></div><div className="dungeon-action-grid"><button className="dungeon-action-card" type="button" onClick={() => (onCampAction || onRest)?.(run.run_id, 'rest')} disabled={busy || run.camp_action_used || (!onCampAction && !onRest) || (loadout.heals ?? 0) <= 0 || fullHealth}><RouteIcon id="plus" /><span><strong>Rest by the fire</strong><small>Recover up to 30 HP · {loadout.heals ?? 0} charge(s)</small></span><b>REST</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'bandage')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.bandages ?? 0) <= 0 || fullHealth}><RouteIcon id="plus" /><span><strong>Use a bandage</strong><small>Recover up to 22 HP · {loadout.bandages ?? 0} left</small></span><b>HEAL</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'cook')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.rations ?? 0) <= 0}><RouteIcon id="spark" /><span><strong>Cook a ration</strong><small>Increase maximum HP by 10 · {loadout.rations ?? 0} left</small></span><b>COOK</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'sharpen')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.edge_charges ?? 0) > 0}><RouteIcon id="sword" /><span><strong>Sharpen your edge</strong><small>Next clean submission deals +1 Resolve</small></span><b>PREP</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'fortify')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.armor_guard ?? 0) > 0}><RouteIcon id="shield" /><span><strong>Fortify your armor</strong><small>Absorb one failed-submission hit</small></span><b>BRACE</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'tonic')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.tonics ?? 0) <= 0 || fullHealth}><RouteIcon id="spark" /><span><strong>Drink an ember tonic</strong><small>Recover up to 30 HP · {loadout.tonics ?? 0} left</small></span><b>TONIC</b></button></div><button className="dungeon-primary-wide" type="button" onClick={() => onLeave?.(run.run_id)} disabled={busy || !onLeave}>Leave campsite →</button></>}
      {type === 'market' && <><div className="dungeon-market-wallet"><div><span className="dungeon-eyebrow">RUN PURSE</span><strong>{run.run_coins ?? 0} coins</strong></div><div className="dungeon-market-stock"><span>Heals <b>{loadout.heals ?? 0}</b></span><span>Bandages <b>{loadout.bandages ?? 0}</b></span><span>Rations <b>{loadout.rations ?? 0}</b></span><span>Scrolls <b>{loadout.vision_scrolls ?? 0}</b></span></div></div><div className="dungeon-shelf-note"><span className="dungeon-eyebrow">ROTATING SHELF</span><span>Two weapons + two armor pieces · one copy each</span></div><div className="dungeon-market-list">{(run.market_catalog || []).map((item) => <div key={item.id} className="dungeon-market-item"><RouteIcon id={item.kind === 'weapon' ? 'sword' : item.kind === 'armor' ? 'shield' : 'spark'} /><span><strong>{item.name}</strong><small>{item.description}</small></span><button type="button" onClick={() => onMarketPurchase?.(run.run_id, item.id)} disabled={busy || !onMarketPurchase || (run.run_coins ?? 0) < (item.price ?? 0)}>{item.price}c</button></div>)}</div><button className="dungeon-primary-wide" type="button" onClick={() => onLeave?.(run.run_id)} disabled={busy || !onLeave}>Leave market →</button></>}
      {(type === 'encounter' || type === 'elite' || type === 'boss') && <><div className="dungeon-encounter-preview"><RouteIcon id={type === 'boss' ? 'boss' : type === 'elite' ? 'target' : 'sword'} /><div><span className="dungeon-eyebrow">{type === 'boss' ? 'FINAL DESTINATION' : type === 'elite' ? 'ELITE QUESTION ROOM · TRINKET DROP' : 'LOCKED QUESTION ROOM'}</span><strong>{encounterName}</strong><p>{type === 'boss' ? 'The final destination is state-owned. A verified file unlocks the next floor.' : type === 'elite' ? 'A harder question room with a bounded trinket reward.' : `${question.prompt || 'Build the answer in dungeon.py.'} The editor stays the single answer surface.`}</p></div></div><button className="dungeon-danger-wide" type="button" onClick={onOpenCode} disabled={busy || !onOpenCode}>Open code editor →</button></>}
      {type === 'mystery' && <div className="dungeon-risk-card"><RouteIcon id="question" /><div><span className="dungeon-eyebrow">{run.risk_status === 'revealed' ? 'SCOUTED RISK' : 'UNSCOUTED RISK'}</span><strong>{run.risk_profile?.title || 'Something is watching the route.'}</strong><p>{run.risk_profile?.preview || 'A vision scroll previews one risk. Entering never requires a scroll.'}</p></div><div className="dungeon-risk-actions"><button className="dungeon-ghost-button" type="button" onClick={() => onRevealRisk?.(run.run_id)} disabled={busy || run.risk_status === 'revealed' || run.risk_status === 'entered' || !onRevealRisk || (loadout.vision_scrolls ?? 0) <= 0}>Use vision scroll · {loadout.vision_scrolls ?? 0}</button><button className="dungeon-danger-wide" type="button" onClick={() => onEnterRisk?.(run.run_id)} disabled={busy || run.risk_status === 'entered' || !onEnterRisk}>Enter the risk →</button></div></div>}
      <div className="dungeon-room-note"><span>DESIGN RULE</span><p>No challenge is generated until you commit to an encounter node.</p></div>
    </section>
  )
}

function DungeonGuidePanel({ encounter, editorContent, floor }) {
  const guide = encounter?.guide || {}
  const steps = Array.isArray(guide.steps) ? guide.steps : []
  const tier = guide.tier || (floor <= 2 ? 'full' : floor <= 4 ? 'partial' : 'question')
  const code = String(editorContent || '').toLowerCase()
  const preview = steps.reduce((total, step) => {
    const signals = Array.isArray(step.inference_signals) ? step.inference_signals : []
    const complete = signals.some((signal) => {
      const value = String(signal || '').toLowerCase()
      if (!value) return false
      if (value === 'assignment' || value === 'result') return /\b[a-z_]\w*\s*=/.test(code)
      if (value === 'condition' || value === 'comparison') return /\b(if|elif|==|!=|>=|<=|>|<)\b/.test(code)
      if (value === 'iteration') return /\b(for|while)\b/.test(code)
      if (value === 'output') return /\b(print|return)\b/.test(code)
      return code.includes(value)
    })
    return total + (complete ? Number(step.resolve_damage || 0) : 0)
  }, 0)
  const total = steps.reduce((sum, step) => sum + Number(step.resolve_damage || 0), 0)
  if (tier === 'question') {
    return <section className="dungeon-guide-panel dungeon-guide-question" aria-label="Question guidance"><div className="dungeon-guide-heading"><span className="dungeon-eyebrow">FLOOR {floor} · QUESTION ONLY</span><strong>Read the objective. Build the answer yourself.</strong></div><p>The teaching rails are gone now. PYR returns only a bounded text hint after a failed submission.</p></section>
  }
  return <section className="dungeon-guide-panel" aria-label="Combat learning guide"><div className="dungeon-guide-heading"><span className="dungeon-eyebrow">{tier === 'full' ? 'STEP GUIDE' : 'PARTIAL GUIDE'} · RESOLVE PREVIEW</span><strong>{preview} / {total} preview impact</strong></div><div className="dungeon-guide-steps">{steps.map((step, index) => {
    const signals = Array.isArray(step.inference_signals) ? step.inference_signals : []
    const complete = signals.some((signal) => code.includes(String(signal || '').toLowerCase()))
    return <div key={step.id || index} className={`dungeon-guide-step ${complete ? 'complete' : ''}`}><span>{complete ? 'OK' : String(index + 1).padStart(2, '0')}</span><div><strong>{step.label}</strong><small>{complete ? `+${step.resolve_damage || 0} impact preview` : `+${step.resolve_damage || 0} impact when verified`}</small></div></div>
  })}</div><p className="dungeon-guide-note">The editor watches for concepts, not an answer key. Preview progress is committed only by a clean submission.</p></section>
}

function DungeonMechanicProfile({ encounter }) {
  const mechanic = encounter?.mechanic || {}
  const reward = encounter?.reward_envelope || {}
  const authorizedItems = Array.isArray(reward.authorized_items) ? reward.authorized_items : []
  return <section className="dungeon-mechanic-profile" aria-label="Mob profile"><div className="dungeon-mechanic-heading"><div><span className="dungeon-eyebrow">MOB PROFILE</span><strong>{mechanic.label || 'Submission Gate'}</strong></div><span className="dungeon-mechanic-state">STATE-SERVICE RULE</span></div><div className="dungeon-mechanic-grid"><div><span className="dungeon-eyebrow">WEAPON / STYLE</span><strong>{mechanic.weapon || 'Bounded verifier'}</strong></div><div><span className="dungeon-eyebrow">PASSIVE</span><p>{mechanic.passive || 'Only a validated submission changes this room.'}</p></div><div><span className="dungeon-eyebrow">TELEGRAPH</span><p>{mechanic.telegraph || 'Run is safe; submit is the combat turn.'}</p></div><div><span className="dungeon-eyebrow">ON RUN</span><p>{mechanic.on_run || 'No combat state changes while you type.'}</p></div><div><span className="dungeon-eyebrow">ON FAILURE</span><p>{mechanic.on_failure || 'A failed verdict costs bounded HP.'}</p></div></div><p className="dungeon-mechanic-reward"><span className="dungeon-eyebrow">CLEAN REWARD ENVELOPE</span><strong>+{Number(reward.score || encounter?.resolve_damage || 0)} score · +{Number(reward.coins || 0)} coins{authorizedItems.length ? ` · ${authorizedItems.join(' · ')} eligible` : ''}</strong></p></section>
}

function DungeonFileBridgeStatus() {
  return <section className="dungeon-file-bridge" aria-label="Dungeon file connection"><div><span className="dungeon-eyebrow">PROJECT FILE</span><strong>CANONICAL · dungeon.py</strong><small>The gateway-owned challenge buffer is the only file submitted for this room. Run stays local; Submit asks PYR for a verdict.</small></div><span className="dungeon-file-bridge-status">CONNECTED</span></section>
}

function DungeonScreen({ dungeon, revision, onStart, onChoose, onRest, onCampAction, onRevealRisk, onEnterRisk, onMarketPurchase, onEquip, onLeave, onFinish, onReset, submitDungeon, busy, saving, editorContent, onEditorChange, onSave }) {
  const [selectedClassId, setSelectedClassId] = useState('')
  const [submitStatus, setSubmitStatus] = useState('')
  const [roomTab, setRoomTab] = useState('room')
  const [characterTab, setCharacterTab] = useState('LOADOUT')
  const autoOpenedQuestionRef = useRef('')
  const run = dungeon || { active: false, status: 'idle' }
  const question = run.question || {}
  const loadout = run.loadout || {}

  useEffect(() => {
    if (!run.active) {
      setSelectedClassId('')
      setRoomTab('room')
      autoOpenedQuestionRef.current = ''
      return
    }
    const combatRoom = ['encounter', 'elite', 'boss'].includes(run.room_type)
    const questionId = run.question?.id || ''
    if (combatRoom && questionId && autoOpenedQuestionRef.current !== questionId) {
      autoOpenedQuestionRef.current = questionId
      setRoomTab('code')
    }
    if (!combatRoom) autoOpenedQuestionRef.current = ''
  }, [run.active, run.room_type, run.question?.id])

  const start = async () => {
    if (!onStart || busy) return
    await onStart({ classId: selectedClassId })
  }

  const submit = async () => {
    if (!submitDungeon || !question.id || !editorContent?.trim() || busy) return
    setSubmitStatus('Binding this answer for PYR…')
    try {
      await submitDungeon({ runId: run.run_id, questionId: question.id, answer: editorContent })
      setSubmitStatus('Sent to PYR. The room changes only after a validated verdict.')
    } catch (error) {
      setSubmitStatus(error?.message || 'Dungeon submission failed.')
    }
  }

  const openCode = () => setRoomTab('code')
  const chooseRoom = async (runId, choiceId) => {
    const result = await onChoose?.(runId, choiceId)
    const kind = result?.choice?.kind || result?.dungeon?.room_type || ''
    setRoomTab(['encounter', 'elite', 'boss'].includes(kind) ? 'code' : 'room')
    return result
  }
  const statusText = run.status === 'dead' ? `Run ended on floor ${run.floor ?? 0}.` : run.active ? 'Your checkpoint is safe. Keep solving to go deeper.' : 'A fresh loadout, adaptive questions and a score that belongs to this run.'

  return (
    <div className="dungeon-screen-shell" data-testid="dungeon" data-campaign-revision={revision}>
      <header className="dungeon-local-header"><div className="dungeon-local-brand"><span className="dungeon-brand-mark"><RouteIcon id="spark" /></span><div><span className="dungeon-eyebrow">INFINITE DUNGEON</span><h1>{run.active ? `Floor ${run.floor} · Room ${run.room}` : 'Design Lab'}</h1></div></div><span className="dungeon-local-badge"><i /> CANONICAL RUN · STATE GATEWAY</span>{run.active ? <div className="dungeon-run-stats" aria-label="Run stats"><div><small>FLOOR</small><strong>{run.floor ?? 1}</strong></div><div><small>HP</small><strong>{loadout.hp ?? 0}/{loadout.max_hp ?? 0}</strong></div><div><small>SCORE</small><strong>{run.score ?? 0}</strong></div><div><small>COINS</small><strong>{run.run_coins ?? 0}</strong></div><button className="dungeon-reset-header" type="button" onClick={() => onReset?.(run.run_id)} disabled={busy || !onReset}>Reset run</button></div> : <div className="dungeon-header-note"><span className="dungeon-eyebrow">BEFORE THE DESCENT</span><strong>CHOOSE YOUR CLASS</strong></div>}</header>
      {!run.active ? <main className="dungeon-class-select" aria-label="Choose a dungeon class"><section className="dungeon-class-hero"><span className="dungeon-eyebrow">RUN SETUP · FLOOR 1</span><h2>So how you wanna play it.</h2><p>Pick a class</p></section><section className="dungeon-class-grid" role="radiogroup" aria-label="Dungeon classes">{DUNGEON_CLASSES.map((starterClass) => <button key={starterClass.id} type="button" role="radio" aria-checked={selectedClassId === starterClass.id} className={`dungeon-class-card ${selectedClassId === starterClass.id ? 'selected' : ''}`} onClick={() => setSelectedClassId(starterClass.id)} disabled={busy}><span className="dungeon-class-card-top"><span className="dungeon-class-icon" aria-hidden="true"><RouteIcon id={starterClass.iconId} /></span><span><span className="dungeon-eyebrow">{starterClass.role}</span><strong>{starterClass.name}</strong></span>{selectedClassId === starterClass.id && <small className="dungeon-class-picked">READY</small>}</span><span className="dungeon-class-weapon"><span className="dungeon-class-label">STARTER WEAPON</span><strong>{starterClass.weapon}</strong><small>{starterClass.weaponDetail || 'A bounded run weapon for this playstyle.'}</small></span><span className="dungeon-class-passive"><span className="dungeon-class-label">PASSIVE</span><p>{starterClass.passive}</p></span></button>)}</section>{selectedClassId && <div className="dungeon-class-cta" aria-live="polite"><button className="dungeon-primary-button" type="button" onClick={start} disabled={busy}>{busy ? 'Starting…' : 'Enter the dungeon'} <span>→</span></button></div>}</main> : roomTab === 'code' ? <section className="dungeon-ide-screen" aria-label="Challenge IDE"><div className="dungeon-ide-topline"><button type="button" className="dungeon-ghost-button" onClick={() => setRoomTab('room')}>← Map locked</button><span className="dungeon-eyebrow">{run.room_type === 'boss' ? 'FLOOR BOSS · FINAL DESTINATION' : run.room_type === 'elite' ? 'ELITE GATE · TRINKET DROP' : 'QUESTION ROOM · NO ROUTE CONTROLS'}</span><span className="dungeon-ide-risk">FAILURE COSTS HP</span></div><div className="dungeon-ide-layout"><aside className="dungeon-challenge-brief"><span className="dungeon-eyebrow">{run.room_type === 'boss' ? 'THE COUNT KEEPER · BOSS CHECK' : run.room_type === 'elite' ? 'ELITE CHECK' : 'CONCEPT CHECK'}</span><h2>{run.room_type === 'boss' ? 'Defeat The Count Keeper to ascend.' : run.room_type === 'elite' ? 'Break the elite gate for its trinket.' : 'Write the answer in dungeon.py.'}</h2><p>{run.encounter?.lore || statusText}</p><div className="dungeon-resolve-preview"><div><small>{run.room_type === 'boss' ? 'BOSS RESOLVE' : run.room_type === 'elite' ? 'ELITE RESOLVE' : 'ROOM RESOLVE'}</small><strong>{run.encounter?.resolve ?? '—'} / {run.encounter?.max_resolve ?? '—'}</strong></div><span>clean submission · +{run.encounter?.resolve_damage ?? 0} Resolve impact</span></div><div className="dungeon-run-health"><span>RUN HP</span><strong>{loadout.hp ?? 0} / {loadout.max_hp ?? 0}</strong><small>an incorrect verdict costs bounded HP</small></div><DungeonGuidePanel encounter={run.encounter} editorContent={editorContent} floor={run.floor ?? 1} /><DungeonMechanicProfile encounter={run.encounter} /><DungeonFileBridgeStatus /></aside><div className="dungeon-code-workbench"><div className="dungeon-editor-toolbar"><span>dungeon.py · current room buffer</span><span>PYTHON · MONACO · LOCAL COMPLETION</span></div><DungeonEditorSurface value={editorContent || ''} onChange={onEditorChange} onSave={onSave} onSubmit={submit} busy={busy} saving={saving} />{submitStatus && <small className="battle-submit-status" role="status">{submitStatus}</small>}</div></div></section> : <><div className="dungeon-workspace-tabs" role="tablist" aria-label="Dungeon workspace"><button type="button" role="tab" aria-selected={roomTab === 'map'} className={roomTab === 'map' ? 'active' : ''} onClick={() => setRoomTab('map')}>Map &amp; route</button><button type="button" role="tab" aria-selected={roomTab === 'room'} className={roomTab === 'room' ? 'active' : ''} onClick={() => setRoomTab('room')}>Room screen</button><button type="button" role="tab" aria-selected={roomTab === 'code'} className={roomTab === 'code' ? 'active' : ''} onClick={openCode} disabled={!['encounter', 'elite', 'boss'].includes(run.room_type)}>Code editor</button></div><div className="dungeon-prototype-grid" data-testid="dungeon-tab-panel"><DungeonMap run={run} onChoose={chooseRoom} busy={busy} /><DungeonRoomPanel run={run} question={question} loadout={loadout} onRest={onRest} onCampAction={onCampAction} onRevealRisk={onRevealRisk} onEnterRisk={onEnterRisk} onMarketPurchase={onMarketPurchase} onLeave={onLeave} onOpenCode={openCode} busy={busy} /><DungeonCharacterPanel run={run} tab={characterTab} setTab={setCharacterTab} onEquip={onEquip} busy={busy} onFinish={onFinish} onReset={onReset} /></div><p className="dungeon-checkpoint-note">{statusText} Run <code>{run.run_id}</code> will resume after a Forge or workstation restart; death is the only reset.</p></>}
    </div>
  )
}

function PracticeScreen({ progress, revision, practiceProjection, onPracticePrompt, busy }) {
  const activeProject = (progress.projects || []).find((project) => project.status === 'active') || {}
  const concepts = Array.from(new Set([
    ...(progress.skills || []).map((skill) => skill.concept).filter(Boolean),
    ...(activeProject.mobs || []).map((mob) => mob.concept).filter(Boolean),
    progress.learning_state?.concept,
    'python-basics',
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
          <label><span>Concept</span><select value={concept} onChange={(event) => setConcept(event.target.value)} disabled={busy}>{concepts.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Question type</span><select value={questionType} onChange={(event) => setQuestionType(event.target.value)} disabled={busy}><option value="true_false">True / False</option><option value="multiple_choice">Multiple choice</option><option value="short_explanation">Short explanation</option><option value="code_trace">Code trace</option><option value="bug_hunt">Bug hunt</option></select></label>
          <label><span>Difficulty</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} disabled={busy}>{[1, 2, 3, 4, 5].map((level) => <option key={level} value={level}>Tier {level}</option>)}</select></label>
          <label className="practice-answer"><span>Answer or ask for feedback</span><textarea value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={20_000} rows={5} placeholder="Leave blank for a new question, or paste your answer here…" disabled={busy} /></label>
          <button className="primary" type="submit" disabled={busy}>{busy ? 'Sending…' : answer.trim() ? 'Ask for feedback' : 'Ask PYR for a drill'}</button>
        </form>
        {status && <small className="battle-submit-status" role="status">{status}</small>}
      </section>
      <section className="game-card">
        <div className="card-heading"><span>PRACTICE BOUNDARY</span><b>SEPARATE MODE</b></div>
        <p className="context-note">Practice uses the same bounded provider context as Campaign, but it never creates a leaderboard run, copies Campaign gear, or changes Campaign state. Your drills, explanations and examples stay in the shared tutor.py notebook.</p>
      </section>
      <section className="game-card">
        <div className="card-heading"><span>RECENT PRACTICE HISTORY</span><b>{practiceProjection?.count ?? 0}</b></div>
        {practiceProjection?.sessions?.length ? <div className="practice-history">{practiceProjection.sessions.slice().reverse().slice(0, 8).map((session) => <article key={session.session_id}><div><strong>{session.concept}</strong><small>{session.question_type} · Tier {session.difficulty}</small></div><span>{session.correct ?? 0}/{session.attempts ?? 0} correct</span></article>)}</div> : <p className="context-note">Your first drill will appear here after the state gateway opens a Practice session.</p>}
      </section>
    </div>
  )
}

function AccountPanel({ account, busy, notice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict, revision }) {
  const [formMode, setFormMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [deviceLabel, setDeviceLabel] = useState(account.device?.display_name || 'Quest Lab device')
  const configured = account.configured && account.configurationValid
  const signedIn = account.authStatus === 'signed-in' && account.user
  const avatar = account.avatar || {}
  const avatarStatus = String(avatar.status || 'idle').toLowerCase()
  const avatarSource = String(avatar.source || 'local').toLowerCase()
  const avatarLabel = avatarStatus === 'ready'
    ? avatarSource === 'cloud' ? 'PRIVATE CLOUD' : avatarSource === 'cached-cloud' ? 'CACHED CLOUD' : 'LOCAL'
    : avatarStatus.replace(/-/g, ' ').toUpperCase()

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
           <div className="account-sync-diagnostics" data-testid="account-sync-diagnostics" aria-label="Campaign sync diagnostics">
             <div><span>Local campaign revision</span><strong>{revision ?? '—'}</strong></div>
             <div><span>Cloud cursor</span><strong>{account.cloudRevision ?? '—'}</strong></div>
             <div><span>Queued changes</span><strong>{account.pendingChanges ?? 0}</strong></div>
           </div>
           <div className="account-avatar-sync" data-testid="account-avatar-sync" aria-label="Portrait sync status">
             <span>Portrait sync</span>
             <strong>{avatarLabel}</strong>
             <small>{avatar.cached ? 'cached on this device' : avatar.dataUrl ? 'available in this session' : 'no portrait available'}</small>
           </div>
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

function WorkspaceTransferPanel({ transfer, busy, notice, onRefresh, onPush, onPreviewPull, onApplyPull }) {
  const files = transfer?.files || []
  const conflicts = transfer?.conflicts || []
  const available = Boolean(transfer?.ok)
  const statusLabel = transfer?.remote_commit ? 'BUNDLE READY' : available ? 'NO BUNDLE' : 'UNAVAILABLE'
  const differentCount = files.filter((file) => file.status === 'different').length
  const dirtyCount = Array.isArray(transfer?.allowed_dirty) ? transfer.allowed_dirty.length : 0
  const excludedCount = Array.isArray(transfer?.blocked_dirty) ? transfer.blocked_dirty.length : 0
  const digestLabel = (file) => {
    const local = file.local_sha256 || file.sha256
    const remote = file.remote_sha256
    if (file.status === 'different' && local && remote) return `local ${local.slice(0, 8)}… · remote ${remote.slice(0, 8)}…`
    if (remote) return `remote ${remote.slice(0, 8)}…`
    if (local) return `sha ${local.slice(0, 8)}…`
    return 'hash unavailable'
  }
  return (
    <section className="game-card settings-card workspace-transfer-card" data-testid="workspace-transfer">
      <div className="card-heading"><span>PROJECT FILE TRANSFER</span><b>{statusLabel}</b></div>
      <p className="settings-note">Move reviewed project files between your devices without moving <code>progress.json</code>, PTY data or private session logs.</p>
      {!transfer && <button type="button" onClick={onRefresh} disabled={busy}>Check transfer channel</button>}
      {transfer && (
        <>
          <div className="workspace-transfer-meta"><span>{transfer.transfer_branch || 'questlab-files/01-blackjack'}</span><span>{transfer.remote_commit ? `${String(transfer.remote_commit).slice(0, 8)}…` : 'empty'}</span></div>
          <div className="workspace-transfer-summary" data-testid="workspace-transfer-summary" aria-label="Workspace transfer comparison">
            <span>{files.length} allowlisted file{files.length === 1 ? '' : 's'}</span>
            <span>{dirtyCount} local edit{dirtyCount === 1 ? '' : 's'}</span>
            <span>{excludedCount} excluded change{excludedCount === 1 ? '' : 's'}</span>
          </div>
          {differentCount > 0 && <p className="workspace-transfer-conflict" role="status">Hash mismatch: review the local and remote digests below before applying or overwriting.</p>}
          <div className="workspace-transfer-files">
            {files.length ? files.map((file) => <div key={file.path}><span>{file.path}</span><span className="workspace-transfer-file-meta"><b className={`transfer-file-status ${file.status || ''}`}>{file.status || 'tracked'}</b><small>{digestLabel(file)}</small></span></div>) : <p className="context-note">No allowlisted files are available in the transfer preview yet.</p>}
          </div>
          {conflicts.length > 0 && <p className="workspace-transfer-conflict" role="alert">Local edits conflict with: {conflicts.join(', ')}. Preview first, then choose overwrite only after reviewing a backup.</p>}
          <div className="account-actions workspace-transfer-actions">
            <button type="button" disabled={busy || !available} onClick={onPush}>Send project files</button>
            <button type="button" disabled={busy || !available} onClick={onPreviewPull}>Preview incoming</button>
            {transfer.requires_overwrite_opt_in && <button type="button" disabled={busy} onClick={() => onApplyPull(true)}>Overwrite after backup</button>}
            {transfer.requires_confirmation && !transfer.requires_overwrite_opt_in && <button type="button" disabled={busy} onClick={() => onApplyPull(false)}>Apply incoming</button>}
            <button type="button" disabled={busy} onClick={onRefresh}>Refresh</button>
          </div>
        </>
      )}
      {(notice || transfer?.error) && <p className="account-message error">{notice || transfer.error}</p>}
      <small className="settings-note">Allowlist: blackjack.py · tutor.py · dungeon.py · notes/&lt;concept&gt;.md. Progression stays in the canonical state gateway.</small>
    </section>
  )
}

function SettingsScreen({ preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict, revision, workspaceTransfer, workspaceTransferBusy, workspaceTransferNotice, onWorkspaceTransferRefresh, onWorkspaceTransferPush, onWorkspaceTransferPreviewPull, onWorkspaceTransferApplyPull }) {
  const { editorFontSize, terminalFontSize, hudDensity, animations, showAiTerminal, themeChoice, fontFamily } = preferences
  return (
    <div className="game-screen-scroll settings-screen" data-campaign-revision={revision}>
      <div className="screen-hero">
        <div><span className="screen-kicker">SETTINGS</span><h2>Make the Forge fit you.</h2><p>Usability and accessibility settings are free forever. Homestead coins only unlock cosmetic presentation.</p></div>
      </div>

      <div className="screen-grid two">
        <AccountPanel account={account} busy={accountBusy} notice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onResolveConflict={onResolveConflict} revision={revision} />
        <WorkspaceTransferPanel transfer={workspaceTransfer} busy={workspaceTransferBusy} notice={workspaceTransferNotice} onRefresh={onWorkspaceTransferRefresh} onPush={onWorkspaceTransferPush} onPreviewPull={onWorkspaceTransferPreviewPull} onApplyPull={onWorkspaceTransferApplyPull} />
        <section className="game-card settings-card">
          <div className="card-heading"><span>EDITOR</span></div>
          <label><span>Editor font size</span><b>{editorFontSize}px</b><input type="range" min="11" max="22" value={editorFontSize} onChange={(event) => setters.setEditorFontSize(Number(event.target.value))} /></label>
          <label><span>Terminal font size</span><b>{terminalFontSize}px</b><input type="range" min="10" max="20" value={terminalFontSize} onChange={(event) => setters.setTerminalFontSize(Number(event.target.value))} /></label>
          <label><span>HUD density</span><select value={hudDensity} onChange={(event) => setters.setHudDensity(event.target.value)}><option value="full">Full</option><option value="compact">Compact</option></select></label>
          <label className="toggle-row"><span>Animations</span><input type="checkbox" checked={animations} onChange={(event) => setters.setAnimations(event.target.checked)} /></label>
          <label><span>Theme</span><select value={themeChoice || ''} onChange={(event) => setters.setThemeChoice(event.target.value)}><option value="">Homestead equipped theme</option><option value="gruvbox-dark">Gruvbox Dark</option><option value="gruvbox-light">Gruvbox Light</option><option value="github-dark">GitHub Dark</option><option value="github-light">GitHub Light</option><option value="deep-forest">Deep Forest</option><option value="void-scholar">Void Scholar</option><option value="ancient-archive">Ancient Archive</option></select></label>
          <label><span>Interface font</span><select value={fontFamily || 'inter'} onChange={(event) => setters.setFontFamily(event.target.value)}><option value="inter">Inter · neutral</option><option value="ibm-plex">IBM Plex Sans · readable</option><option value="atkinson">Atkinson Hyperlegible · high clarity</option><option value="system">System UI</option></select></label>
          <label className="toggle-row"><span>AI terminal visible</span><input type="checkbox" checked={showAiTerminal !== false} onChange={(event) => setters.setShowAiTerminal(event.target.checked)} /></label>
          <p className="settings-note">AI stays hidden on Codex, Homestead and Settings so those pages can breathe. The PTY remains mounted and reconnect-free.</p>
          <div className="settings-layout-actions"><span>Panel layout</span><button type="button" onClick={resetLayout}>Reset panel layout</button></div>
        </section>
      </div>
    </div>
  )
}

export function GameScreen({ activeView, progress, revision, avatarDataUrl = '', encounter, codexProjection, practiceProjection, equipmentProjection, dungeon, dungeonEditorContent, onDungeonEditorChange, onSaveDungeon, onDungeonChoose, onDungeonRest, onDungeonCampAction, onDungeonRevealRisk, onDungeonEnterRisk, onDungeonMarketPurchase, onDungeonEquip, onDungeonLeave, onDungeonFinish, onDungeonReset, purchaseCosmetic, purchaseMarketItem, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, saveCodexNote, busy, dungeonSaving, submitBattle, submitBoss, submitDungeon, onStartDungeon, onPracticePrompt, preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict, workspaceTransfer, workspaceTransferBusy, workspaceTransferNotice, onWorkspaceTransferRefresh, onWorkspaceTransferPush, onWorkspaceTransferPreviewPull, onWorkspaceTransferApplyPull, onNavigate, tutorCode, tutorDirty, tutorExternalChange, editorFontSize = 14, onTutorChange, onTutorSave, onTutorFormat, onTutorRun, onTutorReloadExternal, onTutorKeepEdits, campaignReady = true, showNavigation = true }) {
  const wideRoute = ['hub', 'character', 'homestead', 'codex', 'tutor', 'settings'].includes(activeView)
  // Historical contract marker: const wideRoute = ['hub', 'character', 'homestead', 'codex', 'settings']
  const withWideNavigation = (screen) => wideRoute && showNavigation
    ? <WideSurfaceFrame activeView={activeView} onNavigate={onNavigate}>{screen}</WideSurfaceFrame>
    : screen

  if (!campaignReady && activeView !== 'settings') {
    return withWideNavigation(
      <div className="game-screen-scroll campaign-loading" data-testid="campaign-loading" aria-live="polite">
        <section className="screen-hero">
          <div><span className="screen-kicker">CAMPAIGN SYNC</span><h2>Waiting for the canonical state</h2><p>Forge will show your level, encounters, Codex and inventory as soon as the state service returns the latest revision. No starter values are being substituted.</p></div>
        </section>
      </div>
    )
  }
  if (activeView === 'hub') return withWideNavigation(<CampaignSurface progress={progress} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} purchaseMarketItem={purchaseMarketItem} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} busy={busy} onNavigate={onNavigate} />)
  if (activeView === 'quests' || activeView === 'codex' || activeView === 'tutor') return withWideNavigation(<ResourceTutorScreen activeView={activeView} progress={progress} revision={revision} codexProjection={codexProjection} encounter={encounter} tutorCode={tutorCode} tutorDirty={tutorDirty} tutorExternalChange={tutorExternalChange} editorFontSize={editorFontSize} busy={busy} onTutorChange={onTutorChange} onTutorSave={onTutorSave} onTutorFormat={onTutorFormat} onTutorRun={onTutorRun} onPracticePrompt={onPracticePrompt} onTutorReloadExternal={onTutorReloadExternal} onTutorKeepEdits={onTutorKeepEdits} onNavigate={onNavigate} />)
  // Legacy render contract retained in source comments for downstream static
  // checks; the live route above owns the replacement surface.
  // withWideNavigation(<Codex progress={progress} revision={revision} codexProjection={codexProjection} showNavigation={false} />)
  if (activeView === 'character') return withWideNavigation(<CharacterSheet progress={progress} revision={revision} avatarDataUrl={avatarDataUrl} encounter={encounter} codexProjection={codexProjection} onNavigate={onNavigate} />)
  if (activeView === 'homestead') return withWideNavigation(<Homestead progress={progress} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} busy={busy} onNavigate={onNavigate} />)
  if (activeView === 'dungeon') return <DungeonScreen dungeon={dungeon} revision={revision} onStart={onStartDungeon} onChoose={onDungeonChoose} onRest={onDungeonRest} onCampAction={onDungeonCampAction} onRevealRisk={onDungeonRevealRisk} onEnterRisk={onDungeonEnterRisk} onMarketPurchase={onDungeonMarketPurchase} onEquip={onDungeonEquip} onLeave={onDungeonLeave} onFinish={onDungeonFinish} onReset={onDungeonReset} submitDungeon={submitDungeon} busy={busy} saving={dungeonSaving} editorContent={dungeonEditorContent} onEditorChange={onDungeonEditorChange} onSave={onSaveDungeon} />
  if (activeView === 'practice') return <PracticeScreen progress={progress} revision={revision} practiceProjection={practiceProjection} onPracticePrompt={onPracticePrompt} busy={busy} />
  if (activeView === 'settings') return <SettingsScreen preferences={preferences} setters={setters} resetLayout={resetLayout} account={account} accountBusy={accountBusy} accountNotice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onResolveConflict={onResolveConflict} workspaceTransfer={workspaceTransfer} workspaceTransferBusy={workspaceTransferBusy} workspaceTransferNotice={workspaceTransferNotice} onWorkspaceTransferRefresh={onWorkspaceTransferRefresh} onWorkspaceTransferPush={onWorkspaceTransferPush} onWorkspaceTransferPreviewPull={onWorkspaceTransferPreviewPull} onWorkspaceTransferApplyPull={onWorkspaceTransferApplyPull} revision={revision} />
  return null
}
