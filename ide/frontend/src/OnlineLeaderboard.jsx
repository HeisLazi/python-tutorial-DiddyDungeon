import { useEffect, useState } from 'react'
import { hunterGroupLadder } from './cloud/hunterGroups.js'

export default function OnlineLeaderboard({ groupId, userId, onClose, backLabel = '← Lobby', loadLadder = hunterGroupLadder }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true
    setRows(null)
    setError('')
    loadLadder(groupId)
      .then(next => { if (active) setRows(next) })
      .catch(reason => { if (active) setError(reason?.message || 'Leaderboards could not be loaded.') })
    return () => { active = false }
  }, [groupId, refreshKey, loadLadder])

  const loading = rows === null && !error
  return <section className="online-leaderboard online-menu-leaderboard" aria-label="Group Leaderboards">
    <header className="online-heading online-leaderboard-heading">
      <div><span>COLOSSEUM · RANKED DUELS</span><h2>Leaderboards</h2><p>Ranked results for your private group.</p></div>
      <div className="online-leaderboard-buttons online-menu-leaderboard-buttons">
        <button type="button" className="online-menu-secondary" disabled={loading} onClick={() => setRefreshKey(key => key + 1)}>Refresh</button>
        <button type="button" className="online-menu-secondary" onClick={onClose}>{backLabel}</button>
      </div>
    </header>
    <div className="online-leaderboard-board">
      {loading && <p className="online-leaderboard-empty" role="status">Loading group standings…</p>}
      {error && <div className="online-leaderboard-error" role="alert"><p>{error}</p><button type="button" className="online-menu-secondary" onClick={() => setRefreshKey(key => key + 1)}>Try again</button></div>}
      {rows?.length === 0 && <p className="online-leaderboard-empty">No group members are listed yet.</p>}
      {rows?.length > 0 && <div className="online-leaderboard-table-scroll">
        <table className="online-leaderboard-table">
          <caption>Ranked Colosseum standings for this group</caption>
          <thead><tr><th scope="col">Rank</th><th scope="col">Hunter</th><th scope="col" className="online-leaderboard-numeric">Rating</th><th scope="col" className="online-leaderboard-numeric">W–L–D</th></tr></thead>
          <tbody>{rows.map((row, index) => <tr className={row.user_id === userId ? 'is-current-player' : ''} key={row.user_id}>
            <td className="online-leaderboard-rank">{index + 1}</td>
            <th scope="row" className="online-leaderboard-hunter">{row.name}{row.user_id === userId && <span className="online-leaderboard-you">YOU</span>}</th>
            <td className="online-leaderboard-numeric online-leaderboard-rating">{Number(row.rating) || 1000}</td>
            <td className="online-leaderboard-numeric">{Number(row.wins) || 0}–{Number(row.losses) || 0}–{Number(row.draws) || 0}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </div>
    <p className="online-leaderboard-note">Only ranked duels change ratings. Friendly and unranked matches do not count.</p>
  </section>
}
