import { syncEngine } from './cloud/syncEngine.js'
import {
  AVATAR_CLOUD_MIME_TYPES,
  AVATAR_MAX_BYTES,
  AVATAR_MAX_SOURCE_BYTES,
  AVATAR_MIME_TYPES,
  readCachedAvatar,
  validateAvatarDataUrl,
  writeCachedAvatar,
} from './cloud/avatarStorage.js'
import { pyrClientId } from './cloud/pyrClient.js'

const ICONS = {
  'Quest Hub': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7M5 9v11h14V9M9 20v-6h6v6"/></svg>',
  Forge: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 15h16M7 15V9l5-4 5 4v6M9 19h6"/></svg>',
  'Tutor Notebook': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 3v5l-4 8a3 3 0 0 0 2.7 4h8.6A3 3 0 0 0 19 16l-4-8V3M8 11h8M9 16h6"/></svg>',
  'Quest Journal': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h12v16H6zM9 8h6M9 12h6M9 16h4"/></svg>',
  Codex: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5zM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21.5z"/></svg>',
  Character: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/></svg>',
  Homestead: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-7 9 7M5 10v10h14V10M9 20v-6h6v6"/></svg>',
  Settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A7 7 0 0 0 15 6l-.3-2.6h-4L10.4 6a7 7 0 0 0-1.5.9l-2.4-1-2 3.4 2 1.5a7 7 0 0 0 0 2.2l-2 1.5 2 3.4 2.4-1a7 7 0 0 0 1.5.9l.3 2.6h4l.3-2.6a7 7 0 0 0 1.5-.9l2.4 1 2-3.4-2-1.5c.1-.3.1-.7.1-1z"/></svg>',
  Flame: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z"/></svg>',
  Shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z"/></svg>',
  Sword: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14 4 6-1-1 6-9 9-4-4zM6 14l-3 3 4 4 3-3"/></svg>',
  Gem: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 7 5-7 13L5 8zM5 8h14M9 8l3 13 3-13"/></svg>',
  Crown: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 7 4 4 4-7 4 7 4-4-2 11H6zM6 21h12"/></svg>',
  Trophy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4h8v4a4 4 0 0 1-8 0zM8 6H4v2a4 4 0 0 0 4 4M16 6h4v2a4 4 0 0 1-4 4M12 12v5M8 21h8M9 17h6"/></svg>',
  Monitor: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 21h8M12 16v5"/></svg>',
  'Infinite Dungeon': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V8l7-5 7 5v12M8 20v-5h8v5M9 9h6M12 9v3"/></svg>',
  Practice: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/></svg>',
}

const icon = (name, className = 'quest-icon') => `<span class="${className}">${ICONS[name] || ICONS.Forge}</span>`
const visible = (element) => Boolean(element && element.offsetParent !== null)
const findButton = (matcher) => [...document.querySelectorAll('button')].find((button) => visible(button) && matcher(button.textContent.trim(), button))

function clickSave() {
  const button = findButton((text) => text === 'Save' || text === 'Save Tutor')
  if (button) button.click()
}

function clickRun() {
  const button = [...document.querySelectorAll('.toolbar-actions button.primary')].find(visible)
  if (button) button.click()
}

function clickPretty() {
  const button = findButton((text) => text === 'Pretty')
  if (button) button.click()
}

function focusTerminal(selector) {
  const textarea = document.querySelector(`${selector} .xterm-helper-textarea`)
  textarea?.focus()
}

function terminalText() {
  const rows = document.querySelector('.terminal-panel .xterm-rows')
  if (!rows) return ''
  return rows.innerText
    .split('\n')
    .map((line) => line.replace(/\s+$/g, ''))
    .filter(Boolean)
    .slice(-28)
    .join('\n')
}

function activeFileLabel() {
  const text = document.querySelector('.editor-panel .active-file')?.textContent || 'unknown file'
  return text.replace('PYR WRITABLE', '').replace('•', '').trim()
}

function showToast(message, tone = 'default') {
  let toast = document.querySelector('.qol-toast')
  if (!toast) {
    toast = document.createElement('div')
    toast.className = 'qol-toast'
    document.body.appendChild(toast)
  }
  toast.dataset.tone = tone
  toast.textContent = message
  toast.classList.add('show')
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600)
}

async function requestPyrContext(output) {
  const publisher = window.__questlabPublishPyrContext
  if (typeof publisher === 'function') {
    try {
      return await publisher({ terminalTail: output })
    } catch {
      // Fall through to the direct local bridge request when React is still
      // mounting or the current editor surface is unavailable.
    }
  }

  const response = await fetch('/api/pyr/context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      active_path: activeFileLabel(),
      selection: '',
      terminal_tail: output,
      client_id: pyrClientId(),
    }),
  })
  if (!response.ok) throw new Error('The local PYR context bridge is unavailable.')
  const result = await response.json()
  return result.context || result
}

