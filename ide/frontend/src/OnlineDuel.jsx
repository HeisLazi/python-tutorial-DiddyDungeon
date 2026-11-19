import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { onlineDuel as defaultOnlineDuel, onlineDuelsConfigured as defaultOnlineDuelsConfigured } from './cloud/onlineDuel.js'
import { hunterAppearance } from './hunterEquipment.js'
import { combatWeaponVariant } from './combatWeaponArt.js'
import { clearDuelRecovery, duelRecoveryKey, readDuelRecovery, writeDuelRecovery } from './cloud/duelRecovery.js'
import './onlineDuel.css'

export default function OnlineDuel({ groupId, userId, visitors, onClose, duelClient = defaultOnlineDuel, configured = defaultOnlineDuelsConfigured }) {
  const onlineDuel = duelClient
  const onlineDuelsConfigured = configured
  const recoveryKey = duelRecoveryKey(userId, groupId)
  const [recovery] = useState(() => readDuelRecovery(recoveryKey))
  const [opponent, setOpponent] = useState('')
  const [chain, setChain] = useState('basic')
  const [choice, setChoice] = useState(null)
  const [mode, setMode] = useState('fair')
  const [catalog, setCatalog] = useState(null)
  const [selection, setSelection] = useState({weapon:'', armor:'', trinket:'', weapon_appearance:'', armor_appearance:''})
  const [pending, setPending] = useState([])
  const [recoverable, setRecoverable] = useState([])
  const [invitation, setInvitation] = useState(recovery?.invitation || '')
  const [matchId, setMatchId] = useState(recovery?.matchId || '')
  const [match, setMatch] = useState(null)
  const [code, setCode] = useState(recovery?.code || '')
  const [stdin, setStdin] = useState(recovery?.stdin || '')
  const [output, setOutput] = useState('Run your code to try it before submitting.')
  const [running, setRunning] = useState(false)
  const [stance, setStance] = useState('attack')
  const [bonusAnswer, setBonusAnswer] = useState(null)
  const [bonusReward, setBonusReward] = useState('heal')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [clock, setClock] = useState(Date.now())
  const frame = useRef(null)
  const frameReady = useRef(false)
  const sceneState = useRef({ simulated:false, region:'duel-colosseum', enemy:'duel-rival', style:'sword', armorLook:'classic' })
  const lastRound = useRef(recovery?.round ?? -1)
  const lastAnimation = useRef('')
  const pendingRef = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => {
    writeDuelRecovery(recoveryKey, {matchId, invitation, code, stdin, round:lastRound.current})
  }, [recoveryKey, matchId, invitation, code, stdin, match?.round])
  useEffect(() => {
    const tick = setInterval(() => setClock(Date.now()), 250)
    return () => clearInterval(tick)
  }, [])
  const sendScene = payload => {
    try { if (frameReady.current) frame.current?.contentWindow?.diddyCombatReceive?.(JSON.stringify(payload)) } catch { /* scene is loading */ }
  }
  useEffect(() => {
    function message(event) {
      if (event.origin !== window.location.origin || event.source !== frame.current?.contentWindow || event.data?.source !== 'diddy-combat' || event.data?.type !== 'ready') return
      frameReady.current = true
      sendScene(sceneState.current)
    }
    window.addEventListener('message', message)
    return () => window.removeEventListener('message', message)
  }, [])
  useEffect(() => {
    if (!onlineDuelsConfigured || matchId) return undefined
    let active = true
    async function poll() {
      if (pendingRef.current) return
      pendingRef.current = true
      try {
        const [incoming, sent, resumed] = await Promise.all([
          onlineDuel.pending(groupId),
          invitation ? onlineDuel.invitation(groupId, invitation) : Promise.resolve(null),
          onlineDuel.recoverable(groupId),
        ])
        if (!active) return
        setNotice(current => current === 'The duel service is unavailable.' ? '' : current)
        setPending(incoming.invitations || [])
        setRecoverable(resumed.matches || [])
        if (sent?.match_id) { setMatchId(sent.match_id); setInvitation(''); setNotice('Your challenge was accepted.') }
        else if (sent?.expired) { setInvitation(''); setNotice('The challenge expired.') }
      } catch { if (active) setNotice('The duel service is unavailable.') }
      finally { pendingRef.current = false }
    }
    void poll()
    const id = setInterval(poll, 3000)
    return () => { active = false; clearInterval(id) }
  }, [groupId, invitation, matchId])
  useEffect(() => {
    if (!matchId) return undefined
    let active = true, working = false
    async function poll() {
      if (working) return
      working = true
      try {
        const next = await onlineDuel.match(groupId, matchId)
        if (!active) return
        setNotice(current => current === 'Connection interrupted. Reconnecting to the match…' ? '' : current)
        const offset = next.server_now * 1000 - Date.now()
        setMatch({ ...next, clockOffset:offset })
        if (next.you.loadout && next.phase === 'loadout') {
          setSelection({ weapon:next.you.loadout.weapon?.id || '', armor:next.you.loadout.armor?.id || '', trinket:next.you.loadout.trinket?.id || '', weapon_appearance:next.you.loadout.appearances?.weapon?.id || '', armor_appearance:next.you.loadout.appearances?.armor?.id || '' })
        }
        if (next.you.loadout && next.opponent.loadout) {
          const own = next.you.loadout, rival = next.opponent.loadout
          const ownLook = hunterAppearance(own.armor?.name, own.trinket?.name)
          const rivalLook = hunterAppearance(rival.armor?.name, rival.trinket?.name)
          sceneState.current = { ...sceneState.current, armorLook:ownLook.armorLook,
            style:own.weapon?.combat_style || 'unarmed', weaponId:own.weapon?.id || '', weaponVariant:own.weapon?.id === 'hunter-gravebound-greatblade' ? 'graveblade' : combatWeaponVariant(own.weapon?.name),
            armorMastery:own.appearances?.armor?.tier || '', weaponMastery:own.appearances?.weapon?.tier || '',
            rivalArmorLook:rivalLook.armorLook, rivalStyle:rival.weapon?.combat_style || 'unarmed', rivalWeaponId:rival.weapon?.id || '',
            rivalWeaponVariant:rival.weapon?.id === 'hunter-gravebound-greatblade' ? 'graveblade' : combatWeaponVariant(rival.weapon?.name),
            rivalArmorMastery:rival.appearances?.armor?.tier || '', rivalWeaponMastery:rival.appearances?.weapon?.tier || '' }
          sendScene(sceneState.current)
        }
        if (next.round !== lastRound.current) {
          lastRound.current = next.round
          // An empty baseline means there is nothing to restore; keep the editor as it is.
          // A standalone step (`fresh`) always opens on its own starter.
          setCode(current => next.challenge.recovery_baseline || (next.round === 0 || next.challenge.fresh ? next.challenge.starter : current))
          setChoice(null)
        }
        if (next.exchange) {
          const key = `${matchId}-${next.round}`
          if (key !== lastAnimation.current) {
            lastAnimation.current = key
            const result = next.exchange
            const outcome = result.passed && result.opponent_passed ? 'both' : result.passed ? 'correct' : result.opponent_passed ? 'incorrect' : ''
            if (outcome) { sceneState.current = { ...sceneState.current, turn_id:key, outcome }; sendScene(sceneState.current) }
          }
        }
      } catch (error) {
        if (!active) return
        if (error?.status === 404) {
          clearDuelRecovery(recoveryKey)
          setMatchId('')
          setMatch(null)
          setNotice('That saved duel is no longer active. Choose another duel from the lobby.')
        } else if (error?.status === 401) {
          setNotice('Your Quest Lab session expired. Sign in again to reconnect to this duel.')
        } else {
          setNotice('Connection interrupted. Reconnecting to the match…')
        }
      }
      finally { working = false }
    }
    void poll()
    const id = setInterval(poll, 1500)
    return () => { active = false; clearInterval(id) }
  }, [groupId, matchId, recoveryKey])
  useEffect(() => {
    if (!matchId || match?.phase !== 'loadout' || catalog) return undefined
    let active = true
    onlineDuel.catalog(groupId, match.mode).then(result => { if (active) setCatalog(result) }).catch(() => { if (active) setNotice('Could not load the equipment catalog.') })
    return () => { active = false }
  }, [groupId, matchId, match?.phase, catalog])
  async function action(fn) {
    if (busy) return
    setBusy(true); setNotice('')
    try { await fn() } catch (error) { if (mounted.current) setNotice(error?.message || 'The duel service is unavailable.') } finally { if (mounted.current) setBusy(false) }
  }
  async function runPractice() {
    if (running || !match || match.phase !== 'coding' || match.you.submitted || !code.trim()) return
    const round = match.round
    setRunning(true); setOutput('Running in the isolated practice environment…')
    try {
      const result = await onlineDuel.practice(groupId, matchId, code, stdin)
      if (!mounted.current || lastRound.current !== round) return
      const suffix = result.reason === 'timeout' ? '\nStopped after the time limit.' : result.reason === 'output_limit' ? '\nOutput limit reached.' : result.exit_code ? `\nProgram exited with code ${result.exit_code}.` : ''
      setOutput((result.output || '(No output. Use print(...) to show a result.)') + suffix)
    } catch (error) { if (mounted.current && lastRound.current === round) setOutput(error?.message || 'Practice runner unavailable.') }
    finally { if (mounted.current) setRunning(false) }
  }
  const seconds = match ? Math.max(0, Math.ceil(match.deadline - (clock + match.clockOffset) / 1000)) : 0
  const duration = match?.phase === 'bonus'
    ? (match.bonus_question?.duration_seconds || 30)
    : match?.phase === 'exchange'
      ? 60
      : (match?.challenge?.duration_seconds || 180)
  const timeText = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  const status = match?.phase === 'aborted' ? 'The duel was cancelled. No result was recorded.' : match?.phase === 'finished' ? `${match.you.hp === match.opponent.hp ? 'Draw' : match.you.hp > match.opponent.hp ? 'Victory' : 'Defeat'} · ${match.settlement === 'pending' ? 'Ladder update pending.' : match.settlement === 'settled' ? 'Ladder updated.' : 'No ranked result.'}` : match?.phase === 'exchange' ? 'Exchange resolved. Both hunters must be ready for the next challenge.' : match?.you?.submitted ? 'Answer locked. Waiting for the other hunter and the evaluator.' : 'Write your answer before the timer finishes.'
  const setLoadoutField = (field, value) => setSelection(current => ({ ...current, [field]:value }))
  const back = () => {
    if (matchId && (!match || !['finished', 'aborted'].includes(match.phase))) return action(async () => { await onlineDuel.cancel(groupId, matchId); clearDuelRecovery(recoveryKey); onClose() })
    if (invitation && !matchId) return action(async () => {
      // An opponent may accept while the host is leaving: discover and cancel
      // that match instead of leaving them stranded.
      const current = await onlineDuel.invitation(groupId, invitation)
      if (current.match_id) await onlineDuel.cancel(groupId, current.match_id)
      else await onlineDuel.withdraw(groupId, invitation)
      clearDuelRecovery(recoveryKey); onClose()
    })
    clearDuelRecovery(recoveryKey)
    onClose()
  }
  const invite = () => action(async () => {
    if (!opponent) throw new Error('Pick a friend who is online first.')
    const result = await onlineDuel.invite(groupId, opponent, chain, mode)
    setInvitation(result.invite_id)
    setNotice('Challenge sent. Waiting for your friend to accept.')
  })
  const accept = inviteId => action(async () => {
    const result = await onlineDuel.accept(groupId, inviteId)
    setMatchId(result.match_id)
    setInvitation('')
    setNotice('Challenge accepted. Choose your loadout.')
  })
  const resume = item => action(async () => {
    setMatchId(item.match_id)
    setNotice('Rejoining your saved duel…')
  })
  const lockLoadout = () => action(async () => {
    await onlineDuel.loadout(groupId, matchId, selection)
    setNotice('Loadout locked. Waiting for your opponent.')
  })
  const submitCode = () => action(async () => {
    const asking = match?.challenge?.kind === 'choice'
    await onlineDuel.submit(groupId, matchId, asking ? '' : code, stance, asking ? choice : undefined)
    setNotice('Answer submitted. The evaluator is checking it.')
  })
  const lockBonus = () => action(async () => {
    await onlineDuel.bonus(groupId, matchId, bonusAnswer, bonusReward)
    setNotice('Bonus answer locked. Waiting for your opponent.')
  })
  const ready = () => action(async () => {
    await onlineDuel.ready(groupId, matchId)
    setNotice('Ready. Waiting for your opponent.')
  })
  const names = new Map((visitors || []).map(visitor => [visitor.id, visitor.name || 'Friend']))
  const modeText = mode === 'friendly'
    ? 'Friendly · choose any gear; its duel effects apply only in this match.'
    : mode === 'geared'
      ? 'Ranked · only server-verified owned gear is allowed; results update your group ladder.'
      : 'Unranked · both hunters use equal combat stats.'
  const outcomeText = match?.exchange
    ? match.exchange.passed && match.exchange.opponent_passed
      ? 'Both hunters solved it. The exchange is even.'
      : match.exchange.passed
        ? 'Correct answer. You landed the hit.'
        : match.exchange.opponent_passed
          ? 'Your opponent solved it and landed the hit.'
          : 'Neither answer passed, so no damage was dealt.'
    : ''
  const stanceName = value => ({ attack:'Attack', guard:'Guard', focus:'Focus' }[value] || '')
  const exchangeDetail = ex => {
    if (!ex) return ''
    const parts = [`You dealt ${ex.dealt ?? 0}`, `took ${ex.taken ?? 0}`]
    if (ex.healed > 0) parts.push(`healed ${ex.healed}`)
    const notes = []
    if (ex.stance) notes.push(`Your stance: ${stanceName(ex.stance)}${ex.stance === 'focus' && ex.passed ? ' (+10 on your next hit)' : ''}`)
    if (ex.opponent_stance) notes.push(`Rival: ${stanceName(ex.opponent_stance)}`)
    if (ex.blocked > 0) notes.push(`you blocked ${ex.blocked}`)
    if (ex.rival_blocked > 0) notes.push(`rival blocked ${ex.rival_blocked}`)
    return `${parts.join(' · ')}.${notes.length ? ` ${notes.join(' · ')}.` : ''}`
  }
  const exchangeSummary = match?.exchange ? `${outcomeText} ${exchangeDetail(match.exchange)}` : ''
  const isChoice = match?.challenge?.kind === 'choice'
  const canEdit = match?.phase === 'coding' && !match.you?.submitted && seconds > 0
  const timePercent = Math.max(0, Math.min(100, (seconds / Math.max(1, duration)) * 100))
  const hp = value => Math.max(0, Math.min(100, Number(value) || 0))
  const catalogItems = slot => catalog?.catalog?.[slot] || []
  const equipmentBonus = (slot, id) => {
    if (match?.mode !== 'friendly' || !id) return ''
    const item = catalogItems(slot).find(entry => entry.id === id)
    const bonus = item?.duel_bonus
    if (!bonus) return ''
    return [bonus.damage && `+${bonus.damage} attack`, bonus.guard && `−${bonus.guard} damage taken`, bonus.heal && `+${bonus.heal} HP on a correct answer`].filter(Boolean).join(' · ') || 'No duel effect'
  }

  return <section className="online-duel" aria-label="Online coding duel">
    <header>
      <div><span>PRIVATE MATCH · COLOSSEUM</span><h2>Colosseum</h2></div>
      <button type="button" className="campaign-button ghost" disabled={busy} onClick={back}>
        {matchId && (!match || !['finished', 'aborted'].includes(match.phase)) ? 'Cancel duel & return' : invitation ? 'Withdraw challenge & return' : 'Back to PvP menu'}
      </button>
    </header>
    {notice && <p className="online-duel-error" role="status">{notice}</p>}
    {!onlineDuelsConfigured && <p className="online-duel-error" role="status">Online duels are not configured on this installation.</p>}

    {!matchId && <div className="online-duel-lobby">
      <h3>Challenge a friend</h3>
      <p>Pick a friend who is online, choose a difficulty, then duel in the arena. Your friend accepts under “Challenges for you”.</p>
      <label htmlFor="duel-opponent">Opponent</label>
      <select id="duel-opponent" value={opponent} disabled={busy || !onlineDuelsConfigured} onChange={event => setOpponent(event.target.value)}>
        <option value="">{visitors?.length ? 'Choose a friend' : 'No friends are in the house yet'}</option>
        {(visitors || []).filter(visitor => visitor.id !== userId).map(visitor => <option key={visitor.id} value={visitor.id}>{visitor.name || 'Friend'}</option>)}
      </select>
      <label htmlFor="duel-mode">Match mode</label>
      <select id="duel-mode" value={mode} disabled={busy || !onlineDuelsConfigured} onChange={event => setMode(event.target.value)}>
        <option value="fair">Unranked · equal stats</option>
        <option value="friendly">Friendly · choose any gear</option>
        <option value="geared">Ranked · verified owned gear</option>
      </select>
      <p className="online-duel-mode-note">{modeText}</p>
      <label htmlFor="duel-chain">Difficulty</label>
      <select id="duel-chain" value={chain} disabled={busy || !onlineDuelsConfigured} onChange={event => setChain(event.target.value)}>
        <optgroup label="Difficulty">
          <option value="basic">Basic · quick questions and tiny coding tasks</option>
          <option value="normal">Normal · lists, dictionaries and small classes</option>
          <option value="advanced">Advanced · build a mini poker game, then face an interview question</option>
        </optgroup>
        <optgroup label="Fun modes">
          <option value="bughunt">Bug Hunt · spot the bug, then fix it</option>
          <option value="oracle">Output Oracle · predict what the code prints</option>
        </optgroup>
      </select>
      <button type="button" className="campaign-button" disabled={busy || !onlineDuelsConfigured || !opponent} onClick={invite}>Send challenge</button>
      {invitation && <p role="status">Challenge sent. It expires after five minutes; you can withdraw it above.</p>}
      <RecoverableDuels matches={recoverable} names={names} busy={busy} onResume={resume} />
      <section className="online-duel-incoming" aria-label="Incoming challenges">
        <h3>Challenges for you</h3>
        {pending.length ? <ul>{pending.map(item => <li key={item.invite_id}>
          <span>{names.get(item.host_id) || 'A group member'} challenged you · {item.mode === 'geared' ? 'Ranked' : item.mode === 'friendly' ? 'Friendly' : 'Unranked'}</span>
          <button type="button" className="campaign-button" disabled={busy} onClick={() => accept(item.invite_id)}>Accept</button>
        </li>)}</ul> : <p>No incoming challenges.</p>}
      </section>
    </div>}

    {matchId && match && match.phase === 'loadout' && <div className="online-duel-lobby">
      <h3>Prepare your loadout</h3>
      <p>{match.mode === 'friendly' ? 'Choose any gear. Its bounded duel effects apply only in this match.' : match.mode === 'geared' ? 'Choose only gear this account has earned and verified. Ranked results update your private group ladder.' : 'Both hunters have equal combat stats. Choose a weapon style and appearance.'} Your inventory will not change.</p>
      {['weapon', 'armor', 'trinket'].map(slot => <label key={slot} htmlFor={`duel-${slot}`}>
        {slot === 'armor' ? 'Armour' : slot[0].toUpperCase() + slot.slice(1)}
        <select id={`duel-${slot}`} value={selection[slot]} disabled={busy || !!match.you.loadout} onChange={event => setLoadoutField(slot, event.target.value)}>
          <option value="">None</option>
          {catalogItems(slot).map(item => <option key={item.id} value={item.id}>{item.name}{slot === 'weapon' && !item.combat_style ? ' · no weapon animation yet' : ''}</option>)}
        </select>
        {equipmentBonus(slot, selection[slot]) && <small>{equipmentBonus(slot, selection[slot])}</small>}
      </label>)}
      <AppearanceSelect label="Weapon mastery appearance" field="weapon_appearance" type="weapon" disabled={busy || !!match.you.loadout} value={selection.weapon_appearance} catalog={catalog} weaponStyle={catalogItems('weapon').find(item => item.id === selection.weapon)?.combat_style} onChange={setLoadoutField} />
      <AppearanceSelect label="Armour mastery appearance" field="armor_appearance" type="armor" disabled={busy || !!match.you.loadout} value={selection.armor_appearance} catalog={catalog} onChange={setLoadoutField} />
      <button type="button" className="campaign-button" disabled={busy || !catalog || !!match.you.loadout} onClick={lockLoadout}>{match.you.loadout ? 'Loadout locked' : 'Lock loadout'}</button>
      <p role="status">{match.opponent.loadout_locked ? 'Opponent is ready.' : 'Waiting for your opponent to choose their loadout.'}</p>
      {match.mode === 'geared' && !(catalog?.owned_ids || []).length && <small>No verified gear on this account yet. You can still play without equipment.</small>}
    </div>}

    {matchId && match && match.phase !== 'loadout' && <div className="online-duel-layout">
      <main>
        {match.phase === 'bonus' ? <div className="online-duel-bonus">
          <small>BONUS QUESTION · NO DAMAGE FOR A WRONG ANSWER</small>
          <h3>{match.bonus_question?.prompt || 'Bonus question'}</h3>
          <p>Choose an answer and the reward you want if correct.</p>
          <div className="online-duel-bonus-options">{(match.bonus_question?.options || []).map((option, index) => <button key={index} type="button" aria-pressed={bonusAnswer === index} disabled={busy || match.bonus_question?.answered} onClick={() => setBonusAnswer(index)}>{option}</button>)}</div>
          <label htmlFor="duel-bonus-reward">Reward</label>
          <select id="duel-bonus-reward" value={bonusReward} disabled={busy || match.bonus_question?.answered} onChange={event => setBonusReward(event.target.value)}>
            <option value="heal">Restore up to 10 HP</option><option value="guard">Block 10 damage next exchange</option><option value="boon">Add 5 damage to your next hit</option>
          </select>
          <button type="button" className="campaign-button" disabled={busy || match.bonus_question?.answered || bonusAnswer === null || seconds <= 0} onClick={lockBonus}>{match.bonus_question?.answered ? 'Answer locked' : 'Lock bonus answer'}</button>
          <p>{match.bonus_question?.answered ? 'Waiting for the other hunter.' : 'The timer is shared; a missed answer has no penalty.'}</p>
        </div> : <>
          <div className="online-duel-task">
            <small>CHALLENGE {match.round + 1} · {match.challenge?.id}</small>
            <h3>{match.challenge?.title}</h3>
            <p>{match.challenge?.prompt}</p>
            {match.challenge?.recovery_baseline && <p>A working baseline is in the editor because the previous step was missed.</p>}
          </div>
          {isChoice ? <div className="online-duel-choices">
            {match.challenge.snippet && <pre className="online-duel-snippet" aria-label="Code to study">{match.challenge.snippet}</pre>}
            <div className="online-duel-bonus-options" role="group" aria-label="Answers">{(match.challenge.options || []).map((option, index) => <button key={index} type="button" aria-pressed={choice === index} disabled={busy || !canEdit} onClick={() => setChoice(index)}>{option}</button>)}</div>
            <p>{match.you.submitted ? 'Answer locked.' : 'Pick an answer and a stance, then submit. Quick questions are timed.'}</p>
          </div> : <><div className="online-duel-editor"><Editor height="100%" language="python" value={code} onChange={value => setCode(value ?? '')} theme="vs-dark" options={{ readOnly: !canEdit, minimap:{enabled:false}, automaticLayout:true, scrollBeyondLastLine:false }} /></div>
          <div className="online-duel-terminal">
            <div><b>PROGRAM OUTPUT</b><button type="button" className="campaign-button ghost" disabled={running || !canEdit || !code.trim()} onClick={runPractice}>{running ? 'Running…' : 'Run code'}</button><small>Practice only · no damage</small></div>
            <pre aria-live="polite">{output}</pre>
            <details><summary>Provide input for input()</summary><textarea aria-label="Program input" value={stdin} onChange={event => setStdin(event.target.value)} maxLength={4000} placeholder="One input per line" /></details>
          </div></>}
          <div className="online-duel-actions">
            {match.phase === 'coding' && <button type="button" className="campaign-button" disabled={busy || !canEdit || (isChoice ? choice === null : !code.trim())} onClick={submitCode}>Submit answer</button>}
            {match.phase === 'evaluating' && <p role="status">Your answer is locked. Waiting for the evaluator and your opponent.</p>}
            {match.phase === 'exchange' && <><p className="online-duel-exchange" role="status">{exchangeSummary}</p><button type="button" className="campaign-button" disabled={busy || match.you.ready} onClick={ready}>{match.you.ready ? 'Waiting for opponent…' : 'Ready for next challenge'}</button></>}
            {['finished', 'aborted'].includes(match.phase) && <><h3>{match.phase === 'aborted' ? 'Match ended' : match.you.hp === match.opponent.hp ? 'Draw' : match.you.hp > match.opponent.hp ? 'Victory' : 'Defeat'}</h3><p className="online-duel-exchange" role="status">{status}</p>{match.mode === 'geared' && match.phase === 'finished' && <p>{match.settlement === 'settled' ? 'Your private group ladder has been updated.' : match.settlement === 'pending' ? 'Ranked result is saved and ladder settlement is pending.' : 'This match did not change the ladder.'}</p>}</>}
            {match.phase === 'coding' && <p>{status}</p>}
          </div>
        </>}
      </main>
      <aside>
        <div className="online-duel-timer" aria-label={`${timeText} remaining`}><span>{match.phase === 'bonus' ? 'BONUS ROUND' : 'ROUND TIMER'}</span><strong>{timeText}</strong><div><i style={{width:`${timePercent}%`}} /></div></div>
        <div className="online-duel-bars" aria-label="Hunter health">
          <div><b>You</b><span>{hp(match.you.hp)} / 100 HP</span><i style={{'--hp':`${hp(match.you.hp)}%`}} /></div>
          <div><b>Rival</b><span>{hp(match.opponent.hp)} / 100 HP</span><i style={{'--hp':`${hp(match.opponent.hp)}%`}} /></div>
        </div>
        <div className="online-duel-scene"><iframe ref={frame} title="Colosseum fight scene" src="/combat/index.html?embed=1" onLoad={() => { frameReady.current = false }} /></div>
        <div className="online-duel-stances" aria-label="Combat stance">{[['attack', 'Attack'], ['guard', 'Guard'], ['focus', 'Focus']].map(([value, label]) => <button key={value} type="button" aria-pressed={stance === value} disabled={!canEdit} onClick={() => setStance(value)}>{label}</button>)}</div>
        <p className="online-duel-exchange">{exchangeSummary || (match.phase === 'finished' ? status : 'Attack: +10 damage if your code passes. Focus: +10 on your next hit if it passes. Guard: blocks 10 incoming damage even if it fails.')}</p>
      </aside>
    </div>}
  </section>
}

