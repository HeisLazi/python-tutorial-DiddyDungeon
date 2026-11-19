const $ = (selector) => document.querySelector(selector)
const arena = $('#arena')
const options = [...document.querySelectorAll('[data-answer]')]
const state = { hp: 84, maxHp: 100, resolve: 12, maxResolve: 18, turn: 1, selected: null, locked: false }
let timer
function render() {
  $('#hunter-value').textContent = `${state.hp} / ${state.maxHp}`
  $('#top-hp').textContent = state.hp
  $('#hunter-bar').style.width = `${100 * state.hp / state.maxHp}%`
  $('#enemy-value').textContent = `${state.resolve} / ${state.maxResolve}`
  $('#enemy-bar').style.width = `${100 * state.resolve / state.maxResolve}%`
  $('#turn').textContent = String(state.turn).padStart(2, '0')
  $('#submit').disabled = state.selected === null || state.locked || state.hp === 0 || state.resolve === 0
  options.forEach((option, index) => { option.setAttribute('aria-checked', String(index === state.selected)); option.disabled = state.locked })
}
options.forEach((option, index) => option.addEventListener('click', () => { state.selected = index; render() }))
$('#submit').addEventListener('click', () => {
  if (state.selected === null || state.locked || state.hp === 0 || state.resolve === 0) return
  const correct = state.selected === 1
  state.locked = true
  arena.classList.remove('attack', 'retaliate')
  void arena.offsetWidth
  arena.classList.add(correct ? 'attack' : 'retaliate')
  const damage = $('#damage')
  damage.className = `damage ${correct ? 'enemy-hit' : 'hunter-hit'}`
  damage.textContent = correct ? '−4' : '−12'
  $('#turn-label').textContent = correct ? 'TATE ATTACKS!' : 'THE WRAITH STRIKES!'
  const feedback = $('#feedback')
  feedback.className = `feedback ${correct ? 'correct' : 'incorrect'}`
  feedback.textContent = correct ? 'Correct! Tate strikes the wraith for 4 Resolve.' : 'Not quite. The wraith strikes Tate for 12 HP.'
  render()
  timer = setTimeout(() => {
    if (correct) state.resolve = Math.max(0, state.resolve - 4)
    else state.hp = Math.max(0, state.hp - 12)
    render()
  }, 360)
  setTimeout(() => {
    arena.classList.remove('attack', 'retaliate')
    state.turn += 1
    state.selected = null
    state.locked = false
    $('#turn-label').textContent = state.resolve === 0 ? 'ENEMY RESOLVE BROKEN' : state.hp === 0 ? 'HUNTER DOWN' : 'AWAITING YOUR ANSWER'
    if (state.resolve === 0) feedback.textContent = 'The wraith’s Resolve is broken. Reset to try again.'
    if (state.hp === 0) feedback.textContent = 'Tate is down. Reset to try again.'
    render()
  }, 1100)
})
$('#reset').addEventListener('click', () => { clearTimeout(timer); location.reload() })
const shapes = {
 sword: '<path fill="#171320" d="M9 0h4v35h5v4h-5v9H9v-9H4v-4h5z"/><path fill="#e1e6e8" d="M10 2h2v33h-2z"/><path fill="#8da6be" d="M12 6h1v28h-1z"/><path fill="#e9b75f" d="M5 35h12v3H5z"/><path fill="#744a30" d="M10 39h2v9h-2z"/>',
 spear: '<path fill="#171320" d="M11 0 16 9 13 14v34H9V14L6 9z"/><path fill="#e1e6e8" d="M11 2 14 9 11 13 8 9z"/><path fill="#b78348" d="M10 14h2v34h-2z"/>',
 dagger: '<path fill="#171320" d="M10 19h3v17h4v3h-4v9H9v-9H5v-3h5z"/><path fill="#e1e6e8" d="M11 21h1v15h-1z"/><path fill="#e9b75f" d="M6 36h10v2H6z"/><path fill="#80532f" d="M10 39h2v8h-2z"/>'
}
$('#weapon-select').addEventListener('change', (event) => { $('#weapon-art').innerHTML = shapes[event.target.value]; $('#weapon-label').textContent = event.target.selectedOptions[0].textContent })
render()

const locations = {
  crypt: { title: 'THE FORGOTTEN CRYPT', floor: 2, image: 'assets/crypt-v2.png' },
}
$('#location-select').addEventListener('change', (event) => {
  const location = locations[event.target.value]
  arena.style.backgroundImage = `url("${location.image}")`
  $('#location-title').textContent = location.title
  $('#room-tag').textContent = `FLOOR ${location.floor} · ENCOUNTER`
  $('#top-floor').textContent = `✦ FLOOR ${location.floor}`
  document.querySelector('.brief-top span:nth-child(2)').textContent = `FLOOR ${location.floor} · ROOM 4`
})
$('#enemy-scale').addEventListener('change', (event) => { arena.dataset.enemyScale = event.target.value })
