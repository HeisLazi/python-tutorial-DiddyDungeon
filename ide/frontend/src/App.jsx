import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'

const api = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `${response.status} ${response.statusText}`)
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

const TerminalPane = forwardRef(function TerminalPane({ banner = 'Quest terminal connected.' }, ref) {
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
      fontSize: 13,
      theme: {
        background: '#090b0a',
        foreground: '#e9e4d8',
        cursor: '#d8a657',
        selectionBackground: '#3b4035',
      },
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
  }, [banner])

  return <div className="terminal-host" ref={hostRef} />
})

const clamp = (value, min, max) => Math.max(min, Math.min(max, value))

function App() {
  const shellTerminalRef = useRef(null)
  const aiTerminalRef = useRef(null)
  const [campaign, setCampaign] = useState(null)
  const [files, setFiles] = useState([])
  const [activePath, setActivePath] = useState('')
  const [code, setCode] = useState('')
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [leftWidth, setLeftWidth] = useState(220)
  const [rightWidth, setRightWidth] = useState(390)
  const [terminalHeight, setTerminalHeight] = useState(245)

  const player = campaign?.progress?.player || {}
  const stats = campaign?.progress?.stats || {}
  const streak = campaign?.progress?.streak || {}
  const companion = campaign?.progress?.companion || {}
  const quest = campaign?.progress?.current_quest || 'Choose a quest.'
  const activity = campaign?.activity || {}
  const git = campaign?.git || {}

  const shields = useMemo(
    () => (campaign?.progress?.skills || []).filter((skill) => skill.shield?.tier && skill.shield.tier !== 'none').length,
    [campaign],
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
        const preferred = (result.items || []).find((item) => item.type === 'file' && item.path.endsWith('.py'))
        if (preferred) openFile(preferred.path)
      }
    } catch (error) {
      setNotice(`File tree failed: ${error.message}`)
    }
  }

  useEffect(() => {
    refreshCampaign()
    refreshFiles()
  }, [])

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        saveFile()
      }
      if (event.shiftKey && event.altKey && event.key.toLowerCase() === 'f') {
        event.preventDefault()
        formatCurrent()
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
      if (kind === 'left') setLeftWidth(clamp(startLeft + (moveEvent.clientX - startX), 150, 420))
      if (kind === 'right') setRightWidth(clamp(startRight - (moveEvent.clientX - startX), 280, 720))
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
      return true
    } catch (error) {
      setNotice(`Save failed: ${error.message}`)
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
    shellTerminalRef.current?.send(`python ${JSON.stringify(activePath)}\n`)
    shellTerminalRef.current?.focus()
  }

  const summon = (command) => {
    aiTerminalRef.current?.send(`${command}\n`)
    aiTerminalRef.current?.focus()
  }

  const gridStyle = {
    gridTemplateColumns: `${leftWidth}px 5px minmax(420px, 1fr) 5px ${rightWidth}px`,
    gridTemplateRows: `minmax(220px, 1fr) 5px ${terminalHeight}px`,
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">PYTHON QUEST LAB</div>
          <h1>Forge IDE</h1>
        </div>
        <div className="top-stats">
          <span>LV {player.level ?? 1}</span>
          <span>{player.xp ?? 0}/{player.xp_next ?? 100} XP</span>
          <span>HP {player.hp ?? 100}</span>
          <span>🔥 {streak.current ?? 0}</span>
          <span>🛡 {shields}</span>
          <span>⚔ {stats.bosses_defeated ?? 0}</span>
          <span>DEV {activity.activity_score ?? 0}</span>
        </div>
      </header>

      <div className="quest-banner">
        <div><strong>{companion.name || 'PYR'}</strong> · {companion.form || 'Tiny Code-Flame'}</div>
        <div className="quest-text">{quest}</div>
        <div className="git-pill">{git.branch || 'no branch'} · {git.dirty_count ?? 0} changes</div>
      </div>

      <main className="workspace-grid" style={gridStyle}>
        <aside className="left-panel panel">
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
        </aside>

        <div className="resize-handle vertical left-resizer" onPointerDown={(event) => startResize('left', event)} />

        <section className="editor-panel panel">
          <div className="editor-toolbar">
            <div className="active-file">{activePath || 'No file selected'}{dirty ? ' •' : ''}</div>
            <div className="toolbar-actions">
              <button onClick={saveFile} disabled={!activePath || busy}>Save</button>
              <button onClick={formatCurrent} disabled={!activePath || busy} title="Format document (Shift+Alt+F)">Pretty</button>
              <button className="primary" onClick={runCurrent} disabled={!activePath || !activePath.endsWith('.py')}>▶ Run</button>
            </div>
          </div>
          <div className="editor-wrap">
            <Editor
              path={activePath || 'untitled.txt'}
              language={languageFor(activePath)}
              value={code}
              onChange={(value) => { setCode(value ?? ''); setDirty(true) }}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: 'JetBrains Mono, ui-monospace, monospace',
                lineHeight: 22,
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
            <span>TERMINAL</span>
            <span className="terminal-hint">real local shell · starts in workspace</span>
          </div>
          <TerminalPane ref={shellTerminalRef} banner="Forge shell connected." />
        </section>

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
          <div className="ai-note">Independent terminal session. Launch one AI CLI here; keep your normal shell separate below the editor.</div>
          <TerminalPane ref={aiTerminalRef} banner="PYR channel ready. Choose Codex, Claude, or Gemini above." />
        </aside>
      </main>

      <footer className="statusbar">
        <span>{notice || 'Ready.'}</span>
        <span>{busy ? 'working…' : activePath ? `${languageFor(activePath)} · Ctrl+S save · Shift+Alt+F format` : 'select a file'}</span>
      </footer>
    </div>
  )
}

export default App
