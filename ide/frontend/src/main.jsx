import ReactDOM from 'react-dom/client'
import { loader } from '@monaco-editor/react'
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

// Load Monaco's prebuilt AMD build from the same origin (copied into
// public/monaco by scripts/copy-monaco.mjs) so Forge stays usable offline and
// keeps every language and worker without Rollup bundling Monaco.
// @monaco-editor/react otherwise defaults to a jsDelivr loader.
loader.config({ paths: { vs: `${import.meta.env.BASE_URL}monaco/vs` } })

// Quest Lab owns real PTY/WebSocket sessions. React StrictMode intentionally
// double-mounts effects in development, which creates/kills duplicate shells.
// Run the local IDE once so each visible terminal maps to one PTY session.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