function contextPrompt(context, fallbackOutput) {
  const activeFile = context?.active_file
  const selection = context?.selection?.text || ''
  const terminalTail = context?.terminal?.tail || fallbackOutput
  const quest = context?.quest || {}
  const encounter = context?.encounter || null
  const assistance = quest.assistance || {}
  const fileLabel = activeFile?.path || activeFileLabel()
  const fileContent = activeFile?.content || ''
  const gitDiff = context?.git?.diff || ''
  const verdict = context?.verdict || null

  return [
    'Quest Lab structured context from the local PYR bridge.',
    `Campaign revision: ${context?.revision ?? 'unknown'}`,
    `Active file: ${fileLabel}${activeFile?.truncated ? ' (content truncated)' : ''}`,
    '',
    'Selected code:',
    '```text',
    selection || '(no selection)',
    '```',
    '',
    'Active file content:',
    '```text',
    fileContent || '(file content unavailable)',
    '```',
    '',
    'Recent Forge terminal output:',
    '```text',
    terminalTail || '(no terminal output)',
    '```',
    '',
    'Git diff (state files and secret-looking files are excluded):',
    '```diff',
    gitDiff || '(no code diff)',
    '```',
    '',
    'Validated current quest/mob state (future locked encounters are omitted):',
    JSON.stringify({ quest, encounter, assistance }, null, 2),
    '',
    `Battle verdict challenge: ${verdict?.nonce || '(none; capture context while an encounter is active)'}`,
    'For Battle, first bind the player answer with POST /api/pyr/battle-submission, then independently adjudicate that submission and use POST /api/pyr/verdict with its exact tokens. Never supply Impact, reward or damage values.',
    '',
    'Act as PYR under TUTOR_CONTRACT.md. Do not invent rewards or mutate player state directly. Tutor me from this context using the hint ladder; use tutor.py for examples and send any progression decision through the controlled state service.',
    '',
  ].join('\n')
}

async function submitRunToAI() {
  const output = terminalText()
  if (!output) {
    showToast('Nothing recent in the Forge terminal to submit.', 'warn')
    return
  }

  const provider = sessionStorage.getItem('questlab.aiProvider')
  if (!provider) {
    showToast('Launch Codex, Claude, or AGY first, then submit the run.', 'warn')
    focusTerminal('.ai-panel')
    return
  }

  const textarea = document.querySelector('.ai-panel .xterm-helper-textarea')
  if (!textarea) {
    showToast('AI terminal is not ready yet.', 'warn')
    return
  }

  try {
    const context = await requestPyrContext(output)
    const payload = contextPrompt(context, output)
    textarea.focus()
    const data = new DataTransfer()
    data.setData('text/plain', `${payload}\n`)
    const event = new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true })
    textarea.dispatchEvent(event)
    showToast(`Submitted recent run to ${provider}.`, 'success')
  } catch {
    const fallback = [
      'Quest Lab context submission (local bridge unavailable).',
      `Active file: ${activeFileLabel()}`,
      '',
      'Recent Forge terminal output:',
      '```text',
      output,
      '```',
      '',
      'Act as PYR under TUTOR_CONTRACT.md. Do not edit required project files. Tutor me from this run using the hint ladder; use tutor.py for examples.',
      '',
    ].join('\n')
    navigator.clipboard?.writeText(fallback)
    focusTerminal('.ai-panel')
    showToast('Context copied. Paste it into the AI terminal with Ctrl+V.', 'warn')
  }
}

function installSubmitButton() {
  const toolbar = document.querySelector('.editor-panel .toolbar-actions')
  if (!toolbar || toolbar.querySelector('[data-qol-submit]')) return
  const button = document.createElement('button')
  button.dataset.qolSubmit = 'true'
  button.className = 'qol-submit-button'
  button.textContent = 'Submit run'
  button.title = 'Send recent Forge terminal output to the active AI (Ctrl+Shift+Enter)'
  button.addEventListener('click', submitRunToAI)
  toolbar.prepend(button)
}

function trackAIProvider() {
  document.querySelectorAll('.ai-actions button').forEach((button) => {
    if (button.dataset.providerTracked) return
    const label = button.textContent.trim()
    if (!['Codex', 'Claude', 'AGY'].includes(label)) return
    button.dataset.providerTracked = 'true'
    button.addEventListener('click', () => {
      sessionStorage.setItem('questlab.aiProvider', label)
      showToast(`${label} selected as the active tutor terminal.`, 'success')
    })
  })
}

