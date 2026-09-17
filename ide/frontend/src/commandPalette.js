const isVisible = (element) => Boolean(element && element.offsetParent !== null)
const buttons = () => [...document.querySelectorAll('button')]
const byText = (text) => buttons().find((button) => isVisible(button) && button.textContent.trim() === text)

function clickText(text) {
  byText(text)?.click()
}

function clickRail(label) {
  document.querySelector(`.activity-button[aria-label="${label}"]`)?.click()
}

function focusXterm(selector) {
  document.querySelector(`${selector} .xterm-helper-textarea`)?.focus()
}

const commands = [
  { label: 'Run current file', keys: 'Ctrl+Enter', run: () => document.querySelector('.editor-panel .toolbar-actions button.primary')?.click() },
  { label: 'Save current file', keys: 'Ctrl+S', run: () => (byText('Save Tutor') || byText('Save'))?.click() },
  { label: 'Pretty / format', keys: 'Shift+Alt+F', run: () => clickText('Pretty') },
  { label: 'Submit recent run to PYR', keys: 'Ctrl+Shift+Enter', run: () => document.querySelector('[data-qol-submit]')?.click() },
  { label: 'Open Forge', run: () => clickRail('Forge') },
  { label: 'Open Tutor Notebook', run: () => clickRail('Tutor Notebook') },
  { label: 'Open Codex', run: () => clickRail('Codex') },
  { label: 'Open Character', run: () => clickRail('Character') },
  { label: 'Open Homestead', run: () => clickRail('Homestead') },
  { label: 'Open Settings', run: () => clickRail('Settings') },
  { label: 'Focus Forge terminal', keys: 'Ctrl+`', run: () => focusXterm('.terminal-panel') },
  { label: 'Focus AI terminal', keys: 'Ctrl+Shift+`', run: () => focusXterm('.ai-panel') },
  { label: 'Launch Codex CLI', run: () => clickText('Codex') },
  { label: 'Launch Claude CLI', run: () => clickText('Claude') },
  { label: 'Launch AGY CLI', run: () => clickText('AGY') },
  { label: 'Reconnect Forge terminal', run: () => {
      const button = buttons().find((candidate) => isVisible(candidate) && /reconnect/i.test(candidate.textContent) && candidate.closest('.terminal-panel'))
      button?.click()
    }
  },
  { label: 'Reconnect AI terminal', run: () => {
      const button = buttons().find((candidate) => isVisible(candidate) && /reconnect/i.test(candidate.textContent) && candidate.closest('.ai-panel'))
      button?.click()
    }
  },
]

let palette = null
let filtered = commands
let selected = 0

function closePalette() {
  palette?.remove()
  palette = null
}

function renderList() {
  if (!palette) return
  const list = palette.querySelector('.command-palette-list')
  list.innerHTML = ''
  filtered.forEach((command, index) => {
    const row = document.createElement('button')
    row.className = `command-palette-row ${index === selected ? 'selected' : ''}`
    row.innerHTML = `<span>${command.label}</span>${command.keys ? `<kbd>${command.keys}</kbd>` : ''}`
    row.addEventListener('mouseenter', () => {
      selected = index
      renderList()
    })
    row.addEventListener('click', () => execute(index))
    list.appendChild(row)
  })
}

function execute(index = selected) {
  const command = filtered[index]
  if (!command) return
  closePalette()
  requestAnimationFrame(command.run)
}

function openPalette() {
  if (palette) {
    palette.querySelector('input')?.focus()
    return
  }

  palette = document.createElement('div')
  palette.className = 'command-palette-backdrop'
  palette.innerHTML = `
    <div class="command-palette" role="dialog" aria-label="Forge command palette">
      <div class="command-palette-title"><span>FORGE COMMANDS</span><kbd>Esc</kbd></div>
      <input type="text" placeholder="Type a command…" autocomplete="off" spellcheck="false" />
      <div class="command-palette-list"></div>
    </div>
  `
  palette.addEventListener('mousedown', (event) => {
    if (event.target === palette) closePalette()
  })
  document.body.appendChild(palette)

  const input = palette.querySelector('input')
  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase()
    filtered = commands.filter((command) => command.label.toLowerCase().includes(query))
    selected = 0
    renderList()
  })
  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      selected = Math.min(selected + 1, filtered.length - 1)
      renderList()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      selected = Math.max(selected - 1, 0)
      renderList()
    } else if (event.key === 'Enter') {
      event.preventDefault()
      execute()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      closePalette()
    }
  })

  filtered = commands
  selected = 0
  renderList()
  requestAnimationFrame(() => input.focus())
}

window.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'p') {
    event.preventDefault()
    openPalette()
    return
  }
  if (event.key === 'Escape' && palette) closePalette()
})
