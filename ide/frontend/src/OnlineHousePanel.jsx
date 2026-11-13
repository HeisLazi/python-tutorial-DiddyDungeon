import { useEffect, useState } from 'react'
import { listHunterGroups } from './cloud/hunterGroups.js'
import { onlineDuel } from './cloud/onlineDuel.js'
import OnlineMerchant from './OnlineMerchant.jsx'
import OnlineLeaderboard from './OnlineLeaderboard.jsx'

export default function OnlineHousePanel({ page, account, onNavigate, onClose, onEquipmentSynced }) {
  const signedIn = account?.authStatus === 'signed-in' && Boolean(account?.user?.id)
  const userId = account?.user?.id || ''
  const [groups, setGroups] = useState([])
  const [groupId, setGroupId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const activeGroup = groups.find(group => group.id === groupId) || null

  useEffect(() => {
    if (!signedIn) {
      setGroups([])
      setGroupId('')
      setLoading(false)
      setError('')
      return undefined
    }
    let active = true
    setLoading(true)
    setError('')
    listHunterGroups()
      .then(next => {
        if (!active) return
        const available = Array.isArray(next) ? next : []
        setGroups(available)
        setGroupId(current => available.some(group => group.id === current) ? current : available[0]?.id || '')
      })
      .catch(reason => { if (active) setError(reason?.message || 'Your online lobby could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [signedIn, userId])

  return <section className="online-house-panel" aria-label={page === 'shop' ? 'Sir Getrich’s shop' : 'Group Leaderboards'}>
    {!signedIn ? <div className="online-house-state">
      <h2>Sign in to use Shax Champions House</h2>
      <p>Your online shop and group standings need your Quest Lab account.</p>
      <button type="button" className="online-menu-primary" onClick={() => onNavigate?.('settings')}>Open account settings</button>
    </div> : loading ? <p className="online-house-state" role="status">Loading your online lobby…</p>
      : error ? <div className="online-house-state" role="alert"><h2>Couldn’t open this page</h2><p>{error}</p><button type="button" className="online-menu-secondary" onClick={() => onNavigate?.('online')}>Open online lobby</button></div>
        : !groups.length ? <div className="online-house-state"><h2>Join a lobby first</h2><p>Create or join your private lobby from the Online menu, then return here.</p><button type="button" className="online-menu-primary" onClick={() => onNavigate?.('online')}>Open online lobby</button></div>
          : <>
            {groups.length > 1 && <label className="online-house-group">Lobby<select value={groupId} onChange={event => setGroupId(event.target.value)}>{groups.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>}
            {activeGroup && page === 'shop' && <OnlineMerchant groupId={activeGroup.id} client={onlineDuel} onClose={onClose} onEquipmentSynced={onEquipmentSynced} backLabel="← Shax Champions House" />}
            {activeGroup && page === 'leaderboard' && <OnlineLeaderboard groupId={activeGroup.id} userId={userId} onClose={onClose} backLabel="← Shax Champions House" />}
          </>}
  </section>
}
