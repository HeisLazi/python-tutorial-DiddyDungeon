import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendPort = Number(process.env.QUESTLAB_BACKEND_PORT || 7331)
const frontendPort = Number(process.env.QUESTLAB_FRONTEND_PORT || 5173)
const backendHttp = `http://127.0.0.1:${backendPort}`
const backendWs = `ws://127.0.0.1:${backendPort}`

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': backendHttp,
      '/ws': {
        target: backendWs,
        ws: true,
      },
    },
  },
})
