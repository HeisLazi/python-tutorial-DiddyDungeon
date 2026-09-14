import ReactDOM from 'react-dom/client'
import App from './AppV2.jsx'
import './styles.css'
import './v2.css'
import './enhancements.css'
import './forgeEnhancements.js'
import '@xterm/xterm/css/xterm.css'

// Quest Lab owns real PTY/WebSocket sessions. React StrictMode intentionally
// double-mounts effects in development, which creates/kills duplicate shells.
// Run the local IDE once so each visible terminal maps to one PTY session.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
