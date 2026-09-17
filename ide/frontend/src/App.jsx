import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { ActivityRail, ContextPanel, GameScreen } from './RpgViews'

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
      // Keep raw response text when it is not JSON.
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

const LEGACY_STAT_PATHS = {
  heart: '<path d="M20 8c0 5-8 11-8 11S4 13 4 8a4 4 0 0 1 7-3 4 4 0 0 1 7 0 4 4 0 0 1 2 3z"/>',
  coin: '<circle cx="12" cy="12" r="8"/><path d="M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5M12 6v12"/>',
  flame: '<path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z"/>',
  shield: '<path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z"/>',
  sword: '<path d="m14 4 6-1-1 6-9 9-4-4zM6 14l-3 3 4 4 3-3"/>',
}

function LegacyStatIcon({ name }) {
  return (
    <span className="quest-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" dangerouslySetInnerHTML={{ __html: LEGACY_STAT_PATHS[name] || LEGACY_STAT_PATHS.heart }} />
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
      // Local preferences should never break the IDE.
    }
  }, [key, value])

  return [value, setValue]
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
  { banner = 'Quest terminal connected.', fontSize = 13, skin = 'terminal-charcoal' },
  ref,
) {
  const hostRef = useRef(null)
  const socketRef = useRef(null)
  const termRef = useRef(null)

  const sendPacket = (packet) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(packet))
      return true
    }
    return false
  }

  useImperativeHandle(ref, () => ({
    send(text) {
      sendPacket({ type: 'input', data: text })
    },
    focus() {
      termRef.current?.focus()
    },
    clear() {
      termRef.current?.clear()
    },
  }))

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      convertEol: false,
      scrollback: 5000,
      fontFamily: 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace',
      fontSize,
      theme: terminalPalette(skin),
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(hostRef.current)
    fit.fit()
    termRef.current = term

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`)
    socketRef.current = socket

    const syncSize = () => {
      fit.fit()
      if (socket.readyState === WebSocket.OPEN && term.cols > 0 && term.rows > 0) {
        socket.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
      }
    }

    socket.onopen = () => {
      term.writeln(`\r\n\x1b[38;5;214m${banner}\x1b[0m`)
      syncSize()
    }
    socket.onmessage = (event) => term.write(event.data)
    socket.onclose = () => term.writeln('\r\n\x1b[31mTerminal disconnected. Restart Quest Lab to reconnect.\x1b[0m')
    socket.onerror = () => term.writeln('\r\n\x1b[31mTerminal connection error.\x1b[0m')

    const disposable = term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'input', data }))
      }
    })

    const observer = new ResizeObserver(() => syncSize())
    observer.observe(hostRef.current)

    return () => {
      observer.disconnect()
      disposable.dispose()
      socket.close()
      term.dispose()
    }
  }, [banner, fontSize, skin])

  return <div className="terminal-host" ref={hostRef} />
})

function App() {
  const shellTerminalRef = useRef(null)
  const aiTerminalRef = useRef(null)
  const [campaign, setCampaign] = useState(null)
  const [files, setFiles] = useState([])
  const [activePath, setActivePath] = useState('')
  const [code, setCode] = useState('')
  const [dirty, setDirty] = useState(false)
  const [tutorCode, setTutorCode] = useState('')
  const [tutorDirty, setTutorDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

  const [storedActiveView, setStoredActiveView] = usePersistentState('questlab.activeView', 'forge')
  const normalizeView = (value) => value === 'practice' ? 'tutor' : value === 'quests' ? 'codex' : value
  const activeView = normalizeView(storedActiveView)
  const setActiveView = (next) => setStoredActiveView((current) => normalizeView(typeof next === 'function' ? next(current) : next))
  const [leftWidth, setLeftWidth] = usePersistentState('questlab.leftWidth', 220)
  const [rightWidth, setRightWidth] = usePersistentState('questlab.rightWidth', 390)
  const [terminalHeight, setTerminalHeight] = usePersistentState('questlab.terminalHeight', 245)
  const [editorFontSize, setEditorFontSize] = usePersistentState('questlab.editorFontSize', 14)
  const [terminalFontSize, setTerminalFontSize] = usePersistentState('questlab.terminalFontSize', 13)
  const [hudDensity, setHudDensity] = usePersistentState('questlab.hudDensity', 'full')
  const [animations, setAnimations] = usePersistentState('questlab.animations', true)

  const progress = campaign?.progress || {}
  const player = progress.player || {}
  const stats = progress.stats || {}
  const streak = progress.streak || {}
  const companion = progress.companion || {}
  const activity = campaign?.activity || {}
  const git = campaign?.git || {}
  const homestead = progress.homestead || {}
  const equipped = homestead.equipped || {}
  const theme = (equipped.theme || 'theme-ember-forge').replace('theme-', '')
  const terminalSkin = equipped.terminal || 'terminal-charcoal'
  const campaignReady = Boolean(campaign && campaign.progress && typeof campaign.progress === 'object')

  const shields = useMemo(
    () => (progress.skills || []).filter((skill) => skill.shield?.tier && skill.shield.tier !== 'none').length,
    [progress.skills],
  )

  const refreshCampaign = async () => {
    try {
      setCampaign(await api('/api/campaign'))
    } catch (error) {
      setNotice(`Campaign load failed: ${error.message}`)
    }
  }

  const refreshFiles = async () => {
    try {
      const result = await api('/api/tree')
      setFiles(result.items || [])
      if (!activePath) {
        const preferred = (result.items || []).find((item) => item.type === 'file' && item.path.endsWith('.py') && item.path !== 'tutor.py')
        if (preferred) openFile(preferred.path)
      }
    } catch (error) {
      setNotice(`File tree failed: ${error.message}`)
    }
  }

  const refreshTutor = async () => {
    try {
      const result = await api('/api/tutor')
      setTutorCode(result.content ?? '')
      setTutorDirty(false)
    } catch (error) {
      setNotice(`Tutor notebook failed: ${error.message}`)
    }
  }

  useEffect(() => {
    refreshCampaign()
    refreshFiles()
    refreshTutor()
  }, [])

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        if (activeView === 'tutor') saveTutor()
        else if (activeView === 'forge') saveFile()
      }
      if (event.shiftKey && event.altKey && event.key.toLowerCase() === 'f') {
        event.preventDefault()
        if (activeView === 'tutor') formatTutor()
        else if (activeView === 'forge') formatCurrent()
      }
      if ((event.ctrlKey || event.metaKey) && event.key === '`') {
        event.preventDefault()
        setActiveView('forge')
        shellTerminalRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const startResize = (kind, event) => {
    event.preventDefault()
    const startX = event.clientX
    const startY = event.clientY
    const startLeft = leftWidth
    const startRight = rightWidth
    const startTerminal = terminalHeight

    const move = (moveEvent) => {
      if (kind === 'left') setLeftWidth(clamp(startLeft + (moveEvent.clientX - startX), 170, 420))
      if (kind === 'right') setRightWidth(clamp(startRight - (moveEvent.clientX - startX), 290, 760))
      if (kind === 'terminal') setTerminalHeight(clamp(startTerminal - (moveEvent.clientY - startY), 140, 560))
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

  const openFile = async (path) => {
    if (dirty && path !== activePath && !window.confirm('Discard unsaved changes?')) return
    try {
      setBusy(true)
      const result = await api(`/api/file?path=${encodeURIComponent(path)}`)
      setActivePath(path)
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
      await api('/api/tutor', {
        method: 'PUT',
        body: JSON.stringify({ content: tutorCode }),
      })
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
      refreshCampaign()
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
      await openFile(path)
    } catch (error) {
      setNotice(`Create failed: ${error.message}`)
    }
  }

  const runCurrent = async () => {
    if (!activePath) return
    if (dirty) {
      const ok = await saveFile()
      if (!ok) return
    }
    setActiveView('forge')
    shellTerminalRef.current?.send(`python3 ${JSON.stringify(activePath)}\n`)
    shellTerminalRef.current?.focus()
  }

  const runTutor = async () => {
    if (tutorDirty) {
      const ok = await saveTutor()
      if (!ok) return
    }
    shellTerminalRef.current?.send('python3 tutor.py\n')
    shellTerminalRef.current?.focus()
  }

  const summon = (command) => {
    try {
      sessionStorage.setItem('questlab.aiProvider', command)
    } catch {
      // A storage-blocked browser can still use the raw AI terminal.
    }
    aiTerminalRef.current?.send(`${command}\n`)
    aiTerminalRef.current?.focus()
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

  const resetLayout = () => {
    setLeftWidth(220)
    setRightWidth(390)
    setTerminalHeight(245)
    setNotice('Forge panel layout reset.')
  }

  const gridStyle = {
    gridTemplateColumns: `48px ${leftWidth}px 5px minmax(420px, 1fr) 5px ${rightWidth}px`,
    gridTemplateRows: `minmax(220px, 1fr) 5px ${terminalHeight}px`,
  }

  const preferences = { editorFontSize, terminalFontSize, hudDensity, animations }
  const setters = { setEditorFontSize, setTerminalFontSize, setHudDensity, setAnimations }
  const xpPercent = campaignReady ? clamp(((player.xp ?? 0) / Math.max(1, player.xp_next ?? 100)) * 100, 0, 100) : 0
  const showEditor = activeView === 'forge' || activeView === 'tutor'

  return (
    <div
      className={`app-shell ${hudDensity === 'compact' ? 'hud-compact' : ''} ${animations ? '' : 'no-animations'}`}
      data-theme={theme}
      data-cursor={equipped.cursor || 'cursor-basic'}
      data-hud={equipped.hud || 'hud-forge'}
      data-terminal={terminalSkin}
    >
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
          <span className="hp-stat" data-react-stat="true" data-campaign-stat="hp"><LegacyStatIcon name="heart" /><span data-stat-value>{campaignReady ? (player.hp ?? 100) : '—'}</span></span>
          <span data-react-stat="true" data-campaign-stat="coins"><LegacyStatIcon name="coin" /><span data-stat-value>{campaignReady ? (player.coins ?? 0) : '—'}{campaignReady ? 'c' : ''}</span></span>
          <span data-react-stat="true" data-campaign-stat="streak"><LegacyStatIcon name="flame" /><span data-stat-value>{campaignReady ? (streak.current ?? 0) : '—'}</span></span>
          <span className="optional-stat" data-react-stat="true" data-campaign-stat="shields"><LegacyStatIcon name="shield" /><span data-stat-value>{campaignReady ? shields : '—'}</span></span>
          <span className="optional-stat" data-react-stat="true" data-campaign-stat="bosses"><LegacyStatIcon name="sword" /><span data-stat-value>{campaignReady ? (stats.bosses_defeated ?? 0) : '—'}</span></span>
          <span className="optional-stat">DEV {campaignReady ? (activity.activity_score ?? 0) : '—'}</span>
          <span className="rank-stat">RANK {campaignReady ? (player.rank || 'F') : '—'}</span>
        </div>
      </header>

      <div className="quest-banner">
        <div><strong>{campaignReady ? (companion.name || 'PYR') : 'PYR'}</strong> · {campaignReady ? (companion.form || 'Tiny Code-Flame') : 'waiting for campaign'}</div>
        <div className="quest-text">{campaignReady ? (progress.current_quest || 'Choose a quest.') : 'Syncing campaign state…'}</div>
        <div className="git-pill">{campaignReady ? `${git.branch || 'no branch'} · ${git.dirty_count ?? 0} changes` : 'campaign unavailable'}</div>
      </div>

      <main className="workspace-grid" style={gridStyle}>
        <ActivityRail activeView={activeView} setActiveView={setActiveView} player={player} campaignReady={campaignReady} />

        <aside className="left-panel panel">
          <ContextPanel
            activeView={activeView}
            campaign={campaign}
            files={files}
            activePath={activePath}
            openFile={openFile}
            newFile={newFile}
            setActiveView={setActiveView}
          />
        </aside>

        <div className="resize-handle vertical left-resizer" onPointerDown={(event) => startResize('left', event)} />

        {showEditor ? (
          <>
            <section className={`editor-panel panel ${activeView === 'tutor' ? 'tutor-editor-panel' : ''}`}>
              <div className="editor-toolbar">
                <div className="active-file">
                  {activeView === 'tutor' ? (
                    <><span className="safe-badge">PYR WRITABLE</span> tutor.py{tutorDirty ? ' •' : ''}</>
                  ) : (
                    <>{activePath || 'No file selected'}{dirty ? ' •' : ''}</>
                  )}
                </div>
                <div className="toolbar-actions">
                  {activeView === 'tutor' ? (
                    <>
                      <button onClick={saveTutor} disabled={busy}>Save Tutor</button>
                      <button onClick={formatTutor} disabled={busy}>Pretty</button>
                      <button className="primary" onClick={runTutor} disabled={busy}>▶ Run Tutor</button>
                    </>
                  ) : (
                    <>
                      <button onClick={saveFile} disabled={!activePath || busy}>Save</button>
                      <button onClick={formatCurrent} disabled={!activePath || busy} title="Format document (Shift+Alt+F)">Pretty</button>
                      <button className="primary" onClick={runCurrent} disabled={!activePath || !activePath.endsWith('.py')}>▶ Run</button>
                    </>
                  )}
                </div>
              </div>
              {activeView === 'tutor' && (
                <div className="tutor-boundary-banner">
                  <strong>Collaborative notebook:</strong> PYR can write examples here. Required project source remains yours to write.
                </div>
              )}
              <div className="editor-wrap">
                <Editor
                  path={activeView === 'tutor' ? 'tutor.py' : (activePath || 'untitled.txt')}
                  language={activeView === 'tutor' ? 'python' : languageFor(activePath)}
                  value={activeView === 'tutor' ? tutorCode : code}
                  onChange={(value) => {
                    if (activeView === 'tutor') {
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
                    formatOnPaste: false,
                    formatOnType: false,
                  }}
                />
              </div>
            </section>

            <div className="resize-handle horizontal terminal-resizer" onPointerDown={(event) => startResize('terminal', event)} />

            <section className="terminal-panel panel">
              <div className="panel-title">
                <span>{activeView === 'tutor' ? 'TUTOR OUTPUT / TERMINAL' : 'TERMINAL'}</span>
                <span className="terminal-hint">real local shell · starts in workspace</span>
              </div>
              <TerminalPane ref={shellTerminalRef} banner="Forge shell connected." fontSize={terminalFontSize} skin={terminalSkin} />
            </section>
          </>
        ) : (
          <section className="game-screen panel">
            <GameScreen
              activeView={activeView}
              progress={progress}
              purchaseCosmetic={purchaseCosmetic}
              equipCosmetic={equipCosmetic}
              busy={busy}
              preferences={preferences}
              setters={setters}
              resetLayout={resetLayout}
              onNavigate={setActiveView}
              campaignReady={campaignReady}
            />
          </section>
        )}

        <div className="resize-handle vertical right-resizer" onPointerDown={(event) => startResize('right', event)} />

        <aside className="ai-panel panel">
          <div className="ai-toolbar">
            <div>
              <span className="panel-title-inline">PYR / AI</span>
              <span className="ai-subtitle"> {companion.form || 'Tiny Code-Flame'}</span>
            </div>
            <div className="ai-actions">
              <button onClick={() => summon('codex')}>Codex</button>
              <button onClick={() => summon('claude')}>Claude</button>
              <button onClick={() => summon('gemini')}>Gemini</button>
              <button onClick={() => aiTerminalRef.current?.clear()}>Clear</button>
            </div>
          </div>
          <div className="ai-note">Raw CLI terminal: powerful, not sandboxed. The future controlled PYR tutor will only be able to write tutor.py.</div>
          <TerminalPane ref={aiTerminalRef} banner="PYR channel ready. Choose Codex, Claude, or Gemini above." fontSize={terminalFontSize} skin={terminalSkin} />
        </aside>
      </main>

      <footer className="statusbar">
        <span>{notice || 'Ready.'}</span>
        <span>{busy ? 'working…' : activeView === 'tutor' ? 'tutor.py · Ctrl+S save · Shift+Alt+F format' : activePath ? `${languageFor(activePath)} · Ctrl+S save · Shift+Alt+F format` : 'select a file'}</span>
      </footer>
    </div>
  )
}

export default App
