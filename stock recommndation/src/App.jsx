import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import QuizPage from './pages/QuizPage'
import PortfolioPage from './pages/PortfolioPage'
import RecommendationsPage from './pages/RecommendationsPage'
import LiveFeedPage from './pages/LiveFeedPage'
import HomePage from './pages/HomePage'
import WatchlistPage from './pages/WatchlistPage'
import TickertapeStockModal from './components/TickertapeStockModal'
import AIConfigModal from './components/AIConfigModal'
import { getWsUrl } from './config'

// ─── Global Context ──────────────────────────────────────────────────────────
export const AppContext = createContext(null)

export function useApp() { return useContext(AppContext) }

// ─── WebSocket Tick Store ─────────────────────────────────────────────────────
function useTickFeed() {
  const [ticks, setTicks] = useState({})
  const [wsStatus, setWsStatus] = useState('connecting') // 'connected' | 'connecting' | 'disconnected'
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  function connect() {
    setWsStatus('connecting')
    try {
      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onopen = () => setWsStatus('connected')

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
        setWsStatus('disconnected')
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    } catch (_) { setWsStatus('disconnected') }
  }

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) wsRef.current.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [])

  return { ticks, wsStatus }
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
  const { openStockModal } = useApp() || {}
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
                style={{ padding: '5px 10px', fontSize: 12, display: 'flex', justifyContent: 'space-between', cursor: 'pointer', borderRadius: 'var(--r-sm)', transition: 'background 0.15s' }}
                onClick={() => openStockModal(t.symbol)}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.08)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
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

// ─── Ticker Tape & Top Bar ───────────────────────────────────────────────────
function TickerTape({ ticks, wsStatus, onSelectStock, onOpenAiConfig }) {
  const items = Object.values(ticks)
  const doubled = items.length ? [...items, ...items] : []
  const statusLabel = { connected: '● Live', connecting: '◌ Connecting', disconnected: '○ Offline' }

  return (
    <div className="top-bar">
      <div className="ticker-wrap">
        {doubled.length > 0 ? (
          <div className="ticker-track">
            {doubled.map((t, i) => (
              <span
                key={`${t.symbol}-${i}`}
                className="ticker-item"
                onClick={() => onSelectStock && onSelectStock(t.symbol)}
                title="Click to view Scorecard & Forecasts"
              >
                <span className="ticker-sym">{t.symbol}</span>
                <span className="ticker-price">₹{t.price?.toFixed(2)}</span>
                <span className={`ticker-chg ${t.change_pct >= 0 ? 'up' : 'dn'}`}>
                  {t.change_pct >= 0 ? '▲' : '▼'}{Math.abs(t.change_pct).toFixed(2)}%
                </span>
              </span>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: 'var(--clr-text-3)', paddingLeft: 8 }}>
            Waiting for live data — start the backend to see real-time NSE ticks
          </div>
        )}
      </div>
      <div className={`ws-status ${wsStatus}`}>
        <div className="live-dot" style={{ width: 6, height: 6 }} />
        {statusLabel[wsStatus] || 'Offline'}
      </div>
      <button
        onClick={onOpenAiConfig}
        className="ai-settings-btn"
        title="Configure TradingAgents LLM Provider"
      >
        <span className="pulse-dot"></span>
        <span>🤖 TradingAgents AI</span>
      </button>
    </div>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const { ticks, wsStatus } = useTickFeed()
  const [selectedStock, setSelectedStock] = useState(null)
  const [showAiConfig, setShowAiConfig] = useState(false)
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
          <TickerTape
            ticks={ticks}
            wsStatus={wsStatus}
            onSelectStock={openStockModal}
            onOpenAiConfig={() => setShowAiConfig(true)}
          />
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

      <AIConfigModal
        isOpen={showAiConfig}
        onClose={() => setShowAiConfig(false)}
      />
    </AppContext.Provider>
  )
}

