import { useEffect, useMemo, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import DungeonCombatArena from './DungeonCombatArena.jsx'
import { makeRaidCombatTurn } from './raidCombatUi.js'
import { onlineRaid as defaultRaidClient, onlineRaidsConfigured as defaultConfigured } from './cloud/onlineRaid.js'

const statusLabels = { available:'Ready', blocked:'Waiting on earlier task', evaluating:'Checking code…', submitted:'Needs peer review', accepted:'Accepted', failed:'Checks failed', changes_requested:'Changes requested' }

export default function OnlineRaid({ groupId, userId, playerName, playerLook = 'classic', visitors = [], onClose,
  raidClient = defaultRaidClient, configured = defaultConfigured }) {
  const [raid, setRaid] = useState(null)
  const [loadingCurrent, setLoadingCurrent] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)
  const [selectedTask, setSelectedTask] = useState('')
  const [drafts, setDrafts] = useState({})
  const [reassign, setReassign] = useState('')
  const [swapTask, setSwapTask] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [combatTurn, setCombatTurn] = useState(null)
  const syncedBossCode = useRef({})
  const seenAttackSequence = useRef(null)
  const members = useMemo(() => new Map([[userId, { name:playerName || 'Hunter', look:playerLook }], ...visitors.map(visitor => [visitor.id, { name:visitor.name, look:visitor.look }])]), [userId, playerName, playerLook, visitors])

  useEffect(() => {
    let active = true
    setRaid(null)
    setLoadError('')
    setLoadingCurrent(true)
    const refresh = async () => {
      try {
        const current = await raidClient.current(groupId)
        if (active) {
          setRaid(current)
          setLoadError('')
          setLoadingCurrent(false)
          const questionId = current.boss?.question?.id
          const source = current.boss?.draft_source
          const syncKey = current.boss && questionId ? `${current.raid_id}:${questionId}` : ''
          if (source && syncKey && syncedBossCode.current[syncKey] !== source) {
            syncedBossCode.current[syncKey] = source
            setDrafts(existing => ({...existing, [questionId]:source}))
          }
        }
      } catch (reason) {
        if (active) {
          setLoadError(reason?.message || 'Could not reconnect to the co-op board.')
          setLoadingCurrent(false)
        }
      }
    }
    void refresh()
    const timer = setInterval(refresh, 3000)
    return () => { active = false; clearInterval(timer) }
  }, [groupId, raidClient, refreshTick])

  const tasks = raid?.tasks || []
  const selected = tasks.find(task => task.id === selectedTask) || tasks.find(task => task.status !== 'accepted') || tasks[0]
  const code = selected ? (drafts[selected.id] !== undefined ? drafts[selected.id] : (selected.source || selected.starter || '')) : ''
  const boss = raid?.boss
  const bossCode = boss ? (drafts[boss.question?.id] !== undefined ? drafts[boss.question.id] : (boss.draft_source || boss.question?.starter || '')) : ''
  const hunterDown = boss ? (boss.hunter_hp?.[userId] ?? 0) <= 0 : false
  const nameOf = id => !id ? 'Open for volunteers' : members.get(id)?.name || `Member ${String(id).slice(0, 8)}`
  const swapChoices = tasks.filter(task => task.id !== selected?.id && ['available','blocked'].includes(task.status) && task.assignee && !task.volunteer_open)
  const raidParty = boss && raid ? raid.members.map((id, index) => ({
    id,
    name:nameOf(id),
    look:members.get(id)?.look || ['spectral','wayfarer','arcane','harvest'][index % 4],
    hp:boss.hunter_hp?.[id] ?? 5,
    is_you:id === userId,
    style:'sword',
  })) : []

  useEffect(() => {
    if (!boss) return
    const sequence = Number(boss.attack_sequence) || 0
    if (seenAttackSequence.current === null) {
      seenAttackSequence.current = sequence
      return
    }
    if (sequence < seenAttackSequence.current) {
      seenAttackSequence.current = sequence
      return
    }
    if (sequence === seenAttackSequence.current) return
    seenAttackSequence.current = sequence
    setCombatTurn(makeRaidCombatTurn(boss, raid.raid_id, userId))
  }, [boss?.attack_sequence, boss?.last_attack, boss?.hunter_hp, raid?.raid_id, userId])

  async function act(action, success = '') {
    if (busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await action()
      if (result) {
        setRaid(result)
        const questionId = result.boss?.question?.id
        const source = result.boss?.draft_source
        const syncKey = result.boss && questionId ? `${result.raid_id}:${questionId}` : ''
        if (source && syncKey && syncedBossCode.current[syncKey] !== source) {
          syncedBossCode.current[syncKey] = source
          setDrafts(existing => ({...existing, [questionId]:source}))
        }
      }
      if (success) setNotice(success)
    }
    catch (reason) { setError(reason?.message || 'The co-op action did not work.') }
    finally { setBusy(false) }
  }

  function submit() {
    if (!selected) return
    const requestId = globalThis.crypto?.randomUUID?.() || `submission-${Date.now()}-${Math.random().toString(16).slice(2)}`
    void act(() => raidClient.submit(groupId, raid.raid_id, selected.id, requestId, code), 'Submission sent to the isolated checker.')
  }

  return <section className="online-raid" aria-label="Co-op coding project">
    <header className="online-raid-heading"><div><span>LEADERBOARDS · CO-OP RAID</span><h2>The Choef Chief’s Keep</h2><p>Build the treasure ledger together, review each other’s work, then take on the Chief.</p></div><button className="campaign-button ghost" type="button" onClick={onClose}>← Shax Champions House</button></header>
    {!configured ? <div className="online-raid-card"><h3>Co-op is not connected</h3><p>The private online service and isolated evaluator must be available before a raid can start.</p></div> : loadingCurrent ? <div className="online-raid-card" role="status" aria-busy="true"><h3>Checking the group board…</h3><p>Looking for the group’s active or completed raid.</p></div> : loadError && !raid ? <div className="online-raid-card" role="alert"><h3>The group board is unavailable</h3><p>{loadError}</p><button className="campaign-button" type="button" onClick={() => { setLoadError(''); setLoadingCurrent(true); setRefreshTick(value => value + 1) }}>Retry</button></div> : !raid ? <div className="online-raid-card online-raid-start"><div><h3>Start or resume the group project</h3><p>Tasks are shared with your invited group. Code is checked on the host, and another member reviews each passing contribution.</p></div><button className="campaign-button" disabled={busy || loadingCurrent || Boolean(loadError)} onClick={() => void act(() => raidClient.create(groupId), 'The group project is ready.')}>Begin project</button></div> : <>
      <div className="online-raid-summary"><span className={`online-raid-state ${raid.status === 'boss_ready' ? 'accepted' : raid.status}`}>{raid.status === 'active' ? 'PROJECT ACTIVE' : raid.status === 'boss_ready' ? 'LEDGER READY' : raid.status === 'boss_fight' ? 'THRONE ROOM' : raid.status === 'completed' ? 'RAID COMPLETE' : raid.status === 'boss_failed' ? 'PARTY DOWN' : raid.status.toUpperCase()}</span><p>{raid.status === 'boss_ready' ? 'The shared treasure ledger is ready. Take it to the throne room and face The Choef Chief.' : raid.status === 'boss_fight' ? 'The throne-room fight is live. Most mistakes hit only the hunter who submitted; missed mechanics can strike the whole party.' : raid.status === 'boss_failed' ? 'The group is down. Restart the encounter to regroup and try again; no reward has been granted.' : raid.status === 'completed' ? 'The group defeated The Choef Chief. The online reward is recorded for each member.' : 'Finish each coding task, then ask another member to review it.'}</p>{['active','boss_ready','boss_fight'].includes(raid.status) && raid.creator_id === userId && <button type="button" className="campaign-button ghost" disabled={busy} onClick={() => void act(() => raidClient.abandon(groupId, raid.raid_id), 'Project abandoned.')}>Abandon project</button>}</div>
      {raid.status === 'active' && <div className="online-raid-workspace"><nav className="online-raid-tasks" aria-label="Project tasks"><h3>Task board</h3>{tasks.map((task, index) => <button type="button" key={task.id} className={selected?.id === task.id ? 'selected' : ''} onClick={() => setSelectedTask(task.id)}><span>{String(index + 1).padStart(2, '0')} · {task.title}</span><small>{statusLabels[task.status] || task.status} · {nameOf(task.assignee)}</small></button>)}<p>Work is shared across the group. Open a task for volunteers, trade assignments, or reassign it; code still unlocks in prerequisite order.</p></nav>
        {selected && <article className="online-raid-editor"><div className="online-raid-task-head"><div><span>YOUR OBJECTIVE</span><h3>{selected.title}</h3><p>{selected.objective}</p><small>{selected.prompt}</small></div><b className={`online-raid-state ${selected.status}`}>{statusLabels[selected.status] || selected.status}</b></div>
          {selected.status === 'accepted' && <div className="online-raid-accepted"><strong>Peer review passed.</strong><p>Contribution from {nameOf(selected.assignee)} is part of the shared project.</p><pre>{selected.source}</pre></div>}
          {selected.status !== 'accepted' && <><Editor height="min(48vh, 430px)" language="python" theme="vs-dark" value={code} onChange={value => setDrafts(current => ({ ...current, [selected.id]:value || '' }))} options={{readOnly:busy || selected.assignee !== userId || !['available','failed','changes_requested'].includes(selected.status), minimap:{enabled:false}, fontSize:14, wordWrap:'on', scrollBeyondLastLine:false, automaticLayout:true, padding:{top:12,bottom:12}}} />
            <div className="online-raid-actions">{selected.assignee === userId && ['available','failed','changes_requested'].includes(selected.status) && <button className="campaign-button" type="button" disabled={busy || !code.trim()} onClick={submit}>{selected.status === 'available' ? 'Check and submit' : 'Resubmit for review'}</button>}
              {selected.status === 'submitted' && selected.assignee !== userId && <><button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.review(groupId, raid.raid_id, selected.id, 'approve'), 'Contribution approved.')}>Approve contribution</button><button className="campaign-button ghost" type="button" disabled={busy} onClick={() => void act(() => raidClient.review(groupId, raid.raid_id, selected.id, 'request_changes'), 'Changes requested.')}>Request changes</button></>}
              {selected.volunteer_open && selected.assignee !== userId && ['available','blocked'].includes(selected.status) && <button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.volunteer(groupId, raid.raid_id, selected.id), 'You volunteered for this task.')}>Volunteer for this task</button>}
              {!selected.volunteer_open && selected.assignee && ['available','blocked'].includes(selected.status) && (selected.assignee === userId || raid.creator_id === userId) && <button className="campaign-button ghost" type="button" disabled={busy} onClick={() => void act(() => raidClient.openForVolunteers(groupId, raid.raid_id, selected.id), 'The task is open for a volunteer.')}>Open for volunteers</button>}
              {['available','blocked'].includes(selected.status) && raid.status === 'active' && (selected.assignee === userId || raid.creator_id === userId) && <div className="online-raid-reassign"><label htmlFor="raid-reassign">Reassign to</label><select id="raid-reassign" value={reassign} onChange={event => setReassign(event.target.value)}><option value="">Choose a member</option>{raid.members.filter(member => member !== selected.assignee).map(member => <option key={member} value={member}>{nameOf(member)}</option>)}</select><button className="campaign-button ghost" type="button" disabled={busy || !reassign} onClick={() => void act(() => raidClient.assign(groupId, raid.raid_id, selected.id, reassign), 'Task reassigned.')}>Reassign</button></div>}
              {['available','blocked'].includes(selected.status) && !selected.volunteer_open && swapChoices.length > 0 && (selected.assignee === userId || raid.creator_id === userId) && <div className="online-raid-reassign"><label htmlFor="raid-swap">Swap assignments</label><select id="raid-swap" value={swapTask} onChange={event => setSwapTask(event.target.value)}><option value="">Choose another task</option>{swapChoices.map(task => <option key={task.id} value={task.id}>{task.title} · {nameOf(task.assignee)}</option>)}</select><button className="campaign-button ghost" type="button" disabled={busy || !swapTask} onClick={() => void act(() => raidClient.swap(groupId, raid.raid_id, selected.id, swapTask), 'Task assignments swapped.')}>Swap tasks</button></div>}
            </div></>}
        </article>}
      </div>}
      {raid.status === 'boss_ready' && <section className="online-raid-ready"><div><span>THRONE ROOM UNSEALED</span><h3>The shared treasure ledger passed every check.</h3><p>Gather your group, then enter the castle to face the Keeper of the Choefs.</p></div><button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.startBoss(groupId, raid.raid_id), 'The throne room doors open.')}>Enter the throne room</button></section>}
      {boss && ['boss_fight','boss_failed','completed'].includes(raid.status) && <section className={`online-raid-boss phase-${boss.phase || 0}`}>
        <header className="online-raid-boss-heading"><div><span>THE CHOEF CHIEF’S KEEP · FINAL ENCOUNTER</span><h3>The Choef Chief <small>Keeper of the Choefs</small></h3></div><span className={`online-raid-state ${raid.status}`}>{raid.status === 'completed' ? 'KEEP CLEARED' : raid.status === 'boss_failed' ? 'PARTY DOWN' : boss.seated ? 'UNBOTHERED' : 'IN THE FIGHT'}</span></header>
        <DungeonCombatArena
          raidMode
          raidParty={raidParty}
          raidSeated={boss.seated}
          run={{ region:{ id:'choef-chief-keep' }, room_type:'boss', floor:1, encounter:{ name:'The Choef Chief', resolve:boss.hp, max_resolve:boss.max_hp, phase:boss.phase } }}
          loadout={{ hp:boss.hunter_hp?.[userId] ?? 5, max_hp:5, weapon:'Hunter’s Sword', armor:playerLook, trinket:'' }}
          turn={combatTurn}
        />
        {raid.status === 'boss_fight' && boss.feint_pending && <div className="online-raid-feint"><span>THE SARCASM FEINT</span><h4>He claims your passing code is wrong. The checker says it passed.</h4><p>Stand by your answer to deal 1.5× damage. Withdraw it and he will tamper with <code>can_buy</code>; fix the bug before the fight continues.</p>{boss.feint_player === userId ? <div className="online-raid-actions"><button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.resolveBossFeint(groupId, raid.raid_id, 'stand_firm'), 'You held your ground. The Chief takes 1.5× damage.')}>Stand firm · deal 1.5×</button><button className="campaign-button ghost" type="button" disabled={busy} onClick={() => void act(() => raidClient.resolveBossFeint(groupId, raid.raid_id, 'withdraw'), 'The Chief tampered with your helper. Fix the exact-price check.')}>Withdraw · inspect the bug</button></div> : <p role="status">Waiting for {nameOf(boss.feint_player)} to choose whether to stand firm.</p>}</div>}
        {raid.status === 'boss_fight' && !boss.feint_pending && <div className="online-raid-boss-question"><div className="online-raid-task-head"><div><span>QUESTION {Math.min(boss.question_index + 1, boss.question_count)} OF {boss.question_count}</span><h4>{boss.question?.title}</h4><p>{boss.question?.prompt}</p></div><b className="online-raid-state">{boss.seated ? 'INTRO' : `PHASE ${boss.phase + 1}`}</b></div>{boss.mechanic_attack === 'aoe' && <p className="online-raid-mechanic-warning"><strong>TEAM MECHANIC</strong> · Miss this check and the Chief hits the whole party for 1 HP each.</p>}<Editor height="min(34vh, 300px)" language="python" theme="vs-dark" value={bossCode} onChange={value => setDrafts(current => ({...current, [boss.question.id]:value || ''}))} options={{readOnly:busy || hunterDown, minimap:{enabled:false}, fontSize:14, wordWrap:'on', scrollBeyondLastLine:false, automaticLayout:true, padding:{top:12,bottom:12}}}/><div className="online-raid-actions"><button className="campaign-button" type="button" disabled={busy || hunterDown || !bossCode.trim()} onClick={() => { const requestId = globalThis.crypto?.randomUUID?.() || `boss-${Date.now()}-${Math.random().toString(16).slice(2)}`; void act(() => raidClient.submitBoss(groupId, raid.raid_id, boss.question.id, requestId, bossCode), 'The isolated checker has your answer.') }}>{hunterDown ? 'Hunter is down' : 'Run and submit answer'}</button><span>{hunterDown ? 'Another group member must carry the code forward.' : boss.mechanic_attack === 'aoe' ? 'Missed mechanics strike every hunter · other mistakes target only the submitter.' : 'Wrong answers target only the submitting hunter for 1 HP.'}</span></div></div>}
        {raid.status === 'boss_failed' && <div className="online-raid-result"><p>The reward is still locked. Restart the encounter with the group’s remaining hearts.</p><button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.startBoss(groupId, raid.raid_id), 'The group regroups at the throne room entrance.')}>Retry the encounter</button></div>}
        {raid.status === 'completed' && <div className="online-raid-result"><strong>Raid complete · 100 Wazi Bucks recorded for each group member.</strong><p>The reward was recorded once by the host after the Chief’s HP reached zero.</p>{raid.creator_id === userId && <button className="campaign-button" type="button" disabled={busy} onClick={() => void act(() => raidClient.create(groupId), 'A new co-op project is ready.')}>Start another raid</button>}</div>}
      </section>}
    </>}
    {(notice || error) && <p className={`online-raid-message ${error ? 'error' : ''}`} role="status">{error || notice}</p>}
  </section>
}
