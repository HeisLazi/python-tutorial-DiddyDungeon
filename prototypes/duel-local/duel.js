const chains = {
  potion: { name:'Potion shop', starter:'', steps:[
    { title:'Can you afford it?', prompt:'Write can_buy(balance, price). Return True when the balance covers the price, otherwise return False.', baseline:'def can_buy(balance, price):\n    return balance >= price\n' },
    { title:'Make the purchase', prompt:'Add buy_potion(balance, price). Use can_buy: return the remaining balance after a purchase, or the unchanged balance if it cannot be afforded.', baseline:'def can_buy(balance, price):\n    return balance >= price\n\ndef buy_potion(balance, price):\n    if can_buy(balance, price):\n        return balance - price\n    return balance\n' },
    { title:'Close the loophole', prompt:'A negative price would add coins. Update buy_potion so a negative price leaves the balance unchanged. Normal purchases must still work.', baseline:'' },
  ]},
  chest: { name:'Broken treasure chest', starter:'def chest_reward(gold, reward):\n    return gold - reward\n', steps:[
    { title:'Find the bug', prompt:'The chest subtracts your reward instead of adding it. Fix chest_reward(gold, reward) so it returns the new total.', baseline:'def chest_reward(gold, reward):\n    return gold + reward\n' },
    { title:'Locked chest', prompt:'Add an opened parameter to chest_reward(gold, reward, opened). A closed chest leaves gold unchanged; an open chest adds the reward.', baseline:'def chest_reward(gold, reward, opened):\n    if opened:\n        return gold + reward\n    return gold\n' },
    { title:'Collect the chests', prompt:'Add collect_chests(gold, chests). Each entry is a (reward, opened) pair. Use chest_reward to calculate the final gold after every chest.', baseline:'' },
  ]},
};
const $ = id => document.getElementById(id);
let state = null;
let roomSession = null;
let applyingRoomResult = false;
const ROUND_SECONDS = 180;
let clockHandle = null;
function stopClock() { clearInterval(clockHandle); clockHandle = null; }
function renderClock(seconds) {
  const remaining = Math.max(0, Math.ceil(seconds));
  $('timer-label').textContent = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
  $('timer-bar').style.width = `${Math.max(0, seconds / ROUND_SECONDS * 100)}%`;
  $('timer-bar').classList.toggle('low', seconds <= 30);
  $('timer-track').setAttribute('aria-valuenow', String(remaining));
}
function startClock(seconds = ROUND_SECONDS) {
  stopClock();
  const match = state;
  match.remaining = seconds;
  match.deadline = performance.now() + seconds * 1000;
  renderClock(seconds);
  clockHandle = setInterval(() => {
    if (state !== match || match.done) { stopClock(); return; }
    match.remaining = Math.max(0, (match.deadline - performance.now()) / 1000);
    renderClock(match.remaining);
    if (match.remaining <= 0) {
      stopClock();
      resolveRound(false, 'Time is up. A working baseline is available for the next challenge.');
    }
  }, 200);
}
function refreshStances(enabled) {
  document.querySelectorAll('[data-stance]').forEach(button => {
    button.disabled = !enabled;
    button.setAttribute('aria-pressed', String(button.dataset.stance === state.stance));
  });
  $('focus-status').textContent = `FOCUS: ${state.focus}`;
}
function updateBars() {
  $('hp').textContent = `${state.hp} / 100`;
  $('enemyhp').textContent = `${state.enemy} / 100`;
  $('hpbar').style.width = state.hp + '%';
  $('enemybar').style.width = state.enemy + '%';
}
function showStep() {
  const step = chains[state.chain].steps[state.step];
  $('step').textContent = `${chains[state.chain].name.toUpperCase()} · CHALLENGE ${state.step + 1} / 3`;
  $('title').textContent = step.title;
  $('prompt').textContent = step.prompt;
  $('code').disabled = false;
  $('code').readOnly = false;
  $('submit').disabled = false;
  $('run').disabled = false;
  $('next').hidden = true;
  $('feedback').textContent = '';
  refreshStances(true);
  startClock();
}
function start(chain) {
  stopClock();
  queuedTurns = [];
  sendScene(arenaBase);
  state = {chain, step: 0, hp: 100, enemy: 100, bonus: false, done: false, log: [], stance: 'attack', focus: 0};
  $('code').value = chains[chain].starter;
  $('bonus').style.display = 'none';
  $('history').hidden = true;
  $('log').replaceChildren();
  $('result').textContent = '';
  $('baseline').hidden = true;
  $('editorhint').textContent = 'Local scratch editor';
  $('combat').textContent = 'Three exchanges. Your rival is a scripted training opponent.';
  updateBars();
  showStep();
}
let sceneReady = false;
let queuedTurns = [];
const arenaBase = {simulated:false, region:'duel-colosseum', enemy:'duel-rival', style:'sword', armorLook:'classic'};
function sendScene(payload) {
  if (!sceneReady) { if (payload.turn_id) queuedTurns.push(payload); return; }
  try { $('combat-frame').contentWindow.diddyCombatReceive(JSON.stringify(payload)); } catch { /* loading */ }
}
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== $('combat-frame').contentWindow || event.data?.source !== 'diddy-combat' || event.data?.type !== 'ready') return;
  sceneReady = true;
  $('scene-loading').hidden = true;
  sendScene(arenaBase);
  for (const turn of queuedTurns) sendScene(turn);
  queuedTurns = [];
});
function recordRound(passed, rival, dealt, taken) {
  const entry = document.createElement('li');
  entry.textContent = `${chains[state.chain].steps[state.step].title}: ${passed ? 'checks passed' : 'checks missed'} · dealt ${dealt}, took ${taken}`;
  $('log').append(entry);
  $('history').hidden = false;
  state.log.push({passed, rival, dealt, taken});
}
document.querySelectorAll('[data-chain]').forEach(button => button.addEventListener('click', () => { if (roomSession) { $('room-status').textContent = 'Reload to leave the local room.'; return; } start(button.dataset.chain); }));
document.querySelectorAll('[data-stance]').forEach(button => button.addEventListener('click', () => {
  if (!state || state.done || $('code').readOnly) return;
  state.stance = button.dataset.stance;
  refreshStances(true);
}));
function resolveRound(passed, feedback) {
  if (roomSession && !applyingRoomResult) { submitRoomResult(passed, feedback); return; }
  stopClock();
  const rr = roomSession && applyingRoomResult ? roomSession.result : null;
  const rival = rr ? rr.opponent_passed : [true, false, true][state.step];
  let dealt = rr ? rr.dealt : passed ? (rival ? 20 : 30) : 0;
  let taken = rr ? rr.taken : rival ? (passed ? 20 : 30) : 0;
  if (!rr && passed) {
    dealt += state.focus;
    state.focus = 0;
    if (state.stance === 'attack') dealt += 10;
    if (state.stance === 'focus') state.focus = 10;
  }
  if (!rr && state.stance === 'guard') taken = Math.max(0, taken - 10);
  state.enemy = Math.max(0, state.enemy - dealt);
  state.hp = Math.max(0, state.hp - taken);
  updateBars();
  if (passed || rival) sendScene({...arenaBase, turn_id: `${Date.now()}-${state.step}`, outcome: passed && rival ? 'both' : passed ? 'correct' : 'incorrect'});
  recordRound(passed, rival, dealt, taken);
  state.passed = passed;
  $('code').readOnly = true;
  $('submit').disabled = true;
  $('run').disabled = true;
  refreshStances(false);
  $('feedback').textContent = feedback;
  $('combat').textContent = passed ? (rival ? 'Both hunters land a hit.' : 'Your hunter lands a clean hit!') : (rival ? 'Your rival attacks. A working baseline is available for the next step.' : 'Neither hunter lands a hit.');
  if (state.step === 2 || state.hp === 0 || state.enemy === 0) {
    state.done = true;
    $('next').hidden = true;
    const outcome = state.hp === state.enemy ? 'Draw' : state.hp > state.enemy ? 'Victory' : 'Defeat';
    $('result').className = 'outcome';
    $('result').textContent = `${outcome} · Your hunter ${state.hp} HP · Rival ${state.enemy} HP. Choose a chain to play again.`;
    $('feedback').textContent += ' Duel complete.';
  } else {
    $('next').hidden = false;
    if (!roomSession && state.step === 0) { $('bonus').style.display = 'block'; $('next').disabled = true; }
  }
}
$('submit').addEventListener('click', async () => {
  if (!state || state.done || $('code').readOnly) return;
  const currentMatch = state;
  const remaining = Math.max(0, (state.deadline - performance.now()) / 1000);
  if (remaining <= 0) { resolveRound(false, 'Time is up.'); return; }
  stopClock();
  $('submit').disabled = true;
  $('run').disabled = true;
  refreshStances(false);
  $('feedback').textContent = 'Checking your code…';
  try {
    const response = await fetch('/check', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chain:state.chain, step:state.step, code:$('code').value})});
    if (!response.ok) throw Error('Checker unavailable');
    const result = await response.json();
    if (state !== currentMatch) return;
    resolveRound(result.passed, result.feedback);
  } catch {
    if (state !== currentMatch) return;
    $('feedback').textContent = 'Could not reach the local checker. Start the prototype server and try again.';
    $('submit').disabled = false;
    $('run').disabled = false;
    refreshStances(true);
    startClock(remaining);
  }
});
document.querySelectorAll('[data-answer]').forEach(button => button.addEventListener('click', () => {
  if (!state || state.bonus) return;
  state.bonus = true;
  if (button.dataset.answer === 'true') {
    state.hp = Math.min(100, state.hp + 10);
    $('combat').textContent = 'Correct! Your hunter recovers 10 HP.';
  } else $('combat').textContent = 'Not quite: functions can call other functions. No damage taken.';
  updateBars();
  $('bonus').style.display = 'none';
  $('next').disabled = false;
}));
$('next').addEventListener('click', () => {
  if (roomSession) { readyRoom(); return; }
  if (!state.passed) {
    $('code').value = chains[state.chain].steps[state.step].baseline;
    $('editorhint').textContent = 'Recovery baseline';
    $('baseline').textContent = 'The previous step was missed, so this working example replaces your last answer. Read it before building the next step.';
    $('baseline').hidden = false;
  } else {
    $('editorhint').textContent = 'Your code carries forward';
    $('baseline').hidden = true;
  }
  state.step++;
  showStep();
});
$('code').addEventListener('keydown', event => {
  if (event.key === 'Tab') {
    event.preventDefault();
    event.target.setRangeText('    ', event.target.selectionStart, event.target.selectionEnd, 'end');
  }
});

