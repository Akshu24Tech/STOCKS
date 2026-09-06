import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import QuizPage from './pages/QuizPage'
import PortfolioPage from './pages/PortfolioPage'
import RecommendationsPage from './pages/RecommendationsPage'
import LiveFeedPage from './pages/LiveFeedPage'
import HomePage from './pages/HomePage'
import WatchlistPage from './pages/WatchlistPage'
import TickertapeStockModal from './components/TickertapeStockModal'
import { getWsUrl } from './config'

// ─── Global Context ──────────────────────────────────────────────────────────
export const AppContext = createContext(null)

export function useApp() { return useContext(AppContext) }

// ─── WebSocket Tick Store ─────────────────────────────────────────────────────
function useTickFeed() {
  const [ticks, setTicks] = useState({})
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  function connect() {
    try {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === 'tick') {
          setTicks(prev => {
            const next = { ...prev }
            msg.data.forEach(t => { next[t.symbol] = t })
            return next
          })
        }
      }

      ws.onclose = () => {
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    } catch (_) {}
  }

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) wsRef.current.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [])

  return ticks
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { path: '/', icon: '🏠', label: 'Dashboard' },
  { path: '/watchlist', icon: '👁️', label: 'Watchlist' },
  { path: '/quiz', icon: '🧠', label: 'Risk Quiz' },
  { path: '/portfolio', icon: '💼', label: 'My Portfolio' },
  { path: '/recommendations', icon: '🎯', label: 'AI Picks' },
  { path: '/live', icon: '⚡', label: 'Live Market' },
]

function Sidebar({ ticks }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const tickArr = Object.values(ticks).slice(0, 10)

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">₹</div>
          <div>
            <div className="logo-text">IndiaStocks AI</div>
            <div className="logo-sub">Smart Advisor</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group">
          <div className="nav-label">Navigation</div>
          {NAV_ITEMS.map(item => (
            <button
              key={item.path}
              className={`nav-item ${pathname === item.path ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>

        {tickArr.length > 0 && (
          <div className="nav-group">
            <div
              className="nav-label"
              style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              onClick={() => navigate('/watchlist')}
            >
              <span>Live Watchlist</span>
              <span style={{ fontSize: 10, color: 'var(--clr-primary)' }}>Manage ⚙️</span>
            </div>
            {tickArr.map(t => (
              <div
                key={t.symbol}
                style={{ padding: '5px 10px', fontSize: 12, display: 'flex', justifyContent: 'space-between', cursor: 'pointer' }}
                onClick={() => navigate('/watchlist')}
              >
                <span style={{ fontWeight: 600, color: 'var(--clr-text-2)', fontFamily: 'var(--font-mono)' }}>{t.symbol}</span>
                <span className={t.change_pct >= 0 ? 'badge badge-green' : 'badge badge-red'} style={{ fontSize: 10, padding: '1px 6px' }}>
                  {t.change_pct >= 0 ? '+' : ''}{t.change_pct?.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="live-badge">
          <div className="live-dot" />
          NSE Live Feed Active
        </div>
      </div>
    </aside>
  )
}

// ─── Ticker Tape ──────────────────────────────────────────────────────────────
function TickerTape({ ticks, onSelectStock }) {
  const items = Object.values(ticks)
  if (!items.length) return null

  const doubled = [...items, ...items] // infinite scroll trick

  return (
    <div className="top-bar">
      <div className="ticker-wrap">
        <div className="ticker-track">
          {doubled.map((t, i) => (
            <span
              key={`${t.symbol}-${i}`}
              className="ticker-item"
              style={{ cursor: 'pointer' }}
              onClick={() => onSelectStock && onSelectStock(t.symbol)}
              title="Click to view Tickertape Scorecard & Forecasts"
            >
              <span className="ticker-sym">{t.symbol}</span>
              <span className="ticker-price">₹{t.price?.toFixed(2)}</span>
              <span className={`ticker-chg ${t.change_pct >= 0 ? 'up' : 'dn'}`}>
                {t.change_pct >= 0 ? '▲' : '▼'}{Math.abs(t.change_pct).toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const ticks = useTickFeed()
  const [selectedStock, setSelectedStock] = useState(null)
  const [riskScore, setRiskScore] = useState(() => {
    const s = localStorage.getItem('risk_score')
    return s ? parseInt(s) : null
  })
  const [portfolio, setPortfolio] = useState(() => {
    const p = localStorage.getItem('portfolio')
    return p ? JSON.parse(p) : []
  })
  const [quizAnswers, setQuizAnswers] = useState({})

  const saveRiskScore = (s) => {
    setRiskScore(s)
    localStorage.setItem('risk_score', s)
  }

  const savePortfolio = (p) => {
    setPortfolio(p)
    localStorage.setItem('portfolio', JSON.stringify(p))
  }

  const openStockModal = (sym) => {
    if (!sym) return
    const clean = sym.replace('.NS', '').replace('.BO', '').toUpperCase()
    setSelectedStock(clean)
  }

  return (
    <AppContext.Provider value={{
      ticks,
      riskScore,
      saveRiskScore,
      portfolio,
      savePortfolio,
      quizAnswers,
      setQuizAnswers,
      openStockModal,
    }}>
      <div className="app-layout">
        <Sidebar ticks={ticks} />
        <div className="main-content">
          <TickerTape ticks={ticks} onSelectStock={openStockModal} />
          <div className="page-container">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/quiz" element={<QuizPage />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
              <Route path="/recommendations" element={<RecommendationsPage />} />
              <Route path="/live" element={<LiveFeedPage />} />
            </Routes>
          </div>
        </div>
      </div>

      {selectedStock && (
        <TickertapeStockModal
          symbol={selectedStock}
          ticks={ticks}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </AppContext.Provider>
  )
}