export function RecoverableDuels({ matches, names = new Map(), busy = false, onResume = () => {} }) {
  if (!matches?.length) return null
  return <section className="online-duel-incoming" aria-label="Saved duels">
    <h3>Continue a duel</h3>
    <ul>{matches.map(item => <li key={item.match_id}>
      <span>{names.get(item.opponent_id) || 'A group member'} · {item.mode === 'geared' ? 'Ranked' : item.mode === 'friendly' ? 'Friendly' : 'Unranked'} · Challenge {item.round + 1}</span>
      <button type="button" className="campaign-button" disabled={busy} onClick={() => onResume(item)}>Resume</button>
    </li>)}</ul>
    <p>Unfinished duels stay saved if the app closes or reconnects.</p>
  </section>
}

function AppearanceSelect({ label, field, type, value, disabled, catalog, weaponStyle, onChange }) {
  const owned = new Set(catalog?.owned_appearance_ids || [])
  const progress = catalog?.mastery_progress || { total_wins:0, weapon_wins:{} }
  const entries = (catalog?.appearances || []).filter(item => item.appearance_type === type && (type !== 'weapon' || item.style === weaponStyle))
  const remaining = item => {
    const wins = item.unlock_rule === 'total_wins' ? progress.total_wins || 0 : progress.weapon_wins?.[item.style] || 0
    return Math.max(0, item.required_wins - wins)
  }
  return <label className="online-mastery-select">{label}<select value={value} disabled={disabled || !catalog || (type === 'weapon' && !weaponStyle)} onChange={event => onChange(field, event.target.value)}>
    <option value="">Use equipment appearance</option>
    {entries.map(item => <option key={item.id} value={item.id} disabled={!owned.has(item.id)}>{item.tier[0].toUpperCase() + item.tier.slice(1)} · {item.name}{owned.has(item.id) ? ' · unlocked' : ` · ${remaining(item)} more wins`}</option>)}
  </select><small>{type === 'weapon' && !weaponStyle ? 'Equip a supported weapon to select its mastery appearance.' : entries.length ? 'Cosmetic only. This does not change match stats or effects.' : 'No mastery appearance for this weapon style yet.'}</small></label>
}
