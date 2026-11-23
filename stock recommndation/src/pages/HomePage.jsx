import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, Check } from 'lucide-react'
import { useApp } from '../App'
import { API } from '../config'

const INDEX_NAMES = { NSEI: 'NIFTY 50', BSESN: 'SENSEX', NSEBANK: 'NIFTY Bank' }
const cleanSym = (s = '') => s.replace('^', '')

function fmt(n, d = 2) {
  if (n === undefined || n === null || Number.isNaN(n)) return '—'
  return Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })
}

function getTier(s) {
  if (s <= 20) return 'Very conservative'
  if (s <= 40) return 'Conservative'
  if (s <= 60) return 'Balanced'
  if (s <= 80) return 'Growth'
  return 'Aggressive'
}

function moodFor(pct) {
  if (pct === undefined || pct === null) return { title: 'Getting today’s market ready', cls: '' }
  if (pct >= 1) return { title: 'A strong day on Dalal Street', cls: 'up' }
  if (pct >= 0.15) return { title: 'Markets are climbing today', cls: 'up' }
  if (pct > -0.15) return { title: 'Markets are holding steady', cls: '' }
  if (pct > -1) return { title: 'Markets are slipping today', cls: 'dn' }
  return { title: 'A rough day for the market', cls: 'dn' }
}

