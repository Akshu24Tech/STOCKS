import React, { useState, useEffect } from 'react'
import { API } from '../config'

const CATEGORY_ICONS = {
  Momentum: '⚡',
  Trend: '📈',
  Volatility: '〰️',
  Volume: '🔊',
  Valuation: '💲',
  Profitability: '💰',
  Leverage: '⚖️',
  Growth: '🚀',
}

const IMPACT_COLOR = {
  '+': { bg: 'var(--clr-green-lt)', text: 'var(--clr-green)', border: '#A7F3D0' },
  '-': { bg: 'var(--clr-red-lt)', text: 'var(--clr-red)', border: '#FECACA' },
  'Neutral': { bg: 'var(--clr-amber-lt)', text: 'var(--clr-amber)', border: '#FDE68A' },
}

function ImpactChip({ impact }) {
  const isPos = impact.startsWith('+')
  const isNeg = impact.startsWith('−') || impact.startsWith('-')
  const style = isPos ? IMPACT_COLOR['+'] : isNeg ? IMPACT_COLOR['-'] : IMPACT_COLOR['Neutral']
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px',
      background: style.bg, color: style.text,
      border: `1px solid ${style.border}`,
      borderRadius: 100, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
      fontFamily: 'var(--font-mono)',
    }}>
      {impact}
    </span>
  )
}

function IndicatorCard({ indicator, type }) {
  const [open, setOpen] = useState(false)
  const typeColor = type === 'technical' ? 'var(--clr-primary)' : 'var(--clr-accent)'
  const typeBg = type === 'technical' ? 'var(--clr-primary-lt)' : '#F5F3FF'

  return (
    <div style={{
      border: '1px solid var(--clr-border)', borderRadius: 'var(--r-lg)',
      overflow: 'hidden', marginBottom: 10,
    }}>
      {/* Header */}
      <div
        style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer',
          background: open ? typeBg : 'var(--clr-surface)' }}
        onClick={() => setOpen(o => !o)}
      >
        <span style={{ fontSize: 22, flex: 'none' }}>{indicator.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--clr-text)' }}>{indicator.name}</span>
            <span style={{ fontSize: 10, fontWeight: 700, background: typeBg, color: typeColor,
              padding: '2px 8px', borderRadius: 100 }}>
              {CATEGORY_ICONS[indicator.category]} {indicator.category}
            </span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--clr-text-3)', marginTop: 2 }}>{indicator.description}</div>
        </div>
        <span style={{ color: 'var(--clr-text-3)', fontSize: 14, flex: 'none' }}>{open ? '▲' : '▼'}</span>
      </div>

      {/* Expanded detail */}
      {open && (
        <div style={{ padding: '0 16px 16px', background: 'var(--clr-surface-2)', borderTop: '1px solid var(--clr-border)' }}>
          {/* Formula */}
          {indicator.formula && (
            <div style={{ margin: '12px 0 10px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', marginBottom: 4 }}>Formula</div>
              <code style={{ fontSize: 12, background: '#1E293B', color: '#A5F3FC', padding: '8px 12px',
                borderRadius: 8, display: 'block', fontFamily: 'var(--font-mono)', lineHeight: 1.6 }}>
                {indicator.formula}
              </code>
            </div>
          )}

          {/* Signals table */}
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase', marginBottom: 8 }}>Scoring Rules</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(indicator.signals || []).map((sig, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 10, alignItems: 'center',
                background: 'var(--clr-surface)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--clr-primary)' }}>
                    {sig.condition}
                  </span>
                  <span style={{ color: 'var(--clr-text-3)', marginLeft: 8 }}>→ {sig.signal}</span>
                </div>
                <ImpactChip impact={sig.score_impact} />
                <span style={{ fontSize: 11, color: 'var(--clr-text-3)', whiteSpace: 'nowrap' }}>{sig.action}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ScoreFormula({ data }) {
  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap', padding: '20px 0' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--clr-primary)', fontFamily: 'var(--font-mono)' }}>
          {data?.scoring_formula?.technical_weight}%
        </div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--clr-text-3)' }}>Technical</div>
        <div style={{ width: 80, height: 8, background: 'linear-gradient(90deg,var(--clr-primary),var(--clr-teal))',
          borderRadius: 100, marginTop: 6 }} />
      </div>
      <div style={{ fontSize: 28, color: 'var(--clr-text-3)' }}>+</div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--clr-accent)', fontFamily: 'var(--font-mono)' }}>
          {data?.scoring_formula?.fundamental_weight}%
        </div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--clr-text-3)' }}>Fundamental</div>
        <div style={{ width: 80, height: 8, background: 'linear-gradient(90deg,var(--clr-accent),var(--clr-orange))',
          borderRadius: 100, marginTop: 6 }} />
      </div>
      <div style={{ fontSize: 28, color: 'var(--clr-text-3)' }}>=</div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--clr-text)', fontFamily: 'var(--font-mono)' }}>Score</div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--clr-text-3)' }}>0 – 100</div>
        <div style={{ width: 80, height: 8, background: 'linear-gradient(90deg,var(--clr-red),var(--clr-amber),var(--clr-green))',
          borderRadius: 100, marginTop: 6 }} />
      </div>
    </div>
  )
}

