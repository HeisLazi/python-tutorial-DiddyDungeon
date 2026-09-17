import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { ActivityRail, ContextPanel, GameScreen, RewardQueue, TutorPracticeBar } from './RpgViews'
import { syncEngine } from './cloud/syncEngine.js'
import { pyrClientId } from './cloud/pyrClient.js'

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
      if (parsed?.detail) message = parsed.detail
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
  const socketRef = useRef(null)
  const termRef = useRef(null)
  const fitRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const pendingRef = useRef([])
  const disposedRef = useRef(false)
  const [state, setState] = useState('connecting')

  const reportState = (next) => {
    setState(next)
    onStateChange?.(next)
  }

  const fitAndSync = () => {
    const term = termRef.current
    const fit = fitRef.current
    const socket = socketRef.current
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

  const connect = () => {
    if (disposedRef.current) return
    const current = socketRef.current
    if (current && (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)) return

    reportState('connecting')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/terminal/${role}`)
    socketRef.current = socket

    socket.onopen = () => {
      if (disposedRef.current) return
      reportState('connected')
      termRef.current?.writeln(`\r\n\x1b[38;5;214m${banner}\x1b[0m`)
      fitAndSync()
      while (pendingRef.current.length && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data: pendingRef.current.shift() }))
      }
    }

    socket.onmessage = (event) => termRef.current?.write(event.data)

    socket.onerror = () => {
      if (!disposedRef.current) reportState('error')
    }

    socket.onclose = () => {
      if (disposedRef.current) return
      reportState('reconnecting')
      termRef.current?.writeln('\r\n\x1b[38;5;203m[Quest Lab] Terminal link dropped. Reconnecting…\x1b[0m')
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = setTimeout(connect, 1200)
    }
  }

  useImperativeHandle(ref, () => ({
    send(text) {
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data: text }))
        return true
      }
      pendingRef.current.push(text)
      connect()
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
    reconnect() {
      const socket = socketRef.current
      if (socket && socket.readyState < WebSocket.CLOSING) socket.close()
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = setTimeout(connect, 80)
    },
    fit() {
      fitAndSync()
    },
  }))

  useEffect(() => {
    disposedRef.current = false
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

    const input = term.onData((data) => {
      const socket = socketRef.current
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const observer = new ResizeObserver(() => fitAndSync())
    observer.observe(hostRef.current)
    connect()

    return () => {
      disposedRef.current = true
      clearTimeout(reconnectTimerRef.current)
      observer.disconnect()
      input.dispose()
      const socket = socketRef.current
      if (socket && socket.readyState < WebSocket.CLOSING) socket.close()
      socketRef.current = null
      term.dispose()
      termRef.current = null
      fitRef.current = null
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
      const socket = socketRef.current
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
        <button className={`terminal-reconnect state-${state}`} onClick={connect} title="Reconnect terminal">
          {state === 'connecting' ? 'connecting…' : state === 'reconnecting' ? 'reconnecting…' : 'reconnect'}
        </button>
      )}
    </div>
  )
})

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
  const [code, setCode] = useState('')
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

  // Hub is the first-run/default destination. A previously selected route is
  // retained so a reload returns the learner to the screen they were using.
  const [storedActiveView, setStoredActiveView] = usePersistentState('questlab.activeView', 'hub')
  // Practice was an older navigation alias for the Tutor notebook. Keep old
  // localStorage/deep-link state usable, but persist the single Tutor route
  // so the rail can never grow a duplicate destination again.
  const activeView = storedActiveView === 'practice' ? 'tutor' : storedActiveView
  const setActiveView = (next) => setStoredActiveView((current) => {
    const candidate = typeof next === 'function' ? next(current) : next
    return candidate === 'practice' ? 'tutor' : candidate
  })
  const [leftWidth, setLeftWidth] = usePersistentState('questlab.leftWidth', 220)
  const [rightWidth, setRightWidth] = usePersistentState('questlab.rightWidth', 410)
  const [terminalHeight, setTerminalHeight] = usePersistentState('questlab.terminalHeight', 245)
  const [editorFontSize, setEditorFontSize] = usePersistentState('questlab.editorFontSize', 14)
  const [terminalFontSize, setTerminalFontSize] = usePersistentState('questlab.terminalFontSize', 13)
  const [hudDensity, setHudDensity] = usePersistentState('questlab.hudDensity', 'full')
  const [animations, setAnimations] = usePersistentState('questlab.animations', true)
  const [showAiTerminal, setShowAiTerminal] = usePersistentState('questlab.showAiTerminal', true)
  const [themeChoice, setThemeChoice] = usePersistentState('questlab.themeChoice', '')
  const [fontFamily, setFontFamily] = usePersistentState('questlab.fontFamily', 'inter')
  const [initialLaunch] = useState(() => launchContext())
  const [showSplash, setShowSplash] = useState(() => initialLaunch.show)
  const [splashClosing, setSplashClosing] = useState(false)
  const [aiPopoverOpen, setAiPopoverOpen] = useState(false)

  const progress = campaign?.progress || {}
  const player = progress.player || {}
  const stats = progress.stats || {}
  const streak = progress.streak || {}
  const companion = progress.companion || {}
  const activity = campaign?.activity || {}
  const git = campaign?.git || {}
  const homestead = progress.homestead || {}
  const dungeon = campaign?.dungeon || { active: false, status: 'idle', editor_content: '' }
  const equipped = homestead.equipped || {}
  const campaignReady = Boolean(campaign && campaign.progress && typeof campaign.progress === 'object')
  const theme = (themeChoice || equipped.theme || 'theme-ember-forge').replace('theme-', '')
  const terminalSkin = equipped.terminal || 'terminal-charcoal'
  const showEditor = activeView === 'forge' || activeView === 'tutor' || activeView === 'practice'
  const tutorSurface = activeView === 'tutor' || activeView === 'practice'
  const aiRouteHidden = ['hub', 'character', 'codex', 'quests', 'homestead', 'settings'].includes(activeView)
  const hubMode = activeView === 'hub'
  const wideSurface = ['hub', 'character', 'homestead'].includes(activeView)
  const aiGridVisible = showAiTerminal && !aiRouteHidden
  const aiVisible = showAiTerminal && (!aiRouteHidden || aiPopoverOpen)
  const welcomeName = cloudState.profile?.display_name || player.name || cloudState.user?.email?.split('@')?.[0] || 'Adventurer'
  const runtimeBranch = runtime?.repo_git?.branch || 'checking branch…'
  const runtimeMismatch = Boolean(runtime?.expected_branch && runtimeBranch !== runtime.expected_branch)
  const runtimeStale = Boolean(runtime?.repo_git?.behind_upstream > 0)
  const runtimeContractMissing = Boolean(
    runtime && (
      !runtime.expected_branch
      || !runtime.repo_git?.head_sha
      || !runtime.state_authority?.canonical_path
      || !runtime.state_authority?.legacy_path
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
      if (event.outcome === 'correct') {
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
          body: event.run_died ? `Score ${event.score ?? 0}` : event.mob_name ? `${event.mob_name} · −${Number(event.damage ?? 0)} HP` : `−${Number(event.damage ?? 0)} HP`,
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
    } else if (action === 'dungeon_record_death') {
      notifications.push({
        id: `${event.id}:dungeon-death`,
        kind: 'warning',
        title: 'DUNGEON RUN ENDED',
        body: `Floor ${event.floor ?? 0} · ${event.score ?? 0} score`,
        detail: 'Death resets the run; Campaign progress is unchanged',
      })
    } else if (action === 'practice_session_started') {
      notifications.push({
        id: `${event.id}:practice`,
        kind: 'objective',
        title: 'PRACTICE DRILL READY',
        body: `${event.concept || 'Concept'} · ${event.question_type || 'question'}`,
        detail: `Tier ${event.difficulty ?? 1} · no Campaign or Dungeon rewards`,
      })
    } else if (action === 'practice_record_attempt') {
      notifications.push({
        id: `${event.id}:practice-result`,
        kind: event.outcome === 'correct' ? 'reward' : 'objective',
        title: 'PRACTICE RESULT RECORDED',
        body: String(event.outcome || 'reviewed').toUpperCase(),
        detail: 'Learning history updated; game state unchanged',
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

  const refreshFiles = async () => {
    try {
      const result = await api('/api/tree')
      const nextFiles = result.items || []
      setFiles(nextFiles)
      // The tree also contains Quest Lab infrastructure. Never open an
      // arbitrary backend __init__.py as the learner's campaign surface;
      // prefer the active project's conventional file and otherwise leave
      // the editor empty until the transferred project source arrives.
      const projectFiles = nextFiles.filter((item) => {
        if (item.type !== 'file' || !item.path.endsWith('.py') || item.path === 'tutor.py') return false
        const normalized = item.path.replaceAll('\\\\', '/').toLowerCase()
        return !normalized.startsWith('ide/') && !normalized.startsWith('tools/') && !normalized.startsWith('tests/') && !normalized.includes('/test_') && !normalized.includes('/tests/')
      })
      const activeProjectFile = projectFiles.some((item) => item.path === activePath)
      if (!activeProjectFile) {
        const preferredNames = ['blackjack.py', 'campaign.py', 'main.py']
        const preferred = preferredNames.map((name) => projectFiles.find((item) => item.path.toLowerCase() === name)).find(Boolean) || projectFiles[0]
        if (preferred) await openFile(preferred.path, false)
        else {
          setActivePath('')
          setCode('')
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

  const submitBattle = async ({ objectiveId, answer }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!provider) throw new Error('Launch Codex, Claude, or AGY first, then submit the Battle answer.')
    if (typeof answer !== 'string' || !answer.trim()) throw new Error('Write an answer before entering Battle.')

    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const nonce = context?.verdict?.nonce
    if (!nonce) throw new Error('There is no active PYR encounter challenge. Capture context again.')
    const result = await api('/api/pyr/battle-submission', {
      method: 'POST',
      body: JSON.stringify({ nonce, objective_id: objectiveId, answer }),
    })
    const submission = result.submission
    const objective = (context.encounter?.available_objectives || []).find((item) => item.id === objectiveId) || {}
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
      'Player answer:',
      '```text',
      answer.trim(),
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

  const submitBoss = async ({ requirementId, answer }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!provider) throw new Error('Launch Codex, Claude, or AGY first, then submit the boss evidence.')
    if (typeof answer !== 'string' || !answer.trim()) throw new Error('Write evidence before entering the boss gate.')

    const context = await publishPyrContext({ terminalTail: shellTerminalRef.current?.getText?.() || '' })
    const nonce = context?.verdict?.nonce
    if (!nonce || context?.verdict?.challenge_type !== 'boss') throw new Error('There is no active boss challenge. Capture context again.')
    const result = await api('/api/pyr/boss-submission', {
      method: 'POST',
      body: JSON.stringify({ nonce, requirement_id: requirementId, answer }),
    })
    const submission = result.submission
    const prompt = [
      'Quest Lab boss gate — provider adjudication required.',
      `Provider: ${provider}`,
      `Campaign revision: ${submission.revision}`,
      `Project: ${submission.project_id}`,
      `Boss: ${submission.boss_name}`,
      `Requirement: ${submission.requirement_id}`,
      `Submission ID: ${submission.submission_id}`,
      `Challenge nonce: ${submission.nonce}`,
      `Evidence ID: ${submission.evidence_id}`,
      `Answer digest: ${submission.answer_digest}`,
      '',
      'Player evidence:',
      '```text',
      answer.trim(),
      '```',
      '',
      'Adjudicate only this submitted evidence against the current bounded context and project files. Do not reveal hidden future questions or answers. Call POST /api/pyr/boss-verdict with this exact nonce, submission_id, answer_digest, requirement_id and evidence_id, verdict=correct or incorrect, and a concise reason. Never supply rewards, Impact, HP or damage values. A project completes only after all three requirements are separately verified.',
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
    setNotice(`Boss ${requirementId.replaceAll('_', ' ')} sent to ${provider}; waiting for its validated verdict.`)
    return submission
  }

  const submitDungeon = async ({ runId, questionId, answer }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!provider) throw new Error('Launch Codex, Claude, or AGY first, then submit the Dungeon answer.')
    if (typeof answer !== 'string' || !answer.trim()) throw new Error('Write an answer in dungeon.py before submitting it.')

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

  // Track real use rather than treating a hot reload as an away period. The
  // splash is an interruption only on first launch or after twenty minutes
  // away; it never unmounts the editor or either PTY.
  useEffect(() => {
    if (storedActiveView === 'practice') setStoredActiveView('tutor')
  }, [storedActiveView, setStoredActiveView])

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
    const timer = window.setInterval(touch, 60_000)
    return () => {
      window.removeEventListener('pointerdown', onActivity)
      window.removeEventListener('keydown', onActivity)
      window.clearInterval(timer)
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
    return () => {
      delete window.__questlabPublishPyrContext
    }
  }, [])

  useEffect(() => () => {
    editorSelectionSubscriptionRef.current?.dispose()
    editorSelectionSubscriptionRef.current = null
  }, [])

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
        return
      }
      if (modifier && event.shiftKey && event.key === 'Enter') {
        // Submit has the same Monaco interception problem as Run. The
        // enhancement owns the bounded PYR context bridge, so trigger its
        // button from this capture-phase guard while the editor still has
        // focus; the fallback clipboard path remains in that handler.
        event.preventDefault()
        event.stopPropagation()
        document.querySelector('[data-qol-submit]')?.click()
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
  }, [activeView, leftWidth, rightWidth, terminalHeight])

  const startResize = (kind, event) => {
    event.preventDefault()
    const startX = event.clientX
    const startY = event.clientY
    const startLeft = leftWidth
    const startRight = rightWidth
    const startTerminal = terminalHeight

    const move = (moveEvent) => {
      if (kind === 'left') setLeftWidth(clamp(startLeft + moveEvent.clientX - startX, 170, 430))
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
      setActivePath(path)
      editorSelectionRef.current = ''
      setCode(result.content ?? '')
      setDirty(false)
      setNotice('')
    } catch (error) {
      setNotice(`Open failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  const saveFile = async () => {
    if (!activePath) return false
    try {
      setBusy(true)
      await api('/api/file', {
        method: 'PUT',
        body: JSON.stringify({ path: activePath, content: code }),
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

  const saveDungeon = async () => {
    if (!dungeon.active || !dungeon.run_id || dungeonSaving) return false
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
  const buyDungeonItem = (runId, itemId) => dungeonAction('/api/dungeon/market', { run_id: runId, item_id: itemId }, (result) => `Bought ${result.item?.name || itemId} for run currency.`)
  const equipDungeonItem = (runId, itemId) => dungeonAction('/api/dungeon/equip', { run_id: runId, item_id: itemId }, (result) => `${result.equipped || itemId} equipped.`)
  const chooseDungeonRoom = (runId, choiceId) => dungeonAction('/api/dungeon/choose', { run_id: runId, choice_id: choiceId }, (result) => {
    const kind = result.choice?.kind || result.dungeon?.room_type || 'room'
    return `${String(kind).replaceAll('_', ' ')} selected. The state service issued this room.`
  })
  const leaveDungeonRoom = (runId) => dungeonAction('/api/dungeon/leave', { run_id: runId }, () => 'Room cleared. Choose the next route on the map.')
  const finishDungeonRun = (runId) => dungeonAction('/api/dungeon/finish', { run_id: runId }, (result) => `Run banked at ${result.score ?? result.dungeon?.score ?? 0} score.`)

  const startDungeon = async (conceptId) => {
    try {
      setBusy(true)
      const payload = conceptId ? { concept_id: conceptId } : {}
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

  const requestPracticePrompt = async ({ concept, questionType, difficulty, answer }) => {
    const provider = sessionStorage.getItem('questlab.aiProvider')
    if (!provider) throw new Error('Launch Codex, Claude, or AGY first, then ask for practice help.')
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
    if (activeView !== 'dungeon' || !dungeon.active || !dungeonDirty || dungeonSaving) return undefined
    const timer = window.setTimeout(() => {
      void saveDungeon()
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [activeView, dungeon.active, dungeon.run_id, dungeon.question?.id, dungeonCode, dungeonDirty, dungeonSaving])

  const formatCurrent = async () => {
    if (!activePath) return
    try {
      setBusy(true)
      const result = await api('/api/format', {
        method: 'POST',
        body: JSON.stringify({ path: activePath, content: code }),
      })
      setCode(result.content ?? code)
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
    const path = window.prompt('New file path relative to the quest workspace, e.g. scratch.py')
    if (!path) return
    try {
      await api('/api/file', { method: 'PUT', body: JSON.stringify({ path, content: '' }) })
      await refreshFiles()
      await openFile(path, false)
    } catch (error) {
      setNotice(`Create failed: ${error.message}`)
    }
  }

  const runCurrent = async () => {
    if (!activePath) return
    if (dirty && !(await saveFile())) return
    setActiveView('forge')
    shellTerminalRef.current?.send(`python3 ${JSON.stringify(activePath)}\n`)
    shellTerminalRef.current?.focus()
  }

  const runTutor = async () => {
    if (tutorDirty && !(await saveTutor())) return
    setActiveView('tutor')
    shellTerminalRef.current?.send('python3 tutor.py\n')
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
    setLeftWidth(220)
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

  const signIn = ({ email, password }) => accountAction(() => syncEngine.signIn(email, password), 'Signed in. This device is registered.')
  const signUp = ({ email, password, displayName }) => accountAction(() => syncEngine.signUp(email, password, displayName), 'Account created. Check your email if confirmation is required.')
  const signOut = () => accountAction(() => syncEngine.signOut(), 'Signed out. Forge stays available locally.')
  const saveDeviceLabel = (label) => accountAction(() => syncEngine.setDeviceLabel(label), 'Device name saved.')
  const resolveCloudConflict = (choice) => accountAction(() => syncEngine.resolveConflict(choice), choice === 'cloud' ? 'Cloud campaign copy applied.' : 'This device campaign copy published.')

  const gridStyle = wideSurface
    ? {
        gridTemplateColumns: 'minmax(0, 1fr)',
        gridTemplateRows: 'minmax(220px, 1fr)',
      }
    : {
        gridTemplateColumns: aiGridVisible
          ? `48px ${leftWidth}px 5px minmax(420px, 1fr) 5px ${rightWidth}px`
          : `48px ${leftWidth}px 5px minmax(420px, 1fr)`,
        gridTemplateRows: `minmax(220px, 1fr) 5px ${terminalHeight}px`,
      }
  const preferences = { editorFontSize, terminalFontSize, hudDensity, animations, showAiTerminal, themeChoice, fontFamily }
  const setters = { setEditorFontSize, setTerminalFontSize, setHudDensity, setAnimations, setShowAiTerminal, setThemeChoice, setFontFamily }
  const xpPercent = campaignReady ? clamp(((player.xp ?? 0) / Math.max(1, player.xp_next ?? 100)) * 100, 0, 100) : 0
  const commands = runtime?.commands || {}

  return (
    <div
      className={`app-shell forge-v2 ${hubMode ? 'hub-mode' : ''} ${wideSurface ? 'wide-mode' : ''} ${hudDensity === 'compact' ? 'hud-compact' : ''} ${animations ? '' : 'no-animations'}`}
      data-theme={theme}
      data-font={fontFamily}
      data-cursor={equipped.cursor || 'cursor-basic'}
      data-hud={equipped.hud || 'hud-forge'}
      data-terminal={terminalSkin}
      data-view={activeView}
      data-campaign-revision={campaign?.revision ?? ''}
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
      <header className="topbar">
        <div className="brand-lockup">
          <div className="eyebrow">PYTHON QUEST LAB</div>
          <h1>Forge</h1>
        </div>
        <div className="hud-xp">
          <div><strong>{campaignReady ? `LV ${player.level ?? 1}` : 'SYNCING'}</strong><span>{campaignReady ? (player.title || 'Apprentice Coder') : 'Campaign state'}</span></div>
          <div className="hud-xp-track"><span style={{ width: `${xpPercent}%` }} /></div>
          <small>{campaignReady ? `${player.xp ?? 0}/${player.xp_next ?? 100} XP` : 'waiting for revision…'}</small>
        </div>
        <div className="top-stats">
          <span className="hp-stat" data-react-stat="true" data-campaign-stat="hp" data-campaign-stat-value={campaignReady ? (player.hp ?? 100) : '—'}><StatIcon name="heart" /><span data-stat-value>{campaignReady ? (player.hp ?? 100) : '—'}</span></span>
          <span data-react-stat="true" data-campaign-stat="coins" data-campaign-stat-value={campaignReady ? (player.coins ?? 0) : '—'}><StatIcon name="coin" /><span data-stat-value>{campaignReady ? `${player.coins ?? 0}c` : '—'}</span></span>
          <span data-react-stat="true" data-campaign-stat="streak" data-campaign-stat-value={campaignReady ? (streak.current ?? 0) : '—'}><StatIcon name="flame" /><span data-stat-value>{campaignReady ? (streak.current ?? 0) : '—'}</span></span>
          <span className="optional-stat" data-react-stat="true" data-campaign-stat="shields" data-campaign-stat-value={campaignReady ? shields : '—'}><StatIcon name="shield" /><span data-stat-value>{campaignReady ? shields : '—'}</span></span>
          <span className="optional-stat" data-react-stat="true" data-campaign-stat="bosses" data-campaign-stat-value={campaignReady ? (stats.bosses_defeated ?? 0) : '—'}><StatIcon name="sword" /><span data-stat-value>{campaignReady ? (stats.bosses_defeated ?? 0) : '—'}</span></span>
          <span className="optional-stat">DEV {campaignReady ? (activity.activity_score ?? 0) : '—'}</span>
          <span
            className={`cloud-pill ${cloudState.error || cloudState.syncStatus === 'conflict' ? 'error' : cloudState.configured ? 'ready' : 'local'}`}
            title={cloudState.detail}
          >
            {cloudState.label}
          </span>
          <span className="rank-stat">RANK {campaignReady ? (player.rank || 'F') : '—'}</span>
          {showAiTerminal && aiRouteHidden && (
            <button className="ai-popout-toggle" type="button" onClick={() => setAiPopoverOpen((open) => !open)} aria-expanded={aiPopoverOpen} aria-controls="questlab-ai-panel">
              {aiPopoverOpen ? 'Hide AI' : 'Open AI'}
            </button>
          )}
        </div>
      </header>

      <div className="quest-banner">
        <div><strong>{campaignReady ? (companion.name || 'PYR') : 'PYR'}</strong> · {campaignReady ? (companion.form || 'Tiny Code-Flame') : 'waiting for campaign'}</div>
        <div className="quest-text">{campaignReady ? (progress.current_quest || 'Choose a quest.') : 'Syncing campaign state…'}</div>
        <div className="git-pill">{campaignReady ? `${git.branch || 'no branch'} · ${git.dirty_count ?? 0} changes` : 'campaign unavailable'}</div>
      </div>

      <main className="workspace-grid" style={gridStyle}>
        {!wideSurface && <ActivityRail activeView={activeView} setActiveView={setActiveView} player={player} campaignReady={campaignReady} />}

        {!wideSurface && <aside className="left-panel panel">
          <ContextPanel
            activeView={activeView}
            campaign={campaign}
            files={files}
            activePath={activePath}
            openFile={openFile}
            newFile={newFile}
            setActiveView={setActiveView}
            submitBattle={submitBattle}
            busy={busy}
          />
        </aside>}

        {!wideSurface && <div className="resize-handle vertical left-resizer" onPointerDown={(event) => startResize('left', event)} />}

        <section className={`editor-panel panel ${showEditor ? '' : 'surface-hidden'} ${tutorSurface ? 'tutor-editor-panel' : ''}`}>
          <div className="editor-toolbar">
            <div className="active-file">
              {tutorSurface ? (
                <><span className="safe-badge">PYR WRITABLE</span> tutor.py{tutorDirty ? ' •' : ''}</>
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
            <TutorPracticeBar progress={progress} practiceProjection={campaign?.practice_projection} onPracticePrompt={requestPracticePrompt} busy={busy} />
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
              path={tutorSurface ? 'tutor.py' : (activePath || 'untitled.txt')}
              language={tutorSurface ? 'python' : languageFor(activePath)}
              value={tutorSurface ? tutorCode : code}
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
                } else {
                  setCode(value ?? '')
                  setDirty(true)
                }
              }}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: editorFontSize,
                fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                lineHeight: Math.round(editorFontSize * 1.55),
                padding: { top: 14 },
                smoothScrolling: true,
                automaticLayout: true,
                tabSize: 4,
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
          <section className="game-screen panel">
            <GameScreen
              activeView={activeView}
              progress={progress}
              revision={campaign?.revision ?? 0}
              codexProjection={campaign?.codex_projection}
              practiceProjection={campaign?.practice_projection}
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
              onDungeonMarketPurchase={buyDungeonItem}
              onDungeonEquip={equipDungeonItem}
              onDungeonChoose={chooseDungeonRoom}
              onDungeonLeave={leaveDungeonRoom}
              onDungeonFinish={finishDungeonRun}
              onStartDungeon={startDungeon}
              onPracticePrompt={requestPracticePrompt}
              dungeonSaving={dungeonSaving}
              submitBattle={submitBattle}
              submitBoss={submitBoss}
              submitDungeon={submitDungeon}
              purchaseCosmetic={purchaseCosmetic}
              equipCosmetic={equipCosmetic}
              saveCodexNote={saveCodexNote}
              busy={busy}
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
              onNavigate={setActiveView}
              campaignReady={campaignReady}
            />
          </section>
        )}

        {aiGridVisible && <div className="resize-handle vertical right-resizer" onPointerDown={(event) => startResize('right', event)} />}

        <aside id="questlab-ai-panel" className={`ai-panel panel ${aiGridVisible ? '' : aiPopoverOpen && showAiTerminal ? 'ai-popout' : 'ai-panel-parked'} ${aiVisible ? '' : 'surface-hidden'}`} aria-hidden={!aiVisible}>
          <div className="ai-toolbar">
            <div>
              <span className="panel-title-inline">PYR / AI</span>
              <span className="ai-subtitle"> {companion.form || 'Tiny Code-Flame'}</span>
            </div>
            <div className="ai-actions">
              <button disabled={runtime && !commands.codex} onClick={() => summon('codex')} title={commands.codex === false ? 'Codex CLI not found' : 'Launch Codex'}>Codex</button>
              <button disabled={runtime && !commands.claude} onClick={() => summon('claude')} title={commands.claude === false ? 'Claude CLI not found' : 'Launch Claude'}>Claude</button>
              <button disabled={runtime && !commands.agy} onClick={() => summon('agy')} title={commands.agy === false ? 'AGY CLI not found' : 'Launch AGY'}>AGY</button>
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
            banner="PYR channel ready. Choose Codex, Claude, or AGY above."
            fontSize={terminalFontSize}
            skin={terminalSkin}
            onStateChange={setAiState}
          />
        </aside>
      </main>

      <footer className="statusbar">
        <span>{notice || `Runtime: ${runtime?.shell || 'checking shell…'}`}</span>
        <span className={`runtime-identity ${runtimeContractMissing || runtimeMismatch || runtimeStale ? 'warning' : ''}`} title={runtime?.repo_root || ''}>
          {runtimeContractMissing
            ? 'RUNTIME STALE · use current launcher'
            : runtimeMismatch
            ? `CHECKOUT MISMATCH · ${runtimeBranch}`
            : runtimeStale
              ? `CHECKOUT STALE · ${runtimeBranch}`
              : `CHECKOUT ${runtimeBranch}`}
        </span>
        <span>
          {busy
            ? 'working…'
            : tutorSurface
              ? 'tutor.py · Ctrl+S save · Ctrl+Enter run · Shift+Alt+F format'
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