function MoodHero({ indices, ticksLive }) {
  const nifty = indices.find(i => cleanSym(i.symbol) === 'NSEI')
  const mood = moodFor(nifty?.change_pct)
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })
  const up = (nifty?.change_pct ?? 0) >= 0

  return (
    <section className="mood-hero" aria-live="polite">
      <div className="mood-date">
        {ticksLive && <span className="live-dot" style={{ background: '#6CDB9C' }} />}
        {today}
      </div>
      <h1 className="mood-headline">{mood.title}</h1>
      <p className="mood-sub">
        {nifty
          ? <>NIFTY 50 is {up ? 'up' : 'down'} <strong className={`pct ${up ? 'up' : 'dn'}`} style={{ color: up ? '#6CDB9C' : '#FF8B9B' }}>{Math.abs(nifty.change_pct).toFixed(2)}%</strong> at {fmt(nifty.price)}. Tap any stock to see its scorecard, forecast and AI verdict.</>
          : 'Index levels load from the live NSE feed. Start the backend to see today’s numbers.'}
      </p>
      <div className="mood-indices">
        {(indices.length ? indices : [{ symbol: 'NSEI' }, { symbol: 'BSESN' }, { symbol: 'NSEBANK' }]).map(idx => {
          const sym = cleanSym(idx.symbol)
          const iu = (idx.change_pct ?? 0) >= 0
          return (
            <div className="mood-index" key={sym}>
              <div className="name">{INDEX_NAMES[sym] || sym}</div>
              <div>
                <span className="val">{idx.price ? fmt(idx.price) : '—'}</span>
                {idx.change_pct !== undefined && (
                  <span className={`chg ${iu ? 'up' : 'dn'}`}>{iu ? '+' : '−'}{Math.abs(idx.change_pct).toFixed(2)}%</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Journey({ riskScore, holdings }) {
  const navigate = useNavigate()
  const steps = [
    {
      done: riskScore !== null,
      title: riskScore !== null ? `Risk profile: ${getTier(riskScore)}` : 'Find your risk profile',
      desc: riskScore !== null ? `Score ${riskScore}/100 · retake anytime` : '10 quick questions, about 2 minutes',
      path: '/quiz',
    },
    {
      done: holdings > 0,
      title: holdings > 0 ? `${holdings} holding${holdings > 1 ? 's' : ''} in your portfolio` : 'Add what you already own',
      desc: holdings > 0 ? 'See live P&L and sector exposure' : 'Type them in or connect your broker',
      path: '/portfolio',
    },
    {
      done: false,
      title: 'Get your AI picks',
      desc: 'Stocks and ETFs ranked for your profile',
      path: '/recommendations',
    },
  ]
  const nextIdx = steps.findIndex(s => !s.done)

  return (
    <section className="journey" aria-label="Getting started">
      <div className="journey-head">Your next step</div>
      {steps.map((s, i) => (
        <button
          key={s.path}
          className={`journey-step ${s.done ? 'done' : ''} ${i === nextIdx ? 'next' : ''}`}
          onClick={() => navigate(s.path)}
        >
          <span className="num">{s.done ? <Check size={15} strokeWidth={3} /> : i + 1}</span>
          <span>
            <div className="t">{s.title}</div>
            <div className="d">{s.desc}</div>
          </span>
          <ChevronRight className="go" size={18} />
        </button>
      ))}
    </section>
  )
}

function MoversTable({ rows, onSelect }) {
  if (!rows.length) {
    return (
      <div className="empty-state" style={{ padding: '36px 16px' }}>
        <h3>No movers yet</h3>
        <p>Top gainers and losers show up here once live market data is flowing.</p>
      </div>
    )
  }
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr><th>Stock</th><th style={{ textAlign: 'right' }}>Price</th><th style={{ textAlign: 'right' }}>Change</th></tr>
        </thead>
        <tbody>
          {rows.slice(0, 7).map(s => {
            const up = s.change_pct >= 0
            return (
              <tr key={s.symbol} onClick={() => onSelect(s.symbol)}>
                <td>
                  <div className="sym-cell">
                    <span className="sym-avatar">{s.symbol.slice(0, 2)}</span>
                    <span style={{ fontWeight: 600 }}>{s.symbol}</span>
                  </div>
                </td>
                <td style={{ textAlign: 'right' }}>₹{fmt(s.price)}</td>
                <td style={{ textAlign: 'right' }}>
                  <span className={`badge ${up ? 'badge-green' : 'badge-red'}`}>
                    {up ? '+' : '−'}{Math.abs(s.change_pct).toFixed(2)}%
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function HomePage() {
  const { ticks, riskScore, portfolio, openStockModal } = useApp()
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState(null)
  const [gainers, setGainers] = useState([])
  const [losers, setLosers] = useState([])
  const [tab, setTab] = useState('gainers')

  useEffect(() => {
    const get = (path, set) => fetch(`${API}${path}`).then(r => r.json()).then(d => Array.isArray(d) || d ? set(d) : null).catch(() => {})
    get('/api/market/snapshot', setSnapshot)
    get('/api/market/gainers', d => setGainers(Array.isArray(d) ? d : []))
    get('/api/market/losers', d => setLosers(Array.isArray(d) ? d : []))
  }, [])

  const indices = snapshot?.indices || []
  const tickArr = Object.values(ticks)
  const adv = tickArr.filter(t => t.change_pct > 0).length
  const dec = tickArr.filter(t => t.change_pct < 0).length
  const total = Math.max(adv + dec, 1)
  const best = [...tickArr].sort((a, b) => b.change_pct - a.change_pct)[0]
  const worst = [...tickArr].sort((a, b) => a.change_pct - b.change_pct)[0]

  return (
    <div>
      <div className="mood">
        <MoodHero indices={indices} ticksLive={tickArr.length > 0} />
        <Journey riskScore={riskScore} holdings={portfolio.length} />
      </div>

      <div className="dash-grid">
        <section className="card" style={{ padding: 0 }}>
          <div className="card-header" style={{ padding: '18px 20px 0', marginBottom: 12, flexWrap: 'wrap' }}>
            <div>
              <div className="card-title">Today’s movers</div>
              <div className="card-subtitle">Biggest moves on the NSE right now</div>
            </div>
            <div className="tabs" style={{ marginBottom: 0 }} role="tablist">
              <button role="tab" aria-selected={tab === 'gainers'} className={`tab-btn ${tab === 'gainers' ? 'active' : ''}`} onClick={() => setTab('gainers')}>Gainers</button>
              <button role="tab" aria-selected={tab === 'losers'} className={`tab-btn ${tab === 'losers' ? 'active' : ''}`} onClick={() => setTab('losers')}>Losers</button>
            </div>
          </div>
          <MoversTable rows={tab === 'gainers' ? gainers : losers} onSelect={openStockModal} />
          <div style={{ padding: '12px 20px 16px', borderTop: '1px solid var(--clr-border)' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/live')}>Open the live market</button>
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <section className="card">
            <div className="card-title">Market breadth</div>
            <div className="card-subtitle">Across the {tickArr.length || 0} stocks you’re watching</div>
            <div className="breadth" role="img" aria-label={`${adv} advancing, ${dec} declining`} style={{ marginTop: 14 }}>
              <div className="adv" style={{ width: `${(adv / total) * 100}%` }} />
              <div className="dec" style={{ width: `${(dec / total) * 100}%` }} />
            </div>
            <div className="breadth-legend">
              <span><strong style={{ color: 'var(--clr-green)' }}>{adv}</strong> advancing</span>
              <span><strong style={{ color: 'var(--clr-red)' }}>{dec}</strong> declining</span>
            </div>
          </section>

          <section className="card">
            <div className="card-title" style={{ marginBottom: 6 }}>At a glance</div>
            <div className="kv"><span>Best on your list</span><span style={{ color: 'var(--clr-green)' }}>{best ? `${best.symbol} +${best.change_pct.toFixed(2)}%` : '—'}</span></div>
            <div className="kv"><span>Weakest on your list</span><span style={{ color: 'var(--clr-red)' }}>{worst ? `${worst.symbol} ${worst.change_pct.toFixed(2)}%` : '—'}</span></div>
            <div className="kv"><span>Your risk profile</span><span>{riskScore !== null ? getTier(riskScore) : <button className="btn btn-secondary btn-sm" onClick={() => navigate('/quiz')}>Take the quiz</button>}</span></div>
            <div className="kv"><span>Holdings tracked</span><span>{portfolio.length}</span></div>
          </section>
        </div>
      </div>
    </div>
  )
}
