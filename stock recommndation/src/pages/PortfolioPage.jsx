import React, { useState, useEffect } from 'react'
import { useApp } from '../App'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import BrokerConnect from '../components/BrokerConnect'

import { API } from '../config'

const SECTOR_COLORS = [
  '#4F46E5', '#7C3AED', '#0891B2', '#059669', '#D97706',
  '#DC2626', '#DB2777', '#EA580C', '#65A30D', '#0369A1',
]

function PieChartCard({ title, data }) {
  const chartData = Object.entries(data || {}).map(([name, pct]) => ({ name, value: pct }))
  if (!chartData.length) return null
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-header"><div className="card-title">{title}</div></div>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie data={chartData} cx="50%" cy="50%" outerRadius={60} dataKey="value"
            label={({ name, value }) => `${name} ${value}%`} labelLine={false}>
            {chartData.map((_, i) => <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={v => `${v}%`} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function PortfolioPage() {
  const { portfolio, savePortfolio, ticks, openStockModal } = useApp()
  const [form, setForm] = useState({ symbol: '', qty: '', buy_price: '' })
  const [analysis, setAnalysis] = useState(null)
  const [analyzeLoading, setAnalyzeLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('manual') // 'manual' | 'broker'
  const [brokerPortfolio, setBrokerPortfolio] = useState(() => {
    try { return JSON.parse(localStorage.getItem('broker_portfolio') || '[]') } catch { return [] }
  })
  const [connectedBrokers, setConnectedBrokers] = useState(() => {
    try { return JSON.parse(localStorage.getItem('connected_brokers') || '[]') } catch { return [] }
  })

  const saveBrokerPortfolio = (p) => {
    setBrokerPortfolio(p)
    localStorage.setItem('broker_portfolio', JSON.stringify(p))
  }

  const addHolding = (e) => {
    e.preventDefault()
    if (!form.symbol || !form.qty || !form.buy_price) return
    const updated = [...portfolio, {
      symbol: form.symbol.toUpperCase().trim(),
      qty: parseFloat(form.qty),
      buy_price: parseFloat(form.buy_price),
    }]
    savePortfolio(updated)
    setForm({ symbol: '', qty: '', buy_price: '' })
  }

  const removeHolding = (idx) => savePortfolio(portfolio.filter((_, i) => i !== idx))

  const analyzePortfolio = async () => {
    const combined = [...portfolio, ...brokerPortfolio]
    if (!combined.length) return
    setAnalyzeLoading(true)
    try {
      const res = await fetch(`${API}/api/portfolio/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(combined),
      })
      setAnalysis(await res.json())
    } catch (e) { console.error(e) }
    setAnalyzeLoading(false)
  }

  const livePrice = (symbol) => {
    const sym = symbol.replace('.NS', '').replace('.BO', '').toUpperCase()
    return ticks[sym]?.price || null
  }

  const allHoldings = [...portfolio, ...brokerPortfolio]

  const totalCurrentValue = allHoldings.reduce((sum, h) => {
    const price = livePrice(h.symbol) || h.buy_price
    return sum + price * h.qty
  }, 0)
  const totalCost = allHoldings.reduce((sum, h) => sum + h.buy_price * h.qty, 0)
  const totalPnL = totalCurrentValue - totalCost
  const totalPnLPct = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0

  return (
    <div>
      <div className="page-header">
        <h1>My Portfolio 💼</h1>
        <p>Track holdings, connect brokers, and analyze your actual risk exposure</p>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ maxWidth: 420, marginBottom: 24 }}>
        <button className={`tab-btn ${activeTab === 'manual' ? 'active' : ''}`} onClick={() => setActiveTab('manual')}>
          ✏️ Manual Entry
        </button>
        <button className={`tab-btn ${activeTab === 'broker' ? 'active' : ''}`} onClick={() => setActiveTab('broker')}>
          🔗 Connect Broker {brokerPortfolio.length > 0 && `(${brokerPortfolio.length})`}
        </button>
      </div>

      <div className="portfolio-grid">
        {/* Left panel */}
        <div>
          {activeTab === 'manual' && (
            <>
              {/* Add form */}
              <div className="card" style={{ marginBottom: 20 }}>
                <div className="card-header"><div className="card-title">Add Holding</div></div>
                <form onSubmit={addHolding} className="portfolio-add-form">
                  <div className="form-group">
                    <label className="form-label">Symbol (NSE)</label>
                    <input className="form-input" placeholder="e.g. RELIANCE" value={form.symbol}
                      onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Qty</label>
                    <input className="form-input" type="number" placeholder="100" value={form.qty}
                      onChange={e => setForm(f => ({ ...f, qty: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Buy Price (₹)</label>
                    <input className="form-input" type="number" placeholder="2500" value={form.buy_price}
                      onChange={e => setForm(f => ({ ...f, buy_price: e.target.value }))} />
                  </div>
                  <div style={{ paddingBottom: 1 }}>
                    <button type="submit" className="btn btn-primary">+ Add</button>
                  </div>
                </form>
              </div>

              {/* Manual holdings */}
              {portfolio.length > 0 ? (
                <div className="card">
                  <div className="card-header">
                    <div>
                      <div className="card-title">Manual Holdings ({portfolio.length})</div>
                      <div className="card-subtitle">Live prices from tick feed</div>
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={analyzePortfolio} disabled={analyzeLoading}>
                      {analyzeLoading ? '⏳' : '🔍'} Analyze All
                    </button>
                  </div>
                  <HoldingsTable holdings={portfolio} livePrice={livePrice} onRemove={removeHolding}
                    totalValue={totalCurrentValue} totalCost={totalCost} totalPnL={totalPnL} totalPnLPct={totalPnLPct}
                    onSelectStock={openStockModal} />
                </div>
              ) : (
                <div className="card">
                  <div className="empty-state">
                    <div className="empty-state-icon">📋</div>
                    <h3>No manual holdings</h3>
                    <p>Add holdings above or connect your broker below for automatic import.</p>
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === 'broker' && (
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">Connect Your Broker</div>
                  <div className="card-subtitle">
                    Automatically import portfolio from Zerodha, Upstox, Angel One, or upload CSV
                  </div>
                </div>
              </div>

              {/* Broker-imported holdings preview */}
              {brokerPortfolio.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--clr-text-2)', marginBottom: 10 }}>
                    Imported Holdings ({brokerPortfolio.length})
                  </div>
                  <HoldingsTable
                    holdings={brokerPortfolio}
                    livePrice={livePrice}
                    onRemove={(idx) => saveBrokerPortfolio(brokerPortfolio.filter((_, i) => i !== idx))}
                    totalValue={0} totalCost={0} totalPnL={0} totalPnLPct={0}
                    compact
                    onSelectStock={openStockModal}
                  />
                  <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }}
                    onClick={analyzePortfolio} disabled={analyzeLoading}>
                    {analyzeLoading ? '⏳' : '🔍'} Analyze Broker Portfolio
                  </button>
                </div>
              )}

              {/* BrokerConnect component without API keys */}
              <BrokerConnect
                connectedBrokers={connectedBrokers}
                onHoldingsImported={(imported, brokerId) => {
                  const existingSyms = new Set(brokerPortfolio.map(h => h.symbol))
                  const newItems = imported.filter(h => !existingSyms.has(h.symbol))
                  const updated = [...brokerPortfolio, ...newItems]
                  saveBrokerPortfolio(updated)
                  if (!connectedBrokers.includes(brokerId)) {
                    const nextB = [...connectedBrokers, brokerId]
                    setConnectedBrokers(nextB)
                    localStorage.setItem('connected_brokers', JSON.stringify(nextB))
                  }
                }}
                onDisconnectBroker={(brokerId) => {
                  const nextB = connectedBrokers.filter(b => b !== brokerId)
                  setConnectedBrokers(nextB)
                  localStorage.setItem('connected_brokers', JSON.stringify(nextB))
                  const updated = brokerPortfolio.filter(h => !(h.source || '').toLowerCase().includes(brokerId))
                  saveBrokerPortfolio(updated)
                }}
              />
            </div>
          )}
        </div>

        {/* Right: Analysis */}
        <div>
          {/* Combined summary */}
          {allHoldings.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title" style={{ marginBottom: 12 }}>Combined Portfolio</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Holdings', value: allHoldings.length, sub: `${portfolio.length} manual + ${brokerPortfolio.length} imported` },
                  { label: 'Total Value', value: `₹${totalCurrentValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, sub: `Cost: ₹${totalCost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
                ].map(s => (
                  <div key={s.label} style={{ background: 'var(--clr-surface-2)', borderRadius: 'var(--r-md)', padding: '10px 14px' }}>
                    <div style={{ fontSize: 11, color: 'var(--clr-text-3)', fontWeight: 600, textTransform: 'uppercase' }}>{s.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: 'var(--clr-text-3)' }}>{s.sub}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, background: totalPnL >= 0 ? 'var(--clr-green-lt)' : 'var(--clr-red-lt)',
                borderRadius: 'var(--r-md)', padding: '10px 14px' }}>
                <div style={{ fontSize: 11, color: 'var(--clr-text-3)', fontWeight: 600, textTransform: 'uppercase' }}>Overall P&L</div>
                <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-mono)',
                  color: totalPnL >= 0 ? 'var(--clr-green)' : 'var(--clr-red)' }}>
                  {totalPnL >= 0 ? '+' : ''}₹{totalPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  <span style={{ fontSize: 14 }}> ({totalPnLPct.toFixed(2)}%)</span>
                </div>
              </div>
            </div>
          )}

          {analysis && (
            <>
              <div className="card" style={{ textAlign: 'center', marginBottom: 16 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>Portfolio Health Score</div>
                <div style={{ fontSize: 52, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--clr-primary)' }}>
                  {analysis.portfolio_score}
                </div>
                <div style={{ fontSize: 14, color: 'var(--clr-text-3)', marginBottom: 8 }}>
                  Rating: <strong>{analysis.portfolio_rating}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span className={`badge ${analysis.concentration_risk === 'Low' ? 'badge-green' : analysis.concentration_risk === 'Medium' ? 'badge-amber' : 'badge-red'}`}>
                    {analysis.concentration_risk} Concentration Risk
                  </span>
                  <span className="badge badge-blue">Diversification: {analysis.diversification_score}%</span>
                </div>
              </div>
              <PieChartCard title="Sector Breakdown" data={analysis.sector_breakdown} />
              <PieChartCard title="Asset Type" data={analysis.type_breakdown} />
            </>
          )}

          {!analysis && (
            <div className="card">
              <div className="empty-state">
                <div className="empty-state-icon">📊</div>
                <h3>Portfolio Analysis</h3>
                <p>Add holdings manually or connect your broker, then click "Analyze" to see sector exposure, risk metrics, and diversification score.</p>
                {allHoldings.length > 0 && (
                  <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={analyzePortfolio} disabled={analyzeLoading}>
                    {analyzeLoading ? '⏳ Analyzing…' : '🔍 Analyze Portfolio'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── HoldingsTable (shared) ───────────────────────────────────────────────────
function HoldingsTable({ holdings, livePrice, onRemove, compact, onSelectStock }) {
  const totalCurrentValue = holdings.reduce((sum, h) => {
    const price = livePrice(h.symbol) || h.buy_price
    return sum + price * h.qty
  }, 0)
  const totalCost = holdings.reduce((sum, h) => sum + h.buy_price * h.qty, 0)
  const totalPnL = totalCurrentValue - totalCost
  const totalPnLPct = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0

  if (!compact) {
    return (
      <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Total Cost', value: `₹${totalCost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            { label: 'Current Value', value: `₹${totalCurrentValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            { label: 'P&L', value: `${totalPnL >= 0 ? '+' : ''}₹${totalPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })} (${totalPnLPct.toFixed(2)}%)`, color: totalPnL >= 0 ? 'var(--clr-green)' : 'var(--clr-red)' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--clr-surface-2)', borderRadius: 'var(--r-md)', padding: '8px 12px' }}>
              <div style={{ fontSize: 10, color: 'var(--clr-text-3)', fontWeight: 700, textTransform: 'uppercase' }}>{s.label}</div>
              <div style={{ fontSize: 14, fontWeight: 800, fontFamily: 'var(--font-mono)', color: s.color || 'var(--clr-text)' }}>{s.value}</div>
            </div>
          ))}
        </div>
        <HoldingRows holdings={holdings} livePrice={livePrice} onRemove={onRemove} onSelectStock={onSelectStock} />
      </>
    )
  }
  return <HoldingRows holdings={holdings} livePrice={livePrice} onRemove={onRemove} onSelectStock={onSelectStock} />
}

function HoldingRows({ holdings, livePrice, onRemove, onSelectStock }) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Qty</th>
          <th>Buy</th>
          <th>Live</th>
          <th>P&L</th>
          <th>Source</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {holdings.map((h, i) => {
          const live = livePrice(h.symbol) || h.buy_price
          const pnlPct = ((live - h.buy_price) / h.buy_price) * 100
          return (
            <tr key={i}>
              <td>
                <span
                  className="mono"
                  style={{
                    fontWeight: 700,
                    cursor: onSelectStock ? 'pointer' : 'default',
                    color: onSelectStock ? 'var(--clr-primary)' : 'inherit',
                  }}
                  onClick={() => onSelectStock && onSelectStock(h.symbol)}
                  title="Click to view Tickertape Scorecard & Insights"
                >
                  {h.symbol} {onSelectStock && '↗'}
                </span>
              </td>
              <td className="mono">{h.qty}</td>
              <td className="mono">₹{h.buy_price?.toFixed(2)}</td>
              <td className="mono">₹{live.toFixed(2)}</td>
              <td><span className={`badge ${pnlPct >= 0 ? 'badge-green' : 'badge-red'}`}>{pnlPct.toFixed(2)}%</span></td>
              <td>
                {h.source && <span className="badge badge-gray" style={{ fontSize: 10 }}>{h.source}</span>}
              </td>
              <td>
                <button className="btn btn-danger btn-sm" onClick={() => onRemove(i)}>✕</button>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
