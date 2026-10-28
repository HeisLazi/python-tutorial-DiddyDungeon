import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { buildQuestDocument, ContextPanel, GameScreen, projectDirOf, PyrChatPanel, RewardQueue, SurfaceNavigation, TutorPracticeBar } from './RpgViews.jsx?homePortParity20260921'
import { syncEngine } from './cloud/syncEngine.js'
import { pyrClientId } from './cloud/pyrClient.js'

const FRONTEND_BUILD_SHA = typeof __QUESTLAB_BUILD_SHA__ === 'string' ? __QUESTLAB_BUILD_SHA__ : ''

const api = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const body = await response.text()
    let message = body || `${response.status} ${response.statusText}`
    try {
      const parsed = JSON.parse(body)
      if (parsed?.detail) message = typeof parsed.detail === 'object' && parsed.detail.message ? parsed.detail.message : parsed.detail
    } catch {
      // Raw text is still useful when the backend is not returning JSON.
    }
    throw new Error(message)
  }
  return response.json()
}

const languageFor = (path = '') => {
  if (path.endsWith('.py')) return 'python'
  if (path.endsWith('.json')) return 'json'
  if (path.endsWith('.md')) return 'markdown'
  if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript'
  if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript'
  if (path.endsWith('.html')) return 'html'
  if (path.endsWith('.css') || path.endsWith('.scss')) return 'css'
  if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml'
  return 'plaintext'
}

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

function StatIcon({ name }) {
  const paths = {
    heart: <path d="M20 8c0 5-8 11-8 11S4 13 4 8a4 4 0 0 1 7-3 4 4 0 0 1 7 0 4 4 0 0 1 2 3z" />,
    coin: <><circle cx="12" cy="12" r="8" /><path d="M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5M12 6v12" /></>,
    flame: <path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z" />,
    shield: <path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z" />,
    sword: <path d="m14 4 6-1-1 6-9 9-4-4zM6 14l-3 3 4 4 3-3" />,
  }
  return (
    <span className="quest-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">{paths[name]}</svg>
    </span>
  )
}

function usePersistentState(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key)
      return stored === null ? initialValue : JSON.parse(stored)
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Device preferences should never break the IDE.
    }
  }, [key, value])

  return [value, setValue]
}

const LAUNCH_IDLE_MS = 20 * 60 * 1000

function launchContext() {
  try {
    const lastSeen = Number(window.localStorage.getItem('questlab.lastSeenAt') || 0)
    const hasLaunched = window.localStorage.getItem('questlab.hasLaunched') === '1'
    const returning = hasLaunched && lastSeen > 0 && Date.now() - lastSeen > LAUNCH_IDLE_MS
    return { show: !hasLaunched || returning, returning }
  } catch {
    // A storage-blocked browser should still be usable; show the lightweight
    // splash once for this mount rather than failing the IDE boot.
    return { show: true, returning: false }
  }
}

function launchWasAwayTooLong() {
  return launchContext().show
}

const terminalPalette = (skin) => {
  if (skin === 'terminal-emberglass') {
    return {
      background: '#100b09',
      foreground: '#f0e2d4',
      cursor: '#f0a45d',
      selectionBackground: '#4a2b1e',
    }
  }
  return {
    background: '#090b0a',
    foreground: '#e9e4d8',
    cursor: '#d8a657',
    selectionBackground: '#3b4035',
  }
}

// Vite Fast Refresh can tear down a component effect while a source edit is
// being applied. Keep the actual browser WebSocket/PTY session outside the
// React module instance so a hot UI refresh rebinds to the same shell instead
// of closing it and creating a second process. A short detach grace period
// still closes truly abandoned sessions (for example, when the page exits).
const terminalSessions = (() => {
  if (typeof globalThis === 'undefined') return new Map()
  const key = '__QUESTLAB_TERMINAL_SESSIONS__'
  if (globalThis[key] instanceof Map) return globalThis[key]
  const sessions = new Map()
  globalThis[key] = sessions
  return sessions
})()

const terminalSessionFor = (role) => {
  let session = terminalSessions.get(role)
  if (!session) {
    session = {
      role,
      socket: null,
      pending: [],
      consumer: null,
      reconnectTimer: null,
      detachTimer: null,
      state: 'connecting',
      banner: '',
    }
    terminalSessions.set(role, session)
  }
  return session
}

const clearTerminalTimer = (session, key) => {
  if (session?.[key]) {
    clearTimeout(session[key])
    session[key] = null
  }
}

const closeTerminalSession = (session) => {
  if (!session) return
  clearTerminalTimer(session, 'reconnectTimer')
  clearTerminalTimer(session, 'detachTimer')
  const socket = session.socket
  session.socket = null
  if (socket && socket.readyState < WebSocket.CLOSING) socket.close()
  session.consumer = null
  session.pending.length = 0
  terminalSessions.delete(session.role)
}

const scheduleTerminalDetach = (session) => {
  if (!session) return
  clearTerminalTimer(session, 'detachTimer')
  session.detachTimer = setTimeout(() => {
    if (!session.consumer) closeTerminalSession(session)
  }, 2_000)
}

