import ReactDOM from 'react-dom/client'
import { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'
import App from './AppV2.jsx?homePortParity20260921'
import './styles.css'
import './foundation.css'
import './v2.css'
import './enhancements.css'
import './uiPolish.css'
import './commandPalette.css'
import './combatShell.css'
import './forgeEnhancements.js'
import './uiPolish.js'
import './commandPalette.js'
import './combatShell.js'
import '@xterm/xterm/css/xterm.css'

// Bundle Monaco and its language workers locally so Forge remains usable when
// the machine has no internet connection. @monaco-editor/react otherwise
// defaults to a jsDelivr AMD loader.
self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker()
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
  },
}
loader.config({ monaco })

// Quest Lab owns real PTY/WebSocket sessions. React StrictMode intentionally
// double-mounts effects in development, which creates/kills duplicate shells.
// Run the local IDE once so each visible terminal maps to one PTY session.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