function RatingScale({ ratings }) {
  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
      {(ratings || []).map((r, i) => (
        <div key={i} style={{ flex: 1, minWidth: 130, background: `${r.color}10`, border: `1px solid ${r.color}40`,
          borderRadius: 'var(--r-lg)', padding: '12px 16px', textAlign: 'center' }}>
          <div style={{ fontWeight: 800, fontSize: 15, color: r.color }}>{r.label}</div>
          <div style={{ fontSize: 11, color: 'var(--clr-text-3)', marginTop: 2 }}>{r.min_score}+ score</div>
          <div style={{ fontSize: 11, color: 'var(--clr-text-3)', marginTop: 4 }}>{r.description}</div>
        </div>
      ))}
    </div>
  )
}

export default function AnalysisMethodologyModal({ onClose }) {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('technical')

  useEffect(() => {
    fetch(`${API}/api/methodology`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
  }, [])

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.5)',
      zIndex: 300, display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(4px)', padding: 20 }}
      onClick={onClose}
    >
      <div style={{ background: 'var(--clr-surface)', borderRadius: 'var(--r-2xl)',
        width: '100%', maxWidth: 820, maxHeight: '92vh', display: 'flex', flexDirection: 'column',
        boxShadow: 'var(--shadow-xl)', overflow: 'hidden' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--clr-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>📐 AI Analysis Methodology</div>
            <div style={{ fontSize: 13, color: 'var(--clr-text-3)', marginTop: 2 }}>
              How every stock recommendation is scored
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>✕ Close</button>
        </div>

        {/* Scrollable body */}
        <div style={{ overflowY: 'auto', flex: 1, padding: '20px 24px' }}>
          {!data ? (
            <div style={{ textAlign: 'center', padding: 48 }}><div className="loading-spinner" /></div>
          ) : (
            <>
              {/* Score formula */}
              <div className="card" style={{ marginBottom: 20 }}>
                <div className="card-title" style={{ marginBottom: 4 }}>Combined Scoring Formula</div>
                <div style={{ fontSize: 13, color: 'var(--clr-text-3)' }}>{data.scoring_formula?.description}</div>
                <ScoreFormula data={data} />
              </div>

              {/* Rating scale */}
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Rating Scale</div>
                <RatingScale ratings={data.rating_scale} />
              </div>

              {/* Portfolio weighting info */}
              <div style={{ background: 'var(--clr-primary-lt)', border: '1px solid #C7D2FE',
                borderRadius: 'var(--r-lg)', padding: '14px 18px', marginBottom: 20 }}>
                <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--clr-primary)', marginBottom: 8 }}>
                  🎯 How Broker Portfolio Enhances Recommendations
                </div>
                <ol style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {(data.portfolio_weighting?.steps || []).map((s, i) => (
                    <li key={i} style={{ fontSize: 13, color: 'var(--clr-text-2)' }}>{s}</li>
                  ))}
                </ol>
              </div>

              {/* Indicator tabs */}
              <div className="tabs">
                <button className={`tab-btn ${tab === 'technical' ? 'active' : ''}`} onClick={() => setTab('technical')}>
                  📈 Technical Indicators ({data.technical_indicators?.length})
                </button>
                <button className={`tab-btn ${tab === 'fundamental' ? 'active' : ''}`} onClick={() => setTab('fundamental')}>
                  📋 Fundamental Indicators ({data.fundamental_indicators?.length})
                </button>
              </div>

              {tab === 'technical' && (
                <div>
                  {(data.technical_indicators || []).map((ind, i) => (
                    <IndicatorCard key={i} indicator={ind} type="technical" />
                  ))}
                </div>
              )}

              {tab === 'fundamental' && (
                <div>
                  {(data.fundamental_indicators || []).map((ind, i) => (
                    <IndicatorCard key={i} indicator={ind} type="fundamental" />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