const connectTerminalSession = (session, banner = session?.banner || '') => {
  if (!session || typeof window === 'undefined') return
  session.banner = banner
  clearTerminalTimer(session, 'detachTimer')
  const current = session.socket
  if (current && (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)) {
    session.consumer?.reportState(session.state)
    return
  }

  session.consumer?.reportState('connecting')
  session.state = 'connecting'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/terminal/${session.role}`)
  session.socket = socket

  socket.onopen = () => {
    if (session.socket !== socket) return
    session.state = 'connected'
    session.consumer?.reportState('connected')
    session.consumer?.term?.writeln(`\r\n\x1b[38;5;214m${session.banner}\x1b[0m`)
    session.consumer?.fitAndSync()
    while (session.pending.length && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'input', data: session.pending.shift() }))
    }
  }

  socket.onmessage = (event) => {
    session.consumer?.term?.write(event.data)
  }

  socket.onerror = () => {
    if (session.socket === socket) {
      session.state = 'error'
      session.consumer?.reportState('error')
    }
  }

  socket.onclose = () => {
    if (session.socket !== socket) return
    session.socket = null
    session.state = 'reconnecting'
    session.consumer?.reportState('reconnecting')
    session.consumer?.term?.writeln('\r\n\x1b[38;5;203m[Quest Lab] Terminal link dropped. Reconnecting…\x1b[0m')
    if (!session.consumer) return
    clearTerminalTimer(session, 'reconnectTimer')
    session.reconnectTimer = setTimeout(() => connectTerminalSession(session), 1_200)
  }
}

const TerminalPane = forwardRef(function TerminalPane(
  {
    role,
    banner,
    fontSize = 13,
    skin = 'terminal-charcoal',
    onStateChange,
  },
  ref,
) {
  const hostRef = useRef(null)
  const termRef = useRef(null)
  const fitRef = useRef(null)
  const sessionRef = useRef(null)
  const [state, setState] = useState('connecting')

  const reportState = (next) => {
    setState(next)
    onStateChange?.(next)
  }

  const fitAndSync = () => {
    const term = termRef.current
    const fit = fitRef.current
    const socket = sessionRef.current?.socket
    if (!term || !fit || !hostRef.current) return
    try {
      fit.fit()
      if (socket?.readyState === WebSocket.OPEN && term.cols > 0 && term.rows > 0) {
        socket.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
      }
    } catch {
      // Hidden/resizing terminal surfaces can briefly have zero geometry.
    }
  }

  const reconnectTerminal = () => {
    const session = sessionRef.current || terminalSessionFor(role)
    sessionRef.current = session
    const socket = session.socket
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close()
    clearTerminalTimer(session, 'reconnectTimer')
    session.reconnectTimer = setTimeout(() => connectTerminalSession(session, banner), 80)
  }

  useImperativeHandle(ref, () => ({
    send(text) {
      const session = sessionRef.current || terminalSessionFor(role)
      sessionRef.current = session
      const socket = session.socket
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data: text }))
        return true
      }
      session.pending.push(text)
      connectTerminalSession(session, banner)
      return false
    },
    focus() {
      termRef.current?.focus()
    },
    clear() {
      termRef.current?.clear()
    },
    getText() {
      const buffer = termRef.current?.buffer?.active
      if (!buffer) return ''
      const start = Math.max(0, buffer.length - 80)
      const lines = []
      for (let index = start; index < buffer.length; index += 1) {
        const line = buffer.getLine(index)
        if (line) lines.push(line.translateToString(true))
      }
      return lines.join('\n').replace(/\s+$/g, '').trim()
    },
    reconnect: reconnectTerminal,
    fit() {
      fitAndSync()
    },
  }))

  useEffect(() => {
    const session = terminalSessionFor(role)
    sessionRef.current = session
    clearTerminalTimer(session, 'detachTimer')
    const term = new Terminal({
      cursorBlink: true,
      convertEol: false,
      scrollback: 8000,
      fontFamily: 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace',
      fontSize,
      theme: terminalPalette(skin),
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(hostRef.current)
    termRef.current = term
    fitRef.current = fit

    session.consumer = {
      term,
      fitAndSync,
      reportState,
    }
    reportState(session.state)

    const input = term.onData((data) => {
      const socket = sessionRef.current?.socket
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const observer = new ResizeObserver(() => fitAndSync())
    observer.observe(hostRef.current)
    connectTerminalSession(session, banner)

    return () => {
      observer.disconnect()
      input.dispose()
      if (session.consumer?.term === term) session.consumer = null
      term.dispose()
      termRef.current = null
      fitRef.current = null
      scheduleTerminalDetach(session)
    }
  }, [role, banner])

  // Cosmetic terminal preferences are applied in place. Keeping this out of
  // the PTY/WebSocket lifecycle effect lets a live shell survive font-size or
  // Homestead terminal-skin changes.
  useEffect(() => {
    const term = termRef.current
    if (!term) return
    term.options.fontSize = fontSize
    term.options.theme = terminalPalette(skin)
    try {
      fitRef.current?.fit()
      const socket = sessionRef.current?.socket
      if (socket?.readyState === WebSocket.OPEN && term.cols > 0 && term.rows > 0) {
        socket.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
      }
    } catch {
      // Hidden/resizing terminal surfaces can briefly have zero geometry.
    }
  }, [fontSize, skin])

  return (
    <div className="terminal-v2-wrap">
      <div className="terminal-host" ref={hostRef} />
      {state !== 'connected' && (
        <button className={`terminal-reconnect state-${state}`} onClick={reconnectTerminal} title="Reconnect terminal">
          {state === 'connecting' ? 'connecting…' : state === 'reconnecting' ? 'reconnecting…' : 'reconnect'}
        </button>
      )}
    </div>
  )
})

// The banner follows the live board, so an extended board never shows a stale boss line.
function questLine(progress) {
  const project = (progress?.projects || []).find((item) => item?.status === 'active')
  const mobs = Array.isArray(project?.mobs) ? project.mobs : []
  const next = mobs.find((mob) => mob?.status === 'available')
  if (project && next && project.boss_status !== 'available') return `${project.name || project.branch}: next bounty, ${next.name}. Then face ${project.boss || 'the boss'}.`
  if (project && !project.completed && mobs.length && mobs.every((mob) => mob?.status === 'defeated' || mob?.status === 'cleared')) return `${project.name || project.branch}: the board is clear. Face ${project.boss || 'the boss'} in the Forge.`
  return progress?.current_quest || 'Choose a quest.'
}

// What a Dungeon fate room did, in plain words.
const DUNGEON_RISK_OUTCOMES = {
  elite: 'Elite ambush! A harder fight begins.',
  quiz: 'Risk quiz: answer right for run coins.',
  reward: 'Hidden cache: +20 run coins and a field bandage.',
  debuff: 'Hexed route: your next miss costs double HP.',
  buff: 'Ember blessing: your next correct answer hits harder.',
  teleport: 'The corridor folds: the route moves on.',
  discount: 'Discount stall: one supply at a discount.',
  armory: 'Sealed armory: take one weapon or armour piece.',
}

// Campaign objectives answered by clicking an option rather than submitting a file.
const BATTLE_CHOICE_TYPES = new Set(['prediction', 'explanation'])

// `cd "<workspace>/<folder>" && python3 "<file>"`, or the plain relative
// command while the workspace path is still loading.
function runInFolderCommand(workspace, path) {
  const parts = String(path || '').replaceAll('\\', '/').split('/').filter(Boolean)
  const file = parts.pop() || ''
  if (!workspace) return `python3 ${JSON.stringify(String(path || ''))}`
  const folder = [String(workspace).replace(/\/+$/, ''), ...parts].join('/')
  return `cd ${JSON.stringify(folder)} && python3 ${JSON.stringify(file)}`
}
const BOSS_PHASE_NAMES = { required_behavior: 'Required behaviour', explanation: 'Read your code', edge_cases: 'The boss twist', twist_2: "The boss's second phase", twist_3: "The boss's third phase", twist_4: "The boss's final phase", read_2: 'Read your code again', interview: 'Code interview' }
// Boss goals answered by clicking: a question about the player's own file.
const BOSS_CHOICE_TYPES = new Set(['snippet_check', 'code_interview'])

function AppV2() {
  const shellTerminalRef = useRef(null)
  const aiTerminalRef = useRef(null)
  const editorSelectionRef = useRef('')
  const editorSelectionSubscriptionRef = useRef(null)
  const pyrContextPublisherRef = useRef(null)
  const [campaign, setCampaign] = useState(null)
  const [rewardQueue, setRewardQueue] = useState([])
  const [runtime, setRuntime] = useState(null)
  const [files, setFiles] = useState([])
  const [activePath, setActivePath] = useState('')
  const [editorMode, setEditorMode] = useState('file')
  const [code, setCode] = useState('')
  // The editor text as of the last keystroke: Ctrl+S can fire before React
  // re-renders, so saving reads this, never a possibly stale `code`.
  const codeRef = useRef('')
  const setEditorCode = (value) => {
    codeRef.current = value
    setCode(value)
  }
  const [dirty, setDirty] = useState(false)
  const [tutorCode, setTutorCode] = useState('')
  const [tutorDirty, setTutorDirty] = useState(false)
  const [tutorDiskRevision, setTutorDiskRevision] = useState('')
  const [tutorExternalChange, setTutorExternalChange] = useState(null)
  const [dungeonCode, setDungeonCode] = useState('')
  const [dungeonDirty, setDungeonDirty] = useState(false)
  const [dungeonSaving, setDungeonSaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [shellState, setShellState] = useState('connecting')
  const [aiState, setAiState] = useState('connecting')
  const [cloudState, setCloudState] = useState(syncEngine.getState())
  const [accountBusy, setAccountBusy] = useState(false)
  const [accountNotice, setAccountNotice] = useState('')
  const [workspaceTransfer, setWorkspaceTransfer] = useState(null)
  const [workspaceTransferBusy, setWorkspaceTransferBusy] = useState(false)
  const [workspaceTransferNotice, setWorkspaceTransferNotice] = useState('')
  const tutorDirtyRef = useRef(false)
  const tutorDiskRevisionRef = useRef('')
  const tutorExternalChangeRef = useRef(null)
  const dungeonDirtyRef = useRef(false)
  const dungeonCodeRef = useRef('')
  const dungeonQuestionRef = useRef('')
  const campaignRevisionRef = useRef(null)
  const campaignInitializedRef = useRef(false)
  const seenStateEventsRef = useRef(new Set())
  const campaignRefreshInFlightRef = useRef(null)
  const submitCampaignRunRef = useRef(null)

  // Hub is the first-run/default destination. A previously selected route is
  // retained so a reload returns the learner to the screen they were using.
  const [storedActiveView, setStoredActiveView] = usePersistentState('questlab.activeView', 'hub')
  // Practice was an older navigation alias for the Tutor notebook. Keep old
  // Keep one Tutor route while allowing the now state-backed Infinite Dungeon
  // to be a first-class surface. Legacy quests still land in the Codex.
  const normalizeView = (value) => {
    if (value === 'practice') return 'tutor'
    if (value === 'quests') return 'codex'
    // The prototype replaces the old standalone Character and Homestead
    // destinations with the merged Campaign surface. Redirect persisted
    // legacy routes so a reload cannot reopen the retired pages.
    if (value === 'character' || value === 'homestead') return 'hub'
    return value
  }
  const activeView = normalizeView(storedActiveView)
  const setActiveView = (next) => setStoredActiveView((current) => {
    const candidate = typeof next === 'function' ? next(current) : next
    return normalizeView(candidate)
  })
  const [leftWidth, setLeftWidth] = usePersistentState('questlab.leftWidth', 300)
  const [leftPanelCollapsed, setLeftPanelCollapsed] = usePersistentState('questlab.leftPanelCollapsed', false)
  const [rightWidth, setRightWidth] = usePersistentState('questlab.rightWidth', 410)
  const [terminalHeight, setTerminalHeight] = usePersistentState('questlab.terminalHeight', 245)
  const [editorFontSize, setEditorFontSize] = usePersistentState('questlab.editorFontSize', 14)
  const [terminalFontSize, setTerminalFontSize] = usePersistentState('questlab.terminalFontSize', 13)
  const [hudDensity, setHudDensity] = usePersistentState('questlab.hudDensity', 'full')
  const [animations, setAnimations] = usePersistentState('questlab.animations', true)
  const [showAiTerminal, setShowAiTerminal] = usePersistentState('questlab.showAiTerminal', true)
  const [zenMode, setZenMode] = usePersistentState('questlab.zenMode', false)
  const [gameMode, setGameMode] = usePersistentState('questlab.gameMode', false)
  const [bossIntroSeen, setBossIntroSeen] = usePersistentState('questlab.bossIntroSeen', '')
  // OpenCode-backed PYR (ide/server/ai_tutor.py). `pyrThinking` is the label
  // shown while a model call runs; state writes pause until it clears.
  const [aiTutor, setAiTutor] = useState({ loaded: false, settings: null, opencode: null })
  const [pyrThinking, setPyrThinking] = useState('')
  // Forge PYR panel log (OpenCode mode): questions, replies and verdicts.
  const [pyrLog, setPyrLog] = useState([])
  const pushPyrLog = (entry) => setPyrLog((current) => [...current, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, ...entry }].slice(-40))
  const [themeChoice, setThemeChoice] = usePersistentState('questlab.themeChoice', '')
  const [fontFamily, setFontFamily] = usePersistentState('questlab.fontFamily', 'inter')
  const [initialLaunch] = useState(() => launchContext())
  const [showSplash, setShowSplash] = useState(() => initialLaunch.show)
  const [splashClosing, setSplashClosing] = useState(false)

  useEffect(() => {
    if (!showSplash) return
    const timer = setTimeout(() => dismissSplash(), 2500)
    return () => clearTimeout(timer)
  }, [showSplash])
  const [aiPopoverOpen, setAiPopoverOpen] = useState(false)
  const [levelUp, setLevelUp] = useState(false)
  const [confetti, setConfetti] = useState([])
  const [celebration, setCelebration] = useState(null)
  const prevBossGateRef = useRef(false)
  const prevLevelRef = useRef(null)

  const playSound = (freq, duration = 0.15) => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      const ctx = new Ctx()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = freq
      osc.type = 'square'
      gain.gain.setValueAtTime(0.08, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
      osc.start()
      osc.stop(ctx.currentTime + duration)
    } catch {}
  }

  const spawnConfetti = () => {
    const pieces = Array.from({ length: 40 }, (_, i) => ({
      id: i + Date.now(),
      left: Math.random() * 100,
      delay: Math.random() * 0.3,
      color: ['#00ff99', '#ff00ff', '#ffff00', '#00ffff'][i % 4],
    }))
    setConfetti(pieces)
    setTimeout(() => setConfetti([]), 1200)
  }

  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        setZenMode((z) => !z)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])
  const progress = campaign?.progress || {}
  const player = progress.player || {}
  // The active campaign project decides which file the Forge opens; a boss
  // clear moves the campaign on to the next project and its entry file.
  const activeProjectInfo = (progress.projects || []).find((project) => project.status === 'active') || {}
  const activeEntryFile = typeof activeProjectInfo.entry_file === 'string' ? activeProjectInfo.entry_file : ''
  const activeEntryFileRef = useRef('')
  activeEntryFileRef.current = activeEntryFile
  const lastProjectBranchRef = useRef(null)
  useEffect(() => {
    const branch = activeProjectInfo.branch || ''
    if (!branch) return
    if (lastProjectBranchRef.current && lastProjectBranchRef.current !== branch && activeEntryFile) {
      const exists = files.some((item) => String(item.path || '').toLowerCase() === activeEntryFile.toLowerCase())
      const name = activeProjectInfo.name || 'a new project'
      void (async () => {
        // Keep the old project's edits, then never leave its file open as
        // if it belonged to the new project.
        if (dirty) await saveFile()
        if (exists) return openFile(activeEntryFile, false)
        setEditorMode('file')
        setActivePath('')
        setEditorCode('')
        setDirty(false)
        setNotice(`Now playing ${name}. Its first bounty walks you through making ${activeEntryFile} in the terminal.`)
      })()
    }
    lastProjectBranchRef.current = branch
  }, [activeProjectInfo.branch])
  useEffect(() => {
    // On load the file tree can arrive before the campaign does; once the
    // entry file is known, a folder campaign re-picks one of its own files.
    const dir = projectDirOf(activeEntryFile).toLowerCase()
    if (!dir || dirty || editorMode !== 'file') return
    if (activePath && activePath.toLowerCase().startsWith(`${dir}/`)) return
    void refreshFiles()
  }, [activeEntryFile])
  const stats = progress.stats || {}
  const streak = progress.streak || {}
  const companion = progress.companion || {}
  const activity = campaign?.activity || {}
  const git = campaign?.git || {}
  const homestead = progress.homestead || {}
  const dungeon = campaign?.dungeon || { active: false, status: 'idle', editor_content: '' }
  const equipped = homestead.equipped || {}
  const campaignReady = Boolean(campaign && campaign.progress && typeof campaign.progress === 'object')
  const questDocument = buildQuestDocument(campaign)
  // Arcade is the default look; "homestead" opts back into the theme equipped
  // through Homestead cosmetics, and the named themes stay selectable.
  const theme = themeChoice === 'homestead'
    ? (equipped.theme || 'theme-ember-forge').replace('theme-', '')
    : (themeChoice || 'arcade')
  const terminalSkin = equipped.terminal || 'terminal-charcoal'
  // Tutor is now a self-contained resource surface (Codex → IDE → notes).
  // Forge remains the only route that owns the outer editor grid; keeping the
  // tutor editor mounted here would render the old duplicate surface beside
  // the new prototype port.
  const showEditor = activeView === 'forge'
  const tutorSurface = false
  const questSurface = activeView === 'forge' && editorMode === 'quest'
  const aiRouteHidden = ['hub', 'character', 'codex', 'tutor', 'homestead', 'settings', 'dungeon'].includes(activeView)
  const hubMode = activeView === 'hub'
  // Codex is a reading room, not another editor-column panel. Keep its
  // active-quest rail inside the folio while giving the book the full Forge
  // viewport so the page cannot collapse into a narrow infinite-feed shape.
  const wideSurface = ['hub', 'character', 'homestead', 'codex', 'tutor', 'settings'].includes(activeView)
  // Historical contract marker: the original wide route set was
  // const wideSurface = ['hub', 'character', 'homestead', 'codex', 'settings']
  // Tutor is intentionally included now because it owns the full resource
  // reader/IDE surface rather than the legacy Forge editor grid.
  const dungeonSurface = activeView === 'dungeon'
  const aiGridVisible = showAiTerminal && !aiRouteHidden && !zenMode
  const aiVisible = showAiTerminal && (!aiRouteHidden || aiPopoverOpen)
  const bossGateActive = activeView === 'forge' && (
    campaign?.encounter?.status === 'boss_available'
    || campaign?.encounter?.boss_status === 'available'
  )
  // The boss intro is a one-time announcement per boss, not a wall in front
  // of the editor the player needs to fight it from.
  const bossIntroKey = `${campaign?.encounter?.project_id || progress.current_project || 'project'}:${campaign?.encounter?.boss || 'boss'}`
  const showBossIntro = bossGateActive && bossIntroSeen !== bossIntroKey
  const welcomeName = cloudState.profile?.display_name || player.name || cloudState.user?.email?.split('@')?.[0] || 'Adventurer'
  const runtimeBranch = runtime?.repo_git?.branch || 'checking branch…'
  const runtimeMismatch = Boolean(runtime?.expected_branch && runtimeBranch !== runtime.expected_branch)
  const runtimeStale = Boolean(runtime?.repo_git?.behind_upstream > 0)
  const runtimeBuildMismatch = Boolean(
    FRONTEND_BUILD_SHA
      && runtime?.repo_git?.head_sha
      && FRONTEND_BUILD_SHA !== runtime.repo_git.head_sha,
  )
  const runtimeAuthority = runtime?.state_authority || {}
  const runtimeContractMissing = Boolean(
    runtime && (
      !runtime.expected_branch
      || !runtime.repo_git?.head_sha
      || !runtimeAuthority.canonical_path
      || runtimeAuthority.canonical_authoritative !== true
      || runtimeAuthority.legacy_authoritative !== false
      // A canonical-root workspace intentionally has no separate legacy path.
      // Treat null as the explicit one-authority shape, while still rejecting
      // an omitted or malformed path from a stale backend.
      || (
        runtimeAuthority.legacy_path !== null
        && (
          typeof runtimeAuthority.legacy_path !== 'string'
          || !runtimeAuthority.legacy_path.trim()
        )
      )
    ),
  )

  const shields = useMemo(
    () => (progress.skills || []).filter((skill) => skill.shield?.tier && skill.shield.tier !== 'none').length,
    [progress.skills],
  )

  const eventNotifications = (event) => {
    if (!event || typeof event !== 'object') return []
    const notifications = []
    const action = String(event.action || '')
    const mobName = event.mob_name || 'Current encounter'
    const xp = Number(event.reward_xp ?? event.xp ?? 0)
    const coins = Number(event.reward_coins ?? event.coins ?? 0)
    const levelBefore = Number(event.level_before)
    const levelAfter = Number(event.level_after)

    if (action === 'record_battle_objective') {
      if (Number(event.impact) > 0 && !event.mob_defeated) {
        notifications.push({
          id: `${event.id}:impact`,
          kind: 'objective',
          title: 'OBJECTIVE VERIFIED',
          body: `${mobName} · −${event.impact} Resolve`,
          detail: event.question_type ? `${event.question_type} checkpoint` : 'Validated Battle objective',
        })
      }
      if (event.guard_break) {
        notifications.push({
          id: `${event.id}:guard-break`,
          kind: 'reward',
          title: 'GUARD BROKEN',
          body: `${mobName} · free mistake banked`,
          detail: `+${Number(event.guard_break.coins || 0)} coins · the fight still needs every objective`,
        })
      }
      if (event.aid_loot) {
        notifications.push({
          id: `${event.id}:aid`,
          kind: 'unlock',
          title: 'AID FOUND',
          body: event.aid_loot.name,
          detail: event.aid_loot.effect || 'Added to your Armory (Aid)',
        })
      }
      if (event.loot) {
        notifications.push({
          id: `${event.id}:loot`,
          kind: 'unlock',
          title: `LOOT · ${String(event.loot.tier || '').toUpperCase()}`,
          body: event.loot.name,
          detail: event.loot.effect || 'Added to your Armory',
        })
      }
      if (event.mob_defeated) {
        notifications.push({
          id: `${event.id}:defeated`,
          kind: 'defeat',
          title: 'MOB DEFEATED',
          body: mobName,
          detail: [xp > 0 ? `+${xp} XP` : '', coins > 0 ? `+${coins} Coins` : ''].filter(Boolean).join(' · '),
        })
        if (event.next_mob) {
          notifications.push({
            id: `${event.id}:next`,
            kind: 'unlock',
            title: 'NEXT ENCOUNTER',
            body: event.next_mob,
            detail: 'Unlocked by the verified clear',
          })
        }
        if (event.boss_unlocked) {
          notifications.push({
            id: `${event.id}:boss-gate`,
            kind: 'unlock',
            title: 'BOSS GATE UNLOCKED',
            body: event.boss_name || 'Integrated project challenge',
            detail: 'All mobs cleared · behaviour, explanation and interview remain',
          })
        }
      }
    } else if (action === 'record_boss_clear' && event.boss_defeated) {
      const bossRewardValue = event.boss_reward_xp ?? event.reward_xp
      const bossRewardXp = typeof bossRewardValue === 'number' && Number.isFinite(bossRewardValue)
        ? bossRewardValue
        : null
      notifications.push({
        id: `${event.id}:boss`,
        kind: 'defeat',
        title: 'BOSS DEFEATED',
        body: event.boss_name || 'Project boss',
        detail: [
          bossRewardXp !== null ? `+${bossRewardXp} XP` : '',
          event.project_name || 'Project complete',
          event.next_project_name ? `Unlocked: ${event.next_project_name}` : '',
        ].filter(Boolean).join(' · '),
      })
      if (event.project_completed) {
        notifications.push({
          id: `${event.id}:complete`,
          kind: 'unlock',
          title: 'CAMPAIGN COMPLETE',
          body: event.project_name || 'Project complete',
          detail: 'Verified integrated challenge recorded; choose the next project when ready',
        })
      }
      if (event.companion_form_before && event.companion_form_after && event.companion_form_before !== event.companion_form_after) {
        notifications.push({
          id: `${event.id}:companion`,
          kind: 'mastery',
          title: 'COMPANION EVOLVED',
          body: event.companion_form_after,
          detail: `${event.companion_form_before} · first boss clear`,
        })
      }
    } else if (action === 'award_learning_reward' && (xp > 0 || coins > 0)) {
      notifications.push({
        id: `${event.id}:reward`,
        kind: 'reward',
        title: 'LEARNING REWARD',
        body: [xp > 0 ? `+${xp} XP` : '', coins > 0 ? `+${coins} Coins` : ''].filter(Boolean).join(' · '),
        detail: event.reason || 'Validated learning evidence',
      })
    } else if (action === 'record_achievement' && event.achievement_id) {
      notifications.push({
        id: `${event.id}:achievement`,
        kind: 'achievement',
        title: 'ACHIEVEMENT UNLOCKED',
        body: event.achievement_id,
        detail: event.reason || 'Validated campaign milestone',
      })
    } else if (action === 'homestead_purchase' && event.item_name) {
      notifications.push({
        id: `${event.id}:item`,
        kind: 'item',
        title: 'NEW ITEM',
        body: event.item_name,
        detail: 'Added to Homestead',
      })
    } else if (action === 'homestead_equip' && event.item_name) {
      notifications.push({
        id: `${event.id}:equip`,
        kind: 'item',
        title: 'LOADOUT UPDATED',
        body: event.item_name,
        detail: 'Equipment projection updated',
      })
    } else if (action === 'homestead_action') {
      const homeAction = event.home_action || ''
      const labels = {
        recover: 'Hearth restored your HP',
        bandage: 'Bandage used',
        meal: 'Meal used',
        feed_pyr: 'Pyr enjoyed a meal',
        train_pyr: 'Pyr training recorded',
        spend_token: 'Legacy upgrade token spent',
      }
      notifications.push({
        id: `${event.id}:home-action`,
        kind: homeAction === 'feed_pyr' || homeAction === 'train_pyr' ? 'mastery' : 'item',
        title: labels[homeAction] || 'Home action complete',
        body: event.pyr_form_after && event.pyr_form_after !== event.pyr_form_before ? `Pyr evolved · ${event.pyr_form_after}` : 'Homestead state updated',
        detail: event.healed ? `+${event.healed} HP` : event.reason || 'Saved through the canonical state gateway',
      })
    } else if (action === 'equip_equipment' && event.item_name) {
      notifications.push({
        id: `${event.id}:campaign-equip`,
        kind: 'item',
        title: 'CAMPAIGN LOADOUT UPDATED',
        body: event.item_name,
        detail: `${String(event.slot || 'equipment').toUpperCase()} slot equipped through the state gateway`,
      })
    } else if (action === 'record_equipment_unlock' && event.item_name) {
      notifications.push({
        id: `${event.id}:equipment-unlock`,
        kind: 'unlock',
        title: 'NEW CAMPAIGN GEAR',
        body: event.item_name,
        detail: 'Validated equipment unlock recorded',
      })
    } else if (action === 'record_codex_note') {
      notifications.push({
        id: `${event.id}:codex-note`,
        kind: 'objective',
        title: 'CODEX NOTE SAVED',
        body: 'Personal field note recorded',
        detail: `${Number(event.note_count ?? 0)} note${Number(event.note_count ?? 0) === 1 ? '' : 's'} on this encounter`,
      })
    } else if (action === 'record_battle_miss' || action === 'player_hp_change') {
      const damage = Number(event.damage ?? Math.max(0, -(Number(event.amount) || 0)))
      if (action === 'record_battle_miss' && event.objective_id) {
        notifications.push({
          id: `${event.id}:attempt`,
          kind: 'warning',
          title: 'BATTLE ATTEMPT RECORDED',
          body: `${mobName} · ${event.question_type || 'objective'}`,
          detail: 'Incorrect result added to the Codex; mastery evidence unchanged',
        })
      }
      if (damage > 0) {
        notifications.push({
          id: `${event.id}:hp`,
          kind: 'warning',
          title: 'COUNTERATTACK',
          body: `−${damage} HP`,
          detail: event.reason || 'Verified Battle miss',
        })
      }
      if (event.ward_used) {
        notifications.push({
          id: `${event.id}:ward`,
          kind: 'reward',
          title: 'WARD HELD',
          body: `Blocked ${Number(event.prevented_damage || 0)} HP of damage`,
          detail: 'Your armed ward took that wrong answer',
        })
      }
      if (event.trinket_trigger) {
        notifications.push({
          id: `${event.id}:trinket`,
          kind: 'reward',
          title: 'TRINKET TRIGGERED',
          body: event.trinket_trigger,
          detail: event.revived
            ? 'Revived at 1 HP'
            : event.prevented_damage
              ? `Prevented ${event.prevented_damage} HP damage`
              : 'Combat-only effect applied',
        })
      }
    } else if (action === 'record_boss_requirement') {
      notifications.push({
        id: `${event.id}:boss-phase`,
        kind: 'objective',
        title: 'BOSS PHASE VERIFIED',
        // The phase just verified, not the next one (boss_phase_label names the next goal).
        body: (event.boss_requirements_projection || []).find((phase) => phase.id === event.requirement_id)?.label || BOSS_PHASE_NAMES[event.requirement_id] || event.requirement_id || 'Boss requirement',
        detail: Array.isArray(event.remaining_boss_requirements) && event.remaining_boss_requirements.length
          ? `${event.remaining_boss_requirements.length} phase${event.remaining_boss_requirements.length === 1 ? '' : 's'} remaining`
          : 'Final gate ready for the integrated clear',
      })
    } else if (action === 'dungeon_start_run') {
      notifications.push({
        id: `${event.id}:dungeon-start`,
        kind: 'objective',
        title: 'DUNGEON RUN STARTED',
        body: `Floor ${event.floor ?? 1} · ${event.concept_id || 'adaptive concept'}`,
        detail: 'Starter loadout equipped; checkpoint is active',
      })
    } else if (action === 'dungeon_question_rotated') {
      notifications.push({
        id: `${event.id}:dungeon-question`,
        kind: 'unlock',
        title: 'NEW DUNGEON QUESTION',
        body: `${event.question_type || 'question'} · ${event.concept_id || 'adaptive concept'}`,
        detail: 'dungeon.py cleared for this room',
      })
    } else if (action === 'dungeon_record_verdict') {
      const fight = event.fight || null
      const blastNote = fight?.blast ? ` · self-destruct −${fight.blast} HP` : ''
      if (event.outcome === 'correct' && fight && !fight.fight_done) {
        notifications.push({
          id: `${event.id}:dungeon-hit`,
          kind: 'objective',
          title: fight.broke ? 'RESOLVE BROKEN' : 'HIT',
          body: `${event.mob_name || 'Mob'} · −${Number(fight.chip ?? 0)} Resolve`,
          detail: `Question ${fight.questions_cleared} of ${fight.questions_total} answered${fight.broke ? ' · free mistake banked' : ''}${blastNote}`,
        })
      } else if (event.outcome !== 'correct' && fight?.guard_used) {
        notifications.push({
          id: `${event.id}:dungeon-guard`,
          kind: 'reward',
          title: 'GUARD HELD',
          body: 'Free mistake used · no HP lost',
          detail: `Answer this question again${blastNote}`,
        })
      } else if (event.outcome === 'correct') {
        notifications.push({
          id: `${event.id}:dungeon-clear`,
          kind: 'objective',
          title: event.mob_name ? 'MOB DEFEATED' : 'DUNGEON ROOM CLEARED',
          body: event.mob_name || `+${Number(event.score_delta ?? 0)} score · +${Number(event.coins_delta ?? 0)} run coins`,
          detail: event.mob_name
            ? `+${Number(event.score_delta ?? 0)} score · +${Number(event.coins_delta ?? 0)} run coins · next room ${event.next_room ?? 'ready'}`
            : `Next room ${event.next_room ?? 'ready'} · ${event.next_room_type || 'encounter'}`,
        })
      } else {
        notifications.push({
          id: `${event.id}:dungeon-hit`,
          kind: 'warning',
          title: event.run_died ? 'DUNGEON RUN ENDED' : event.mob_name ? 'MOB COUNTERATTACK' : 'DUNGEON COUNTERATTACK',
          body: event.run_died ? `Score ${event.score ?? 0}` : event.mob_name ? `${event.mob_name} · −${Number(event.damage ?? 0) + Number(fight?.blast ?? 0)} HP` : `−${Number(event.damage ?? 0) + Number(fight?.blast ?? 0)} HP`,
          detail: event.run_died ? 'Death resets this run; Campaign is untouched' : 'Validated result; the current room remains active',
        })
      }
    } else if (action === 'dungeon_use_rest') {
      notifications.push({
        id: `${event.id}:dungeon-rest`,
        kind: 'reward',
        title: 'REST USED',
        body: `+${Number(event.healed ?? 0)} HP`,
        detail: `Room ${event.next_room ?? 'next'} is ready`,
      })
    } else if (action === 'dungeon_market_purchase') {
      notifications.push({
        id: `${event.id}:dungeon-market`,
        kind: 'item',
        title: 'DUNGEON ITEM',
        body: event.item_name || 'Run aid purchased',
        detail: `${Number(event.coins_delta ?? 0)} run coins`,
      })
    } else if (action === 'dungeon_finish_run') {
      notifications.push({
        id: `${event.id}:dungeon-finish`,
        kind: 'achievement',
        title: 'RUN BANKED',
        body: `${Number(event.score ?? 0)} score`,
        detail: 'Local leaderboard updated',
      })
    } else if (action === 'dungeon_run_reset') {
      notifications.push({
        id: `${event.id}:dungeon-reset`,
        kind: 'warning',
        title: 'DUNGEON RUN RESET',
        body: 'Checkpoint discarded',
        detail: 'Campaign progress and Codex evidence were left untouched',
      })
    } else if (action === 'dungeon_record_death') {
      notifications.push({
        id: `${event.id}:dungeon-death`,
        kind: 'warning',
        title: 'DUNGEON RUN ENDED',
        body: `Floor ${event.floor ?? 0} · ${event.score ?? 0} score`,
        detail: 'Death resets the run; Campaign progress is unchanged',
      })
    } else if (action === 'practice_record_attempt') {
      notifications.push({
        id: `${event.id}:practice-result`,
        kind: event.outcome === 'correct' ? 'reward' : 'objective',
        title: event.outcome === 'correct' ? 'TRAINING · CORRECT' : 'TRAINING · NOT YET',
        body: event.concept || 'Tutor training',
        detail: event.outcome === 'correct' ? 'Your sign grows. Training never costs HP.' : 'No HP lost. Read the why, then try another.',
      })
    } else if (action === 'reconcile_legacy_progress') {
      const restoredMobs = Array.isArray(event.restored_mobs) ? event.restored_mobs : []
      const restoredFields = Array.isArray(event.restored_fields) ? event.restored_fields : []
      const playerChanged = restoredFields.some((field) => field.startsWith('player.') || field.startsWith('stats.'))
      const encounterChanged = restoredFields.includes('encounter_state') || restoredFields.some((field) => field.includes('.mobs.') && field.endsWith('.status'))
      const codexChanged = restoredFields.some((field) => field.startsWith('codex.'))
      if (playerChanged) {
        notifications.push({
          id: `${event.id}:restored`,
          kind: 'reward',
          title: 'PROGRESS RESTORED',
          body: [
            Number.isFinite(Number(event.restored_level)) ? `Level ${event.restored_level}` : '',
            Number.isFinite(Number(event.restored_xp)) ? `${event.restored_xp} XP` : '',
            Number.isFinite(Number(event.restored_coins)) ? `${event.restored_coins} Coins` : '',
          ].filter(Boolean).join(' · '),
          detail: `Validated legacy evidence · ${restoredMobs.length} Blackjack mob${restoredMobs.length === 1 ? '' : 's'} cleared`,
        })
      }
      if (event.next_mob && encounterChanged) {
        notifications.push({
          id: `${event.id}:next`,
          kind: 'unlock',
          title: 'NEXT ENCOUNTER',
          body: event.next_mob,
          detail: 'Restored from the verified encounter sequence',
        })
      }
      if (Array.isArray(event.codex_entries) && event.codex_entries.length > 0 && codexChanged) {
        notifications.push({
          id: `${event.id}:codex`,
          kind: 'objective',
          title: 'CODEX UPDATED',
          body: `${event.codex_entries.length} encounter record${event.codex_entries.length === 1 ? '' : 's'}`,
          detail: 'Knowledge reconstructed from approved session evidence',
        })
      }
    }

    if (event.trinket_trigger && action !== 'record_battle_miss') {
      notifications.push({
        id: `${event.id}:trinket`,
        kind: 'reward',
        title: 'TRINKET TRIGGERED',
        body: event.trinket_trigger,
        detail: event.bonus_impact
          ? `+${event.bonus_impact} bonus Impact`
          : event.revived
            ? 'Revived at 1 HP'
            : event.prevented_damage
              ? `Prevented ${event.prevented_damage} HP damage`
              : 'Combat-only effect applied',
      })
    }

    if (Number.isFinite(levelBefore) && Number.isFinite(levelAfter) && levelAfter > levelBefore) {
      notifications.push({
        id: `${event.id}:level`,
        kind: 'level',
        title: 'LEVEL UP',
        body: `${levelBefore} → ${levelAfter}`,
        detail: 'Validated progression milestone',
      })
    }
    const unlockedAchievements = Array.isArray(event.achievements_unlocked) && event.achievements_unlocked.length
      ? event.achievements_unlocked
      : event.achievement_unlocked
        ? [event.achievement_unlocked]
        : []
    unlockedAchievements.forEach((achievement, index) => {
      notifications.push({
        id: `${event.id}:achievement-extra:${index}`,
        kind: 'achievement',
        title: 'ACHIEVEMENT UNLOCKED',
        body: achievement,
        detail: event.action === 'record_boss_clear' ? 'Verified boss milestone' : 'First verified encounter clear',
      })
    })
    const mastery = event.mastery || event.mastery_shield || event.shield
    if (mastery && typeof mastery === 'object' && (mastery.tier || mastery.shield || mastery.gained)) {
      notifications.push({
        id: `${event.id}:mastery`,
        kind: 'mastery',
        title: 'MASTERY SHIELD GAINED',
        body: mastery.tier || mastery.shield || 'New mastery evidence',
        detail: event.reason || 'Validated concept evidence',
      })
    }
    return notifications
  }

  const applyCampaign = (next) => {
    if (!next || typeof next !== 'object') return
    if (next.sync_storage_namespace) syncEngine.setCheckoutIdentity(next.sync_storage_namespace)
    const nextRevision = Number(next.revision ?? next.progress?.meta?.revision ?? 0)
    const revisionRegressed = campaignInitializedRef.current && campaignRevisionRef.current !== null && nextRevision < campaignRevisionRef.current
    if (revisionRegressed) {
      // A deliberate local reset or canonical-save restore can move the
      // revision backwards. Accept that new authority instead of freezing on
      // stale UI while the one-second poller retries the same snapshot.
      campaignInitializedRef.current = false
      campaignRevisionRef.current = null
      seenStateEventsRef.current = new Set()
    }
    const events = Array.isArray(next.progress?.state_events) ? next.progress.state_events : []
    if (!campaignInitializedRef.current) {
      events.forEach((event) => event?.id && seenStateEventsRef.current.add(event.id))
      campaignInitializedRef.current = true
    } else {
      const fresh = []
      events.forEach((event) => {
        if (!event?.id || seenStateEventsRef.current.has(event.id)) return
        seenStateEventsRef.current.add(event.id)
        fresh.push(...eventNotifications(event))
      })
      if (fresh.length) setRewardQueue((current) => [...current, ...fresh].slice(-8))
    }
    campaignRevisionRef.current = nextRevision
    setCampaign(next)
    syncEngine.observeCampaign(next)
  }

  const refreshCampaign = async ({ silent = false } = {}) => {
    if (campaignRefreshInFlightRef.current) return campaignRefreshInFlightRef.current
    const request = (async () => {
      try {
        const next = await api('/api/campaign')
        applyCampaign(next)
        setNotice((current) => /^(Campaign load failed|Campaign sync check failed)/.test(current || '') ? '' : current)
        return next
      } catch (error) {
        if (!silent || !campaignInitializedRef.current) setNotice(`Campaign load failed: ${error.message}`)
        return null
      } finally {
        campaignRefreshInFlightRef.current = null
      }
    })()
    campaignRefreshInFlightRef.current = request
    return request
  }

  const refreshAiTutor = async () => {
    try {
      const next = await api('/api/ai/status')
      setAiTutor({ loaded: true, settings: next.settings, opencode: next.opencode })
      return next
    } catch (error) {
      setAiTutor({ loaded: true, settings: null, opencode: { ready: false, detail: error.message } })
      return null
    }
  }

  const saveAiSettings = async (update) => {
    const next = await api('/api/ai/settings', { method: 'POST', body: JSON.stringify(update) })
    setAiTutor((current) => ({ ...current, settings: next.settings }))
    return next.settings
  }

  const openCodeReady = Boolean(aiTutor.opencode?.ready)
  // OpenCode mode is the default; Classic brings back the CLI terminal.
  // Without a ready OpenCode the panel falls back to Classic on its own.
  const pyrMode = aiTutor.settings?.mode === 'classic' ? 'classic' : 'opencode'
  const builtInPyr = pyrMode === 'opencode' && openCodeReady
  const autoGrade = builtInPyr && aiTutor.settings?.auto_grade !== false

  // Run one OpenCode call with the shared "PYR is thinking" lock. Concurrent
  // requests are refused so a second click cannot double-submit.
  const withPyr = async (label, task) => {
    if (pyrThinking) throw new Error('PYR is still thinking about the last request.')
    setPyrThinking(label)
    try {
      return await task()
    } finally {
      setPyrThinking('')
    }
  }

  // Grade an already-bound submission. A judge failure leaves the challenge
  // pending (no HP, no Resolve) so the player can simply submit again.
  const judgeWithPyr = (kind, submission, answer, question = '') => withPyr('PYR is judging your submission…', async () => {
    const result = await api('/api/ai/judge', {
      method: 'POST',
      body: JSON.stringify({ kind, submission, answer, question, client_id: pyrClientId() }),
    })
    setNotice(`PYR ${result.verdict === 'correct' ? '✔ correct' : '✘ not yet'} — ${result.reason}`)
    pushPyrLog({ role: 'verdict', verdict: result.verdict, text: result.reason })
    await refreshCampaign({ silent: true })
    return result
  })

  // Tutor Notebook tools: a real Ask PYR channel and AI-chosen question lenses.
  const pyrTools = {
    ready: openCodeReady,
    chooseLensEnabled: openCodeReady && aiTutor.settings?.choose_practice_lens !== false,
    ask: ({ question, concept, code, battle = false }) => withPyr('PYR is thinking…', async () => {
      const result = await api('/api/ai/ask', { method: 'POST', body: JSON.stringify({ question, concept, code, battle }) })
      if (result.assist) {
        // Help during a fight costs that fight's rewards (see the battle sidebar),
        // unless an armed PYR's Favour paid for it.
        const { reward_scale: scale, loot_lost: lootLost, mob_name: mobName, free, free_asks_left: freeLeft } = result.assist
        setNotice(free
          ? `PYR's Favour spent: that ask cost nothing (${freeLeft} free ask${freeLeft === 1 ? '' : 's'} left).`
          : `PYR helped against ${mobName}: it now pays ${scale}% XP and coins${lootLost ? ' and drops no loot' : ''}.`)
        void refreshCampaign({ silent: true })
      }
      return result.reply
    }),
    chooseLens: ({ concept, lenses }) => withPyr('PYR is picking a practice lens…', () => api('/api/ai/practice-lens', {
      method: 'POST',
      body: JSON.stringify({ concept, lenses }),
    })),
  }

  const refreshRuntime = async () => {
    try {
      const next = await api('/api/runtime')
      if (next.sync_storage_namespace) syncEngine.setCheckoutIdentity(next.sync_storage_namespace)
      setRuntime(next)
      return next
    } catch (error) {
      setNotice(`Runtime check failed: ${error.message}`)
      return null
    }
  }

  // Files made in the terminal (touch notes.md, mkdir tests) show up on
  // their own: while the Forge is open the tree is re-read every few
  // seconds and when the window regains focus. It only replaces the list
  // when something changed and never switches the open file.
  const filesSignatureRef = useRef('')
  filesSignatureRef.current = files.map((item) => `${item.type}:${item.path}`).join('|')
  useEffect(() => {
    if (activeView !== 'forge') return undefined
    let stopped = false
    const poll = async () => {
      if (stopped || document.visibilityState !== 'visible') return
      try {
        const result = await api('/api/tree')
        const nextFiles = (result.items || []).filter((item) => {
          const path = String(item?.path || '')
          return path && !path.startsWith('\\') && !path.includes('\0')
        })
        const signature = nextFiles.map((item) => `${item.type}:${item.path}`).join('|')
        if (!stopped && signature !== filesSignatureRef.current) setFiles(nextFiles)
      } catch {
        // The next tick tries again; a failed poll is never shown.
      }
    }
    const timer = window.setInterval(poll, 2500)
    window.addEventListener('focus', poll)
    return () => {
      stopped = true
      window.clearInterval(timer)
      window.removeEventListener('focus', poll)
    }
  }, [activeView])

  const refreshFiles = async () => {
    try {
      const result = await api('/api/tree')
      // Keep a malformed literal-backslash transfer directory from becoming
      // a second filesystem root if an older backend is still serving the
      // tree. The canonical server applies the same guard while walking.
      const nextFiles = (result.items || []).filter((item) => {
        const path = String(item?.path || '')
        return path && !path.startsWith('\\') && !path.includes('\0')
      })
      setFiles(nextFiles)
      // The tree also contains Quest Lab infrastructure. Never open an
      // arbitrary backend __init__.py as the learner's campaign surface;
      // prefer the active project's conventional file and otherwise leave
      // the editor empty until the transferred project source arrives.
      // A campaign in its own folder only ever opens a file from that folder,
      // so another campaign's blackjack.py is never shown in its place.
      const projectDir = projectDirOf(activeEntryFileRef.current).toLowerCase()
      const projectFiles = nextFiles.filter((item) => {
        if (item.type !== 'file' || !item.path.endsWith('.py') || item.path === 'tutor.py') return false
        const normalized = item.path.replaceAll('\\\\', '/').toLowerCase()
        if (projectDir) return normalized.startsWith(`${projectDir}/`) && !normalized.includes('/test_') && !normalized.includes('/tests/')
        return !normalized.startsWith('ide/') && !normalized.startsWith('tools/') && !normalized.startsWith('tests/') && !normalized.includes('/test_') && !normalized.includes('/tests/')
      })
      // Any file of a folder campaign (its README.md, notes) stays open.
      const activeProjectFile = projectFiles.some((item) => item.path === activePath)
        || (Boolean(projectDir) && nextFiles.some((item) => item.type === 'file' && item.path === activePath && item.path.toLowerCase().startsWith(`${projectDir}/`)))
      if (!activeProjectFile) {
        const preferredNames = [activeEntryFileRef.current.toLowerCase(), ...(projectDir ? [] : ['blackjack.py', 'campaign.py', 'main.py'])].filter(Boolean)
        const preferred = preferredNames.map((name) => projectFiles.find((item) => item.path.toLowerCase() === name)).find(Boolean) || projectFiles[0]
        if (preferred) await openFile(preferred.path, false)
        else {
          setActivePath('')
          setEditorCode('')
          setDirty(false)
        }
      }
    } catch (error) {
      setNotice(`File tree failed: ${error.message}`)
    }
  }

  const refreshTutor = async () => {
    try {
      const result = await api('/api/tutor')
      const revision = result.revision ?? ''
      tutorDiskRevisionRef.current = revision
      tutorExternalChangeRef.current = null
      tutorDirtyRef.current = false
      setTutorDiskRevision(revision)
      setTutorExternalChange(null)
      setTutorCode(result.content ?? '')
      setTutorDirty(false)
    } catch (error) {
      setNotice(`Tutor notebook failed: ${error.message}`)
    }
  }

  const publishPyrContext = async ({ terminalTail } = {}) => {
    const activeFile = activeView === 'tutor' || activeView === 'practice'
      ? 'tutor.py'
      : activeView === 'dungeon'
        ? 'dungeon.py'
        : activePath || null
    const result = await api('/api/pyr/context', {
      method: 'POST',
      body: JSON.stringify({
        active_path: activeFile,
        selection: editorSelectionRef.current || '',
        terminal_tail:
          typeof terminalTail === 'string' ? terminalTail : shellTerminalRef.current?.getText?.() || '',
        client_id: pyrClientId(),
      }),
    })
    return result.context || result
  }

  const pasteAiPrompt = (payload) => {
    const textarea = document.querySelector('.ai-panel .xterm-helper-textarea')
    if (!textarea) throw new Error('AI terminal is not ready yet.')
    textarea.focus()
    const data = new DataTransfer()
    data.setData('text/plain', `${payload}\n`)
    textarea.dispatchEvent(new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }))
  }

  const forgeSubmission = () => {
    const path = String(activePath || '').replaceAll('\\', '/')
    const filename = path.split('/').at(-1)?.toLowerCase() || ''
    if (!/\.(py|md)$/i.test(path) || filename === 'tutor.py' || filename === 'dungeon.py') {
      throw new Error('Open the campaign .py or README .md file this goal is graded on, then submit it.')
    }
    if (!String(code || '').trim()) throw new Error('Save or write evidence in the active Forge file before submitting it.')
    return { path, answer: String(code) }
  }

  const submitBattle = async ({ objectiveId }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!autoGrade && !provider) throw new Error('Set up OpenCode in Settings → AI Tutor, or launch a CLI in the PYR panel, then submit the Battle answer.')
    const forge = forgeSubmission()

    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const nonce = context?.verdict?.nonce
    if (!nonce) throw new Error('There is no active PYR encounter challenge. Capture context again.')
    const result = await api('/api/pyr/battle-submission', {
      method: 'POST',
      body: JSON.stringify({ nonce, objective_id: objectiveId, answer: forge.answer, answer_source: 'forge_active_file', source_path: forge.path, file_digest: context?.active_file?.digest || null }),
    })
    const submission = result.submission
    const objective = (context.encounter?.available_objectives || []).find((item) => item.id === objectiveId) || {}
    if (autoGrade) {
      await judgeWithPyr('battle', submission, forge.answer, objective.quest || objective.brief || objective.label || '')
      return submission
    }
    const prompt = [
      'Quest Lab Battle submission — provider adjudication required.',
      `Provider: ${provider}`,
      `Campaign revision: ${submission.revision}`,
      `Encounter: ${submission.mob_name}`,
      `Objective: ${submission.objective_id} (${submission.question_type}, ${submission.impact} Impact)`,
      `Submission ID: ${submission.submission_id}`,
      `Challenge nonce: ${submission.nonce}`,
      `Evidence ID: ${submission.evidence_id}`,
      `Answer digest: ${submission.answer_digest}`,
      '',
      `Active Forge file (${forge.path}) — submit this file as the player evidence:`,
      '```text',
      forge.answer.trim(),
      '```',
      '',
      'Adjudicate only this submitted answer against the current bounded context and the project evidence. Do not reveal hidden future questions or answers. If the answer is sufficient, call POST /api/pyr/verdict with this exact nonce, submission_id, answer_digest, objective_id and evidence_id, verdict=correct, and a concise reason. If it is incomplete or incorrect, call the same endpoint with verdict=incorrect and explain the learning gap. Never supply Impact, rewards, HP or damage values.',
      `Current objective metadata: ${JSON.stringify(objective)}`,
      '',
      'Bounded Quest Lab context (use only this current projection; do not infer or reveal future encounters):',
      `Quest projection: ${JSON.stringify(context.quest || {})}`,
      `Encounter projection: ${JSON.stringify(context.encounter || {})}`,
      `Active file (${context.active_file?.path || 'none'}):`,
      '```text',
      context.active_file?.content || '(none)',
      '```',
      'Selected code:',
      '```text',
      context.selection?.text || '(none)',
      '```',
      'Recent shell output:',
      '```text',
      context.terminal?.tail || '(none)',
      '```',
      `Git branch: ${context.git?.branch || 'detached'}`,
      'Bounded git diff:',
      '```diff',
      context.git?.diff || '(none)',
      '```',
      '',
    ].join('\n')
    pasteAiPrompt(prompt)
    setNotice(`Battle answer sent to ${provider}; waiting for its validated verdict.`)
    return submission
  }

  const submitBoss = async () => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!autoGrade && !provider) throw new Error('Set up OpenCode in Settings → AI Tutor, or launch a CLI in the PYR panel, then submit the boss evidence.')
    const forge = forgeSubmission()

    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const nonce = context?.verdict?.nonce
    if (!nonce || context?.verdict?.challenge_type !== 'boss') throw new Error('There is no active boss challenge. Capture context again.')
    const currentGoal = context?.encounter?.boss_current_requirement
    const requirementId = currentGoal?.id || context?.verdict?.current_requirement
    if (!requirementId) throw new Error('The boss has no current goal. Capture fresh context again.')
    if (BOSS_CHOICE_TYPES.has(currentGoal?.question_type)) throw new Error('This boss goal is a question about your code: click your answer in the left sidebar.')
    const result = await api('/api/pyr/boss-submission', {
      method: 'POST',
      body: JSON.stringify({ nonce, requirement_id: requirementId, answer: forge.answer, answer_source: 'forge_active_file', source_path: forge.path, file_digest: context?.active_file?.digest || null }),
    })
    const submission = result.submission
    if (autoGrade) {
      await judgeWithPyr('boss', submission, forge.answer, currentGoal?.quest || currentGoal?.label || requirementId)
      return submission
    }
    const prompt = [
      'Quest Lab boss gate — provider adjudication required.',
      `Provider: ${provider}`,
      `Campaign revision: ${submission.revision}`,
      `Project: ${submission.project_id}`,
      `Boss: ${submission.boss_name}`,
      `Current goal: ${currentGoal?.label || submission.requirement_id} (${currentGoal?.damage ?? currentGoal?.impact ?? 'canonical'} damage)`,
      `Submission ID: ${submission.submission_id}`,
      `Challenge nonce: ${submission.nonce}`,
      `Evidence ID: ${submission.evidence_id}`,
      `Answer digest: ${submission.answer_digest}`,
      '',
      `Active Forge file (${forge.path}) — submit this file as the player evidence:`,
      '```text',
      forge.answer.trim(),
      '```',
      '',
      'Adjudicate only this submitted evidence against the current bounded goal and project files. Do not reveal hidden future questions or answers. Call POST /api/pyr/boss-verdict with this exact nonce, submission_id, answer_digest, requirement_id and evidence_id, verdict=correct or incorrect, and a concise reason. Never supply rewards, Impact, HP or damage values; the state service owns those values. A correct verdict applies the canonical damage and reveals the next goal.',
      '',
      'Bounded current context:',
      `Quest projection: ${JSON.stringify(context.quest || {})}`,
      `Encounter projection: ${JSON.stringify(context.encounter || {})}`,
      `Active file (${context.active_file?.path || 'none'}):`,
      '```text',
      context.active_file?.content || '(none)',
      '```',
      'Selected code:',
      '```text',
      context.selection?.text || '(none)',
      '```',
      'Recent shell output:',
      '```text',
      context.terminal?.tail || '(none)',
      '```',
      `Git branch: ${context.git?.branch || 'detached'}`,
      'Bounded git diff:',
      '```diff',
      context.git?.diff || '(none)',
      '```',
      '',
    ].join('\n')
    pasteAiPrompt(prompt)
    setNotice(`Boss goal ${currentGoal?.label || requirementId.replaceAll('_', ' ')} sent to ${provider}; waiting for its validated verdict.`)
    return submission
  }

  const submitCampaignRun = async () => {
    if (activeView !== 'forge') throw new Error('Open Forge before submitting the campaign file.')
    const encounter = campaign?.encounter || {}
    const bossMode = encounter.status === 'boss_available' || encounter.boss_status === 'available'
    if (bossMode) return submitBoss()
    // Submit run answers BUILD / FIX objectives with the project file; PREDICT
    // and EXPLAIN objectives are clickable questions in the battle sidebar.
    // A goal that names its file is graded on that file, so submit the open
    // goal that matches the file in the editor (README.md, test_casino.py...).
    const setupGoal = (encounter.available_objectives || []).find((item) => item.question_type === 'setup_check')
    if (setupGoal) throw new Error(`Finish the setup step first: "${setupGoal.label}". Do it in the terminal, then press Check in the battle sidebar.`)
    const codeGoals = (encounter.available_objectives || []).filter((item) => !BATTLE_CHOICE_TYPES.has(item.question_type))
    const openPath = String(activePath || '').replaceAll('\\', '/')
    const board = campaign?.campaign_board || {}
    const goalPath = (item) => (item.file ? (board.project_dir ? `${board.project_dir}/${item.file}` : item.file) : String(board.entry_file || ''))
    const multiFile = (progress.projects || []).some((item) => item?.status === 'active' && item.multi_file === true)
    const currentQuest = codeGoals.find((item) => goalPath(item) === openPath) || (multiFile || codeGoals.some((item) => item.file) ? null : codeGoals[0])
    if (!currentQuest?.id) {
      if (codeGoals.length) throw new Error(`Open ${goalPath(codeGoals[0]) || 'the project file'} to submit "${codeGoals[0].label}".`)
      if ((encounter.available_objectives || []).length) throw new Error('Answer the question in the battle sidebar: this objective is a click, not a file.')
      throw new Error('There is no current state-owned quest to submit yet.')
    }
    return submitBattle({ objectiveId: currentQuest.id })
  }

  // Tutor sparring: simulated fights with foes already met (no damage).
  const sparActions = {
    ask: (targetId, round) => withPyr('PYR is writing the next round…', async () => {
      const result = await api('/api/ai/spar-question', { method: 'POST', body: JSON.stringify({ target_id: targetId, round }) })
      return result.question
    }),
    answerCode: async (targetId, code) => {
      setBusy(true)
      try {
        const result = await api('/api/spar/answer-code', { method: 'POST', body: JSON.stringify({ target_id: targetId, code }) })
        await refreshCampaign({ silent: true })
        return result
      } finally {
        setBusy(false)
      }
    },
    answer: async (targetId, index) => {
      setBusy(true)
      try {
        const result = await api('/api/spar/answer-option', { method: 'POST', body: JSON.stringify({ target_id: targetId, option_index: index }) })
        await refreshCampaign({ silent: true })
        return result
      } finally {
        setBusy(false)
      }
    },
  }

  // Clickable campaign questions (PREDICT / EXPLAIN objectives).
  const [battleQuestions, setBattleQuestions] = useState({})
  const [battleFeedback, setBattleFeedback] = useState(null)
  const askBattleQuestion = (objectiveId) => withPyr('PYR is writing your question…', async () => {
    const result = await api('/api/ai/battle-question', { method: 'POST', body: JSON.stringify({ objective_id: objectiveId }) })
    setBattleQuestions((current) => ({ ...current, [objectiveId]: result.question }))
  }).catch((error) => setNotice(`PYR could not write the question (${error.message}).`))
  const answerBattleOption = async (objectiveId, index) => {
    setBusy(true)
    try {
      const result = await api('/api/battle/answer-option', { method: 'POST', body: JSON.stringify({ objective_id: objectiveId, option_index: index }) })
      setBattleFeedback({ objectiveId, verdict: result.verdict, reason: result.reason })
      setBattleQuestions((current) => {
        const next = { ...current }
        delete next[objectiveId]
        return next
      })
      await refreshCampaign({ silent: true })
    } catch (error) {
      setNotice(`Answer not checked: ${error.message}`)
      setBattleQuestions((current) => {
        const next = { ...current }
        delete next[objectiveId]
        return next
      })
    } finally {
      setBusy(false)
    }
  }

  // A workshop setup step (make the folder, the file, run it): the server
  // looks on disk itself. Not done yet is no miss, just try again.
  const checkSetupStep = async (objectiveId) => {
    setBusy(true)
    try {
      const result = await api('/api/battle/setup-check', { method: 'POST', body: JSON.stringify({ objective_id: objectiveId }) })
      setBattleFeedback({ objectiveId, verdict: result.verdict, reason: result.reason, output: result.output })
      await Promise.all([refreshCampaign({ silent: true }), refreshFiles()])
    } catch (error) {
      setNotice(`Setup not checked: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  // Clickable boss goals (read your code, code interview), about your own file.
  const askBossQuestion = (requirementId) => withPyr('PYR is reading your code for a question…', async () => {
    const result = await api('/api/ai/boss-question', { method: 'POST', body: '{}' })
    setBattleQuestions((current) => ({ ...current, [`boss:${requirementId}`]: result.question }))
  }).catch((error) => setNotice(`PYR could not write the question (${error.message}).`))
  const answerBossOption = async (requirementId, index) => {
    setBusy(true)
    try {
      const result = await api('/api/boss/answer-option', { method: 'POST', body: JSON.stringify({ requirement_id: requirementId, option_index: index }) })
      setBattleFeedback({ objectiveId: `boss:${requirementId}`, verdict: result.verdict, reason: result.complete ? `${result.reason} The boss falls!` : result.reason })
      await refreshCampaign({ silent: true })
    } catch (error) {
      setNotice(`Answer not checked: ${error.message}`)
    } finally {
      setBattleQuestions((current) => {
        const next = { ...current }
        delete next[`boss:${requirementId}`]
        return next
      })
      setBusy(false)
    }
  }

  const submitDungeon = async ({ runId, questionId, answer }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!autoGrade && !provider) throw new Error('Set up OpenCode in Settings → AI Tutor, or launch a CLI in the PYR panel, then submit the Dungeon answer.')
    if (typeof answer !== 'string' || !answer.trim()) throw new Error('Write an answer in dungeon.py before submitting it.')

    // Flush the editor checkpoint first: an autosave landing between the
    // context capture and the submission changes the revision, and the
    // gateway then rejects the answer as stale.
    if (dungeonSavePromiseRef.current) await dungeonSavePromiseRef.current
    if (dungeonDirtyRef.current) await saveDungeon()

    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const challenge = context?.dungeon_verdict
    if (!challenge?.nonce || challenge.run_id !== runId || challenge.question_id !== questionId) {
      throw new Error('There is no active Dungeon challenge for this room. Capture context again.')
    }
    const result = await api('/api/pyr/dungeon-submission', {
      method: 'POST',
      body: JSON.stringify({ nonce: challenge.nonce, run_id: runId, question_id: questionId, answer }),
    })
    const submission = result.submission
    if (autoGrade) {
      const judged = await judgeWithPyr('dungeon', submission, answer, context.dungeon?.question?.prompt || '')
      return { ...submission, judged }
    }
    const prompt = [
      'Quest Lab Infinite Dungeon — provider adjudication required.',
      `Provider: ${provider}`,
      `Campaign revision: ${submission.revision}`,
      `Run: ${submission.run_id}`,
      `Room question: ${submission.question_id} (${submission.question_type}, ${submission.concept_id})`,
      `Submission ID: ${submission.submission_id}`,
      `Challenge nonce: ${submission.nonce}`,
      `Evidence ID: ${submission.evidence_id}`,
      `Answer digest: ${submission.answer_digest}`,
      '',
      'Player Dungeon answer:',
      '```text',
      answer.trim(),
      '```',
      '',
      'Adjudicate only this submitted answer against the current Dungeon question and bounded context. Do not reveal hidden future questions or answer keys. Call POST /api/pyr/dungeon-verdict with this exact nonce, submission_id, answer_digest, verdict=correct or incorrect, run_id, question_id, evidence_id and a concise reason. Never supply score, coins, damage or rewards; the state service decides those values. A correct verdict clears this room and rotates dungeon.py to a blank next-room buffer.',
      '',
      'Current Dungeon projection:',
      JSON.stringify(context.dungeon || {}),
      'Bounded current context:',
      `Quest projection: ${JSON.stringify(context.quest || {})}`,
      `Encounter projection: ${JSON.stringify(context.encounter || {})}`,
      `Active file (${context.active_file?.path || 'none'}):`,
      '```text',
      context.active_file?.content || '(none)',
      '```',
      'Recent shell output:',
      '```text',
      context.terminal?.tail || '(none)',
      '```',
      '',
    ].join('\n')
    pasteAiPrompt(prompt)
    setNotice(`Dungeon answer sent to ${provider}; waiting for its validated verdict.`)
    return submission
  }

  pyrContextPublisherRef.current = publishPyrContext
  submitCampaignRunRef.current = submitCampaignRun

  // Track real use rather than treating a hot reload as an away period. The
  // splash is an interruption only on first launch or after twenty minutes
  // away; it never unmounts the editor or either PTY.
  useEffect(() => {
    if (storedActiveView === 'practice') setStoredActiveView('tutor')
  }, [storedActiveView, setStoredActiveView])

  useEffect(() => {
    if (activeView !== 'forge' && editorMode === 'quest') setEditorMode('file')
  }, [activeView, editorMode])

  useEffect(() => {
    if (!aiRouteHidden) setAiPopoverOpen(false)
  }, [activeView, aiRouteHidden])

  useEffect(() => {
    const touch = () => {
      try {
        window.localStorage.setItem('questlab.hasLaunched', '1')
        window.localStorage.setItem('questlab.lastSeenAt', String(Date.now()))
      } catch {
        // Preferences are best-effort and must not block the Forge.
      }
    }
    touch()
    const onActivity = () => touch()
    window.addEventListener('pointerdown', onActivity, { passive: true })
    window.addEventListener('keydown', onActivity, { passive: true })
    return () => {
      window.removeEventListener('pointerdown', onActivity)
      window.removeEventListener('keydown', onActivity)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      // Resolve the opaque checkout namespace before auth restoration so a
      // same-origin second checkout cannot reuse this one's sync mailbox.
      await refreshRuntime()
      if (cancelled) return
      syncEngine.initialize()
      await Promise.all([refreshCampaign(), refreshFiles()])
      // OpenCode discovery shells out a couple of times; keep it off the
      // critical path so the campaign renders first.
      void refreshAiTutor()
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [])

  // Tutor Notebook and Practice intentionally share one tutor.py IDE surface.
  // Practice selectors sit above this editor and provider adjudication still
  // records bounded learning evidence through the state service.

  // The DOM enhancement layer and any local AI client can request this
  // explicitly captured context without knowing React's editor/terminal refs.
  // The function itself is stable; the ref always points at the current view.
  useEffect(() => {
    window.__questlabPublishPyrContext = (options) => pyrContextPublisherRef.current?.(options)
    window.__questlabSubmitCampaignRun = () => submitCampaignRunRef.current?.()
    return () => {
      delete window.__questlabPublishPyrContext
      delete window.__questlabSubmitCampaignRun
    }
  }, [])

  useEffect(() => () => {
    editorSelectionSubscriptionRef.current?.dispose()
    editorSelectionSubscriptionRef.current = null
  }, [])

  useEffect(() => {
    if (activeView !== 'settings') return undefined
    void refreshWorkspaceTransfer()
    return undefined
  }, [activeView])

  useEffect(() => {
    editorSelectionRef.current = ''
  }, [activeView])

  // Campaign state is an external projection: check the cheap revision every
  // second and fetch the full snapshot only when the state service committed a
  // new revision. This effect never touches either PTY lifecycle.
  useEffect(() => {
    let cancelled = false
    const pollCampaignRevision = async () => {
      try {
        const metadata = await api('/api/state/revision')
        if (cancelled) return
        if (metadata.sync_storage_namespace) syncEngine.setCheckoutIdentity(metadata.sync_storage_namespace)
        const revision = Number(metadata.revision ?? 0)
        if (!campaignInitializedRef.current || campaignRevisionRef.current === null) {
          await refreshCampaign({ silent: true })
          return
        }
        if (revision !== campaignRevisionRef.current) await refreshCampaign({ silent: true })
      } catch (error) {
        if (!cancelled && !campaignInitializedRef.current) setNotice(`Campaign sync check failed: ${error.message}`)
      }
    }
    void pollCampaignRevision()
    const timer = window.setInterval(pollCampaignRevision, 1000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    if (!rewardQueue.length) return undefined
    const timer = window.setTimeout(() => setRewardQueue((current) => current.slice(1)), 5200)
    return () => window.clearTimeout(timer)
  }, [rewardQueue])

  // Publish after React has committed the new projection so DOM enhancement
  // layers (combat shell/icon polish) read the same revision and values.
  useEffect(() => {
    if (campaign) window.dispatchEvent(new CustomEvent('questlab:campaign-updated', { detail: campaign }))
  }, [campaign])

  useEffect(() => {
    tutorDirtyRef.current = tutorDirty
  }, [tutorDirty])

  useEffect(() => {
    tutorDiskRevisionRef.current = tutorDiskRevision
  }, [tutorDiskRevision])

  useEffect(() => {
    dungeonDirtyRef.current = dungeonDirty
  }, [dungeonDirty])

  useEffect(() => {
    const snapshot = campaign?.dungeon
    const questionId = snapshot?.question?.id || ''
    const previousQuestionId = dungeonQuestionRef.current
    const questionRotated = Boolean(previousQuestionId && questionId && previousQuestionId !== questionId)
    dungeonQuestionRef.current = questionId
    if (questionRotated || !dungeonDirtyRef.current || !snapshot?.active) {
      const nextContent = snapshot?.active ? snapshot.editor_content || '' : ''
      dungeonCodeRef.current = nextContent
      setDungeonCode(nextContent)
      setDungeonDirty(false)
      dungeonDirtyRef.current = false
    }
  }, [campaign?.dungeon?.run_id, campaign?.dungeon?.question?.id, campaign?.dungeon?.editor_content, campaign?.dungeon?.status])

  // Poll only while the collaborative notebook is visible. A clean editor
  // follows an external write immediately; a dirty editor keeps its text and
  // surfaces the external version as an explicit reload/keep decision.
  useEffect(() => {
    if (!['tutor', 'practice'].includes(activeView)) return undefined
    let cancelled = false

    const pollTutor = async () => {
      try {
        const result = await api('/api/tutor')
        if (cancelled) return
        const revision = result.revision ?? ''
        const previousRevision = tutorDiskRevisionRef.current
        if (!previousRevision) {
          tutorDiskRevisionRef.current = revision
          setTutorDiskRevision(revision)
          return
        }
        if (revision === previousRevision) return

        tutorDiskRevisionRef.current = revision
        setTutorDiskRevision(revision)
        if (tutorDirtyRef.current) {
          const external = { revision, content: result.content ?? '' }
          tutorExternalChangeRef.current = external
          setTutorExternalChange(external)
          setNotice('tutor.py changed externally. Your edits are preserved; choose Reload or Keep my edits.')
          return
        }

        tutorDirtyRef.current = false
        tutorExternalChangeRef.current = null
        setTutorExternalChange(null)
        setTutorCode(result.content ?? '')
        setTutorDirty(false)
        setNotice('PYR updated tutor.py')
      } catch (error) {
        if (!cancelled) setNotice(`Tutor sync check failed: ${error.message}`)
      }
    }

    void pollTutor()
    const timer = window.setInterval(pollTutor, 1000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [activeView])

  useEffect(() => {
    const unsubscribe = syncEngine.subscribe(setCloudState)
    return unsubscribe
  }, [])

  useEffect(() => {
    const onKey = (event) => {
      const modifier = event.ctrlKey || event.metaKey
      if (modifier && !event.shiftKey && event.key === 'Enter') {
        // Monaco treats Ctrl/Cmd+Enter as a command only when the browser
        // event is intercepted early. Prevent the newline/space insertion and
        // run the currently visible source through the existing save gateway.
        event.preventDefault()
        event.stopPropagation()
        if (tutorSurface) void runTutor()
        else if (activeView === 'forge') void runCurrent()
        else if (activeView === 'dungeon') document.querySelector('[data-dungeon-run]')?.click()
        else if (activeView === 'tutor' || activeView === 'practice') document.querySelector('[data-tutor-run]')?.click()
        return
      }
      if (modifier && event.shiftKey && event.key === 'Enter') {
        // Submit has the same Monaco interception problem as Run. The
        // enhancement owns the bounded PYR context bridge, so trigger its
        // button from this capture-phase guard while the editor still has
        // focus; the fallback clipboard path remains in that handler.
        event.preventDefault()
        event.stopPropagation()
        // Each surface owns its own submit button; click the one on screen.
        const target = activeView === 'dungeon' ? '[data-dungeon-submit]' : activeView === 'tutor' || activeView === 'practice' ? '[data-tutor-submit]' : '[data-qol-submit]'
        document.querySelector(target)?.click()
        return
      }
      if (modifier && event.key.toLowerCase() === 's') {
        event.preventDefault()
        event.stopPropagation()
        if (activeView === 'tutor' || activeView === 'practice') saveTutor()
        if (activeView === 'forge') saveFile()
        if (activeView === 'dungeon') saveDungeon()
      }
      if (event.shiftKey && event.altKey && event.key.toLowerCase() === 'f') {
        event.preventDefault()
        event.stopPropagation()
        if (activeView === 'tutor' || activeView === 'practice') formatTutor()
        if (activeView === 'forge') formatCurrent()
      }
      if (modifier && event.key === '`') {
        event.preventDefault()
        event.stopPropagation()
        setActiveView('forge')
        setTimeout(() => shellTerminalRef.current?.focus(), 30)
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  })

  useEffect(() => {
    const timer = setTimeout(() => {
      shellTerminalRef.current?.fit()
      aiTerminalRef.current?.fit()
    }, 40)
    return () => clearTimeout(timer)
  }, [activeView, leftWidth, leftPanelCollapsed, rightWidth, terminalHeight])

  const startResize = (kind, event) => {
    event.preventDefault()
    event.currentTarget?.setPointerCapture?.(event.pointerId)
    const startX = event.clientX
    const startY = event.clientY
    const startLeft = leftWidth
    const startRight = rightWidth
    const startTerminal = terminalHeight

    const move = (moveEvent) => {
       if (kind === 'left') setLeftWidth(clamp(startLeft + moveEvent.clientX - startX, 260, 560))
      if (kind === 'right') setRightWidth(clamp(startRight - (moveEvent.clientX - startX), 300, 780))
      if (kind === 'terminal') setTerminalHeight(clamp(startTerminal - (moveEvent.clientY - startY), 140, 580))
    }
    const stop = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', stop)
      document.body.classList.remove('resizing')
    }

    document.body.classList.add('resizing')
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', stop)
  }

  const openFile = async (path, confirmDiscard = true) => {
    if (confirmDiscard && dirty && path !== activePath && !window.confirm('Discard unsaved changes?')) return
    try {
      setBusy(true)
      const result = await api(`/api/file?path=${encodeURIComponent(path)}`)
      setEditorMode('file')
      setActivePath(path)
      editorSelectionRef.current = ''
      setEditorCode(result.content ?? '')
      setDirty(false)
      setNotice('')
    } catch (error) {
      setNotice(`Open failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const openQuestDocument = () => {
    if (dirty && !window.confirm('Discard unsaved Forge edits before opening the state-owned quest view?')) return
    setEditorMode('quest')
    editorSelectionRef.current = ''
    setDirty(false)
    setNotice('Opened quest.md state view. Progress and Resolve remain gateway-owned.')
  }

  const saveFile = async () => {
    if (!activePath || editorMode === 'quest') return false
    try {
      setBusy(true)
      await api('/api/file', {
        method: 'PUT',
        body: JSON.stringify({ path: activePath, content: codeRef.current }),
      })
      setDirty(false)
      setNotice(`Saved ${activePath}`)
      refreshCampaign()
      refreshFiles()
      return true
    } catch (error) {
      setNotice(`Save failed: ${error.message}`)
      return false
    } finally {
      setBusy(false)
    }
  }

  const saveTutor = async () => {
    try {
      setBusy(true)
      const result = await api('/api/tutor', {
        method: 'PUT',
        body: JSON.stringify({ content: tutorCode }),
      })
      const revision = result.revision ?? ''
      tutorDiskRevisionRef.current = revision
      tutorExternalChangeRef.current = null
      tutorDirtyRef.current = false
      setTutorDiskRevision(revision)
      setTutorExternalChange(null)
      setTutorDirty(false)
      setNotice('Saved collaborative tutor.py')
      refreshFiles()
      return true
    } catch (error) {
      setNotice(`Tutor save failed: ${error.message}`)
      return false
    } finally {
      setBusy(false)
    }
  }

  // The in-flight checkpoint save, so a submit can wait for it.
  const dungeonSavePromiseRef = useRef(null)
  const saveDungeon = async () => {
    if (dungeonSavePromiseRef.current) return dungeonSavePromiseRef.current
    const pending = saveDungeonNow()
    dungeonSavePromiseRef.current = pending
    try {
      return await pending
    } finally {
      if (dungeonSavePromiseRef.current === pending) dungeonSavePromiseRef.current = null
    }
  }
  const saveDungeonNow = async () => {
    if (!dungeon.active || !dungeon.run_id) return false
    const contentToSave = dungeonCodeRef.current
    const questionId = dungeon.question?.id || ''
    if (!questionId) {
      setNotice('Dungeon checkpoint failed: the current question is unavailable.')
      return false
    }
    try {
      setDungeonSaving(true)
      const result = await api('/api/dungeon/editor', {
        method: 'PUT',
        body: JSON.stringify({ run_id: dungeon.run_id, question_id: questionId, content: contentToSave }),
      })
      if (dungeonCodeRef.current === contentToSave) {
        setDungeonDirty(false)
        dungeonDirtyRef.current = false
      }
      await refreshCampaign({ silent: true })
      setNotice('Dungeon checkpoint saved. This room will resume after a restart.')
      return true
    } catch (error) {
      setNotice(`Dungeon checkpoint failed: ${error.message}`)
      return false
    } finally {
      setDungeonSaving(false)
    }
  }

  const dungeonAction = async (path, payload, successMessage) => {
    try {
      setBusy(true)
      const result = await api(path, { method: 'POST', body: JSON.stringify(payload) })
      await refreshCampaign({ silent: true })
      setNotice(successMessage(result))
      return result
    } catch (error) {
      setNotice(`Dungeon action failed: ${error.message}`)
      throw error
    } finally {
      setBusy(false)
    }
  }

  const useDungeonRest = (runId) => dungeonAction('/api/dungeon/rest', { run_id: runId }, (result) => `Rest used. +${result.healed ?? 0} HP; the next room is ready.`)
  const useDungeonCampAction = (runId, action) => dungeonAction('/api/dungeon/camp', { run_id: runId, action }, (result) => {
    const labels = { rest: 'Rest', bandage: 'Bandage', tonic: 'Tonic', cook: 'Cooked ration', sharpen: 'Sharpened edge', fortify: 'Fortified armor' }
    return `${labels[action] || action} complete${result.healed ? ` · +${result.healed} HP` : ''}. One campsite action used.`
  })
  const revealDungeonRisk = (runId) => dungeonAction('/api/dungeon/risk/reveal', { run_id: runId }, () => 'Vision scroll consumed. The risk profile is now visible.')
  const enterDungeonRisk = (runId) => dungeonAction('/api/dungeon/risk/enter', { run_id: runId }, (result) => DUNGEON_RISK_OUTCOMES[result.risk_kind] || 'The fate is sealed. Choose your next room.')
  const buyDungeonItem = (runId, itemId) => dungeonAction('/api/dungeon/market', { run_id: runId, item_id: itemId }, (result) => `Bought ${result.item?.name || itemId} for run currency.`)
  // A clicked option is graded instantly by the server's hidden key; a
  // question without one (built-in, or after a restart) goes to PYR as text.
  const answerDungeonOption = async ({ runId, questionId, index, text }) => {
    setBusy(true)
    try {
      const result = await api('/api/dungeon/answer-option', { method: 'POST', body: JSON.stringify({ run_id: runId, question_id: questionId, option_index: index }) })
      if (result.graded) {
        await refreshCampaign({ silent: true })
        return result
      }
    } finally {
      setBusy(false)
    }
    return submitDungeon({ runId, questionId, answer: text })
  }
  const travelDungeon = (runId, nodeId) => dungeonAction('/api/dungeon/travel', { run_id: runId, node_id: nodeId }, () => 'You walk back through explored rooms.')
  const applyDungeonOil = (runId, oilId) => dungeonAction('/api/dungeon/oil', { run_id: runId, oil_id: oilId }, (result) => `${result.oil?.name || 'Oil'} applied: ${result.oil?.effect || ''}`)
  const equipDungeonItem = (runId, itemId) => dungeonAction('/api/dungeon/equip', { run_id: runId, item_id: itemId }, (result) => `${result.equipped || itemId} equipped.`)
  const chooseDungeonRoom = (runId, choiceId) => dungeonAction('/api/dungeon/choose', { run_id: runId, choice_id: choiceId }, (result) => {
    const kind = result.choice?.kind || result.dungeon?.room_type || 'room'
    const words = { encounter: 'A gate fight', elite: 'An elite fight', rest: 'A camp', market: 'A market', mystery: 'A fate room', boss: 'The boss' }
    return `${words[kind] || 'A new room'} waits. Read the room panel.`
  })
  const leaveDungeonRoom = (runId) => dungeonAction('/api/dungeon/leave', { run_id: runId }, () => 'Room cleared. Choose the next route on the map.')
  const finishDungeonRun = (runId) => dungeonAction('/api/dungeon/finish', { run_id: runId }, (result) => `Run banked at ${result.score ?? result.dungeon?.score ?? 0} score.`)
  const resetDungeonRun = (runId) => {
    if (typeof window !== 'undefined' && typeof window.confirm === 'function' && !window.confirm('Reset this Dungeon run? The checkpoint, score and run gear will be discarded; Campaign progress stays safe.')) return Promise.resolve(null)
    return dungeonAction('/api/dungeon/reset', { run_id: runId }, () => 'Dungeon run reset. Choose a class to begin again.')
  }

  const startDungeon = async (startOptions) => {
    try {
      setBusy(true)
      const options = typeof startOptions === 'string' ? { conceptId: startOptions } : (startOptions || {})
      const payload = {
        ...(options.conceptId ? { concept_id: options.conceptId } : {}),
        ...(options.classId ? { class_id: options.classId } : {}),
        ...(options.regionId ? { region_id: options.regionId } : {}),
      }
      const result = await api('/api/dungeon/start', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const nextContent = result.dungeon?.editor_content || ''
      dungeonCodeRef.current = nextContent
      setDungeonCode(nextContent)
      setDungeonDirty(false)
      dungeonDirtyRef.current = false
      setActiveView('dungeon')
      await refreshCampaign({ silent: true })
      setNotice(`Dungeon run started on floor ${result.dungeon?.floor ?? 1}.`)
    } catch (error) {
      setNotice(`Dungeon start failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const requestPracticePrompt = async ({ concept, questionType, difficulty, answer, question = '' }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    const hasPracticeAnswer = typeof answer === 'string' && answer.trim()
    if (!(autoGrade && hasPracticeAnswer) && !provider) throw new Error('Set up OpenCode in Settings → AI Tutor, or launch a CLI in the PYR panel, then ask for practice help.')
    const sessionResult = await api('/api/practice/session', {
      method: 'POST',
      body: JSON.stringify({ concept, question_type: questionType, difficulty }),
    })
    const session = sessionResult.practice?.sessions?.at(-1) || sessionResult.result?.session || sessionResult.session
    const sessionId = session?.session_id
    if (!sessionId) throw new Error('Practice session could not be opened through the state gateway.')
    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const hasAnswer = typeof answer === 'string' && answer.trim()
    let submission = null
    if (hasAnswer) {
      const bound = await api('/api/pyr/practice-submission', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, answer }),
      })
      submission = bound.submission
      if (autoGrade) return judgeWithPyr('practice', submission, answer, question || `${questionType} question about ${concept}`)
    }
    const prompt = [
      'Quest Lab Tutor / Practice mode — provider teaching request.',
      `Provider: ${provider}`,
      `Concept: ${concept}`,
      `Question type: ${questionType}`,
      `Difficulty tier: ${difficulty}`,
      `Practice session: ${sessionId}`,
      submission ? `Submission ID: ${submission.submission_id}` : '',
      submission ? `Challenge nonce: ${submission.nonce}` : '',
      submission ? `Evidence ID: ${submission.evidence_id}` : '',
      submission ? `Answer digest: ${submission.answer_digest}` : '',
      hasAnswer ? 'Give feedback on the submitted practice answer below.' : 'Generate one self-contained practice question now.',
      hasAnswer ? 'If the answer is correct, incomplete or needs review, call POST /api/pyr/practice-verdict with the exact nonce, submission_id, answer_digest, verdict (correct, incorrect or reviewed), session_id, evidence_id and a concise reason. Never award XP, coins, HP, Resolve or Dungeon score.' : 'Tutor / Practice is unlimited and separate from Campaign and Dungeon. Do not issue a Battle verdict, award rewards, change HP, or reveal future Dungeon questions. Keep all examples and learner notes in tutor.py or the requested workspace notes file.',
      'Teach with one short explanation, then let the learner write the answer in tutor.py, then ask for a teach-back. Never reveal the answer, answer key or a project-specific missing snippet before the learner attempts it.',
      'If the learner is blocked, show one tiny generic example with unrelated names and values, explain only the next concept boundary, and ask for a new attempt. Do not patch blackjack.py, campaign.py or another required project file for them.',
      hasAnswer ? ['Player practice answer:', '```text', answer.trim(), '```'].join('\n') : '',
      '',
      'Use only this bounded current context for personalization:',
      `Quest projection: ${JSON.stringify(context.quest || {})}`,
      `Encounter projection: ${JSON.stringify(context.encounter || {})}`,
      `Active file: ${context.active_file?.path || '(none)'}`,
      '```text',
      context.active_file?.content || '(none)',
      '```',
      'Selected code:',
      '```text',
      context.selection?.text || '(none)',
      '```',
      'Recent shell output:',
      '```text',
      context.terminal?.tail || '(none)',
      '```',
      '',
    ].join('\n')
    pasteAiPrompt(prompt)
    setNotice(hasAnswer ? `Practice feedback sent to ${provider}.` : `Practice drill requested from ${provider}.`)
  }

  useEffect(() => {
    if (activeView !== 'dungeon' || !dungeon.active || !dungeonDirty || dungeonSaving || pyrThinking) return undefined
    const timer = window.setTimeout(() => {
      void saveDungeon()
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [activeView, dungeon.active, dungeon.run_id, dungeon.question?.id, dungeonCode, dungeonDirty, dungeonSaving, pyrThinking])

  // Let PYR write each new combat room's question once. Only while the room
  // buffer is empty, so a rewrite (which resets dungeon.py) never wipes work.
  const pyrWrittenRoomsRef = useRef(new Set())
  useEffect(() => {
    const question = dungeon.question
    if (!openCodeReady || aiTutor.settings?.generate_dungeon_questions === false || pyrThinking) return
    if (activeView !== 'dungeon' || !dungeon.active || !question?.id || !['encounter', 'elite', 'boss'].includes(dungeon.room_type)) return
    // dungeon.pyr_written survives restarts; dungeonDirty means the player is typing.
    if (dungeon.pyr_written || dungeonDirty || pyrWrittenRoomsRef.current.has(question.id) || String(dungeonCode || '').trim()) return
    pyrWrittenRoomsRef.current.add(question.id)
    withPyr('PYR is writing this room…', async () => {
      await api('/api/ai/dungeon-question', { method: 'POST', body: JSON.stringify({ run_id: dungeon.run_id }) })
      await refreshCampaign({ silent: true })
    }).catch((error) => setNotice(`PYR could not write this room (${error.message}); using the built-in question.`))
  }, [openCodeReady, aiTutor.settings?.generate_dungeon_questions, activeView, dungeon.active, dungeon.run_id, dungeon.room_type, dungeon.question?.id, dungeon.pyr_written, dungeonCode, dungeonDirty, pyrThinking])

  const formatCurrent = async () => {
    if (!activePath || editorMode === 'quest') return
    try {
      setBusy(true)
      const result = await api('/api/format', {
        method: 'POST',
        body: JSON.stringify({ path: activePath, content: codeRef.current }),
      })
      setEditorCode(result.content ?? codeRef.current)
      setDirty(false)
      setNotice(`Formatted ${activePath} with ${result.formatter}`)
    } catch (error) {
      setNotice(`Format failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const formatTutor = async () => {
    try {
      setBusy(true)
      const result = await api('/api/tutor/format', {
        method: 'POST',
        body: JSON.stringify({ path: 'tutor.py', content: tutorCode }),
      })
      setTutorCode(result.content ?? tutorCode)
      const disk = await api('/api/tutor')
      const revision = disk.revision ?? ''
      tutorDiskRevisionRef.current = revision
      tutorExternalChangeRef.current = null
      tutorDirtyRef.current = false
      setTutorDiskRevision(revision)
      setTutorExternalChange(null)
      setTutorDirty(false)
      setNotice(`Formatted tutor.py with ${result.formatter}`)
    } catch (error) {
      setNotice(`Tutor format failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const newFile = async () => {
    const dir = projectDirOf(activeEntryFileRef.current)
    const path = window.prompt(
      dir ? `New file path relative to the quest workspace, e.g. ${dir}/notes.md` : 'New file path relative to the quest workspace, e.g. scratch.py',
      dir ? `${dir}/` : '',
    )
    if (!path || path.endsWith('/')) return
    try {
      await api('/api/file', { method: 'PUT', body: JSON.stringify({ path, content: '' }) })
      await refreshFiles()
      await openFile(path, false)
    } catch (error) {
      setNotice(`Create failed: ${error.message}`)
    }
  }

  // Explorer New file / New folder. The server refuses an existing name, so
  // this can never overwrite work; a new file opens in the editor.
  const createWorkspaceEntry = async (path, type) => {
    try {
      await api('/api/workspace/new', { method: 'POST', body: JSON.stringify({ path, type }) })
      await refreshFiles()
      if (type === 'file') await openFile(path)
      setNotice(`Created ${path}${type === 'dir' ? '/' : ''}`)
      return { ok: true }
    } catch (error) {
      return { ok: false, error: error.message }
    }
  }

  // Explorer Delete: the server moves it to <workspace>/.questlab-trash/, so
  // it can be got back. A deleted open file leaves the editor empty.
  const deleteWorkspaceEntry = async (path) => {
    try {
      const result = await api('/api/workspace/delete', { method: 'POST', body: JSON.stringify({ path }) })
      if (activePath === path || activePath.startsWith(`${path}/`)) {
        setActivePath('')
        setEditorCode('')
        setDirty(false)
      }
      await refreshFiles()
      setNotice(`Deleted ${path} (kept in ${result.trash || '.questlab-trash'} in case you need it back).`)
      return { ok: true }
    } catch (error) {
      setNotice(`Delete failed: ${error.message}`)
      return { ok: false, error: error.message }
    }
  }

  const runCurrent = async () => {
    if (!activePath || editorMode === 'quest') return
    if (dirty && !(await saveFile())) return
    setActiveView('forge')
    // Run it the way the quests teach: from inside the file's own folder.
    // The terminal may already be in another folder (cd silver_reels), so
    // go there by absolute path instead of trusting the current one.
    shellTerminalRef.current?.send(`${runInFolderCommand(campaign?.workspace, activePath)}\n`)
    shellTerminalRef.current?.focus()
  }

  const runTutor = async () => {
    if (tutorDirty && !(await saveTutor())) return
    setActiveView('tutor')
    shellTerminalRef.current?.send(`${runInFolderCommand(campaign?.workspace, 'tutor.py')}\n`)
    shellTerminalRef.current?.focus()
  }

  const summon = (command) => {
    // Practice/Battle/Dungeon requests need to know which local provider the
    // learner explicitly launched. Keep this tab-scoped and opaque; the
    // provider still receives only the bounded context prompt below.
    try {
      sessionStorage.setItem('questlab.aiProvider', command)
    } catch {
      // A storage-blocked browser can still use the raw AI terminal.
    }
    aiTerminalRef.current?.send(`${command}\n`)
    aiTerminalRef.current?.focus()
    setNotice(`${command.toUpperCase()} launched. You can now ask for a bounded learning drill.`)
  }

  const purchaseCosmetic = async (itemId) => {
    try {
      setBusy(true)
      const result = await api('/api/homestead/purchase', {
        method: 'POST',
        body: JSON.stringify({ item_id: itemId }),
      })
      await refreshCampaign()
      setNotice(result.already_owned ? 'Already owned.' : `Homestead purchase complete. ${result.coins}c remain.`)
    } catch (error) {
      setNotice(`Purchase failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const equipCosmetic = async (itemId) => {
    try {
      setBusy(true)
      const result = await api('/api/homestead/equip', {
        method: 'POST',
        body: JSON.stringify({ item_id: itemId }),
      })
      await refreshCampaign()
      setNotice(`Equipped ${result.item?.name || itemId}.`)
    } catch (error) {
      setNotice(`Equip failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const purchaseMarketItem = async (itemId) => {
    try {
      setBusy(true)
      const result = await api('/api/campaign/market/purchase', {
        method: 'POST',
        body: JSON.stringify({ item_id: itemId }),
      })
      await refreshCampaign()
      setNotice(result.already_owned ? 'That lot is already in your kit.' : `${result.item?.name || itemId} added to Home. ${result.coins}c remain.`)
      return result
    } catch (error) {
      setNotice(`Market purchase failed: ${error.message}`)
      return null
    } finally {
      setBusy(false)
    }
  }

  const buildRoomUpgrade = async (upgradeId) => {
    try {
      setBusy(true)
      const result = await api('/api/homestead/room-upgrade', {
        method: 'POST',
        body: JSON.stringify({ upgrade_id: upgradeId }),
      })
      await refreshCampaign()
      const upgradeName = result.upgrade?.name || upgradeId
      setNotice(result.already_built ? `${upgradeName} is already built.` : `${upgradeName} built. The homestead is stronger.`)
    } catch (error) {
      setNotice(`Room upgrade failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const purchaseHomeRoom = async (roomId, expectedLevel) => {
    try {
      setBusy(true)
      const result = await api('/api/home/rooms/purchase', {
        method: 'POST',
        body: JSON.stringify({ room_id: roomId, expected_level: expectedLevel }),
      })
      let refreshed = await refreshCampaign()
      if (refreshed && Number(refreshed.revision) < Number(result.revision)) refreshed = await refreshCampaign()
      if (!refreshed) setCampaign((current) => current ? { ...current, progress: result.progress, home_rooms: result.home_rooms, revision: result.revision } : current)
      setNotice(`${result.step?.name || 'Room upgrade'} built.`)
      return result
    } catch (error) {
      setNotice(`Room upgrade failed: ${error.message}`)
      throw error
    } finally {
      setBusy(false)
    }
  }

  const performHomesteadAction = async (action) => {
    try {
      setBusy(true)
      const result = await api('/api/homestead/action', {
        method: 'POST',
        body: JSON.stringify({ action }),
      })
      await refreshCampaign()
      const event = result.event || {}
      if (event.pyr_form_after && event.pyr_form_after !== event.pyr_form_before) setNotice(`Pyr evolved into ${event.pyr_form_after}.`)
      else if (event.healed) setNotice(`Home action complete · +${event.healed} HP.`)
      else setNotice('Home action complete. The canonical state is saved.')
      return result
    } catch (error) {
      setNotice(`Home action failed: ${error.message}`)
      throw error
    } finally {
      setBusy(false)
    }
  }

  // Spend one free stat point on the hunter sheet.
  const spendStatPoint = async (stat) => {
    try {
      await api('/api/hunter/stat', { method: 'POST', body: JSON.stringify({ stat }) })
      await refreshCampaign({ silent: true })
    } catch (error) {
      setNotice(`Stat point not spent: ${error.message}`)
    }
  }

  const craftOil = async (oilId) => {
    try {
      await api('/api/hunter/craft', { method: 'POST', body: JSON.stringify({ oil_id: oilId }) })
      await refreshCampaign({ silent: true })
      setNotice('Oil crafted. Apply it in a fight against its beast.')
    } catch (error) {
      setNotice(`Oil not crafted: ${error.message}`)
    }
  }

  const hunterPost = async (url, body, failure) => {
    try {
      const result = await api(url, { method: 'POST', body: JSON.stringify(body) })
      await refreshCampaign({ silent: true })
      return result
    } catch (error) {
      setNotice(`${failure}: ${error.message}`)
      return null
    }
  }
  const armoryActions = {
    equip: (itemId) => hunterPost('/api/armory/equip', { item_id: itemId }, 'Could not equip that'),
    unequip: (slot) => hunterPost('/api/armory/unequip', { slot }, 'Could not take that off'),
    use: async (itemId) => {
      const result = await hunterPost('/api/armory/use', { item_id: itemId }, 'Could not use that')
      if (result) setNotice(result.armed ? `Armed: ${[result.armed.free_asks ? `${result.armed.free_asks} free PYR ask${result.armed.free_asks === 1 ? '' : 's'}` : '', result.armed.wards ? `${result.armed.wards} ward${result.armed.wards === 1 ? '' : 's'}` : ''].filter(Boolean).join(' and ')}. It waits until a fight needs it.` : result.healed ? `+${result.healed} HP.` : 'Your next battle is buffed.')
      return result
    },
    buy: async (itemId) => {
      const result = await hunterPost('/api/armory/buy', { item_id: itemId }, 'Purchase failed')
      if (result) setNotice('Bought. Find it in your Armory at Home.')
      return result
    },
  }
  const hunterActions = {
    craftOil,
    upgradeKit: async (track) => {
      const result = await hunterPost('/api/hunter/kit', { track }, 'Kit not upgraded')
      if (result) setNotice('Kit upgraded. It comes with you into every delve.')
      return result
    },
    identifyStart: () => hunterPost('/api/hunter/identify/start', {}, 'Could not read the vial'),
    identifyAnswer: (puzzleId, choice) => hunterPost('/api/hunter/identify/answer', { puzzle_id: puzzleId, choice }, 'Reading not checked'),
  }

  // Switch the active campaign project; the one left keeps its board.
  const selectCampaign = async (branch) => {
    try {
      const result = await api('/api/campaign/select', { method: 'POST', body: JSON.stringify({ branch }) })
      await refreshCampaign({ silent: true })
      if (result.changed !== false) setNotice(`Now playing ${result.project?.name || branch}.`)
      return result
    } catch (error) {
      setNotice(`Campaign switch failed: ${error.message}`)
      return null
    }
  }

  // Paper-doll appearance (equipment.avatar); cosmetic only.
  const setAvatar = async (update) => {
    try {
      await api('/api/avatar', { method: 'POST', body: JSON.stringify(update) })
      await refreshCampaign({ silent: true })
    } catch (error) {
      setNotice(`Appearance change failed: ${error.message}`)
    }
  }

  const equipCampaignItem = async (itemId) => {
    try {
      setBusy(true)
      const result = await api('/api/equipment/equip', {
        method: 'POST',
        body: JSON.stringify({ item_id: itemId }),
      })
      await refreshCampaign()
      setNotice(`Equipped ${result.item?.name || itemId}.`)
    } catch (error) {
      setNotice(`Campaign loadout failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const saveCodexNote = async (entryId, note, conceptId = entryId) => {
    try {
      setBusy(true)
      const canonicalResult = await api('/api/codex/note', {
        method: 'POST',
        body: JSON.stringify({ entry_id: entryId, note }),
      })
      // Keep the learner's durable Markdown notebook beside the project so it
      // can travel through the bounded workspace-transfer channel. The
      // canonical Codex event above remains the validated projection source.
      const safeConcept = String(conceptId || entryId)
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9._-]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 120) || 'concept'
      const existing = await api(`/api/notes/${encodeURIComponent(safeConcept)}`)
      const prior = existing.note?.content || ''
      const trimmed = note.trim()
      const priorEntries = prior.split(/\n\s*\n/).map((entry) => entry.trim()).filter(Boolean)
      const next = priorEntries.includes(trimmed)
        ? prior
        : prior
          ? `${prior.replace(/\s+$/g, '')}\n\n${trimmed}`
          : trimmed
      const noteResult = await api(`/api/notes/${encodeURIComponent(safeConcept)}`, {
        method: 'PUT',
        body: JSON.stringify({ content: next }),
      })
      await refreshCampaign({ silent: true })
      setNotice(canonicalResult.already_saved ? 'That note is already in the Codex; the workspace notebook is up to date.' : 'Codex note saved to the canonical record and workspace notebook.')
      return { ...canonicalResult, workspace_note: noteResult.note }
    } catch (error) {
      setNotice(`Codex note failed: ${error.message}`)
      throw error
    } finally {
      setBusy(false)
    }
  }

  const resetLayout = () => {
    setLeftWidth(300)
    setRightWidth(410)
    setTerminalHeight(245)
    setNotice('Forge panel layout reset.')
  }

  const dismissSplash = () => {
    if (splashClosing) return
    setSplashClosing(true)
    window.setTimeout(() => {
      setShowSplash(false)
      setSplashClosing(false)
    }, 320)
    try {
      window.localStorage.setItem('questlab.hasLaunched', '1')
      window.localStorage.setItem('questlab.lastSeenAt', String(Date.now()))
    } catch {
      // The overlay is still dismissible when storage is unavailable.
    }
  }

  const accountAction = async (action, successMessage) => {
    setAccountBusy(true)
    setAccountNotice('')
    try {
      await action()
      setAccountNotice(successMessage)
    } catch (error) {
      setAccountNotice(error.message)
      throw error
    } finally {
      setAccountBusy(false)
    }
  }

  const reloadExternalTutor = () => {
    const external = tutorExternalChangeRef.current
    if (!external) return
    tutorDiskRevisionRef.current = external.revision
    tutorDirtyRef.current = false
    tutorExternalChangeRef.current = null
    setTutorDiskRevision(external.revision)
    setTutorCode(external.content)
    setTutorDirty(false)
    setTutorExternalChange(null)
    setNotice('Reloaded external tutor.py; local edits were discarded.')
  }

  const keepTutorEdits = () => {
    if (!tutorExternalChangeRef.current) return
    tutorExternalChangeRef.current = null
    setTutorExternalChange(null)
    setNotice('Kept local tutor.py edits. Save when you are ready to overwrite the external version.')
  }

  const refreshWorkspaceTransfer = async () => {
    setWorkspaceTransferBusy(true)
    setWorkspaceTransferNotice('')
    try {
      const result = await api('/api/workspace-transfer')
      setWorkspaceTransfer(result)
      return result
    } catch (error) {
      setWorkspaceTransfer({ ok: false, error: error.message })
      setWorkspaceTransferNotice(error.message)
      return null
    } finally {
      setWorkspaceTransferBusy(false)
    }
  }

  const workspaceTransferAction = async (payload) => {
    setWorkspaceTransferBusy(true)
    setWorkspaceTransferNotice('')
    try {
      const result = await api('/api/workspace-transfer', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setWorkspaceTransfer(result)
      if (result.applied && payload.action === 'pull_apply') {
        await refreshFiles()
        if (!tutorDirtyRef.current) await refreshTutor()
        setWorkspaceTransferNotice('Incoming project files applied. Reopen or reload any open editor buffer before continuing.')
      } else if (payload.action === 'push') {
        setWorkspaceTransferNotice(result.applied ? 'Reviewed project files published to the transfer ref.' : 'The transfer ref is already current.')
      } else {
        setWorkspaceTransferNotice('Incoming files previewed. Nothing was written.')
      }
      return result
    } catch (error) {
      setWorkspaceTransferNotice(error.message)
      setWorkspaceTransfer((current) => ({ ...(current || {}), ok: false, error: error.message }))
      return null
    } finally {
      setWorkspaceTransferBusy(false)
    }
  }

  const pushWorkspaceFiles = () => {
    if (typeof window !== 'undefined' && !window.confirm('Send only blackjack.py, tutor.py, dungeon.py and notes/*.md to the reviewed transfer ref? progress.json and PTYs stay local.')) return
    return workspaceTransferAction({ action: 'push', confirmation: 'PUSH_WORKSPACE_FILES' })
  }

  const previewWorkspacePull = () => workspaceTransferAction({ action: 'pull_preview' })
  const applyWorkspacePull = (allowOverwrite = false) => {
    if (typeof window !== 'undefined' && !window.confirm(allowOverwrite ? 'Overwrite conflicting project files after creating a backup? Review the preview first.' : 'Apply the clean incoming project files now?')) return
    return workspaceTransferAction({ action: 'pull_apply', confirmation: 'PULL_WORKSPACE_FILES', allow_overwrite: allowOverwrite })
  }

  const signIn = ({ email, password }) => accountAction(() => syncEngine.signIn(email, password), 'Signed in. This device is registered.')
  const signUp = ({ email, password, displayName }) => accountAction(() => syncEngine.signUp(email, password, displayName), 'Account created. Check your email if confirmation is required.')
  const signOut = () => accountAction(() => syncEngine.signOut(), 'Signed out. Forge stays available locally.')
  const saveDeviceLabel = (label) => accountAction(() => syncEngine.setDeviceLabel(label), 'Device name saved.')
  const resolveCloudConflict = (choice) => accountAction(() => syncEngine.resolveConflict(choice), choice === 'cloud' ? 'Cloud campaign copy applied.' : 'This device campaign copy published.')

  // The encounter card can compact itself; it must not silently override the
  // learner's resize choice when Boss Gate is active.
  // A campaign battle brief needs room for the question and its code.
  const battleSidebar = activeView === 'forge' && Boolean(campaign?.encounter?.mob_name || campaign?.encounter?.status === 'boss_available')
  const effectiveLeftWidth = Math.max(battleSidebar ? 380 : 260, Number(leftWidth) || 300)
  // Keep the grid's separator column in compact mode so the editor remains
  // column-four even while the visible resize affordance is hidden.
  const leftPanelColumns = leftPanelCollapsed ? '76px 5px' : `${effectiveLeftWidth}px 5px`
  const gridStyle = zenMode
    ? {
        gridTemplateColumns: 'minmax(0, 1fr)',
        gridTemplateRows: `minmax(220px, 1fr) 5px ${terminalHeight}px`,
      }
    : wideSurface
    ? {
        gridTemplateColumns: 'minmax(0, 1fr)',
        gridTemplateRows: 'minmax(220px, 1fr)',
      }
    : dungeonSurface
      ? {
          gridTemplateColumns: 'minmax(0, 1fr)',
          gridTemplateRows: 'minmax(220px, 1fr)',
        }
      : {
        gridTemplateColumns: aiGridVisible
          ? `0px ${leftPanelColumns} minmax(420px, 1fr) 5px ${rightWidth}px`
          : `0px ${leftPanelColumns} minmax(420px, 1fr)`,
        gridTemplateRows: `minmax(220px, 1fr) 5px ${terminalHeight}px`,
      }
  const preferences = { editorFontSize, terminalFontSize, hudDensity, animations, showAiTerminal, themeChoice, fontFamily, zenMode, crtMode: gameMode }
  const setters = { setEditorFontSize, setTerminalFontSize, setHudDensity, setAnimations, setShowAiTerminal, setThemeChoice, setFontFamily, setZenMode, setCrtMode: setGameMode }
  const xpPercent = campaignReady ? clamp(((player.xp ?? 0) / Math.max(1, player.xp_next ?? 100)) * 100, 0, 100) : 0

  useEffect(() => {
    if (!campaignReady) return
    const currentLevel = player.level ?? 1
    // The first loaded save sets the baseline: opening the app is not a level up.
    if (prevLevelRef.current === null) {
      prevLevelRef.current = currentLevel
      return
    }
    if (currentLevel > prevLevelRef.current) {
      setLevelUp(true)
      playSound(880, 0.12)
      setTimeout(() => playSound(1320, 0.15), 120)
      spawnConfetti()
      setCelebration({ title: `Level ${currentLevel}!`, subtitle: 'You leveled up!' })
      setTimeout(() => setCelebration(null), 2500)
      setTimeout(() => setLevelUp(false), 600)
    }
    prevLevelRef.current = currentLevel
  }, [player.level, campaignReady])

  useEffect(() => {
    if (bossGateActive && !prevBossGateRef.current) {
      playSound(220, 0.3)
      setTimeout(() => playSound(165, 0.4), 300)
    }
    prevBossGateRef.current = bossGateActive
  }, [bossGateActive])
  const commands = runtime?.commands || {}

  return (
    <div
      className={`app-shell forge-v2 ${hubMode ? 'hub-mode' : ''} ${wideSurface ? 'wide-mode' : ''} ${['tutor', 'codex'].includes(activeView) ? 'resource-mode' : ''} ${dungeonSurface ? 'dungeon-mode' : ''} ${hudDensity === 'compact' ? 'hud-compact' : ''} ${animations ? '' : 'no-animations'} ${zenMode ? 'zen-mode' : ''} ${gameMode ? 'game-mode' : ''}`}
      data-theme={theme}
      data-font={fontFamily}
      data-cursor={equipped.cursor || 'cursor-basic'}
      data-hud={equipped.hud || 'hud-forge'}
      data-terminal={terminalSkin}
      data-view={activeView}
      data-boss-gate={bossGateActive ? 'true' : 'false'}
      data-campaign-revision={campaign?.revision ?? ''}
      data-frontend-build-sha={FRONTEND_BUILD_SHA || 'unmarked'}
      data-runtime-build-mismatch={runtimeBuildMismatch ? 'true' : 'false'}
    >
      {showSplash && (
        <div className={`launch-splash ${splashClosing ? 'is-closing' : ''}`} role="dialog" aria-modal="true" aria-label="Welcome to Python Quest Lab">
          <div className="launch-splash-mark" aria-hidden="true"><StatIcon name="flame" /></div>
          <span className="screen-kicker">PYTHON QUEST LAB</span>
          <h2>{initialLaunch.returning ? `Welcome back, ${welcomeName}` : 'Welcome to the Forge'}</h2>
          <p>{initialLaunch.returning ? 'Your campaign, notes and checkpoint are waiting. Resume exactly where you left off.' : 'Your campaign, notes and checkpoint are ready. The shell and AI sessions stay connected while this welcome screen is open.'}</p>
          <button className="primary" type="button" onClick={dismissSplash} disabled={splashClosing}>{splashClosing ? 'Opening…' : 'Enter Forge'}</button>
        </div>
      )}
      <RewardQueue items={rewardQueue} />
      {confetti.length > 0 && (
        <div className="confetti-layer" aria-hidden="true">
          {confetti.map((p) => (
            <span key={p.id} className="confetti-piece" style={{ left: `${p.left}%`, background: p.color, animationDelay: `${p.delay}s` }} />
          ))}
        </div>
      )}
      {showBossIntro && (
        <div className="boss-overlay" role="dialog" aria-modal="true" aria-label="Boss gate">
          <div className="boss-card">
            <span className="screen-kicker">BOSS GATE OPEN</span>
            <h2>⚔ {campaign?.encounter?.boss || 'The boss'} awaits</h2>
            <p>Every bounty on this board is cleared. This boss has its own gauntlet: coding phases you Submit run in the Forge, and questions about your own code you answer in the left sidebar. Watch its phases on the left.</p>
            <button className="primary" type="button" onClick={() => setBossIntroSeen(bossIntroKey)} autoFocus>Fight</button>
          </div>
        </div>
      )}
      {celebration && (
        <div className="celebration-overlay" role="dialog" aria-modal="true">
          <div className="celebration-card">
            <h2>{celebration.title}</h2>
            <p>{celebration.subtitle}</p>
          </div>
        </div>
      )}      <header className="topbar">
        <div className="brand-lockup">
          <div className="eyebrow">PYTHON QUEST LAB</div>
          <h1>Forge</h1>
        </div>
        <div className="hud-xp">
          <div><strong>{campaignReady ? `LV ${player.level ?? 1}` : 'SYNCING'}</strong><span>{campaignReady ? (player.title || 'Apprentice Coder') : 'Campaign state'}</span></div>
          <div className="hud-xp-track"><span className={levelUp ? 'level-up' : ''} style={{ width: `${xpPercent}%` }} /></div>
          <small>{campaignReady ? `${player.xp ?? 0}/${player.xp_next ?? 100} XP` : 'waiting for revision…'}</small>
        </div>
        <div className="top-stats">
          <span className="hp-stat" data-stat-label="HP" data-stat-tooltip={campaignReady ? `Health · ${player.hp ?? 100}/${player.max_hp ?? 100}` : 'Health · waiting for campaign'} title={campaignReady ? `HP · ${player.hp ?? 100}/${player.max_hp ?? 100}` : 'HP · waiting for campaign'} data-react-stat="true" data-campaign-stat="hp" data-campaign-stat-value={campaignReady ? (player.hp ?? 100) : '—'}><StatIcon name="heart" /><span data-stat-value>{campaignReady ? (player.hp ?? 100) : '—'}</span></span>
          <span data-stat-label="GOLD" data-stat-tooltip={campaignReady ? `Gold · ${player.coins ?? 0} coins available for validated purchases` : 'Gold · waiting for campaign'} title={campaignReady ? `Gold · ${player.coins ?? 0} coins` : 'Gold · waiting for campaign'} data-react-stat="true" data-campaign-stat="coins" data-campaign-stat-value={campaignReady ? (player.coins ?? 0) : '—'}><StatIcon name="coin" /><span data-stat-value>{campaignReady ? `${player.coins ?? 0}c` : '—'}</span></span>
          <span data-stat-label="STREAK" data-stat-tooltip={campaignReady ? `Learning streak · ${streak.current ?? 0} consecutive validated days` : 'Learning streak · waiting for campaign'} title={campaignReady ? `Learning streak · ${streak.current ?? 0} days` : 'Learning streak · waiting for campaign'} data-react-stat="true" data-campaign-stat="streak" data-campaign-stat-value={campaignReady ? (streak.current ?? 0) : '—'}><StatIcon name="flame" /><span data-stat-value>{campaignReady ? (streak.current ?? 0) : '—'}</span></span>
          <span className="optional-stat" data-stat-label="SHIELDS" data-stat-tooltip={campaignReady ? `Mastery shields · ${shields} earned protection charges` : 'Mastery shields · waiting for campaign'} title={campaignReady ? `Mastery shields · ${shields} earned` : 'Mastery shields · waiting for campaign'} data-react-stat="true" data-campaign-stat="shields" data-campaign-stat-value={campaignReady ? shields : '—'}><StatIcon name="shield" /><span data-stat-value>{campaignReady ? shields : '—'}</span></span>
          <span className="optional-stat" data-stat-label="BOSSES" data-stat-tooltip={campaignReady ? `Boss clears · ${stats.bosses_defeated ?? 0} validated victories` : 'Boss clears · waiting for campaign'} title={campaignReady ? `Boss clears · ${stats.bosses_defeated ?? 0}` : 'Boss clears · waiting for campaign'} data-react-stat="true" data-campaign-stat="bosses" data-campaign-stat-value={campaignReady ? (stats.bosses_defeated ?? 0) : '—'}><StatIcon name="sword" /><span data-stat-value>{campaignReady ? (stats.bosses_defeated ?? 0) : '—'}</span></span>
          <span className="optional-stat activity-stat" data-stat-label="ACTIVITY" data-stat-tooltip={campaignReady ? `Activity score · ${activity.activity_score ?? 0} validated learning actions` : 'Activity score · waiting for campaign'} title={campaignReady ? `Activity score · ${activity.activity_score ?? 0} validated actions` : 'Activity score · waiting for campaign'}>ACTIVITY {campaignReady ? (activity.activity_score ?? 0) : '—'}</span>
          <button
            type="button"
            className={`cloud-pill ${cloudState.error || cloudState.syncStatus === 'conflict' ? 'error' : cloudState.configured ? 'ready' : 'local'}`}
            title={`${cloudState.detail || ''} · open account settings`}
            onClick={() => setActiveView('settings')}
          >
            {cloudState.label}
          </button>
          {pyrThinking && <span className="pyr-thinking-pill" role="status">{pyrThinking}</span>}
          <span className="rank-stat">RANK {campaignReady ? (player.rank || 'F') : '—'}</span>
          {showAiTerminal && aiRouteHidden && (
            <button className="ai-popout-toggle" type="button" onClick={() => setAiPopoverOpen((open) => !open)} aria-expanded={aiPopoverOpen} aria-controls="questlab-ai-panel">
              {aiPopoverOpen ? 'Hide AI' : 'Open AI'}
            </button>
          )}
          {zenMode && (
            <button className="zen-toggle" type="button" onClick={() => setZenMode(false)} title="Leave Zen mode (Ctrl+Shift+Z)">
              Exit Zen
            </button>
          )}
          {/* Settings lives here, out of the destination nav. */}
          <button className={`hud-settings ${activeView === 'settings' ? 'active' : ''}`} type="button" onClick={() => setActiveView('settings')} title="Settings" aria-label="Settings" aria-current={activeView === 'settings' ? 'page' : undefined}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a8 8 0 0 0-1.7-1L14.5 3h-5l-.4 3a8 8 0 0 0-1.7 1L5 6 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5 5 18l2.4-1a8 8 0 0 0 1.7 1l.4 3h5l.4-3a8 8 0 0 0 1.7-1l2.4 1 2-3.5-2.1-1.5a7 7 0 0 0 .1-1z" /></svg>
          </button>
        </div>
      </header>

      <div className="quest-banner">
        <div><strong>{campaignReady ? (companion.name || 'PYR') : 'PYR'}</strong> · {campaignReady ? (companion.form || 'Tiny Code-Flame') : 'waiting for campaign'}</div>
        <div className="quest-text">{campaignReady ? questLine(progress) : 'Syncing campaign state…'}</div>
        <div className="git-pill">{campaignReady ? `${git.branch || 'no branch'} · ${git.dirty_count ?? 0} changes` : 'campaign unavailable'}</div>
      </div>

      <SurfaceNavigation activeView={activeView} onNavigate={setActiveView} />

      <main className="workspace-grid" style={gridStyle}>
        {!wideSurface && !dungeonSurface && !zenMode && <aside className={`left-panel panel ${leftPanelCollapsed ? 'left-panel-compact' : ''}`}>
          <ContextPanel
            activeView={activeView}
            campaign={campaign}
            files={files}
            activePath={activePath}
            compact={leftPanelCollapsed}
            onToggleCompact={() => setLeftPanelCollapsed((collapsed) => !collapsed)}
            editorMode={editorMode}
            openFile={openFile}
            openQuestDocument={openQuestDocument}
            newFile={newFile}
            onCreateEntry={createWorkspaceEntry}
            onDeleteEntry={deleteWorkspaceEntry}
            setActiveView={setActiveView}
            submitBattle={submitBattle}
            submitBoss={submitBoss}
            battleQuestions={battleQuestions}
            battleFeedback={battleFeedback}
            onAskBattleQuestion={askBattleQuestion}
            onAnswerBattleOption={answerBattleOption}
            onCheckSetup={checkSetupStep}
            onAskBossQuestion={askBossQuestion}
            onAnswerBossOption={answerBossOption}
            busy={busy || Boolean(pyrThinking)}
          />
        </aside>}

        {!wideSurface && !dungeonSurface && !leftPanelCollapsed && !zenMode && <div className="resize-handle vertical left-resizer" role="separator" aria-orientation="vertical" aria-label="Resize encounter panel" onPointerDown={(event) => startResize('left', event)} />}
        <section className={`editor-panel panel ${showEditor ? '' : 'surface-hidden'} ${tutorSurface ? 'tutor-editor-panel' : ''}`}>
            <div className="editor-toolbar">
              <div className="active-file">
                {tutorSurface ? (
                  <><span className="safe-badge">PYR WRITABLE</span> tutor.py{tutorDirty ? ' •' : ''}</>
                ) : questSurface ? (
                  <><span className="safe-badge">STATE VIEW</span> quest.md</>
                ) : (
                  <>{activePath || 'No file selected'}{dirty ? ' •' : ''}</>
                )}
              </div>
              <div className="toolbar-actions">
              {tutorSurface ? (
                <>
                  <button onClick={saveTutor} disabled={busy}>Save Tutor</button>
                  <button onClick={formatTutor} disabled={busy}>Pretty</button>
                  <button className="primary" onClick={runTutor} disabled={busy}>▶ Run Tutor</button>
                </>
              ) : questSurface ? (
                <>
                  <span className="editor-readonly-note">Read-only projection</span>
                </>
              ) : (
                <>
                  <button onClick={saveFile} disabled={!activePath || busy}>Save</button>
                  <button onClick={formatCurrent} disabled={!activePath || busy}>Pretty</button>
                  <button className="primary" onClick={runCurrent} disabled={!activePath || !activePath.endsWith('.py')}>▶ Run</button>
                </>
              )}
            </div>
          </div>
          {tutorSurface && (
            <div className="tutor-boundary-banner">
              <strong>Practice / Tutor workspace:</strong> choose a concept and question lens, then use tutor.py for your explanation and examples. Required project source remains yours.
            </div>
          )}
          {tutorSurface && (
            <TutorPracticeBar progress={progress} practiceProjection={campaign?.practice_projection} onPracticePrompt={requestPracticePrompt} busy={busy || Boolean(pyrThinking)} />
          )}
          {tutorSurface && tutorExternalChange && (
            <div className="tutor-conflict-banner" role="alert">
              <strong>External tutor.py change detected.</strong>
              <span>Your unsaved edits are preserved.</span>
              <button onClick={reloadExternalTutor}>Reload external version</button>
              <button onClick={keepTutorEdits}>Keep my edits</button>
            </div>
          )}
          <div className="editor-wrap">
            <Editor
              path={tutorSurface ? 'tutor.py' : questSurface ? 'quest.md' : (activePath || 'untitled.txt')}
              language={tutorSurface ? 'python' : questSurface ? 'markdown' : languageFor(activePath)}
              value={tutorSurface ? tutorCode : questSurface ? questDocument : code}
              onMount={(editor) => {
                editorSelectionSubscriptionRef.current?.dispose()
                const updateSelection = () => {
                  const selection = editor.getSelection()
                  const model = editor.getModel()
                  editorSelectionRef.current = selection && model ? model.getValueInRange(selection) : ''
                }
                updateSelection()
                editorSelectionSubscriptionRef.current = editor.onDidChangeCursorSelection(updateSelection)
              }}
              onChange={(value) => {
                if (tutorSurface) {
                  setTutorCode(value ?? '')
                  setTutorDirty(true)
                } else if (!questSurface) {
                  setEditorCode(value ?? '')
                  setDirty(true)
                }
              }}
              theme="vs-dark"
              options={{
                minimap: { enabled: false }, acceptSuggestionOnEnter: 'off',
                fontSize: editorFontSize,
                fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                lineHeight: Math.round(editorFontSize * 1.55),
                padding: { top: 14 },
                smoothScrolling: true,
                automaticLayout: true,
                tabSize: 4,
                readOnly: questSurface,
              }}
            />
          </div>
        </section>

        <div className={`resize-handle horizontal terminal-resizer ${showEditor ? '' : 'surface-hidden'}`} onPointerDown={(event) => startResize('terminal', event)} />

        <section className={`terminal-panel panel ${showEditor ? '' : 'surface-hidden'}`}>
          <div className="panel-title terminal-title-v2">
            <span>{tutorSurface ? 'TUTOR OUTPUT / TERMINAL' : 'TERMINAL'}</span>
            <div className="terminal-title-actions">
              <span className={`connection-pill ${shellState}`}>{shellState}</span>
              <button onClick={() => shellTerminalRef.current?.reconnect()}>↻</button>
            </div>
          </div>
          <TerminalPane
            ref={shellTerminalRef}
            role="shell"
            banner="Forge shell connected."
            fontSize={terminalFontSize}
            skin={terminalSkin}
            onStateChange={setShellState}
          />
        </section>

        {!showEditor && (
          <section className={`game-screen panel ${['tutor', 'codex'].includes(activeView) ? 'resource-game-screen' : ''}`}>
            <GameScreen
              activeView={activeView}
              progress={progress}
              revision={campaign?.revision ?? 0}
              avatarDataUrl={cloudState.avatar?.dataUrl || ''}
              codexProjection={campaign?.codex_projection}
              practiceProjection={campaign?.practice_projection}
              equipmentProjection={campaign?.equipment_projection}
              encounter={campaign?.encounter}
              dungeon={dungeon}
              dungeonEditorContent={dungeonCode}
              onDungeonEditorChange={(value) => {
                const nextContent = value ?? ''
                dungeonCodeRef.current = nextContent
                setDungeonCode(nextContent)
                setDungeonDirty(true)
                dungeonDirtyRef.current = true
              }}
              onSaveDungeon={saveDungeon}
              onDungeonRest={useDungeonRest}
              onDungeonCampAction={useDungeonCampAction}
              onDungeonRevealRisk={revealDungeonRisk}
              onDungeonEnterRisk={enterDungeonRisk}
              onDungeonMarketPurchase={buyDungeonItem}
              onDungeonEquip={equipDungeonItem}
              onDungeonApplyOil={applyDungeonOil}
              onDungeonTravel={travelDungeon}
              onDungeonAnswerOption={answerDungeonOption}
              hunterActions={hunterActions}
              armory={campaign?.armory || null}
              sparRoster={campaign?.spar_roster || []}
              sparActions={sparActions}
              armoryActions={armoryActions}
              campaignBoard={campaign?.campaign_board || null}
              onDungeonChoose={chooseDungeonRoom}
              onDungeonLeave={leaveDungeonRoom}
              onDungeonFinish={finishDungeonRun}
              onDungeonReset={resetDungeonRun}
              onStartDungeon={startDungeon}
              onPracticePrompt={requestPracticePrompt}
              dungeonSaving={dungeonSaving}
              submitBattle={submitBattle}
              submitBoss={submitBoss}
              submitDungeon={submitDungeon}
              purchaseCosmetic={purchaseCosmetic}
              purchaseMarketItem={purchaseMarketItem}
              equipCosmetic={equipCosmetic}
              equipCampaignItem={equipCampaignItem}
              buildRoomUpgrade={buildRoomUpgrade}
              homeRooms={campaign?.home_rooms}
              purchaseHomeRoom={purchaseHomeRoom}
              performHomesteadAction={performHomesteadAction}
              saveCodexNote={saveCodexNote}
              pyr={pyrTools}
              setAvatar={setAvatar}
              selectCampaign={selectCampaign}
              hunter={campaign?.hunter_projection}
              spendStatPoint={spendStatPoint}
              settingsAi={{ aiTutor, refreshAiTutor, saveAiSettings }}
              runtime={runtime}
              busy={busy || Boolean(pyrThinking)}
              preferences={preferences}
              setters={setters}
              resetLayout={resetLayout}
              account={cloudState}
              accountBusy={accountBusy}
              accountNotice={accountNotice}
              onSignIn={signIn}
              onSignUp={signUp}
              onSignOut={signOut}
              onDeviceLabelSave={saveDeviceLabel}
              onResolveConflict={resolveCloudConflict}
              workspaceTransfer={workspaceTransfer}
              workspaceTransferBusy={workspaceTransferBusy}
              workspaceTransferNotice={workspaceTransferNotice}
              onWorkspaceTransferRefresh={refreshWorkspaceTransfer}
              onWorkspaceTransferPush={pushWorkspaceFiles}
              onWorkspaceTransferPreviewPull={previewWorkspacePull}
               onWorkspaceTransferApplyPull={applyWorkspacePull}
               onNavigate={setActiveView}
               tutorCode={tutorCode}
               tutorDirty={tutorDirty}
               tutorExternalChange={tutorExternalChange}
               editorFontSize={editorFontSize}
               onTutorChange={(value) => {
                 setTutorCode(value ?? '')
                 setTutorDirty(true)
               }}
               onTutorSave={saveTutor}
               onTutorFormat={formatTutor}
               onTutorRun={runTutor}
               onTutorReloadExternal={reloadExternalTutor}
               onTutorKeepEdits={keepTutorEdits}
               campaignReady={campaignReady}
               showNavigation={false}
            />
          </section>
        )}

        {aiGridVisible && <div className="resize-handle vertical right-resizer" onPointerDown={(event) => startResize('right', event)} />}

        <aside id="questlab-ai-panel" className={`ai-panel panel ${aiGridVisible ? '' : aiPopoverOpen && showAiTerminal ? 'ai-popout' : 'ai-panel-parked'} ${aiVisible ? '' : 'surface-hidden'}`} aria-hidden={!aiVisible}>
          {builtInPyr && (
            <PyrChatPanel
              log={pyrLog}
              ready={openCodeReady}
              thinking={pyrThinking}
              model={aiTutor.settings?.model || 'Auto'}
              onOpenSettings={() => setActiveView('settings')}
              battleCost={campaign?.encounter?.mob_name ? { mob: campaign.encounter.mob_name, asks: campaign.encounter.pyr_assists || 0, scale: campaign.encounter.reward_scale ?? 100, free: campaign?.armory?.charges?.free_asks || 0 } : null}
              onAsk={(question) => {
                pushPyrLog({ role: 'you', text: question })
                pyrTools.ask({ question, concept: campaign?.encounter?.concept || campaign?.encounter?.mob?.concept || '', code: String(code || ''), battle: Boolean(campaign?.encounter?.mob_name) })
                  .then((reply) => pushPyrLog({ role: 'pyr', text: reply }))
                  .catch((error) => pushPyrLog({ role: 'pyr', text: `I couldn't answer that just now (${error.message}).` }))
              }}
            />
          )}
          <div className="ai-classic" hidden={builtInPyr}>
          <div className="ai-toolbar">
            <div>
              <span className="panel-title-inline">PYR / AI</span>
              <span className="ai-subtitle"> {companion.form || 'Tiny Code-Flame'}</span>
            </div>
            <div className="ai-actions">
              <button disabled={runtime && !commands.codex} onClick={() => summon('codex')} title={commands.codex === false ? 'Codex CLI not found' : 'Launch Codex'}>Codex</button>
              <button disabled={runtime && !commands.claude} onClick={() => summon('claude')} title={commands.claude === false ? 'Claude CLI not found' : 'Launch Claude'}>Claude</button>
              <button disabled={runtime && !commands.agy} onClick={() => summon('agy')} title={commands.agy === false ? 'AGY CLI not found' : 'Launch AGY'}>AGY</button>
              <button disabled={runtime && commands.copilot === false} onClick={() => summon('copilot')} title={commands.copilot === false ? 'GitHub Copilot CLI not found' : 'Launch GitHub Copilot CLI'}>Copilot</button>
              <button onClick={() => aiTerminalRef.current?.clear()}>Clear</button>
            </div>
          </div>
          <div className="ai-note ai-note-v2">
            <span>Raw CLI terminal · not sandboxed</span>
            <span className={`connection-pill ${aiState}`}>{aiState}</span>
            <button onClick={() => aiTerminalRef.current?.reconnect()}>Reconnect</button>
          </div>
          <TerminalPane
            ref={aiTerminalRef}
            role="ai"
            banner="PYR channel ready. Choose Codex, Claude, AGY, or Copilot above."
            fontSize={terminalFontSize}
            skin={terminalSkin}
            onStateChange={setAiState}
          />
          </div>
        </aside>
      </main>

      <footer className="statusbar">
        <span>{notice || `Runtime: ${runtime?.shell || 'checking shell…'}`}</span>
        <span className={`runtime-identity ${runtimeContractMissing || runtimeMismatch || runtimeStale || runtimeBuildMismatch ? 'warning' : ''}`} title={runtime?.repo_root || ''}>
          {runtimeContractMissing
            ? 'RUNTIME STALE · use current launcher'
            : runtimeBuildMismatch
              ? 'FRONTEND STALE · restart current launcher'
            : runtimeMismatch
            ? `CHECKOUT MISMATCH · ${runtimeBranch}`
            : runtimeStale
              ? `CHECKOUT STALE · ${runtimeBranch}`
              : `CHECKOUT ${runtimeBranch}`}
        </span>
        <span>
          {pyrThinking
            ? pyrThinking
            : busy
            ? 'working…'
          : tutorSurface
              ? 'tutor.py · Ctrl+S save · Ctrl+Enter run · Shift+Alt+F format'
              : questSurface
                ? 'quest.md · state-owned current quest · read-only'
              : activeView === 'dungeon'
                ? `dungeon.py · ${dungeonDirty ? 'checkpoint pending' : 'checkpoint saved'}`
              : activePath
                ? `${languageFor(activePath)} · Ctrl+S save · Shift+Alt+F format`
                : 'select a file'}
        </span>
      </footer>
    </div>
  )
}

export default AppV2
