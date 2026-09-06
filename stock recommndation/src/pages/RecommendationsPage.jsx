import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import AnalysisMethodologyModal from '../components/AnalysisMethodologyModal'

import { API } from '../config'

const RATING_COLOR = {
  'Strong Buy': 'var(--clr-green)',
  'Buy':        '#10B981',
  'Hold':       'var(--clr-amber)',
  'Sell':       'var(--clr-red)',
}
const RATING_BADGE = {
  'Strong Buy': 'badge-green',
  'Buy':        'badge-green',
  'Hold':       'badge-amber',
  'Sell':       'badge-red',
}
const RATING_BAR = {
  'Strong Buy': 'strong',
  'Buy':        'good',
  'Hold':       'hold',
  'Sell':       'sell',
}

// ─── Why Recommended Panel ────────────────────────────────────────────────────
function WhyPanel({ reasons, fillsGap, gapBonus }) {
  if (!reasons?.length) return null
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', marginBottom: 6 }}>
        Why Recommended
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {reasons.map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: 11, color: 'var(--clr-text-2)', lineHeight: 1.4 }}>
            <span style={{ color: i === 0 ? 'var(--clr-primary)' : fillsGap && i === reasons.length - 1 ? 'var(--clr-accent)' : 'var(--clr-green)', flex: 'none', marginTop: 1 }}>
              {i === 0 ? '🎯' : '✓'}
            </span>
            <span dangerouslySetInnerHTML={{ __html: r.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
          </div>
        ))}
        {fillsGap && (
          <div style={{ marginTop: 4 }}>
            <span className="badge badge-purple" style={{ fontSize: 10 }}>
              +{gapBonus} pts portfolio gap bonus
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Stock Card ───────────────────────────────────────────────────────────────
function StockCard({ rec, onSelect }) {
  const score = rec.combined_score || 0
  const rating = rec.combined_rating || 'Hold'

  return (
    <div className="stock-card" onClick={() => onSelect(rec)}>
      <div className="stock-card-top">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="stock-card-symbol">{rec.symbol}</div>
            {rec.fills_gap && (
              <span className="badge badge-purple" style={{ fontSize: 9 }}>🧩 Gap Fill</span>
            )}
          </div>
          <div className="stock-card-name">{rec.name}</div>
          <div style={{ display: 'flex', gap: 5, marginTop: 5, flexWrap: 'wrap' }}>
            <span className="badge badge-gray">{rec.type || 'Stock'}</span>
            <span className="badge badge-purple">{rec.sector || ''}</span>
          </div>
        </div>
        <div>
          <div className="stock-card-price">₹{rec.current_price?.toFixed(2)}</div>
          <div className="stock-card-change" style={{ marginTop: 4 }}>
            <span className={`badge ${RATING_BADGE[rating]}`}>{rating}</span>
          </div>
        </div>
      </div>

      <div className="score-bar-wrap">
        <div className="score-bar-label">
          <span>AI Score</span>
          <span style={{ color: RATING_COLOR[rating], fontWeight: 700 }}>{score}/100</span>
        </div>
        <div className="score-bar">
          <div className={`score-bar-fill ${RATING_BAR[rating]}`} style={{ width: `${score}%` }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8 }}>
        <div style={{ background: 'var(--clr-primary-lt)', borderRadius: 6, padding: '5px 8px', textAlign: 'center' }}>
          <div style={{ fontSize: 9, color: 'var(--clr-text-3)', fontWeight: 700, textTransform: 'uppercase' }}>Technical</div>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--clr-primary)', fontFamily: 'var(--font-mono)' }}>
            {rec.technical?.score}/100
          </div>
        </div>
        <div style={{ background: '#F5F3FF', borderRadius: 6, padding: '5px 8px', textAlign: 'center' }}>
          <div style={{ fontSize: 9, color: 'var(--clr-text-3)', fontWeight: 700, textTransform: 'uppercase' }}>Fundamental</div>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--clr-accent)', fontFamily: 'var(--font-mono)' }}>
            {rec.fundamental?.score}/100
          </div>
        </div>
      </div>

      <div className="returns-row">
        {['1y_cagr', '3y_cagr', '5y_cagr'].map((k, i) => {
          const val = rec.expected_returns?.[k] || 0
          return (
            <div key={k} className="return-chip">
              <div className="return-chip-label">{['1Y', '3Y', '5Y'][i]} CAGR</div>
              <div className={`return-chip-val ${val >= 0 ? 'pos' : 'neg'}`}>
                {val >= 0 ? '+' : ''}{val}%
              </div>
            </div>
          )
        })}
        {rec.expected_returns?.max_drawdown_5y != null && (
          <div className="return-chip" style={{ background: 'var(--clr-red-lt)', borderColor: '#FECACA' }}>
            <div className="return-chip-label" style={{ color: 'var(--clr-red)' }}>5Y Max DD</div>
            <div className="return-chip-val neg" style={{ color: 'var(--clr-red)' }}>
              {rec.expected_returns.max_drawdown_5y}%
            </div>
          </div>
        )}
      </div>

      <WhyPanel reasons={rec.why_recommended} fillsGap={rec.fills_gap} gapBonus={rec.gap_bonus} />
    </div>
  )
}

