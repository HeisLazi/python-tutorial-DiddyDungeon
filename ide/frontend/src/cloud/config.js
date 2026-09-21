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
