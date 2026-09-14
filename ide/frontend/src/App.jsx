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
  if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript'
  if (path.endsWith('.html')) return 'html'
  if (path.endsWith('.css')) return 'css'
  return 'plaintext'
}

const TerminalPane = forwardRef(function TerminalPane(_, ref) {
  const hostRef = useRef(null)
  const socketRef = useRef(null)
  const termRef = useRef(null)

  useImperativeHandle(ref, () => ({
    send(text) {
      if (socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.send(text)
    },
    focus() {
      termRef.current?.focus()
    },
  }))

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      convertEol: false,
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
    socket.onopen = () => term.writeln('\r\n\x1b[38;5;214mQuest terminal connected.\x1b[0m')
    socket.onmessage = (event) => term.write(event.data)
    socket.onclose = () => term.writeln('\r\n\x1b[31mTerminal disconnected. Restart Quest Lab to reconnect.\x1b[0m')
    socket.onerror = () => term.writeln('\r\n\x1b[31mTerminal connection error.\x1b[0m')

    const disposable = term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) socket.send(data)
    })

    const observer = new ResizeObserver(() => fit.fit())
    observer.observe(hostRef.current)

    return () => {
      observer.disconnect()
      disposable.dispose()
      socket.close()
      term.dispose()
    }
  }, [])

  return <div className="terminal-host" ref={hostRef} />
})

function App() {
  const terminalRef = useRef(null)
  const [campaign, setCampaign] = useState(null)
  const [files, setFiles] = useState([])
  const [activePath, setActivePath] = useState('')
  const [code, setCode] = useState('')
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')

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
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

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
      return true
    } catch (error) {
      setNotice(`Save failed: ${error.message}`)
      return false
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
    terminalRef.current?.send(`python ${JSON.stringify(activePath)}\n`)
    terminalRef.current?.focus()
  }

  const summon = (command) => {
    terminalRef.current?.send(`${command}\n`)
    terminalRef.current?.focus()
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

      <main className="workspace-grid">
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

        <section className="editor-panel panel">
          <div className="editor-toolbar">
            <div className="active-file">{activePath || 'No file selected'}{dirty ? ' •' : ''}</div>
            <div className="toolbar-actions">
              <button onClick={saveFile} disabled={!activePath || busy}>Save</button>
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
              }}
            />
          </div>
        </section>

        <aside className="right-panel panel">
          <div className="panel-title"><span>PYR</span><span className="pyr-dot">●</span></div>
          <div className="pyr-card">
            <div className="pyr-avatar">🔥</div>
            <strong>{companion.form || 'Tiny Code-Flame'}</strong>
            <p>Your terminal is real. Launch whichever coding AI CLI you already use and keep the repo rules open beside it.</p>
          </div>
          <div className="summon-grid">
            <button onClick={() => summon('codex')}>Summon Codex</button>
            <button onClick={() => summon('claude')}>Summon Claude</button>
            <button onClick={() => summon('gemini')}>Summon Gemini</button>
          </div>
          <div className="rule-card">
            <strong>Forge rules</strong>
            <p>Teach → practice → teach-back → build from scratch. Exact project help only through Reference Mode.</p>
          </div>
          <div className="mini-stats">
            <div><span>Learning streak</span><b>{streak.current ?? 0}</b></div>
            <div><span>Dev streak</span><b>{activity.current_streak ?? 0}</b></div>
            <div><span>Commits 7d</span><b>{activity.commits_7d ?? 0}</b></div>
            <div><span>Clean clears</span><b>{stats.clean_clears ?? 0}</b></div>
          </div>
        </aside>

        <section className="terminal-panel panel">
          <div className="panel-title">
            <span>TERMINAL</span>
            <span className="terminal-hint">real shell · workspace scoped</span>
          </div>
          <TerminalPane ref={terminalRef} />
        </section>
      </main>

      <footer className="statusbar">
        <span>{notice || 'Ready.'}</span>
        <span>{busy ? 'working…' : activePath ? `${languageFor(activePath)} · Ctrl+S to save` : 'select a file'}</span>
      </footer>
    </div>
  )
}

export default App