function replaceRailIcons() {
  const mark = document.querySelector('.activity-mark')
  if (mark && !mark.dataset.vectorized) {
    mark.dataset.vectorized = 'true'
    mark.innerHTML = icon('Flame', 'quest-icon quest-mark-icon')
  }

  document.querySelectorAll('.activity-button').forEach((button) => {
    if (button.dataset.vectorized) return
    const label = button.getAttribute('aria-label') || button.title
    if (!ICONS[label]) return
    button.dataset.vectorized = 'true'
    button.innerHTML = icon(label)
  })
}

function replaceGameIcons() {
  const pyrOrb = document.querySelector('.pyr-orb')
  if (pyrOrb && !pyrOrb.dataset.vectorized) {
    pyrOrb.dataset.vectorized = 'true'
    pyrOrb.innerHTML = icon('Flame', 'quest-icon quest-game-icon')
  }

  const equipment = [...document.querySelectorAll('.equipment-list > div > span')]
  const equipmentIcons = ['Shield', 'Gem', 'Crown']
  equipment.forEach((node, index) => {
    if (node.dataset.vectorized) return
    node.dataset.vectorized = 'true'
    node.innerHTML = icon(equipmentIcons[index] || 'Gem', 'quest-icon quest-game-icon')
  })

  const hearth = document.querySelector('.homestead-hearth > span')
  if (hearth && !hearth.dataset.vectorized) {
    hearth.dataset.vectorized = 'true'
    hearth.innerHTML = icon('Flame', 'quest-icon quest-game-icon')
  }
  const desk = document.querySelector('.homestead-desk > span')
  if (desk && !desk.dataset.vectorized) {
    desk.dataset.vectorized = 'true'
    desk.innerHTML = icon('Monitor', 'quest-icon quest-game-icon')
  }
  const shelf = document.querySelector('.homestead-shelf > span')
  if (shelf && !shelf.dataset.vectorized) {
    shelf.dataset.vectorized = 'true'
    shelf.innerHTML = icon('Trophy', 'quest-icon quest-game-icon')
  }
}

let activeAvatar

function getAvatar() {
  return activeAvatar === undefined ? readCachedAvatar() : activeAvatar
}

function setLocalAvatar(dataUrl) {
  activeAvatar = dataUrl || ''
  if (!writeCachedAvatar(activeAvatar)) showToast('Could not store the avatar in this browser.', 'warn')
  applyAvatar(true)
}

function avatarImage(dataUrl, className) {
  const img = document.createElement('img')
  img.src = dataUrl
  img.alt = 'Character avatar'
  img.className = className
  return img
}

function avatarVersion(dataUrl) {
  return dataUrl ? `${dataUrl.length}:${dataUrl.slice(-24)}` : 'default'
}

function applyAvatar(force = false) {
  const dataUrl = getAvatar()
  const version = avatarVersion(dataUrl)
  const activity = document.querySelector('.activity-avatar')
  if (activity) {
    let slot = activity.querySelector('.quest-avatar-slot')
    if (!slot) {
      slot = activity.querySelector('span')
      if (slot) slot.classList.add('quest-avatar-slot')
    }
    if (slot && (force || slot.dataset.avatarVersion !== version)) {
      slot.dataset.avatarVersion = version
      slot.innerHTML = ''
      if (dataUrl) slot.appendChild(avatarImage(dataUrl, 'quest-avatar-img compact'))
      else slot.textContent = 'L'
    }
  }

  const sigil = document.querySelector('.character-sigil')
  if (sigil && (force || sigil.dataset.avatarVersion !== version)) {
    sigil.dataset.avatarVersion = version
    sigil.innerHTML = ''
    if (dataUrl) sigil.appendChild(avatarImage(dataUrl, 'quest-avatar-img character'))
    else sigil.textContent = 'L'
  }
}

