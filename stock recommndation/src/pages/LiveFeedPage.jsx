import React, { useState, useEffect, useRef } from 'react'
import { useApp } from '../App'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar,
} from 'recharts'

import { API } from '../config'

function formatVol(v) {
  if (!v) return '—'
  if (v >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`
  if (v >= 1e5) return `${(v / 1e5).toFixed(2)} L`
  return v.toLocaleString('en-IN')
}

function PriceCell({ value, prevValue }) {
  const up = value >= (prevValue || value)
  const flashClass = value !== prevValue ? (up ? 'flash-green' : 'flash-red') : ''
  return (
    <span className={`mono ${flashClass}`} style={{ fontWeight: 700 }}>₹{value?.toFixed(2)}</span>
  )
}

function ChangeCell({ chg, pct }) {
  const up = pct >= 0
  return (
    <span className={`badge ${up ? 'badge-green' : 'badge-red'}`}>
      {up ? '▲' : '▼'} {Math.abs(pct).toFixed(2)}%
    </span>
  )
}

function MarketTable({ title, icon, data, loading, colorKey }) {
  return (
    <div className="market-table-wrap">
      <div className="market-table-header">
        <div className="market-table-title">
          <span className="icon">{icon}</span>
          {title}
        </div>
        {loading && <div style={{ width: 14, height: 14, border: '2px solid var(--clr-border)', borderTopColor: 'var(--clr-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />}
      </div>
      {loading && !data.length ? (
        <div style={{ padding: 16 }}>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="skeleton" style={{ height: 36, marginBottom: 6 }} />
          ))}
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Change</th>
              {colorKey === 'volume' && <th>Volume</th>}
            </tr>
          </thead>
          <tbody>
            {data.map(s => (
              <tr key={s.symbol}>
                <td><span className="mono" style={{ fontWeight: 700, fontSize: 12 }}>{s.symbol}</span></td>
                <td><PriceCell value={s.price} /></td>
                <td><ChangeCell chg={s.change} pct={s.change_pct} /></td>
                {colorKey === 'volume' && <td style={{ fontSize: 11, color: 'var(--clr-text-3)' }}>{formatVol(s.volume)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function IndexBanner({ indices }) {
  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
      {indices.map(idx => {
        const up = idx.change_pct >= 0
        return (
          <div key={idx.symbol} style={{
            background: up ? 'var(--clr-green-lt)' : 'var(--clr-red-lt)',
            border: `1px solid ${up ? '#A7F3D0' : '#FECACA'}`,
            borderRadius: 'var(--r-lg)',
            padding: '12px 20px',
            display: 'flex', alignItems: 'center', gap: 16,
            flex: 1, minWidth: 200,
          }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                {idx.symbol === 'NSEI' ? 'NIFTY 50' : idx.symbol === 'BSESN' ? 'SENSEX' : idx.symbol === 'NSEBANK' ? 'BANK NIFTY' : idx.symbol}
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)', color: up ? 'var(--clr-green)' : 'var(--clr-red)' }}>
                {idx.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: 12, fontWeight: 600, color: up ? 'var(--clr-green)' : 'var(--clr-red)' }}>
                {up ? '▲' : '▼'} {Math.abs(idx.change_pct).toFixed(2)}%
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function TickChart({ ticks }) {
  const items = Object.values(ticks)
  if (!items.length) return null
  const data = items.map(t => ({ name: t.symbol, pct: parseFloat((t.change_pct || 0).toFixed(2)) }))
    .sort((a, b) => b.pct - a.pct).slice(0, 12)

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-header">
        <div className="card-title">📡 Live Market Overview</div>
        <span className="badge badge-green">
          <div className="live-dot" style={{ width: 6, height: 6 }} /> {items.length} Stocks Live
        </span>
      </div>
      <div className="chart-container">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--clr-border)" />
            <XAxis dataKey="name" tick={{ fontSize: 9 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${v}%`} />
            <Tooltip formatter={(v) => [`${v}%`, '% Change']} contentStyle={{ fontSize: 12 }} />
            <Bar dataKey="pct" fill="#4F46E5"
              radius={[4, 4, 0, 0]}
              label={false}
            >
              {data.map((d, i) => (
                <rect key={i} fill={d.pct >= 0 ? '#059669' : '#DC2626'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function TickerBoard({ ticks }) {
  const items = Object.values(ticks)
  if (!items.length) return null

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div className="card-header">
        <div className="card-title">⚡ Tick-by-Tick Feed</div>
        <span className="badge badge-green" style={{ fontSize: 10 }}>
          <div className="live-dot" style={{ width: 6, height: 6 }} /> LIVE
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 8 }}>
        {items.map(t => {
          const up = t.change_pct >= 0
          return (
            <div key={t.symbol} style={{
              background: up ? '#F0FDF4' : '#FFF1F2',
              border: `1px solid ${up ? '#BBF7D0' : '#FECDD3'}`,
              borderRadius: 'var(--r-md)',
              padding: '8px 12px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{t.symbol}</div>
                <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>₹{t.price?.toFixed(2)}</div>
              </div>
              <span className={`badge ${up ? 'badge-green' : 'badge-red'}`} style={{ fontSize: 10 }}>
                {up ? '+' : ''}{t.change_pct?.toFixed(2)}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function LiveFeedPage() {
  const { ticks } = useApp()
  const [gainers, setGainers] = useState([])
  const [losers, setLosers] = useState([])
  const [volume, setVolume] = useState([])
  const [indices, setIndices] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [g, l, v, snap] = await Promise.all([
        fetch(`${API}/api/market/gainers`).then(r => r.json()),
        fetch(`${API}/api/market/losers`).then(r => r.json()),
        fetch(`${API}/api/market/volume`).then(r => r.json()),
        fetch(`${API}/api/market/snapshot`).then(r => r.json()),
      ])
      setGainers(g)
      setLosers(l)
      setVolume(v)
      setIndices(snap.indices || [])
      setLastUpdate(new Date().toLocaleTimeString('en-IN'))
    } catch (e) {
      console.error('Feed error:', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 30000) // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1>Live Market Feed ⚡</h1>
          <p>Real-time NSE tick data · Top gainers, losers & volume shakers</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {lastUpdate && <span style={{ fontSize: 12, color: 'var(--clr-text-3)' }}>Updated: {lastUpdate}</span>}
          <button className="btn btn-secondary btn-sm" onClick={fetchAll} disabled={loading}>
            {loading ? '⏳' : '🔄'} Refresh
          </button>
        </div>
      </div>

      {/* Index banner */}
      {indices.length > 0 && <IndexBanner indices={indices} />}

      {/* Live tick board */}
      <TickerBoard ticks={ticks} />

      {/* Bar chart overview */}
      <TickChart ticks={ticks} />

      {/* Three tables */}
      <div className="market-grid">
        <MarketTable title="Top Gainers" icon="🚀" data={gainers} loading={loading} colorKey="gain" />
        <MarketTable title="Top Losers" icon="📉" data={losers} loading={loading} colorKey="loss" />
        <MarketTable title="Volume Shakers" icon="🔥" data={volume} loading={loading} colorKey="volume" />
      </div>
    </div>
  )
}
