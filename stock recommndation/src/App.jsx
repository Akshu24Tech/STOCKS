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
import { LayoutDashboard, Activity, Sparkles, BriefcaseBusiness, Eye, Brain, Menu, Bot } from 'lucide-react'

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

// ─── Navigation ───────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard', short: 'Home' },
  { path: '/live', icon: Activity, label: 'Live market', short: 'Market' },
  { path: '/recommendations', icon: Sparkles, label: 'AI picks', short: 'Picks' },
  { path: '/portfolio', icon: BriefcaseBusiness, label: 'My portfolio', short: 'Portfolio' },
  { path: '/watchlist', icon: Eye, label: 'Watchlist', short: 'Watchlist' },
  { path: '/quiz', icon: Brain, label: 'Risk profile', short: 'Risk' },
]

const STATUS_TEXT = {
  connected: 'Live NSE feed connected',
  connecting: 'Connecting to live feed…',
  disconnected: 'Live feed offline — retrying',
}

function Sidebar({ ticks, wsStatus, open, onClose }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { openStockModal } = useApp() || {}
  const tickArr = Object.values(ticks).slice(0, 8)
  const go = (path) => { navigate(path); onClose() }

  return (
    <>
      <div className={`rail-scrim ${open ? 'open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${open ? 'open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-logo">
          <div className="logo-mark">
            <div className="logo-icon">₹</div>
            <div>
              <div className="logo-text">IndiaStocks AI</div>
              <div className="logo-sub">Your market co-pilot</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-group">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon
              const active = pathname === item.path
              return (
                <button
                  key={item.path}
                  className={`nav-item ${active ? 'active' : ''}`}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => go(item.path)}
                >
                  <span className="nav-icon"><Icon size={18} strokeWidth={2} /></span>
                  {item.label}
                </button>
              )
            })}
          </div>

          {tickArr.length > 0 && (
            <div className="nav-group">
              <div className="nav-label">
                <span>Watching</span>
                <button onClick={() => go('/watchlist')}>Edit</button>
              </div>
              {tickArr.map(t => (
                <button key={t.symbol} className="rail-tick" onClick={() => { openStockModal(t.symbol); onClose() }}>
                  <span className="sym">{t.symbol}</span>
                  <span className={t.change_pct >= 0 ? 'up' : 'dn'}>
                    {t.change_pct >= 0 ? '+' : ''}{t.change_pct?.toFixed(2)}%
                  </span>
                </button>
              ))}
            </div>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className={`live-badge ${wsStatus}`}>
            <div className="live-dot" />
            {STATUS_TEXT[wsStatus] || STATUS_TEXT.disconnected}
          </div>
        </div>
      </aside>
    </>
  )
}

function BottomNav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  return (
    <nav className="bottom-nav" aria-label="Quick navigation">
      {NAV_ITEMS.slice(0, 5).map(item => {
        const Icon = item.icon
        return (
          <button key={item.path} className={pathname === item.path ? 'active' : ''} onClick={() => navigate(item.path)}>
            <Icon size={20} strokeWidth={2} />
            {item.short}
          </button>
        )
      })}
    </nav>
  )
}

// ─── Top bar with ticker tape ─────────────────────────────────────────────────
function TickerTape({ ticks, wsStatus, onSelectStock, onOpenAiConfig, onOpenMenu }) {
  const items = Object.values(ticks)
  const doubled = items.length ? [...items, ...items] : []
  const statusLabel = { connected: 'Live', connecting: 'Connecting', disconnected: 'Offline' }

  return (
    <header className="top-bar">
      <button className="menu-btn" onClick={onOpenMenu} aria-label="Open menu"><Menu size={18} /></button>
      <div className="ticker-wrap">
        {doubled.length > 0 ? (
          <div className="ticker-track">
            {doubled.map((t, i) => (
              <button
                key={`${t.symbol}-${i}`}
                className="ticker-item"
                onClick={() => onSelectStock && onSelectStock(t.symbol)}
                title={`Open ${t.symbol} details`}
                tabIndex={i >= items.length ? -1 : 0}
              >
                <span className="ticker-sym">{t.symbol}</span>
                <span className="ticker-price">₹{t.price?.toFixed(2)}</span>
                <span className={`ticker-chg ${t.change_pct >= 0 ? 'up' : 'dn'}`}>
                  {t.change_pct >= 0 ? '+' : '−'}{Math.abs(t.change_pct).toFixed(2)}%
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="ticker-empty">Live prices appear here once the backend is running.</div>
        )}
      </div>
      <div className={`ws-status ${wsStatus}`} title={STATUS_TEXT[wsStatus]}>
        <div className="live-dot" />
        <span className="label">{statusLabel[wsStatus] || 'Offline'}</span>
      </div>
      <button onClick={onOpenAiConfig} className="ai-settings-btn" title="Choose the AI model used for analysis">
        <Bot size={16} />
        <span className="label">AI settings</span>
        <span className="pulse-dot" />
      </button>
    </header>
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
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])

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
        <Sidebar ticks={ticks} wsStatus={wsStatus} open={menuOpen} onClose={() => setMenuOpen(false)} />
        <div className="main-content">
          <TickerTape
            ticks={ticks}
            wsStatus={wsStatus}
            onSelectStock={openStockModal}
            onOpenAiConfig={() => setShowAiConfig(true)}
            onOpenMenu={() => setMenuOpen(true)}
          />
          <main className="page-container">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/quiz" element={<QuizPage />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
              <Route path="/recommendations" element={<RecommendationsPage />} />
              <Route path="/live" element={<LiveFeedPage />} />
            </Routes>
          </main>
          <BottomNav />
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