function createAvatarInput() {
  let input = document.querySelector('#questlab-avatar-input')
  if (input) return input
  input = document.createElement('input')
  input.id = 'questlab-avatar-input'
  input.type = 'file'
  input.accept = 'image/png,image/jpeg,image/webp'
  input.hidden = true
  input.addEventListener('change', async () => {
    const file = input.files?.[0]
    input.value = ''
    if (!file) return
    if (!AVATAR_MIME_TYPES.includes(file.type)) {
      showToast('Avatar must be a PNG, JPEG or WebP image.', 'warn')
      return
    }
    if (file.size > AVATAR_MAX_SOURCE_BYTES) {
      showToast('Avatar image must be under 5 MB.', 'warn')
      return
    }

    try {
      const source = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result))
        reader.onerror = reject
        reader.readAsDataURL(file)
      })

      const image = await new Promise((resolve, reject) => {
        const img = new Image()
        img.onload = () => resolve(img)
        img.onerror = reject
        img.src = source
      })

      const canvas = document.createElement('canvas')
      canvas.width = 256
      canvas.height = 256
      const context = canvas.getContext('2d')
      if (!context) throw new Error('Canvas is unavailable.')
      const side = Math.min(image.naturalWidth, image.naturalHeight)
      const sx = (image.naturalWidth - side) / 2
      const sy = (image.naturalHeight - side) / 2
      context.drawImage(image, sx, sy, side, side, 0, 0, 256, 256)

      let dataUrl = ''
      for (const quality of [0.86, 0.72, 0.58, 0.44, 0.32]) {
        const candidate = canvas.toDataURL('image/webp', quality)
        try {
          validateAvatarDataUrl(candidate, { maxBytes: AVATAR_MAX_BYTES, allowedMimeTypes: AVATAR_CLOUD_MIME_TYPES })
          dataUrl = candidate
          break
        } catch {
          // Try a lower quality before refusing an oversized portrait.
        }
      }
      if (!dataUrl) throw new Error('Avatar image must be under 1 MB after processing.')

      if (syncEngine.getState().authStatus === 'signed-in') {
        await syncEngine.setAvatarDataUrl(dataUrl)
        showToast('Character portrait synced to your account.', 'success')
      } else {
        setLocalAvatar(dataUrl)
        showToast('Character portrait updated on this device.', 'success')
      }
      document.querySelector('.avatar-controls')?.remove()
      installAvatarControls()
    } catch (error) {
      showToast(error?.message || 'That image could not be loaded.', 'warn')
    }
  })
  document.body.appendChild(input)
  return input
}

function installAvatarControls() {
  const card = document.querySelector('.character-card')
  if (!card || card.querySelector('.avatar-controls')) return
  const controls = document.createElement('div')
  controls.className = 'avatar-controls'

  const upload = document.createElement('button')
  upload.textContent = getAvatar() ? 'Change portrait' : 'Upload portrait'
  upload.addEventListener('click', () => createAvatarInput().click())
  controls.appendChild(upload)

  if (getAvatar()) {
    const remove = document.createElement('button')
    remove.textContent = 'Remove'
    remove.addEventListener('click', async () => {
      try {
        if (syncEngine.getState().authStatus === 'signed-in') await syncEngine.removeAvatar()
        else setLocalAvatar('')
        controls.remove()
        installAvatarControls()
        showToast(syncEngine.getState().authStatus === 'signed-in' ? 'Character portrait removed from your account.' : 'Character portrait removed.')
      } catch (error) {
        showToast(error?.message || 'Avatar could not be removed.', 'warn')
      }
    })
    controls.appendChild(remove)
  }

  card.appendChild(controls)
}

window.addEventListener('questlab:avatar-updated', (event) => {
  activeAvatar = typeof event.detail?.dataUrl === 'string' ? event.detail.dataUrl : ''
  applyAvatar(true)
  installAvatarControls()
})

function enhance() {
  installSubmitButton()
  trackAIProvider()
  replaceRailIcons()
  replaceGameIcons()
  applyAvatar()
  installAvatarControls()
}

window.addEventListener('keydown', (event) => {
  if (event.defaultPrevented || event.__questlabHandled) return
  const modifier = event.ctrlKey || event.metaKey
  if (modifier && !event.shiftKey && event.key.toLowerCase() === 's') {
    event.preventDefault()
    event.__questlabHandled = true
    clickSave()
    return
  }
  if (modifier && !event.shiftKey && event.key === 'Enter') {
    event.preventDefault()
    event.__questlabHandled = true
    clickRun()
    return
  }
  if (modifier && event.shiftKey && event.key === 'Enter') {
    event.preventDefault()
    event.__questlabHandled = true
    submitRunToAI()
    return
  }
  if (event.shiftKey && event.altKey && event.key.toLowerCase() === 'f') {
    event.preventDefault()
    event.__questlabHandled = true
    clickPretty()
    return
  }
  if (modifier && !event.shiftKey && event.key === '`') {
    event.preventDefault()
    event.__questlabHandled = true
    focusTerminal('.terminal-panel')
    return
  }
  if (modifier && event.shiftKey && event.key === '`') {
    event.preventDefault()
    event.__questlabHandled = true
    focusTerminal('.ai-panel')
  }
})

let enhanceFrame = 0
const observer = new MutationObserver(() => {
  if (enhanceFrame) return
  enhanceFrame = requestAnimationFrame(() => {
    enhanceFrame = 0
    enhance()
  })
})
observer.observe(document.documentElement, { subtree: true, childList: true })
window.addEventListener('load', enhance)
queueMicrotask(enhance)
