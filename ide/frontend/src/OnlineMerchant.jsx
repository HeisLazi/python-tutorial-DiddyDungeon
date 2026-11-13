import { useEffect, useState } from 'react'

const GETRICH_QUOTES = [
  '“I dressed like a jackpot and still got here by bus. Buy something, please.”',
  '“Wazi Bucks only. My accountant says campaign coins are ‘not my department.’”',
  '“I call these premium chains. The receipt calls them clearance.”',
  '“I’m the richest man in the house. It’s a very small house.”',
]

export default function OnlineMerchant({ groupId, client, onClose, backLabel = '← Colosseum lobby' }) {
  const [stock, setStock] = useState(null)
  const [error, setError] = useState('')
  const [quoteIndex, setQuoteIndex] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => setQuoteIndex(index => (index + 1) % GETRICH_QUOTES.length), 6500)
    return () => window.clearInterval(timer)
  }, [])

  async function refresh() {
    setError('')
    try {
      setStock(await client.merchant(groupId))
    }
    catch (reason) { setError(reason?.message || 'The merchant stock could not be loaded.') }
  }

  useEffect(() => { void refresh() }, [groupId])
  const walletBalance = Number(stock?.wallet?.balance)
  const balance = Number.isFinite(walletBalance) ? walletBalance : 0
  return <section className="online-merchant" aria-label="Online merchant">
    <header className="online-heading online-merchant-heading"><div className="online-merchant-showcase"><img src="/online-raid/sir-getrich.png" alt="Sir Getrich in oversized Y2K streetwear, gold glasses, durag and chains" /><div><span>PRIVATE ONLINE SHOP</span><h2>Sir Getrich</h2><p>“{GETRICH_QUOTES[quoteIndex].slice(1, -1)}”</p><small>Shop stock is coming soon.</small></div></div><div className="online-merchant-actions"><button type="button" className="campaign-button ghost" onClick={() => void refresh()}>Refresh balance</button><button type="button" className="campaign-button ghost" onClick={onClose}>{backLabel}</button></div></header>
    <div className="online-merchant-wallet"><span>WAZI BUCKS</span><strong>{stock?.wallet?.balance ?? '—'}</strong><small>Raids {stock?.wallet?.earned?.raid ?? '—'} · Colosseum {stock?.wallet?.earned?.pvp ?? '—'}</small></div>
    {error && <p className="online-status error" role="alert">{error}</p>}
    <section className="online-shop-coming-soon" aria-label="Online shop coming soon"><span aria-hidden="true">✦</span><div><h3>Shop coming soon</h3><p>Keep your Wazi Bucks. You earn 5 for each Colosseum win, and Sir Getrich will have stock later.</p><small>{stock ? `${balance} Wazi Bucks saved to your account` : 'Loading your wallet…'}</small></div></section>
  </section>
}

