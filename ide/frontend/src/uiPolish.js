const svg = (path, extra = '') => `<span class="quest-icon ${extra}"><svg viewBox="0 0 24 24" aria-hidden="true">${path}</svg></span>`

const ICON = {
  flame: svg('<path d="M13 2s1 4-2 7c-2 2-3 4-2 7 1 2 3 3 5 2 3-1 5-4 4-8 3 3 4 8 1 11-4 4-12 2-13-4-1-5 3-8 7-15z"/>'),
  shield: svg('<path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z"/>'),
  sword: svg('<path d="m14 4 6-1-1 6-9 9-4-4zM6 14l-3 3 4 4 3-3"/>'),
  heart: svg('<path d="M20 8c0 5-8 11-8 11S4 13 4 8a4 4 0 0 1 7-3 4 4 0 0 1 7 0 4 4 0 0 1 2 3z"/>'),
  coin: svg('<circle cx="12" cy="12" r="8"/><path d="M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5M12 6v12"/>'),
  book: svg('<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5zM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21.5z"/>'),
}

function replaceTopStat(node) {
  if (node.dataset.iconCleaned) {
    const value = node.querySelector('[data-stat-value]')
    if (value && node.dataset.campaignStatValue !== undefined && value.textContent !== node.dataset.campaignStatValue) value.textContent = node.dataset.campaignStatValue
    return
  }
  const text = node.textContent.trim()
  const replacements = [
    ['♥', 'heart'],
    ['◈', 'coin'],
    ['🔥', 'flame'],
    ['🛡', 'shield'],
    ['⚔', 'sword'],
  ]
  for (const [glyph, name] of replacements) {
    if (!text.startsWith(glyph)) continue
    node.dataset.iconCleaned = 'true'
    node.innerHTML = `${ICON[name]}<span data-stat-value>${text.slice(glyph.length).trim()}</span>`
    break
  }
}

function syncCampaignValues() {
  document.querySelectorAll('[data-campaign-stat]').forEach((node) => {
    const value = node.querySelector('[data-stat-value]')
    if (value && node.dataset.campaignStatValue !== undefined) value.textContent = node.dataset.campaignStatValue
  })
  document.querySelectorAll('.skill-icon[data-skill-shield]').forEach((node) => {
    const kind = node.dataset.skillShield !== 'none' ? 'shield' : 'book'
    if (node.dataset.skillIconKind === kind) return
    node.innerHTML = ICON[kind]
    node.dataset.skillIconKind = kind
  })
}

function cleanIcons() {
  document.querySelectorAll('.top-stats > span').forEach(replaceTopStat)

  document.querySelectorAll('.skill-icon').forEach((node) => {
    if (node.dataset.iconCleaned) return
    node.dataset.iconCleaned = 'true'
    node.innerHTML = node.textContent.includes('🛡') ? ICON.shield : ICON.book
  })
  syncCampaignValues()
}

function addShortcutHelp() {
  const screen = document.querySelector('.settings-screen')
  if (!screen || screen.querySelector('[data-shortcut-card]')) return
  const card = document.createElement('section')
  card.className = 'game-card shortcut-card'
  card.dataset.shortcutCard = 'true'
  card.innerHTML = `
    <div class="card-heading"><span>KEYBOARD SHORTCUTS</span><b>QOL</b></div>
    <div class="shortcut-grid">
      <div><kbd>Ctrl</kbd><span>+</span><kbd>S</kbd><strong>Save</strong></div>
      <div><kbd>Ctrl</kbd><span>+</span><kbd>Enter</kbd><strong>Run current file</strong></div>
      <div><kbd>Ctrl</kbd><span>+</span><kbd>Shift</kbd><span>+</span><kbd>Enter</kbd><strong>Submit recent run to PYR</strong></div>
      <div><kbd>Ctrl</kbd><span>+</span><kbd>Shift</kbd><span>+</span><kbd>P</kbd><strong>Command palette</strong></div>
      <div><kbd>Shift</kbd><span>+</span><kbd>Alt</kbd><span>+</span><kbd>F</kbd><strong>Pretty / format</strong></div>
      <div><kbd>Ctrl</kbd><span>+</span><kbd>\`</kbd><strong>Focus Forge terminal</strong></div>
      <div><kbd>Ctrl</kbd><span>+</span><kbd>Shift</kbd><span>+</span><kbd>\`</kbd><strong>Focus AI terminal</strong></div>
    </div>
    <p class="settings-note">Submit Run sends the recent visible Forge terminal output plus the active filename to whichever AI you launched from the right panel. PYR is reminded to stay read-only on project source and use tutor.py for examples.</p>
  `
  screen.appendChild(card)
}

function polish() {
  cleanIcons()
  addShortcutHelp()
}

let polishFrame = 0
const observer = new MutationObserver(() => {
  if (polishFrame) return
  polishFrame = requestAnimationFrame(() => {
    polishFrame = 0
    polish()
  })
})
observer.observe(document.documentElement, { subtree: true, childList: true })
window.addEventListener('load', polish)
window.addEventListener('questlab:campaign-updated', syncCampaignValues)
queueMicrotask(polish)
