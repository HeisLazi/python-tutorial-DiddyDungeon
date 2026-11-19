const PYR_CLIENT_ID_KEY = 'questlab.pyr.client-id'

export const pyrClientId = () => {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) return 'default'
    const current = window.sessionStorage.getItem(PYR_CLIENT_ID_KEY)
    if (current && /^[A-Za-z0-9._:-]{1,128}$/.test(current)) return current
    const generated = typeof window.crypto?.randomUUID === 'function'
      ? window.crypto.randomUUID()
      : `tab-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    window.sessionStorage.setItem(PYR_CLIENT_ID_KEY, generated)
    return generated
  } catch {
    return 'default'
  }
}
