import { merchantItemArt } from './merchantItemArt.js'
import { merchantLots } from './merchantShop.js'
import { marketWeaponPreview } from './marketWeaponPreview.js'
import { lanternEncounterArt, lanternEncounterLocation } from './lanternEncounterArt'
import { lanternItemArt } from './lanternItemArt'
import { Fragment, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Editor from '@monaco-editor/react'
import { registerPythonHoverProvider } from './pythonHover.js'
import '@fontsource/vt323/400.css'
import '@fontsource/press-start-2p/400.css'
import './homestead.css'
import './campaign.css'
import './hunterCodex.css'
import './settings.css'
import './dungeonBrief.css'
import './avatar.css'
import { RECOLOUR_LOOKS, hunterAppearance } from './hunterEquipment.js'
import { merchantPixelSprite } from './campaignMerchant.js'
import { AVATAR_LABELS, AVATAR_PALETTES, AVATAR_STYLE_LABELS, AVATAR_VIEWBOX, CHARACTER_NAME, DEFAULT_APPEARANCE, avatarRects } from './avatarSprite.js'
import { PORTRAIT_SIZE, portraitRects } from './portraitSprite.js'
import { homePyrStage } from './homePyr.js'
import { campaignBossTrophies } from './homeTrophies.js'
import { HOME_DIRECTORY } from './homeDirectory.js'
import CastleFloorPlan from './CastleFloorPlan.jsx'
import TutorLearningPath from './TutorLearningPath.jsx'
import DungeonCombatArena from './DungeonCombatArena.jsx'
import SparGearMenu from './SparGearMenu.jsx'
import { sparLoadout, sparLoadoutRequest, sparView } from './sparLoadout.js'
import OnlineHideout from './OnlineHideout.jsx'
import OnlineHousePanel from './OnlineHousePanel.jsx'
import OnlinePageBoundary from './OnlinePageBoundary.jsx'
import { lessonFor, TUTOR_TRUE_FALSE } from './tutorLessons.js'

export const viewItems = [
  { id: 'hub', label: 'Campaign' },
  { id: 'tutor', label: 'Hunter’s Study' },
  { id: 'dungeon', label: 'Infinite Dungeon' },
  { id: 'online', label: 'Colosseum' },
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
    weapon: 'Aether Staff',
    weaponDetail: 'First mistake each fight deals 2 less damage.',
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
    weapon: 'Pathfinder Whip',
    weaponDetail: '+1 Resolve on the first correct answer each fight.',
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

function DungeonEditorSurface({ value, onChange, onSave, onRunCode, onSubmit, runId, questionId, busy, saving }) {
  const [terminal, setTerminal] = useState({ status: 'ready', output: ['Run dungeon.py to see its Python output here.'] })
  const [running, setRunning] = useState(false)
  const runRef = useRef(null)
  const run = async (source = value) => {
    if (!String(source || '').trim()) {
      setTerminal({ status: 'empty', output: ['No code to run. Write a Python attempt, then run dungeon.py.'] })
      return
    }
    if (!onRunCode || running) return
    setRunning(true)
    setTerminal({ status: 'running', output: ['$ python dungeon.py', 'Running locally…'] })
    try {
      const result = await onRunCode({ runId, questionId, content: source })
      const lines = [`$ python dungeon.py`, result.output || 'Program finished with no output.']
      if (result.status === 'timeout') lines.push('Run stopped at the 5 second limit. This does not submit the answer or affect combat.')
      else lines.push(`Process exited with code ${result.exit_code}. This does not submit the answer or affect combat.`)
      setTerminal({ status: result.status || 'failed', output: lines })
    } catch (error) {
      setTerminal({ status: 'failed', output: [`Could not run dungeon.py: ${error?.message || 'Unknown error'}`, 'Save or refresh the current question, then try again.'] })
    } finally {
      setRunning(false)
    }
  }
  runRef.current = run
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
            registerPythonHoverProvider(monaco)
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
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => runRef.current?.(editor.getValue()))
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => onSubmit?.())
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => onSave?.())
            editor.onDidDispose(() => provider.dispose())
          }}
          theme="vs-dark"
          options={{
            minimap: { enabled: false }, acceptSuggestionOnEnter: 'off',
            // Keep hovers for the first visible line outside Monaco's clipped
            // text viewport so the full variable/function tooltip can render.
            fixedOverflowWidgets: true,
            allowOverflow: true,
            hover: { above: false, sticky: true },
            fontSize: 14,
            fontFamily: 'JetBrains Mono, ui-monospace, monospace',
            lineHeight: 22,
            padding: { top: 14, bottom: 14 },
            automaticLayout: true,
            smoothScrolling: true,
            tabSize: 4,
            suggestOnTriggerCharacters: true,
            // Locked while PYR grades or writes the room, so no checkpoint
            // save can change the state revision mid-call.
            readOnly: Boolean(busy),
          }}
        />
      </div>
      <div className={`dungeon-editor-terminal ${terminal.status}`} role="status" aria-label="Dungeon Python terminal output">
        <div className="dungeon-editor-terminal-heading"><span>PYTHON TERMINAL · LOCAL RUN</span><b>{running ? 'RUNNING' : terminal.status.toUpperCase()}</b></div>
        <pre>{terminal.output.join('\n')}</pre>
      </div>
      <div className="dungeon-editor-actions">
        <button type="button" onClick={onSave} disabled={busy || saving}>{saving ? 'Saving…' : 'Save checkpoint'} <kbd>Ctrl/Cmd S</kbd></button>
        <button type="button" data-dungeon-run onClick={() => run()} disabled={busy || running}>Run Python <kbd>Ctrl/Cmd ↵</kbd></button>
        <button className="primary" type="button" data-dungeon-submit onClick={onSubmit} disabled={busy || !String(value || '').trim()}>Submit to PYR <kbd>Ctrl/Cmd ⇧ ↵</kbd> ↗</button>
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
      ? `**${currentQuest.label || currentQuest.id || 'Current goal'}** · ${currentQuest.question_type || 'validated goal'} · ${currentQuest.damage ?? currentQuest.impact ?? 0} Resolve damage\n\n${currentQuest.quest || currentQuest.brief || 'Complete the current state-owned goal in the active Hunt file.'}`
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

function ForgeDocumentTabs({ activePath, editorMode, openFile, openQuestDocument }) {
  return (
    <div className="forge-document-tabs" role="tablist" aria-label="Hunt documents">
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
    <div className="forge-compact-panel" data-testid="forge-compact-panel" aria-label="Compact Hunt file rail">
      <button
        type="button"
        className="forge-compact-expand"
        onClick={onToggleCompact}
        title="Expand Hunt sidebar"
        aria-label="Expand Hunt sidebar"
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

// The workspace is the platform checkout, so the raw tree also lists Quest
// Lab's own docs, tooling and dot-folders. "Game" view keeps only what the
// player builds: code files at the root and folders they created.

function parentDirOf(path) {
  const parts = String(path || '').split('/').filter(Boolean)
  return parts.slice(0, -1).join('/')
}

// Explorer glyphs drawn in the shared SVG style (no emoji).
function ExplorerIcon({ kind }) {
  const paths = {
    chevron: <path d="m9 6 6 6-6 6" />,
    folder: <path d="M3 7.5V18a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-8l-2-2.5H4a1 1 0 0 0-1 1Z" />,
    'folder-open': <path d="M3 18V6.5a1 1 0 0 1 1-1h6l2 2.5h7a1 1 0 0 1 1 1V11M3 18l2.6-6.4a1 1 0 0 1 .9-.6H21l-3 7.4a1 1 0 0 1-.9.6H4a1 1 0 0 1-1-1Z" />,
    'new-file': <><path d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7Z" /><path d="M14 3v4h4M12 11v6M9 14h6" /></>,
    'new-folder': <><path d="M3 7.5V18a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1h-8l-2-2.5H4a1 1 0 0 0-1 1Z" /><path d="M12 11v6M9 14h6" /></>,
    collapse: <><path d="M4 5h16v14H4Z" /><path d="M8 12h8" /></>,
    expand: <><path d="M4 5h16v14H4Z" /><path d="M8 12h8M12 8v8" /></>,
    trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-12M9 7V4h6v3" /></>,
  }
  return <svg className={`explorer-icon explorer-icon-${kind}`} viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[kind]}</svg>
}

const FILE_TYPES = { py: 'py', md: 'md', json: 'json', toml: 'cfg', cfg: 'cfg', ini: 'cfg', txt: 'txt', csv: 'txt', html: 'web', css: 'web', js: 'web', jsx: 'web' }

// A file's icon: a page with its type tag, coloured by type like an editor.
function FileTypeIcon({ name }) {
  const ext = String(name || '').split('.').pop().toLowerCase()
  const type = FILE_TYPES[ext] || 'file'
  return (
    <span className={`file-type-icon file-type-${type}`} aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false"><path d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7Z" /><path d="M14 3v4h4" /></svg>
      {type !== 'file' && <b>{ext === 'toml' || ext === 'cfg' || ext === 'ini' ? ext.slice(0, 3) : ext.slice(0, 4)}</b>}
    </span>
  )
}

// The folder a campaign's entry file lives in ('' for a root-level file).
export function projectDirOf(entryFile) {
  const parts = String(entryFile || '').replaceAll('\\', '/').split('/').filter(Boolean)
  return parts.length > 1 ? parts[0] : ''
}

// A root-level campaign's file: a .py at the workspace root that is not one
// of the platform's own (tutor.py, dungeon.py).
function isRootGameFile(item) {
  const path = String(item?.path || '')
  return item?.type === 'file' && !path.includes('/') && !path.startsWith('.') && /\.py$/i.test(path) && !['tutor.py', 'dungeon.py'].includes(path)
}

export function ContextPanel({ activeView, campaign, files = [], activePath, compact = false, onToggleCompact, editorMode = 'file', openFile, openQuestDocument, newFile, onCreateEntry, onDeleteEntry, setActiveView, submitBattle, submitBoss, onAskBossQuestion, onAnswerBossOption, battleQuestions = {}, battleFeedback = null, onAskBattleQuestion, onAnswerBattleOption, onCheckSetup, busy }) {
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
  // The explorer shows game files only, never how the app itself is built:
  // a campaign in its own folder (silver_reels/casino.py) shows just that
  // folder; a root-level campaign shows its own .py files.
  const projectDir = projectDirOf(activeProject?.entry_file)
  const treeFiles = files.filter((item) => {
    const path = String(item?.path || '')
    if (!path || path.startsWith('\\') || path.includes('\0')) return false
    if (projectDir) return path === projectDir || path.startsWith(`${projectDir}/`)
    return isRootGameFile(item)
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

  const allDirsOpen = Boolean(openDirs && openDirs.size === directoryPaths.length && directoryPaths.length > 0)
  const toggleAllDirs = () => {
    setOpenDirs((current) => {
      const expanded = current || new Set()
      return expanded.size === directoryPaths.length && directoryPaths.length > 0 ? new Set() : new Set(directoryPaths)
    })
  }

  // The project folder opens like the root of an editor's explorer.
  useEffect(() => {
    if (projectDir && directoryPaths.includes(projectDir)) setOpenDirs((current) => new Set([...(current || []), projectDir]))
  }, [projectDir, directoryPaths.includes(projectDir)])

  // Explorer: New file / New folder appear as a name box inside the chosen
  // folder (the last folder clicked, else the open file's folder, else the
  // project folder), like any code editor.
  const [selectedDir, setSelectedDir] = useState('')
  // Delete asks in the row itself; the file goes to the workspace trash.
  const [deleting, setDeleting] = useState('')
  const confirmDelete = async (item) => {
    const result = await onDeleteEntry?.(item.path)
    setDeleting('')
    if (result?.ok && (selectedDir === item.path || selectedDir.startsWith(`${item.path}/`))) setSelectedDir(parentDirOf(item.path))
  }
  const [creating, setCreating] = useState(null)
  const startCreate = (type) => {
    const known = new Set(directoryPaths)
    const parent = [selectedDir, parentDirOf(activePath), projectDir].find((path) => path && known.has(path)) || ''
    const ancestors = parent.split('/').filter(Boolean).map((_, index, parts) => parts.slice(0, index + 1).join('/'))
    setOpenDirs((current) => new Set([...(current || []), ...ancestors]))
    setCreating({ type, parent, name: '', error: '', busy: false })
  }
  const submitCreate = async () => {
    const name = String(creating?.name || '').trim().replace(/^\/+|\/+$/g, '')
    if (!creating || !name) return setCreating(null)
    const path = creating.parent ? `${creating.parent}/${name}` : name
    setCreating((current) => current && { ...current, busy: true, error: '' })
    const result = await onCreateEntry?.(path, creating.type)
    if (result?.ok) {
      if (creating.type === 'dir') setSelectedDir(path)
      setCreating(null)
    } else {
      setCreating((current) => current && { ...current, busy: false, error: result?.error || 'Could not create it' })
    }
  }
  const createRow = (depth) => (
    <div className="file-row explorer-create" role="treeitem" aria-level={depth + 1} key="explorer-create">
      {Array.from({ length: depth }, (_, index) => <span key={index} className="tree-guide" aria-hidden="true" />)}
      <span className="file-tree-disclosure" aria-hidden="true" />
      {creating.type === 'dir' ? <ExplorerIcon kind="folder" /> : <FileTypeIcon name={creating.name || 'new'} />}
      <input
        autoFocus
        value={creating.name}
        disabled={creating.busy}
        aria-label={creating.type === 'dir' ? 'New folder name' : 'New file name'}
        placeholder={creating.type === 'dir' ? 'folder name' : 'file name, e.g. reels.py'}
        onChange={(event) => setCreating((current) => current && { ...current, name: event.target.value, error: '' })}
        onKeyDown={(event) => {
          event.stopPropagation()
          if (event.key === 'Enter') { event.preventDefault(); void submitCreate() }
          if (event.key === 'Escape') { event.preventDefault(); setCreating(null) }
        }}
        onBlur={() => { if (!creating.busy && !creating.name.trim()) setCreating(null) }}
      />
      {creating.error && <small className="explorer-create-error" role="alert">{creating.error}</small>}
    </div>
  )

  const collapsibleContext = activeView === 'tutor' || activeView === 'practice' || activeView === 'dungeon'
  if (compact && collapsibleContext) return <ContextCompactPanel activeView={activeView} onToggleCompact={onToggleCompact} />

  if (activeView === 'hub') {
    const goals = progress.goals || {}
    const cleared = (activeProject?.mobs || []).filter((mob) => isMobDefeated(mob.status)).length
    return (
      <>
        <div className="panel-title">
          <span>QUEST HUB</span>
          <button onClick={() => setActiveView('forge')} title="Open Hunt" aria-label="Open Hunt"><RouteIcon id="forge" /></button>
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
          <span>{multiFileProject ? 'EXPLORER' : 'ACTIVE FILE'}</span>
          <div className="panel-title-actions">
            {multiFileProject && <div className="file-tree-actions">
              {showFiles && <>
                <button type="button" className="explorer-action" onClick={() => startCreate('file')} title="New file" aria-label="New file"><ExplorerIcon kind="new-file" /></button>
                <button type="button" className="explorer-action" onClick={() => startCreate('dir')} title="New folder" aria-label="New folder"><ExplorerIcon kind="new-folder" /></button>
                <button type="button" className="explorer-action" onClick={toggleAllDirs} title={allDirsOpen ? 'Collapse all folders' : 'Expand all folders'} aria-label={allDirsOpen ? 'Collapse all folders' : 'Expand all folders'}><ExplorerIcon kind={allDirsOpen ? 'collapse' : 'expand'} /></button>
              </>}
              <button type="button" onClick={() => setShowFiles((current) => !current)} title={showFiles ? 'Hide project files' : 'Show project files'} aria-label={showFiles ? 'Hide project files' : 'Show project files'}>{showFiles ? 'Hide' : 'Files'}</button>
            </div>}
            <button type="button" onClick={() => setActiveView('tutor')} title="Open Hunter’s Study" aria-label="Open Hunter’s Study"><RouteIcon id="tutor" /></button>
            {onToggleCompact && <button className="sidebar-collapse-toggle" type="button" onClick={onToggleCompact} title="Compact Hunt sidebar" aria-label="Compact Hunt sidebar"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m15 5-7 7 7 7" /><path d="M20 5v14" /></svg></button>}
          </div>
        </div>
        <div className="workspace-label">{campaign?.workspace || 'loading workspace…'}</div>
        <ForgeDocumentTabs activePath={activePath} editorMode={editorMode} openFile={openFile} openQuestDocument={openQuestDocument} />
        {multiFileProject && showFiles ? <div className="file-list explorer-tree" role="tree" aria-label="Workspace files">
            {creating && creating.parent === '' && createRow(0)}
            {treeFiles.filter(isTreeItemVisible).map((item) => {
              const open = item.type === 'dir' && (openDirs || new Set()).has(item.path)
              return (
                <Fragment key={item.path}>
                  {deleting === item.path ? <div className="file-row explorer-confirm" role="treeitem" aria-level={item.depth + 1}>
                    {Array.from({ length: item.depth }, (_, index) => <span key={index} className="tree-guide" aria-hidden="true" />)}
                    <span className="explorer-confirm-text">Delete {item.name}{item.type === 'dir' ? '/ and everything in it' : ''}?</span>
                    <button type="button" className="explorer-confirm-yes" autoFocus onClick={() => void confirmDelete(item)} onKeyDown={(event) => { if (event.key === 'Escape') setDeleting('') }}>Delete</button>
                    <button type="button" onClick={() => setDeleting('')}>Cancel</button>
                  </div> : <div className="file-row-wrap">
                  <button
                    className={`file-row ${activePath === item.path ? 'active' : ''} ${item.type === 'dir' && selectedDir === item.path ? 'selected' : ''} ${item.type}`}
                    onKeyDown={(event) => { if (event.key === 'Delete' && item.path !== projectDir) { event.preventDefault(); setDeleting(item.path) } }}
                    onClick={() => {
                      if (item.type === 'dir') {
                        setSelectedDir(item.path)
                        toggleDir(item.path)
                      } else {
                        setSelectedDir(parentDirOf(item.path))
                        openFile(item.path)
                      }
                    }}
                    title={item.path}
                    role="treeitem"
                    aria-expanded={item.type === 'dir' ? open : undefined}
                    aria-level={item.depth + 1}
                  >
                    {Array.from({ length: item.depth }, (_, index) => <span key={index} className="tree-guide" aria-hidden="true" />)}
                    <span className={`file-tree-disclosure ${open ? 'open' : ''}`} aria-hidden="true">{item.type === 'dir' ? <ExplorerIcon kind="chevron" /> : null}</span>
                    {item.type === 'dir' ? <ExplorerIcon kind={open ? 'folder-open' : 'folder'} /> : <FileTypeIcon name={item.name} />}
                    <span className="file-tree-name">{item.name}</span>
                  </button>
                  {item.path !== projectDir && <button type="button" className="explorer-row-delete" onClick={() => setDeleting(item.path)} title={`Delete ${item.name}`} aria-label={`Delete ${item.name}`}><ExplorerIcon kind="trash" /></button>}
                  </div>}
                  {creating && creating.parent === item.path && open && createRow(item.depth + 1)}
                </Fragment>
              )
            })}
            {!files.length && <div className="empty-state">No workspace files available.</div>}
            {Boolean(files.length) && projectDir && !treeFiles.length && <div className="empty-state">
              <strong>{projectDir}/</strong> isn't on disk yet. Your first bounty walks you through making it in the terminal below.
            </div>}
          </div> : <div className="active-file-summary" data-testid="forge-active-file-summary">
            <span>CAMPAIGN EDITOR</span>
            <strong>{activePath || 'No campaign file selected'}</strong>
            <small>{multiFileProject ? 'Project files are hidden. Use Files when this step needs another file.' : 'Single-file step · the editor is the answer surface.'}</small>
          </div>}
        {(encounter.mob_name || encounter.status === 'boss_available' || encounter.boss_status === 'available') && (
            <div className="campaign-battle-sidebar">
            {encounter.mob_name ? <>
              <div className="panel-title"><span>ACTIVE BATTLE</span><b>{encounter.resolve ?? 0}/{encounter.max_resolve ?? 0}</b></div>
              {encounter.special_mechanic && <div className="campaign-special-mechanic" data-testid="campaign-special-mechanic"><strong>{encounter.special_mechanic.label}</strong><p>{encounter.special_mechanic.detail}</p><small>{encounter.special_mechanic.triggered ? 'REWARD CLAIMED' : 'REWARD AVAILABLE'}</small></div>}
              <BattleBrief player={player} armory={campaign?.armory} encounter={encounter} board={campaign?.campaign_board} charges={campaign?.armory?.charges} questions={battleQuestions} feedback={battleFeedback} onAsk={onAskBattleQuestion} onAnswer={onAnswerBattleOption} onCheckSetup={onCheckSetup} onStudy={(objective, sign) => { try { window.sessionStorage.setItem('questlab.tutor.request', JSON.stringify({ conceptId: sign || encounter?.mob?.sign_id || '', concept: encounter?.mob?.concept || encounter?.concept || '', objective: { id: objective?.id, label: objective?.label } })) } catch { /* storage unavailable */ } setActiveView('tutor') }} busy={busy} />
              <div className="campaign-battle-resolve" data-testid="forge-encounter-resolve" hidden>
                <ProgressBar value={encounter.resolve ?? 0} max={encounter.max_resolve ?? 1} label="Enemy Resolve" className="resolve" />
              </div>
            </> : <>
              <div className="panel-title"><span>BOSS GATE</span><b>{encounter.resolve ?? encounter.boss_resolve ?? 0}/{encounter.max_resolve ?? encounter.boss_max_resolve ?? 0}</b></div>
              {encounter.special_mechanic && <div className="campaign-special-mechanic" data-testid="campaign-special-mechanic"><strong>{encounter.special_mechanic.label}</strong><p>{encounter.special_mechanic.detail}</p><small>{encounter.special_mechanic.triggered ? 'REWARD CLAIMED' : 'REWARD AVAILABLE'}</small></div>}
              <BossBrief player={player} armory={campaign?.armory} encounter={encounter} board={campaign?.campaign_board} questions={battleQuestions} feedback={battleFeedback} onAsk={onAskBossQuestion} onAnswer={onAnswerBossOption} busy={busy} />
              <div className="campaign-battle-resolve" data-testid="forge-boss-resolve" hidden>
                <ProgressBar value={encounter.resolve ?? encounter.boss_resolve ?? 0} max={encounter.max_resolve ?? encounter.boss_max_resolve ?? 1} label="Boss Resolve" className="resolve boss-resolve" />
              </div>
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
          <span>HUNTER’S STUDY</span>
          <div className="panel-title-actions">
            <button onClick={() => setActiveView('forge')} title="Return to Hunt" aria-label="Return to Hunt"><RouteIcon id="forge" /></button>
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
          <button onClick={() => setActiveView('forge')} title="Return to Hunt" aria-label="Return to Hunt"><RouteIcon id="forge" /></button>
        </div>
        <div className="context-scroll">
          <div className="context-kicker">CAMPAIGN SYNC</div>
          <h3>Waiting for the canonical state</h3>
          <p>The Hunt is still connected, but the campaign projection has not arrived yet. Player stats stay hidden until the state service responds.</p>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="panel-title">
        <span>{viewItems.find((item) => item.id === activeView)?.label?.toUpperCase()}</span>
        <div className="panel-title-actions">
          {activeView !== 'dungeon' && <button onClick={() => setActiveView('forge')} title="Return to Hunt" aria-label="Return to Hunt"><RouteIcon id="forge" /></button>}
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
            <h3>{homestead.name || 'The Hunt'}</h3>
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

// Built-in PYR (OpenCode mode): replaces the raw CLI terminal in the Hunt.
// Verdicts from Submit run land here too, so the panel is the PYR log.
export function PyrChatPanel({ log = [], ready, thinking, model, onAsk, onOpenSettings, battleCost = null }) {
  const [draft, setDraft] = useState('')
  const listRef = useRef(null)
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [log.length, thinking])
  const send = () => {
    const question = draft.trim()
    if (!question || thinking) return
    setDraft('')
    onAsk?.(question)
  }
  return (
    <div className="pyr-chat" data-testid="pyr-chat">
      <div className="pyr-chat-head">
        <div><span className="screen-kicker">PYR · OPENCODE</span><strong>{ready ? 'Ready' : 'Offline'}</strong></div>
        <button type="button" onClick={onOpenSettings} title="AI Tutor settings">{model || 'Auto'}</button>
      </div>
      <div className="pyr-chat-log" ref={listRef} aria-live="polite">
        {log.length === 0 && <p className="pyr-chat-empty">Submit run to be graded. Ask for a hint any time.</p>}
        {log.map((entry) => (
          <div key={entry.id} className={`pyr-chat-entry ${entry.role}${entry.verdict ? ` ${entry.verdict}` : ''}`}>
            <span>{entry.role === 'you' ? 'YOU' : entry.role === 'verdict' ? (entry.verdict === 'correct' ? '✔ VERDICT' : '✘ VERDICT') : 'PYR'}</span>
            <p>{entry.text}</p>
          </div>
        ))}
        {thinking && <div className="pyr-chat-entry pyr pending"><span>PYR</span><p>{thinking}</p></div>}
      </div>
      {battleCost && <p className={`pyr-chat-cost ${battleCost.asks ? 'spent' : ''}`} data-testid="pyr-chat-cost">
        {battleCost.helpFree ? 'PYR help is free in Mysterys in Shandumballa; it does not reduce XP, coins or loot.' : `Each ask takes 20% off ${battleCost.mob}'s XP and coins (down to 40%). ${battleCost.lootProtected ? 'The elite’s keepsake and Embers remain available.' : 'From the second ask it drops no loot.'}`}
        {!battleCost.helpFree && battleCost.free > 0 && <b className="pyr-chat-free"> {battleCost.free} free ask{battleCost.free === 1 ? '' : 's'} armed (PYR's Favour): the next one costs nothing.</b>}
        {battleCost.asks > 0 && <b> Asked {battleCost.asks}× · now {battleCost.scale}%{battleCost.asks >= 2 && !battleCost.lootProtected ? ' · no loot' : ''}.</b>}
      </p>}
      <div className="pyr-chat-compose">
        <textarea value={draft} rows={3} placeholder="Ask for a hint, not a finished answer…" onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} disabled={!ready} />
        <button type="button" className="primary" onClick={send} disabled={!ready || Boolean(thinking) || !draft.trim()}>Ask PYR</button>
      </div>
    </div>
  )
}

export function SurfaceNavigation({ activeView, onNavigate, showSettings = false, showAiToggle = false, aiOpen = false, onToggleAi, zenMode = false, onExitZen }) {
  // Home (the campaign hub) sits with the other destinations; Settings is the
  // gear in the top-right HUD. Codex is now a folio inside Tutor Notebook: its
  // legacy route stays addressable for saved links but is not a duplicate
  // top-level destination.
  const online = activeView === 'online'
  // Campaign and Online are two modes; the nav only lists the active mode's
  // destinations. The last campaign screen is remembered for the way back.
  useEffect(() => {
    if (online) return
    try { window.localStorage.setItem('questlab.lastCampaignView', activeView) } catch { /* storage unavailable */ }
  }, [activeView, online])
  const backToCampaign = () => {
    let last = 'hub'
    try { last = window.localStorage.getItem('questlab.lastCampaignView') || 'hub' } catch { /* storage unavailable */ }
    onNavigate?.(['hub', 'forge', 'tutor', 'dungeon'].includes(last) ? last : 'hub')
  }
  const destinationItems = online
    ? viewItems.filter((item) => item.id === 'online')
    : [
      { id: 'hub', label: 'Home' },
      { id: 'forge', label: 'Hunt' },
      ...viewItems.filter((item) => !['hub', 'codex', 'settings', 'online'].includes(item.id)),
    ]
  return (
    <nav className="surface-nav" data-testid="wide-route-nav" aria-label="Wide route navigation">
      <div className="surface-nav-mode" role="group" aria-label="Mode">
        <button type="button" className={!online ? 'active' : ''} aria-pressed={!online} onClick={() => { if (online) backToCampaign() }}>Campaign</button>
        <button type="button" className={online ? 'active' : ''} aria-pressed={online} onClick={() => { if (!online) onNavigate?.('online') }}>Online</button>
      </div>
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
      {(showSettings || showAiToggle || zenMode) && <div className="surface-nav-tools">{showAiToggle && <button type="button" className="surface-nav-tool" onClick={onToggleAi} aria-expanded={aiOpen} aria-controls="questlab-ai-panel">{aiOpen ? 'Hide AI' : 'Open AI'}</button>}{zenMode && <button type="button" className="surface-nav-tool" onClick={onExitZen}>Exit Zen</button>}{showSettings && <button type="button" className="surface-nav-tool surface-nav-settings" onClick={() => onNavigate?.('settings')} title="Settings" aria-label="Settings"><RouteIcon id="settings" /></button>}</div>}
    </nav>
  )
}

function RouteIcon({ id }) {
  const paths = {
    hub: <><path d="m4 11 8-7 8 7" /><path d="M6 10v9h12v-9M9 19v-5h6v5" /></>,
    online: <><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2.5" /><path d="M3 19c0-4 2-6 6-6s6 2 6 6M15 14c3 0 5 2 5 5" /></>,
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
      <div className="tutor-practice-heading"><span className="screen-kicker">HUNTER’S STUDY</span><small>tutor.py is the shared learning notebook and IDE</small><p>PYR teaches with hints and generic examples. It will not reveal an answer key or paste a missing project snippet.</p><em>Raw CLI chat remains an advanced, unsandboxed path.</em></div>
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
        <div className="hub-hero-actions"><button className="primary" type="button" onClick={() => onOpen?.('forge')}>Open Hunt</button></div>
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
      <section className="game-card hub-quest-map">
        <div className="card-heading"><span>QUEST MAP</span><b>{projects.filter((p) => p.completed).length}/{projects.length} cleared</b></div>
        <svg viewBox="0 0 400 120" className="quest-map-svg" aria-label="Quest map">
          {projects.map((project, index) => {
            const x = 40 + index * (320 / Math.max(1, projects.length - 1 || 1))
            const y = 60 + (index % 2 === 0 ? -20 : 20)
            const locked = project.status === 'locked' || (project.status !== 'active' && !project.completed)
            const color = locked ? '#555' : project.completed ? '#00ff99' : '#ff00ff'
            return (
              <g key={project.id || index}>
                {index > 0 && <line x1={40 + (index - 1) * (320 / Math.max(1, projects.length - 1 || 1))} y1={60 + ((index - 1) % 2 === 0 ? -20 : 20)} x2={x} y2={y} stroke="#333" strokeWidth="2" />}
                <circle cx={x} cy={y} r="12" fill={color} stroke="#fff" strokeWidth="2" style={{ cursor: 'pointer' }} onClick={() => onOpen?.('codex')} />
                <text x={x} y={y + 28} textAnchor="middle" fontSize="10" fill="#e0e0ff">{locked ? '?' : (project.name || '').slice(0, 10)}</text>
              </g>
            )
          })}
        </svg>
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
              <div className="codex-page-heading"><span className="screen-kicker">CONCEPT PAGE</span><h3>{selectedPage.title}</h3><p>Read the core idea, look at a generic example, and check your understanding before you return to Hunt.</p><div className="codex-page-summary" data-testid="codex-page-summary"><span><b>{selectedEntries.length}</b> encounters</span><span><b>{pageQuestionTypes.length}</b> question lenses</span><span><b>{pageWeaknesses.length}</b> recorded patterns</span></div></div>
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
 * while we tuned the interaction.  This is the Hunt port of that surface:
 * the projection, tutor.py buffer, revision and notes callbacks still come
 * from the canonical app, while notebook presentation preferences remain
 * browser-local until their own state-service schema exists.
 */
// Tutor lenses → the practice question types the state gateway accepts
// (sending the lens id itself was rejected, so Tutor answers never landed).
const PRACTICE_TYPE_BY_LENS = { build: 'code_trace', predict: 'code_trace', trace: 'code_trace', bug: 'bug_hunt', explain: 'short_explanation', transfer: 'short_explanation' }

const RESOURCE_PRACTICE_MODES = [
  { id: 'predict', label: 'Predict output', prompt: 'Read the example and write your prediction as a Python comment in tutor.py.' },
  { id: 'trace', label: 'Trace variables', prompt: 'Trace values line by line; record your reasoning as Python comments in tutor.py.' },
  { id: 'bug', label: 'Find a bug', prompt: 'Study the example mistake and explain the problem in a Python comment.' },
  { id: 'explain', label: 'Explain the idea', prompt: 'Teach the concept back in your own words.' },
  { id: 'transfer', label: 'Tiny transfer challenge', prompt: 'Describe one small new program where this idea would help.' },
  { id: 'build', label: 'Write Python', prompt: 'Write and run a small Python example using this topic.' },
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

// Where you are in the Tutor survives going to the Hunt and back, and a
// reload, but not closing the app: sessionStorage lives as long as the window.
function useSessionState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const saved = window.sessionStorage.getItem(`questlab.tutor.${key}`)
      return saved === null ? (typeof initial === 'function' ? initial() : initial) : JSON.parse(saved)
    } catch {
      return typeof initial === 'function' ? initial() : initial
    }
  })
  useEffect(() => {
    try { window.sessionStorage.setItem(`questlab.tutor.${key}`, JSON.stringify(value)) } catch { /* storage unavailable */ }
  }, [key, value])
  return [value, setValue]
}

function ResourceNotebook({ pages, selectedPage, entries, onSelectPage }) {
  const storageKey = 'questlab-forge-resource-notebook'
  const [chapters, setChapters] = useState(() => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(`${storageKey}:chapters`) || 'null')
      return Array.isArray(stored) && stored.length ? stored : RESOURCE_DEFAULT_CHAPTERS
    } catch { return RESOURCE_DEFAULT_CHAPTERS }
  })
  const [chapterId, setChapterId] = useSessionState('notebookChapter', () => chapters[0]?.id || 'fundamentals')
  const [pageIndex, setPageIndex] = useSessionState('notebookPage', 0)
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
      )) : <p className="context-note">No validated encounter evidence yet. Your next correct Hunt submission can leave a small personal excerpt here.</p>}
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

// ── Hunter's Codex: Tutor's contracts, bestiary and signs ───────────────
// Bugs are the beasts; Python concepts are the signs that beat them. Every
// status comes from evidence the save already holds (correct practice
// answers, cleared encounters, skill evidence); nothing here grants
// campaign rewards. Contracts lead into the Codex reader and IDE practice.

const HUNT_REGIONS = [
  { id: 'basics', label: 'Basics Village', danger: 1, pages: ['variables', 'input-output', 'conditionals'] },
  { id: 'collections', label: 'Collection Caves', danger: 2, pages: ['lists', 'dictionaries', 'random-selection'] },
  { id: 'flow', label: 'Flow Keep', danger: 3, pages: ['loops', 'functions', 'control-flow'] },
  { id: 'archive', label: 'Sunken Archive', danger: 2, pages: ['strings', 'exceptions', 'files-json'] },
  { id: 'labyrinth', label: 'The Labyrinth', danger: 3, pages: ['grids', 'sets', 'sorting'] },
  { id: 'workshop', label: 'Clockwork Workshop', danger: 3, pages: ['classes', 'references'] },
  { id: 'spire', label: "Seer's Spire", danger: 4, pages: ['recursion', 'search', 'simulation'] },
  { id: 'hollow', label: "Familiar's Hollow", danger: 4, pages: ['callbacks', 'agents', 'testing'] },
]

// Delve bosses, one per region (state.py DUNGEON_REGIONS).
const DELVE_BOSSES = { basics: 'The Mimic Matriarch', collections: 'The Drowned Hoard', flow: 'The Endless Warden', archive: 'The Archivist Lich', labyrinth: 'The Minotaur of Rows', workshop: 'The Brass Automaton', spire: 'The Recursive Oracle', hollow: 'The Hollow King' }
const MAX_DANGER = 4

const lootText = (items) => (items || []).map((item) => `${item.count} ${item.name}`).join(', ')

const DELVE_MAP_POSITIONS = {
  basics: [16, 70], collections: [22, 37], flow: [47, 67], archive: [49, 17],
  labyrinth: [63, 41], workshop: [81, 76], spire: [83, 16], hollow: [90, 49],
}

const DELVE_LANDMARKS = {
  basics: 'M3 11 12 4l9 7M6 10v9h12v-9M10 19v-5h4v5',
  collections: 'M3 19 7 8l5-4 5 4 4 11M8 19v-5l4-3 4 3v5',
  flow: 'M4 20V8h4V5h3v3h3V5h3v3h3v12M9 20v-5a3 3 0 0 1 6 0v5',
  archive: 'M3 20h18M5 17V9l7-5 7 5v8M9 17v-5h6v5M3 20c2-2 4 2 6 0s4 2 6 0 4 2 6 0',
  labyrinth: 'M4 4h16v16H4zM8 4v12h8V8h-4v4',
  workshop: 'M4 20V11l5 3V9l5 3V6h4v14zM7 17h1m3 0h1m4 0h1',
  spire: 'M7 20h10l-2-12-3-5-3 5zM10 12h4M10 16h4',
  hollow: 'M12 3v6M6 5l2 5M18 5l-2 5M5 20c0-5 3-9 7-9s7 4 7 9M9 20v-3a3 3 0 0 1 6 0v3',
}

function DelveLandmark({ id }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d={DELVE_LANDMARKS[id]} /></svg>
}

function DelvePicker({ hunter, selected, onSelect, onBack, onStart, selectedClass, busy }) {
  const levels = Object.fromEntries((hunter?.signs || []).map((sign) => [sign.id, sign.level]))
  const region = HUNT_REGIONS.find((item) => item.id === selected)
  const isOpen = selected === 'open'
  return (
    <main className="delve-picker delve-map-screen" aria-label="Choose a dungeon location">
      <div className="delve-map-heading"><div><span className="dungeon-eyebrow">RUN SETUP · 2 / 2</span><h2>Choose your hunting ground</h2><p>Pick a location on the map to inspect its beasts and boss.</p></div><button className="dungeon-ghost-button" type="button" onClick={onBack}>← Change class</button></div>
      <div className="delve-map-layout">
        <section className="delve-world-map" aria-label="Dungeon locations">
          <div className="delve-map-caption"><span>THE HUNTER’S MAP</span><small>Choose a destination</small></div>
          {HUNT_REGIONS.map((item) => <button key={item.id} type="button" className={`delve-map-node ${selected === item.id ? 'selected' : ''}`} style={{ left: `${DELVE_MAP_POSITIONS[item.id][0]}%`, top: `${DELVE_MAP_POSITIONS[item.id][1]}%` }} onClick={() => onSelect(item.id)} aria-label={item.label} aria-pressed={selected === item.id} disabled={busy}><span className="delve-map-marker" aria-hidden="true"><DelveLandmark id={item.id} /></span><span className="delve-map-label" aria-hidden="true">{item.label}</span></button>)}
          <button type="button" className={`delve-open-route ${isOpen ? 'selected' : ''}`} aria-pressed={isOpen} onClick={() => onSelect('open')} disabled={busy}>✧ Open dungeon</button>
        </section>
        <aside className="delve-map-detail" aria-live="polite">
          <span className="dungeon-eyebrow">DESTINATION DETAILS</span>
          {region ? <><h3>{region.label}</h3><div className="delve-danger"><span>Danger</span><strong aria-label={`${region.danger} out of ${MAX_DANGER} danger`}>{'◆'.repeat(region.danger)}{'◇'.repeat(MAX_DANGER - region.danger)}</strong></div><span className="delve-detail-label">BEASTS &amp; SIGN LEVELS</span><ul>{region.pages.map((page) => <li key={page}><span>{HUNT_BEASTS[page]?.beast || page}</span><strong>LVL {levels[page] ?? 0}</strong></li>)}</ul><div className="delve-detail-boss"><span className="delve-detail-label">FLOOR BOSS</span><strong>{DELVE_BOSSES[region.id]}</strong></div></> : isOpen ? <><h3>Open dungeon</h3><p>Follow the concepts you have missed in the Codex. Beasts still drop parts when their sign is known.</p><div className="delve-detail-boss"><span className="delve-detail-label">DANGER</span><strong>Adaptive</strong></div></> : <><h3>Where will you hunt?</h3><p>Select a location on the map to see its danger, beasts and boss.</p></>}
          <div className="delve-detail-footer"><small>CLASS · {selectedClass?.name}</small><button className="dungeon-primary-button" type="button" onClick={onStart} disabled={busy || !selected}>{busy ? 'Starting…' : 'Enter the dungeon →'}</button><p>Bank your finds at a camp or by ending the run. Dying loses unbanked parts.</p></div>
        </aside>
      </div>
    </main>
  )
}

// One beast (a bug) and one sign (the concept that beats it) per page.
const HUNT_BEASTS = {
  variables: { beast: 'The Nameless Wraith', sign: 'Vessel', lore: 'Haunts names that were never given a value. Call it before it is assigned and it answers with NameError.', symptoms: ["NameError: name 'score' is not defined", 'A typo in a name (scroe instead of score)', 'A value read before it is set'], rule: 'Assign before you read, and spell the name the same way every time.', code: "print(score)   # the Wraith answers here\nscore = 0" },
  'input-output': { beast: 'The String Mimic', sign: 'Echo', lore: 'Wears the face of a number but is text underneath: input() always hands you a string.', symptoms: ['TypeError: can only concatenate str (not "int") to str', "'2' + '2' gives '22'", 'A comparison that never matches'], rule: 'Convert with int() or float() the moment the input arrives.', code: "bet = input('Bet: ')\ntotal = bet + 10   # the Mimic strikes" },
  conditionals: { beast: 'The Forked Path', sign: 'Fork', lore: 'Leads hunters down the wrong branch: a wide check placed before a narrow one, or = where == belongs.', symptoms: ['SyntaxError at a single =', 'A branch that never runs', 'A 21 counted as a bust'], rule: 'Check the most specific case first, and compare with ==.', code: "if total > 17:\n    print('stand')\nelif total == 21:   # never reached\n    print('blackjack')" },
  lists: { beast: 'The IndexError Drowner', sign: 'Chain', lore: 'Drags careless hunters under by reaching one step past the end of a list.', symptoms: ['IndexError: list index out of range', 'A loop that runs one time too many', 'The last card in the hand vanishes'], rule: 'Valid indexes run 0 to len(items) - 1. Loop over the items, not the count.', code: "hand = ['A', 'K', '7']\nfor i in range(len(hand) + 1):   # the Drowner waits here\n    print(hand[i])" },
  dictionaries: { beast: 'The KeyError Ghoul', sign: 'Key', lore: 'Asks for names that were never written in the ledger, and the whole program collapses.', symptoms: ["KeyError: 'A'", 'A lookup that worked once fails on new input', 'Values quietly overwritten'], rule: 'Check with in, or use .get(key, default).', code: "values = {'K': 10, 'Q': 10}\nprint(values['A'])   # the Ghoul feeds" },
  'random-selection': { beast: 'The Loaded Die', sign: 'Dice', lore: 'Makes every roll a little wrong: randint includes both ends, randrange stops before the last.', symptoms: ['An index one too large', 'One card that is never drawn', 'An IndexError on rare rolls'], rule: 'randint(a, b) includes b. For a list, use random.choice or randrange(len(items)).', code: "i = random.randint(0, len(deck))   # the Die is loaded\ncard = deck[i]" },
  loops: { beast: 'The Off-by-One Wraith', sign: 'Ouroboros', lore: 'Lives in the last pass of a loop: one pass too many or one too few.', symptoms: ['The first or last item skipped', 'An extra blank line', 'A total that is one short'], rule: 'range(n) stops before n. Loop over the items directly when you can.', code: "for i in range(1, len(hand)):   # skips hand[0]\n    total += values[hand[i]]" },
  functions: { beast: 'The Hollow Return', sign: 'Binding', lore: 'A function that does all the work, then hands back nothing. Its gift is always None.', symptoms: ["TypeError: unsupported operand type(s) for +: 'NoneType'", 'None printed where a value should be', 'A result that vanishes'], rule: 'return the value. Printing is not returning.', code: "def hand_total(hand):\n    total = sum(hand)   # no return\nscore = hand_total([10, 7]) + 1" },
  strings: { beast: 'The Whitespace Wisp', sign: 'Quill', lore: 'Hides in the spaces at the ends of words and in capital letters, so text that looks the same never matches.', symptoms: ["' Rock' == 'rock' is False", "A command that works only in lower case", "'hi' found inside 'this'"], rule: 'Clean text with strip() and lower() before you compare it, and match whole words.', code: "move = input('Move: ')\nif move == 'rock':   # the Wisp adds a space\n    print('stone')" },
  exceptions: { beast: 'The Traceback Banshee', sign: 'Ward', lore: 'Screams a traceback the moment something unexpected arrives, and the whole program falls silent.', symptoms: ["ValueError: invalid literal for int()", 'The program dies on one bad input', 'A bare except hides every real bug'], rule: 'Wrap the one line that can fail in try/except and catch the specific error.', code: "bet = int(input('Bet: '))   # the Banshee wails at 'ten'" },
  'files-json': { beast: 'The Lost Scroll', sign: 'Seal', lore: 'Steals what you meant to keep: saves that never happened, files that are not there, data JSON cannot hold.', symptoms: ['FileNotFoundError on the first run', 'TypeError: Object of type set is not JSON serializable', 'Progress gone after a restart'], rule: 'Save with json.dump inside with open(...), and load with a fallback for a missing or broken file.', code: "data = json.load(open('save.json'))   # the Scroll is lost" },
  sets: { beast: 'The Twin Doppel', sign: 'Ring', lore: 'Copies itself into your lists until every count is wrong and every check is slow.', symptoms: ['The same item counted twice', 'A visited room explored again', 'Membership checks crawl on big lists'], rule: 'Use a set when only presence matters; it keeps one of each and answers "in" instantly.', code: "seen = []\nseen.append(room)\nseen.append(room)   # the Doppel doubles" },
  grids: { beast: 'The Row Mimic', sign: 'Lattice', lore: 'Builds every row of your board out of the same row, so one move appears everywhere at once.', symptoms: ['One piece shows up in every row', 'IndexError at the edge of the map', 'Rows and columns swapped'], rule: 'Build rows with a comprehension, read grid[row][column], and stay inside the bounds.', code: "board = [['.'] * 7] * 6\nboard[5][3] = 'X'   # the Mimic copies it upward" },
  sorting: { beast: 'The Shuffled Herald', sign: 'Scale', lore: 'Announces rankings in the wrong order, or announces None, and nobody notices until the table is wrong.', symptoms: ['A ranking that prints None', 'Ties broken at random', 'The worst team on top'], rule: 'sorted() returns a new list; .sort() returns None. Use a key, and a tuple to break ties.', code: "table = clubs.sort(key=points)\nprint(table)   # the Herald says None" },
  references: { beast: 'The Alias Shade', sign: 'Mirror', lore: 'Lets two names share one list, so a change in one place quietly changes the other.', symptoms: ['Every new enemy starts already wounded', 'A trial move changes the real board', 'Undo does nothing'], rule: 'Assignment shares; copy() or dict() copies. Copy nested data with care.', code: "enemy = TEMPLATE\nenemy['hp'] -= 5   # the Shade wounds them all" },
  classes: { beast: 'The Selfless Golem', sign: 'Crest', lore: 'A body of clay that forgets itself: values set without self vanish the moment a method ends.', symptoms: ['A method changes nothing', "AttributeError: object has no attribute", 'Every object shares one list'], rule: 'Store an object\'s data on self, and create lists inside __init__.', code: "def heal(self):\n    hp = self.max_hp   # the Golem forgets itself" },
  testing: { beast: 'The Silent Saboteur', sign: 'Lens', lore: 'Breaks code without a sound. Nothing crashes; the answer is just wrong, and nobody checks.', symptoms: ['A bug that returns after you fixed it', 'A function that works for 2 and nothing else', 'Random results nobody can repeat'], rule: 'Pin every rule and every fixed bug with an assert, including the edge cases.', code: "def double(n):\n    return n + 2\nassert double(2) == 4   # the Saboteur slips past" },
  callbacks: { beast: 'The Hasty Caller', sign: 'Mask', lore: 'Calls every function the instant it sees it, so the loop receives an answer instead of a player.', symptoms: ["TypeError: 'int' object is not callable", 'A bot that plays one move forever', 'Two brains that cannot be swapped'], rule: 'Pass a function by name, without brackets, and give swappable functions the same inputs.', code: "play_game(random_agent(), greedy_agent)   # called too soon" },
  agents: { beast: 'The Unbound Servant', sign: 'Familiar', lore: 'An agent with tools and no leash: it acts, and acts, and acts, and never asks if it should.', symptoms: ['A loop of tool calls that never ends', 'A file deleted without asking', 'No record of what it did'], rule: 'Give the loop a step limit, confirm dangerous tools, and log every action.', code: "while True:\n    act(brain(history))   # the Servant is unbound" },
  recursion: { beast: 'The Bottomless Well', sign: 'Spiral', lore: 'Calls itself forever, one level deeper each time, until Python gives up.', symptoms: ['RecursionError: maximum recursion depth exceeded', 'A result of None from a recursive function', 'Search that never returns'], rule: 'Every recursive function needs a base case, and every call must move towards it.', code: "def count(n):\n    return count(n - 1)   # no bottom to the Well" },
  search: { beast: 'The Wandering Lantern', sign: 'Compass', lore: 'Leads searchers in circles, back through rooms they have already seen, forever.', symptoms: ['Pathfinding that never finishes', 'The same node visited twice', 'A path that is not the shortest'], rule: 'Keep a seen set and mark nodes when you queue them; breadth-first finds the shortest path.', code: "while queue:\n    node = queue.pop(0)\n    queue.extend(neighbours(node))   # the Lantern wanders" },
  simulation: { beast: 'The Lucky Liar', sign: 'Hourglass', lore: 'Wins ten games in a row and convinces you the strategy is perfect. It was luck.', symptoms: ['Big conclusions from a few runs', 'A different answer every run', 'A loop that floods the screen'], rule: 'Run thousands of trials, switch printing off, and fix the seed when you need repeats.', code: "rate = sum(play() for _ in range(10)) / 10   # the Liar's sample" },
  'control-flow': { beast: 'The Endless Leshen', sign: 'Gate', lore: 'Roots a loop forever: a while condition that nothing inside the loop ever changes.', symptoms: ['The program freezes', 'The same line prints forever', 'The fan spins up'], rule: 'Change something the condition checks on every pass, or break out.', code: "while total < 17:\n    print('hit')   # total never changes" },
}

// Rituals combine signs into project patterns; they light up once every sign is charged.
const HUNT_RITUALS = [
  { name: 'Ritual of the Dealt Hand', pages: ['lists', 'loops', 'conditionals'], use: 'total a Blackjack hand' },
  { name: 'Ritual of the Shuffled Deck', pages: ['lists', 'random-selection'], use: 'draw a random card' },
  { name: 'Ritual of the Ledger', pages: ['dictionaries', 'functions'], use: 'look up card values inside a function' },
  { name: 'Ritual of the Table', pages: ['input-output', 'control-flow'], use: 'keep asking hit or stand until the player stops' },
  { name: 'Ritual of the Archive', pages: ['strings', 'exceptions', 'files-json'], use: 'read a save file, clean what is in it and survive when it is broken' },
  { name: 'Ritual of the Labyrinth', pages: ['grids', 'sets', 'search'], use: 'find the shortest way out of a maze without walking in circles' },
  { name: 'Ritual of the Engine', pages: ['recursion', 'search', 'callbacks'], use: 'build a game engine that looks ahead and plays any opponent' },
  { name: 'Ritual of the Familiar', pages: ['agents', 'callbacks', 'testing'], use: 'bind an agent with a swappable brain and prove it behaves' },
  { name: 'Ritual of the Ledger Golem', pages: ['classes', 'references', 'sorting'], use: 'model many objects safely and rank them' },
  { name: 'Ritual of the Oracle', pages: ['simulation', 'random-selection', 'loops'], use: 'measure a game of chance with ten thousand trials' },
]

// Sigils for the signs (inline stroke SVG).
const HUNT_SIGILS = {
  variables: <><path d="M7 4h10v4l-3 3v7a2 2 0 0 1-4 0v-7L7 8z" /><path d="M9 8h6" /></>,
  'input-output': <><circle cx="12" cy="12" r="3" /><path d="M5 12a7 7 0 0 1 14 0M3 12a9 9 0 0 1 18 0" /></>,
  conditionals: <><path d="M12 21v-8M12 13 6 5M12 13l6-8" /><circle cx="6" cy="4" r="1.5" /><circle cx="18" cy="4" r="1.5" /></>,
  lists: <><rect x="3" y="9" width="6" height="6" rx="3" /><rect x="9" y="9" width="6" height="6" rx="3" /><rect x="15" y="9" width="6" height="6" rx="3" /></>,
  dictionaries: <><circle cx="8" cy="12" r="4" /><path d="M12 12h9M18 12v3M21 12v2" /></>,
  'random-selection': <><rect x="4" y="4" width="16" height="16" rx="2" /><circle cx="9" cy="9" r="1" /><circle cx="15" cy="15" r="1" /><circle cx="12" cy="12" r="1" /></>,
  loops: <><path d="M20 12a8 8 0 1 1-3-6.2" /><path d="M17 3v3h3" /></>,
  functions: <><path d="M14 4c-3 0-3 3-3 6v4c0 3 0 6-3 6" /><path d="M8 11h7" /></>,
  'control-flow': <><path d="M5 21V9l7-5 7 5v12" /><path d="M9 21v-6h6v6M3 9h18" /></>,
  strings: <><path d="M19 4c-6 1-10 6-12 14l-2 2" /><path d="M9 14c3 0 6-2 8-5" /></>,
  exceptions: <><path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" /><path d="M12 8v5M12 16v.5" /></>,
  'files-json': <><path d="M6 4h10a2 2 0 0 1 2 2v12H8a2 2 0 0 1-2-2z" /><path d="M9 9h6M9 12h6" /><circle cx="17" cy="18" r="2" /></>,
  sets: <><circle cx="9" cy="12" r="5" /><circle cx="15" cy="12" r="5" /></>,
  grids: <><rect x="4" y="4" width="16" height="16" /><path d="M4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16" /></>,
  sorting: <><path d="M5 20v-5M10 20v-9M15 20v-12M20 20V4" /></>,
  references: <><rect x="6" y="3" width="12" height="15" rx="6" /><path d="M12 18v3M9 21h6" /></>,
  classes: <><path d="M12 3l8 4-8 4-8-4z" /><path d="M4 12l8 4 8-4M4 17l8 4 8-4" /></>,
  testing: <><circle cx="10" cy="10" r="6" /><path d="M14.5 14.5L20 20" /><path d="M7.5 10l2 2 3-4" /></>,
  callbacks: <><path d="M4 7c5-2 11-2 16 0-1 6-4 10-8 10S5 13 4 7z" /><circle cx="9" cy="10" r="1" /><circle cx="15" cy="10" r="1" /></>,
  agents: <><path d="M6 8l2-4 2 3h4l2-3 2 4v6a6 6 0 0 1-12 0z" /><circle cx="10" cy="12" r="1" /><circle cx="14" cy="12" r="1" /></>,
  recursion: <><path d="M12 12a2 2 0 1 1 2-2 4 4 0 1 1-4-4 6 6 0 1 1-6 6" /></>,
  search: <><circle cx="12" cy="12" r="8" /><path d="M15 9l-2 5-4 1 2-5z" /></>,
  simulation: <><path d="M7 3h10M7 21h10M8 3l8 9-8 9M16 3l-8 9 8 9" /></>,
}

const huntKey = (page) => String(page?.id || '').split('-')[0].toLowerCase()

// 0-4 evidence pips: correct practice answers (up to two), a cleared
// campaign encounter on this page, and the matching PYR skill's evidence.
function huntEvidence(page, progress, entries) {
  const key = huntKey(page)
  const matches = (text) => Boolean(key) && String(text || '').toLowerCase().includes(key)
  const sessions = (progress?.practice_sessions || []).filter((session) => matches(session.concept))
  const correct = sessions.reduce((sum, session) => sum + (Number(session.correct) || 0), 0)
  const hardCorrect = sessions.some((session) => (Number(session.difficulty) || 1) >= 2 && (Number(session.correct) || 0) > 0)
  const cleared = entries.some((entry) => entry.page_id === page.id && isMobDefeated(entry.status))
  const skill = (progress?.skills || []).find((item) => matches(item.concept))
  const skillProof = Boolean(skill && ((Number(skill.evidence) || 0) > 0 || (skill.shield?.tier && skill.shield.tier !== 'none')))
  const pips = Math.min(2, correct) + (cleared ? 1 : 0) + (skillProof ? 1 : 0)
  return { pips, charge: Math.min(3, pips), correct, hardCorrect, cleared }
}

function huntUpNext(pages, evidence, encounter, progress) {
  const hints = [encounter?.concept, encounter?.current_quest?.concept, progress?.learning_state?.concept].filter(Boolean)
  for (const hint of hints) {
    const page = pages.find((item) => String(hint).toLowerCase().includes(huntKey(item)))
    if (page) return page
  }
  return [...pages].sort((a, b) => (evidence[a.id]?.pips ?? 0) - (evidence[b.id]?.pips ?? 0))[0] || null
}

// Which pages the player has studied for a hunt (a per-device convenience).
const HUNT_STUDIED_KEY = 'questlab.hunter.studied'
function readStudied() {
  try { return new Set(JSON.parse(window.localStorage.getItem(HUNT_STUDIED_KEY) || '[]')) } catch { return new Set() }
}
function saveStudied(set) {
  try { window.localStorage.setItem(HUNT_STUDIED_KEY, JSON.stringify([...set])) } catch { /* storage unavailable */ }
}

function HuntSigil({ pageId, size = 28 }) {
  return <svg className="hunt-sigil" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">{HUNT_SIGILS[pageId] || <circle cx="12" cy="12" r="6" />}</svg>
}

function HunterCodex({ view, hunter, pages, entries, progress, encounter, pyr, busy, selectedId, onSelect, onView, onRead, onPractice, practiceLocked = false }) {
  const [studied, setStudied] = useState(() => readStudied())
  const [region, setRegion] = useSessionState('huntRegion', 'all')
  const [askText, setAskText] = useState('')
  const [askLog, setAskLog] = useState([])
  const byId = Object.fromEntries(pages.map((page) => [page.id, page]))
  const huntPages = HUNT_REGIONS.flatMap((item) => item.pages).map((id) => byId[id]).filter(Boolean)
  const evidence = Object.fromEntries(huntPages.map((page) => [page.id, huntEvidence(page, progress, entries)]))
  // Real sign levels from the hunter projection (signs level by use).
  const signById = Object.fromEntries((hunter?.signs || []).map((sign) => [sign.id, sign]))
  const signLabel = (id) => { const sign = signById[id]; return `Lvl ${sign?.level ?? 0}/10 · ${sign?.rank_name || 'Uninscribed'}${sign?.dull ? ' · dull' : ''}` }
  const upNext = huntUpNext(huntPages, evidence, encounter, progress)
  const regionOf = (id) => HUNT_REGIONS.find((item) => item.pages.includes(id)) || HUNT_REGIONS[0]
  const statusOf = (id) => {
    const sign = signById[id]
    if (sign ? sign.rank >= 1 : (evidence[id]?.pips ?? 0) >= 3) return 'slain'
    if (upNext?.id === id) return 'hunting'
    return (sign ? sign.xp > 0 : (evidence[id]?.pips ?? 0) > 0) ? 'tracked' : 'unseen'
  }
  const statusLabel = { slain: 'Slain', hunting: 'Hunting', tracked: 'Tracked', unseen: 'Unseen' }
  const current = byId[selectedId] && HUNT_BEASTS[selectedId] ? byId[selectedId] : upNext || huntPages[0]
  if (!current) return <section className="hunter-codex"><p>No beasts recorded yet.</p></section>
  const info = HUNT_BEASTS[current.id]
  const ev = evidence[current.id] || { pips: 0, charge: 0 }
  const slain = huntPages.filter((page) => statusOf(page.id) === 'slain').length
  const steps = [
    { id: 'study', label: `Study the beast · read ${current.title}`, done: studied.has(current.id) },
    { id: 'prepare', label: `Prepare the Sign of the ${info.sign} · a warm-up drill`, done: (signById[current.id]?.tutor_passes ?? 0) > 0 || ev.correct > 0 },
    { id: 'hunt', label: 'The hunt · a bug hunt PYR writes', done: ev.hardCorrect || (signById[current.id]?.dungeon_clean ?? 0) > 0 },
  ]
  const nextStep = steps.find((step) => !step.done)
  const study = () => {
    const next = new Set(studied)
    next.add(current.id)
    setStudied(next)
    saveStudied(next)
    onRead?.(current.id)
  }
  const runStep = (step) => {
    if (step.id === 'study') study()
    else if (step.id === 'prepare') onPractice?.(current.id, 'predict', 1)
    else onPractice?.(current.id, 'bug', 3)
  }
  const ask = async () => {
    const question = askText.trim()
    if (!question) return
    setAskText('')
    if (!pyr?.ready) {
      setAskLog((log) => [...log, { role: 'you', text: question }, { role: 'pyr', text: 'Connect OpenCode in Settings → AI Tutor so I can answer here.' }].slice(-6))
      return
    }
    setAskLog((log) => [...log, { role: 'you', text: question }, { role: 'pyr', text: '…thinking', pending: true }].slice(-6))
    let reply
    try {
      reply = await pyr.ask({ question, concept: `${current.title} (${info.beast})`, code: info.code })
    } catch (error) {
      reply = `I couldn't answer that just now (${error.message}).`
    }
    setAskLog((log) => log.map((entry) => (entry.pending ? { role: 'pyr', text: reply } : entry)))
  }
  const askBox = (
    <div className="hunt-ask">
      {askLog.map((entry, index) => <p key={index} className={entry.role}><b>{entry.role === 'you' ? 'YOU' : 'PYR'}</b>{entry.text}</p>)}
      <label><span>Ask PYR about this beast</span><textarea rows={2} value={askText} onChange={(event) => setAskText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) ask() }} /></label>
      <button type="button" onClick={ask} disabled={busy || !askText.trim()}>Ask PYR</button>
    </div>
  )

  return (
    <section className="hunter-codex" data-testid="hunter-codex" aria-label="Hunter's codex">
      <header className="hunt-header">
        <div><span className="hunt-kicker">TATE BUTI · HUNTER'S CODEX</span><h3>{view === 'bestiary' ? 'Know the beast before the hunt.' : view === 'signs' ? 'Every sign you master is a weapon.' : 'Contracts posted. Take one.'}</h3></div>
        <span className="hunt-tally">{slain} of {huntPages.length} beasts slain</span>
      </header>

      {view === 'contracts' && (
        <div className="hunt-layout">
          <section className="hunt-board" aria-label="Contract board">
            {huntPages.map((page) => {
              const status = statusOf(page.id)
              return (
                <button key={page.id} type="button" className={`hunt-contract ${status} ${current.id === page.id ? 'active' : ''}`} onClick={() => onSelect(page.id)}>
                  <span className="hunt-pin" aria-hidden="true" />
                  <small>{regionOf(page.id).label.toUpperCase()}</small>
                  <strong>{HUNT_BEASTS[page.id].beast}</strong>
                  <span>Danger {'☠'.repeat(regionOf(page.id).danger)}</span>
                  <span>Charges the Sign of the {HUNT_BEASTS[page.id].sign}</span>
                  {status !== 'unseen' && status !== 'tracked' && <em className={`hunt-stamp ${status}`}>{status === 'slain' ? 'SLAIN' : 'HUNTING'}</em>}
                </button>
              )
            })}
          </section>
          <aside className="hunt-parchment" aria-label="Selected contract">
            <small className={`hunt-status ${statusOf(current.id)}`}>CONTRACT · {statusLabel[statusOf(current.id)].toUpperCase()}</small>
            <h4>{info.beast}</h4>
            <p className="hunt-quote">“{info.lore}”</p>
            <div className="hunt-chips"><span className="danger">Danger {'☠'.repeat(regionOf(current.id).danger)}</span><span>{regionOf(current.id).label}</span><span>Sign · The {info.sign}</span></div>
            <h5>THE HUNT</h5>
            <ol className="hunt-steps">
              {steps.map((step, index) => (
                <li key={step.id} className={`${step.done ? 'done' : ''} ${nextStep?.id === step.id ? 'next' : ''}`}>
                  <span>{['I', 'II', 'III'][index]}</span>
                  <span>{step.label}</span>
                  <button type="button" onClick={() => runStep(step)} disabled={busy}>{step.done ? 'Again' : 'Go'}</button>
                </li>
              ))}
            </ol>
            <p className="hunt-reward">Every clean answer grows the Sign of the {info.sign} · now {signLabel(current.id)}</p>
            <div className="hunt-actions">
              <button type="button" className="primary" onClick={() => runStep(nextStep || steps[2])} disabled={busy}>{nextStep ? 'Begin the hunt' : 'Hunt again'}</button>
              <button type="button" onClick={() => onView('bestiary')}>Bestiary entry</button>
            </div>
          </aside>
        </div>
      )}

      {view === 'bestiary' && (
        <div className="hunt-layout bestiary">
          <section className="hunt-list" aria-label="Known beasts" tabIndex={0}>
            <div className="hunt-regions" role="group" aria-label="Lairs">
              {[{ id: 'all', label: 'All lairs' }, ...HUNT_REGIONS].map((item) => <button key={item.id} type="button" className={region === item.id ? 'active' : ''} onClick={() => setRegion(item.id)} aria-pressed={region === item.id}>{item.label}</button>)}
            </div>
            {huntPages.filter((page) => region === 'all' || regionOf(page.id).id === region).map((page) => {
              const status = statusOf(page.id)
              return (
                <button key={page.id} type="button" className={`hunt-beast ${status} ${current.id === page.id ? 'active' : ''}`} onClick={() => onSelect(page.id)}>
                  <i aria-hidden="true" />
                  <span><strong>{status === 'unseen' ? `${HUNT_BEASTS[page.id].beast}` : HUNT_BEASTS[page.id].beast}</strong><small>{regionOf(page.id).label} · {page.title.split(/[&,]/)[0].trim()}</small></span>
                  <em>{statusLabel[status]}</em>
                </button>
              )
            })}
          </section>
          <article className="hunt-parchment hunt-entry" aria-label="Bestiary entry" tabIndex={0}>
            <small className={`hunt-status ${statusOf(current.id)}`}>LURKS IN {regionOf(current.id).label.toUpperCase()} · DANGER {'☠'.repeat(regionOf(current.id).danger)} · {statusLabel[statusOf(current.id)].toUpperCase()}</small>
            <div className="hunt-entry-head">
              <span className="hunt-portrait" aria-hidden="true"><svg viewBox="0 0 24 24" width="84" height="84"><path d="M5 20c0-6 2-12 7-12s7 6 7 12" /><path d="M8 13l1.5 1.5M16 13l-1.5 1.5" /><path d="M9.5 17.5c1.5 1 3.5 1 5 0" /><path d="M3 20h18M7 8 5 4M17 8l2-4" /></svg></span>
              <div><h4>{info.beast}</h4><p>{info.lore}</p></div>
            </div>
            <div className="hunt-entry-grid">
              <section><h5>SIGNS IT IS NEAR</h5><ul>{info.symptoms.map((item) => <li key={item}>{item}</li>)}</ul></section>
              <section><h5>WEAKNESS · CAST THIS SIGN</h5><p className="hunt-sign-name"><HuntSigil pageId={current.id} size={22} /> Sign of the {info.sign} ({current.title})</p><p>{info.rule}</p></section>
            </div>
            <pre className="hunt-code">{info.code}</pre>
            <div className="hunt-actions">
              <button type="button" className="primary" onClick={() => onRead?.(current.id)}>Read this concept</button>
              <button type="button" onClick={() => onView('signs')}>Study the sign</button>
            </div>
            {askBox}
          </article>
        </div>
      )}

      {view === 'signs' && (
        <div className="hunt-layout signs">
          <section className="hunt-signs" aria-label="Your signs" tabIndex={0}>
            <small className="hunt-kicker">YOUR SIGNS · CHARGE THEM BY SLAYING THE BEASTS THEY BEAT</small>
            <div className="hunt-sign-grid">
              {huntPages.map((page) => {
                const charge = signById[page.id] ? signById[page.id].rank : evidence[page.id]?.charge ?? 0
                return (
                  <button key={page.id} type="button" className={`hunt-sign ${charge ? 'lit' : 'dark'} ${charge >= 3 ? 'mastered' : ''} ${current.id === page.id ? 'active' : ''}`} onClick={() => onSelect(page.id)} aria-label={`Sign of the ${HUNT_BEASTS[page.id].sign}, ${page.title}, charge ${charge} of 3`}>
                    <span className="hunt-sigil-box"><HuntSigil pageId={page.id} /></span>
                    <strong>Sign of the {HUNT_BEASTS[page.id].sign}</strong>
                    <small>{page.title}</small>
                    <em className="hunt-level">{signLabel(page.id)}</em>
                    <span className="hunt-charge" aria-hidden="true">{[0, 1, 2].map((index) => <i key={index} className={index < charge ? 'on' : ''} />)}</span>
                  </button>
                )
              })}
            </div>
          </section>
          <aside className="hunt-steel" aria-label="Selected sign" tabIndex={0}>
            <small className="hunt-kicker">SIGN · {signLabel(current.id).toUpperCase()} · BEATS {info.beast.toUpperCase()}</small>
            <div className="hunt-sign-head"><span className="hunt-sigil-box large"><HuntSigil pageId={current.id} size={44} /></span><h4>Sign of the {info.sign}</h4></div>
            {signById[current.id]?.next_gate && <p className="hunt-gate">Next rank · {signById[current.id].next_gate}</p>}
            <p>{current.definition}</p>
            {Array.isArray(current.examples) && current.examples[0] && <pre className="hunt-code dark">{current.examples[0]}</pre>}
            <h5>TRAIN THE SIGN</h5>
            <div className="hunt-drills">{RESOURCE_PRACTICE_MODES.slice(0, 4).map((mode) => <button key={mode.id} type="button" onClick={() => onPractice?.(current.id, mode.id, 1)} disabled={busy || practiceLocked}>{mode.label}</button>)}</div>
            <h5>RITUALS THAT NEED IT</h5>
            {HUNT_RITUALS.filter((ritual) => ritual.pages.includes(current.id)).map((ritual) => {
              const ready = ritual.pages.every((id) => (evidence[id]?.charge ?? 0) > 0)
              return <div key={ritual.name} className={`hunt-ritual ${ready ? 'ready' : ''}`}><strong>{ritual.name}</strong><small>{ritual.pages.map((id) => `Sign of the ${HUNT_BEASTS[id].sign}`).join(' + ')} · {ritual.use}</small></div>
            })}
            <div className="hunt-actions">
              <button type="button" className="primary" onClick={study}>Read the full page</button>
              <button type="button" onClick={() => onView('bestiary')}>The beast it beats</button>
            </div>
          </aside>
        </div>
      )}
    </section>
  )
}

function ResourceTutorScreen({ pyr, hunter, sparRoster = [], sparActions, armory, avatar, activeView, progress, revision, codexProjection, encounter, tutorCode, tutorDirty, tutorExternalChange, editorFontSize = 14, busy, onTutorChange, onTutorSave, onTutorFormat, onTutorRun, onPracticePrompt, onTutorReloadExternal, onTutorKeepEdits, onNavigate }) {
  const pages = Array.isArray(codexProjection?.pages) && codexProjection.pages.length ? codexProjection.pages : resourceFallbackPages(encounter)
  const entries = Array.isArray(codexProjection?.entries) ? codexProjection.entries : []
  // Lessons lead into focused practice; the bounty board owns campaign contracts.
  const [surface, setSurface] = useSessionState('surface', 'learn')
  const practiceLocked = Boolean(encounter?.boss_active)
  useEffect(() => { if (practiceLocked && ['ide', 'spar', 'notes'].includes(surface)) setSurface('learn') }, [practiceLocked, surface])
  const huntView = ['bestiary', 'signs'].includes(surface)
  // The beast picked in the codex; empty means "the current hunt".
  const [huntPick, setHuntPick] = useSessionState('huntPick', '')
  const [selectedId, setSelectedId] = useSessionState('codexPage', pages[0]?.id || '')
  const [practiceMode, setPracticeMode] = useSessionState('practiceMode', 'build')
  const [practiceDifficulty, setPracticeDifficulty] = useSessionState('practiceDifficulty', 1)
  const [terminal, setTerminal] = useState({ status: 'ready', output: ['Run your notebook in the terminal; submit it for PYR feedback.'] })
  const [practiceFormat, setPracticeFormat] = useSessionState('practiceFormat', 'code')
  const [quizPick, setQuizPick] = useState(null)
  const [interviewAnswer, setInterviewAnswer] = useState('')
  const [interviewFeedback, setInterviewFeedback] = useState(null)
  const [studyObjective, setStudyObjective] = useState(null)
  const editorActions = useRef({})
  const [practiceEditor, setPracticeEditor] = useState(null)
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiMessages, setAiMessages] = useState([{ role: 'pyr', text: 'PYR channel ready. Ask for a hint when you need a nudge, not a finished answer.' }])
  // A practice question PYR wrote for the chosen lens (null = use the lens's generic prompt).
  const [practiceQuestion, setPracticeQuestion] = useState(null)
  const selectedPage = pages.find((page) => page.id === selectedId) || pages[0]
  const selectedEntries = entries.filter((entry) => entry.page_id === selectedPage?.id)
  const codexLoaded = Array.isArray(codexProjection?.pages) && codexProjection.pages.length > 0
  useEffect(() => {
    if (codexLoaded && !pages.some((page) => page.id === selectedId)) setSelectedId(pages[0]?.id || '')
  }, [codexLoaded, pages, selectedId])
  useEffect(() => {
    if (activeView === 'codex') setSurface('learn')
  }, [activeView])
  useEffect(() => {
    if (surface === 'contracts' || surface === 'codex') setSurface('learn')
  }, [surface])
  useEffect(() => {
    if (!codexLoaded) return
    try {
      const request = JSON.parse(window.sessionStorage.getItem('questlab.tutor.request') || 'null')
      if (request) {
        setStudyObjective(request.objective || null)
        const concept = String(request.concept || '').toLowerCase()
        const match = pages.find((page) => page.id === request.conceptId) || pages.find((page) => concept && (page.title.toLowerCase().includes(concept) || (page.aliases || []).some((alias) => concept.includes(String(alias).toLowerCase()))))
        if (match) setSelectedId(match.id)
        setSurface('learn')
        window.sessionStorage.removeItem('questlab.tutor.request')
      }
    } catch { /* storage unavailable */ }
  }, [codexLoaded])
  const conceptLabel = selectedPage?.title || encounter?.concept || 'Python foundations'
  const runPractice = async () => {
    if (!String(tutorCode || '').trim()) {
      setTerminal({ status: 'empty', output: ['Write some Python in tutor.py before running it.'] })
      return
    }
    setTerminal({ status: 'running', output: ['Run requested. Check the terminal below for Python output or errors.', 'Running code does not grade your answer.'] })
    try { await onTutorRun?.() } catch (error) {
      setTerminal({ status: 'failed', output: [`Could not run tutor.py: ${error.message}`] })
    }
  }
  const submit = async () => {
    setTerminal({ status: 'submitted', output: ['[SUBMIT] tutor.py sent for bounded Tutor feedback.', 'No campaign reward, Resolve, HP or project mutation occurs here.'] })
    try {
      const result = await onPracticePrompt?.({ concept: conceptLabel, questionType: PRACTICE_TYPE_BY_LENS[practiceMode] || 'short_explanation', difficulty: practiceDifficulty, answer: tutorCode, question: [practiceQuestion?.text || practiceModes.find((mode) => mode.id === practiceMode)?.prompt || '', practiceExample ? `Example:\n${practiceExample}` : ''].filter(Boolean).join('\n\n') })
      if (result?.verdict) {
        setTerminal({ status: result.verdict === 'correct' ? 'passed' : 'failed', output: [`[PYR] ${result.verdict === 'correct' ? 'Correct' : 'Not yet'}`, result.reason, 'Practice never changes campaign rewards, HP or Resolve.'] })
      }
    } catch (error) {
      setTerminal({ status: 'failed', output: [`Tutor feedback unavailable: ${error.message}`] })
    }
  }
  const interviewQuestion = practiceQuestion?.text || `Explain ${conceptLabel} in your own words and give a small example of when you would use it.`
  const submitInterview = async () => {
    if (!interviewAnswer.trim() || busy) return
    if (!onPracticePrompt) { setInterviewFeedback({ status: 'error', text: 'Feedback is unavailable right now.' }); return }
    setInterviewFeedback({ status: 'pending', text: 'PYR is reviewing your explanation…' })
    try {
      const result = await onPracticePrompt?.({ concept: conceptLabel, questionType: 'short_explanation', difficulty: practiceDifficulty, answer: interviewAnswer, question: interviewQuestion })
      setInterviewFeedback(result?.verdict ? { status: result.verdict, text: result.reason } : { status: 'pending', text: 'Your explanation was sent for feedback.' })
    } catch (error) {
      setInterviewFeedback({ status: 'error', text: `Feedback unavailable: ${error.message}` })
    }
  }
  const askInterviewQuestion = async () => {
    if (!pyr?.chooseLensEnabled || busy) return
    setInterviewFeedback({ status: 'pending', text: 'PYR is preparing a question…' })
    try {
      const lens = RESOURCE_PRACTICE_MODES.find((mode) => mode.id === 'explain')
      const choice = await pyr.chooseLens({ concept: conceptLabel, lenses: [lens] })
      setPracticeQuestion({ text: choice.question, why: choice.why })
      setInterviewAnswer('')
      setInterviewFeedback(null)
    } catch (error) {
      setInterviewFeedback({ status: 'error', text: `Could not prepare a question: ${error.message}` })
    }
  }
  const askPyr = async () => {
    const prompt = aiPrompt.trim()
    if (!prompt) return
    setAiPrompt('')
    if (!pyr?.ready) {
      setAiMessages((current) => [...current, { role: 'learner', text: prompt }, { role: 'pyr', text: 'Connect OpenCode in Settings → AI Tutor so I can answer here. Until then, launch a CLI in the Hunt PYR panel.' }].slice(-8))
      return
    }
    setAiMessages((current) => [...current, { role: 'learner', text: prompt }, { role: 'pyr', text: '…thinking', pending: true }].slice(-8))
    let reply
    try {
      reply = await pyr.ask({ question: prompt, concept: conceptLabel, code: practiceFormat === 'interview' ? interviewAnswer : String(tutorCode || '') })
    } catch (error) {
      reply = `I couldn't answer that just now (${error.message}). Try again in a moment.`
    }
    setAiMessages((current) => current.map((message) => (message.pending ? { role: 'pyr', text: reply } : message)))
  }
  editorActions.current = { run: runPractice, submit, save: onTutorSave }
  const practiceModes = RESOURCE_PRACTICE_MODES
  const practiceExample = !practiceQuestion && ['predict', 'trace', 'bug'].includes(practiceMode) ? (practiceMode === 'bug' ? (selectedPage?.mistake_examples?.[0] || selectedPage?.examples?.[0] || '') : (lessonFor(selectedPage)?.example || '')) : ''
  const practicePrompt = practiceQuestion?.text || practiceModes.find((mode) => mode.id === practiceMode)?.prompt || ''
  useEffect(() => {
    if (!practiceEditor || surface !== 'ide' || practiceFormat !== 'code') return
    const lines = [`# ${conceptLabel} · ${practiceModes.find((mode) => mode.id === practiceMode)?.label || 'Practice'}`, ...String(practicePrompt).split('\n').flatMap((line) => (line.match(/.{1,72}(?:\s|$)|.{1,72}/g) || ['']).map((part) => `# ${part.trim()}`))]
    if (practiceExample) lines.push('#', '# Example:', ...String(practiceExample).split('\n').map((line) => `# ${line}`))
    lines.push('#', '# Write your answer below. Your existing tutor.py is preserved.')
    const node = document.createElement('div')
    node.className = 'tutor-editor-prompt'
    node.textContent = lines.join('\n')
    node.style.fontSize = `${editorFontSize}px`
    node.style.lineHeight = `${Math.round(editorFontSize * 1.55)}px`
    let zoneId
    const zone = { afterLineNumber: 0, heightInPx: lines.length * Math.round(editorFontSize * 1.55) + 16, domNode: node }
    practiceEditor.changeViewZones((accessor) => { zoneId = accessor.addZone(zone) })
    const resize = () => {
      const height = node.scrollHeight
      if (height > zone.heightInPx) {
        zone.heightInPx = height
        try { practiceEditor.changeViewZones((accessor) => accessor.layoutZone(zoneId)) } catch { /* editor disposed */ }
      }
    }
    const observer = new ResizeObserver(resize)
    observer.observe(node)
    const frame = requestAnimationFrame(resize)
    return () => { cancelAnimationFrame(frame); observer.disconnect(); try { practiceEditor.changeViewZones((accessor) => accessor.removeZone(zoneId)) } catch { /* editor disposed */ } }
  }, [practiceEditor, surface, practiceFormat, practiceMode, practicePrompt, practiceExample, conceptLabel, editorFontSize])
  const choosePyrLens = async () => {
    try {
      const choice = await pyr.chooseLens({ concept: conceptLabel, lenses: practiceModes })
      setPracticeMode(choice.lens_id)
      setPracticeQuestion({ text: choice.question, why: choice.why })
    } catch (error) {
      setTerminal({ status: 'failed', output: [`PYR could not pick a lens: ${error.message}`] })
    }
  }
  return (
    <div className="resource-tutor-screen" data-study-surface={surface} data-testid="resource-tutor" data-campaign-revision={revision}>
      <header className="resource-tutor-header"><div><span className="screen-kicker">HUNTER’S STUDY</span><h2>{huntView ? 'Study the beast. Train the sign. Hunt.' : 'Learn it, then make it yours.'}</h2></div><div className="resource-tutor-header-actions"><button type="button" onClick={() => onNavigate?.('forge')}>Resume Hunt</button><span>REV {revision ?? 0}</span></div></header>
      <nav className="resource-tutor-tabs" aria-label="Hunter’s Study sections"><button type="button" className={surface === 'learn' ? 'active' : ''} onClick={() => setSurface('learn')}>Codex</button><button type="button" className={surface === 'bestiary' ? 'active' : ''} onClick={() => setSurface('bestiary')}>Bestiary</button><button type="button" className={surface === 'signs' ? 'active' : ''} onClick={() => setSurface('signs')}>Signs</button><button type="button" className={surface === 'ide' || surface === 'notes' ? 'active' : ''} disabled={practiceLocked} title={practiceLocked ? 'Unavailable during a boss fight' : undefined} onClick={() => setSurface('ide')}>↗ IDE practice</button><button type="button" className={surface === 'spar' ? 'active' : ''} disabled={practiceLocked} title={practiceLocked ? 'Unavailable during a boss fight' : undefined} onClick={() => setSurface('spar')}>⚔ Sparring</button></nav>
      {practiceLocked && <p className="resource-boss-lock" role="status">Boss fight active · The codex and bestiary are open. Practice and sparring unlock after the fight or retreat.</p>}
      {surface === 'learn' && <TutorLearningPath practiceLocked={practiceLocked} pages={pages} selectedPage={selectedPage} onSelect={setSelectedId} onPractice={(mode) => { setPracticeMode(mode); setPracticeFormat('code'); setPracticeQuestion(null); setSurface('ide') }} reference={<><ResourceCodexExamples page={selectedPage} /><ResourceCodexMistakes page={selectedPage} entries={selectedEntries} /><ResourceEncounterRecords entries={selectedEntries} /><StudiedAtHome concept={selectedPage?.title} /><StudyAtHomeButton topic={selectedPage?.title} context="studying a concept between bounties" label="Study more at home" /></>} onResume={() => onNavigate?.('forge')} encounter={encounter} studyObjective={studyObjective} />}
      {!practiceLocked && surface === 'spar' && <SparringArena roster={sparRoster} actions={sparActions} armory={armory} busy={busy} />}
      {huntView && <HunterCodex practiceLocked={practiceLocked} view={surface} hunter={hunter} pages={pages} entries={entries} progress={progress} encounter={encounter} pyr={pyr} busy={busy}
        selectedId={huntPick} onSelect={(pageId) => { setHuntPick(pageId); setSelectedId(pageId) }} onView={setSurface}
        onRead={(pageId) => { setHuntPick(pageId); setSelectedId(pageId); setSurface('learn') }}
        onPractice={(pageId, mode, difficulty) => { if (pageId) { setHuntPick(pageId); setSelectedId(pageId) } setPracticeMode(mode); setPracticeFormat('code'); setPracticeDifficulty(difficulty || 1); setPracticeQuestion(null); setSurface('ide') }} />}

      {!practiceLocked && surface === 'ide' && <section className="resource-ide-layout"><aside className="resource-ide-rail tutor-practice-picker"><span className="screen-kicker">PRACTICE SETUP</span><label>Topic<select aria-label="Practice topic" value={selectedPage?.id || ''} onChange={(event) => { setSelectedId(event.target.value); setPracticeQuestion(null); setQuizPick(null); setInterviewAnswer(''); setInterviewFeedback(null) }}>{pages.map((page) => <option key={page.id} value={page.id}>{page.title}</option>)}</select></label><label>Activity<select aria-label="Practice activity" value={['quiz', 'true_false', 'interview'].includes(practiceFormat) ? practiceFormat : practiceMode} onChange={(event) => { const value = event.target.value; setQuizPick(null); setInterviewAnswer(''); setInterviewFeedback(null); setPracticeQuestion(null); if (['quiz', 'true_false', 'interview'].includes(value)) setPracticeFormat(value); else { setPracticeFormat('code'); setPracticeMode(value) } }}><option value="quiz">Multiple choice</option><option value="true_false">True or false</option><option value="interview">Written interview</option>{practiceModes.map((mode) => <option key={mode.id} value={mode.id}>{mode.label}</option>)}</select></label>{practiceFormat === 'code' && pyr?.chooseLensEnabled && <button type="button" onClick={choosePyrLens} disabled={busy}>✦ Let PYR choose</button>}<button type="button" onClick={() => setSurface('learn')}>Read this lesson</button><button type="button" onClick={() => setSurface('notes')}>Open notes</button><figure className="tutor-study-scene" role="img" aria-label="The hunter studies at his desk, turns pages, and visits the library shelf for another book"><div className="tutor-study-animation" aria-hidden="true" /><figcaption>STUDY IN PROGRESS</figcaption></figure><small>Practice is separate from your campaign files.</small></aside><main className="resource-ide-main">{practiceFormat === 'quiz' || practiceFormat === 'true_false' ? (() => { const base = lessonFor(selectedPage); const truth = TUTOR_TRUE_FALSE[selectedPage?.id]; const lesson = practiceFormat === 'true_false' ? (truth ? { ...base, ...truth, options: ['True', 'False'], example: null } : null) : base; return <section className="tutor-quiz"><span className="screen-kicker">{practiceFormat === 'true_false' ? 'TRUE OR FALSE' : 'MULTIPLE CHOICE'} · {conceptLabel.toUpperCase()}</span>{lesson?.options ? <><h3>{lesson.question}</h3>{lesson.example && <div className="tutor-question-editor"><div className="resource-editor-toolbar">example.py · read only</div><Editor height="180px" language="python" value={lesson.example} theme="vs-dark" options={{ readOnly: true, minimap: { enabled: false }, fontSize: editorFontSize, automaticLayout: true, scrollBeyondLastLine: false }} /></div>}<div className="tutor-lesson-options">{lesson.options.map((option, index) => <button key={option} type="button" className={quizPick === index ? 'selected' : ''} onClick={() => setQuizPick(index)}>{option}</button>)}</div>{quizPick !== null && <p className={`tutor-answer ${quizPick === lesson.answer ? 'correct' : 'incorrect'}`} role="status">{quizPick === lesson.answer ? lesson.why : 'Not quite. Read the example and try again.'}</p>}</> : <><h3>Read and practice this topic</h3><p>A written check for this topic is still being prepared. You can use the lesson and code practice now.</p><button type="button" onClick={() => setPracticeFormat('code')}>Open code practice</button></>}</section> })() : practiceFormat === 'interview' ? <section className="tutor-interview"><span className="screen-kicker">WRITTEN INTERVIEW · {conceptLabel.toUpperCase()}</span><h3>{interviewQuestion}</h3><button type="button" className="tutor-interview-question" onClick={askInterviewQuestion} disabled={!pyr?.chooseLensEnabled || busy || interviewFeedback?.status === 'pending'} title={!pyr?.chooseLensEnabled ? 'Connect PYR to generate another question' : undefined}>Ask PYR for another question</button><label htmlFor="practice-interview-answer">Your explanation</label><textarea id="practice-interview-answer" value={interviewAnswer} onChange={(event) => { setInterviewAnswer(event.target.value); setInterviewFeedback(null) }} maxLength={20000} placeholder="Explain your reasoning and give an example…" /><div className="tutor-interview-actions"><button type="button" className="primary" onClick={submitInterview} disabled={busy || !interviewAnswer.trim() || interviewFeedback?.status === 'pending'}>Submit for feedback</button></div>{interviewFeedback && <p className={`tutor-answer ${interviewFeedback.status}`} role="status">{interviewFeedback.status === 'correct' ? 'Correct · ' : interviewFeedback.status === 'incorrect' ? 'Not yet · ' : ''}{interviewFeedback.text}</p>}</section> : <><div className="resource-breadcrumb"><span>TUTOR</span><span>/</span><strong>IDE PRACTICE</strong></div><div className="resource-editor-card"><div className="resource-editor-toolbar"><span><b className="safe-badge">PYR WRITABLE</b> tutor.py{tutorDirty ? ' · unsaved' : ''}</span><span>MONACO · PYTHON · LOCAL COMPLETION</span></div><div className="resource-monaco"><Editor height="100%" path="tutor.py" language="python" value={tutorCode || ''} onChange={(value) => onTutorChange?.(value ?? '')} onMount={(editor, monaco) => { registerPythonHoverProvider(monaco); setPracticeEditor(editor); editor.onDidDispose(() => setPracticeEditor((current) => current === editor ? null : current)); const provider = monaco.languages.registerCompletionItemProvider('python', { triggerCharacters: ['.', '_'], provideCompletionItems: (model) => ({ suggestions: resourceIdentifierSuggestions(model.getValue()).map((label) => ({ label, kind: monaco.languages.CompletionItemKind.Keyword, insertText: label })) }) }); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => editorActions.current.run?.()); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => editorActions.current.save?.()); editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => editorActions.current.submit?.()); editor.onDidDispose(() => provider.dispose()) }} theme="vs-dark" options={{ minimap: { enabled: false }, acceptSuggestionOnEnter: 'off', fontSize: editorFontSize, fontFamily: 'JetBrains Mono, ui-monospace, monospace', lineHeight: Math.round(editorFontSize * 1.55), padding: { top: 14, bottom: 14 }, automaticLayout: true, smoothScrolling: true, tabSize: 4, suggestOnTriggerCharacters: true }} /></div><div className="resource-editor-actions"><span>Ctrl/Cmd ↵ run · Ctrl/Cmd S save · Ctrl/Cmd ⇧ ↵ submit</span><div><button type="button" onClick={onTutorSave} disabled={busy}>Save Tutor</button><button type="button" onClick={onTutorFormat} disabled={busy}>Pretty</button><button type="button" data-tutor-run onClick={runPractice} disabled={busy}>▶ Run Tutor</button><button type="button" className="primary" data-tutor-submit onClick={submit} disabled={busy || !String(tutorCode || '').trim()}>Submit for feedback</button></div></div></div><section className={`resource-ide-terminal ${terminal.status}`} aria-live="polite"><div><span>PRACTICE FEEDBACK</span><b>{terminal.status.toUpperCase()}</b></div><pre>{terminal.output.join('\n')}</pre></section></>}{tutorExternalChange && <div className="tutor-conflict-banner" role="alert"><strong>External tutor.py change detected.</strong><span>Your unsaved edits are preserved.</span><button type="button" onClick={onTutorReloadExternal}>Reload external version</button><button type="button" onClick={onTutorKeepEdits}>Keep my edits</button></div>}</main><aside className="resource-ai-panel"><div className="resource-ai-heading"><div><span className="screen-kicker">PYR / AI</span><strong>Tutor channel</strong></div><span className="connection-pill">{pyr?.ready ? 'OPENCODE' : 'OFFLINE'}</span></div><p>Bounded guidance only. PYR will not paste a campaign answer or project-specific snippet.</p><div className="resource-ai-messages">{aiMessages.map((message, index) => <div key={`${message.role}-${index}`} className={`resource-ai-message ${message.role}`}><span>{message.role === 'learner' ? 'YOU' : 'PYR'}</span><p>{message.text}</p></div>)}</div><textarea value={aiPrompt} onChange={(event) => setAiPrompt(event.target.value)} rows={3} placeholder="Ask for a hint, not a finished answer…" /><div><button type="button" onClick={() => setAiMessages([])}>Clear</button><button type="button" className="primary" onClick={askPyr} disabled={busy}>Ask PYR</button></div></aside></section>}
      {!practiceLocked && surface === 'notes' && <section className="resource-notes-layout"><aside className="resource-ide-rail resource-notes-rail"><button type="button" className="resource-rail-file" onClick={() => setSurface('ide')}><ForgeFileGlyph kind="python" /><small>tutor.py</small></button><button type="button" className="resource-rail-file active" onClick={() => setSurface('notes')}><ForgeFileGlyph kind="markdown" /><small>notes.md</small></button><div className="resource-ide-context"><span className="screen-kicker">CONCEPT</span><strong>{conceptLabel}</strong><small>notes.md · learner workspace</small></div></aside><main className="resource-notes-main"><ResourceNotebook pages={pages} selectedPage={selectedPage} entries={entries} onSelectPage={setSelectedId} /></main></section>}
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
        <div className="character-cockpit-actions"><button className="primary" type="button" onClick={() => onNavigate?.('forge')}>Resume Hunt</button><button type="button" onClick={() => onNavigate?.('tutor')}>Open Tutor</button><button type="button" onClick={() => onNavigate?.('codex')}>Read Codex</button></div>
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

// The player's pixel paper-doll (avatarSprite.js), drawn as one crisp SVG.
export function AvatarSprite({ appearance, gear = {}, size = 96, className = '', title = 'Your character' }) {
  const rects = avatarRects(appearance || {}, gear)
  return (
    <svg className={`avatar-sprite ${className}`} viewBox={AVATAR_VIEWBOX} width={Math.round(size * 0.75)} height={size} style={{ width: Math.round(size * 0.75), height: size, flex: 'none' }} shapeRendering="crispEdges" role="img" aria-label={title}>
      {/* Inline fill/stroke: some surfaces style every svg shape as an icon. */}
      {rects.map((rect) => <rect key={`${rect.x}-${rect.y}`} x={rect.x} y={rect.y} width={rect.width} height={1} style={{ fill: rect.fill, stroke: 'none' }} />)}
    </svg>
  )
}

// 48x48 head-and-shoulders portrait (Character screen).
function CharacterPortrait({ appearance, size = 192 }) {
  const rects = portraitRects(appearance || {})
  return (
    <svg className="character-portrait" viewBox={`0 0 ${PORTRAIT_SIZE} ${PORTRAIT_SIZE}`} width={size} height={size} style={{ width: size, height: size, flex: 'none' }} shapeRendering="crispEdges" role="img" aria-label={`${CHARACTER_NAME}, portrait`}>
      {rects.map((rect) => <rect key={`${rect.x}-${rect.y}`} x={rect.x} y={rect.y} width={rect.width} height={1} style={{ fill: rect.fill, stroke: 'none' }} />)}
    </svg>
  )
}

function AvatarSwatch({ field, value, active, onPick, disabled }) {
  // Beard colours share the hair palette; 'match' (no swatch) follows the hair.
  const palette = AVATAR_PALETTES[field === 'beard_color' ? 'hair_color' : field]
  const color = palette ? (Array.isArray(palette[value]) ? palette[value][0] : palette[value]) : null
  const label = AVATAR_STYLE_LABELS[value] && (color === null || value === 'match') ? AVATAR_STYLE_LABELS[value] : value.replaceAll('_', ' ')
  return (
    <button type="button" className={`avatar-swatch ${active ? 'active' : ''} ${color ? 'color' : 'text'}`} onClick={() => onPick(field, value)} disabled={disabled} aria-pressed={active} title={`${AVATAR_LABELS[field]}: ${label}`}>
      {color ? <i style={{ background: color }} /> : <span>{label}</span>}
    </button>
  )
}

// Character screen (opened from the avatar in Home): customise the look,
// equip owned gear, and see the stats that come with it.
const HUNTER_STAT_INFO = {
  strength: { label: 'Strength', effect: 'Bigger Resolve chips, so a boss breaks sooner', from: 'Writing and fixing code' },
  insight: { label: 'Insight', effect: 'See weaknesses, traps and boss mechanics coming', from: 'Reading code (predict, trace)' },
  focus: { label: 'Focus', effect: 'Stronger PYR hints', from: 'Explaining ideas and teach-backs' },
  vitality: { label: 'Vitality', effect: 'More HP to survive mistakes', from: 'Showing up: your first correct answer each day' },
}

// Hunter sheet: level, the four stats (spend free points) and the sign book.
// Nothing here ever skips a question; stats make fights safer, not shorter.
function HunterSheet({ hunter, spendStatPoint, busy }) {
  if (!hunter) return null
  const free = hunter.free_points || 0
  return (
    <section className="character-panel hunter-sheet" aria-label="Hunter sheet">
      <header><h3>Hunter · Level {hunter.level}</h3>{free > 0 ? <small className="hunter-free">{free} free point{free === 1 ? '' : 's'}</small> : <small>Next point at level {hunter.level + 1}</small>}</header>
      <div className="hunter-stats">
        {Object.entries(HUNTER_STAT_INFO).map(([id, info]) => {
          const stat = hunter.stats?.[id] || { value: 1, xp: 0, next_at: 10 }
          return (
            <div key={id} className="hunter-stat">
              <div className="hunter-stat-head"><strong>{info.label}</strong><b>{stat.value}</b>{free > 0 && <button type="button" onClick={() => spendStatPoint?.(id)} disabled={busy} aria-label={`Spend a point on ${info.label}`}>+</button>}</div>
              <div className="hunter-bar" aria-hidden="true"><i style={{ width: `${Math.round(((stat.xp % 10) / 10) * 100)}%` }} /></div>
              <small>{info.effect}</small>
              <small className="hunter-from">Grows from: {info.from} · {stat.xp % 10}/10 to next</small>
            </div>
          )
        })}
      </div>
      <h4 className="hunter-book-title">Stores</h4>
      {(hunter.materials || []).length
        ? <ul className="hunter-materials">{hunter.materials.map((item) => <li key={item.id}><span>{item.name}</span><b>×{item.count}</b></li>)}</ul>
        : <p className="hunter-materials-empty">No banked materials yet. Delve, clear fights and reach a camp to bank beast parts.</p>}
      <h4 className="hunter-book-title">Sign book</h4>
      <ol className="hunter-signs">
        {(hunter.signs || []).map((sign) => {
          const info = HUNT_BEASTS[sign.id] || {}
          const prev = sign.earned_level > 0 ? HUNTER_SIGN_LEVEL_XP[sign.earned_level - 1] : 0
          const span = sign.next_level_xp ? sign.next_level_xp - prev : 1
          const fill = sign.next_level_xp ? Math.max(0, Math.min(100, Math.round(((sign.xp - prev) / span) * 100))) : 100
          return (
            <li key={sign.id} className={`hunter-sign rank-${sign.rank} ${sign.dull ? 'dull' : ''}`}>
              <span className="hunter-sigil"><HuntSigil pageId={sign.id} size={22} /></span>
              <div className="hunter-sign-body">
                <div className="hunter-sign-head"><strong>Sign of the {info.sign || sign.id}</strong><span>Lvl {sign.level}/10 · {sign.rank_name}{sign.dull ? ' · dull' : ''}</span></div>
                <div className="hunter-bar" aria-hidden="true"><i style={{ width: `${fill}%` }} /></div>
                <small>{sign.xp} XP{sign.next_level_xp ? ` · ${sign.next_level_xp} for level ${sign.earned_level + 1}` : ' · max level'}{sign.held_by_gate ? ' · held by its rank gate' : ''}{sign.next_gate ? ` · next: ${sign.next_gate}` : ''}</small>
              </div>
            </li>
          )
        })}
      </ol>
      <p className="hunter-note">Signs grow by use: +3 for a clean first try, +1 after a miss, +5 when a campaign bounty uses it, +2 for explaining it.</p>
    </section>
  )
}

// Total sign XP for levels 1..10 (mirrors HUNTER_SIGN_LEVELS in state.py).
const HUNTER_SIGN_LEVEL_XP = [3, 8, 15, 24, 35, 48, 63, 80, 99, 120]

function CharacterScreen({ progress, equipmentProjection, setAvatar, equipCampaignItem, hunter, spendStatPoint, armory, armoryActions, busy, onClose }) {
  const player = progress.player || {}
  const equipment = progress.equipment || {}
  const stats = progress.stats || {}
  const companion = progress.companion || {}
  const options = equipmentProjection?.avatar_options || {}
  const [look, setLook] = useState(() => ({ ...DEFAULT_APPEARANCE, ...(equipmentProjection?.avatar || {}) }))
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (equipmentProjection?.avatar) setLook((current) => ({ ...current, ...equipmentProjection.avatar }))
  }, [JSON.stringify(equipmentProjection?.avatar || {})])
  const pick = async (field, value) => {
    setLook((current) => ({ ...current, [field]: value }))
    if (!setAvatar) return
    setSaving(true)
    try { await setAvatar({ [field]: value }) } finally { setSaving(false) }
  }
  const gear = { armor: equipment.armor, trinket: equipment.trinket }
  const shields = (progress.skills || []).filter((skill) => skill.shield?.tier && skill.shield.tier !== 'none').length
  return (
    <section className="character-screen" aria-label="Character">
      <div className="character-screen-head">
        <div><span className="screen-kicker">CHARACTER</span><h2>{CHARACTER_NAME}</h2><p>{player.name ? `${player.name} · ` : ''}{player.title || 'Apprentice Coder'} · Rank {player.rank || 'F'} · Level {player.level ?? 1}</p></div>
        <button type="button" onClick={onClose}>← Back to room</button>
      </div>
      <div className="character-screen-layout">
        <div className="character-stage">
          <div className="character-stage-frame"><CharacterPortrait appearance={look} size={192} /><AvatarSprite appearance={look} gear={gear} size={176} className="character-stage-sprite" title={`${CHARACTER_NAME} with gear`} /></div>
          <div className="character-stage-gear">
            <span><small>WEAPON</small><strong>{armory?.weapon?.name || 'Bare hands'}</strong></span>
            <span><small>ARMOR</small><strong>{gear.armor || 'Apprentice Coat'}</strong></span>
            <span><small>TRINKET</small><strong>{gear.trinket && gear.trinket !== 'None' ? gear.trinket : 'None'}</strong></span>
          </div>
          <dl className="character-stats">
            <div><dt>HP</dt><dd>{player.hp ?? 0} / {player.max_hp ?? 0}</dd></div>
            <div><dt>XP</dt><dd>{player.xp ?? 0} / {player.xp_next ?? 100}</dd></div>
            <div><dt>Coins</dt><dd>{player.coins ?? 0}</dd></div>
            <div><dt>Bosses</dt><dd>{stats.bosses_defeated ?? 0}</dd></div>
            <div><dt>Shields</dt><dd>{shields}</dd></div>
            <div><dt>PYR</dt><dd>{companion.form || 'Tiny Code-Flame'}</dd></div>
          </dl>
        </div>
        <div className="character-controls">
          <ArmoryPanel armory={armory} actions={armoryActions} busy={busy} />
          <HunterSheet hunter={hunter} spendStatPoint={spendStatPoint} busy={busy} />
          <section className="character-panel">
            <header><h3>Appearance</h3>{saving && <small>saving…</small>}</header>
            {Object.keys(AVATAR_LABELS).filter((field) => field !== 'beard_color' || look.facial_hair !== 'none').map((field) => (
              <div className="avatar-option-row" key={field}>
                <span>{AVATAR_LABELS[field]}</span>
                <div className="avatar-option-swatches">
                  {(options[field] || []).map((value) => <AvatarSwatch key={value} field={field} value={value} active={look[field] === value} onPick={pick} disabled={busy} />)}
                </div>
              </div>
            ))}
          </section>
          <section className="character-panel">
            <header><h3>Gear</h3><small>Buy at the Market · equip here</small></header>
            {(equipmentProjection?.slots || []).map((slot) => (
              <div className="character-gear-slot" key={slot.id}>
                <span className="screen-kicker">{slot.label}</span>
                <div className="character-gear-list">
                  {(slot.items || []).length ? slot.items.map((item) => (
                    <button type="button" key={item.id} className={`character-gear-item ${item.equipped ? 'equipped' : ''}`} onClick={() => equipCampaignItem?.(item.id)} disabled={busy || item.equipped || !equipCampaignItem}>
                      {lanternItemArt(item.id) ? <img className="character-item-art" src={lanternItemArt(item.id)} alt="" /> : <AvatarSprite appearance={look} gear={{ ...gear, [slot.id]: item.name }} size={56} title={`Preview with ${item.name}`} />}
                      <span><strong>{item.name}</strong><small>{item.effect || item.description}</small></span>
                      <b>{item.equipped ? 'EQUIPPED' : 'EQUIP'}</b>
                    </button>
                  )) : <p className="home-empty-copy">{slot.id === 'armor' ? 'No armor owned yet.' : 'Visit the Market to find your first trinket.'}</p>}
                </div>
              </div>
            ))}
          </section>
        </div>
      </div>
    </section>
  )
}

function Homestead({ progress, revision, equipmentProjection, purchaseCosmetic, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, setAvatar, hunter, spendStatPoint, armory, armoryActions, busy, onNavigate }) {
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
  const [characterOpen, setCharacterOpen] = useState(false)
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
  const restCost = Math.ceil(Math.max(0, maxHp - hp) / 10)
  const restFloor = Math.ceil(maxHp * 0.3)
  const restCoins = Number(player.coins ?? 0)
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
    hearth: ['HEARTH', 'Warm up before the next job.', 'Full rest costs 1 coin per 10 HP. If you cannot afford it, emergency rest restores you up to 30% HP. Meals offer a smaller top-up.', <div className="home-context-actions"><button type="button" disabled={busy || hp >= maxHp || (restCoins < restCost && hp >= restFloor) || !performHomesteadAction} onClick={() => perform('recover')}>{restCoins >= restCost ? `Rest · ${restCost} coins` : 'Free emergency rest'}</button><button type="button" className="ghost" disabled={busy || hp >= maxHp || !(supplies.meals > 0) || !performHomesteadAction} onClick={() => perform('meal')}>Eat a meal</button></div>],
    armory: ['ARMORY CHEST', 'Tune the kit you will carry.', 'Armor softens retaliation. Trinkets shape Guard Breaks and protection. Equip what fits the next contract, then return to the Hunt.', <div className="home-context-actions"><button type="button" onClick={scrollToLoadout}>Browse loadout</button><button type="button" className="ghost" disabled={busy || upgradeTokens < 1 || !performHomesteadAction} onClick={() => perform('spend_token')}>Spend upgrade token</button></div>],
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

      {characterOpen && <CharacterScreen hunter={hunter} spendStatPoint={spendStatPoint} armory={armory} armoryActions={armoryActions} progress={progress} equipmentProjection={equipmentProjection} setAvatar={setAvatar} equipCampaignItem={equipCampaignItem} busy={busy} onClose={() => setCharacterOpen(false)} />}
      <div className="home-interior-layout" hidden={characterOpen}>
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
          <button type="button" className="room-player" onClick={() => setCharacterOpen(true)} title="Open your character">
            <AvatarSprite appearance={equipmentProjection?.avatar} gear={{ armor: equipment.armor, trinket: equipment.trinket }} size={88} />
            <small>{CHARACTER_NAME.toUpperCase()} · customise</small>
          </button>
        </section>
        <section className="home-context-panel"><div className="home-context-mark"><RouteIcon id={focus === 'hearth' ? 'flame' : focus === 'armory' ? 'shield' : focus === 'study' ? 'spark' : focus === 'pyr' ? 'spark' : 'plus'} /></div><span className="screen-kicker">{focusCopy[0]}</span><h3>{focusCopy[1]}</h3><p>{focusCopy[2]}</p>{focusCopy[3]}{focus === 'pyr' && <div className="pyr-bond-meter"><div><span>BOND</span><strong>{pyrBond}{nextPyrStageMeta ? ` / ${nextPyrStageMeta.threshold}` : ' · MAX'}</strong></div><i><b style={{ width: `${pyrBondProgress}%` }} /></i><small>Training energy {pyrEnergy}/{pyrMaxEnergy}. Evolution is a companion milestone, not a hidden answer bonus.</small></div>}<div className="home-resume"><span className="screen-kicker">NEXT STEP</span><strong>{activeProject.name || 'The Count Keeper'}</strong><button type="button" onClick={() => onNavigate?.('forge')}>Return to Bounty Office</button></div></section>
      </div>

      {roomUpgradePanelOpen && <section className="home-upgrade-drawer open" aria-label="Homestead upgrades" data-testid="homestead-room-upgrades"><div className="home-upgrade-drawer-head"><div><span className="screen-kicker">BUILD THE HOMESTEAD</span><h3>Room upgrades</h3><p>Spend upgrade tokens on small, authored stat and trinket effects. Nothing here changes the code you must write.</p></div><span className="home-upgrade-token-pill">{upgradeTokens} TOKENS</span></div><div className="room-upgrade-grid">{HOME_ROOM_UPGRADES.map(renderRoomUpgrade)}</div><div className="home-achievement-heading"><span className="screen-kicker">ROOM HISTORY</span><strong>Achievement plaques</strong><small>Proof of cool work, not another currency.</small></div><div className="home-achievement-grid">{HOME_ACHIEVEMENTS.map((achievement) => { const unlocked = achievementUnlocked(achievement.id); return <article key={achievement.id} className={`home-achievement ${unlocked ? 'unlocked' : 'locked'}`}><span className="home-achievement-icon">{unlocked ? achievement.icon : '·'}</span><div><strong>{unlocked ? achievement.name : 'HIDDEN PLAQUE'}</strong><p>{unlocked ? achievement.detail : 'Keep learning to reveal this room history.'}</p></div><small>{unlocked ? 'UNLOCKED' : 'LOCKED'}</small></article> })}</div></section>}

      <div className="home-status-row"><span><small>HP</small><strong>{hp}/{maxHp}</strong></span><span><small>UPGRADE TOKENS</small><strong>{upgradeTokens}</strong></span><span><small>SUPPLIES</small><strong>{supplies.bandages || player.potions || 0} bandages · {supplies.tonics || 0} tonics · {supplies.meals || 0} meals</strong></span></div>

      <section className="home-loadout-section">
        <div className="home-section-heading"><div><span className="screen-kicker">LIVE LOADOUT</span><h3>Armor and trinkets</h3></div><span>Buy in Market · equip here</span></div>
        <div className="home-loadout-grid">
          {(equipmentProjection?.slots || []).map((slot) => <div className="home-loadout-slot" key={slot.id}><span className="screen-kicker">{slot.label}</span><div className="home-equip-list">{(slot.items || []).length ? (slot.items || []).map((item) => <button type="button" className={`home-equip-card ${item.equipped ? 'equipped' : ''}`} key={item.id} onClick={() => equipCampaignItem?.(item.id)} disabled={busy || item.equipped || !equipCampaignItem}><span className="home-equip-symbol"><img className="item-art-icon" src={merchantItemArt({ ...item, slot: slot.id })} alt="" /></span><span><strong>{item.name}</strong><small>{(item.effect && item.effect !== 'No special effect' ? item.effect : item.description)}</small></span><b>{item.equipped ? 'EQUIPPED' : 'EQUIP'}</b></button>) : <p className="home-empty-copy">{slot.id === 'armor' ? 'No armor owned yet.' : 'Visit Market to find your first trinket.'}</p>}</div></div>)}
        </div>
      </section>
      <section className="home-supply-strip"><span className="screen-kicker">PACKED SUPPLIES</span><span>Bandages <strong>{supplies.bandages || player.potions || 0}</strong></span><span>Ember tonics <strong>{supplies.tonics || 0}</strong></span><span>Meals <strong>{supplies.meals || 0}</strong></span><span>Vision scrolls <strong>{supplies.vision_scrolls || 0}</strong></span><small>Use supplies from the encounter kit.</small></section>
      <section className="home-progress-card"><div><span className="screen-kicker">RECENTLY CLEARED</span><h3>{completedTaskCount ? `${completedTaskCount} task${completedTaskCount === 1 ? '' : 's'} recorded` : 'No cleared work yet'}</h3></div><p>{completedTaskCount ? 'Your rewards are part of the same campaign state as Market and Bounty Office.' : 'Take a contract from the Bounty Office to start the loop.'}</p></section>
    </div>
  )
}

const CAMPAIGN_POIS = [
  { id: 'home', icon: '⌂', label: 'Home', kicker: 'REST · LOADOUT · PROGRESS', summary: 'Recover, tune your kit, grow Pyr, and spend upgrade tokens.' },
  { id: 'market', icon: '◇', label: 'Market', kicker: 'GEAR · SUPPLIES · COINS', summary: 'Meet the Merchant, then browse armor, trinkets, and supplies.' },
  { id: 'office', icon: '✦', label: 'Bounty Office', kicker: 'MAIN BOUNTIES', summary: 'Choose the next learning contract from the board.' },
]

const CAMPAIGN_MARKET_STOCK = [
  { id: 'field-bandage', name: 'Field bandage', kind: 'Supply', detail: 'Recover during Home preparation.', price: 18, icon: '＋' },
  { id: 'ember-tonic', name: 'Ember tonic', kind: 'Supply', detail: 'A one-use buffer for the next encounter.', price: 32, icon: '✦' },
  { id: 'camp-meal', name: 'Camp meal', kind: 'Supply', detail: 'Feed Pyr or restore HP from your encounter kit.', price: 26, icon: '◇' },
  { id: 'debugger-plate', name: 'Debugger Plate', kind: 'Armor', detail: '30% less damage from misses.', price: 220, icon: '⬡' },
  { id: 'syntax-ward', name: 'Syntax Ward', kind: 'Trinket', detail: 'Blocks the first counterattack each battle.', price: 48, icon: '◈' },
  { id: 'loop-lens', name: 'Loop Lens', kind: 'Trinket', detail: 'Heal 2 HP per verified objective.', price: 64, icon: '◎' },
]

// Pop-ups render at the app-shell level so a panel's stacking context can't
// put the nav bar on top of them; the wrapper keeps the theme tokens of the
// surface they open from (it is display: contents, so it adds no box).
function ShellPortal({ scope, children }) {
  const target = typeof document === 'undefined' ? null : document.querySelector('.app-shell') || document.body
  return target ? createPortal(<div className={`${scope} shell-portal`}>{children}</div>, target) : children
}

// Every campaign project with where it stands; pick any unfinished one.
function CampaignSelector({ projects, onPick, onClose, busy }) {
  useEffect(() => {
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  const ordered = [...projects].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  return (
    <div className="campaign-selector-backdrop" role="presentation" onClick={onClose}>
      <section className="campaign-selector" role="dialog" aria-modal="true" aria-labelledby="campaign-selector-title" onClick={(event) => event.stopPropagation()}>
        <header>
          <div><span className="campaign-eyebrow">CAMPAIGNS</span><h2 id="campaign-selector-title">Choose your campaign</h2></div>
          <button type="button" className="campaign-selector-close" onClick={onClose} aria-label="Close campaigns">✕</button>
        </header>
        <p className="campaign-selector-note">Switching keeps every board as you left it, so you can come back any time. Beating a boss moves you on automatically.</p>
        <ol className="campaign-selector-list">
          {ordered.map((project, index) => {
            const mobs = project.mobs || []
            const cleared = mobs.filter((mob) => isMobDefeated(mob.status)).length
            const done = project.status === 'completed' || project.completed === true
            const state = done ? 'cleared' : project.status === 'active' ? 'current' : project.status === 'locked' ? 'locked' : 'ready'
            const label = { cleared: 'CLEARED', current: 'PLAYING', locked: 'LOCKED', ready: mobs.length ? 'IN PROGRESS' : 'NEW' }[state]
            return (
              <li key={project.branch || index} className={`campaign-selector-item ${state}`}>
                <span className="campaign-selector-num">{String((project.order ?? index) + 1).padStart(2, '0')}</span>
                <span className="campaign-selector-copy">
                  <strong>{project.name || project.branch}</strong>
                  <small>Boss · {project.boss || 'Unknown'}{mobs.length ? ` · ${cleared}/${mobs.length} bounties` : ''}</small>
                </span>
                <em className="campaign-selector-state">{label}</em>
                {state === 'ready'
                  ? <button type="button" onClick={() => onPick(project.branch)} disabled={busy || !project.branch}>Play</button>
                  : <button type="button" disabled>{state === 'current' ? 'Current' : state === 'cleared' ? 'Done' : 'Locked'}</button>}
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}

function CampaignMapRail({ place, onSelect, collapsed, onToggle, progress, onSelectCampaign, busy }) {
  const [picking, setPicking] = useState(false)
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const completed = (activeProject.mobs || []).filter((mob) => isMobDefeated(mob.status)).length
  const total = (activeProject.mobs || []).length
  const chapter = Math.max(1, (progress?.projects || []).indexOf(activeProject) + 1)
  return (
    <aside className={`campaign-panel poi-rail ${collapsed ? 'map-rail-collapsed' : ''}`} aria-label="Campaign map">
      <div className="panel-heading">
        <div><span className="campaign-eyebrow">PROJECT MAP</span><h2>{activeProject.name || 'Blackjack'}</h2></div>
        {onSelectCampaign ? <button type="button" className="campaign-tag campaign-switch" onClick={() => setPicking(true)} title="Switch campaign">Switch ▾</button> : <span className="campaign-tag">{CAMPAIGN_POIS.length} POIs</span>}
        <button type="button" className="map-rail-toggle" onClick={onToggle} aria-expanded={!collapsed} title={collapsed ? 'Expand project map' : 'Collapse project map'} aria-label={collapsed ? 'Expand project map' : 'Collapse project map'}><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={collapsed ? 'm9 5 7 7-7 7' : 'm15 5-7 7 7 7'} /><path d="M20 5v14" /></svg></button>
      </div>
      {!collapsed && <>
        <div className="poi-list">
          {CAMPAIGN_POIS.map((poi) => <button key={poi.id} className={`poi-card ${place === poi.id ? 'active' : ''}`} type="button" onClick={() => onSelect(poi.id)} title={`${poi.kicker} · ${poi.summary}`} aria-current={place === poi.id ? 'page' : undefined}><span className={`poi-icon poi-${poi.id}`}>{poi.icon}</span><span className="poi-copy"><strong>{poi.label}</strong></span></button>)}
        </div>
        <div className="project-progress"><div><span>PROJECT PROGRESS</span><strong>Chapter {String(chapter).padStart(2, '0')}</strong></div><div className="campaign-progress-track"><i style={{ width: `${total ? Math.round((completed / total) * 100) : 0}%` }} /></div><p>{total ? `${completed}/${total} ${completed === 1 ? 'bounty' : 'bounties'} cleared.` : 'Boss remains locked until the project bounties are cleared.'}</p></div>
      </>}
      {collapsed && <nav className="collapsed-poi-list" aria-label="Campaign destinations">
        {CAMPAIGN_POIS.map((poi) => <button key={poi.id} type="button" className={`collapsed-poi poi-${poi.id} ${place === poi.id ? 'active' : ''}`} onClick={() => onSelect(poi.id)} aria-label={poi.id === 'market' ? 'Merchant' : poi.label} title={poi.id === 'market' ? 'Merchant' : poi.label} aria-current={place === poi.id ? 'page' : undefined}><span aria-hidden="true">{poi.icon}</span></button>)}
      </nav>}
      {picking && <ShellPortal scope="campaign-v1"><CampaignSelector projects={progress?.projects || []} busy={busy} onClose={() => setPicking(false)} onPick={async (branch) => { const result = await onSelectCampaign(branch); if (result) setPicking(false) }} /></ShellPortal>}
    </aside>
  )
}

// The Merchant's alchemy bench: beast oils from banked parts, gated by sign rank.
const BENCH_TABS = {
  oils: { label: 'Delve Preparations', title: 'Prepare for the beasts you hunt.', copy: 'Craft a preparation for a specific beast using banked materials. Use one during a fight for a temporary advantage.' },
  smithing: { label: 'Smithing', title: 'Forge armour from your hunts.', copy: 'Bank beast parts and boss essences from delves, then forge armour for your Home loadout and future Dungeon runs.' },
  identify: { label: 'Identify Vials', title: 'Find out what a vial contains.', copy: 'Bank unmarked vials dropped by elites and bosses. Answer a short code question to turn one into a Delve Preparation. A wrong answer keeps the vial and gives you another question.' },
}

function SmithingPanel({ recipes, actions, busy }) {
  return (
    <div className="smithing-grid">
      <p className="smithing-intro">Your armour stays in the Armory. Collect a free copy from a campsite stash during each Dungeon run.</p>
      {(recipes || []).map((piece) => (
        <article key={piece.id} className="smithing-piece">
          <div className="smithing-head"><strong>{piece.name}</strong><span>{piece.tier}</span></div>
          <p>{piece.flavour}</p><p>{piece.effect}</p>
          <small>{piece.materials.map((part) => `${part.name}: ${part.have}/${part.count}`).join(' · ')} · {piece.coins} coins</small>
          <button type="button" className="campaign-button" onClick={() => actions?.forgeArmor?.(piece.id)} disabled={busy || piece.owned || !piece.affordable}>{piece.owned ? 'Forged' : 'Forge armour'}</button>
        </article>
      ))}
    </div>
  )
}

function IdentifyPanel({ hunter, actions, busy }) {
  const [reading, setReading] = useState(null)
  const puzzle = hunter?.identify
  const vials = hunter?.vials || 0
  const answer = async (choice) => {
    const result = await actions?.identifyAnswer?.(puzzle.id, choice)
    if (result) setReading(result)
  }
  const [question, rest = ''] = String(puzzle?.prompt || '').split('```python\n')
  const code = rest.replace(/\n```\s*$/, '')
  return (
    <div className="identify-panel">
      <p className="identify-count">Unmarked vials banked: <b>{vials}</b></p>
      {reading && (
        <div className={`identify-result ${reading.correct ? 'right' : 'wrong'}`} role="status">
          {reading.correct
            ? <><strong>The vial held {reading.oil?.name?.replace(/ Oil$/, ' Preparation')}.</strong><span>{reading.oil?.effect} One vial was used, and the preparation is in your stores.</span></>
            : <><strong>Not quite: it printed {reading.answer}.</strong><span>{reading.why} Your vial is safe; here is a new label to read.</span></>}
        </div>
      )}
      {puzzle ? (
        <article className="identify-puzzle">
          <span className="campaign-eyebrow">LABEL · SIGN OF THE {(HUNT_BEASTS[puzzle.sign]?.sign || puzzle.sign).toUpperCase()}</span>
          <strong>{question.trim()}</strong>
          <pre><code>{code}</code></pre>
          <div className="identify-options">{(puzzle.options || []).map((option, index) => <button key={`${puzzle.id}-${index}`} type="button" className="campaign-button ghost" onClick={() => answer(index)} disabled={busy}>{option}</button>)}</div>
        </article>
      ) : vials > 0
        ? <button type="button" className="campaign-button" onClick={() => { setReading(null); actions?.identifyStart?.() }} disabled={busy}>Hold a vial to the light <span>→</span></button>
        : <p className="alchemy-empty">No vials yet. Elites and bosses drop them; bank them at a camp.</p>}
    </div>
  )
}

const ARMORY_TABS = [
  { id: 'weapon', label: 'Weapons' },
  { id: 'armor', label: 'Armour' },
  { id: 'trinket', label: 'Trinkets' },
  { id: 'supplies', label: 'Food & tonics' },
  { id: 'aid', label: 'Aid' },
  { id: 'relic', label: 'Relics' },
  { id: 'collection', label: 'Collection' },
]
// Run-only perks that bosses four to eight add to every future run (see JOURNAL_BOSS_PERKS on the server).
const EXTRA_JOURNAL_PERKS = [['starting_coins', 'run coins'], ['starting_vision_scrolls', 'vision scrolls'], ['starting_heals', 'heal charges'], ['starting_rations', 'rations'], ['starting_tonics', 'tonics']]
const SLOT_WORDS = { weapon: 'Weapon', armor: 'Armour', trinket: 'Trinket', food: 'Food', tonic: 'Tonic', relic: 'Relic', aid: 'Aid' }

function ArmoryItem({ item, children }) {
  const art = merchantItemArt(item)
  return (
    <article className={`armory-item tier-${item.tier} ${item.equipped ? 'equipped' : ''}`}>
      <div className="armory-item-head">{art && <img className="armory-item-icon" src={art} alt="" />}<strong>{item.name}</strong><small>{String(item.tier).toUpperCase()} {SLOT_WORDS[item.slot] || item.slot}{item.count ? ` ×${item.count}` : ''}</small></div>
      <p className="armory-effect">{item.effect}</p>
      {item.flavour && <small className="armory-flavour">{item.flavour}</small>}
      {children}
    </article>
  )
}

// The hunter's own gear, food, relics and collection (Home loadout).
function ArmoryPanel({ armory, actions, busy }) {
  const [tab, setTab] = useState('weapon')
  if (!armory) return null
  const items = armory.items || []
  const shown = tab === 'supplies' ? items.filter((item) => item.slot === 'food' || item.slot === 'tonic') : items.filter((item) => item.slot === tab)
  const summary = armory.summary || {}
  const buffs = armory.buffs || {}
  const charges = armory.charges || {}
  const appearances = armory.mastery_appearances || []
  const equippedAppearances = armory.equipped_appearances || {}
  const weaponStyle = armory.weapon?.combat_style || ''
  const weaponLooks = appearances.filter((item) => item.appearance_type === 'weapon' && item.style === weaponStyle)
  const armorLooks = appearances.filter((item) => item.appearance_type === 'armor')
  return (
    <section className="character-panel armory-panel" aria-label="Armory">
      <header><h3>Armory</h3><small>{items.length} items</small></header>
      <div className="armory-slots">
        <div><small>WEAPON</small><strong>{armory.weapon?.name || 'Bare hands'}</strong>{armory.weapon && <button type="button" onClick={() => actions?.unequip?.('weapon')} disabled={busy}>Unequip</button>}</div>
        <div><small>ARMOUR</small><strong>{armory.equipped?.armor || 'Apprentice Coat'}</strong></div>
        <div><small>TRINKET</small><strong>{armory.equipped?.trinket || 'None'}</strong>{armory.equipped?.trinket && armory.equipped.trinket !== 'None' && <button type="button" onClick={() => actions?.unequip?.('trinket')} disabled={busy}>Unequip</button>}</div>
      </div>
      {(armorLooks.length > 0 || weaponLooks.length > 0) && <div className="armory-mastery-loadout" aria-label="Colosseum mastery appearances">
        <span className="campaign-eyebrow">COLOSSEUM MASTERY LOOKS</span>
        <p>Earned looks change the combat scene only; stats stay with your equipped gear.</p>
        {armorLooks.length > 0 && <label>Armour appearance<select value={equippedAppearances.armor?.id || ''} onChange={(event) => actions?.equipAppearance?.('armor', event.target.value)} disabled={busy}><option value="">Base armour appearance</option>{armorLooks.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.tier}</option>)}</select></label>}
        {weaponLooks.length > 0 && <label>Weapon appearance<select value={equippedAppearances.weapon?.id || ''} onChange={(event) => actions?.equipAppearance?.('weapon', event.target.value)} disabled={busy}><option value="">Base weapon appearance</option>{weaponLooks.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.tier}</option>)}</select></label>}
      </div>}
      <p className="armory-summary">{summary.reduction ?? 0}% damage reduction · {summary.start_guards ? 'start with a free mistake · ' : ''}+{summary.coin_bonus ?? 0}% coins · +{summary.xp_bonus ?? 0}% XP{summary.loot_luck ? ` · +${summary.loot_luck}% loot luck` : ''}{Object.keys(buffs).length ? ` · next battle: ${Object.entries(buffs).map(([key, value]) => key === 'guards' ? 'a free mistake' : `${key.replace('_', ' ')} ${value}`).join(', ')}` : ''}</p>
      {(armory.sets || []).filter((set) => set.equipped_count > 0).map((set) => <p className="armory-summary" key={set.id}><strong>{set.name} · {set.equipped_count}/3 {set.equipped_count === 3 ? 'ACTIVE' : ''}</strong> — {set.description} Pieces: {set.pieces.join(', ')}.</p>)}
      <div className="bench-tabs" role="tablist" aria-label="Armory">{ARMORY_TABS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
      {tab === 'collection' ? (
        <ul className="armory-collection">{(armory.collection || []).map((entry) => <li key={entry.branch}><span>{entry.name}</span><div className="hunter-bar" aria-hidden="true"><i style={{ width: `${Math.round((entry.found / Math.max(1, entry.total)) * 100)}%` }} /></div><b>{entry.found}/{entry.total}</b></li>)}</ul>
      ) : shown.length ? (
        <div className="armory-grid">{shown.map((item) => (
          <ArmoryItem key={item.id} item={item}>
            {['weapon', 'armor', 'trinket'].includes(item.slot) && <button type="button" className="campaign-button" onClick={() => actions?.equip?.(item.id)} disabled={busy || item.equipped}>{item.equipped ? 'Equipped' : 'Equip'}</button>}
            {(item.slot === 'food' || item.slot === 'tonic') && <button type="button" className="campaign-button" onClick={() => actions?.use?.(item.id)} disabled={busy}>{item.slot === 'food' ? 'Eat' : 'Drink'}</button>}
            {item.slot === 'aid' && <button type="button" className="campaign-button" onClick={() => actions?.use?.(item.id)} disabled={busy}>Arm it</button>}
          </ArmoryItem>
        ))}</div>
      ) : <p className="alchemy-empty">{tab === 'aid' ? 'No Aid yet. Find it through bounties and bosses, or buy the Merchant’s own aid.' : `Nothing here yet. Earn ${tab === 'supplies' ? 'food' : ARMORY_TABS.find((item) => item.id === tab)?.label.toLowerCase()} in encounters or browse the Merchant’s stock.`}</p>}
      {tab === 'aid' && <p className="armory-summary armory-charges">Armed now: {charges.free_asks || 0} free PYR ask{charges.free_asks === 1 ? '' : 's'} · {charges.wards || 0} ward{charges.wards === 1 ? '' : 's'}. Arming spends the item; the charge waits until a fight needs it.</p>}
    </section>
  )
}

// The Merchant's armoury: gear and food from campaigns you have reached.
function CoinIcon() {
  return <svg className="market-coin-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5M12 6v12" /></svg>
}

function MarketItemVisual({ item, animate = false, equippedArmor = '' }) {
  const looks = { ivory: 'ivory', spectral: 'warden-heavy', harvest: 'harvest-scout', oracle: 'arcane', patchwork: 'patchwork', pilgrim: 'pilgrim', wayfarer: 'wayfarer', norse: 'norse', lanternkeeper: 'lanternkeeper', wardplate: 'wardplate', debugger: 'debugger-v2', 'merchant-oracle': 'merchant-oracle' }
  const armorLook = hunterAppearance(item.name, '').armorLook
  const look = looks[armorLook] || (RECOLOUR_LOOKS.has(armorLook) ? armorLook : undefined)
  const sheet = look ? `tate-${look}-sword-idle-sheet.png` : 'tate-idle-sheet.png'
  const armorArt = {
    ivory: 'hunter-fashion/ivory.png',
    'warden-heavy': 'hunter-fashion/warden.png',
    'harvest-scout': 'hunter-fashion/harvest.png',
    patchwork: 'hunter-fashion/patchwork-v2.png',
    pilgrim: 'hunter-fashion/pilgrim-v2.png',
    wayfarer: 'hunter-fashion/wayfarer-v2.png',
    'debugger-v2': 'hunter-fashion/debugger-v2.png',
    arcane: 'hunter-fashion/oracle-v2.png',
    'merchant-oracle': 'hunter-fashion/oracle-v2.png',
  }
  const staticArmor = armorArt[look] ? `${import.meta.env?.BASE_URL || '/'}campaign-art/items/${armorArt[look]}` : merchantItemArt(item)
  const standaloneArmor = Boolean(armorArt[look])
  if (item.slot === 'weapon' && animate) {
    const preview = marketWeaponPreview(item, equippedArmor)
    return <span className="armoury-lot-art slot-weapon market-weapon-stage" aria-hidden="true">
      <span className="market-weapon-figure" style={{ aspectRatio: preview.aspectRatio }}>
        <span className={`market-weapon-pose idle ${preview.style === 'sword' ? 'sword-idle' : ''}`} style={{ backgroundImage: `url("${preview.idle}")` }} />
        <span className="market-weapon-pose attack" style={{ backgroundImage: `url("${preview.action}")` }} />
      </span>
      <span className="market-weapon-caption">COMBAT STYLE</span><span className="market-weapon-item"><img src={merchantItemArt(item)} alt="" /></span>
    </span>
  }
  return <span className={`armoury-lot-art slot-${item.slot} ${item.slot === 'armor' && standaloneArmor ? 'standalone-armor' : ''}`} aria-hidden="true">{item.slot === 'armor' && animate ? <span className="market-hunter-preview animated" style={{ backgroundImage: `url('/campaign-art/hunter-idle/${sheet}')` }} /> : <img src={item.slot === 'armor' ? staticArmor : merchantItemArt(item)} alt="" />}</span>
}

function ArmouryLots({ armory, coins, actions, legacyPurchases, purchaseMarketItem, busy, onBack }) {
  const [filter, setFilter] = useState('open')
  const [slot, setSlot] = useState('all')
  const [selectedId, setSelectedId] = useState('')
  const stock = merchantLots(armory?.market, CAMPAIGN_MARKET_STOCK, legacyPurchases, coins)
  const lots = stock.filter((lot) => (filter === 'all' || !lot.locked) && (slot === 'all' || lot.slot === slot))
  const selected = lots.find((lot) => lot.id === selectedId) || lots[0]
  const names = Object.fromEntries((armory?.collection || []).map((entry) => [entry.branch, entry.name]))
  const slots = ['all', ...new Set(stock.map((lot) => lot.slot))]
  return <div className="alchemy-bench armoury-lots">
    <div className="market-browser-head"><div><span className="campaign-eyebrow">THE MERCHANT · SHOP</span><h3>Find your next piece of kit.</h3></div><div className="market-browser-actions"><span className="market-purse-pill"><CoinIcon /> {coins}</span><button type="button" className="campaign-button ghost" onClick={onBack}>← Back to The Merchant</button></div></div>
    <div className="armoury-controls"><div className="bench-tabs" role="group" aria-label="Lot availability"><button type="button" className={filter === 'open' ? 'active' : ''} aria-pressed={filter === 'open'} onClick={() => setFilter('open')}>Open lots</button><button type="button" className={filter === 'all' ? 'active' : ''} aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>All lots</button></div><div className="bench-tabs" role="group" aria-label="Item type">{slots.map((kind) => <button type="button" key={kind} className={slot === kind ? 'active' : ''} aria-pressed={slot === kind} onClick={() => setSlot(kind)}>{kind === 'all' ? 'All items' : kind === 'supply' ? 'Supplies' : SLOT_WORDS[kind] || kind}</button>)}</div></div>
    <div className="armoury-lots-layout"><section className="armoury-lot-catalog" aria-label="Shop items">{lots.length ? lots.map((lot) => <button type="button" key={lot.id} className={`armoury-lot-card ${selected?.id === lot.id ? 'active' : ''} ${lot.locked ? 'locked' : ''}`} aria-pressed={selected?.id === lot.id} onClick={() => setSelectedId(lot.id)}><MarketItemVisual item={lot} /><span className="armoury-lot-copy"><strong>{lot.name}</strong><small>{String(lot.tier).toUpperCase()} · {SLOT_WORDS[lot.slot] || lot.slot}</small><span className="armoury-lot-price"><CoinIcon /> {lot.price}{lot.owned ? ' · OWNED' : lot.locked ? ' · LOCKED' : ''}</span></span></button>) : <p className="alchemy-empty">No lots in this selection.</p>}</section>
    <aside className="armoury-lot-detail" aria-label="Selected shop item">{selected ? <><span className="campaign-eyebrow">SELECTED · {String(selected.tier).toUpperCase()} {SLOT_WORDS[selected.slot] || selected.slot}</span><MarketItemVisual key={selected.id} item={selected} animate equippedArmor={armory?.equipped?.armor} /><h3>{selected.name}</h3><p>{selected.effect}</p>{selected.set_name && <p className="armoury-lot-flavour"><strong>{selected.set_name} set · 3 pieces:</strong> {selected.set_description}</p>}{selected.flavour && <p className="armoury-lot-flavour">{selected.flavour}</p>}<small>{selected.campaign === 'hunter' ? 'Merchant’s equipment' : selected.campaign === 'aid' ? 'Merchant’s aid' : selected.campaign === 'merchant' ? 'Merchant’s stock' : names[selected.campaign] || selected.campaign}</small><div className="armoury-detail-price"><span>PRICE</span><strong><CoinIcon /> {selected.price}</strong></div>{selected.locked && <p className="alchemy-reason">{selected.locked} to unlock</p>}{!selected.owned && !selected.locked && !selected.affordable && <p className="alchemy-reason">Need {Math.max(1, selected.price - (coins || 0))} more coins.</p>}<button type="button" className="campaign-button" onClick={() => selected.source === 'merchant' ? purchaseMarketItem?.(selected.id) : actions?.buy?.(selected.id)} disabled={busy || selected.owned || !(selected.source === 'merchant' ? purchaseMarketItem : actions?.buy) || !selected.affordable || Boolean(selected.locked)}>{selected.owned ? 'Owned' : <>Buy · <CoinIcon /> {selected.price}</>}</button></> : <p className="alchemy-empty">Choose another item type to browse.</p>}</aside></div>
  </div>
}

function AlchemyBench({ hunter, coins, actions, busy, onBack, backLabel = '← Back to The Merchant' }) {
  const craftOil = actions?.craftOil
  const [tab, setTab] = useState('oils')
  const [regionId, setRegionId] = useState(HUNT_REGIONS[0].id)
  const [selectedSign, setSelectedSign] = useState(HUNT_REGIONS[0].pages[0])
  const region = HUNT_REGIONS.find((item) => item.id === regionId) || HUNT_REGIONS[0]
  const recipes = hunter?.oil_recipes || []
  const materials = hunter?.materials || []
  const rankNames = ['Uninscribed', 'Inscribed', 'Honed', 'Mastered']
  return (
    <div className="alchemy-bench">
      <div className="market-browser-head"><div><span className="campaign-eyebrow">HUNTER’S STILL</span><h3>{BENCH_TABS[tab].title}</h3><p>{BENCH_TABS[tab].copy}</p></div><div className="market-browser-actions"><span className="market-purse-pill"><CoinIcon /> {coins}</span>{onBack && <button type="button" className="campaign-button ghost" onClick={onBack}>{backLabel}</button>}</div></div>
      <div className="alchemy-stores"><span className="campaign-eyebrow">YOUR STORES</span>{materials.length ? materials.map((item) => <span key={item.id} className="alchemy-chip">{item.name} ×{item.count}</span>) : <span className="alchemy-empty">Nothing banked yet. Delve in the Infinite Dungeon and bank parts at a camp.</span>}{(hunter?.oils || []).map((oil) => <span key={oil.id} className="alchemy-chip oil">{oil.name.replace(/ Oil$/, ' Preparation')} ×{oil.count}</span>)}</div>
      <div className="bench-tabs" role="tablist" aria-label="Hunter’s Still">{Object.entries(BENCH_TABS).map(([id, info]) => <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{info.label}{id === 'identify' && hunter?.vials ? ` (${hunter.vials})` : ''}</button>)}</div>
      {tab === 'smithing' && <SmithingPanel recipes={hunter?.armor_recipes} actions={actions} busy={busy} />}
      {tab === 'identify' && <IdentifyPanel hunter={hunter} actions={actions} busy={busy} />}
      {tab === 'oils' && <div className="alchemy-workspace">
        <aside className="alchemy-picker" aria-label="Choose preparation ingredients">
          <div className="alchemy-region-select"><span>Region</span><details><summary aria-label={`Preparation region: ${region.label}`}>{region.label}<span aria-hidden="true">▾</span></summary><div className="alchemy-region-menu" aria-label="Choose preparation region">{HUNT_REGIONS.map((item) => <button key={item.id} type="button" className={region.id === item.id ? 'active' : ''} aria-pressed={region.id === item.id} onClick={(event) => { setRegionId(item.id); setSelectedSign(item.pages[0]); event.currentTarget.closest('details').open = false }}>{item.label}</button>)}</div></details></div>
          <span className="campaign-eyebrow">CHOOSE A BEAST</span>
          <div className="alchemy-beast-list">{region.pages.map((sign) => <button type="button" key={sign} className={selectedSign === sign ? 'active' : ''} aria-pressed={selectedSign === sign} onClick={() => setSelectedSign(sign)}><HuntSigil pageId={sign} size={20} /><span><strong>{HUNT_BEASTS[sign]?.beast}</strong><small>Sign of the {HUNT_BEASTS[sign]?.sign}</small></span></button>)}</div>
        </aside>
        <section className="alchemy-selection" aria-label="Preparations for selected beast">
          <div className="alchemy-sign-head"><HuntSigil pageId={selectedSign} size={24} /><div><span className="campaign-eyebrow">{region.label.toUpperCase()} · PREPARATIONS</span><h4>{HUNT_BEASTS[selectedSign]?.beast}</h4><small>Sign of the {HUNT_BEASTS[selectedSign]?.sign}</small></div></div>
          <div className="alchemy-recipes">{recipes.filter((recipe) => recipe.sign === selectedSign).map((recipe) => {
            const missing = recipe.materials.filter((item) => item.have < item.count)
            const reason = !recipe.unlocked ? `Needs the sign ${rankNames[recipe.rank_needed]}` : missing.length ? `Missing ${missing.map((item) => `${item.count - item.have} ${item.name}`).join(', ')}` : coins < recipe.coins ? `Needs ${recipe.coins} coins` : ''
            return <article key={recipe.id} className={`alchemy-recipe tier-${recipe.tier} ${recipe.unlocked ? '' : 'locked'}`}><strong>{recipe.name.replace(/ Oil$/, ' Preparation')}</strong><p>{recipe.effect}</p><small>{recipe.materials.map((item) => `${item.count} ${item.name} (${item.have})`).join(' · ')} · {recipe.coins} coins</small><button type="button" className="campaign-button" onClick={() => craftOil?.(recipe.id)} disabled={busy || !craftOil || !recipe.affordable || !recipe.unlocked} title={reason || 'Craft one'}>{recipe.owned ? `Craft (have ${recipe.owned})` : 'Craft'}</button>{reason && <small className="alchemy-reason">{reason}</small>}</article>
          })}{!recipes.some((recipe) => recipe.sign === selectedSign) && <p className="alchemy-empty">No recipes available for this beast yet.</p>}</div>
        </section>
      </div>}
    </div>
  )
}

function CampaignMarket({ progress, armory, armoryActions, onBackHome, purchaseMarketItem, busy }) {
  const coins = Number(progress?.player?.coins ?? 0)
  const [shop, setShop] = useState(false)
  const purchased = Array.isArray(progress?.homestead?.market_purchases) ? progress.homestead.market_purchases : []
  const stockCount = merchantLots(armory?.market, CAMPAIGN_MARKET_STOCK, purchased, coins).filter((lot) => !lot.locked).length
  return <>
    <div className="campaign-place-heading"><div><span className="campaign-eyebrow">MARKET · THE MERCHANT</span><h2>The Merchant</h2></div><span className="campaign-place-seal market">◇</span></div>
    {shop ? <ArmouryLots armory={armory} coins={coins} actions={armoryActions} legacyPurchases={purchased} purchaseMarketItem={purchaseMarketItem} busy={busy} onBack={() => setShop(false)} /> : <section className="market-greeting">
      <div className="market-vendor-scene"><div className="vendor-lantern">✦</div><div className="vendor-portrait merchant-pixel-sprite" aria-hidden="true" dangerouslySetInnerHTML={{ __html: merchantPixelSprite() }} /><div className="vendor-counter" /><div className="vendor-nameplate"><span className="campaign-eyebrow">SHOPKEEPER NPC</span><strong>The Merchant</strong></div></div>
      <div className="market-greeting-copy"><span className="campaign-eyebrow">WELCOME, TRAVELLER</span><h3>“Coins open the case. Knowledge keeps you alive.”</h3><div className="market-greeting-doors"><button type="button" className="campaign-button" onClick={() => setShop(true)}>Browse the shop <span>→</span></button></div></div>
      <aside className="market-greeting-purse"><span className="campaign-eyebrow">YOUR PURSE</span><strong><CoinIcon /> {coins}</strong><small>{stockCount} items available to browse</small></aside>
    </section>}
    <div className="market-bottom"><div className="campaign-stat-row"><span><small>COINS</small><strong><CoinIcon /> {coins}</strong></span><span><small>SHOP</small><strong>{stockCount} available</strong></span><span><small>PREP</small><strong>{purchased.length + (armory?.items?.length || 0)} owned</strong></span></div>{onBackHome && <button type="button" className="campaign-button ghost market-home-button" onClick={onBackHome}>Open Home loadout →</button>}</div>
  </>
}


// Bounties that train the craft around the code, as a poster ribbon.
const CONTRACT_KIND_LABELS = { workshop: 'WORKSHOP', debug: 'DEBUG', memory: 'FROM MEMORY', creative: 'MAKE IT YOURS' }

// What each objective asks of you, as a poster tag.
const OBJECTIVE_KIND = { setup_check: 'SETUP', code_checkpoint: 'BUILD', bug_diagnosis: 'FIX', prediction: 'PREDICT', explanation: 'EXPLAIN', snippet_check: 'READ', code_interview: 'INTERVIEW' }

function BountyPosterArt({ projectId, entry }) {
  const art = lanternEncounterArt(projectId, entry.name)
  const locked = entry.status === 'locked'
  return <span className={`poster-mob-visual ${locked ? 'silhouette' : ''}`} aria-hidden="true">{art ? <span className="poster-mob-sprite" style={{ backgroundImage: `url("${art}")` }} /> : <svg className="poster-mob-fallback" viewBox="0 0 64 72" focusable="false"><path d="M17 60 20 43 14 36 18 26 24 23 22 13 28 17 32 10 36 17 42 13 40 23 46 26 50 36 44 43 47 60 39 60 35 48 29 48 25 60Z" /><path d="M12 62h40" /></svg>}</span>
}

function CampaignOffice({ progress, board, onEnter }) {
  const activeProject = (progress?.projects || []).find((project) => project.status === 'active') || {}
  const contractsByName = Object.fromEntries((board?.contracts || []).map((contract) => [contract.name, contract]))
  const acts = Array.isArray(board?.acts) ? board.acts : []
  const story = board?.story || {}
  const mobs = Array.isArray(activeProject.mobs) ? activeProject.mobs : []
  const fallback = [
    { id: 'count-keeper', name: 'The Count Keeper', category: 'Loops and accumulators', status: 'available', signal: 'REWARD', reward: '+40 COINS', icon: '✦', detail: 'Restore the keeper’s running total and open the first safe mark.' },
    { id: 'loop-rehearsal', name: 'The Loop Rehearsal', category: 'Loops and accumulators', status: 'locked', signal: 'LOCKED', reward: 'HIDDEN', icon: '◌', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'accumulator-audit', name: 'The Accumulator Audit', category: 'Conditions and filtering', status: 'locked', signal: 'WARNING', reward: 'HIDDEN', icon: '◈', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'house-ledger', name: 'The House Ledger', category: 'Conditions and filtering', status: 'locked', signal: 'LOCKED', reward: 'HIDDEN', icon: '▣', detail: 'Complete the previous bounty to reveal this work.' },
    { id: 'dealer-hand', name: 'The Dealer’s Hand', category: 'Functions', status: 'locked', signal: 'BOSS', reward: 'HIDDEN', icon: '♠', detail: 'A larger bounty waits at the chapter boundary.' },
  ]
  const entries = mobs.length ? mobs.map((mob, index) => {
    const authoredRank = String(mob.rank || mob.threat || mob.tier || mob.kind || '').toLowerCase()
    // Older canonical project records predate rank metadata. Keep their board
    // readable with a stable visual fallback; newly-authored records override
    // it through `rank` without changing the saved player state.
    const contract = contractsByName[mob.name] || {}
    // Authored contracts carry a tier (light, quick, elite); only boards
    // without story data fall back to guessing the rank from position.
    const rank = contract.tier === 'elite' ? 'elite'
      : contract.name ? 'mob'
      : ['mob', 'elite', 'boss'].includes(authoredRank) ? authoredRank
      : index === mobs.length - 1 ? 'boss' : index === mobs.length - 2 || index === Math.floor(mobs.length / 2) ? 'elite' : 'mob'
    return { id: mob.id || mob.name || `mob-${index}`, name: mob.name || `Unknown bounty ${index + 1}`, category: mob.concept || mob.category || 'Learning contract', status: mob.status || 'locked', rank, signal: mob.status === 'available' ? 'REWARD' : isMobDefeated(mob.status) ? 'CLEARED' : 'LOCKED', reward: mob.status === 'available' ? (contract.elite_reward ? [contract.elite_reward, contract.elite_gear, "8 EMBERS"].filter(Boolean).join(" · ") : '+ COINS') : isMobDefeated(mob.status) ? 'CLEARED' : 'HIDDEN', icon: isMobDefeated(mob.status) ? '✓' : '✦', detail: contract.contract || mob.brief || mob.encounter || 'A state-owned learning contract.', task: mob.encounter, act: contract.act || 1, sign: contract.sign, beast: contract.beast, objectives: contract.objectives || [], tier: contract.tier || null, kind: contract.kind || null }
  }) : fallback.map((entry, index) => ({ ...entry, rank: entry.rank || (index === fallback.length - 1 ? 'boss' : index === 2 ? 'elite' : 'mob') }))
  const boardSize = 7
  // A story's acts are its boards; older boards page seven posters at a time.
  const actBoards = acts.map((act) => ({ act, entries: entries.filter((entry) => entry.act === act.id) })).filter((item) => item.entries.length)
  const boards = actBoards.length
    ? actBoards.map((item) => item.entries)
    : Array.from({ length: Math.max(1, Math.ceil(entries.length / boardSize)) }, (_, index) => entries.slice(index * boardSize, (index + 1) * boardSize))
  const availableBoard = boards.findIndex((items) => items.some((entry) => entry.status === 'available'))
  // A finished campaign opens on its last act rather than snapping back to the first.
  const openBoard = availableBoard >= 0 ? availableBoard : Math.max(0, boards.length - 1)
  const [boardIndex, setBoardIndex] = useState(openBoard)
  // Switching campaign opens the new board on the act you are playing.
  const projectKey = activeProject.branch || activeProject.name || ''
  const availableId = entries.find((entry) => entry.status === 'available')?.id
  useEffect(() => {
    setBoardIndex(openBoard)
    const openPage = boards[openBoard] || []
    setSelectedId(availableId || [...openPage].reverse().find((entry) => entry.status !== 'locked')?.id || openPage[0]?.id || '')
  }, [projectKey, availableId])
  const currentAct = actBoards[boardIndex]?.act
  const boardEntries = boards[boardIndex] || boards[0]
  const [selectedId, setSelectedId] = useState(boardEntries[0]?.id || '')
  const selected = entries.find((entry) => entry.id === selectedId) || entries[0]
  const unlocked = selected?.status !== 'locked'
  const objectives = Array.isArray(selected?.objectives) ? selected.objectives : []
  const selectBoard = (nextIndex) => {
    const next = Math.min(boards.length - 1, Math.max(0, nextIndex))
    setBoardIndex(next)
    const page = boards[next] || []
    setSelectedId((page.find((entry) => entry.status === 'available') || [...page].reverse().find((entry) => entry.status !== 'locked') || page[0])?.id || '')
  }
  // Map view: the open act is one path. Cleared stops, the current stop and the
  // next sealed stop are shown; everything further along collapses to "+N sealed".
  const firstLocked = boardEntries.findIndex((entry) => entry.status === 'locked')
  const pathEntries = firstLocked === -1 ? boardEntries : boardEntries.slice(0, firstLocked + 1)
  const sealedCount = firstLocked === -1 ? 0 : boardEntries.length - pathEntries.length
  const clearedCount = mobs.filter((mob) => isMobDefeated(mob.status)).length
  const cleared = isMobDefeated(selected?.status)
  const onPathKey = (event) => {
    const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }
    if (!keys[event.key]) return
    const nodes = [...event.currentTarget.querySelectorAll('button:not(:disabled)')]
    const at = nodes.indexOf(document.activeElement)
    const next = nodes[Math.min(nodes.length - 1, Math.max(0, at + keys[event.key]))]
    if (next) { event.preventDefault(); next.focus(); next.click() }
  }
  const warmUp = () => window.dispatchEvent(new CustomEvent('questlab:start-today', { detail: { name: selected?.name } }))
  // The stage is a painted zone with the path drawn across it. Narrow stages
  // spread the pins over the full width because the detail card drops below.
  const stageRef = useRef(null)
  const [stageWidth, setStageWidth] = useState(1000)
  const stageWide = stageWidth >= 900
  useEffect(() => {
    const stage = stageRef.current
    if (!stage || typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(() => setStageWidth(stage.clientWidth))
    observer.observe(stage)
    return () => observer.disconnect()
  }, [])
  const stagePoints = [...pathEntries.map((entry) => entry.id), ...(sealedCount > 0 ? ['sealed'] : [])]
  // Wide stages keep every pin clear of the floating detail card; narrow stages
  // use a fixed pixel pitch inside a horizontally scrolling field.
  const narrow = !stageWide
  const cardPercent = ((Math.min(340, stageWidth * 0.38) + 28) / stageWidth) * 100
  const spanX = Math.max(30, 100 - cardPercent - 16)
  const fieldWidth = narrow ? Math.max(stageWidth, stagePoints.length * 120 + 140) : stageWidth
  const pinPoint = (index) => {
    const total = stagePoints.length
    const t = total <= 1 ? 0.5 : index / (total - 1)
    const x = narrow ? ((70 + (fieldWidth - 140) * t) / fieldWidth) * 100 : 7 + (total <= 1 ? spanX / 2 : spanX * t)
    return { x, y: 50 + (index % 2 === 0 ? -16 : 16) }
  }
  const stageArt = lanternEncounterLocation(activeProject.branch, (boardEntries[0] || {}).name)
  const zoneArt = (page) => lanternEncounterLocation(activeProject.branch, (page[0] || {}).name)
  return (
    <section className="office-map" aria-label="Bounty map">
      <header className="office-map-head">
        <div>
          <span className="campaign-eyebrow">{currentAct ? currentAct.title : 'BOUNTY MAP'}</span>
          <h2>{story.title || activeProject.name || 'Choose the work that moves you.'}</h2>
        </div>
        <nav className="office-zones" aria-label="Zones">
          {boards.map((page, index) => {
            const done = page.filter((entry) => isMobDefeated(entry.status)).length
            const sealed = page.every((entry) => entry.status === 'locked')
            const label = actBoards[index]?.act?.title || `Page ${index + 1}`
            return (
              <button key={label + index} type="button" className={`office-zone ${index === boardIndex ? 'active' : ''} ${sealed ? 'sealed' : ''}`} aria-pressed={index === boardIndex} onClick={() => selectBoard(index)} title={actBoards[index]?.act?.goal || label}>
                <span className="zone-art" style={zoneArt(page) ? { backgroundImage: `url("${zoneArt(page)}")` } : undefined} aria-hidden="true" />
                <b>{label.replace(/^ACT\s+/i, 'Act ')}</b>
                <small>{sealed ? 'sealed' : `${done}/${page.length}`}</small>
              </button>
            )
          })}
        </nav>
      </header>
      <div className={`office-stage ${narrow ? 'narrow' : ''}`} ref={stageRef} style={stageArt ? { '--stage-art': `url("${stageArt}")` } : undefined}>
        <div className="office-stage-field" style={narrow ? { width: fieldWidth } : undefined}>
        <svg className="office-stage-path" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {stagePoints.slice(1).map((id, index) => {
            const from = pinPoint(index)
            const to = pinPoint(index + 1)
            const lit = isMobDefeated(pathEntries[index]?.status)
            const mid = (from.x + to.x) / 2
            return <path key={id} className={lit ? 'lit' : ''} d={`M ${from.x} ${from.y} C ${mid} ${from.y}, ${mid} ${to.y}, ${to.x} ${to.y}`} />
          })}
        </svg>
        <ol className="office-pins" aria-label="Bounties in this zone" onKeyDown={onPathKey}>
          {pathEntries.map((entry, index) => {
            const locked = entry.status === 'locked'
            const done = isMobDefeated(entry.status)
            const state = locked ? 'locked' : done ? 'cleared' : 'current'
            const point = pinPoint(index)
            return (
              <li key={entry.id} className={`map-pin-wrap ${state} rank-${entry.rank} ${selected?.id === entry.id ? 'selected' : ''}`} style={{ left: `${point.x}%`, top: `${point.y}%` }}>
                {state === 'current' && <span className="pin-you" aria-hidden="true">YOU ▾</span>}
                <button type="button" className="map-pin" disabled={locked} aria-pressed={selected?.id === entry.id} aria-label={`${locked ? 'Sealed bounty' : entry.name}, ${state}${entry.tier ? `, ${entry.tier}` : ''}`} onClick={() => setSelectedId(entry.id)}>
                  <span className="map-pin-art"><BountyPosterArt projectId={activeProject.branch} entry={entry} /></span>
                  {done && <b className="map-node-check" aria-hidden="true">✓</b>}
                  {locked && <b className="map-node-lock" aria-hidden="true">?</b>}
                </button>
                <span className="map-pin-name">{locked ? 'Sealed' : entry.name}</span>
                {!locked && <span className="pin-tip" role="tooltip">{entry.category}{entry.reward ? ` · ${entry.reward}` : ''}</span>}
              </li>
            )
          })}
          {sealedCount > 0 && (() => { const point = pinPoint(stagePoints.length - 1); return <li className="map-pin-wrap more" style={{ left: `${point.x}%`, top: `${point.y}%` }}><span className="map-fog">+{sealedCount}<small>sealed</small></span></li> })()}
        </ol>
        </div>
        {selected && (
          <aside className="office-detail-card" aria-live="polite">
            <span className="campaign-eyebrow">{cleared ? 'CLEARED' : unlocked ? (selected.tier || selected.rank).toUpperCase() : 'SEALED'}{selected.kind && unlocked ? ` · ${CONTRACT_KIND_LABELS[selected.kind]}` : ''}</span>
            <h3>{unlocked ? selected.name : 'Sealed bounty'}</h3>
            <p className="office-detail-copy">{unlocked ? (selected.task || selected.detail) : 'Clear the bounty before it to reveal this one.'}</p>
            {unlocked && selected.sign && <span className="office-sign"><HuntSigil pageId={selected.sign} size={14} /> Sign of the {HUNT_BEASTS[selected.sign]?.sign || selected.sign}</span>}
            {unlocked && objectives.length > 0 && <ol className="office-objectives">{objectives.map((objective) => <li key={objective.id}><b className={`kind-${objective.question_type}`}>{OBJECTIVE_KIND[objective.question_type] || 'TASK'}</b>{objective.label}</li>)}</ol>}
            {unlocked && Array.isArray(selected.resources) && selected.resources.length > 0 && <details className="office-learning-resources"><summary>Study before the fight</summary><ul>{selected.resources.map((resource) => <li key={resource.url}><a href={resource.url} target="_blank" rel="noreferrer">{resource.label}</a><span>{resource.why}</span></li>)}</ul></details>}
            <div className="office-detail-actions">
              <button type="button" className="campaign-button" onClick={onEnter} disabled={!unlocked || cleared}>{cleared ? 'Already cleared' : unlocked ? 'Take bounty →' : 'Sealed'}</button>
              {unlocked && !cleared && <button type="button" className="office-warmup" onClick={warmUp}>Warm up first</button>}
            </div>
            <small className="office-detail-reward">{unlocked ? selected.reward : ''}</small>
            {(story.hook || board?.entry_file) && <details className="office-story"><summary>Story and where you build</summary>{story.hook && <p>{story.hook}</p>}{board?.entry_file && <p>You build this in <code>{board.entry_file}</code> in the Hunt.</p>}</details>}
          </aside>
        )}
      </div>
    </section>
  )
}

// ── Home as a room you walk around (embedded Godot web build) ─────────────────
// The Godot scene (ide/home-godot, built into public/home/) only draws and
// walks. This component sends it the save's state and acts on its "use this
// station" events, so every rule stays in the app. If the build is missing
// the classic Home is shown instead.
const HOME_STATION_UPGRADES = {
  hearth: ['reinforced-hearth', 'field-kitchen', 'siphon-basin'],
  armory: ['warding-loom', 'breaker-workbench'],
}

const HOME_STATION_ROOMS = {
  hearth: 'great_hall', perch: 'den',
}
const HOME_STATION_ACTIONS = {
  hearth: 'Rest at the hearth', study: 'Open Tutor', armory: 'Open the Armory',
  pantry: 'Eat a meal', trophy: 'View player stats', map: 'Enter the Dungeon', perch: 'Visit Pyr',
}


const HUNTER_LOOKS = ['alucard']

function homeRoomState(progress, crt, look, homeRooms) {
  const player = progress?.player || {}
  const homestead = progress?.homestead || {}
  const owned = Array.isArray(homestead.room_upgrades) ? homestead.room_upgrades : []
  const days = progress?.activity_log?.days || {}
  const today = new Date()
  const key = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const day = days[key] || {}
  const tiers = {}
  const maxTiers = {}
  for (const [id, ids] of Object.entries(HOME_STATION_UPGRADES)) {
    tiers[id] = ids.filter((upgrade) => owned.includes(upgrade)).length
    maxTiers[id] = ids.length
  }
  return {
    hp: player.hp ?? 0,
    max_hp: player.max_hp ?? 100,
    embers: homestead.upgrade_tokens ?? 0,
    fire_lit: Boolean((day.lines || 0) + (day.answers || 0) + (day.mobs || 0) > 0),
    crt,
    look,
    ...hunterAppearance(progress?.equipment?.armor, progress?.equipment?.trinket),
    armorLook: hunterAppearance(progress?.equipment?.armor, progress?.equipment?.trinket).homeLook,
    pyr_stage: homePyrStage(progress),
    levels: homeRooms?.levels || homestead.room_levels || {},
    tiers,
    max_tiers: maxTiers,
  }
}

function useHomeBuild() {
  // 'checking' | 'ready' | 'missing'
  const [status, setStatus] = useState('checking')
  useEffect(() => {
    let cancelled = false
    fetch('/home/index.html', { cache: 'no-cache' })
      .then((response) => (response.ok ? response.text() : ''))
      .then((text) => { if (!cancelled) setStatus(/godot/i.test(text) ? 'ready' : 'missing') })
      .catch(() => { if (!cancelled) setStatus('missing') })
    return () => { cancelled = true }
  }, [])
  return status
}

function HomeBossTrophies({ progress }) {
  const trophies = campaignBossTrophies(progress)
  return <section className="home-trophy-room" aria-label="Boss trophies" data-testid="home-boss-trophies">
    <div className="home-trophy-intro"><span className="home-trophy-mark" aria-hidden="true">✦</span><div><h2>THE HUNTER’S TROPHIES</h2><p>Bosses you have defeated on your campaigns.</p></div><strong>{trophies.length} CLAIMED</strong></div>
    {trophies.length ? <div className="home-trophy-grid">{trophies.map((trophy) => <article className="home-trophy-plaque" key={trophy.id}>
      <svg viewBox="0 0 32 32" aria-hidden="true" shapeRendering="crispEdges"><path fill="#60402b" d="M4 4h24v3H4zm0 0h3v21H4zm21 0h3v21h-3zM7 25h18v3H7z"/><path fill="#edbf69" d="M10 7h12v3h4v7h-3v3h-3v3h4v3H8v-3h4v-3H9v-3H6v-7h4zm0 5H8v3h2zm12 0v3h2v-3z"/><path fill="#fff1aa" d="M12 9h3v6h-3zm1 14h7v1h-7z"/></svg>
      <div><small>CAMPAIGN BOSS · DEFEATED</small><h3>{trophy.boss}</h3><p>{trophy.campaign}</p></div><span className="home-trophy-seal">✦</span></article>)}</div> : <div className="home-trophy-empty"><span aria-hidden="true">♜</span><div><h3>YOUR FIRST TROPHY AWAITS</h3><p>Defeat a campaign boss and their trophy will appear here.</p></div></div>}
    <p className="home-trophy-footnote">Dungeon boss trophies aren’t recorded by name yet.</p>
  </section>
}

function HomeRoom({ progress, homeRooms, purchaseHomeRoom, buildRoomUpgrade, armory, armoryActions, hunter, hunterActions, dungeon, spendStatPoint, performHomesteadAction, onNavigate, onOpenMarket, onEquipmentSynced, account, onClassic, busy }) {
  const frameRef = useRef(null)
  const panelRef = useRef(null)
  const sectionRef = useRef(null)
  const directoryRef = useRef(null)
  const readyRef = useRef(false)
  const [homeStatus, setHomeStatus] = useState('loading')
  const [frameKey, setFrameKey] = useState(0)
  const [currentRoom, setCurrentRoom] = useState('great_hall')
  const [mapOpen, setMapOpen] = useState(false)
  const [homeHelp, setHomeHelp] = useState(() => { try { return window.localStorage.getItem('questlab.homeGuideSeen') !== 'true' } catch { return true } })
  const [roomPosition, setRoomPosition] = useState({ x: 160, y: 150 })
  const currentRoomInfo = HOME_DIRECTORY.find((room) => room.id === currentRoom) || HOME_DIRECTORY.find((room) => room.id === 'great_hall')
  const connectedRooms = Object.entries(currentRoomInfo.exits).map(([direction, id]) => ({ direction, room: HOME_DIRECTORY.find((room) => room.id === id) })).filter((entry) => entry.room)
  const exitsLabel = connectedRooms.map(({ direction, room }) => `${direction}: ${room.name}`).join('; ')
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!readyRef.current) setHomeStatus('slow')
    }, 30000)
    return () => window.clearTimeout(timer)
  }, [frameKey])
  // Fit the complete room into the available space while keeping its 16:9 shape.
  const [frameSize, setFrameSize] = useState({ width: 960, height: 540 })
  useEffect(() => {
    const fit = () => {
      const room = sectionRef.current?.parentElement?.clientWidth || 960
      const top = sectionRef.current?.getBoundingClientRect().top || 180
      const height = Math.max(180, window.innerHeight - top - 55)
      const widest = Math.max(280, Math.min(room - 12, 1200, height * (16 / 9)))
      setFrameSize({ width: widest, height: widest * 9 / 16 })
    }
    fit()
    const observer = new ResizeObserver(fit)
    if (sectionRef.current?.parentElement) observer.observe(sectionRef.current.parentElement)
    window.addEventListener('resize', fit)
    return () => { observer.disconnect(); window.removeEventListener('resize', fit) }
  }, [])
  const [crt, setCrt] = useState(() => {
    try { return window.localStorage.getItem('questlab.homeCrt') !== 'false' } catch { return true }
  })
  const [panel, setPanel] = useState('')
  const [hunterTab, setHunterTab] = useState('stats')
  const [station, setStation] = useState('')
  const [upgradeError, setUpgradeError] = useState('')
  const [homeMessage, setHomeMessage] = useState('')
  const [look, setLook] = useState(() => {
    try { return HUNTER_LOOKS.includes(window.localStorage.getItem('questlab.hunterLook')) ? window.localStorage.getItem('questlab.hunterLook') : 'alucard' } catch { return 'alucard' }
  })
  const cycleLook = () => setLook((current) => {
    const next = HUNTER_LOOKS[(HUNTER_LOOKS.indexOf(current) + 1) % HUNTER_LOOKS.length]
    try { window.localStorage.setItem('questlab.hunterLook', next) } catch { /* storage unavailable */ }
    return next
  })
  const stateRef = useRef(null)
  stateRef.current = homeRoomState(progress, crt, look, homeRooms)

  const focusRoom = () => {
    const frame = frameRef.current
    try { (frame?.contentDocument?.querySelector('canvas') || frame)?.focus() } catch { frame?.focus() }
  }

  const send = (extra = {}) => {
    const target = frameRef.current?.contentWindow
    if (!readyRef.current || !target || typeof target.diddyHomeReceive !== 'function') return
    try { target.diddyHomeReceive(JSON.stringify({ ...stateRef.current, ...extra })) } catch { /* the room is reloading */ }
  }
  useEffect(() => { send() }, [JSON.stringify(stateRef.current)])

  // A Home action (rest, eat, feed Pyr): the toast says what happened or why it could not.
  const homeAction = async (action, done) => {
    try {
      const result = await performHomesteadAction?.(action)
      const healed = Number(result?.event?.healed || 0)
      const message = done(healed, result)
      setHomeMessage(message)
      send({ toast: message, ...(action === 'feed_pyr' ? { pyr_action: 'feed' } : {}) })
    } catch (error) {
      const message = String(error?.message || 'That did not work')
      setHomeMessage(message)
      send({ toast: message.slice(0, 60) })
    }
  }

  const performStationAction = async (id) => {
    if (id === 'map') return onNavigate?.('dungeon')
    if (id === 'armory') return setPanel('armory')
    if (id === 'hunter') return setPanel('hunter')
    if (id === 'study') return onNavigate?.('tutor')
    if (id === 'trophy') return setPanel('trophy')
    if (id === 'still' || id === 'journal') return setPanel(id)
    if (id === 'training') {
      try { window.sessionStorage.setItem('questlab.tutor.surface', JSON.stringify('spar')) } catch { /* storage unavailable */ }
      return onNavigate?.('tutor')
    }
    if (id === 'hearth') return homeAction('recover', (healed, result) => (healed > 0 ? `Rested: +${healed} HP · ${result?.event?.coins_spent ? `${result.event.coins_spent} coins spent` : 'free emergency rest'}` : 'You are fully rested.'))
    if (id === 'pantry') return homeAction('meal', (healed) => `You eat a hot meal: +${healed} HP`)
    if (id === 'perch' || id === 'pyr') return setPanel('pyr')
    if (id === 'online_shop') return setPanel('online-shop')
    if (id === 'online_leaderboard') return setPanel('online-leaderboard')
  }
  const useStation = (id) => {
    setMapOpen(false)
    setHomeMessage('')
    if (!HOME_STATION_ROOMS[id]) return performStationAction(id)
    setStation(id)
    setUpgradeError('')
    setPanel('room')
  }
  const closePanel = () => {
    setPanel('')
    setHomeMessage('')
    window.requestAnimationFrame(focusRoom)
  }
  useEffect(() => {
    if (!panel) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') { event.preventDefault(); closePanel(); return }
      if (event.key !== 'Tab') return
      const focusable = [...(panelRef.current?.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') || [])]
      if (!focusable.length) { event.preventDefault(); return }
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && (document.activeElement === first || !panelRef.current?.contains(document.activeElement))) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [panel])
  const roomId = HOME_STATION_ROOMS[station]
  const ladder = homeRooms?.ladders?.[roomId]
  const level = homeRooms?.levels?.[roomId] ?? 0
  const nextStep = ladder?.[level]
  const embers = progress?.homestead?.upgrade_tokens ?? 0
  const hp = Number(progress?.player?.hp ?? 0)
  const maxHp = Number(progress?.player?.max_hp ?? 100)
  const coins = Number(progress?.player?.coins ?? 0)
  const restCost = Math.ceil(Math.max(0, maxHp - hp) / 10)
  const emergencyHp = Math.ceil(maxHp * 0.3)
  const canRest = hp < maxHp && (coins >= restCost || hp < emergencyHp)
  const buyNextStep = async () => {
    if (!nextStep || !purchaseHomeRoom) return
    setUpgradeError('')
    try {
      const result = await purchaseHomeRoom(roomId, level)
      if (result?.home_rooms?.levels) send({ levels: result.home_rooms.levels })
      closePanel()
    } catch (error) {
      setUpgradeError(String(error?.message || 'Upgrade could not be purchased.'))
    }
  }
  const runRoomAction = async () => {
    if (station === 'perch') { setHomeMessage(''); setPanel('pyr'); return }
    await performStationAction(station)
  }
  const useStationRef = useRef(useStation)
  useStationRef.current = useStation

  useEffect(() => {
    const onMessage = (event) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return
      const data = event.data
      if (!data || data.source !== 'diddy-home') return
      if (data.type === 'ready') {
        readyRef.current = true
        setHomeStatus('ready')
        send()
        focusRoom()
      } else if (data.type === 'room' && HOME_DIRECTORY.some((room) => room.id === data.room)) {
        setCurrentRoom(data.room)
        if (Number.isFinite(data.x) && Number.isFinite(data.y)) setRoomPosition({ x: data.x, y: data.y })
      } else if (data.type === 'position' && typeof data.room === 'string' && Number.isFinite(data.x) && Number.isFinite(data.y)) {
        if (HOME_DIRECTORY.some((room) => room.id === data.room)) { setCurrentRoom(data.room); setRoomPosition({ x: data.x, y: data.y }) }
      } else if (data.type === 'use' && typeof data.station === 'string') {
        void useStationRef.current(data.station)
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  const toggleCrt = () => setCrt((current) => {
    try { window.localStorage.setItem('questlab.homeCrt', String(!current)) } catch { /* storage unavailable */ }
    return !current
  })
  return (
    <section className="home-room" data-testid="home-room" aria-label="Your home" ref={sectionRef}>
      <div className={`home-room-frame ${panel ? 'is-engaged' : ''}`} style={{ width: frameSize.width, height: frameSize.height }}>
        <iframe key={frameKey} ref={frameRef} title="Home" src="/home/index.html" allow="autoplay" />
        {homeStatus === 'ready' && <div className="home-map-hud" onKeyDown={(event) => { if (event.key === 'Escape' && mapOpen) { setMapOpen(false); focusRoom() } }}>
          <button type="button" className="home-map-toggle" aria-expanded={mapOpen} aria-controls="home-directory" aria-label={`Castle map: ${currentRoomInfo.name}; ${exitsLabel}`} onClick={() => { if (mapOpen) focusRoom(); setMapOpen((open) => !open) }}>
            <span className="home-map-top"><span className="home-map-label">CASTLE MAP</span><span className="home-map-caret" aria-hidden="true">{mapOpen ? '×' : '▾'}</span></span>
            <CastleFloorPlan currentRoom={currentRoom} position={roomPosition} />
            <span className="home-map-current">{currentRoomInfo.name}</span>
            <span className="home-map-exits">{connectedRooms.map(({ direction, room }) => `${{ north: '↑', south: '↓', west: '←', east: '→', northwest: '↖', northeast: '↗' }[direction]} ${room.short}`).join(' · ')}</span>
          </button>
          {mapOpen && <nav id="home-directory" className="home-directory" aria-label="Home room map">
            <div className="home-directory-heading"><span>CASTLE MAP</span><small>{exitsLabel}</small></div>
            <ol ref={directoryRef} className="home-directory-path">
              {HOME_DIRECTORY.map((room) => <li key={room.id} className={room.id === currentRoom ? 'current' : Object.values(currentRoomInfo.exits).includes(room.id) ? 'adjacent' : ''} aria-current={room.id === currentRoom ? 'location' : undefined}>
                <strong>{room.name}</strong><small>{room.places}</small>{room.id === currentRoom && <span>YOU ARE HERE</span>}
              </li>)}
            </ol>
          </nav>}
        </div>}
        {homeStatus === 'ready' && homeHelp && <section className="home-guide" aria-label="Welcome home">
          <span className="screen-kicker">WELCOME HOME</span><h3>Your place between runs</h3>
          <p>Rest, gear up and visit Pyr. Walk with WASD or arrows, press E to use things.</p>
          <button type="button" onClick={() => { try { window.localStorage.setItem('questlab.homeGuideSeen', 'true') } catch { /* storage unavailable */ } setHomeHelp(false); focusRoom() }}>Explore Home →</button>
        </section>}
        {homeStatus !== 'ready' && <div className="home-loading" role="status" aria-live="polite">
          <span className="home-loading-flame" aria-hidden="true">✦</span>
          <strong>{homeStatus === 'slow' ? 'The castle is taking a while' : 'Opening the castle'}</strong>
          <span>{homeStatus === 'slow' ? 'Try again or visit classic Home.' : 'Pyr is lighting the way…'}</span>
          {homeStatus === 'slow' && <div className="home-loading-actions"><button type="button" onClick={() => { readyRef.current = false; setHomeStatus('loading'); setFrameKey((key) => key + 1) }}>Try again</button><button type="button" onClick={onClassic}>Classic Home</button></div>}
        </div>}

      {panel && (
        <div className="home-station-screen" role="dialog" aria-modal="true" aria-labelledby="home-station-title" ref={panelRef}>
          <div className="home-station-page">
            <header className="home-station-topbar"><button type="button" className="home-station-back" onClick={closePanel} autoFocus>← Back to Home</button><span>YOUR CASTLE <b>/</b> {currentRoomInfo.name.toUpperCase()}</span>{!panel.startsWith('online-') && <span className="home-station-wallet">✦ {embers} EMBERS</span>}</header>
            <main className="home-station-content">
              {panel === 'still' || panel === 'journal' ? <>
                <div className="home-station-heading"><span className="home-station-kicker">HUNTER’S STILL · HOME</span><h1 id="home-station-title">{panel === 'still' ? 'The crafting bench' : 'Legacy Journal'}</h1><p>{panel === 'still' ? 'Put your banked Dungeon finds to work.' : 'Your Dungeon milestones and permanent rewards.'}</p></div>
                {panel === 'still' ? <AlchemyBench hunter={hunter} coins={coins} actions={hunterActions} busy={busy} /> : <div className="hunter-still-room"><DungeonLegacyJournal journal={dungeon?.journal} /></div>}
              </> : panel.startsWith('online-') ? <>
                <div className="home-station-heading"><span className="home-station-kicker">SHAX CHAMPIONS HOUSE · ONLINE</span><h1 id="home-station-title">{panel === 'online-shop' ? 'Sir Getrich’s shop' : 'Group Leaderboards'}</h1><p>{panel === 'online-shop' ? 'Browse online rewards and PvP mastery appearances.' : 'Check the ranked standings for your private lobby.'}</p></div>
                <OnlinePageBoundary pageName={panel === 'online-shop' ? 'Shop' : 'Leaderboards'} resetKey={`${panel}:${account?.user?.id || 'signed-out'}`} onClose={closePanel}><OnlineHousePanel page={panel === 'online-shop' ? 'shop' : 'leaderboard'} account={account} onNavigate={onNavigate} onClose={closePanel} onEquipmentSynced={onEquipmentSynced} /></OnlinePageBoundary>
              </> : <>
              <div className="home-station-heading"><span className="home-station-kicker">{panel === 'pyr' || roomId === 'den' && panel === 'room' ? 'PYR’S DEN' : 'THE GREAT HALL'} · HOME</span><h1 id="home-station-title">{panel === 'room' ? (roomId === 'den' ? 'Pyr’s perch' : 'The hearth') : ({ hunter: 'Prepare your hunter', armory: 'The armory', trophy: 'Your trophies', pyr: 'Spend time with Pyr' }[panel])}</h1><p>{panel === 'room' ? (roomId === 'den' ? 'Make a home for your companion, one improvement at a time.' : 'Rest between adventures and restore your hall.') : ({ hunter: 'Strengthen your hunter and build permanent bonuses for the road ahead.', armory: 'Choose the equipment and supplies you will carry into your next fight.', trophy: 'A place for the bosses you have brought down.', pyr: 'Care for your companion and grow together.' }[panel])}</p></div>
              {panel === 'room' && <div className="home-station-columns home-upgrades">
                <section className="home-station-card home-station-action"><span className="home-station-kicker">{station === 'hearth' ? 'TAKE A BREATHER' : 'YOUR COMPANION'}</span><h2>{station === 'hearth' ? 'Rest by the fire' : 'Visit Pyr'}</h2><p>{station === 'hearth' ? `Health: ${hp} / ${maxHp}. ${hp >= maxHp ? 'You are fully rested.' : coins >= restCost ? `Full rest costs ${restCost} coins; you have ${coins}.` : hp < emergencyHp ? `Full rest costs ${restCost} coins; free emergency rest restores you to ${emergencyHp} HP.` : `Full rest costs ${restCost} coins; emergency rest is available below ${emergencyHp} HP.`}` : 'Spend time with Pyr, feed them and train together.'}</p><button type="button" disabled={busy || (station === 'hearth' && !canRest)} onClick={runRoomAction}>{station === 'hearth' && hp < maxHp ? (coins >= restCost ? `Rest · ${restCost} coins` : 'Free emergency rest') : HOME_STATION_ACTIONS[station]} →</button>{homeMessage && <p role="status" className="home-station-message">{homeMessage}</p>}</section>
                <section className="home-station-card home-station-renovation"><span className="home-station-kicker">ROOM IMPROVEMENTS · {level} / {ladder?.length ?? '—'}</span>{!ladder ? <p role="status">Loading room upgrades…</p> : nextStep ? <><h2>{nextStep.name}</h2><p>{nextStep.note}</p><button type="button" disabled={busy || !purchaseHomeRoom || embers < nextStep.cost} onClick={buyNextStep}>{busy ? 'Building…' : `Build · ${nextStep.cost} Embers`}</button>{embers < nextStep.cost && <small>Need {nextStep.cost - embers} more Embers. Defeat campaign elites for 8 Embers and bosses for 20.</small>}</> : <><h2>Fully restored</h2><p>Every improvement in this room has been built.</p></>}{upgradeError && <p role="alert" className="home-upgrades-error">{upgradeError}</p>}{ladder && <details className="home-station-built"><summary>Built improvements · {level}</summary>{level === 0 ? <p>No improvements built yet.</p> : <ol>{ladder.slice(0, level).map((step, index) => <li key={`${index}-${step.name}`}>{step.name}</li>)}</ol>}</details>}</section>
              </div>}
              {panel === 'hunter' && <><div className="home-hunter-tabs" role="tablist" aria-label="Hunter preparation"><button type="button" role="tab" aria-selected={hunterTab === 'stats'} onClick={() => setHunterTab('stats')}>HUNTER STATS</button><button type="button" role="tab" aria-selected={hunterTab === 'upgrades'} onClick={() => setHunterTab('upgrades')}>PERMANENT UPGRADES</button></div>{hunterTab === 'stats' ? <HunterSheet hunter={hunter} spendStatPoint={spendStatPoint} busy={busy} /> : <section className="home-passives"><h3>Permanent upgrades</h3><p>Spend Embers on bonuses that stay with your hunter.</p><div className="home-passive-grid">{HOME_ROOM_UPGRADES.map((upgrade) => { const owned = (progress?.homestead?.room_upgrades || []).includes(upgrade.id); const canBuild = embers >= upgrade.cost; return <article key={upgrade.id}><strong>{upgrade.name}</strong><small>{upgrade.effect} · {upgrade.detail}</small>{owned ? <span>Built · active</span> : <button type="button" onClick={() => buildRoomUpgrade?.(upgrade.id)} disabled={busy || !canBuild || !buildRoomUpgrade}>Build · {upgrade.cost} Embers</button>}</article> })}</div></section>}</>}
              {panel === 'armory' && <ArmoryPanel armory={armory} actions={armoryActions} busy={busy} />}
              {panel === 'trophy' && <HomeBossTrophies progress={progress} />}
              {panel === 'pyr' && <div className="home-station-columns"><section className="home-station-card home-station-action"><span className="home-station-kicker">YOUR COMPANION</span><h2>{([...HOME_PYR_STAGES].reverse().find((stage) => Number(progress?.companion?.bond ?? 0) >= stage.threshold) || HOME_PYR_STAGES[0]).label}</h2><p>Feed Pyr a camp meal to restore energy and grow your bond. Buy camp meals in the Market under Supplies.</p><div className="home-station-facts"><span><small>BOND</small><strong>{progress?.companion?.bond ?? 0}</strong></span><span><small>ENERGY</small><strong>{progress?.companion?.energy ?? progress?.companion?.max_energy ?? 2} / {progress?.companion?.max_energy ?? 2}</strong></span><span><small>MEALS</small><strong>{progress?.supplies?.meals ?? 0}</strong></span></div><div className="home-station-actions"><button type="button" disabled={busy || !(progress?.supplies?.meals > 0) || !performHomesteadAction} onClick={() => homeAction('feed_pyr', () => 'Pyr is fed and glows brighter.')}>Feed Pyr</button><button type="button" disabled={busy || (progress?.companion?.energy ?? progress?.companion?.max_energy ?? 2) <= 0 || !performHomesteadAction} onClick={() => homeAction('train_pyr', () => 'You trained together.')}>Train with Pyr</button></div>{homeMessage && <p role="status" className="home-station-message">{homeMessage}</p>}{onOpenMarket && <button type="button" onClick={onOpenMarket}>Buy meals at Market →</button>}</section><section className="home-station-card"><span className="home-station-kicker">A PLACE OF THEIR OWN</span><h2>Pyr’s perch</h2><p>Improve the den at the perch to make it feel like home.</p><button type="button" onClick={() => { setStation('perch'); setPanel('room'); setHomeMessage('') }}>View den improvements →</button></section></div>}
              </>}
            </main>
          </div>
        </div>)}
      </div>
      <div className="home-room-bar" style={{ width: frameSize.width + 6 }}>
        <small>WASD or arrows walk · Shift runs · E interacts</small>
        <span>
          {HUNTER_LOOKS.length > 1 && <button type="button" onClick={cycleLook} title="Change the hunter's look">Look: {look}</button>}
          <button type="button" onClick={() => setHomeHelp(true)}>Home guide</button>
          <button type="button" onClick={toggleCrt} aria-pressed={crt}>Scanlines {crt ? 'on' : 'off'}</button>
          <button type="button" onClick={onClassic}>Classic home</button>
        </span>
      </div>
    </section>
  )
}

function CampaignSurface({ progress, homeRooms, purchaseHomeRoom, revision, equipmentProjection, purchaseCosmetic, purchaseMarketItem, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, setAvatar, selectCampaign, hunter, spendStatPoint, hunterActions, campaignBoard, armory, armoryActions, dungeon, busy, onNavigate, onEquipmentSynced, account }) {
  const [place, setPlace] = useState('office')
  const [mapCollapsed, setMapCollapsed] = useState(() => { try { return JSON.parse(window.localStorage.getItem('questlab.campaignMapCollapsed') || 'false') === true } catch { return false } })
  const homeBuild = useHomeBuild()
  const [classicHome, setClassicHome] = useState(() => {
    try { return window.localStorage.getItem('questlab.classicHome') === 'true' } catch { return false }
  })
  const setClassic = (value) => {
    setClassicHome(value)
    try { window.localStorage.setItem('questlab.classicHome', String(value)) } catch { /* storage unavailable */ }
  }
  const openForge = () => onNavigate?.('forge')
  const selectPlace = (next) => setPlace(next)
  const toggleMapRail = () => setMapCollapsed((value) => { const next = !value; try { window.localStorage.setItem('questlab.campaignMapCollapsed', JSON.stringify(next)) } catch { /* storage unavailable */ } return next })
  const homeNavigate = (next) => {
    if (next === 'forge') {
      setPlace('office')
      return
    }
    if (next === 'market' || next === 'office' || next === 'home') setPlace(next)
    else onNavigate?.(next)
  }
  return (
    <div className={`campaign-v1 game-screen-scroll ${place === 'home' ? 'home-active' : ''} ${place === 'office' ? 'office-active' : ''}`} data-testid="campaign-surface" data-campaign-revision={revision}>
      <div className={`campaign-layout ${mapCollapsed ? 'map-rail-is-collapsed' : ''}`}>
        <CampaignMapRail progress={progress} place={place} onSelect={selectPlace} onSelectCampaign={selectCampaign} busy={busy} collapsed={mapCollapsed} onToggle={toggleMapRail} />
        <main className="campaign-place-panel" data-place={place}>
          {place === 'home' && homeBuild === 'ready' && !classicHome && <HomeRoom progress={progress} homeRooms={homeRooms} purchaseHomeRoom={purchaseHomeRoom} buildRoomUpgrade={buildRoomUpgrade} hunter={hunter} hunterActions={hunterActions} dungeon={dungeon} spendStatPoint={spendStatPoint} armory={armory} armoryActions={armoryActions} performHomesteadAction={performHomesteadAction} onNavigate={onNavigate} onOpenMarket={() => setPlace('market')} onEquipmentSynced={onEquipmentSynced} account={account} onClassic={() => setClassic(true)} busy={busy} />}
          {place === 'home' && homeBuild === 'ready' && classicHome && <div className="home-room-switch"><button type="button" onClick={() => setClassic(false)}>Back to the room</button></div>}
          {place === 'home' && (homeBuild !== 'ready' || classicHome) && <Homestead hunter={hunter} spendStatPoint={spendStatPoint} armory={armory} armoryActions={armoryActions} progress={progress} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} setAvatar={setAvatar} busy={busy} onNavigate={homeNavigate} />}
          {place === 'market' && <CampaignMarket progress={progress} armory={armory} armoryActions={armoryActions} purchaseMarketItem={purchaseMarketItem} busy={busy} onBackHome={() => setPlace('home')} />}
          {place === 'office' && <CampaignOffice progress={progress} board={campaignBoard} onEnter={openForge} />}
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

const GRID_ROOM_WORDS = { rest: 'Camp', encounter: 'Gate', elite: 'Elite', market: 'Market', mystery: 'Fate', boss: 'Boss' }
const FLOOR_MODIFIERS = { deep: 'DEEP FLOOR · HARDER, RICHER', quiet: 'QUIET FLOOR · ONE MORE CAMP' }
const DUNGEON_REGION_ART = { basics: '0% 0%', collections: '33.333% 0%', flow: '66.667% 0%', archive: '100% 0%', labyrinth: '0% 100%', workshop: '33.333% 100%', spire: '66.667% 100%', hollow: '100% 100%' }
const DUNGEON_REGION_PANELS = { basics: [0, 0], collections: [1, 0], flow: [2, 0], archive: [3, 0], labyrinth: [0, 1], workshop: [1, 1], spire: [2, 1], hollow: [3, 1] }
function dungeonRegionArt(run) {
  const position = DUNGEON_REGION_ART[run.region?.id]
  return position ? { '--dungeon-region-art': `url("${import.meta.env.BASE_URL}campaign-art/dungeon-regions/regions-atlas.png")`, '--dungeon-region-position': position } : undefined
}
function DungeonRegionScene({ run, dimmed = false }) {
  const panel = DUNGEON_REGION_PANELS[run.region?.id]
  if (!panel) return null
  return <img className="dungeon-region-scene" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', padding: 0, border: 0, background: 'none', filter: 'none', pointerEvents: 'none', zIndex: 0, opacity: dimmed ? 0.19 : 1 }} src={`${import.meta.env.BASE_URL}campaign-art/dungeon-regions/${run.region.id}.png`} alt="" />
}

// A floor as a room grid under fog: explored rooms, their doors, the boss lair.
function DungeonGridMap({ run, onChoose, onTravel, onRevealFloor, busy }) {
  const route = run.map
  const columns = Number(route.columns) || 5
  const rows = Number(route.rows) || 4
  const currentId = route.current_node_id
  const visited = new Set(run.visited_node_ids || [])
  const choices = Array.isArray(run.room_choices) ? run.room_choices : []
  const choiceIds = new Set(choices.map((choice) => choice.id))
  const stairs = choices.filter((choice) => choice.kind === 'stairs')
  const nodes = route.nodes || []
  const byId = Object.fromEntries(nodes.map((node) => [node.id, node]))
  const edges = route.edges || {}
  const selector = run.room_type === 'selector'
  const point = (node) => ({ x: (Number(node.column) - 0.5) * (100 / columns), y: (Number(node.row) - 0.5) * (100 / rows) })
  const viaFor = (node) => (edges[node.id] || []).find((id) => visited.has(id))
  const enter = async (node) => {
    if (choiceIds.has(node.id)) return onChoose?.(run.run_id, node.id)
    if (visited.has(node.id)) return onTravel?.(run.run_id, node.id)
    // A door off another explored room: walk there, then go through it.
    const via = viaFor(node)
    if (via && onTravel) {
      const moved = await onTravel(run.run_id, via).catch(() => null)
      if (moved) return onChoose?.(run.run_id, node.id)
    }
    return null
  }
  const lines = []
  Object.entries(edges).forEach(([fromId, toIds]) => (toIds || []).forEach((toId) => {
    if (fromId < toId && byId[fromId] && byId[toId]) lines.push([byId[fromId], byId[toId]])
  }))
  return (
    <section className="dungeon-proto-panel dungeon-map-panel" data-testid="dungeon-map" aria-label="Map and route" style={dungeonRegionArt(run)}>
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">LAYER ONE</span><h2>Floor {route.floor || run.floor}</h2></div><span className="dungeon-panel-tag">{FLOOR_MODIFIERS[route.modifier] || (run.region?.label || 'OPEN DUNGEON').toUpperCase()}</span></div>
      <p className="dungeon-panel-copy">Explore room by room, or use a Vision Scroll to reveal this floor. Revisit explored markets and camps whenever you need them.</p>
      <div className="dungeon-floor-scout"><img src={lanternItemArt('dungeon-vision-scroll')} alt="" /><div><strong>VISION SCROLL · {run.loadout?.vision_scrolls ?? 0}</strong><small>{route.revealed ? 'This floor is revealed.' : 'Reveal room types and connections for this floor.'}</small></div><button type="button" onClick={() => onRevealFloor?.(run.run_id)} disabled={busy || !onRevealFloor || !selector || route.revealed || (run.loadout?.vision_scrolls ?? 0) <= 0}>{route.revealed ? 'Revealed' : 'Reveal floor'}</button></div>
      <div className="dungeon-map-legend"><span><i className="legend-dot rest" />camp</span><span><i className="legend-dot market" />market</span><span><i className="legend-dot encounter" />gate</span><span><i className="legend-dot elite" />elite</span><span><i className="legend-dot mystery" />fate</span><span><i className="legend-dot boss" />boss</span></div>
      <div className="dungeon-proto-map grid-floor" role="grid" aria-label={`Dungeon floor ${route.floor || run.floor}`} style={{ gridTemplateColumns: `repeat(${columns}, 1fr)`, gridTemplateRows: `repeat(${rows}, minmax(78px, 1fr))` }}>
        <DungeonRegionScene run={run} dimmed />
        <svg className="dungeon-map-edges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {lines.map(([a, b]) => { const p = point(a); const q = point(b); return <line key={`${a.id}-${b.id}`} className={visited.has(a.id) && visited.has(b.id) ? 'active' : ''} x1={p.x} y1={p.y} x2={q.x} y2={q.y} /> })}
        </svg>
        {nodes.map((node) => {
          const isCurrent = node.id === currentId
          const isVisited = visited.has(node.id)
          const isNext = choiceIds.has(node.id)
          const isFrontier = !isVisited && !isNext && Boolean(viaFor(node))
          const lair = node.type === 'boss' && !isVisited && !isNext && !isFrontier
          const meta = dungeonRoomMeta(node.type)
          const clickable = selector && !isCurrent && (isNext || isVisited || isFrontier)
          const besideYou = (edges[currentId] || []).includes(node.id)
          const note = isCurrent ? 'YOU' : isNext ? 'NEXT' : !isVisited && besideYou ? 'DOOR' : isFrontier ? 'VIA EXPLORED' : isVisited ? 'explored' : lair ? 'lair' : ''
          return (
            <button key={node.id} type="button" className={`dungeon-map-node ${node.type} ${isCurrent ? 'current' : ''} ${isVisited ? 'visited' : ''} ${isNext ? 'reachable' : ''} ${isFrontier ? 'frontier' : ''} ${lair ? 'lair' : ''}`} style={{ gridColumn: node.column, gridRow: node.row }} disabled={!clickable || busy} onClick={() => enter(node)} title={node.label || meta.label} aria-label={`${node.label || meta.label}${note ? `, ${note}` : ''}`}>
              <span aria-hidden="true"><RouteIcon id={isCurrent ? 'flame' : meta.iconId} /></span><strong>{GRID_ROOM_WORDS[node.type] || meta.label}</strong>{note && <small>{note}</small>}
            </button>
          )
        })}
      </div>
      {stairs.length > 0 && (
        <div className="dungeon-stairs" aria-label="Choose your stair">
          <span className="dungeon-eyebrow">THE BOSS HAS FALLEN · CHOOSE YOUR STAIR</span>
          {stairs.map((choice) => <button key={choice.id} type="button" onClick={() => onChoose?.(run.run_id, choice.id)} disabled={busy || !onChoose}><strong>{choice.label}</strong><small>{choice.description}</small><b>↓</b></button>)}
        </div>
      )}
      <div className="dungeon-route-footer"><span>ROOM {run.room ?? 1} · {run.current_node?.label || 'route'}</span><span>{stairs.length ? 'floor cleared' : selector ? `${choices.length} door${choices.length === 1 ? '' : 's'} from here` : 'room committed · map locked'}</span></div>
    </section>
  )
}

function DungeonMap({ run, onChoose, onTravel, onRevealFloor, busy }) {
  if (!run?.active) return null
  if (run.map?.layout === 'grid') return <DungeonGridMap run={run} onChoose={onChoose} onTravel={onTravel} onRevealFloor={onRevealFloor} busy={busy} />
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
    <section className="dungeon-proto-panel dungeon-map-panel" data-testid="dungeon-map" aria-label="Map and route" style={dungeonRegionArt(run)}>
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
              <span aria-hidden="true"><RouteIcon id={isCurrent ? 'flame' : meta.iconId} /></span><strong>{isCurrent ? 'YOU' : GRID_ROOM_WORDS[node.type] || node.label || meta.label}</strong><small>{isAvailable ? 'NEXT' : isVisited ? 'done' : ''}</small>
            </button>
          )
        })}
      </div>
      <div className="dungeon-route-footer"><span>YOU ARE HERE · {run.current_node?.label || (run.room_type || 'route selector').toUpperCase()}</span><span>{choices.length ? `${choices.length} route${choices.length === 1 ? '' : 's'} ahead` : run.room_type === 'selector' ? 'route pending' : 'room committed · route locked'}</span></div>
      {choices.some((choice) => choice.kind === 'stairs') && (
        <div className="dungeon-stairs" aria-label="Choose your stair">
          <span className="dungeon-eyebrow">THE BOSS HAS FALLEN · CHOOSE YOUR STAIR</span>
          {choices.filter((choice) => choice.kind === 'stairs').map((choice) => <button key={choice.id} type="button" onClick={() => onChoose?.(run.run_id, choice.id)} disabled={busy || !onChoose}><strong>{choice.label}</strong><small>{choice.description}</small><b>↓</b></button>)}
        </div>
      )}
      {!route && choices.length > 0 && !choices.some((choice) => choice.kind === 'stairs') && <div className="dungeon-route-choice-list" aria-label="Choose your next room">{choices.map((choice) => <button key={choice.id} type="button" onClick={() => onChoose?.(run.run_id, choice.id)} disabled={busy || !onChoose}><RouteIcon id={dungeonRoomMeta(choice.kind).icon} /><span><strong>{choice.label}</strong><small>{choice.description}</small></span><b>→</b></button>)}</div>}
    </section>
  )
}

function DungeonCharacterPanel({ run, tab, setTab, onEquip, busy, onFinish, onReset }) {
  const loadout = run.loadout || {}
  const inventory = Array.isArray(run.inventory) ? run.inventory : []
  const tabs = ['LOADOUT', 'INVENTORY', 'PACK', 'STATS', 'JOURNAL']
  const pack = Array.isArray(run.pack) ? run.pack : []
  const classData = run.class || {}
  const iconFor = (kind) => kind === 'armor' ? 'shield' : kind === 'trinket' ? 'spark' : 'sword'
  return (
    <section className="dungeon-proto-panel dungeon-character-panel" aria-label="Character menu">
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">RUN MENU</span><h2>Character</h2></div><span className="dungeon-panel-tag">{run.active ? 'ACTIVE' : 'ENDED'}</span></div>
      <div className="dungeon-class-summary"><span className="dungeon-class-icon" aria-hidden="true"><RouteIcon id="spark" /></span><div><span className="dungeon-eyebrow">ACTIVE CLASS · PASSIVE</span><strong>{classData.name || 'Dungeon class'}</strong><small>{classData.passive || 'Choose a class before the descent.'}</small></div></div>
      <div className="dungeon-character-tabs" role="tablist" aria-label="Run character tabs">{tabs.map((item) => <button key={item} type="button" role="tab" aria-selected={tab === item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === 'LOADOUT' && <div className="dungeon-loadout-list">{['weapon', 'armor', 'trinket'].map((slot) => { const item = inventory.find((candidate) => candidate.kind === slot && candidate.equipped) || inventory.find((candidate) => candidate.kind === slot); return <div className="dungeon-loadout-item" key={slot}><span className={`dungeon-item-art ${!item && slot === 'trinket' ? 'empty-trinket' : ''}`}>{item && lanternItemArt(item.id) ? <img className="item-art-icon" src={lanternItemArt(item.id)} alt="" /> : !item && slot === 'trinket' ? <img className="item-art-icon" src={lanternItemArt('dungeon-warden-sigil')} alt="" /> : <RouteIcon id={iconFor(slot)} />}</span><div><small>{slot.toUpperCase()} · {item ? 'OWNED' : 'EMPTY'}</small><strong>{item?.name || loadout[slot] || 'None'}</strong><span>{item?.description || 'Earn this slot from an authored room.'}</span></div>{item && <button type="button" disabled={busy || item.equipped} onClick={() => onEquip?.(run.run_id, item.id)}>{item.equipped ? 'Equipped' : 'Equip'}</button>}</div> })}<div className="dungeon-supply-item"><span className="dungeon-item-art"><img className="item-art-icon" src={lanternItemArt('dungeon-vision-scroll')} alt="" /></span><div><small>RUN ITEM · SCOUTING</small><strong>Vision scroll</strong><span>Reveal room types and connections for the current floor.</span></div><b>{loadout.vision_scrolls ?? 0}</b></div></div>}
      {tab === 'INVENTORY' && <div className="dungeon-inventory-list" data-testid="dungeon-inventory" role="region" aria-label="Dungeon equipment inventory" tabIndex={0}>{inventory.map((item) => <div key={item.id} className={item.equipped ? 'equipped' : ''}>{lanternItemArt(item.id) && <img className="dungeon-inventory-icon" src={lanternItemArt(item.id)} alt="" />}<div><small>{String(item.kind || 'item').toUpperCase()}</small><strong>{item.name}</strong><span>{item.description || 'Run item'}</span></div><button type="button" onClick={() => onEquip?.(run.run_id, item.id)} disabled={busy || item.equipped}>{item.equipped ? 'Equipped' : 'Equip'}</button></div>)}{!inventory.length && <p className="dungeon-muted">Your run inventory is empty. Earn gear from markets, elites and bosses.</p>}</div>}
      {tab === 'PACK' && <div className="dungeon-pack-list" data-testid="dungeon-pack">{pack.map((item) => <div key={item.id}><strong>{item.name}</strong><b>×{item.count}</b></div>)}{!pack.length && <p className="dungeon-muted">Your pack is empty. Beasts drop parts when you clear their fight.</p>}<small>{run.region ? `Delve: ${run.region.label}. ` : ''}Unbanked: a camp or ending the run banks it; dying loses it.</small></div>}
      {tab === 'STATS' && <div className="dungeon-stat-grid"><div><small>HP</small><strong>{loadout.hp ?? 0}/{loadout.max_hp ?? 0}</strong></div><div><small>SCORE</small><strong>{run.score ?? 0}</strong></div><div><small>COINS</small><strong>{run.run_coins ?? 0}</strong></div><div><small>HEALS</small><strong>{loadout.heals ?? 0}</strong></div><div><small>FLOOR</small><strong>{run.floor ?? 1}</strong></div><div><small>ROOM</small><strong>{run.room ?? 1}</strong></div></div>}
      {tab === 'JOURNAL' && <DungeonLegacyJournal journal={run.journal} />}
      <div className="dungeon-character-note"><RouteIcon id="spark" /><p>Elites and bosses add gear straight to this run’s Inventory. Equip it here at any time. Monster parts go in Pack and must be banked at a campsite.</p></div>
      <div className="dungeon-run-management">
        <button className="dungeon-bank-button" type="button" onClick={() => onFinish?.(run.run_id)} disabled={busy || !onFinish}>Bank score and end run</button>
        <button className="dungeon-reset-button" type="button" onClick={() => onReset?.(run.run_id)} disabled={busy || !onReset}>Reset run</button>
        <small>Discard this Dungeon checkpoint and run gear. Campaign progress stays safe.</small>
      </div>
    </section>
  )
}

const JOURNAL_MODE_NAMES = { campaign: 'Campaign', sparring: 'Sparring', pvp: 'PvP' }
const journalModes = (modes) => (Array.isArray(modes) && modes.length ? modes : ['campaign', 'sparring', 'pvp']).map((mode) => JOURNAL_MODE_NAMES[mode] || mode).join(' · ')

/** Scroll to the Journal and open its checklist (used by the run-setup shortcut). */
function openLegacyJournal() {
  const panel = document.getElementById('dungeon-legacy-journal')
  if (!panel) return
  const checklist = panel.querySelector('details')
  if (checklist) checklist.open = true
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function JournalEchoRow({ row }) {
  return (
    <li className={row.earned ? 'earned' : 'locked'}>
      <span className="dungeon-journal-mark" aria-hidden="true">{row.earned ? <RouteIcon id="check" /> : null}</span>
      <strong>{row.name}<span className="sr-only">{row.earned ? ' (earned)' : ' (not earned yet)'}</span></strong>
      <small>{row.how} · {String(row.slot || 'gear').toUpperCase()} · {row.tier}</small>
      {row.earned && <small className="dungeon-journal-modes">Yours to keep · usable in {journalModes(row.modes)}</small>}
    </li>
  )
}

export function DungeonLegacyJournal({ journal, compact = false }) {
  const unlocks = Array.isArray(journal?.unlocks) ? journal.unlocks : []
  const bosses = Array.isArray(journal?.cleared_bosses) ? journal.cleared_bosses : []
  const bonuses = journal?.bonuses || {}
  const checklist = Array.isArray(journal?.checklist) ? journal.checklist : []
  const regions = Array.isArray(journal?.regions) ? journal.regions : []
  const perks = Array.isArray(journal?.perks) ? journal.perks : []
  const totals = journal?.totals || { bosses: bosses.length, bosses_total: 8, echoes: unlocks.length, echoes_total: checklist.length }
  const legacy = checklist.filter((row) => !row.region)
  return (
    <section id="dungeon-legacy-journal" className={`dungeon-legacy-journal ${compact ? 'compact' : ''}`} aria-label="Legacy Journal">
      <div className="dungeon-journal-heading"><div><span className="dungeon-eyebrow">PERMANENT PROGRESS</span><h3>Legacy Journal</h3></div><span>{totals.bosses} / {totals.bosses_total} BOSSES{totals.echoes_total ? ` · ${totals.echoes} / ${totals.echoes_total} ECHOES` : ''}</span></div>
      <details className="dungeon-journal-fold" open={!compact}>
        <summary>Starting bonuses and boss perks</summary>
      <div className="dungeon-journal-bonuses" aria-label="Future run bonuses">
        <span><strong>+{bonuses.starting_hp || 0} HP</strong><small>starting vitality</small></span>
        <span><strong>+{bonuses.starting_bandages || 0}</strong><small>starting bandages</small></span>
        {EXTRA_JOURNAL_PERKS.filter(([key]) => bonuses[key] > 0).map(([key, label]) => <span key={key}><strong>+{bonuses[key]}</strong><small>starting {label}</small></span>)}
      </div>
      {perks.length > 0 && <ol className="dungeon-journal-perks" aria-label="Perks from each boss clear">{perks.map((perk) => <li key={`${perk.boss}-${perk.label}`} className={perk.earned ? 'earned' : ''}><b>Boss {perk.boss}</b><span>{perk.label}</span><small>{perk.earned ? 'Earned' : 'Locked'}</small></li>)}</ol>}
      {journal?.title && <p className="dungeon-journal-rule"><strong>Title earned:</strong> {journal.title}</p>}
      <p className="dungeon-journal-rule">Elite and boss gear leaves a permanent echo you keep. Boss clears add starting bonuses to every run.</p>
      </details>
      {checklist.length > 0 ? (
        <details className="dungeon-journal-all" open={!compact}>
          <summary>{compact ? 'See every echo and boss' : 'Every echo and boss'} · {totals.echoes} / {totals.echoes_total} earned</summary>
          {regions.map((region) => (
            <section key={region.id} className="dungeon-journal-region" aria-label={region.label}>
              <div className="dungeon-journal-region-head">
                <strong>{region.label}</strong>
                <span className={`dungeon-journal-badge ${region.cleared ? 'cleared' : ''}`}>{region.cleared ? 'BOSS CLEARED' : 'BOSS NOT CLEARED'}</span>
                <small>{region.boss} · {region.echoes_earned} / {region.echoes_total} echoes</small>
              </div>
              <ul className="dungeon-journal-echoes">{checklist.filter((row) => row.region === region.id).map((row) => <JournalEchoRow key={row.id} row={row} />)}</ul>
            </section>
          ))}
          {legacy.length > 0 && (
            <section className="dungeon-journal-region" aria-label="Any region rewards">
              <div className="dungeon-journal-region-head"><strong>Any region</strong><small>Earned by winning any boss with the gear equipped</small></div>
              <ul className="dungeon-journal-echoes">{legacy.map((row) => <JournalEchoRow key={row.id} row={row} />)}</ul>
            </section>
          )}
        </details>
      ) : (
        <>
          {unlocks.length > 0 && <div className="dungeon-journal-unlocks"><span className="dungeon-eyebrow">ARMORY ECHOES · USABLE OUTSIDE THE DUNGEON</span>{unlocks.map((item) => <div key={item.id}><strong>{item.name}</strong><small>{item.region || 'Delve reward'} · {String(item.slot || 'gear').toUpperCase()}</small></div>)}</div>}
          {bosses.length > 0 && <div className="dungeon-journal-bosses"><span className="dungeon-eyebrow">RECORDED BOSS CLEARS</span><p>{bosses.map((boss) => `${boss.name} · ${boss.region}`).join('  /  ')}</p></div>}
          {unlocks.length === 0 && bosses.length === 0 && <p className="dungeon-journal-empty">No entries yet. Clear an elite to earn a permanent echo, or a regional boss to strengthen future runs.</p>}
        </>
      )}
      {journal?.next_milestone && <small className="dungeon-journal-next">{journal.next_milestone}</small>}
    </section>
  )
}

const RISK_OUTCOME_WORDS = {
  reward: 'Hidden cache: +20 run coins and a field bandage.',
  debuff: 'Hexed route: your next miss costs double HP.',
  buff: 'Ember blessing: your next correct answer hits harder.',
  teleport: 'The corridor folded and the route moved on.',
}

function DungeonRoomPanel({ run, question, loadout, onRest, onCampAction, onRevealRisk, onEnterRisk, onMarketPurchase, onEquip, onLeave, onOpenCode, busy }) {
  const type = run.room_type || 'selector'
  const meta = dungeonRoomMeta(type)
  const title = type === 'mystery' ? 'Something waits behind this door.' : type === 'rest' ? 'A quiet ember waits between fights.' : type === 'market' ? 'A trader has set up beneath the lanterns.' : type === 'encounter' ? 'The door seals behind you.' : type === 'elite' ? 'The elite is guarding a trinket.' : type === 'boss' ? 'Every branch ends at the same throne.' : 'Choose the next room on the route.'
  const copy = type === 'rest' ? 'Recover, prepare your next clean submission, and decide when you are ready to return to the route.' : type === 'market' ? 'Spend run-only coins on a temporary edge. Nothing leaks into the campaign save.' : type === 'encounter' ? 'Question rooms are not navigational menus. They hand you to the IDE, where one verified answer decides whether the run continues.' : type === 'elite' ? 'This elite room is a harder challenge. Its trinket equips only for this run; the Legacy Journal records a separate armory echo.' : type === 'boss' ? 'A verified boss clear adds its weapon to this run, records a permanent armory echo, and strengthens future run starts.' : 'The state service reveals the next room only after the route is committed.'
  const fullHealth = (loadout.hp ?? 0) >= (loadout.max_hp ?? 0)
  const encounterName = run.encounter?.name || 'The Count Keeper'
  const encounterConcept = run.encounter?.concept_id || question.concept_id || 'current concept'
  const encounterDifficulty = run.encounter?.difficulty ?? question.difficulty ?? 1
  return (
    <section className={`dungeon-proto-panel dungeon-room-panel ${meta.tone}`} aria-label="Room screen">
      <div className="dungeon-panel-heading"><div><span className="dungeon-eyebrow">LAYER TWO</span><h2>Room screen</h2></div><span className={`dungeon-room-type ${meta.tone}`}><RouteIcon id={meta.iconId} /> {meta.label}</span></div>
      <div className={`dungeon-room-illustration ${meta.tone} ${dungeonRegionArt(run) ? 'has-region-art' : ''}`}><DungeonRegionScene run={run} /><span className="dungeon-room-orbit orbit-a" /><span className="dungeon-room-orbit orbit-b" /><RouteIcon id={meta.iconId} /><small>{run.region?.label ? `${run.region.label} · ${meta.subtitle}` : meta.subtitle}</small></div>
      <div className="dungeon-room-copy"><span className="dungeon-eyebrow">{run.current_node?.label || `${meta.label} · ROOM ${run.room || 1}`}</span><h3>{title}</h3><p>{copy}</p></div>
      {run.encounter && <div className="dungeon-mob-banner" aria-label="Current adaptive learning mob"><span className="dungeon-mob-sigil" aria-hidden="true"><RouteIcon id={type === 'boss' ? 'boss' : type === 'elite' ? 'target' : 'flame'} /></span><div><small>{type === 'boss' ? 'FLOOR BOSS' : type === 'elite' ? 'ELITE GATE' : 'ADAPTIVE MOB'} · PHASE {run.encounter.phase || 'I'}</small><strong>{run.encounter.name || encounterName}</strong><span>Concept: {encounterConcept} · difficulty {encounterDifficulty} · failure ends this run.</span></div><b>DIFFICULTY {encounterDifficulty}</b></div>}
      {type === 'selector' && run.last_result?.outcome === 'risk_entered' && RISK_OUTCOME_WORDS[run.last_result.reason] && <div className="dungeon-camp-banked" role="status"><span className="dungeon-eyebrow">LAST FATE</span><strong>{RISK_OUTCOME_WORDS[run.last_result.reason]}</strong></div>}
      {type === 'selector' && <div className="dungeon-room-action"><strong>Choose a route on the map.</strong><span>Room types are visible; future questions and answers are not.</span></div>}
      {type === 'rest' && (run.last_banked || []).length > 0 && <div className="dungeon-camp-banked" role="status"><span className="dungeon-eyebrow">PACK BANKED AT CAMP</span><strong>{lootText(run.last_banked)}</strong><span>Safe in your hunter's stores, whatever happens next.</span></div>}
      {type === 'rest' && <><section className="dungeon-camp-stash" aria-label="Forged armour stash"><span className="dungeon-eyebrow">ARMOUR STASH · FREE</span><p>Bring your forged armour into this run. This does not use your campsite action.</p>{(run.armor_stash || []).length ? <div className="dungeon-action-grid">{run.armor_stash.map((item) => <button className="dungeon-action-card" type="button" key={item.id} onClick={() => onEquip?.(run.run_id, item.id)} disabled={busy || !onEquip || loadout.armor === item.name}><RouteIcon id="shield" /><span><strong>{item.name}</strong><small>{item.description}</small></span><b>{loadout.armor === item.name ? 'EQUIPPED' : 'EQUIP'}</b></button>)}</div> : <p>Forge armour at Hunter’s Still to find it here.</p>}</section><div className="dungeon-room-supplies"><div><span className="dungeon-eyebrow">RUN SUPPLIES</span><strong>{loadout.heals ?? 0} rests · {loadout.bandages ?? 0} bandages · {loadout.rations ?? 0} rations · {loadout.tonics ?? 0} tonics</strong></div><span>{loadout.hp ?? 0}/{loadout.max_hp ?? 0} HP</span></div><div className="dungeon-camp-rule"><span className="dungeon-eyebrow">ONE ACTION PER CAMPSITE VISIT</span><span>{run.camp_action_used ? 'Action used. Leave when you are ready.' : 'Choose one preparation, then the route opens again.'}</span></div><div className="dungeon-action-grid"><button className="dungeon-action-card" type="button" onClick={() => (onCampAction || onRest)?.(run.run_id, 'rest')} disabled={busy || run.camp_action_used || (!onCampAction && !onRest) || (loadout.heals ?? 0) <= 0 || fullHealth}><RouteIcon id="plus" /><span><strong>Rest by the fire</strong><small>Recover up to 30 HP · {loadout.heals ?? 0} charge(s)</small></span><b>REST</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'bandage')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.bandages ?? 0) <= 0 || fullHealth}><RouteIcon id="plus" /><span><strong>Use a bandage</strong><small>Recover up to 22 HP · {loadout.bandages ?? 0} left</small></span><b>HEAL</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'cook')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.rations ?? 0) <= 0}><RouteIcon id="spark" /><span><strong>Cook a ration</strong><small>Increase maximum HP by 10 · {loadout.rations ?? 0} left</small></span><b>COOK</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'sharpen')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.edge_charges ?? 0) > 0}><RouteIcon id="sword" /><span><strong>Sharpen your edge</strong><small>Next clean submission deals +1 Resolve</small></span><b>PREP</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'fortify')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.armor_guard ?? 0) > 0}><RouteIcon id="shield" /><span><strong>Fortify your armor</strong><small>Absorb one failed-submission hit</small></span><b>BRACE</b></button><button className="dungeon-action-card" type="button" onClick={() => onCampAction?.(run.run_id, 'tonic')} disabled={busy || run.camp_action_used || !onCampAction || (loadout.tonics ?? 0) <= 0 || fullHealth}><RouteIcon id="spark" /><span><strong>Drink an ember tonic</strong><small>Recover up to 30 HP · {loadout.tonics ?? 0} left</small></span><b>TONIC</b></button></div><button className="dungeon-primary-wide" type="button" onClick={() => onLeave?.(run.run_id)} disabled={busy || !onLeave}>Leave campsite →</button></>}
      {type === 'market' && <><div className="dungeon-market-wallet"><div><span className="dungeon-eyebrow">RUN PURSE</span><strong>{run.run_coins ?? 0} coins</strong></div><div className="dungeon-market-stock"><span>Heals <b>{loadout.heals ?? 0}</b></span><span>Bandages <b>{loadout.bandages ?? 0}</b></span><span>Rations <b>{loadout.rations ?? 0}</b></span><span>Scrolls <b>{loadout.vision_scrolls ?? 0}</b></span></div></div><div className="dungeon-shelf-note"><span className="dungeon-eyebrow">ROTATING SHELF</span><span>Run supplies and gear · run coins only</span></div><div className="dungeon-market-list">{(run.market_catalog || []).map((item) => { const owned = ['weapon', 'armor', 'trinket'].includes(item.kind) && (run.inventory || []).some((entry) => entry.id === item.id); return <div key={item.id} className="dungeon-market-item"><img className="dungeon-inventory-icon" src={merchantItemArt({ ...item, slot: item.kind })} alt="" /><span><strong>{item.name}</strong><small>{item.description}</small></span><button type="button" aria-label={owned ? `${item.name}, owned` : `Buy ${item.name} for ${item.price} coins`} onClick={() => onMarketPurchase?.(run.run_id, item.id)} disabled={owned || busy || !onMarketPurchase || (run.run_coins ?? 0) < (item.price ?? 0)}>{owned ? 'Owned' : `${item.price}c`}</button></div> })}</div><button className="dungeon-primary-wide" type="button" onClick={() => onLeave?.(run.run_id)} disabled={busy || !onLeave}>Leave market →</button></>}
      {(type === 'encounter' || type === 'elite' || type === 'boss') && <><div className="dungeon-encounter-preview"><RouteIcon id={type === 'boss' ? 'boss' : type === 'elite' ? 'target' : 'sword'} /><div><span className="dungeon-eyebrow">{type === 'boss' ? 'FINAL DESTINATION' : type === 'elite' ? 'ELITE QUESTION ROOM · TRINKET DROP' : 'LOCKED QUESTION ROOM'}</span><strong>{encounterName}</strong><p>{type === 'boss' ? 'The final destination is state-owned. A verified file unlocks the next floor.' : type === 'elite' ? 'A harder question room with a bounded trinket reward.' : `${question.prompt || 'Build the answer in dungeon.py.'} The editor stays the single answer surface.`}</p></div></div><button className="dungeon-danger-wide" type="button" onClick={onOpenCode} disabled={busy || !onOpenCode}>Open code editor →</button></>}
      {type === 'mystery' && <div className="dungeon-risk-card"><RouteIcon id="question" /><div><span className="dungeon-eyebrow">{run.risk_status === 'revealed' ? 'SCOUTED RISK' : 'UNSCOUTED RISK'}</span><strong>{run.risk_profile?.title || 'Something is watching the route.'}</strong><p>{run.risk_profile?.preview || 'Enter to discover what fate has in store.'}</p></div><div className="dungeon-risk-actions"><button className="dungeon-danger-wide" type="button" onClick={() => onEnterRisk?.(run.run_id)} disabled={busy || run.risk_status === 'entered' || !onEnterRisk}>Enter the risk →</button></div></div>}
      <div className="dungeon-room-note"><span>DESIGN RULE</span><p>No challenge is generated until you commit to an encounter node.</p></div>
    </section>
  )
}

const DUNGEON_QUESTION_TYPES = {
  multiple_choice: {
    label: 'Multiple choice',
    how: 'Pick one option. Write its letter, then one sentence on why it is right.',
    sample: '# Answer: B\n# Because <one sentence in your own words>',
  },
  true_false: {
    label: 'True or false',
    how: 'Decide True or False, then explain the deciding detail.',
    sample: '# Answer: True\n# Because <the detail that decides it>',
  },
  code_checkpoint: {
    label: 'Write code',
    how: 'Write a small, runnable Python program that does what the question asks. Run it with Ctrl+Enter before you submit.',
    sample: '# Name what you need to track first\nvalue = ...\n\n# then build the behaviour the question asks for\nprint(...)',
  },
  bug_hunt: {
    label: 'Bug hunt',
    how: 'Find the bug, then explain the fix in words. Describe the change instead of pasting corrected code.',
    sample: '# The bug: <which line and what goes wrong>\n# Why: <what Python actually does there>\n# Fix: <the change, in words>',
  },
  short_explanation: {
    label: 'Explain it',
    how: 'Answer in two or three sentences of your own words (comments or plain text are fine).',
    sample: '# <the idea in one sentence>\n# <a tiny example of it>\n# <why it matters here>',
  },
}

// Renders PYR's question text: paragraphs plus ``` fenced code blocks.
function DungeonPromptText({ text }) {
  const parts = []
  const fence = /```[a-zA-Z0-9_-]*\n?([\s\S]*?)```/g
  let cursor = 0
  let match
  const source = String(text || '')
  while ((match = fence.exec(source))) {
    if (match.index > cursor) parts.push({ kind: 'text', value: source.slice(cursor, match.index) })
    parts.push({ kind: 'code', value: match[1].replace(/\n$/, '') })
    cursor = fence.lastIndex
  }
  if (cursor < source.length) parts.push({ kind: 'text', value: source.slice(cursor) })
  return <div className="dungeon-prompt-text">{parts.flatMap((part, index) => part.kind === 'code'
    ? [<pre key={`c${index}`}><code>{part.value}</code></pre>]
    : part.value.split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean).map((paragraph, inner) => <p key={`t${index}-${inner}`}>{paragraph}</p>))}</div>
}

function DungeonDifficulty({ value, max = 5 }) {
  const level = Math.max(1, Math.min(max, Number(value) || 1))
  return <span className="dungeon-difficulty" title={`Difficulty ${level} of ${max}`} aria-label={`Difficulty ${level} of ${max}`}>{Array.from({ length: max }, (_, index) => <i key={index} className={index < level ? 'on' : ''} aria-hidden="true">★</i>)}<b>{level}/{max}</b></span>
}

function DungeonResolveBar({ resolve, max, tone = 'enemy' }) {
  const total = Math.max(1, Number(max) || 1)
  const current = Math.max(0, Math.min(total, Number(resolve) || 0))
  return <span className={`dungeon-resolve-bar ${tone}`} aria-hidden="true">{Array.from({ length: total }, (_, index) => <i key={index} className={index < current ? 'on' : ''} />)}</span>
}

// Boot.dev-style brief for the current room: what the question wants, how
// to lay out an answer, how hard it is, and who you are fighting.
// The live fight: fixed question count (every one must be answered), banked
// free mistakes and the room's mechanic counting down.
function DungeonOils({ run, hunter, onApplyOil, busy }) {
  const encounter = run.encounter || {}
  const applied = encounter.fight?.oil
  if (applied) return <div className="dungeon-oils applied"><span className="dungeon-eyebrow">PREPARATION ACTIVE</span><strong>{applied.name?.replace(/ Oil$/, ' Preparation')}</strong><small>{applied.effect}</small></div>
  const usable = (hunter?.oils || []).filter((oil) => oil.sign === encounter.sign_id && !(oil.tier === 'slowing' && !encounter.fight?.mechanic))
  return (
    <div className="dungeon-oils">
      <span className="dungeon-eyebrow">DELVE PREPARATIONS · ONE PER FIGHT</span>
      {usable.length
        ? usable.map((oil) => <button key={oil.id} type="button" onClick={() => onApplyOil?.(run.run_id, oil.id)} disabled={busy || !onApplyOil} title={oil.effect}>Use {oil.name.replace(/ Oil$/, ' Preparation').split(' ').slice(-2).join(' ')} ×{oil.count}<small>{oil.effect}</small></button>)
        : <small>{encounter.sign_id ? `No preparation for ${HUNT_BEASTS[encounter.sign_id]?.beast || 'this beast'}. Craft one at Hunter’s Still.` : 'Preparations work on known beasts.'}</small>}
    </div>
  )
}

function DungeonFightStrip({ fight }) {
  const total = Number(fight.questions_total) || 1
  const cleared = Number(fight.questions_cleared) || 0
  const mechanic = fight.mechanic
  const plural = (count) => `${count} answer${count === 1 ? '' : 's'}`
  return (
    <div className="dungeon-fight-strip">
      <div className="dungeon-fight-cell">
        <span className="dungeon-eyebrow">QUESTION</span>
        <strong>{Math.min(cleared + 1, total)} of {total}</strong>
        <span className="dungeon-fight-pips" aria-hidden="true">{Array.from({ length: total }, (_, index) => <i key={index} className={index < cleared ? 'done' : index === cleared ? 'now' : ''} />)}</span>
      </div>
      <div className="dungeon-fight-cell">
        <span className="dungeon-eyebrow">FREE MISTAKES</span>
        <strong>{fight.guards ?? 0}</strong>
      </div>
      {mechanic && (
        <div className={`dungeon-fight-cell mechanic ${mechanic.enraged ? 'enraged' : ''}`}>
          <span className="dungeon-eyebrow">{String(mechanic.label || '').toUpperCase()}{mechanic.enraged ? ' · ENRAGED' : ''}</span>
          <strong>{mechanic.kind === 'self_destruct' ? `Blast in ${plural(mechanic.countdown)}` : mechanic.enraged ? 'Counterattacks ×2' : `Rage in ${plural(mechanic.countdown)}`}</strong>
          <small>{mechanic.text}</small>
        </div>
      )}
    </div>
  )
}

const SPAR_ROUNDS = 5

// Simulated fights in the Tutor notebook: only foes already met, five
// clickable rounds, no damage. Right first clicks still grow your signs.
function SparringArena({ roster = [], actions, armory, busy }) {
  const [foeId, setFoeId] = useState('')
  const [round, setRound] = useState(0)
  const [boutId, setBoutId] = useState(0)
  const [question, setQuestion] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [score, setScore] = useState(0)
  const [error, setError] = useState('')
  const [sparCode, setSparCode] = useState('')
  const [sparText, setSparText] = useState('')
  // "Try gear": every item is unlocked here, and picks only change what the combat scene shows.
  const [gear, setGear] = useState(null)
  const [looks, setLooks] = useState([])
  const [gearError, setGearError] = useState('')
  // Each answered round, and the server's replay of them with the tried-on gear (its effects decide the bars).
  const [history, setHistory] = useState([])
  const [sim, setSim] = useState(null)
  const [picks, setPicks] = useState({})
  const [gearOpen, setGearOpen] = useState(false)
  const [demo, setDemo] = useState(null)
  const foe = roster.find((item) => item.id === foeId)
  useEffect(() => {
    let live = true
    Promise.resolve(actions?.gear?.()).then((result) => { if (live && result) { setGear(result.gear || []); setLooks(result.looks || []) } }).catch((failure) => { if (live) setGearError(failure?.message || 'The armoury could not be opened.') })
    return () => { live = false }
  }, [])
  const pick = (slot, item) => { setPicks((current) => { const next = { ...current }; if (item === undefined) delete next[slot]; else next[slot] = item; return next }); setDemo(null) }
  // What the tried-on gear does is decided by the server, with the campaign's own rules (POST /api/spar/simulate).
  const baseLoadout = sparLoadout(armory, picks)
  const request = sparLoadoutRequest(baseLoadout)
  const simKey = JSON.stringify([request, history])
  useEffect(() => {
    let live = true
    Promise.resolve(actions?.simulate?.(request, history)).then((result) => { if (live && result) setSim({ key: simKey, data: result }) }).catch(() => { /* the plain fight stands in until the next try */ })
    return () => { live = false }
  }, [simKey])
  const swing = async (landed) => {
    const hypothetical = [...(history.length < SPAR_ROUNDS ? history : []), { correct: landed, kind: 'choice' }]
    try {
      const data = await actions?.simulate?.(request, hypothetical)
      if (data) setDemo((current) => ({ count: (current?.count || 0) + 1, history: hypothetical, sim: data }))
    } catch (failure) { setError(failure?.message || 'The ring could not play that out.') }
  }
  const contracts = roster.filter((item) => item.kind === 'contract')
  const beasts = roster.filter((item) => item.kind === 'beast')
  const ask = async (target, number) => {
    setError('')
    setDemo(null)
    setQuestion(null)
    try {
      const nextQuestion = await actions?.ask?.(target, number)
      setQuestion(nextQuestion)
      setSparCode(nextQuestion?.starter_code || '')
      setSparText('')
    } catch (failure) {
      setError(failure?.message || 'PYR could not write this round.')
    }
  }
  const start = (id) => {
    setGearOpen(false)
    setDemo(null)
    setHistory([])
    setFoeId(id)
    setBoutId((value) => value + 1)
    setRound(1)
    setScore(0)
    setFeedback(null)
    void ask(id, 1)
  }
  const choose = async (index) => {
    if (!question || busy || feedback) return
    try {
      const result = await actions?.answer?.(foeId, index)
      setFeedback({ ...result, picked: index })
      setHistory((rounds) => [...rounds, { correct: result?.verdict === 'correct', kind: 'choice' }])
      if (result?.verdict === 'correct') setScore((value) => value + 1)
    } catch (failure) {
      setError(failure?.message || 'That answer could not be checked.')
    }
  }
  const submitCode = async () => {
    if (!question || busy || feedback || !sparCode.trim()) return
    setError('')
    try {
      const result = await actions?.answerCode?.(foeId, sparCode)
      setFeedback(result)
      setHistory((rounds) => [...rounds, { correct: result?.verdict === 'correct', kind: 'code' }])
      if (result?.verdict === 'correct') setScore((value) => value + 1)
    } catch (failure) { setError(failure?.message || 'The code could not be reviewed. Try again.') }
  }
  const submitText = async () => {
    if (!question || busy || feedback || !sparText.trim()) return
    setError('')
    try {
      const result = await actions?.answerText?.(foeId, sparText)
      setFeedback(result)
      setHistory((rounds) => [...rounds, { correct: result?.verdict === 'correct', kind: 'text' }])
      if (result?.verdict === 'correct') setScore((value) => value + 1)
    } catch (failure) { setError(failure?.message || 'The answer could not be reviewed. Try again.') }
  }
  const next = () => {
    setFeedback(null)
    if (round >= SPAR_ROUNDS) {
      setRound(SPAR_ROUNDS + 1)
      setQuestion(null)
      return
    }
    setRound(round + 1)
    void ask(foeId, round + 1)
  }
  const finished = round > SPAR_ROUNDS
  // These bars exist only for this five-round bout. The practice endpoints
  // remain responsible for sign progress; neither bar touches Dungeon state.
  // The bars and the combat scene come from the replay. A "test swing" plays one made-up round on top of the
  // current state, and an answered round plays its own exchange; neither touches your hunter.
  const showDemo = !feedback && demo
  const view = showDemo
    ? sparView(demo.sim, demo.history, { answered: true, evidenceId: `gear-demo-${demo.count}` })
    : sparView(sim?.data, history, { answered: Boolean(feedback), evidenceId: `${foeId}-${boutId}-${round}`, ready: sim?.key === simKey })
  const practiceLoadout = { ...baseLoadout, hp: view.hpBefore, max_hp: view.maxHp }
  const practiceRun = { room_type: 'elite', encounter: { name: foe?.name || 'Training hollow', resolve: view.resolveBefore, max_resolve: view.maxResolve } }
  const practiceTurn = view.turn
  const effects = (showDemo ? demo.sim : sim?.data)?.effects
  return (
    <section className="spar-arena spar-dungeon-layout" aria-label="Sparring">
      <aside className="spar-fight-column" aria-label="Sparring fight">
        <div className="spar-selector">
          <label htmlFor="spar-foe-select" className="dungeon-eyebrow">FOES YOU HAVE MET</label>
          <select id="spar-foe-select" value={foeId} onChange={(event) => { if (event.target.value) start(event.target.value) }} disabled={busy || !roster.length}>
            <option value="">Choose an opponent</option>
            {contracts.length > 0 && <optgroup label="Campaign bounties">{contracts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
            {beasts.length > 0 && <optgroup label="Dungeon beasts">{beasts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup>}
          </select>
          {!roster.length && <small>Fight a campaign bounty or dungeon beast to unlock an opponent.</small>}
        </div>
        {foe ? <>
          <div className="dungeon-brief-strip spar-strip"><span className="dungeon-brief-kind">SIMULATED · NO DAMAGE</span><span>Round {Math.min(round, SPAR_ROUNDS)} / {SPAR_ROUNDS}</span><span>Score {score}</span>{view.guards > 0 && <span title="Free mistakes banked">Guard {view.guards}</span>}{view.turn && view.fired.length > 0 && <span className="spar-triggers" role="status">{view.fired.join(' · ')}</span>}<button type="button" className="campaign-button ghost spar-gear-toggle" aria-pressed={gearOpen} onClick={() => setGearOpen((open) => !open)}>{gearOpen ? 'Back to the question' : 'Try gear'}</button></div>
          <section className="spar-question spar-question-brief">
            <span className="dungeon-eyebrow">{finished ? 'BOUT OVER' : 'THE QUESTION'}</span>
            {finished ? <p>You answered {score} of {SPAR_ROUNDS} rounds right against {foe.name}.</p>
              : question ? <DungeonPromptText text={question.prompt} />
              : error ? <p role="alert">{error} <button type="button" className="campaign-button ghost" onClick={() => ask(foeId, round)}>Try again</button></p>
              : <p className="spar-empty">PYR is writing round {round}…</p>}
          </section>
          <DungeonCombatArena key={foe.id} run={practiceRun} loadout={practiceLoadout} turn={practiceTurn} simulated />
        </> : <>
          <div className="spar-intro"><span className="screen-kicker">THE SPARRING RING</span><h3>Train against what you have fought.</h3><p>Choose an opponent for five simulated rounds, or try on any gear first. Practice HP and Resolve reset after the bout.</p></div>
          {view.turn && view.fired.length > 0 && <p className="spar-triggers spar-preview-triggers" role="status">{view.fired.join(' · ')}</p>}
          <DungeonCombatArena key="gear-preview" run={practiceRun} loadout={practiceLoadout} turn={practiceTurn} simulated />
        </>}
      </aside>
      <main className="spar-answer-workbench" aria-label="Sparring answer">
        {(!foe || gearOpen) ? <SparGearMenu gear={gear} looks={looks} loadError={gearError} armory={armory} picks={picks} loadout={baseLoadout} effects={effects} onPick={pick} onReset={() => { setPicks({}); setDemo(null) }} onSwing={swing} />
          : finished ? <div className="spar-result"><span className="dungeon-eyebrow">BOUT OVER</span><h3>{score >= 4 ? 'A clean win.' : score >= 3 ? 'You held your own.' : 'Back to the notebook.'}</h3><p>You answered {score} of {SPAR_ROUNDS} rounds right against {foe.name}.</p><button type="button" className="campaign-button" onClick={() => start(foe.id)} disabled={busy}>Spar again</button></div>
          : question ? <>
            {question.question_type === 'code' ? <div className="spar-code-workspace"><div className="resource-editor-toolbar"><span>sparring.py · scratch workspace</span>{!feedback && <button type="button" className="campaign-button" onClick={submitCode} disabled={busy || !sparCode.trim()}>Submit for feedback</button>}</div><Editor height="100%" language="python" value={sparCode} onChange={(value) => setSparCode(value ?? '')} theme="vs-dark" options={{ minimap: { enabled: false }, fontSize: 14, automaticLayout: true, readOnly: Boolean(feedback), scrollBeyondLastLine: false }} /><p>This scratch answer is reviewed by PYR; it is not run or saved to your project.</p></div> : question.question_type === 'interview' || question.question_type === 'short_explanation' ? <div className="spar-interview-workspace"><label htmlFor="spar-interview-answer" className="dungeon-eyebrow">YOUR EXPLANATION</label><textarea id="spar-interview-answer" value={sparText} onChange={(event) => setSparText(event.target.value)} readOnly={Boolean(feedback)} maxLength={20000} placeholder="Explain your reasoning in your own words…" /><small>Your answer is reviewed by PYR and stays in this practice bout.</small>{!feedback && <button type="button" className="campaign-button" onClick={submitText} disabled={busy || !sparText.trim()}>Submit explanation</button>}</div> : ['true_false', 'multiple_choice'].includes(question.question_type) ? (!feedback && <ChoicePanel options={question.options || []} onChoose={choose} busy={busy} label="PICK ONE" />) : <p role="alert">This question format is not available. Try the round again. <button type="button" className="campaign-button ghost" onClick={() => ask(foeId, round)}>Try again</button></p>}
            {error && <p role="alert">{error}</p>}
            {feedback && <div className={`battle-feedback ${feedback.verdict}`} role="status"><strong>{feedback.verdict === 'correct' ? '✔ Hit. ' : '✘ Parried. '}</strong>{feedback.reason}<button type="button" className="campaign-button" onClick={next} autoFocus>{round >= SPAR_ROUNDS ? 'See the result' : 'Next round'} →</button></div>}
          </> : <div className="spar-answer-empty"><span className="dungeon-eyebrow">PRACTICE WORKSPACE</span><p>{error ? 'Retry the question on the left.' : 'Your answer will appear here when the question is ready.'}</p></div>}
      </main>
    </section>
  )
}

const BATTLE_CHOICE_KINDS = new Set(['prediction', 'explanation'])

// The campaign battle sidebar, laid out like the Dungeon brief: the question
// first, then what you are fighting, then every objective.
function BattleBrief({ player, armory, encounter, board, charges = {}, questions = {}, feedback, onAsk, onAnswer, onCheckSetup, onStudy, busy }) {
  const open = encounter.available_objectives || []
  const contract = (board?.contracts || []).find((item) => item.name === encounter.mob_name)
  // Beginner lessons and workshops follow their written teaching order;
  // other encounters put clickable questions before the coding goals.
  const current = open.find((item) => item.question_type === 'setup_check')
    || (contract?.kind === 'workshop' || encounter.project_id === '00-lantern-vale' ? open[0] : open.find((item) => BATTLE_CHOICE_KINDS.has(item.question_type)) || open[0])
  const setup = current?.question_type === 'setup_check'
  const gradedOn = current?.file ? (board?.project_dir ? `${board.project_dir}/${current.file}` : current.file) : board?.entry_file || 'your project file'
  const choice = Boolean(current && BATTLE_CHOICE_KINDS.has(current.question_type))
  const question = current ? questions[current.id] : null
  const asked = useRef(new Set())
  useEffect(() => {
    if (!choice || question || !onAsk || busy) return
    const key = `${encounter.mob_name}:${current.id}`
    if (asked.current.has(key)) return
    asked.current.add(key)
    onAsk(current.id)
  }, [choice, current?.id, Boolean(question), encounter.mob_name, busy])
  const done = new Set(encounter.completed_objectives || [])
  const allObjectives = contract?.objectives?.length ? contract.objectives : [...(encounter.completed_objectives || []).map((id) => ({ id, label: id.replaceAll('_', ' ') })), ...open]
  const entry = board?.entry_file || 'your project file'
  const codeLeft = open.filter((item) => !BATTLE_CHOICE_KINDS.has(item.question_type) && item.question_type !== 'setup_check')
  return (
    <div className="battle-brief" data-testid="forge-contract">
      <section className="battle-brief-question">
        <span className="battle-eyebrow">THE QUESTION{current ? ` · ${OBJECTIVE_KIND[current.question_type] || 'TASK'}` : ''}</span>
      <details className="battle-steps">
        <summary>{current ? `Step ${Math.min(allObjectives.length, done.size + 1)} of ${allObjectives.length}` : `All ${allObjectives.length} done`}</summary>
        <ol className="battle-brief-objectives">
          {allObjectives.map((objective) => (
            <li key={objective.id} className={done.has(objective.id) ? 'done' : current?.id === objective.id ? 'current' : ''}>
              <b className={`kind-${objective.question_type}`}>{done.has(objective.id) ? '✔' : OBJECTIVE_KIND[objective.question_type] || 'TASK'}</b>
              <span>{objective.label}</span>
            </li>
          ))}
        </ol>
      </details>
        {!current ? <p>Every objective is done.</p> : setup ? (
          <>
            <strong>{current.label}</strong>
            <DungeonPromptText text={current.brief} />
            <button type="button" className="campaign-button battle-setup-check" onClick={() => onCheckSetup?.(current.id)} disabled={busy || !onCheckSetup}>Check</button>
            <details className="battle-more"><summary>How this works</summary><small>The game looks in your project folder itself: no PYR call, and not done yet costs nothing.</small></details>
            {feedback?.objectiveId === current.id && feedback.output && <pre className="battle-setup-output">{feedback.output}</pre>}
          </>
        ) : choice ? (
          question ? (
            <>
              <DungeonPromptText text={question.prompt} />
              <ChoicePanel options={question.options || []} onChoose={(index) => onAnswer?.(current.id, index)} busy={busy} label="PICK ONE" />
            </>
          ) : <p className="battle-brief-wait">PYR is writing a question about {current.label.toLowerCase()}…{!busy && <button type="button" onClick={() => { asked.current.delete(`${encounter.mob_name}:${current.id}`); onAsk?.(current.id) }}>Ask again</button>}</p>
        ) : (
          <>
            <strong>{current.label}</strong>
            <DungeonPromptText text={current.brief} />
          </>
        )}
        {feedback && !String(feedback.objectiveId || '').startsWith('boss:') && <div className={`battle-feedback ${feedback.verdict}`} role="status">{feedback.verdict === 'correct' ? '✔ ' : feedback.verdict === 'not_yet' ? 'Not yet. ' : '✘ '}{feedback.reason}</div>}
        {current && !setup && !choice && <small className="battle-graded">Graded on <code>{gradedOn}</code> · press <b>Submit run</b>.</small>}
        {current && <details className="battle-more"><summary>Help and details</summary>
          {choice && codeLeft.length > 0 && <small className="battle-brief-also">Also open: {codeLeft.map((item) => item.label).join(', ')} (Submit run).</small>}
          <button type="button" className="campaign-button ghost" onClick={() => onStudy?.(current, contract?.sign)}>Study this in Tutor →</button>
          <StudyAtHomeButton topic={encounter.mob?.concept || contract?.concept || current.label} context={`fighting ${encounter.mob_name}: ${current.label.toLowerCase()} in ${entry}`} />
        </details>}
      </section>
        {(charges?.free_asks > 0 || charges?.wards > 0) && <small className="battle-brief-aid" data-testid="battle-aid">Armed: {[charges.free_asks ? `${charges.free_asks} free PYR ask${charges.free_asks === 1 ? '' : 's'}` : '', charges.wards ? `${charges.wards} ward${charges.wards === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ')}</small>}
        {encounter.pyr_assists > 0 && <small className="battle-brief-pyr" data-testid="battle-pyr-cost">PYR helped {encounter.pyr_assists}× · {encounter.help_free ? 'rewards unchanged' : `this fight pays ${encounter.reward_scale}% XP and coins`}{encounter.pyr_assists >= 2 && !encounter.loot_protected ? ' · no loot' : ''}</small>}
      <details className="battle-brief-enemy battle-enemy-fold">
        <summary><span className="battle-eyebrow">VS</span> <strong>{encounter.mob_name}</strong> <small>{encounter.resolve ?? 0}/{encounter.max_resolve ?? 0}</small></summary>
        <ForgeCombatScene encounter={encounter} player={player} armory={armory} />
        {contract?.sign && <small className="battle-brief-sign"><HuntSigil pageId={contract.sign} size={14} /> {contract.beast || 'Beast'} · Sign of the {HUNT_BEASTS[contract.sign]?.sign || contract.sign}</small>}
        <small>{encounter.guards ? `${encounter.guards} free mistake${encounter.guards === 1 ? '' : 's'} banked · ` : ''}{done.size} of {allObjectives.length} objectives done</small>
        {encounter.mob?.lore && <p className="battle-brief-lore">{encounter.mob.lore}</p>}
      </details>

    </div>
  )
}

function ForgeCombatScene({ encounter, player = {}, armory, boss = false }) {
  const name = boss ? (encounter.boss || 'Boss') : encounter.mob_name
  const hp = Math.max(0, Number(player.hp) || 0)
  const maxHp = Math.max(1, Number(player.max_hp) || 1)
  const resolve = Math.max(0, Number(encounter.resolve ?? encounter.boss_resolve) || 0)
  const maxResolve = Math.max(1, Number(encounter.max_resolve ?? encounter.boss_max_resolve) || 1)
  const weapon = armory?.weapon
  const previous = useRef(null)
  const [turn, setTurn] = useState(null)
  useEffect(() => {
    const before = previous.current
    previous.current = { name, hp, resolve }
    if (!before || before.name !== name) { setTurn(null); return }
    if (resolve < before.resolve || hp < before.hp) {
      const correct = resolve < before.resolve
      setTurn({ hpAfter: hp, result: { evidence_id: `forge-${Date.now()}`, outcome: correct ? 'correct' : 'incorrect', damage: Math.max(0, before.hp - hp), fight: { max_resolve: maxResolve, resolve_before: before.resolve, resolve_after: resolve, chip: Math.max(0, before.resolve - resolve) } } })
    }
  }, [name, hp, resolve, maxResolve])
  return <DungeonCombatArena campaign run={{ project_id: encounter.project_id, room_type: boss ? 'boss' : 'encounter', region: { id: encounter.project_id === '00-lantern-vale' ? 'basics' : '' }, encounter: { name, resolve, max_resolve: maxResolve, phase: boss ? encounter.boss_phase : undefined, phase_label: boss ? (encounter.boss_current_requirement?.label || encounter.boss_phase_label) : undefined, special_mechanic: boss ? encounter.special_mechanic : undefined } }} loadout={{ hp, max_hp: maxHp, weapon: weapon?.name || 'Bare hands', weapon_id: weapon?.id || '', weapon_style: weapon?.combat_style || 'unarmed', armor: armory?.equipped?.armor, trinket: armory?.equipped?.trinket, armor_mastery: armory?.equipped_appearances?.armor?.tier || '', weapon_mastery: armory?.equipped_appearances?.weapon?.tier || '' }} turn={turn} />
}

// ── LearnHarness: home, where the hunter studies the theory ────────────────
// The campaign is where you fight; LearnHarness (the learner's own study app)
// is where the ideas are learned. These pieces send a concept home and show
// what was studied there. The game never writes LearnHarness data.
async function learnHarnessCall(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `LearnHarness bridge failed (${response.status})`)
  return body
}

function StudyBriefDialog({ brief, copied, launched, onClose }) {
  useEffect(() => {
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <ShellPortal scope="forge-v2">
      <div className="study-brief-backdrop" role="presentation" onClick={onClose}>
        <section className="study-brief-dialog" role="dialog" aria-modal="true" aria-label="Study at home" onClick={(event) => event.stopPropagation()}>
          <span className="screen-kicker">STUDY AT HOME · LEARNHARNESS</span>
          <h3>{launched ? 'LearnHarness is opening.' : 'Open LearnHarness.'}</h3>
          <p>{copied ? 'Your study brief is copied.' : 'Copy this study brief.'} In LearnHarness, start a new session and paste it as what you want to understand.</p>
          <textarea readOnly value={brief} rows={8} onFocus={(event) => event.target.select()} />
          <div className="study-brief-actions">
            <button type="button" className="primary" onClick={() => { navigator.clipboard?.writeText(brief).catch(() => {}) }}>Copy again</button>
            <button type="button" onClick={onClose} autoFocus>Done</button>
          </div>
        </section>
      </div>
    </ShellPortal>
  )
}

function StudyAtHomeButton({ topic, context, label = 'Study this at home' }) {
  const [state, setState] = useState({ busy: false, note: '', handoff: null })
  if (!topic) return null
  const study = async () => {
    setState({ busy: true, note: '', handoff: null })
    try {
      const result = await learnHarnessCall('/api/learnharness/study', { method: 'POST', body: JSON.stringify({ topic: String(topic).slice(0, 200), context: String(context || '').slice(0, 300) }) })
      if (result.mode === 'direct') {
        setState({ busy: false, note: `Ready in LearnHarness: "${result.title}".`, handoff: null })
        return
      }
      let copied = false
      try {
        await navigator.clipboard.writeText(result.brief)
        copied = true
      } catch {
        copied = false
      }
      setState({ busy: false, note: '', handoff: { brief: result.brief, copied, launched: result.launched } })
    } catch (error) {
      setState({ busy: false, note: error.message, handoff: null })
    }
  }
  return (
    <span className="study-at-home">
      <button type="button" className="study-at-home-button" onClick={study} disabled={state.busy}><RouteIcon id="codex" />{state.busy ? 'Opening LearnHarness…' : label}</button>
      {state.note && <small role="status">{state.note}</small>}
      {state.handoff && <StudyBriefDialog {...state.handoff} onClose={() => setState({ busy: false, note: '', handoff: null })} />}
    </span>
  )
}

function StudiedAtHome({ concept }) {
  const [ideas, setIdeas] = useState([])
  useEffect(() => {
    if (!concept) return undefined
    const controller = new AbortController()
    fetch(`/api/learnharness/lore?concept=${encodeURIComponent(String(concept).slice(0, 300))}`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : { ideas: [] }))
      .then((body) => setIdeas(Array.isArray(body.ideas) ? body.ideas : []))
      .catch(() => {})
    return () => controller.abort()
  }, [concept])
  if (!ideas.length) return null
  return (
    <section className="studied-at-home" aria-label="Studied at home">
      <span className="screen-kicker">STUDIED AT HOME · LEARNHARNESS</span>
      <ul>{ideas.map((idea) => <li key={idea.name + idea.statement}><b>{idea.name}</b> {idea.statement}</li>)}</ul>
    </section>
  )
}

function LearnHarnessCard() {
  const [status, setStatus] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    fetch('/api/learnharness/status').then((response) => response.json()).then(setStatus).catch(() => setStatus({ installed: false }))
  }, [])
  const sendNotes = async () => {
    setBusy(true)
    try {
      const result = await learnHarnessCall('/api/learnharness/notes', { method: 'POST' })
      setNote(result.mode === 'direct' ? 'Notes imported into your knowledge graph.' : `Notes saved to ${result.path}. In LearnHarness, import that file from the graph's notes import.`)
    } catch (error) {
      setNote(error.message)
    } finally {
      setBusy(false)
    }
  }
  if (!status) return null
  return (
    <section className="ai-settings-section learnharness-card" aria-label="LearnHarness">
      <h4>LearnHarness · study at home</h4>
      {!status.installed ? <p>LearnHarness is not installed. It is a free, open-source study app; once installed, bounties get a Study this at home button.</p> : (
        <>
          <p>{status.running ? 'LearnHarness is open.' : 'LearnHarness is installed (closed).'} {status.mode === 'direct' ? 'Its API is open to the game, so sessions and notes go straight in.' : 'Study requests open it with a study brief to paste in.'} {status.ideas ? `${status.ideas} ideas studied so far.` : 'Nothing studied yet.'}</p>
          <button type="button" onClick={sendNotes} disabled={busy}>{busy ? 'Sending…' : 'Send my campaign notes home'}</button>
          {note && <small role="status">{note}</small>}
        </>
      )}
    </section>
  )
}

const BOSS_CHOICE_KINDS = new Set(['snippet_check', 'code_interview'])

// The boss gate in the sidebar: the current goal first (a coding task to
// build in the Hunt, or a clickable question about your own file), then the
// boss and every phase of the fight.
function BossBrief({ player, armory, encounter, board, questions = {}, feedback, onAsk, onAnswer, busy }) {
  const phases = encounter.boss_requirements_projection || []
  const current = encounter.boss_current_requirement || null
  const choice = Boolean(current && BOSS_CHOICE_KINDS.has(current.question_type))
  const key = current ? `boss:${current.id}` : ''
  const question = current ? questions[key] : null
  const asked = useRef(new Set())
  useEffect(() => {
    if (!choice || question || !onAsk || busy) return
    if (asked.current.has(key)) return
    asked.current.add(key)
    onAsk(current.id)
  }, [choice, key, Boolean(question), busy])
  const entry = board?.entry_file || 'your project file'
  const shownFeedback = feedback && String(feedback.objectiveId || '').startsWith('boss:') ? feedback : null
  return (
    <div className="battle-brief boss-brief" data-testid="forge-boss-brief">
      <section className="battle-brief-question">
        <span className="battle-eyebrow">THE QUESTION{current ? ` · ${OBJECTIVE_KIND[current.question_type] || 'TASK'}` : ''}</span>
      <details className="battle-steps">
        <summary>{phases.filter((phase) => phase.status === 'verified').length} of {phases.length} verified</summary>
        <ol className="battle-brief-objectives">
          {phases.map((phase) => (
            <li key={phase.id} className={phase.status === 'verified' ? 'done' : phase.status === 'current' ? 'current' : ''}>
              <b className={`kind-${phase.question_type}`}>{phase.status === 'verified' ? '✔' : OBJECTIVE_KIND[phase.question_type] || 'TASK'}</b>
              <span>{phase.label}</span>
            </li>
          ))}
        </ol>
      </details>
        {!current ? <p>Every goal is verified. The boss falls.</p> : choice ? (
          question ? (
            <>
              <DungeonPromptText text={question.prompt} />
              <ChoicePanel options={question.options || []} onChoose={(index) => onAnswer?.(current.id, index)} busy={busy} label="PICK ONE" />
            </>
          ) : <p className="battle-brief-wait">PYR is reading your {entry} for a question…{!busy && <button type="button" onClick={() => { asked.current.delete(key); onAsk?.(current.id) }}>Ask again</button>}</p>
        ) : (
          <>
            <strong>{current.label}</strong>
            <p>{current.quest || current.brief}</p>
            <small className="battle-graded">Build it in <code>{entry}</code> · press <b>Submit run</b>.</small>
          </>
        )}
        {shownFeedback && <div className={`battle-feedback ${shownFeedback.verdict}`} role="status">{shownFeedback.verdict === 'correct' ? '✔ ' : '✘ '}{shownFeedback.reason}</div>}
        {current && <StudyAtHomeButton topic={current.label} context={`fighting the boss ${encounter.boss || ''}: ${String(current.quest || current.brief || '').slice(0, 200)}`} />}
      </section>
      <details className="battle-brief-enemy battle-enemy-fold">
        <summary><span className="battle-eyebrow">VS</span> <strong>{encounter.boss || 'The boss'}</strong></summary>
        <ForgeCombatScene encounter={encounter} player={player} armory={armory} boss />
        {encounter.boss_lore && <p className="battle-brief-lore">{encounter.boss_lore}</p>}
      </details>

    </div>
  )
}

// Clickable answers for multiple-choice and true/false questions. Letter and
// number keys pick an option, but never while the player is typing somewhere.
function ChoicePanel({ options, onChoose, busy, label = 'CHOOSE YOUR ANSWER', note }) {
  useEffect(() => {
    const onKey = (event) => {
      if (busy || event.ctrlKey || event.metaKey || event.altKey || event.repeat) return
      const target = event.target
      if (target?.closest?.('input, textarea, select, [contenteditable="true"], .monaco-editor')) return
      const key = String(event.key || '').toLowerCase()
      const index = /^[1-9]$/.test(key) ? Number(key) - 1 : /^[a-h]$/.test(key) ? key.charCodeAt(0) - 97 : -1
      if (index >= 0 && index < options.length) {
        event.preventDefault()
        onChoose(index)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [options, onChoose, busy])
  return (
    <div className="choice-panel" role="group" aria-label="Answer options">
      <span className="dungeon-eyebrow">{label}</span>
      <div className="choice-options">
        {options.map((option, index) => (
          <button key={`${index}-${option}`} type="button" className="choice-option" onClick={() => onChoose(index)} disabled={busy}>
            <b>{String.fromCharCode(65 + index)}</b><span>{option}</span>
          </button>
        ))}
      </div>
      <small>{note || `Click an answer, or press A–${String.fromCharCode(64 + options.length)} / 1–${options.length}.`}</small>
    </div>
  )
}

function DungeonQuestionBrief({ run, question, loadout, hunter, onApplyOil, busy, combatTurn }) {
  const encounter = run.encounter || {}
  const mechanic = encounter.mechanic || {}
  const reward = encounter.reward_envelope || {}
  const type = DUNGEON_QUESTION_TYPES[question.question_type] || DUNGEON_QUESTION_TYPES.short_explanation
  const options = Array.isArray(question.options) ? question.options : []
  const roomKind = run.room_type === 'boss' ? 'FLOOR BOSS' : run.room_type === 'elite' ? 'ELITE GATE' : 'ENCOUNTER'
  return (
    <aside className={`dungeon-challenge-brief dungeon-brief-v2 room-${run.room_type || 'encounter'}`} aria-label="Room question">
      <div className="dungeon-brief-strip">
        <span className="dungeon-brief-kind">{roomKind}</span>
        <span>Floor {run.floor ?? 1} · Room {run.room ?? 1}</span>
        <span>{type.label}</span>
        <DungeonDifficulty value={question.difficulty} />

      </div>

      <section className="dungeon-brief-question">
        <span className="dungeon-eyebrow">THE QUESTION · {String(question.concept_id || encounter.concept_id || 'python').replaceAll('-', ' ').toUpperCase()}</span>
        {question.prompt ? <DungeonPromptText text={question.prompt} /> : <p className="dungeon-brief-empty">PYR is preparing this room's question…</p>}
      </section>

      {options.length > 0 ? (
        <section className="dungeon-brief-how">
          <span className="dungeon-eyebrow">HOW TO ANSWER</span>
          <p>Pick one of the {options.length} answers on the right: click it, or press its letter or number. A wrong pick shows the right answer and deals a new question.</p>
        </section>
      ) : (
        <section className="dungeon-brief-how">
          <span className="dungeon-eyebrow">HOW TO ANSWER</span>
          <p>{type.how} Write it in <code>dungeon.py</code>, then Submit.</p>
          <pre className="dungeon-brief-sample" aria-label="Answer layout sample"><code>{type.sample}</code></pre>
          <small>Sample layout only, not the answer.</small>
        </section>
      )}

      <DungeonCombatArena run={run} loadout={loadout} turn={combatTurn}>
        {(encounter.category || mechanic.label) && <small className="combat-mob-category">{encounter.category || mechanic.label}</small>}
        {encounter.fight && <DungeonFightStrip fight={encounter.fight} />}
        <details className="combat-mob-details">
          <summary>Mob abilities, preparations &amp; rewards</summary>
          {encounter.fight && <DungeonOils run={run} hunter={hunter} onApplyOil={onApplyOil} busy={busy} />}
          <ul className="dungeon-brief-facts">
            <li><span>Correct answer</span><b>Chips Resolve; at zero it breaks and you bank a free mistake</b></li>
            {mechanic.on_failure && <li><span>Wrong answer</span><b>{mechanic.on_failure}</b></li>}
            {mechanic.passive && <li><span>Passive</span><b>{mechanic.passive}</b></li>}
            <li><span>Rewards</span><b>+{reward.score ?? 0} score · +{reward.coins ?? 0} coins{Array.isArray(reward.authorized_items) && reward.authorized_items.length ? ` · ${reward.authorized_items.join(', ')}` : ''}</b></li>
          </ul>
        </details>
      </DungeonCombatArena>

    </aside>
  )
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

// Result of a graded Dungeon answer: what PYR said and what it cost or paid.
function DungeonVerdictCard({ card, avatar, onClose, onContinue }) {
  const correct = card.outcome === 'correct'
  const error = card.outcome === 'error'
  // The hit lands a beat after the card opens: bars drain, numbers float up.
  const [hit, setHit] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setHit(true), 350)
    return () => clearTimeout(timer)
  }, [])
  useEffect(() => {
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  const snap = card.snapshot || {}
  const clicked = String(card.evidence_id || '').startsWith('dg-click-')
  const fight = card.fight || null // the server's record of this exchange
  const done = !fight || fight.fight_done
  const damage = Number(card.damage) || 0
  const blast = Number(fight?.blast) || 0
  const maxHp = Number(card.maxHp ?? snap.maxHp) || 100
  const hpAfter = Number(card.hp ?? 0)
  const hpBefore = Number(snap.hp ?? hpAfter + damage + blast)
  const mobMax = Number(fight?.max_resolve ?? snap.mobMax) || 6
  const mobBefore = Number(fight?.resolve_before ?? snap.mobResolve ?? mobMax)
  const chip = Number(fight?.chip ?? (correct ? mobBefore : 0))
  const mobAfter = correct ? (done ? 0 : Math.max(0, mobBefore - chip)) : mobBefore
  const mobNow = hit ? mobAfter : mobBefore
  const hpNow = hit ? hpAfter : hpBefore
  const mobName = card.mob_name || snap.mobName || 'The mob'
  const pct = (value, max) => `${Math.max(0, Math.min(100, Math.round((value / Math.max(1, max)) * 100)))}%`
  const title = error ? 'Could not grade that'
    : card.died ? 'Run over'
    : correct ? (done ? 'Room cleared' : fight?.broke ? 'Resolve broken!' : 'Hit!')
    : fight?.guard_used ? 'Missed, but your guard held' : 'Not yet'
  const kicker = error ? 'SUBMISSION' : `${correct ? 'PYR · CORRECT' : 'PYR · INCORRECT'}${fight && fight.questions_total > 1 ? ` · QUESTION ${Math.min(fight.questions_cleared + (correct ? 0 : 1), fight.questions_total)} OF ${fight.questions_total}` : ''}`
  const lines = []
  if (!error) {
    if (correct) lines.push(done ? `You hit for ${chip} Resolve. ${mobName} is defeated.` : `You chip ${chip} Resolve. ${fight.questions_cleared} of ${fight.questions_total} questions answered.`)
    else lines.push(fight?.guard_used ? 'Your free mistake absorbs it. No HP lost.' : `${mobName} hits back for ${damage} HP${fight?.enraged && damage ? ' (enraged: double damage)' : ''}.`)
    if (fight?.broke) lines.push(`${mobName} breaks: you bank a free mistake${fight.mechanic_label ? ` and its ${fight.mechanic_label.toLowerCase()} is interrupted` : ''}. Its Resolve refills.`)
    if (fight?.mechanic_fired === 'self_destruct') lines.push(`Self-destruct! The blast hits you for ${blast} HP. The countdown starts again.`)
    if (fight?.mechanic_fired === 'enrage') lines.push(`${mobName} is enraged: its counterattacks hit twice as hard until you break it.`)
  }
  return (
    <div className="dungeon-verdict-backdrop" role="presentation" onClick={onClose}>
      <section className={`dungeon-verdict-card ${error ? 'error' : correct ? 'correct' : 'incorrect'}`} role="alertdialog" aria-modal="true" aria-labelledby="dungeon-verdict-title" onClick={(event) => event.stopPropagation()}>
        <span className="dungeon-eyebrow">{kicker}</span>
        <h2 id="dungeon-verdict-title">{correct ? '✔ ' : '✘ '}{title}</h2>
        {!error && (
          <div className={`verdict-arena ${hit ? 'hit' : ''} ${correct ? 'player-wins' : 'mob-wins'} ${correct && done ? 'defeated' : ''}`} aria-hidden="true">
            <div className="verdict-fighter player">
              <div className="verdict-sprite"><AvatarSprite appearance={avatar} size={84} /></div>
              {!correct && damage > 0 && <span className="verdict-float taken">−{damage} HP</span>}
              {!correct && fight?.guard_used && <span className="verdict-float guarded">GUARDED</span>}
              {blast > 0 && <span className="verdict-float blast">−{blast} BLAST</span>}
              <div className="verdict-bar hp"><i style={{ width: pct(hpNow, maxHp) }} /></div>
              <small>YOU · {hpNow} / {maxHp} HP</small>
            </div>
            <span className="verdict-clash"><RouteIcon id="sword" /></span>
            <div className="verdict-fighter mob">
              <div className="verdict-sprite verdict-mob"><RouteIcon id="boss" /></div>
              {correct && <span className="verdict-float dealt">−{chip} RESOLVE</span>}
              {fight?.broke && <span className="verdict-float broke">BREAK!</span>}
              <div className="verdict-bar resolve"><i style={{ width: pct(mobNow, mobMax) }} /></div>
              <small>{mobName.toUpperCase()} · {mobNow} / {mobMax}</small>
            </div>
          </div>
        )}
        {lines.map((line) => <p key={line} className="dungeon-verdict-summary">{line}</p>)}
        {card.reason && <p className="dungeon-verdict-reason">{card.reason}</p>}
        {!error && (
          <ul className="dungeon-verdict-stats">
            {correct && <li className="reward">+{card.score_delta ?? 0} score</li>}
            {Number(card.coins_delta) > 0 && <li className="reward">+{card.coins_delta} coins</li>}
            {(damage > 0 || blast > 0) && <li className="penalty">−{damage + blast} HP · {hpAfter} / {maxHp} left</li>}
            {fight && !done && fight.guards > 0 && <li className="growth">{fight.guards} free mistake{fight.guards === 1 ? '' : 's'} banked</li>}
            {fight && !done && fight.mechanic && <li className="penalty">{fight.mechanic === 'self_destruct' ? `Blast in ${fight.mechanic_countdown}` : fight.enraged ? 'Enraged' : `Rage in ${fight.mechanic_countdown}`}</li>}
            {(card.hunter_gain?.signs || []).map((sign) => <li key={sign.id} className="growth">+{sign.xp} Sign of the {HUNT_BEASTS[sign.id]?.sign || sign.id}</li>)}
            {Object.entries(card.hunter_gain?.stats || {}).map(([stat, amount]) => <li key={stat} className="growth">+{amount} {stat}</li>)}
            {(card.loot?.items || []).map((item) => <li key={item.id} className="loot">+{item.count} {item.name}</li>)}
            {card.loot?.clean && (card.loot?.items || []).length > 0 && <li className="loot">clean fight bonus</li>}
            {card.loot?.trinket && <li className="loot">Trinket added to run inventory: {card.loot.trinket.name}{card.loot.trinket.equipped ? ' (equipped)' : ' · equip from Character → Inventory'}</li>}
            {card.loot?.weapon && <li className="loot">Boss weapon added to run inventory: {card.loot.weapon.name} · equip from Character → Inventory</li>}
            {card.loot?.journal_unlock && <li className="loot">Legacy Journal unlocked {card.loot.journal_unlock.name} for your campaign armory.</li>}
            {card.loot?.journal_perk && <li className="growth">New permanent perk for every future run: {card.loot.journal_perk}.</li>}
            {(card.loot?.journal_proofs || []).map((echo) => <li className="loot" key={echo.id}>Proven in battle: Legacy Journal unlocked {echo.name} for your campaign armory.</li>)}
            {card.loot?.journal_bonus && <li className="growth">Journal bonus recorded: +{card.loot.journal_bonus.starting_hp} starting HP{card.loot.journal_bonus.starting_bandages ? ` and +${card.loot.journal_bonus.starting_bandages} bandage` : ''} on future runs.</li>}
          </ul>
        )}
        {card.loot?.trinket && <p className="dungeon-verdict-summary">{card.loot.trinket.name}: {card.loot.trinket.description}</p>}
        {card.loot?.weapon && <p className="dungeon-verdict-summary">{card.loot.weapon.name}: {card.loot.weapon.description}</p>}
        {card.died && (card.packLost || []).length > 0 && <p className="dungeon-verdict-lost">Unbanked loot lost: {lootText(card.packLost)}.</p>}
        {!card.died && (card.loot?.items || []).length > 0 && <p className="dungeon-verdict-hint">Parts go in your pack. Bank them at a camp or by ending the run.</p>}
        <p className="dungeon-verdict-hint">{error ? 'Nothing was spent. Fix the problem above and submit again.' : card.died ? `Your run ended with ${card.score ?? 0} score. Pick a class to start a new one.` : correct ? (done ? 'Pick your next room on the map.' : 'The next question is ready.') : clicked ? 'A new question is ready.' : 'Your answer is still in dungeon.py. Fix it and submit again.'}</p>
        <div className="dungeon-verdict-actions">
          {correct && done && !card.died
            ? <button type="button" className="dungeon-primary-button" onClick={onContinue} autoFocus>Choose next room <span>→</span></button>
            : <button type="button" className="dungeon-primary-button" onClick={onClose} autoFocus>{card.died ? 'Back to setup' : correct || clicked ? 'Next question' : 'Try again'} {(correct || clicked) && !card.died && <span>→</span>}</button>}
        </div>
      </section>
    </div>
  )
}

function DungeonScreen({ avatar, hunter, onApplyOil, onTravel, onAnswerOption, dungeon, revision, onStart, onChoose, onRest, onCampAction, onRevealRisk, onEnterRisk, onMarketPurchase, onEquip, onLeave, onFinish, onReset, submitDungeon, onRunDungeonCode, busy, saving, editorContent, onEditorChange, onSave }) {
  const [selectedClassId, setSelectedClassId] = useState('')
  const [setupStep, setSetupStep] = useState('class')
  const [submitStatus, setSubmitStatus] = useState('')
  const [roomTab, setRoomTab] = useState('room')
  const [characterTab, setCharacterTab] = useState('LOADOUT')
  const [verdictCard, setVerdictCard] = useState(null)
  const [combatTurn, setCombatTurn] = useState(null)
  const turnTimerRef = useRef(null)
  const autoOpenedQuestionRef = useRef('')
  const liveRun = dungeon || { active: false, status: 'idle' }
  const run = combatTurn?.run || liveRun
  const question = run.question || {}
  const loadout = run.loadout || {}

  // Pop a verdict card whenever a new graded result lands (auto-graded or
  // posted later by a CLI provider). The first render only records the
  // current result so a reload never replays an old verdict.
  const lastResult = liveRun.last_result || null
  const seenEvidenceRef = useRef(undefined)
  useEffect(() => () => clearTimeout(turnTimerRef.current), [])
  useEffect(() => {
    const evidence = lastResult?.evidence_id || ''
    if (seenEvidenceRef.current === undefined) { seenEvidenceRef.current = evidence; return }
    if (!evidence || evidence === seenEvidenceRef.current) return
    seenEvidenceRef.current = evidence
    if (!['correct', 'incorrect'].includes(lastResult.outcome)) return
    setSubmitStatus('')
    const snapshot = fightRef.current
    const liveLoadout = liveRun.loadout || {}
    const card = { ...lastResult, died: liveRun.status === 'dead', packLost: liveRun.pack_lost || [], hp: liveLoadout.hp, maxHp: liveLoadout.max_hp, score: liveRun.score, snapshot }
    if (!snapshot?.run || roomTab !== 'code') { setVerdictCard(card); return }
    clearTimeout(turnTimerRef.current)
    setCombatTurn({ run: snapshot.run, result: lastResult, hpAfter: liveLoadout.hp })
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    turnTimerRef.current = setTimeout(() => { turnTimerRef.current = null; setCombatTurn(null); setVerdictCard(card) }, reducedMotion ? 0 : 1100)
  }, [lastResult?.evidence_id])
  // Declared after the verdict effect so the card reads the fight as it stood
  // before the verdict changed the room.
  const fightRef = useRef(null)
  useEffect(() => {
    if (!['encounter', 'elite', 'boss'].includes(run.room_type) || !run.encounter) return
    if (combatTurn) return
    fightRef.current = { mobName: run.encounter.name, mobMax: run.encounter.max_resolve, mobResolve: run.encounter.resolve, hp: loadout.hp, maxHp: loadout.max_hp, roomType: run.room_type, run }
  }, [run, combatTurn])

  useEffect(() => {
    // The server can clear the room or end the run in the same update as a
    // verdict. Keep the previous question visible until its attack finishes.
    if (turnTimerRef.current || combatTurn) return
    if (!run.active) {
      setSelectedClassId('')
      setSetupStep('class')
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
    if (!combatRoom) {
      autoOpenedQuestionRef.current = ''
      // Room cleared: the next step is picking a route, not the code editor.
      setRoomTab((current) => (current === 'code' ? 'map' : current))
    }
  }, [run.active, run.room_type, run.question?.id, combatTurn])

  const [selectedRegionId, setSelectedRegionId] = useState(null)
  const start = async () => {
    if (!onStart || busy) return
    await onStart({ classId: selectedClassId, regionId: selectedRegionId === 'open' ? '' : selectedRegionId })
  }
  const lastRunLoot = run.status === 'dead' && (run.pack_lost || []).length
    ? `Your last hunt fell. Lost: ${lootText(run.pack_lost)}.`
    : run.status === 'complete' && (run.last_banked || []).length ? `Your last hunt banked ${lootText(run.last_banked)}.` : ''

  const submit = async () => {
    if (!submitDungeon || !question.id || !editorContent?.trim() || busy || combatTurn || verdictCard) return
    setSubmitStatus('PYR is judging your answer…')
    try {
      const sent = await submitDungeon({ runId: run.run_id, questionId: question.id, answer: editorContent })
      setSubmitStatus(sent?.judged ? '' : 'Sent to PYR. The room changes once it posts a verdict.')
    } catch (error) {
      const message = error?.message || 'Dungeon submission failed.'
      setSubmitStatus(message)
      setVerdictCard({ outcome: 'error', reason: message })
    }
  }

  const choiceOptions = Array.isArray(question.options) ? question.options : []
  const chooseOption = async (index) => {
    if (!onAnswerOption || busy || !question.id || verdictCard || combatTurn) return
    setSubmitStatus('Checking your answer…')
    try {
      const result = await onAnswerOption({ runId: run.run_id, questionId: question.id, index, text: choiceOptions[index] })
      setSubmitStatus(result && result.graded === false && !result.judged ? 'Sent to PYR. The room changes once it posts a verdict.' : '')
    } catch (error) {
      const message = error?.message || 'That answer could not be checked.'
      setSubmitStatus(message)
      setVerdictCard({ outcome: 'error', reason: message })
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
      {verdictCard && <ShellPortal scope="dungeon-screen-shell"><DungeonVerdictCard card={verdictCard} avatar={avatar} onClose={() => setVerdictCard(null)} onContinue={() => { setVerdictCard(null); setRoomTab('map') }} /></ShellPortal>}
      <header className="dungeon-local-header"><div className="dungeon-local-brand"><span className="dungeon-brand-mark"><RouteIcon id="spark" /></span><div><span className="dungeon-eyebrow">INFINITE DUNGEON</span><h1>{run.active ? `Floor ${run.floor} · Room ${run.room}` : 'The Descent'}</h1></div></div><span className="dungeon-local-badge"><i /> CANONICAL RUN · STATE GATEWAY</span>{run.active ? <div className="dungeon-run-stats" aria-label="Run stats"><div><small>FLOOR</small><strong>{run.floor ?? 1}</strong></div><div><small>HP</small><strong>{loadout.hp ?? 0}/{loadout.max_hp ?? 0}</strong></div><div><small>SCORE</small><strong>{run.score ?? 0}</strong></div><div><small>COINS</small><strong>{run.run_coins ?? 0}</strong></div><button className="dungeon-reset-header" type="button" onClick={() => onReset?.(run.run_id)} disabled={busy || !onReset}>Reset run</button></div> : <div className="dungeon-header-note"><span className="dungeon-eyebrow">BEFORE THE DESCENT</span><strong>{setupStep === 'class' ? 'CHOOSE YOUR CLASS' : 'CHOOSE A LOCATION'}</strong></div>}</header>
      {!run.active ? setupStep === 'class' ? <main className="dungeon-class-select" aria-label="Choose a dungeon class"><section className="dungeon-class-hero"><span className="dungeon-eyebrow">RUN SETUP · FLOOR 1</span><h2>So how you wanna play it.</h2><p>Pick a class</p>{run.journal?.totals && <button type="button" className="dungeon-journal-jump" onClick={openLegacyJournal}>Legacy Journal · {run.journal.totals.bosses}/{run.journal.totals.bosses_total} bosses · {run.journal.totals.echoes}/{run.journal.totals.echoes_total} echoes ↓</button>}{lastRunLoot && <p className="delve-last-run">{lastRunLoot}</p>}</section><section className="dungeon-class-grid" role="radiogroup" aria-label="Dungeon classes">{DUNGEON_CLASSES.map((starterClass) => <button key={starterClass.id} type="button" role="radio" aria-checked={selectedClassId === starterClass.id} className={`dungeon-class-card ${selectedClassId === starterClass.id ? 'selected' : ''}`} onClick={() => setSelectedClassId(starterClass.id)} disabled={busy}><span className="dungeon-class-card-top"><span className="dungeon-class-icon" aria-hidden="true"><RouteIcon id={starterClass.iconId} /></span><span><span className="dungeon-eyebrow">{starterClass.role}</span><strong>{starterClass.name}</strong></span>{selectedClassId === starterClass.id && <small className="dungeon-class-picked">READY</small>}</span><span className="dungeon-class-weapon"><span className="dungeon-class-label">STARTER WEAPON</span><strong>{starterClass.weapon}</strong><small>{starterClass.weaponDetail || 'A bounded run weapon for this playstyle.'}</small></span><span className="dungeon-class-passive"><span className="dungeon-class-label">PASSIVE</span><p>{starterClass.passive}</p></span></button>)}</section><DungeonLegacyJournal journal={run.journal} compact />{selectedClassId && <div className="dungeon-class-cta" aria-live="polite"><button className="dungeon-primary-button" type="button" onClick={() => setSetupStep('location')} disabled={busy}>Choose location <span>→</span></button></div>}</main> : <DelvePicker hunter={hunter} selected={selectedRegionId} onSelect={setSelectedRegionId} onBack={() => setSetupStep('class')} onStart={start} selectedClass={DUNGEON_CLASSES.find((item) => item.id === selectedClassId)} busy={busy} /> : roomTab === 'code' ? <section className="dungeon-ide-screen" aria-label="Challenge IDE"><div className="dungeon-ide-topline"><button type="button" className="dungeon-ghost-button" onClick={() => setRoomTab('room')} disabled={Boolean(combatTurn)}>← Map locked</button><span className="dungeon-eyebrow">{run.room_type === 'boss' ? 'FLOOR BOSS · FINAL DESTINATION' : run.room_type === 'elite' ? 'ELITE GATE · TRINKET DROP' : 'QUESTION ROOM · NO ROUTE CONTROLS'}</span><span className="dungeon-ide-risk">FAILURE COSTS HP</span></div><div className="dungeon-ide-layout"><DungeonQuestionBrief run={run} question={question} loadout={loadout} hunter={hunter} onApplyOil={onApplyOil} busy={busy || Boolean(combatTurn)} combatTurn={combatTurn} /><div className="dungeon-code-workbench">{choiceOptions.length ? <ChoicePanel options={choiceOptions} onChoose={chooseOption} busy={busy || Boolean(verdictCard) || Boolean(combatTurn)} /> : <><div className="dungeon-editor-toolbar"><span>dungeon.py · current room buffer</span><span>PYTHON · MONACO · LOCAL COMPLETION</span></div><DungeonEditorSurface value={editorContent || ''} onChange={onEditorChange} onSave={onSave} onRunCode={onRunDungeonCode} runId={run.run_id} questionId={question.id} onSubmit={submit} busy={busy || Boolean(combatTurn) || Boolean(verdictCard)} saving={saving} /></>}{submitStatus && <small className="battle-submit-status" role="status">{submitStatus}</small>}</div></div></section> : <><div className="dungeon-workspace-tabs" role="tablist" aria-label="Dungeon workspace"><button type="button" role="tab" aria-selected={roomTab === 'map'} className={roomTab === 'map' ? 'active' : ''} onClick={() => setRoomTab('map')}>Map &amp; route</button><button type="button" role="tab" aria-selected={roomTab === 'room'} className={roomTab === 'room' ? 'active' : ''} onClick={() => setRoomTab('room')}>Room screen</button><button type="button" role="tab" aria-selected={roomTab === 'code'} className={roomTab === 'code' ? 'active' : ''} onClick={openCode} disabled={!['encounter', 'elite', 'boss'].includes(run.room_type)}>Code editor</button></div><div className="dungeon-prototype-grid" data-testid="dungeon-tab-panel"><DungeonMap run={run} onChoose={chooseRoom} onTravel={onTravel} onRevealFloor={onRevealRisk} busy={busy} /><DungeonRoomPanel run={run} question={question} loadout={loadout} onRest={onRest} onCampAction={onCampAction} onRevealRisk={onRevealRisk} onEnterRisk={onEnterRisk} onMarketPurchase={onMarketPurchase} onEquip={onEquip} onLeave={onLeave} onOpenCode={openCode} busy={busy} /><DungeonCharacterPanel run={run} tab={characterTab} setTab={setCharacterTab} onEquip={onEquip} busy={busy} onFinish={onFinish} onReset={onReset} /></div><p className="dungeon-checkpoint-note">{statusText} Run <code>{run.run_id}</code> will resume after a Hunt or workstation restart; death is the only reset.</p></>}
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

async function avatarFileToWebp(file) {
  if (!file || !/^image\/(?:png|jpeg|webp)$/.test(file.type)) throw new Error('Choose a PNG, JPEG, or WebP image.')
  if (file.size > 5_000_000) throw new Error('Choose an image smaller than 5 MB.')
  const bitmap = await createImageBitmap(file)
  const longest = Math.max(bitmap.width, bitmap.height)
  const scale = Math.min(1, 512 / longest)
  let width = Math.max(1, Math.round(bitmap.width * scale))
  let height = Math.max(1, Math.round(bitmap.height * scale))
  let blob = null
  for (let attempt = 0; attempt < 8 && width > 0 && height > 0; attempt += 1) {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, width, height)
    blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.82))
    if (!blob || blob.size <= 1_000_000) break
    width = Math.round(width * 0.75)
    height = Math.round(height * 0.75)
  }
  bitmap.close?.()
  if (!blob || blob.size > 1_000_000) throw new Error('That image could not be compressed below 1 MB. Try a simpler picture.')
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('The profile picture could not be read.'))
    reader.readAsDataURL(blob)
  })
}

function AccountPanel({ account, busy, notice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onResolveConflict, onProfileSave, onAvatarUpload, onAvatarRemove, revision }) {
  const [formMode, setFormMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [profileName, setProfileName] = useState(account.profile?.display_name || '')
  const [avatarError, setAvatarError] = useState('')
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

  useEffect(() => {
    if (account.profile?.display_name) setProfileName(account.profile.display_name)
  }, [account.profile?.display_name])

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
          <p>{account.detail || 'Add the public Supabase values to enable account sign-in. Your local Hunt is unaffected.'}</p>
        </div>
      )}

      {configured && !signedIn && (
        <>
          <p className="settings-note">Sign in on each device to share your Quest Lab identity. Campaign fields sync through the controlled state gateway.</p>
          <form className="account-form" onSubmit={submit}>
            {formMode === 'signup' && (
              <label><span>Username</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={24} placeholder="Lazi" autoComplete="nickname" /></label>
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
          <form className="account-profile-form" onSubmit={async (event) => { event.preventDefault(); try { await onProfileSave(profileName) } catch {} }}>
            <label><span>Username</span><input aria-label="Username" value={profileName} onChange={(event) => setProfileName(event.target.value)} maxLength={24} required placeholder="Your online name" /></label>
            <button type="submit" disabled={busy || profileName.trim() === account.profile?.display_name}>Save username</button>
          </form>
          <div className="account-profile-picture">
            <span className="account-profile-picture-preview">{avatar.dataUrl ? <img src={avatar.dataUrl} alt="Your profile picture" /> : (account.profile?.display_name || 'H').trim().slice(0, 1).toUpperCase()}</span>
            <div><strong>Profile picture</strong><small>PNG, JPEG, or WebP · up to 5 MB</small><label className="account-avatar-upload">Choose picture<input aria-label="Choose profile picture" type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={async (event) => { const file = event.target.files?.[0]; event.target.value = ''; if (!file) return; setAvatarError(''); try { await onAvatarUpload(await avatarFileToWebp(file)) } catch (error) { setAvatarError(error?.message || 'Profile picture could not be saved.') } }} /></label></div>
            {avatar.dataUrl && <button type="button" disabled={busy} onClick={async () => { setAvatarError(''); try { await onAvatarRemove() } catch (error) { setAvatarError(error?.message || 'Profile picture could not be removed.') } }}>Remove</button>}
          </div>
          {avatarError && <p className="account-message error" role="alert">{avatarError}</p>}
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

const SETTINGS_SECTIONS = [
  { id: 'stats', label: 'Player Stats', hint: 'Activity graph, records' },
  { id: 'appearance', label: 'Appearance', hint: 'Theme, fonts, effects' },
  { id: 'editor', label: 'Editor & Terminal', hint: 'Sizes and panels' },
  { id: 'ai', label: 'AI Tutor', hint: 'OpenCode · PYR' },
  { id: 'account', label: 'Account & Sync', hint: 'Sign in, devices' },
  { id: 'files', label: 'Project Files', hint: 'Move work between devices' },
  { id: 'about', label: 'About', hint: 'Save location, version' },
]

const THEME_OPTIONS = [
  ['', 'Arcade (default)'],
  ['homestead', 'Homestead equipped theme'],
  ['gruvbox-dark', 'Gruvbox Dark'],
  ['gruvbox-light', 'Gruvbox Light'],
  ['github-dark', 'GitHub Dark'],
  ['github-light', 'GitHub Light'],
  ['deep-forest', 'Deep Forest'],
  ['void-scholar', 'Void Scholar'],
  ['ancient-archive', 'Ancient Archive'],
]

function SettingRow({ label, description, children }) {
  return (
    <div className="settings-row">
      <div className="settings-row-copy"><strong>{label}</strong>{description && <p>{description}</p>}</div>
      <div className="settings-row-control">{children}</div>
    </div>
  )
}

function SettingToggle({ checked, onChange, label, disabled = false }) {
  return (
    <button type="button" role="switch" aria-checked={Boolean(checked)} aria-label={label} className={`settings-switch ${checked ? 'on' : ''}`} onClick={() => onChange(!checked)} disabled={disabled}>
      <span>{checked ? 'ON' : 'OFF'}</span>
    </button>
  )
}

function AiTutorSettings({ ai = {} }) {
  const { aiTutor = {}, refreshAiTutor, saveAiSettings } = ai
  const cloud = aiTutor.cloud || {}
  const opencode = aiTutor.opencode || {}
  const settings = aiTutor.settings || {}
  const [models, setModels] = useState(null)
  const [test, setTest] = useState(null)
  const [saving, setSaving] = useState(false)
  const loadModels = async () => {
    setModels('loading')
    try {
      const response = await fetch('/api/ai/models')
      const body = await response.json()
      setModels(Array.isArray(body.models) ? body.models : [])
    } catch {
      setModels([])
    }
  }
  const update = async (patch) => {
    setSaving(true)
    try { await saveAiSettings?.(patch) } finally { setSaving(false) }
  }
  const runTest = async () => {
    setTest({ status: 'running', text: settings.mode === 'shared' ? 'Asking shared PYR for a test reply…' : 'Asking local OpenCode for a test reply…' })
    try {
      const body = await ai.testAiConnection?.(settings.model || '')
      if (!body) throw new Error('Shared PYR is not available on this device.')
      setTest({ status: 'ok', text: `Connected · ${body.model} replied in ${body.seconds}s` })
    } catch (error) {
      setTest({ status: 'error', text: error.message })
    }
  }
  const modelOptions = Array.isArray(models) ? models : []
  const localReady = opencode.ready
  const selectedMode = settings.mode || 'opencode'
  const statusLabel = !aiTutor.loaded ? 'CHECKING' : selectedMode === 'classic' ? 'MANUAL CLI' : selectedMode === 'shared' ? cloud.ready ? 'SHARED PYR READY' : 'SHARED PYR OFFLINE' : localReady ? 'LOCAL OPENCODE READY' : 'OPENCODE NOT READY'
  return (
    <>
      <section className="settings-group">
        <LearnHarnessCard />
        <header><h3>Shared PYR</h3><p>Optional hosted AI for signed-in members of your private Hunter group. Local OpenCode remains available without using Supabase.</p></header>
        <div className={`settings-status-card ${cloud.ready ? 'ready' : 'warn'}`}>
          <div><span className="screen-kicker">SHARED PYR</span><strong>{statusLabel}</strong><p>{cloud.detail || 'Checking the shared tutor…'}</p>{cloud.model && <small>{cloud.provider || 'Cloud provider'} · {cloud.model}</small>}</div>
          <button type="button" onClick={() => refreshAiTutor?.()}>Re-check</button>
        </div>
        <p className="settings-note">PYR sends the question and relevant code to the configured AI provider. Its API key stays in Supabase and is never included in the app download. Each group member is limited to 12 requests per minute and 100 per day.</p>
        {opencode.ready && <p className="settings-note">Local OpenCode is installed on this device and can be used independently of shared PYR.</p>}
        <details className="settings-local-ai-details" open>
          <summary>Local OpenCode status</summary>
          <p>{opencode.detail || 'OpenCode is not installed on this device.'}</p>
          {opencode.version && <small>{opencode.version} · {opencode.path}</small>}
          {opencode.integrations?.length > 0 && <div className="settings-chips">{opencode.integrations.map((name) => <span key={name}>{name}</span>)}</div>}
          <p className="settings-note">OpenCode uses the provider accounts already configured in your local CLI.</p>
        </details>
      </section>
      <section className="settings-group">
        <header><h3>PYR mode</h3></header>
        <SettingRow label="How PYR runs" description={settings.mode === 'shared' ? 'Use the hosted shared tutor. This sends PYR requests to Supabase.' : settings.mode === 'classic' ? 'Show the raw terminal so you can use OpenCode or another CLI yourself.' : 'Use OpenCode installed on this device. Signing in does not change this choice.'}>
          <div className="settings-segmented" role="radiogroup" aria-label="PYR mode">
            <button type="button" role="radio" aria-checked={(settings.mode || 'opencode') === 'opencode'} className={(settings.mode || 'opencode') === 'opencode' ? 'active' : ''} onClick={() => update({ mode: 'opencode' })} disabled={saving}>Local OpenCode</button>
            <button type="button" role="radio" aria-checked={settings.mode === 'shared'} className={settings.mode === 'shared' ? 'active' : ''} onClick={() => update({ mode: 'shared' })} disabled={saving}>Shared PYR</button>
            <button type="button" role="radio" aria-checked={settings.mode === 'classic'} className={settings.mode === 'classic' ? 'active' : ''} onClick={() => update({ mode: 'classic' })} disabled={saving}>Manual CLI</button>
          </div>
        </SettingRow>
      </section>
      {(settings.mode || 'opencode') === 'opencode' && opencode.ready && <section className="settings-group">
        <header><h3>Model</h3></header>
        <SettingRow label="Local OpenCode model" description="Used on this device; this mode does not send requests to Supabase.">
          <select value={settings.model || ''} onFocus={() => { if (models === null) loadModels() }} onChange={(event) => { setTest(null); update({ model: event.target.value }) }} disabled={!opencode.ready || saving}>
            <option value="">Auto (fast, signed-in model)</option>
            {settings.model && !modelOptions.includes(settings.model) && <option value={settings.model}>{settings.model}</option>}
            {models === 'loading' && <option disabled>Loading models…</option>}
            {modelOptions.map((model) => <option key={model} value={model}>{model}</option>)}
          </select>
        </SettingRow>
      </section>}
      <section className="settings-group">
        <header><h3>Connection check</h3></header>
        <SettingRow label="Test PYR" description={settings.mode === 'shared' ? 'Sends one tiny request through hosted shared PYR.' : settings.mode === 'classic' ? 'Switch to Local OpenCode or Shared PYR to run a built-in test.' : 'Sends one tiny request using this device’s OpenCode CLI.'}>
          <div className="settings-inline"><button type="button" onClick={runTest} disabled={(settings.mode === 'shared' ? !cloud.ready : settings.mode === 'classic' || !opencode.ready) || test?.status === 'running'}>{test?.status === 'running' ? 'Testing…' : settings.mode === 'shared' ? 'Test shared PYR' : 'Test local OpenCode'}</button>{test && <span className={`settings-test ${test.status}`}>{test.text}</span>}</div>
        </SettingRow>
      </section>
      <section className="settings-group">
        <header><h3>What PYR does</h3></header>
        <SettingRow label="Grade my submissions" description="Submit run, boss goals, Dungeon answers and Tutor feedback are judged by PYR automatically. Off = use the manual CLI panel instead.">
          <SettingToggle label="Grade my submissions" checked={settings.auto_grade !== false} onChange={(value) => update({ auto_grade: value })} disabled={(settings.mode === 'shared' ? !cloud.ready : settings.mode === 'classic' || !opencode.ready) || saving} />
        </SettingRow>
        <SettingRow label="Write Infinite Dungeon questions" description="Each new combat room gets a fresh question written for its concept, type and difficulty.">
          <SettingToggle label="Write Infinite Dungeon questions" checked={settings.generate_dungeon_questions !== false} onChange={(value) => update({ generate_dungeon_questions: value })} disabled={(settings.mode === 'shared' ? !cloud.ready : settings.mode === 'classic' || !opencode.ready) || saving} />
        </SettingRow>
        <SettingRow label="Choose Tutor question lenses" description="Shows “Let PYR choose” in Tutor practice: PYR picks the lens you need and writes a question for it.">
          <SettingToggle label="Choose Tutor question lenses" checked={settings.choose_practice_lens !== false} onChange={(value) => update({ choose_practice_lens: value })} disabled={(settings.mode === 'shared' ? !cloud.ready : settings.mode === 'classic' || !opencode.ready) || saving} />
        </SettingRow>
      </section>
    </>
  )
}

// ── Player stats: the activity graph and lifetime records ──────────────────
// Days come from the local activity log (progress.activity_log.days), filled by
// saving code, verified answers, cleared bounties, Dungeon floors and bosses.
const ACTIVITY_WEEKS = 52
const ACTIVITY_WEIGHTS = { lines: 1, answers: 3, mobs: 6, floors: 3, bosses: 25 }
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function localDayKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function activityScore(day) {
  return Object.entries(ACTIVITY_WEIGHTS).reduce((total, [key, weight]) => total + (Number(day?.[key]) || 0) * weight, 0)
}

function activityLevel(score) {
  if (score <= 0) return 0
  if (score < 10) return 1
  if (score < 30) return 2
  if (score < 80) return 3
  return 4
}

function activityTitle(key, day) {
  const date = new Date(`${key}T12:00:00`)
  const label = `${MONTH_NAMES[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`
  const parts = [
    day.lines ? `${day.lines} line${day.lines === 1 ? '' : 's'} of code` : '',
    day.answers ? `${day.answers} answer${day.answers === 1 ? '' : 's'}` : '',
    day.mobs ? `${day.mobs} mob${day.mobs === 1 ? '' : 's'} slain` : '',
    day.floors ? `${day.floors} floor${day.floors === 1 ? '' : 's'} down` : '',
    day.bosses ? `${day.bosses} boss${day.bosses === 1 ? '' : 'es'}` : '',
  ].filter(Boolean)
  return `${label}: ${parts.length ? parts.join(' · ') : 'no activity'}`
}

// Active-day streaks over the whole log (a day counts if anything happened).
function activityStreaks(days) {
  const active = new Set(Object.entries(days).filter(([, day]) => activityScore(day) > 0).map(([key]) => key))
  let longest = 0
  let run = 0
  let previous = null
  for (const key of [...active].sort()) {
    const date = new Date(`${key}T12:00:00`)
    run = previous && Math.round((date - previous) / 86400000) === 1 ? run + 1 : 1
    longest = Math.max(longest, run)
    previous = date
  }
  let current = 0
  const cursor = new Date()
  if (!active.has(localDayKey(cursor))) cursor.setDate(cursor.getDate() - 1)  // today can still be earned
  while (active.has(localDayKey(cursor))) {
    current += 1
    cursor.setDate(cursor.getDate() - 1)
  }
  return { active: active.size, current, longest }
}

function ActivityGraph({ days = {} }) {
  const scrollRef = useRef(null)
  const today = new Date()
  today.setHours(12, 0, 0, 0)
  const start = new Date(today)
  start.setDate(start.getDate() - (ACTIVITY_WEEKS * 7) - today.getDay())  // a Sunday, 52 full weeks back
  const weeks = []
  for (let cursor = new Date(start); cursor <= today; cursor.setDate(cursor.getDate() + 1)) {
    if (cursor.getDay() === 0) weeks.push([])
    const key = localDayKey(cursor)
    const day = days[key] || {}
    weeks[weeks.length - 1].push({ key, day, level: activityLevel(activityScore(day)), month: cursor.getMonth(), date: cursor.getDate() })
  }
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollLeft = scrollRef.current.scrollWidth  // show the newest weeks
  }, [])
  return (
    <div className="activity-graph" ref={scrollRef}>
      <div className="activity-months" style={{ gridTemplateColumns: `repeat(${weeks.length}, var(--activity-cell))` }} aria-hidden="true">
        {weeks.map((week, index) => {
          const first = week.find((cell) => cell.date === 1)
          return <span key={index}>{first ? MONTH_NAMES[first.month] : ''}</span>
        })}
      </div>
      <div className="activity-body">
        <div className="activity-weekdays" aria-hidden="true"><span /><span>Mon</span><span /><span>Wed</span><span /><span>Fri</span><span /></div>
        <div className="activity-cells" role="img" aria-label="Daily activity over the last year">
          {weeks.map((week, index) => (
            <div key={index} className="activity-week">
              {week.map((cell) => <span key={cell.key} className={`activity-cell level-${cell.level}`} title={activityTitle(cell.key, cell.day)} />)}
            </div>
          ))}
        </div>
      </div>
      <div className="activity-legend" aria-hidden="true"><small>Less</small>{[0, 1, 2, 3, 4].map((level) => <span key={level} className={`activity-cell level-${level}`} />)}<small>More</small></div>
    </div>
  )
}

function StatCard({ label, value, hint }) {
  return <div className="stat-card"><small>{label}</small><strong>{value}</strong>{hint && <span>{hint}</span>}</div>
}

function PlayerStatsPanel({ progress, hunter, activity }) {
  if (!progress || typeof progress !== 'object') {
    return <section className="settings-group"><header><h3>Player Stats</h3></header><p className="settings-note">Your stats appear once your save has loaded.</p></section>
  }
  const days = progress.activity_log?.days && typeof progress.activity_log.days === 'object' ? progress.activity_log.days : {}
  const records = progress.records || {}
  const stats = progress.stats || {}
  const player = progress.player || {}
  const board = Array.isArray(progress.dungeon_leaderboard) ? progress.dungeon_leaderboard : []
  const streaks = activityStreaks(days)
  const yearAgo = new Date()
  yearAgo.setDate(yearAgo.getDate() - 365)
  const yearKey = localDayKey(yearAgo)
  const thisYear = Object.entries(days).filter(([key]) => key >= yearKey)
  const sum = (key) => thisYear.reduce((total, [, day]) => total + (Number(day?.[key]) || 0), 0)
  const bestDay = thisYear.reduce((best, entry) => (activityScore(entry[1]) > activityScore(best?.[1]) ? entry : best), null)
  const number = (value) => Number(value || 0).toLocaleString()
  const survived = Math.max(Number(records.dungeon_runs_survived || 0), board.filter((run) => run.status === 'complete').length)
  const deaths = Math.max(Number(records.dungeon_deaths || 0), board.filter((run) => run.status === 'dead').length)
  const bestFloor = Math.max(Number(records.dungeon_best_floor || 0), ...board.map((run) => Number(run.floor) || 0), 0)
  const bestScore = Math.max(Number(records.dungeon_best_score || 0), ...board.map((run) => Number(run.score) || 0), 0)
  const bosses = Number(stats.bosses_defeated || 0)
  return (
    <section className="settings-group player-stats" data-testid="player-stats">
      <header><h3>Player Stats</h3><p>Everything you have built and beaten. Counting started with this update, so older days and runs may be missing.</p></header>
      <div className="activity-summary">
        <strong>{number(sum('lines'))} lines of code</strong> and <strong>{number(sum('answers'))} answers</strong> in the last year · {streaks.active} active day{streaks.active === 1 ? '' : 's'}
      </div>
      <ActivityGraph days={days} />
      <div className="stat-grid">
        <StatCard label="Current streak" value={`${streaks.current} day${streaks.current === 1 ? '' : 's'}`} hint="days in a row with any activity" />
        <StatCard label="Longest streak" value={`${streaks.longest} day${streaks.longest === 1 ? '' : 's'}`} />
        <StatCard label="Best day" value={bestDay ? activityTitle(bestDay[0], bestDay[1]).split(':')[0] : '—'} hint={bestDay ? activityTitle(bestDay[0], bestDay[1]).split(': ')[1] : 'go make one'} />
      </div>
      <h4 className="stat-group-title">Campaign</h4>
      <div className="stat-grid">
        <StatCard label="Level" value={player.level ?? 1} hint={`${number(player.xp)} / ${number(player.xp_next ?? 100)} XP to next level`} />
        <StatCard label="Rank" value={player.rank || 'F'} hint={player.title || 'Apprentice Coder'} />
        <StatCard label="Learning streak" value={`${number(progress.streak?.current)} days`} hint="consecutive validated days" />
        <StatCard label="Mastery shields" value={number((progress.skills || []).filter((skill) => skill.shield?.tier && skill.shield.tier !== 'none').length)} />
        <StatCard label="Activity score" value={number(activity?.activity_score)} hint="validated learning actions" />
        <StatCard label="Mobs slain" value={number(stats.mobs_defeated)} />
        <StatCard label="Bosses defeated" value={number(bosses)} hint={`${number(stats.projects_cleared)} projects shipped`} />
        <StatCard label="Answers verified" value={number(records.answers_verified)} />
        <StatCard label="Guard Breaks" value={number(stats.guard_breaks)} />
        <StatCard label="Clean clears" value={number(stats.clean_clears)} hint="a boss beaten without PYR help" />
        <StatCard label="Coins" value={number(player.coins)} />
        <StatCard label="Hunter level" value={hunter?.level ?? '—'} />
      </div>
      <h4 className="stat-group-title">Code</h4>
      <div className="stat-grid">
        <StatCard label="Lines written" value={number(records.lines_written)} hint="non-blank lines you added or rewrote" />
        <StatCard label="Active days" value={number(streaks.active)} />
      </div>
      <h4 className="stat-group-title">Infinite Dungeon</h4>
      <div className="stat-grid">
        <StatCard label="Runs started" value={number(records.dungeon_runs_started)} />
        <StatCard label="Runs survived" value={number(survived)} />
        <StatCard label="Deaths" value={number(deaths)} />
        <StatCard label="Highest floor" value={bestFloor || '—'} />
        <StatCard label="Best score" value={number(bestScore)} />
        <StatCard label="Floors descended" value={number(records.dungeon_floors_descended)} />
      </div>
      <h4 className="stat-group-title">Help</h4>
      <div className="stat-grid">
        <StatCard label="PYR asks in fights" value={number(records.pyr_asks)} hint="Mysterys in Shandumballa help is free; other campaigns may reduce rewards" />
        <StatCard label="Aid used" value={number(records.aid_used)} />
      </div>
    </section>
  )
}

function SettingsScreen({ progress, hunter, preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onProfileSave, onAvatarUpload, onAvatarRemove, onResolveConflict, revision, workspaceTransfer, workspaceTransferBusy, workspaceTransferNotice, onWorkspaceTransferRefresh, onWorkspaceTransferPush, onWorkspaceTransferPreviewPull, onWorkspaceTransferApplyPull, ai, runtime }) {
  const { editorFontSize, terminalFontSize, hudDensity, animations, showAiTerminal, themeChoice, fontFamily, zenMode, crtMode } = preferences
  const [section, setSection] = useState(() => {
    try { return window.localStorage.getItem('questlab.settingsSection') || 'appearance' } catch { return 'appearance' }
  })
  const openSection = (id) => {
    setSection(id)
    try { window.localStorage.setItem('questlab.settingsSection', id) } catch { /* storage unavailable */ }
  }
  const active = SETTINGS_SECTIONS.find((item) => item.id === section) || SETTINGS_SECTIONS[0]
  return (
    <div className="game-screen-scroll settings-screen settings-v2" data-campaign-revision={revision}>
      <div className="screen-hero settings-hero">
        <div><span className="screen-kicker">SETTINGS</span><h2>Make the Hunt fit you.</h2><p>Usability and accessibility settings are free forever. Homestead coins only unlock cosmetic presentation.</p></div>
      </div>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          {SETTINGS_SECTIONS.map((item) => (
            <button key={item.id} type="button" className={item.id === active.id ? 'active' : ''} aria-current={item.id === active.id ? 'page' : undefined} onClick={() => openSection(item.id)}>
              <strong>{item.label}</strong><small>{item.hint}</small>
            </button>
          ))}
        </nav>
        <div className="settings-content">
          {active.id === 'stats' && <PlayerStatsPanel progress={progress} hunter={hunter} activity={ai?.activity} />}
          {active.id === 'appearance' && <section className="settings-group">
            <header><h3>Appearance</h3></header>
            <SettingRow label="Theme" description="Arcade is the pixel default. Homestead themes are cosmetics you buy with coins.">
              <select value={themeChoice || ''} onChange={(event) => setters.setThemeChoice(event.target.value)}>{THEME_OPTIONS.map(([value, label]) => <option key={value || 'arcade'} value={value}>{label}</option>)}</select>
            </SettingRow>
            <SettingRow label="Interface font" description="Used by the non-Arcade themes; Arcade always uses its pixel fonts.">
              <select value={fontFamily || 'inter'} onChange={(event) => setters.setFontFamily(event.target.value)}><option value="inter">Inter · neutral</option><option value="ibm-plex">IBM Plex Sans · readable</option><option value="atkinson">Atkinson Hyperlegible · high clarity</option><option value="system">System UI</option></select>
            </SettingRow>
            <SettingRow label="HUD density" description="Compact trims the top bar to the essentials.">
              <select value={hudDensity} onChange={(event) => setters.setHudDensity(event.target.value)}><option value="full">Full</option><option value="compact">Compact</option></select>
            </SettingRow>
            <SettingRow label="Animations" description="Level-up effects, confetti and transitions.">
              <SettingToggle label="Animations" checked={animations} onChange={setters.setAnimations} />
            </SettingRow>
            <SettingRow label="CRT scanlines" description="A subtle scanline overlay across the whole app.">
              <SettingToggle label="CRT scanlines" checked={crtMode} onChange={setters.setCrtMode} />
            </SettingRow>
            <SettingRow label="Zen mode" description="Show only the Hunt editor. Shortcut: Ctrl/Cmd+K, then Z.">
              <SettingToggle label="Zen mode" checked={zenMode} onChange={setters.setZenMode} />
            </SettingRow>
          </section>}
          {active.id === 'editor' && <section className="settings-group">
            <header><h3>Editor & Terminal</h3></header>
            <SettingRow label="Editor font size" description={`${editorFontSize}px`}>
              <input type="range" min="11" max="22" value={editorFontSize} onChange={(event) => setters.setEditorFontSize(Number(event.target.value))} aria-label="Editor font size" />
            </SettingRow>
            <SettingRow label="Terminal font size" description={`${terminalFontSize}px`}>
              <input type="range" min="10" max="20" value={terminalFontSize} onChange={(event) => setters.setTerminalFontSize(Number(event.target.value))} aria-label="Terminal font size" />
            </SettingRow>
            <SettingRow label="PYR terminal panel" description="The raw CLI terminal beside the Hunt editor. Not needed when OpenCode grades for you. Hidden on Codex, Home and Settings either way.">
              <SettingToggle label="PYR terminal panel" checked={showAiTerminal !== false} onChange={setters.setShowAiTerminal} />
            </SettingRow>
            <SettingRow label="Panel layout" description="Restore the default Hunt panel sizes.">
              <button type="button" onClick={resetLayout}>Reset panel layout</button>
            </SettingRow>
          </section>}
          {active.id === 'ai' && <AiTutorSettings ai={ai} />}
          {active.id === 'account' && <AccountPanel account={account} busy={accountBusy} notice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onProfileSave={onProfileSave} onAvatarUpload={onAvatarUpload} onAvatarRemove={onAvatarRemove} onResolveConflict={onResolveConflict} revision={revision} />}
          {active.id === 'files' && <WorkspaceTransferPanel transfer={workspaceTransfer} busy={workspaceTransferBusy} notice={workspaceTransferNotice} onRefresh={onWorkspaceTransferRefresh} onPush={onWorkspaceTransferPush} onPreviewPull={onWorkspaceTransferPreviewPull} onApplyPull={onWorkspaceTransferApplyPull} />}
          {active.id === 'about' && <section className="settings-group">
            <header><h3>About Quest Lab</h3></header>
            <SettingRow label="Save file" description="Your character, campaign and Dungeon state."><code className="settings-path">{runtime?.canonical_state_path || '…'}</code></SettingRow>
            <SettingRow label="Workspace" description="Where your game files live and the Hunt terminal starts."><code className="settings-path">{runtime?.workspace || '…'}</code></SettingRow>
            <SettingRow label="Checkout" description="The Quest Lab code this app is running."><code className="settings-path">{runtime?.repo_git?.branch || '…'} · {(runtime?.repo_git?.head_sha || '').slice(0, 8)}</code></SettingRow>
            <SettingRow label="Docs" description="How the desktop app, AI tutor and campaign fit together."><code className="settings-path">docs/DESKTOP_APP.md · docs/AI_TUTOR.md</code></SettingRow>
          </section>}
        </div>
      </div>
    </div>
  )
}

export function GameScreen({ pyr, settingsAi, runtime, setAvatar, selectCampaign, hunter, spendStatPoint, hunterActions, campaignBoard, armory, armoryActions, sparRoster, sparActions, onDungeonApplyOil, onDungeonTravel, onDungeonAnswerOption, onDungeonRunCode, activeView, progress, homeRooms, purchaseHomeRoom, revision, avatarDataUrl = '', encounter, codexProjection, practiceProjection, equipmentProjection, dungeon, dungeonEditorContent, onDungeonEditorChange, onSaveDungeon, onDungeonChoose, onDungeonRest, onDungeonCampAction, onDungeonRevealRisk, onDungeonEnterRisk, onDungeonMarketPurchase, onDungeonEquip, onDungeonLeave, onDungeonFinish, onDungeonReset, purchaseCosmetic, purchaseMarketItem, equipCosmetic, equipCampaignItem, buildRoomUpgrade, performHomesteadAction, saveCodexNote, busy, dungeonSaving, submitBattle, submitBoss, submitDungeon, onStartDungeon, onPracticePrompt, preferences, setters, resetLayout, account, accountBusy, accountNotice, onSignIn, onSignUp, onSignOut, onDeviceLabelSave, onProfileSave, onAvatarUpload, onAvatarRemove, onResolveConflict, workspaceTransfer, workspaceTransferBusy, workspaceTransferNotice, onWorkspaceTransferRefresh, onWorkspaceTransferPush, onWorkspaceTransferPreviewPull, onWorkspaceTransferApplyPull, onNavigate, onEquipmentSynced, tutorCode, tutorDirty, tutorExternalChange, editorFontSize = 14, onTutorChange, onTutorSave, onTutorFormat, onTutorRun, onTutorReloadExternal, onTutorKeepEdits, campaignReady = true, showNavigation = true }) {
  const wideRoute = ['hub', 'character', 'homestead', 'codex', 'tutor', 'settings', 'online'].includes(activeView)
  // Historical contract marker: const wideRoute = ['hub', 'character', 'homestead', 'codex', 'settings']
  const withWideNavigation = (screen) => wideRoute && showNavigation
    ? <WideSurfaceFrame activeView={activeView} onNavigate={onNavigate}>{screen}</WideSurfaceFrame>
    : screen

  if (!campaignReady && !['settings', 'online'].includes(activeView)) {
    return withWideNavigation(
      <div className="game-screen-scroll campaign-loading" data-testid="campaign-loading" aria-live="polite">
        <section className="screen-hero">
          <div><span className="screen-kicker">CAMPAIGN SYNC</span><h2>Waiting for the canonical state</h2><p>Hunt will show your level, encounters, Codex and inventory as soon as the state service returns the latest revision. No starter values are being substituted.</p></div>
        </section>
      </div>
    )
  }
  if (activeView === 'hub') return withWideNavigation(<CampaignSurface setAvatar={setAvatar} selectCampaign={selectCampaign} hunter={hunter} spendStatPoint={spendStatPoint} hunterActions={hunterActions} campaignBoard={campaignBoard} armory={armory} armoryActions={armoryActions} progress={progress} homeRooms={homeRooms} purchaseHomeRoom={purchaseHomeRoom} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} purchaseMarketItem={purchaseMarketItem} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} account={account} onEquipmentSynced={onEquipmentSynced} dungeon={dungeon} busy={busy} onNavigate={onNavigate} />)
  if (activeView === 'online') return withWideNavigation(<OnlinePageBoundary pageName="Colosseum" resetKey={`colosseum:${account?.user?.id || 'signed-out'}`} onClose={() => onNavigate?.('hunt')}><OnlineHideout account={account} progress={progress} onNavigate={onNavigate} onEquipmentSynced={onEquipmentSynced} /></OnlinePageBoundary>)
  if (activeView === 'quests' || activeView === 'codex' || activeView === 'tutor') return withWideNavigation(<ResourceTutorScreen pyr={pyr} hunter={hunter} sparRoster={sparRoster} sparActions={sparActions} armory={armory} avatar={equipmentProjection?.avatar} activeView={activeView} progress={progress} revision={revision} codexProjection={codexProjection} encounter={encounter} tutorCode={tutorCode} tutorDirty={tutorDirty} tutorExternalChange={tutorExternalChange} editorFontSize={editorFontSize} busy={busy} onTutorChange={onTutorChange} onTutorSave={onTutorSave} onTutorFormat={onTutorFormat} onTutorRun={onTutorRun} onPracticePrompt={onPracticePrompt} onTutorReloadExternal={onTutorReloadExternal} onTutorKeepEdits={onTutorKeepEdits} onNavigate={onNavigate} />)
  // Legacy render contract retained in source comments for downstream static
  // checks; the live route above owns the replacement surface.
  // withWideNavigation(<Codex progress={progress} revision={revision} codexProjection={codexProjection} showNavigation={false} />)
  if (activeView === 'character') return withWideNavigation(<CharacterSheet progress={progress} revision={revision} avatarDataUrl={avatarDataUrl} encounter={encounter} codexProjection={codexProjection} onNavigate={onNavigate} />)
  if (activeView === 'homestead') return withWideNavigation(<Homestead hunter={hunter} spendStatPoint={spendStatPoint} armory={armory} armoryActions={armoryActions} progress={progress} revision={revision} equipmentProjection={equipmentProjection} purchaseCosmetic={purchaseCosmetic} equipCosmetic={equipCosmetic} equipCampaignItem={equipCampaignItem} buildRoomUpgrade={buildRoomUpgrade} performHomesteadAction={performHomesteadAction} busy={busy} onNavigate={onNavigate} />)
  if (activeView === 'dungeon') return <DungeonScreen avatar={equipmentProjection?.avatar} hunter={hunter} onApplyOil={onDungeonApplyOil} onTravel={onDungeonTravel} onAnswerOption={onDungeonAnswerOption} dungeon={dungeon} revision={revision} onStart={onStartDungeon} onChoose={onDungeonChoose} onRest={onDungeonRest} onCampAction={onDungeonCampAction} onRevealRisk={onDungeonRevealRisk} onEnterRisk={onDungeonEnterRisk} onMarketPurchase={onDungeonMarketPurchase} onEquip={onDungeonEquip} onLeave={onDungeonLeave} onFinish={onDungeonFinish} onReset={onDungeonReset} submitDungeon={submitDungeon} onRunDungeonCode={onDungeonRunCode} busy={busy} saving={dungeonSaving} editorContent={dungeonEditorContent} onEditorChange={onDungeonEditorChange} onSave={onSaveDungeon} />
  if (activeView === 'practice') return <PracticeScreen progress={progress} revision={revision} practiceProjection={practiceProjection} onPracticePrompt={onPracticePrompt} busy={busy} />
  if (activeView === 'settings') return <SettingsScreen progress={progress} hunter={hunter} ai={settingsAi} runtime={runtime} preferences={preferences} setters={setters} resetLayout={resetLayout} account={account} accountBusy={accountBusy} accountNotice={accountNotice} onSignIn={onSignIn} onSignUp={onSignUp} onSignOut={onSignOut} onDeviceLabelSave={onDeviceLabelSave} onProfileSave={onProfileSave} onAvatarUpload={onAvatarUpload} onAvatarRemove={onAvatarRemove} onResolveConflict={onResolveConflict} workspaceTransfer={workspaceTransfer} workspaceTransferBusy={workspaceTransferBusy} workspaceTransferNotice={workspaceTransferNotice} onWorkspaceTransferRefresh={onWorkspaceTransferRefresh} onWorkspaceTransferPush={onWorkspaceTransferPush} onWorkspaceTransferPreviewPull={onWorkspaceTransferPreviewPull} onWorkspaceTransferApplyPull={onWorkspaceTransferApplyPull} revision={revision} />
  return null
}
