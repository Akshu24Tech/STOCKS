import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'

import { API } from '../config'

const DEFAULT_WATCHLIST = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Conglomerate', target_price: 3100, note: 'Core holding, accumulate on dips' },
  { symbol: 'TCS', name: 'Tata Consultancy Services', sector: 'IT', target_price: 4200, note: 'Quality compounding dividend payer' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', sector: 'Banking', target_price: 1750, note: 'Leading private bank' },
  { symbol: 'TATAMOTORS', name: 'Tata Motors', sector: 'Auto', target_price: 1100, note: 'EV & JLR commercial vehicle turnaround' },
  { symbol: 'ZOMATO', name: 'Zomato Ltd', sector: 'Tech/Food', target_price: 250, note: 'Blinkit quick-commerce high growth' },
  { symbol: 'BAJFINANCE', name: 'Bajaj Finance', sector: 'NBFC', target_price: 7800, note: 'Top consumer lending franchise' },
  { symbol: 'NIFTYBEES', name: 'Nifty BeES ETF', sector: 'Index', target_price: 260, note: 'Broad market benchmark ETF' },
  { symbol: 'GOLDBEES', name: 'Gold BeES ETF', sector: 'Gold', target_price: 65, note: 'Portfolio inflation hedge' },
]

const QUICK_SUGGESTIONS = [
  'INFY', 'ICICIBANK', 'HAL', 'BEL', 'TITAN', 'MARUTI', 'DIXON', 'POLYCAB', 'TRENT', 'SUZLON', 'BANKBEES'
]

