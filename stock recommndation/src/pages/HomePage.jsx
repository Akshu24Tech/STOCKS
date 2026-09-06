import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

import { API } from '../config'

function IndexCard({ name, data }) {
  if (!data) return (
    <div className="stat-card">
      <div className="stat-label">{name}</div>
      <div className="skeleton" style={{ height: 32, margin: '8px 0 4px' }} />
    </div>
  )
  const up = data.change_pct >= 0
  return (
    <div className="stat-card">
      <div className="stat-label">{name}</div>
      <div className={`stat-value ${up ? 'up' : 'dn'}`}>
        {data.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </div>
      <div className="stat-change">
        <span className={up ? 'up' : 'dn'}>
          {up ? '▲' : '▼'} {Math.abs(data.change_pct).toFixed(2)}%
        </span>
        &nbsp;({up ? '+' : ''}{data.change?.toFixed(2)})
      </div>
    </div>
  )
}

export default function HomePage() {
  const { ticks, riskScore, portfolio } = useApp()
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState(null)
  const [gainers, setGainers] = useState([])

  useEffect(() => {
    fetch(`${API}/api/market/snapshot`)
      .then(r => r.json())
      .then(setSnapshot)
      .catch(() => {})
    fetch(`${API}/api/market/gainers`)
      .then(r => r.json())
      .then(setGainers)
      .catch(() => {})
  }, [])

  const indices = snapshot?.indices || []
  const nifty = indices.find(i => i.symbol === '^NSEI' || i.symbol === 'NSEI')
  const sensex = indices.find(i => i.symbol === '^BSESN' || i.symbol === 'BSESN')
  const bank  = indices.find(i => i.symbol === '^NSEBANK' || i.symbol === 'NSEBANK')

  const getTier = (s) => {
    if (s <= 20) return { label: 'Very Conservative', color: '#0284C7' }
    if (s <= 40) return { label: 'Conservative', color: '#0D9488' }
    if (s <= 60) return { label: 'Moderate Balanced', color: '#4F46E5' }
    if (s <= 80) return { label: 'Growth / Aggressive', color: '#D97706' }
    return { label: 'Very Aggressive / Speculative', color: '#DC2626' }
  }

  const riskTier = riskScore !== null ? getTier(riskScore) : null
  const riskLabel = riskTier?.label || null
  const riskColor = riskTier?.color || 'var(--clr-text-3)'

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Indian stock market intelligence, powered by AI analysis</p>
      </div>

      {/* Indices */}
      <div className="stat-grid">
        <IndexCard name="NIFTY 50" data={nifty} />
        <IndexCard name="SENSEX" data={sensex} />
        <IndexCard name="NIFTY BANK" data={bank} />
        <div className="stat-card">
          <div className="stat-label">Your Risk Profile</div>
          {riskScore !== null ? (
            <>
              <div className="stat-value" style={{ color: riskColor, fontSize: 20, marginTop: 6 }}>{riskLabel}</div>
              <div className="stat-change">Score: {riskScore}/100</div>
            </>
          ) : (
            <div style={{ marginTop: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => navigate('/quiz')}>Take Quiz →</button>
            </div>
          )}
        </div>
        <div className="stat-card">
          <div className="stat-label">Portfolio Holdings</div>
          <div className="stat-value">{portfolio.length}</div>
          <div className="stat-change">
            {portfolio.length === 0
              ? <button className="btn btn-secondary btn-sm" onClick={() => navigate('/portfolio')}>Add Holdings</button>
              : <button className="btn btn-ghost btn-sm" onClick={() => navigate('/portfolio')}>View Portfolio</button>
            }
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Live Stocks Tracked</div>
          <div className="stat-value">{Object.keys(ticks).length}</div>
          <div className="stat-change">WebSocket — tick data</div>
        </div>
      </div>

      {/* Quick Action Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 18, marginBottom: 28 }}>
        <div className="card" style={{ borderLeft: '4px solid var(--clr-primary)', cursor: 'pointer' }} onClick={() => navigate('/quiz')}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🧠</div>
          <div className="card-title">Risk Appetite Quiz</div>
          <p style={{ fontSize: 13, color: 'var(--clr-text-3)', marginTop: 4 }}>
            Answer 10 questions to get your personalized investment profile and unlock AI recommendations.
          </p>
          <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }}>
            {riskScore !== null ? 'Retake Quiz' : 'Start Quiz'} →
          </button>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--clr-accent)', cursor: 'pointer' }} onClick={() => navigate('/recommendations')}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🎯</div>
          <div className="card-title">AI Stock Picks</div>
          <p style={{ fontSize: 13, color: 'var(--clr-text-3)', marginTop: 4 }}>
            Stocks &amp; ETFs recommended based on technical analysis, fundamentals, and your risk profile.
          </p>
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }}>
            View Recommendations →
          </button>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--clr-green)', cursor: 'pointer' }} onClick={() => navigate('/live')}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>⚡</div>
          <div className="card-title">Live Market Feed</div>
          <p style={{ fontSize: 13, color: 'var(--clr-text-3)', marginTop: 4 }}>
            Real-time tick-by-tick NSE data. Top gainers, losers, and volume shakers updated every second.
          </p>
          <button className="btn btn-sm" style={{ marginTop: 12, background: 'var(--clr-green-lt)', color: 'var(--clr-green)' }}>
            Open Live Feed →
          </button>
        </div>
      </div>

      {/* Top Gainers preview */}
      {gainers.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">🚀 Top Gainers Today</div>
              <div className="card-subtitle">Based on live NSE data</div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/live')}>See All</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>Change</th>
                <th>% Change</th>
              </tr>
            </thead>
            <tbody>
              {gainers.slice(0, 6).map(s => (
                <tr key={s.symbol}>
                  <td><span className="mono" style={{ fontWeight: 700 }}>{s.symbol}</span></td>
                  <td className="mono">₹{s.price?.toFixed(2)}</td>
                  <td><span className="badge badge-green">+{s.change?.toFixed(2)}</span></td>
                  <td><span className="badge badge-green">+{s.change_pct?.toFixed(2)}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