// ─── Signal List ──────────────────────────────────────────────────────────────
function SignalList({ signals, title }) {
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--clr-text-2)', marginBottom: 8 }}>{title}</div>
      <div className="signal-list">
        {(signals || []).map((s, i) => (
          <div key={i} className="signal-item">
            <span className="signal-item-label">{s.label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="signal-item-val">{s.value}</span>
              <span className={`signal-item-impact ${s.impact === '+' ? 'pos' : s.impact === '-' ? 'neg' : 'neu'}`}>
                {s.impact === '+' ? '▲' : s.impact === '-' ? '▼' : '●'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Stock Detail Modal ────────────────────────────────────────────────────────
function StockDetail({ rec, onClose }) {
  const [history, setHistory] = useState([])
  const [period, setPeriod] = useState('6mo')

  useEffect(() => {
    fetch(`${API}/api/stock/${rec.symbol}/historical?period=${period}`)
      .then(r => r.json())
      .then(d => setHistory(d.history || []))
      .catch(() => {})
  }, [rec.symbol, period])

  const color = RATING_COLOR[rec.combined_rating] || 'var(--clr-primary)'

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)',
      zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(4px)', padding: 20 }}
      onClick={onClose}
    >
      <div style={{ background: 'var(--clr-surface)', borderRadius: 'var(--r-2xl)',
        width: '100%', maxWidth: 900, maxHeight: '92vh', overflowY: 'auto',
        boxShadow: 'var(--shadow-xl)', padding: 28 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Top */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 24, fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{rec.symbol}</div>
              {rec.fills_gap && <span className="badge badge-purple">🧩 Portfolio Gap Fill</span>}
            </div>
            <div style={{ fontSize: 14, color: 'var(--clr-text-3)' }}>{rec.name} · {rec.sector} · {rec.type}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 28, fontWeight: 800, fontFamily: 'var(--font-mono)' }}>₹{rec.current_price?.toFixed(2)}</div>
            <span className={`badge ${RATING_BADGE[rec.combined_rating]}`} style={{ fontSize: 13 }}>
              {rec.combined_rating}
            </span>
          </div>
        </div>

        {/* Score boxes */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { label: 'AI Score (Combined)', value: `${rec.combined_score}/100`, color: 'var(--clr-primary)', sub: '60% TA + 40% FA' },
            { label: 'Technical Score', value: `${rec.technical?.score}/100`, color: '#0891B2', sub: rec.technical?.rating },
            { label: 'Fundamental Score', value: `${rec.fundamental?.score}/100`, color: '#D97706', sub: rec.fundamental?.rating },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--clr-surface-2)', borderRadius: 'var(--r-md)', padding: '12px 16px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--clr-text-3)', fontWeight: 600, textTransform: 'uppercase' }}>{s.label}</div>
              <div style={{ fontSize: 26, fontWeight: 800, color: s.color, fontFamily: 'var(--font-mono)' }}>{s.value}</div>
              {s.sub && <div style={{ fontSize: 11, color: s.color, fontWeight: 600 }}>{s.sub}</div>}
            </div>
          ))}
        </div>

        {/* Why recommended */}
        {rec.why_recommended?.length > 0 && (
          <div style={{ background: 'linear-gradient(135deg, var(--clr-primary-lt), #F5F3FF)', border: '1px solid #C7D2FE',
            borderRadius: 'var(--r-lg)', padding: '14px 18px', marginBottom: 20 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10, color: 'var(--clr-primary)' }}>
              🎯 Why This Stock is Recommended For You
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {rec.why_recommended.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--clr-text-2)', lineHeight: 1.5 }}>
                  <span style={{ color: 'var(--clr-green)', fontWeight: 700 }}>✓</span>
                  <span dangerouslySetInnerHTML={{ __html: r.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chart */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Price History</div>
            <div className="tabs" style={{ marginBottom: 0, width: 'auto' }}>
              {['1mo', '3mo', '6mo', '1y', '2y', '5y'].map(p => (
                <button key={p} className={`tab-btn ${period === p ? 'active' : ''}`}
                  style={{ flex: 'none', padding: '5px 12px' }}
                  onClick={() => setPeriod(p)}>{p.toUpperCase()}</button>
              ))}
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--clr-border)" />
                <XAxis dataKey="date" tickFormatter={d => d?.slice(5)} tick={{ fontSize: 10 }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} tickFormatter={v => `₹${v}`} />
                <Tooltip formatter={v => [`₹${v}`, 'Close']} contentStyle={{ border: '1px solid var(--clr-border)', borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="close" stroke={color} strokeWidth={2} fill="url(#cg)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Technical + Fundamental signals side-by-side */}
        <div className="analysis-panel" style={{ marginBottom: 16 }}>
          <SignalList signals={rec.technical?.signals} title="📈 Technical Signals" />
          <SignalList signals={rec.fundamental?.signals} title="📋 Fundamental Signals" />
        </div>

        {/* Key metrics grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px,1fr))', gap: 10, marginBottom: 16 }}>
          {[
            { label: 'RSI (14)', value: rec.technical?.rsi ?? 'N/A' },
            { label: 'MACD', value: rec.technical?.macd?.bullish ? '🟢 Bullish' : '🔴 Bearish' },
            { label: 'MA Alignment', value: rec.technical?.moving_averages?.golden_cross ? '🟢 Golden Cross' : '🔴 Death Cross' },
            { label: 'BB Position', value: rec.technical?.bollinger?.position_pct != null ? `${rec.technical.bollinger.position_pct}%` : 'N/A' },
            { label: 'P/E Ratio', value: rec.fundamental?.pe ? `${rec.fundamental.pe}x` : 'N/A' },
            { label: 'ROE', value: rec.fundamental?.roe ? `${rec.fundamental.roe}%` : 'N/A' },
            { label: 'D/E Ratio', value: rec.fundamental?.debt_equity ?? 'N/A' },
            { label: 'EPS Growth', value: rec.fundamental?.eps_growth ? `${rec.fundamental.eps_growth}%` : 'N/A' },
          ].map(m => (
            <div key={m.label} style={{ background: 'var(--clr-surface-2)', borderRadius: 'var(--r-sm)', padding: '8px 12px' }}>
              <div style={{ fontSize: 10, color: 'var(--clr-text-3)', fontWeight: 600, textTransform: 'uppercase' }}>{m.label}</div>
              <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: 2 }}>{String(m.value)}</div>
            </div>
          ))}
        </div>

        {/* Expected returns */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
          {[['1Y CAGR', '1y_cagr'], ['3Y CAGR', '3y_cagr'], ['5Y CAGR', '5y_cagr']].map(([label, key]) => {
            const v = rec.expected_returns?.[key] || 0
            return (
              <div key={key} style={{ flex: 1, background: v >= 0 ? 'var(--clr-green-lt)' : 'var(--clr-red-lt)',
                border: `1px solid ${v >= 0 ? '#A7F3D0' : '#FECACA'}`, borderRadius: 'var(--r-md)', padding: '10px 14px', textAlign: 'center' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)', color: v >= 0 ? 'var(--clr-green)' : 'var(--clr-red)' }}>
                  {v >= 0 ? '+' : ''}{v}%
                </div>
                <div style={{ fontSize: 10, color: 'var(--clr-text-3)' }}>Historical CAGR</div>
              </div>
            )
          })}
        </div>

        <button className="btn btn-ghost btn-full" onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

// ─── Portfolio Gaps Panel ─────────────────────────────────────────────────────
function PortfolioGapsPanel({ portfolioAnalysis, riskLabel }) {
  if (!portfolioAnalysis || !portfolioAnalysis.underweight_sectors?.length) return null
  return (
    <div style={{ background: 'var(--clr-amber-lt)', border: '1px solid #FDE68A', borderRadius: 'var(--r-lg)',
      padding: '14px 18px', marginBottom: 20 }}>
      <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--clr-amber)', marginBottom: 10 }}>
        🧩 Portfolio Gaps Detected ({portfolioAnalysis.underweight_sectors.length} sectors underweight)
      </div>
      <div style={{ fontSize: 13, color: 'var(--clr-text-2)', marginBottom: 10 }}>
        Based on your <strong>{riskLabel}</strong> profile, we've boosted recommendations that fill these gaps in your portfolio:
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {portfolioAnalysis.underweight_sectors.map(s => {
          const curr = portfolioAnalysis.portfolio_sectors?.[s] || 0
          const target = portfolioAnalysis.desired_sectors?.[s] || 0
          return (
            <div key={s} style={{ background: 'white', borderRadius: 8, padding: '6px 12px',
              border: '1px solid #FDE68A', fontSize: 12 }}>
              <strong>{s}</strong>
              <span style={{ color: 'var(--clr-text-3)', marginLeft: 6 }}>
                {curr}% → target {target}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const getRiskTier = (score) => {
  if (score <= 20) return { label: 'Very Conservative', color: '#0284C7', badge: 'badge-blue', desc: 'Focus on sovereign debt, gold ETFs, liquid funds & ultra-stable dividend assets.' }
  if (score <= 40) return { label: 'Conservative', color: '#0D9488', badge: 'badge-teal', desc: 'Low-volatility mega caps, Nifty 50 index ETFs, FMCG & IT leaders.' }
  if (score <= 60) return { label: 'Moderate Balanced', color: '#4F46E5', badge: 'badge-purple', desc: 'Balanced core compounders: Reliance, Infosys, ICICI Bank, Bharti Airtel, Bank BeES.' }
  if (score <= 80) return { label: 'Growth / Aggressive', color: '#D97706', badge: 'badge-amber', desc: 'High-growth midcaps, capital goods, defence, auto & electronics expansion.' }
  return { label: 'Very Aggressive / Speculative', color: '#DC2626', badge: 'badge-red', desc: 'High beta disruptors, quick-commerce, fintech, turnaround & renewable energy.' }
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function RecommendationsPage() {
  const { riskScore, saveRiskScore, portfolio, quizAnswers, openStockModal } = useApp()
  const navigate = useNavigate()
  const [recs, setRecs] = useState([])
  const [portfolioAnalysis, setPortfolioAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('All')
  const [ratingFilter, setRatingFilter] = useState('All')
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [showMethodology, setShowMethodology] = useState(false)

  // Get broker portfolio from localStorage
  const brokerPortfolio = (() => {
    try { return JSON.parse(localStorage.getItem('broker_portfolio') || '[]') } catch { return [] }
  })()

  const loadRecs = async () => {
    if (riskScore === null) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          risk_score: riskScore,
          portfolio,
          broker_portfolio: brokerPortfolio,
          quiz_answers: quizAnswers,
        }),
      })
      const data = await res.json()
      setRecs(data.recommendations || [])
      setPortfolioAnalysis(data.portfolio_analysis || null)
    } catch (e) {
      setError('Could not connect to backend. Make sure the FastAPI server is running on port 8000.')
    }
    setLoading(false)
  }

  useEffect(() => { if (riskScore !== null) loadRecs() }, [riskScore])

  const types   = ['All', ...new Set(recs.map(r => r.type || 'Stock'))]
  const ratings = ['All', 'Strong Buy', 'Buy', 'Hold']

  const filtered = recs
    .filter(r => filter === 'All' || r.type === filter)
    .filter(r => ratingFilter === 'All' || r.combined_rating === ratingFilter)

  const riskTier = riskScore !== null ? getRiskTier(riskScore) : null
  const riskLabel = riskTier?.label || 'Moderate'

  const totalHeld = (portfolio.length || 0) + (brokerPortfolio.length || 0)

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h1>AI Stock Recommendations 🎯</h1>
            <span className="badge badge-purple" style={{ fontSize: 11 }}>
              NIFTY 500 Universe · 5-Year Deep Analysis
            </span>
          </div>
          <p>Ranked using 5-year historical CAGR, RSI momentum, moving averages, fundamentals & portfolio gap filling</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => setShowMethodology(true)}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          📐 How We Score
        </button>
      </div>

      {riskScore === null ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🧠</div>
            <h3>Complete the Risk Quiz First</h3>
            <p>Your risk profile is needed to generate personalized stock recommendations.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/quiz')}>
              Take Risk Quiz →
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Risk + portfolio context banner */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <div style={{
                  width: 58,
                  height: 58,
                  borderRadius: '50%',
                  background: `linear-gradient(135deg, ${riskTier.color}, var(--clr-primary))`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: 22,
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  flexShrink: 0,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                }}>
                  {riskScore}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 800, fontSize: 17, color: 'var(--clr-text-1)' }}>{riskTier.label}</span>
                    <span className={`badge ${riskTier.badge}`} style={{ fontSize: 10 }}>Tier {riskScore <= 20 ? '1' : riskScore <= 40 ? '2' : riskScore <= 60 ? '3' : riskScore <= 80 ? '4' : '5'} / 5</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--clr-text-3)', marginTop: 3 }}>
                    Score {riskScore}/100 · {totalHeld} holdings tracked · {recs.length} NIFTY 500 stocks analyzed over 5 years
                  </div>
                </div>
                {/* Portfolio sources */}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {portfolio.length > 0 && (
                    <span className="badge badge-blue">{portfolio.length} manual</span>
                  )}
                  {brokerPortfolio.length > 0 && (
                    <span className="badge badge-purple">🔗 {brokerPortfolio.length} from broker</span>
                  )}
                  {totalHeld === 0 && (
                    <span className="badge badge-gray" style={{ cursor: 'pointer' }} onClick={() => navigate('/portfolio')}>
                      + Add Portfolio →
                    </span>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button className="btn btn-secondary btn-sm" onClick={loadRecs} disabled={loading}>
                  {loading ? '⏳ Analyzing…' : '🔄 Refresh Picks'}
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => navigate('/quiz')}>Retake Quiz</button>
              </div>
            </div>

            {/* Precise Risk Threshold Slider */}
            <div style={{
              marginTop: 18,
              paddingTop: 16,
              borderTop: '1px solid var(--clr-border)',
              background: 'var(--clr-surface-2)',
              borderRadius: 'var(--r-md)',
              padding: '12px 16px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--clr-text-2)' }}>
                  🎯 Fine-Tune Risk Threshold (0 – 100):
                </span>
                <span style={{ fontSize: 13, fontWeight: 800, fontFamily: 'var(--font-mono)', color: riskTier.color }}>
                  Current: {riskScore} / 100 ({riskTier.label})
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={riskScore}
                onChange={e => saveRiskScore(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: riskTier.color, cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--clr-text-3)', marginTop: 4 }}>
                <span>0 Very Safe</span>
                <span>20 Conservative</span>
                <span>40 Balanced</span>
                <span>60 Growth</span>
                <span>80 Aggressive</span>
                <span>100 Speculative</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--clr-text-2)', marginTop: 6 }}>
                💡 <em>{riskTier.desc}</em>
              </div>
            </div>
          </div>

          {/* Portfolio gap warnings */}
          <PortfolioGapsPanel portfolioAnalysis={portfolioAnalysis} riskLabel={riskLabel} />

          {error && (
            <div style={{ background: 'var(--clr-red-lt)', border: '1px solid #FECACA', borderRadius: 'var(--r-md)',
              padding: '12px 16px', marginBottom: 16, color: 'var(--clr-red)', fontSize: 13 }}>
              ⚠️ {error}
            </div>
          )}

          {/* Filters */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', marginBottom: 4 }}>Type</div>
              <div className="tabs" style={{ marginBottom: 0 }}>
                {types.map(t => (
                  <button key={t} className={`tab-btn ${filter === t ? 'active' : ''}`} onClick={() => setFilter(t)}>{t}</button>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', marginBottom: 4 }}>Rating</div>
              <div className="tabs" style={{ marginBottom: 0 }}>
                {ratings.map(r => (
                  <button key={r} className={`tab-btn ${ratingFilter === r ? 'active' : ''}`} onClick={() => setRatingFilter(r)}>{r}</button>
                ))}
              </div>
            </div>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <div className="loading-spinner" />
              <p style={{ marginTop: 16, color: 'var(--clr-text-3)' }}>
                Running technical + fundamental analysis on {totalHeld > 0 ? 'your portfolio + ' : ''}candidates…
              </p>
            </div>
          ) : (
            <>
              {/* Gap-fill picks */}
              {filtered.some(r => r.fills_gap) && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--clr-accent)', marginBottom: 12 }}>
                    🧩 Portfolio Gap Fills (boosted for your allocation)
                  </div>
                  <div className="rec-grid">
                    {filtered.filter(r => r.fills_gap).map(rec => (
                      <StockCard key={rec.symbol} rec={rec} onSelect={r => openStockModal(r.symbol)} />
                    ))}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--clr-text-2)', margin: '24px 0 12px' }}>
                    📊 All Recommendations
                  </div>
                </div>
              )}

              <div className="rec-grid">
                {filtered.filter(r => !r.fills_gap).map(rec => (
                  <StockCard key={rec.symbol} rec={rec} onSelect={r => openStockModal(r.symbol)} />
                ))}
              </div>
            </>
          )}

          {!loading && filtered.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">🔍</div>
              <h3>No recommendations</h3>
              <p>Try clicking Refresh or adjusting the filters.</p>
            </div>
          )}
        </>
      )}

      {showMethodology && <AnalysisMethodologyModal onClose={() => setShowMethodology(false)} />}
    </div>
  )
}
