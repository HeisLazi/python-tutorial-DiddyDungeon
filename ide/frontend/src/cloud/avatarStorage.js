export const AVATAR_BUCKET = 'avatars'
export const AVATAR_OBJECT_NAME = 'avatar.webp'
export const AVATAR_LOCAL_KEY = 'questlab.avatar.v1'
export const AVATAR_ACCOUNT_KEY_PREFIX = `${AVATAR_LOCAL_KEY}:`
export const AVATAR_MAX_SOURCE_BYTES = 5_000_000
export const AVATAR_MAX_BYTES = 1_000_000
export const AVATAR_MIME_TYPES = Object.freeze(['image/png', 'image/jpeg', 'image/webp'])
export const AVATAR_CLOUD_MIME_TYPES = Object.freeze(['image/webp'])

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const DATA_URL_RE = /^data:([^;,]+);base64,([A-Za-z0-9+/]+={0,2})$/

const safeStorage = (storage) => storage || (typeof globalThis.localStorage !== 'undefined' ? globalThis.localStorage : null)

export function avatarCacheKey(userId = '') {
  const normalized = String(userId || '').trim()
  return normalized ? `${AVATAR_ACCOUNT_KEY_PREFIX}${encodeURIComponent(normalized)}` : AVATAR_LOCAL_KEY
}

export function readCachedAvatar(storage, userId = '') {
  try {
    return safeStorage(storage)?.getItem(avatarCacheKey(userId)) || ''
  } catch {
    return ''
  }
}

export function writeCachedAvatar(dataUrl, storage, userId = '') {
  try {
    const target = safeStorage(storage)
    if (!target) return false
    if (dataUrl) target.setItem(avatarCacheKey(userId), dataUrl)
    else target.removeItem(avatarCacheKey(userId))
    return true
  } catch {
    return false
  }
}

export function removeCachedAvatar(storage, userId = '') {
  return writeCachedAvatar('', storage, userId)
}

export function avatarObjectPath(userId) {
  const normalized = String(userId || '').trim()
  if (!UUID_RE.test(normalized)) throw new Error('Avatar account identity is invalid.')
  return `${normalized}/${AVATAR_OBJECT_NAME}`
}

export function inspectAvatarDataUrl(dataUrl, { maxBytes = AVATAR_MAX_BYTES, allowedMimeTypes = AVATAR_MIME_TYPES } = {}) {
  if (typeof dataUrl !== 'string') throw new Error('Avatar data must be text.')
  const match = DATA_URL_RE.exec(dataUrl)
  if (!match || !allowedMimeTypes.includes(match[1].toLowerCase())) {
    throw new Error('Avatar must be a PNG, JPEG or WebP image.')
  }

  const encoded = match[2]
  const padding = (encoded.match(/=+$/) || [''])[0].length
  const bytes = Math.floor((encoded.length * 3) / 4) - padding
  if (!Number.isFinite(bytes) || bytes <= 0 || bytes > maxBytes) {
    const limit = maxBytes >= 1_000_000 ? `${Math.round(maxBytes / 1_000_000)} MB` : `${maxBytes} bytes`
    throw new Error(`Avatar image must be under ${limit}.`)
  }
  try {
    if (typeof globalThis.atob === 'function') globalThis.atob(encoded)
  } catch {
    throw new Error('Avatar image data is invalid.')
  }
  return { mimeType: match[1].toLowerCase(), bytes }
}

export function validateAvatarDataUrl(dataUrl, options = {}) {
  return inspectAvatarDataUrl(dataUrl, options)
}

export function dataUrlToBlob(dataUrl, options = {}) {
  const { mimeType } = inspectAvatarDataUrl(dataUrl, options)
  const encoded = DATA_URL_RE.exec(dataUrl)[2]
  if (typeof globalThis.atob !== 'function' || typeof globalThis.Blob !== 'function' || typeof globalThis.Uint8Array !== 'function') {
    throw new Error('Avatar upload is unavailable in this browser.')
  }
  const binary = globalThis.atob(encoded)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  return new Blob([bytes], { type: mimeType })
}

export async function blobToDataUrl(blob) {
  if (!blob) throw new Error('Avatar download returned no image.')
  if (typeof FileReader === 'function') {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = () => reject(new Error('Avatar image could not be cached locally.'))
      reader.readAsDataURL(blob)
    })
  }

  if (typeof blob.arrayBuffer === 'function' && typeof globalThis.btoa === 'function') {
    const buffer = await blob.arrayBuffer()
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let index = 0; index < bytes.length; index += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
    }
    return `data:${blob.type || 'image/webp'};base64,${globalThis.btoa(binary)}`
  }

  throw new Error('Avatar image could not be cached locally.')
}
