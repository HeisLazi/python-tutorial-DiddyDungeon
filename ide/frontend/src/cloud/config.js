const readValue = (environment, name) => {
  const value = environment?.[name]
  return typeof value === 'string' ? value.trim() : ''
}

const validHttpUrl = (value) => {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export function resolveCloudConfig(environment = {}) {
  const url = readValue(environment, 'VITE_SUPABASE_URL')
  const anonKey = readValue(environment, 'VITE_SUPABASE_ANON_KEY')

  if (!url && !anonKey) {
    return {
      configured: false,
      valid: true,
      mode: 'local',
      reason: 'Cloud configuration is not set. Forge is running in Offline / Local Mode.',
      url: '',
      anonKey: '',
    }
  }

  if (!url || !anonKey) {
    return {
      configured: false,
      valid: false,
      mode: 'local',
      reason: 'Cloud configuration is incomplete. Set both public Supabase values or neither.',
      url: '',
      anonKey: '',
    }
  }

  if (!validHttpUrl(url)) {
    return {
      configured: false,
      valid: false,
      mode: 'local',
      reason: 'VITE_SUPABASE_URL must be an http(s) URL. Forge is staying local.',
      url: '',
      anonKey: '',
    }
  }

  return {
    configured: true,
    valid: true,
    mode: 'cloud-ready',
    reason: 'Public Supabase client configuration is available.',
    url,
    anonKey,
  }
}

export const cloudConfig = resolveCloudConfig(import.meta.env ?? {})

// The loopback app backend fetches this public config from the match service.
// Using the same origin avoids Windows WebView port/CORS mismatches when more
// than one Quest Lab instance is open. Keep it in memory only.
export async function loadRemoteCloudConfig(fetchImpl = globalThis.fetch, timeoutMs = 3500) {
  try {
    if (!fetchImpl) return null
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    let data
    try {
      const response = await fetchImpl('/api/online/client-config', {signal:controller.signal, cache:'no-store', credentials:'omit', redirect:'error'})
      if (!response.ok) return null
      data = await response.json()
    } finally { clearTimeout(timer) }
    const project = new URL(data?.url)
    if (project.protocol !== 'https:' || !project.hostname.endsWith('.supabase.co') || project.username || project.password || project.pathname !== '/' || project.search || project.hash || typeof data.publishable_key !== 'string' || !data.publishable_key.startsWith('sb_publishable_') || data.publishable_key.length > 512) return null
    return resolveCloudConfig({VITE_SUPABASE_URL:project.origin, VITE_SUPABASE_ANON_KEY:data.publishable_key})
  } catch { return null }
}

export async function initializeCloudConfig() {
  if (cloudConfig.configured || !cloudConfig.valid) return
  const remote = await loadRemoteCloudConfig()
  if (remote) Object.assign(cloudConfig, remote)
}