export default function WatchlistPage() {
  const { ticks } = useApp()
  const navigate = useNavigate()

  const [watchlist, setWatchlist] = useState(() => {
    try {
      const saved = localStorage.getItem('custom_watchlist')
      return saved ? JSON.parse(saved) : DEFAULT_WATCHLIST
    } catch {
      return DEFAULT_WATCHLIST
    }
  })

  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // 'all' | 'gainers' | 'losers'
  const [newSymbol, setNewSymbol] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [newNote, setNewNote] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [niftyStocks, setNiftyStocks] = useState([])
  const [stockDetails, setStockDetails] = useState({})

  // Save to localStorage
  const saveWatchlist = (items) => {
    setWatchlist(items)
    localStorage.setItem('custom_watchlist', JSON.stringify(items))
  }

  // Load Nifty 500 stocks for autocomplete
  useEffect(() => {
    fetch(`${API}/api/nifty500/stocks`)
      .then(r => r.json())
      .then(setNiftyStocks)
      .catch(() => {})
  }, [])

  // Fetch 5-year CAGR and RSI for watchlist items
  useEffect(() => {
    watchlist.forEach(item => {
      if (!stockDetails[item.symbol]) {
        fetch(`${API}/api/stock/${item.symbol}/analysis`)
          .then(r => r.json())
          .then(data => {
            if (data && !data.error) {
              setStockDetails(prev => ({ ...prev, [item.symbol]: data }))
            }
          })
          .catch(() => {})
      }
    })
  }, [watchlist])

  // Add stock to watchlist
  const handleAddStock = (sym, target = null, note = '') => {
    const clean = sym.replace('.NS', '').replace('.BO', '').toUpperCase().trim()
    if (!clean) return
    if (watchlist.some(w => w.symbol === clean)) {
      alert(`${clean} is already in your watchlist!`)
      return
    }

    const matchedNifty = niftyStocks.find(s => s.symbol === clean)
    const newItem = {
      symbol: clean,
      name: matchedNifty?.name || clean,
      sector: matchedNifty?.sector || 'Diversified',
      target_price: target ? parseFloat(target) : null,
      note: note || '',
      added_at: new Date().toLocaleDateString('en-IN'),
    }

    const updated = [newItem, ...watchlist]
    saveWatchlist(updated)
    setNewSymbol('')
    setNewTarget('')
    setNewNote('')
    setShowAddModal(false)
  }

  // Remove stock
  const handleRemoveStock = (symbol) => {
    const updated = watchlist.filter(w => w.symbol !== symbol)
    saveWatchlist(updated)
  }

  // Update stock target/note
  const handleUpdateStock = (e) => {
    e.preventDefault()
    if (!editingItem) return
    const updated = watchlist.map(w => {
      if (w.symbol === editingItem.symbol) {
        return {
          ...w,
          target_price: editingItem.target_price ? parseFloat(editingItem.target_price) : null,
          note: editingItem.note || '',
        }
      }
      return w
    })
    saveWatchlist(updated)
    setEditingItem(null)
  }

  // Live price helpers
  const getLive = (sym) => ticks[sym] || null

  const filteredWatchlist = watchlist
    .filter(item => {
      if (!search) return true
      const q = search.toLowerCase()
      return item.symbol.toLowerCase().includes(q) || (item.name && item.name.toLowerCase().includes(q))
    })
    .filter(item => {
      if (filter === 'all') return true
      const live = getLive(item.symbol)
      if (!live) return true
      if (filter === 'gainers') return live.change_pct >= 0
      if (filter === 'losers') return live.change_pct < 0
      return true
    })

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1>Smart Watchlist 👁️</h1>
          <p>Monitor your favorite Indian stocks, set target buy prices, notes, and track 5-year returns</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowAddModal(true)}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <span>+</span> Add Stock to Watchlist
        </button>
      </div>

      {/* Quick Suggestions Banner */}
      <div style={{
        background: 'var(--clr-surface)',
        border: '1px solid var(--clr-border)',
        borderRadius: 'var(--r-lg)',
        padding: '14px 18px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 10,
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--clr-text-3)', textTransform: 'uppercase' }}>
          Quick Add:
        </span>
        {QUICK_SUGGESTIONS.map(s => {
          const inList = watchlist.some(w => w.symbol === s)
          return (
            <button
              key={s}
              style={{
                background: inList ? 'var(--clr-surface-2)' : 'var(--clr-primary-lt)',
                color: inList ? 'var(--clr-text-3)' : 'var(--clr-primary)',
                border: '1px solid var(--clr-border)',
                borderRadius: 14,
                padding: '3px 10px',
                fontSize: 11,
                fontWeight: 600,
                cursor: inList ? 'default' : 'pointer',
              }}
              disabled={inList}
              onClick={() => handleAddStock(s)}
            >
              {s} {inList ? '✓' : '+'}
            </button>
          )
        })}
      </div>

      {/* Controls Bar: Search & Filter */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 20,
      }}>
        <div style={{ display: 'flex', gap: 10, flex: 1, minWidth: 260 }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search watchlist by symbol or name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ maxWidth: 360 }}
          />
        </div>

        <div className="tabs" style={{ marginBottom: 0, width: 'auto' }}>
          <button className={`tab-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
            All ({watchlist.length})
          </button>
          <button className={`tab-btn ${filter === 'gainers' ? 'active' : ''}`} onClick={() => setFilter('gainers')}>
            📈 Gainers
          </button>
          <button className={`tab-btn ${filter === 'losers' ? 'active' : ''}`} onClick={() => setFilter('losers')}>
            📉 Losers
          </button>
        </div>
      </div>

      {/* Watchlist Table / Grid */}
      {filteredWatchlist.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <h3>No stocks in this view</h3>
          <p style={{ color: 'var(--clr-text-3)', marginTop: 4 }}>Add a new stock from the top button or try changing filters.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="holdings-table" style={{ margin: 0 }}>
              <thead>
                <tr>
                  <th>Stock / Symbol</th>
                  <th>Live Price</th>
                  <th>Day Change</th>
                  <th>5Y CAGR Return</th>
                  <th>Target Price</th>
                  <th>Notes / Alert</th>
                  <th>AI Rating</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredWatchlist.map(item => {
                  const live = getLive(item.symbol)
                  const details = stockDetails[item.symbol]
                  const price = live?.price || details?.current_price || null
                  const changePct = live?.change_pct ?? 0
                  const isUp = changePct >= 0
                  const cagr5y = details?.expected_returns?.['5y_cagr']
                  const rating = details?.combined_rating || 'Buy'

                  // Check if price reached target
                  const targetReached = item.target_price && price && (
                    item.target_price >= price // Price is below or equal to target buy price
                  )

                  return (
                    <tr key={item.symbol}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div>
                            <div style={{ fontWeight: 800, fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--clr-text-1)' }}>
                              {item.symbol}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--clr-text-3)' }}>
                              {item.name || item.symbol} · <span className="badge badge-gray" style={{ fontSize: 9 }}>{item.sector || 'Stock'}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: 14 }}>
                          {price ? `₹${price.toFixed(2)}` : <span className="skeleton" style={{ width: 60, height: 16, display: 'inline-block' }} />}
                        </div>
                      </td>
                      <td>
                        {live ? (
                          <span className={`badge ${isUp ? 'badge-green' : 'badge-red'}`} style={{ fontSize: 11, padding: '2px 8px' }}>
                            {isUp ? '▲ +' : '▼ '}{changePct.toFixed(2)}%
                          </span>
                        ) : (
                          <span style={{ fontSize: 12, color: 'var(--clr-text-3)' }}>—</span>
                        )}
                      </td>
                      <td>
                        {cagr5y != null ? (
                          <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: cagr5y >= 0 ? 'var(--clr-green)' : 'var(--clr-red)' }}>
                            {cagr5y >= 0 ? '+' : ''}{cagr5y}%
                          </span>
                        ) : (
                          <span style={{ fontSize: 12, color: 'var(--clr-text-3)' }}>Analyzing…</span>
                        )}
                      </td>
                      <td>
                        {item.target_price ? (
                          <div>
                            <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                              ₹{item.target_price}
                            </span>
                            {targetReached && (
                              <span className="badge badge-green" style={{ fontSize: 9, marginLeft: 6 }}>
                                🎯 In Buy Zone!
                              </span>
                            )}
                          </div>
                        ) : (
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 11, padding: '2px 6px', color: 'var(--clr-primary)' }}
                            onClick={() => setEditingItem(item)}
                          >
                            + Set Target
                          </button>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: 12, color: item.note ? 'var(--clr-text-2)' : 'var(--clr-text-3)', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {item.note || '—'}
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${rating.includes('Buy') ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: 10 }}>
                          {rating}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: 6 }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: 11, padding: '4px 8px' }}
                            title="Update Target / Notes"
                            onClick={() => setEditingItem(item)}
                          >
                            ✏️ Edit
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 11, padding: '4px 8px', color: 'var(--clr-red)' }}
                            title="Remove from Watchlist"
                            onClick={() => handleRemoveStock(item.symbol)}
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Stock Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()} style={{ maxWidth: 460 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>Add Stock to Watchlist</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowAddModal(false)}>✕</button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); handleAddStock(newSymbol, newTarget, newNote); }}>
              <div className="form-group">
                <label className="form-label">Stock Symbol (NSE)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. INFY, TATAMOTORS, HAL"
                  value={newSymbol}
                  onChange={e => setNewSymbol(e.target.value.toUpperCase())}
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label">Target Buy Price (₹) — Optional</label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="e.g. 1500"
                  value={newTarget}
                  onChange={e => setNewTarget(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Custom Note / Strategy — Optional</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Long-term compounder, buy on 5% dip"
                  value={newNote}
                  onChange={e => setNewNote(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  + Add to Watchlist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Update Stock Modal */}
      {editingItem && (
        <div className="modal-overlay" onClick={() => setEditingItem(null)}>
          <div className="modal-box" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>Update {editingItem.symbol}</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setEditingItem(null)}>✕</button>
            </div>

            <form onSubmit={handleUpdateStock}>
              <div className="form-group">
                <label className="form-label">Target Buy Price (₹)</label>
                <input
                  type="number"
                  className="form-input"
                  placeholder="e.g. 1500"
                  value={editingItem.target_price || ''}
                  onChange={e => setEditingItem({ ...editingItem, target_price: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Notes & Investment Thesis</label>
                <textarea
                  className="form-input"
                  rows={3}
                  placeholder="Add your reasons for watching this stock, support levels, etc."
                  value={editingItem.note || ''}
                  onChange={e => setEditingItem({ ...editingItem, note: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setEditingItem(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
