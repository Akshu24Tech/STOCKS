# IndiaStocks AI — Setup Guide

## 🚀 Quick Start

### Step 1: Start the Backend (FastAPI)
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or double-click **`start.bat`** to launch both services at once.

### Step 2: Start the Frontend (React/Vite)
```bash
npm run dev
```

Then open **http://localhost:3000**

---

## 📦 Features

| Feature | Details |
|---------|---------|
| 🧠 Risk Quiz | 10-question animated quiz → personalized risk score (0–100) |
| 💼 Portfolio Audit | Add holdings, track live P&L via WebSocket tick data |
| 🎯 AI Recommendations | Stocks & ETFs ranked by Technical (RSI, MACD, BB, MA) + Fundamental (P/E, ROE, EPS) analysis |
| 📈 Expected Returns | Historical CAGR for 1Y, 3Y, 5Y from yfinance |
| ⚡ Live Tick Feed | WebSocket from backend → Yahoo Finance tick data for NSE stocks |
| 🚀 Top Gainers/Losers | Real-time market movers |
| 🔥 Volume Shakers | High-volume stocks updated every 30s |

---

## 🛠 Architecture

```
Frontend (React/Vite :3000)
├── Sidebar navigation
├── Live ticker tape (WebSocket)
├── Pages: Home, Quiz, Portfolio, Recommendations, Live Feed
└── Proxy → Backend (:8000)

Backend (FastAPI :8000)
├── WebSocket /ws/feed       → Tick broadcaster (1s intervals)
├── GET /api/market/snapshot → Indices + watchlist prices
├── GET /api/market/gainers  → Top 10 NSE gainers
├── GET /api/market/losers   → Top 10 NSE losers
├── GET /api/market/volume   → Top 10 by volume
├── POST /api/quiz/score     → Risk score from quiz answers
├── POST /api/recommend      → AI-ranked stock recommendations
├── POST /api/portfolio/analyze → Portfolio risk + sector analysis
└── GET /api/stock/{sym}/analysis → Full TA + FA for one stock
```

---

## 📊 AI Scoring Formula

**Combined Score = 60% Technical + 40% Fundamental**

### Technical Signals
- RSI (14): Oversold (<30) = Bullish, Overbought (>70) = Bearish
- MACD: Histogram positive = Bullish
- Bollinger Bands: Near lower = Buy opportunity
- Moving Averages: 20/50/200 day alignment
- Golden Cross (MA50 > MA200): Long-term bullish signal
- Volume surge: >20% above 20-day average

### Fundamental Signals
- P/E Ratio: <15x = Undervalued, >40x = Expensive
- ROE: >20% = Strong, <12% = Weak
- Debt/Equity: <0.3 = Low risk, >2 = High risk
- EPS Growth: >20% = Strong
- Profit Margins: >15% = Strong

---

## 🌐 API Documentation
FastAPI auto-generates interactive docs at: **http://localhost:8000/docs**
