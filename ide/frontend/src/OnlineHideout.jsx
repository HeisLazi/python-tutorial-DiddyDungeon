import { useCallback, useEffect, useMemo, useState } from 'react'
import { createHunterGroup, createHunterGroupInvite, joinHunterGroup, listHunterGroups, connectHunterPresence } from './cloud/hunterGroups.js'
import { onlineDuel, onlineDuelsConfigured } from './cloud/onlineDuel.js'
import OnlineMerchant from './OnlineMerchant.jsx'
import OnlineLeaderboard from './OnlineLeaderboard.jsx'
import OnlineDuel from './OnlineDuel.jsx'
import OnlinePageBoundary from './OnlinePageBoundary.jsx'
import './onlineMenu.css'
import './onlineHideout.css'

const LOBBY_NAME = 'Colosseum Lobby'

export default function OnlineHideout({ account, progress, onNavigate, onEquipmentSynced }) {
  const signedIn = account?.authStatus === 'signed-in' && Boolean(account?.user?.id)
  const userId = account?.user?.id || ''
  const playerName = account?.profile?.display_name || progress?.name || 'Hunter'
  const [groups, setGroups] = useState([])
  const [groupId, setGroupId] = useState('')
  const [visitors, setVisitors] = useState([])
  const [presenceState, setPresenceState] = useState('CLOSED')
  const [inviteCode, setInviteCode] = useState('')
  const [newInvite, setNewInvite] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [dueling, setDueling] = useState(false)
  const [page, setPage] = useState('lobby')
  const [inviteCopied, setInviteCopied] = useState(false)
  const activeGroup = useMemo(() => groups.find(group => group.id === groupId) || null, [groups, groupId])

  const refreshGroups = useCallback(async (preferred = '') => {
    const next = await listHunterGroups()
    setGroups(next)
    const selected = next.find(group => group.id === preferred) || next.find(group => group.id === groupId) || next[0]
    setGroupId(selected?.id || '')
    return next
  }, [groupId])

  useEffect(() => {
    if (!signedIn) {
      setGroups([]); setGroupId(''); setVisitors([]); setPresenceState('CLOSED')
      return undefined
    }
    let active = true
    listHunterGroups().then(next => {
      if (!active) return
      setGroups(next)
      setGroupId(current => next.some(group => group.id === current) ? current : next[0]?.id || '')
      setNotice('')
    }).catch(error => { if (active) setNotice(error?.message || 'Could not load your private group.') })
    return () => { active = false }
  }, [signedIn, userId])

  useEffect(() => {
    if (!signedIn || !groupId) {
      setVisitors([]); setPresenceState('CLOSED')
      return undefined
    }
    let active = true
    let session
    setPresenceState('CONNECTING')
    connectHunterPresence({
      groupId,
      name: playerName,
      look: 'classic',
      onVisitors: next => { if (active) setVisitors(next) },
      onStatus: status => { if (active) setPresenceState(status) },
    }).then(next => { if (active) session = next; else void next.close() })
      .catch(error => { if (active) { setPresenceState('CHANNEL_ERROR'); setNotice(error?.message || 'Friend presence is unavailable.') } })
    return () => { active = false; if (session) void session.close() }
  }, [signedIn, userId, groupId, playerName])

  async function run(action) {
    if (busy) return
    setBusy(true); setNotice(''); setNewInvite(''); setInviteCopied(false)
    try { await action() } catch (error) { setNotice(error?.message || 'The online service is unavailable.') }
    finally { setBusy(false) }
  }

  if (dueling && activeGroup) return <OnlineDuel groupId={activeGroup.id} userId={userId} visitors={visitors} onClose={() => setDueling(false)} />

  return <main className="online-menu" aria-label="Online PvP menu">
    <header className="online-menu-header">
      <div><span className="online-menu-kicker">PRIVATE PVP · 3 PLAYERS</span><h1>Colosseum</h1></div>
      <div className={`online-menu-service ${onlineDuelsConfigured ? 'ready' : 'offline'}`}><i />{onlineDuelsConfigured ? 'MATCH SERVICE READY' : 'MATCH SERVICE OFFLINE'}</div>
    </header>

    {signedIn && <nav className="online-menu-pages" aria-label="Online pages">
      <button type="button" aria-current={page === 'lobby' ? 'page' : undefined} className={page === 'lobby' ? 'active' : ''} onClick={() => { setPage('lobby'); setDueling(false) }}>Lobby</button>
      <button type="button" aria-current={page === 'shop' ? 'page' : undefined} className={page === 'shop' ? 'active' : ''} disabled={!activeGroup} title={!activeGroup ? 'Create or join a lobby first' : undefined} onClick={() => setPage('shop')}>Shop</button>
      <button type="button" aria-current={page === 'leaderboard' ? 'page' : undefined} className={page === 'leaderboard' ? 'active' : ''} disabled={!activeGroup} title={!activeGroup ? 'Create or join a lobby first' : undefined} onClick={() => setPage('leaderboard')}>Leaderboards</button>
    </nav>}

    {!signedIn ? <section className="online-menu-card online-menu-signin">
      <span className="online-menu-step">FIRST STEP</span><h2>Sign in to play online</h2>
      <p>Sign in to challenge your friends.</p>
      <button type="button" className="online-menu-primary" onClick={() => onNavigate?.('settings')}>Open account settings</button>
    </section> : page === 'shop' && activeGroup ? <div className="online-menu-page-body">
      <OnlinePageBoundary pageName="Shop" resetKey={`${activeGroup.id}:shop`} onClose={() => setPage('lobby')}>
        <OnlineMerchant groupId={activeGroup.id} client={onlineDuel} onClose={() => setPage('lobby')} onEquipmentSynced={onEquipmentSynced} />
      </OnlinePageBoundary>
    </div> : page === 'leaderboard' && activeGroup ? <div className="online-menu-page-body">
      <OnlinePageBoundary pageName="Leaderboards" resetKey={`${activeGroup.id}:leaderboard`} onClose={() => setPage('lobby')}>
        <OnlineLeaderboard groupId={activeGroup.id} userId={userId} onClose={() => setPage('lobby')} />
      </OnlinePageBoundary>
    </div> : !activeGroup && page !== 'lobby' ? <section className="online-menu-card online-menu-signin">
      <span className="online-menu-step">PRIVATE LOBBY</span><h2>Join a lobby first</h2>
      <p>The shop and Leaderboards are available after you create or join your private group.</p>
      <button type="button" className="online-menu-primary" onClick={() => setPage('lobby')}>Open lobby</button>
    </section> : <div className="online-menu-columns">
      <section className="online-menu-card online-menu-group">
        <div className="online-menu-card-heading"><div><span className="online-menu-step">PRIVATE LOBBY</span><h2>Your lobby</h2></div>{activeGroup && <span className="online-menu-count">{visitors.length + 1}/3 online</span>}</div>
        {groups.length ? <>
          <label className="online-menu-label" htmlFor="online-group-select">Lobby</label>
          <select id="online-group-select" value={groupId} onChange={event => { setGroupId(event.target.value); setDueling(false); setNotice('') }}>
            {groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}
          </select>
        </> : <p className="online-menu-copy">Create a lobby, then share a code with your two friends.</p>}
        {!groups.length && <button type="button" className="online-menu-primary" disabled={busy} onClick={() => void run(async () => { const id = await createHunterGroup(LOBBY_NAME); await refreshGroups(id); setNotice('Lobby created.') })}>{busy ? 'Creating…' : 'Create lobby'}</button>}
        <form className="online-menu-join" onSubmit={event => { event.preventDefault(); void run(async () => { const id = await joinHunterGroup(inviteCode); setInviteCode(''); await refreshGroups(id); setNotice('Joined. The host can see you online.') }) }}>
          <label className="online-menu-label" htmlFor="online-invite-code">Join with code</label>
          <div className="online-menu-inline"><input id="online-invite-code" value={inviteCode} maxLength={48} onChange={event => setInviteCode(event.target.value.replace(/[^0-9a-f]/gi, '').toLowerCase())} placeholder="48-character code" autoComplete="off" /><button type="submit" className="online-menu-secondary" disabled={busy || inviteCode.length !== 48}>{busy ? 'Joining…' : 'Join'}</button></div>
        </form>
        {activeGroup?.owner_id === userId && <div className="online-menu-invite">
          <button type="button" className="online-menu-secondary" disabled={busy || visitors.length + 1 >= 3} onClick={() => void run(async () => { const code = await createHunterGroupInvite(activeGroup.id); setNewInvite(code); setNotice('Invitation created. It expires in 24 hours and can be used once.') })}>{busy ? 'Working…' : newInvite ? 'Make another invite' : 'Invite a friend'}</button>
          {newInvite && <div className="online-menu-code"><code>{newInvite}</code><button type="button" onClick={async () => { try { await navigator.clipboard.writeText(newInvite); setInviteCopied(true) } catch { setNotice('Select and copy the code manually.') } }}>{inviteCopied ? 'Copied' : 'Copy code'}</button><small>One use · expires in 24 hours</small></div>}
        </div>}
      </section>

      <section className="online-menu-card online-menu-players">
        <div className="online-menu-card-heading"><div><span className="online-menu-step">PLAYERS</span><h2>Online now</h2></div><span className={`online-menu-presence ${presenceState === 'SUBSCRIBED' ? 'connected' : ''}`}>{presenceState === 'SUBSCRIBED' ? 'CONNECTED' : presenceState === 'CONNECTING' ? 'CONNECTING…' : 'OFFLINE'}</span></div>
        {!activeGroup ? <p className="online-menu-copy">Create or join a lobby to see your friends.</p> : <>
          <ul className="online-menu-roster"><li><span className="online-menu-avatar" aria-hidden="true">{account?.avatar?.dataUrl ? <img src={account.avatar.dataUrl} alt="" /> : playerName.trim().slice(0, 1).toUpperCase()}</span><strong>{playerName}</strong><small>YOU</small></li>{visitors.map(visitor => <li key={visitor.id}><span className="online-menu-avatar" aria-hidden="true">{visitor.name.trim().slice(0, 1).toUpperCase()}</span><strong>{visitor.name}</strong><small>ONLINE</small></li>)}</ul>
          {visitors.length ? <button type="button" className="online-menu-primary online-menu-duel-button" disabled={!onlineDuelsConfigured} onClick={() => setDueling(true)}>Open duel setup <span>→</span></button> : <div className="online-menu-wait"><strong>Waiting for your friend</strong><span>Your friends appear here when they join.</span></div>}
        </>}
      </section>
    </div>}

    {notice && <p className="online-menu-notice" role="status">{notice}</p>}
    <footer className="online-menu-footer"><span>Private lobby</span><span>Linux + Windows</span></footer>
  </main>
}
