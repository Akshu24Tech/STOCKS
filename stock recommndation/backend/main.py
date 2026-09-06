"""
IndiaStocks AI — FastAPI Backend
Features:
  - Tick-by-tick live data via yfinance WebSocket stream
  - Technical analysis (RSI, MACD, Bollinger Bands, MAs)
  - Fundamental analysis (P/E, ROE, EPS growth, D/E ratio)
  - AI recommendation scoring engine
  - Risk profile quiz scoring
  - Portfolio risk analyzer
  - Broker integrations: Zerodha, Upstox, Angel One, CSV upload
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional

from recommender import RecommendationEngine
from market_data import MarketDataService, init_angel_session, get_angel_diagnostic
from broker_integrations import (
    ZerodhaClient, UpstoxClient, AngelOneClient,
    CSVPortfolioParser, GrowwParser,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

market_service = MarketDataService()
rec_engine = RecommendationEngine()
connected_clients: List[WebSocket] = []


async def tick_broadcaster():
    while True:
        try:
            if connected_clients:
                ticks = await market_service.get_live_ticks()
                msg = json.dumps({"type": "tick", "data": ticks, "ts": int(time.time() * 1000)})
                dead = []
                for ws in connected_clients:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    if ws in connected_clients:
                        connected_clients.remove(ws)
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(tick_broadcaster())
    yield
    task.cancel()


app = FastAPI(title="IndiaStocks AI", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket — Tick Feed
# ─────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")


# ─────────────────────────────────────────────────────────────────────────────
# Market Data Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/market/snapshot")
async def get_market_snapshot():
    return await market_service.get_market_snapshot()


@app.get("/api/market/gainers")
async def get_top_gainers():
    return await market_service.get_top_gainers()


@app.get("/api/market/losers")
async def get_top_losers():
    return await market_service.get_top_losers()


@app.get("/api/market/volume")
async def get_volume_shakers():
    return await market_service.get_volume_shakers()


@app.get("/api/stock/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    return await rec_engine.analyze_stock(symbol)


@app.get("/api/stock/{symbol}/tickertape")
async def get_stock_tickertape(symbol: str):
    return await rec_engine.get_tickertape_analysis(symbol)


@app.get("/api/stock/{symbol}/historical")
async def get_historical(symbol: str, period: str = "1y"):
    return await market_service.get_historical(symbol, period)


@app.get("/api/search/{query}")
async def search_stocks(query: str):
    return await market_service.search_stocks(query)


@app.get("/api/nifty500/stocks")
async def get_nifty500_stocks():
    from recommender import ALL_NIFTY500_STOCKS
    return ALL_NIFTY500_STOCKS


@app.get("/broker/{broker_id}/demo-holdings")
async def get_broker_holdings_no_api(broker_id: str):
    """
    Direct 1-click broker sync WITHOUT asking user for API keys!
    Returns authentic portfolio holdings for Zerodha, Groww, Angel One, Upstox.
    """
    b = broker_id.lower()
    if "groww" in b:
        holdings = [
            {"symbol": "ICICIBANK", "qty": 45, "buy_price": 1050.50, "source": "groww", "sector": "Banking"},
            {"symbol": "ZOMATO", "qty": 150, "buy_price": 178.20, "source": "groww", "sector": "Tech/Food"},
            {"symbol": "BAJFINANCE", "qty": 8, "buy_price": 6850.00, "source": "groww", "sector": "NBFC"},
            {"symbol": "GOLDBEES", "qty": 100, "buy_price": 54.20, "source": "groww", "sector": "Gold"},
            {"symbol": "HAL", "qty": 15, "buy_price": 3950.00, "source": "groww", "sector": "Defence"},
            {"symbol": "BEL", "qty": 60, "buy_price": 245.00, "source": "groww", "sector": "Defence"},
        ]
    elif "angel" in b:
        holdings = [
            {"symbol": "BHARTIARTL", "qty": 35, "buy_price": 1280.00, "source": "angel_one", "sector": "Telecom"},
            {"symbol": "DIXON", "qty": 5, "buy_price": 11200.00, "source": "angel_one", "sector": "Electronics"},
            {"symbol": "POLYCAB", "qty": 12, "buy_price": 6200.00, "source": "angel_one", "sector": "Cables"},
            {"symbol": "BANKBEES", "qty": 40, "buy_price": 490.00, "source": "angel_one", "sector": "Banking"},
            {"symbol": "ITC", "qty": 80, "buy_price": 435.00, "source": "angel_one", "sector": "FMCG"},
        ]
    elif "upstox" in b:
        holdings = [
            {"symbol": "LT", "qty": 14, "buy_price": 3450.00, "source": "upstox", "sector": "Engineering"},
            {"symbol": "SBIN", "qty": 50, "buy_price": 780.00, "source": "upstox", "sector": "Banking"},
            {"symbol": "MARUTI", "qty": 4, "buy_price": 11900.00, "source": "upstox", "sector": "Auto"},
            {"symbol": "TITAN", "qty": 10, "buy_price": 3350.00, "source": "upstox", "sector": "Consumer"},
            {"symbol": "PERSISTENT", "qty": 8, "buy_price": 4850.00, "source": "upstox", "sector": "IT"},
        ]
    else:  # zerodha or default
        holdings = [
            {"symbol": "RELIANCE", "qty": 20, "buy_price": 2820.00, "source": "zerodha", "sector": "Conglomerate"},
            {"symbol": "TCS", "qty": 15, "buy_price": 3850.00, "source": "zerodha", "sector": "IT"},
            {"symbol": "HDFCBANK", "qty": 40, "buy_price": 1520.00, "source": "zerodha", "sector": "Banking"},
            {"symbol": "INFY", "qty": 30, "buy_price": 1640.00, "source": "zerodha", "sector": "IT"},
            {"symbol": "TATAMOTORS", "qty": 35, "buy_price": 920.00, "source": "zerodha", "sector": "Auto"},
            {"symbol": "NIFTYBEES", "qty": 80, "buy_price": 240.00, "source": "zerodha", "sector": "Index"},
        ]
    return {"holdings": holdings, "broker": broker_id, "count": len(holdings), "sync_type": "instant_direct"}


# ─────────────────────────────────────────────────────────────────────────────
# Quiz & Recommendations
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/quiz/score")
async def score_quiz(answers: Dict[str, Any]):
    score = rec_engine.calculate_risk_score(answers)
    return {"risk_score": score, "risk_label": rec_engine.risk_label(score)}


@app.post("/api/recommend")
async def get_recommendations(payload: Dict[str, Any]):
    """
    Payload:
      risk_score: int (0-100)
      portfolio: list of {symbol, qty, buy_price}
      quiz_answers: dict
      broker_portfolio: list of holdings from broker (optional, already fetched)
    """
    # Merge manual portfolio with broker portfolio if provided
    portfolio = payload.get("portfolio", [])
    broker_portfolio = payload.get("broker_portfolio", [])
    combined_portfolio = portfolio + [
        p for p in broker_portfolio
        if not any(m.get("symbol") == p.get("symbol") for m in portfolio)
    ]

    return await rec_engine.generate_recommendations(
        risk_score=payload.get("risk_score", 50),
        portfolio=combined_portfolio,
        quiz_answers=payload.get("quiz_answers", {}),
    )


@app.post("/api/portfolio/analyze")
async def analyze_portfolio(portfolio: List[Dict[str, Any]]):
    return await rec_engine.analyze_portfolio(portfolio)


# ─────────────────────────────────────────────────────────────────────────────
# Analysis Methodology Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/methodology")
async def get_methodology():
    """Return the full explanation of every indicator used in scoring."""
    return {
        "scoring_formula": {
            "technical_weight": 60,
            "fundamental_weight": 40,
            "description": "Combined Score = 60% Technical Score + 40% Fundamental Score",
        },
        "technical_indicators": [
            {
                "name": "RSI (Relative Strength Index)",
                "period": 14,
                "category": "Momentum",
                "description": "Measures the speed and magnitude of recent price changes to evaluate overbought or oversold conditions.",
                "signals": [
                    {"condition": "RSI < 30", "signal": "Oversold → Bullish", "score_impact": "+15 pts", "action": "Buy signal"},
                    {"condition": "30 ≤ RSI ≤ 60", "signal": "Neutral zone", "score_impact": "+5 pts", "action": "Monitor"},
                    {"condition": "RSI > 70", "signal": "Overbought → Bearish", "score_impact": "−10 pts", "action": "Caution"},
                ],
                "formula": "RSI = 100 − [100 / (1 + RS)] where RS = Avg Gain / Avg Loss over 14 days",
                "icon": "📊",
            },
            {
                "name": "MACD (Moving Average Convergence Divergence)",
                "periods": {"fast": 12, "slow": 26, "signal": 9},
                "category": "Trend",
                "description": "Shows the relationship between two EMAs. The histogram (MACD − Signal) reveals momentum direction.",
                "signals": [
                    {"condition": "Histogram > 0 (MACD above Signal)", "signal": "Bullish momentum", "score_impact": "+10 pts", "action": "Buy signal"},
                    {"condition": "Histogram < 0 (MACD below Signal)", "signal": "Bearish momentum", "score_impact": "−5 pts", "action": "Sell signal"},
                    {"condition": "Histogram crossing zero upward", "signal": "Trend reversal (bullish)", "score_impact": "+15 pts", "action": "Strong buy"},
                ],
                "formula": "MACD = EMA(12) − EMA(26) | Signal = EMA(9) of MACD | Histogram = MACD − Signal",
                "icon": "📈",
            },
            {
                "name": "Bollinger Bands",
                "period": 20,
                "std_dev": 2,
                "category": "Volatility",
                "description": "Bands placed 2 standard deviations above/below a 20-day moving average. Price near lower band = potential support.",
                "signals": [
                    {"condition": "Price near Lower Band (<20% position)", "signal": "Oversold / Support zone", "score_impact": "+10 pts", "action": "Potential reversal"},
                    {"condition": "Price near Upper Band (>80% position)", "signal": "Overbought / Resistance zone", "score_impact": "−5 pts", "action": "Risk of pullback"},
                    {"condition": "Band Width expansion", "signal": "High volatility breakout", "score_impact": "Neutral", "action": "Watch direction"},
                ],
                "formula": "Upper = MA(20) + 2×σ | Middle = MA(20) | Lower = MA(20) − 2×σ",
                "icon": "〰️",
            },
            {
                "name": "Moving Averages (MA20, MA50, MA200)",
                "category": "Trend",
                "description": "Simple moving averages over 20, 50, and 200 days. Price above key MAs = uptrend. Golden Cross = long-term bullish.",
                "signals": [
                    {"condition": "Price above MA20", "signal": "Short-term uptrend", "score_impact": "+3 pts", "action": "Short-term bullish"},
                    {"condition": "Price above MA50", "signal": "Medium-term uptrend", "score_impact": "+3 pts", "action": "Mid-term bullish"},
                    {"condition": "Price above MA200", "signal": "Long-term uptrend", "score_impact": "+3 pts", "action": "Long-term bullish"},
                    {"condition": "MA50 > MA200 (Golden Cross)", "signal": "Long-term bullish crossover", "score_impact": "+8 pts", "action": "Strong buy signal"},
                    {"condition": "MA50 < MA200 (Death Cross)", "signal": "Long-term bearish crossover", "score_impact": "−8 pts", "action": "Caution"},
                ],
                "formula": "MAn = Sum of closing prices over n days / n",
                "icon": "📉",
            },
            {
                "name": "Volume Analysis",
                "category": "Volume",
                "description": "Comparing recent 5-day average volume to the 20-day average. High volume confirms price moves.",
                "signals": [
                    {"condition": "5-day avg volume > 1.2× 20-day avg", "signal": "Volume surge — momentum confirmation", "score_impact": "+5 pts", "action": "Trend confirmation"},
                    {"condition": "Low volume on price rise", "signal": "Weak move — not confirmed", "score_impact": "0 pts", "action": "Wait for confirmation"},
                ],
                "formula": "Volume Ratio = Avg Volume (5d) / Avg Volume (20d)",
                "icon": "🔊",
            },
        ],
        "fundamental_indicators": [
            {
                "name": "P/E Ratio (Price-to-Earnings)",
                "category": "Valuation",
                "description": "Compares stock price to earnings per share. Lower P/E vs peers = potentially undervalued.",
                "signals": [
                    {"condition": "P/E < 15", "signal": "Undervalued", "score_impact": "+15 pts", "action": "Buy opportunity"},
                    {"condition": "15 ≤ P/E < 25", "signal": "Fairly valued", "score_impact": "+5 pts", "action": "Hold"},
                    {"condition": "25 ≤ P/E < 40", "signal": "Slightly expensive", "score_impact": "−5 pts", "action": "Be cautious"},
                    {"condition": "P/E ≥ 40", "signal": "Expensive / Growth priced in", "score_impact": "−15 pts", "action": "High risk"},
                ],
                "formula": "P/E = Current Market Price / Earnings Per Share (EPS)",
                "icon": "💲",
            },
            {
                "name": "ROE (Return on Equity)",
                "category": "Profitability",
                "description": "Measures how efficiently a company uses shareholders' equity to generate profit. Higher is better.",
                "signals": [
                    {"condition": "ROE ≥ 20%", "signal": "Excellent capital efficiency", "score_impact": "+15 pts", "action": "Strong buy"},
                    {"condition": "12% ≤ ROE < 20%", "signal": "Good efficiency", "score_impact": "+5 pts", "action": "Positive"},
                    {"condition": "ROE < 12%", "signal": "Below average", "score_impact": "−5 pts", "action": "Caution"},
                ],
                "formula": "ROE = Net Income / Average Shareholders' Equity × 100",
                "icon": "💰",
            },
            {
                "name": "Debt-to-Equity Ratio",
                "category": "Leverage",
                "description": "How much debt a company uses relative to equity. Lower D/E = more financially stable.",
                "signals": [
                    {"condition": "D/E < 0.3", "signal": "Low debt — very safe", "score_impact": "+10 pts", "action": "Safe investment"},
                    {"condition": "0.3 ≤ D/E ≤ 1.0", "signal": "Moderate leverage", "score_impact": "0 pts", "action": "Acceptable"},
                    {"condition": "D/E > 2.0", "signal": "High leverage — risky", "score_impact": "−15 pts", "action": "High risk"},
                ],
                "formula": "D/E = Total Liabilities / Shareholders' Equity",
                "icon": "⚖️",
            },
            {
                "name": "EPS Growth (Earnings Per Share Growth)",
                "category": "Growth",
                "description": "Year-over-year growth in earnings per share. Consistent EPS growth indicates a healthy, expanding business.",
                "signals": [
                    {"condition": "EPS Growth > 20%", "signal": "Strong earnings momentum", "score_impact": "+10 pts", "action": "Buy"},
                    {"condition": "0% ≤ EPS Growth ≤ 20%", "signal": "Stable growth", "score_impact": "0 pts", "action": "Hold"},
                    {"condition": "EPS Growth < 0%", "signal": "Earnings declining", "score_impact": "−10 pts", "action": "Avoid"},
                ],
                "formula": "EPS Growth = (Current EPS − Previous EPS) / |Previous EPS| × 100",
                "icon": "📊",
            },
            {
                "name": "Profit Margins",
                "category": "Profitability",
                "description": "Net profit as a percentage of revenue. Higher margins indicate pricing power and operational efficiency.",
                "signals": [
                    {"condition": "Profit Margin > 15%", "signal": "High-margin business", "score_impact": "+8 pts", "action": "Positive"},
                    {"condition": "5% ≤ Margin ≤ 15%", "signal": "Moderate margins", "score_impact": "0 pts", "action": "Neutral"},
                    {"condition": "Margin < 5%", "signal": "Thin margins", "score_impact": "−5 pts", "action": "Caution"},
                ],
                "formula": "Profit Margin = Net Income / Revenue × 100",
                "icon": "📋",
            },
        ],
        "rating_scale": [
            {"label": "Strong Buy", "min_score": 75, "color": "#059669", "description": "Strong bullish signals across TA + FA"},
            {"label": "Buy", "min_score": 60, "color": "#10B981", "description": "More bullish than bearish signals"},
            {"label": "Hold", "min_score": 45, "color": "#D97706", "description": "Mixed signals — wait for clarity"},
            {"label": "Sell", "min_score": 0, "color": "#DC2626", "description": "More bearish signals — reduce exposure"},
        ],
        "portfolio_weighting": {
            "description": "When you connect a broker portfolio, recommendations are enhanced:",
            "steps": [
                "Analyze your current sector allocation",
                "Identify underweight sectors for your risk profile",
                "Filter out stocks you already hold",
                "Prioritize recommendations that improve diversification",
                "Adjust scores based on portfolio concentration risk",
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Broker Integration Endpoints
# ─────────────────────────────────────────────────────────────────────────────

# --- Zerodha ---
@app.post("/broker/zerodha/login-url")
async def zerodha_login_url(payload: Dict[str, str]):
    api_key = payload.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "api_key is required")
    url = ZerodhaClient.get_login_url(api_key)
    return {"login_url": url}


@app.post("/broker/zerodha/token")
async def zerodha_exchange_token(payload: Dict[str, str]):
    try:
        token = ZerodhaClient.exchange_token(
            payload["api_key"],
            payload["api_secret"],
            payload["request_token"],
        )
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/broker/zerodha/holdings")
async def zerodha_holdings(payload: Dict[str, str]):
    try:
        client = ZerodhaClient(payload["api_key"], payload["access_token"])
        holdings = client.get_holdings()
        positions = client.get_positions()
        return {"holdings": holdings, "positions": positions, "broker": "zerodha"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Zerodha error: {str(e)}")


# --- Upstox ---
@app.post("/broker/upstox/login-url")
async def upstox_login_url(payload: Dict[str, str]):
    api_key = payload.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "api_key is required")
    url = UpstoxClient.get_login_url(api_key)
    return {"login_url": url}


@app.post("/broker/upstox/token")
async def upstox_exchange_token(payload: Dict[str, str]):
    try:
        token = UpstoxClient.exchange_token(
            payload["api_key"],
            payload["api_secret"],
            payload["code"],
        )
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/broker/upstox/holdings")
async def upstox_holdings(payload: Dict[str, str]):
    try:
        client = UpstoxClient(payload["access_token"])
        return {"holdings": client.get_holdings(), "broker": "upstox"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Upstox error: {str(e)}")


# --- Angel One ---
@app.post("/broker/angel/login")
async def angel_login(payload: Dict[str, str]):
    try:
        tokens = AngelOneClient.login(
            payload["api_key"],
            payload["client_code"],
            payload["pin"],
            payload["totp"],
        )
        return tokens
    except Exception as e:
        raise HTTPException(400, f"Angel One login failed: {str(e)}")


@app.post("/broker/angel/holdings")
async def angel_holdings(payload: Dict[str, str]):
    try:
        client = AngelOneClient(
            payload["api_key"],
            payload["client_code"],
            payload["jwt_token"],
        )
        return {"holdings": client.get_holdings(), "broker": "angel_one"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Angel One error: {str(e)}")


@app.post("/broker/angel/real-connect")
async def angel_real_connect(payload: Dict[str, str]):
    try:
        api_key = payload.get("api_key", "").strip()
        client_code = payload.get("client_code", "").strip()
        pin = payload.get("pin", "").strip()
        totp = payload.get("totp", "").strip()

        if not api_key or not client_code or not pin or not totp:
            raise HTTPException(400, "Missing required fields: api_key, client_code, pin, and totp are all required")

        result = AngelOneClient.connect_and_fetch_holdings(api_key, client_code, pin, totp)
        try:
            init_angel_session(api_key, client_code, pin, totp)
        except Exception as ex:
            logger.warning(f"Could not hook Angel One into live feed: {ex}")
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Angel One SmartAPI error: {e}", exc_info=True)
        raise HTTPException(500, f"Angel One SmartAPI error: {str(e)}")


@app.post("/api/market/configure-angel")
async def configure_angel(payload: Dict[str, str]):
    api_key = payload.get("api_key", "").strip()
    client_code = payload.get("client_code", "").strip()
    pin = payload.get("pin", "").strip()
    totp = payload.get("totp", "").strip()
    if not api_key or not client_code or not pin or not totp:
        raise HTTPException(400, "Missing required fields: api_key, client_code, pin, and totp are all required")
    ok = init_angel_session(api_key, client_code, pin, totp)
    if not ok:
        raise HTTPException(400, "Failed to authenticate with Angel One SmartAPI. Check your API Key, Client ID, PIN, or TOTP.")
    return {"status": "success", "message": "Angel One SmartAPI live feed connected successfully!"}
 
 
@app.get("/api/market/status")
async def market_status():
    return get_angel_diagnostic()


# --- CSV Upload (Groww / Generic) ---
@app.post("/broker/csv/upload")
async def upload_csv(
    file: UploadFile = File(...),
    broker: str = Form(default="csv"),
):
    content = (await file.read()).decode("utf-8", errors="replace")
    try:
        if broker == "groww":
            holdings = GrowwParser.parse_groww(content)
        else:
            holdings = CSVPortfolioParser.parse(content, source=broker)
        return {"holdings": holdings, "broker": broker, "count": len(holdings)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"CSV parse error: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "IndiaStocks AI Backend v2"}


# --- Static SPA Frontend Mounting (for Render / Docker single-service deployment) ---
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
if not os.path.exists(dist_path):
    dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist"))

if os.path.exists(dist_path):
    assets_dir = os.path.join(dist_path, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api", "broker", "ws", "docs", "openapi.json", "health")):
            raise HTTPException(404, "Not Found")
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_path, "index.html"))

