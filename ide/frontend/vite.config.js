import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectDir = path.dirname(fileURLToPath(import.meta.url))

const backendPort = Number(process.env.QUESTLAB_BACKEND_PORT || 7331)
const frontendPort = Number(process.env.QUESTLAB_FRONTEND_PORT || 5173)
const repoRoot = path.resolve(projectDir, '..', '..')
const buildSha = process.env.QUESTLAB_BUILD_SHA || (() => {
  try {
    return execFileSync('git', ['-C', repoRoot, 'rev-parse', '--verify', 'HEAD'], {
      encoding: 'utf8',
      timeout: 1_000,
    }).trim()
  } catch {
    return ''
  }
})()
const backendHttp = `http://127.0.0.1:${backendPort}`
const backendWs = `ws://127.0.0.1:${backendPort}`

export default defineConfig({
  plugins: [react()],
  define: {
    __QUESTLAB_BUILD_SHA__: JSON.stringify(buildSha),
  },
  resolve: {
    // monaco-editor's package exports cover its root ESM entry but not the
    // nested worker modules. Alias that documented Vite path to the bundled
    // local files so Rollup never falls back to the CDN loader.
    alias: {
      'monaco-editor/esm': path.resolve(projectDir, 'node_modules/monaco-editor/esm'),
    },
  },
  optimizeDeps: {
    // The worker entrypoints are Vite ?worker modules, not browser
    // dependencies for esbuild's pre-bundler.
    exclude: ['monaco-editor'],
  },
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