$('run').addEventListener('click', async () => {
  if (!state || state.done || $('code').readOnly) return;
  const match = state;
  $('run').disabled = true;
  $('output').textContent = 'Running…';
  try {
    const response = await fetch('/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code:$('code').value, stdin:$('stdin').value})});
    if (!response.ok) throw Error('Runner unavailable');
    const result = await response.json();
    if (state !== match) return;
    $('output').textContent = result.output + (result.exit_code ? `\nProcess exited with code ${result.exit_code}.` : '');
  } catch {
    if (state === match) $('output').textContent = 'Could not reach the local runner. Restart the preview server.';
  } finally {
    if (state === match && !state.done && !$('code').readOnly) $('run').disabled = false;
  }
});

async function roomCall(action, data) {
  const response = await fetch(`/room/${action}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Room request failed');
  return result;
}
function roomAuth() { return {code:roomSession.code, token:roomSession.token}; }
function beginRoom(result) {
  roomSession = {code:result.room.code, token:result.token, seenResult:-1, step:-1, polling:false};
  $('room-code').value = result.room.code;
  $('room-create').disabled = true;
  $('room-join').disabled = true;
  document.querySelectorAll('[data-chain]').forEach(button => button.disabled = true);
  $('room-status').textContent = `Room ${roomSession.code} · waiting for another hunter on this computer`;
  pollRoom();
  roomSession.interval = setInterval(pollRoom, 1000);
}
$('room-create').addEventListener('click', async () => {
  try { beginRoom(await roomCall('create', {name:$('room-name').value, chain:$('room-chain').value})); }
  catch (error) { $('room-status').textContent = error.message; }
});
$('room-join').addEventListener('click', async () => {
  try { beginRoom(await roomCall('join', {name:$('room-name').value, code:$('room-code').value})); }
  catch (error) { $('room-status').textContent = error.message; }
});
async function pollRoom() {
  if (!roomSession || roomSession.polling) return;
  const session = roomSession;
  session.polling = true;
  try {
    const {room} = await roomCall('state', roomAuth());
    if (roomSession !== session) return;
    if (!room.opponent) { $('room-status').textContent = `Room ${room.code} · waiting for your opponent`; return; }
    $('room-status').textContent = `Room ${room.code} · ${room.you.name} vs ${room.opponent.name} · ${room.phase === 'playing' ? (room.you.submitted ? 'waiting for opponent' : 'coding') : room.phase}`;
    if (session.step < 0) {
      start(room.chain);
      session.step = 0;
      $('combat').textContent = `Duel against ${room.opponent.name}. Both players answer before the exchange resolves.`;
    }
    if (room.phase === 'playing' && room.step > session.step) {
      if (!state.passed) {
        $('code').value = chains[state.chain].steps[state.step].baseline;
        $('editorhint').textContent = 'Recovery baseline';
        $('baseline').hidden = false;
        $('baseline').textContent = 'The previous step was missed. Read this working example before continuing.';
      } else { $('baseline').hidden = true; $('editorhint').textContent = 'Your code carries forward'; }
      session.step = state.step = room.step;
      state.focus = room.you.focus;
      showStep();
    }
    if ((room.phase === 'result' || room.phase === 'finished') && room.result && session.seenResult !== room.step) {
      session.seenResult = room.step;
      session.result = room.result;
      applyingRoomResult = true;
      resolveRound(room.result.passed, room.result.passed ? 'Your checks passed.' : 'Your checks did not pass.');
      applyingRoomResult = false;
      state.hp = room.you.hp;
      state.enemy = room.opponent.hp;
      state.focus = room.you.focus;
      updateBars();
      refreshStances(false);
      if (room.phase === 'finished' && !state.done) {
        state.done = true;
        $('next').hidden = true;
        $('result').className = 'outcome';
        $('result').textContent = `${state.hp === state.enemy ? 'Draw' : state.hp > state.enemy ? 'Victory' : 'Defeat'} · ${state.hp} HP / ${state.enemy} HP`;
      }
      if (room.phase === 'result') { $('next').disabled = room.you.ready; $('next').textContent = room.you.ready ? 'Waiting for opponent…' : 'Ready for next challenge →'; }
    }
  } catch (error) { $('room-status').textContent = `Room connection: ${error.message}`; }
  finally { session.polling = false; }
}
async function submitRoomResult(passed, feedback) {
  stopClock();
  $('code').readOnly = true;
  $('submit').disabled = $('run').disabled = true;
  refreshStances(false);
  $('feedback').textContent = `${feedback} Waiting for your opponent…`;
  try {
    await roomCall('submit', {...roomAuth(), step:state.step, passed, stance:state.stance});
    pollRoom();
  } catch (error) {
    $('feedback').textContent = `Could not submit: ${error.message}. Your local answer has been kept.`;
  }
}
async function readyRoom() {
  $('next').disabled = true;
  $('next').textContent = 'Waiting for opponent…';
  try { await roomCall('ready', {...roomAuth(), step:state.step}); pollRoom(); }
  catch (error) { $('feedback').textContent = error.message; $('next').disabled = false; }
}
