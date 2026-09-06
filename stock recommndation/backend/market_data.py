"""
Market Data Service — Dual-Engine Live Tick Data
Primary: Official Angel One SmartAPI (100% Cloud Compatible, Zero IP Blocking)
Fallback / Default: Yahoo Finance (yfinance Parallel Batch Downloads)
"""
import asyncio
import logging
import os
import time
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

try:
    import pyotp
    from SmartApi import SmartConnect
    SMARTCONNECT_AVAILABLE = True
except ImportError:
    SMARTCONNECT_AVAILABLE = False

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=10)

# ─────────────────────────────────────────────────────────────────────────────
# NSE / BSE Universe — curated list of liquid Indian stocks + ETFs
# ─────────────────────────────────────────────────────────────────────────────
NSE_LARGE_CAP = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "WIPRO.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS",
    "MARUTI.NS", "BAJFINANCE.NS", "NESTLEIND.NS", "TITAN.NS", "HCLTECH.NS",
    "SUNPHARMA.NS", "ASIANPAINT.NS", "TATAMOTORS.NS", "ULTRACEMCO.NS",
    "ADANIENT.NS", "JSWSTEEL.NS", "COALINDIA.NS", "TECHM.NS", "TATASTEEL.NS",
    "M&M.NS", "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS", "EICHERMOT.NS",
    "BAJAJFINSV.NS", "HEROMOTOCO.NS", "BPCL.NS", "GRASIM.NS", "INDUSINDBK.NS",
]

NSE_MID_CAP = [
    "MUTHOOTFIN.NS", "PERSISTENT.NS", "LTIM.NS", "TATAELXSI.NS", "ANGELONE.NS",
    "POLYCAB.NS", "DIXON.NS", "APLAPOLLO.NS", "CAMS.NS",
    "IRCTC.NS", "HAL.NS", "BEL.NS", "BHEL.NS", "NATIONALUM.NS",
    "CROMPTON.NS", "PAGEIND.NS", "MPHASIS.NS", "COFORGE.NS", "ZOMATO.NS",
]

NSE_ETFS = [
    "NIFTYBEES.NS", "JUNIORBEES.NS", "BANKBEES.NS", "ITBEES.NS",
    "GOLDBEES.NS", "SETFNIF50.NS", "MOM100.NS", "ICICIB22.NS",
    "PSUBNKBEES.NS", "LIQUIDBEES.NS",
]

ALL_SYMBOLS = NSE_LARGE_CAP + NSE_MID_CAP + NSE_ETFS

WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "AXISBANK.NS", "WIPRO.NS", "ZOMATO.NS",
    "TATAMOTORS.NS", "BAJFINANCE.NS", "NIFTYBEES.NS", "BANKBEES.NS", "GOLDBEES.NS",
]

# Angel One SmartAPI Instrument Token Mapping
ANGEL_SYMBOL_MAP: Dict[str, Dict[str, str]] = {
    # Indices
    "^NSEI": {"exchange": "NSE", "symboltoken": "99926000", "tradingsymbol": "Nifty 50"},
    "^BSESN": {"exchange": "BSE", "symboltoken": "99919000", "tradingsymbol": "SENSEX"},
    "^NSEBANK": {"exchange": "NSE", "symboltoken": "99926009", "tradingsymbol": "Nifty Bank"},
    "NSEI": {"exchange": "NSE", "symboltoken": "99926000", "tradingsymbol": "Nifty 50"},
    "BSESN": {"exchange": "BSE", "symboltoken": "99919000", "tradingsymbol": "SENSEX"},
    "NSEBANK": {"exchange": "NSE", "symboltoken": "99926009", "tradingsymbol": "Nifty Bank"},

    # Watchlist & Top Equities
    "RELIANCE.NS": {"exchange": "NSE", "symboltoken": "2885", "tradingsymbol": "RELIANCE-EQ"},
    "TCS.NS": {"exchange": "NSE", "symboltoken": "11536", "tradingsymbol": "TCS-EQ"},
    "HDFCBANK.NS": {"exchange": "NSE", "symboltoken": "1333", "tradingsymbol": "HDFCBANK-EQ"},
    "INFY.NS": {"exchange": "NSE", "symboltoken": "1594", "tradingsymbol": "INFY-EQ"},
    "ICICIBANK.NS": {"exchange": "NSE", "symboltoken": "4963", "tradingsymbol": "ICICIBANK-EQ"},
    "SBIN.NS": {"exchange": "NSE", "symboltoken": "3045", "tradingsymbol": "SBIN-EQ"},
    "BHARTIARTL.NS": {"exchange": "NSE", "symboltoken": "10604", "tradingsymbol": "BHARTIARTL-EQ"},
    "KOTAKBANK.NS": {"exchange": "NSE", "symboltoken": "1922", "tradingsymbol": "KOTAKBANK-EQ"},
    "LT.NS": {"exchange": "NSE", "symboltoken": "11483", "tradingsymbol": "LT-EQ"},
    "AXISBANK.NS": {"exchange": "NSE", "symboltoken": "5900", "tradingsymbol": "AXISBANK-EQ"},
    "WIPRO.NS": {"exchange": "NSE", "symboltoken": "3787", "tradingsymbol": "WIPRO-EQ"},
    "TATAMOTORS.NS": {"exchange": "NSE", "symboltoken": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "BAJFINANCE.NS": {"exchange": "NSE", "symboltoken": "317", "tradingsymbol": "BAJFINANCE-EQ"},
    "ZOMATO.NS": {"exchange": "NSE", "symboltoken": "5097", "tradingsymbol": "ZOMATO-EQ"},
    "MARUTI.NS": {"exchange": "NSE", "symboltoken": "10999", "tradingsymbol": "MARUTI-EQ"},
    "SUNPHARMA.NS": {"exchange": "NSE", "symboltoken": "3351", "tradingsymbol": "SUNPHARMA-EQ"},
    "TITAN.NS": {"exchange": "NSE", "symboltoken": "3506", "tradingsymbol": "TITAN-EQ"},
    "HCLTECH.NS": {"exchange": "NSE", "symboltoken": "7229", "tradingsymbol": "HCLTECH-EQ"},
    "ASIANPAINT.NS": {"exchange": "NSE", "symboltoken": "236", "tradingsymbol": "ASIANPAINT-EQ"},
    "NIFTYBEES.NS": {"exchange": "NSE", "symboltoken": "10599", "tradingsymbol": "NIFTYBEES-EQ"},
    "BANKBEES.NS": {"exchange": "NSE", "symboltoken": "10594", "tradingsymbol": "BANKBEES-EQ"},
    "GOLDBEES.NS": {"exchange": "NSE", "symboltoken": "10596", "tradingsymbol": "GOLDBEES-EQ"},
}

# Real Price Cache: symbol → {price, prev_close, ...}
_price_cache: Dict[str, Dict] = {}
_cache_ts: float = 0
_CACHE_TTL = 8  # Cache TTL for smooth live feeds

# Global Angel One SmartConnect Session
_angel_smart_api: Optional[Any] = None
_angel_last_session_time: float = 0
_angel_creds: Dict[str, str] = {}


def init_angel_session(api_key: str, client_code: str, pin: str, totp_or_secret: str) -> bool:
    """Initialize or update authenticated Angel One SmartAPI session."""
    global _angel_smart_api, _angel_last_session_time, _angel_creds
    if not SMARTCONNECT_AVAILABLE:
        logger.warning("smartapi-python library not available")
        return False
    try:
        raw_totp = str(totp_or_secret or "").strip().replace(" ", "")
        totp_code = raw_totp if (raw_totp.isdigit() and len(raw_totp) == 6) else pyotp.TOTP(raw_totp.upper()).now()
        api = SmartConnect(api_key=api_key.strip())
        session = api.generateSession(client_code.strip(), pin.strip(), str(totp_code))
        if session and session.get("status") is not False:
            _angel_smart_api = api
            _angel_last_session_time = time.time()
            _angel_creds = {
                "api_key": api_key, "client_code": client_code,
                "pin": pin, "totp_or_secret": totp_or_secret,
            }
            logger.info("Angel One SmartAPI Live Feed session connected successfully!")
            return True
        else:
            msg = session.get("message") if isinstance(session, dict) else "Unknown"
            logger.warning(f"Angel One session failed: {msg}")
            return False
    except Exception as e:
        logger.warning(f"Angel One session initialization error: {e}")
        return False


def _check_auto_env_angel():
    """Auto-connect Angel One if environment variables are set."""
    global _angel_smart_api, _angel_last_session_time
    if _angel_smart_api and (time.time() - _angel_last_session_time < 3600):
        return
    api_key = os.getenv("ANGEL_API_KEY")
    client_code = os.getenv("ANGEL_CLIENT_CODE")
    pin = os.getenv("ANGEL_PIN")
    totp = os.getenv("ANGEL_TOTP_KEY") or os.getenv("ANGEL_TOTP")
    if api_key and client_code and pin and totp:
        init_angel_session(api_key, client_code, pin, totp)


def _fetch_angel_ticks_sync(symbols: List[str]) -> List[Dict]:
    """Fetch live quotes directly from Angel One SmartAPI."""
    global _angel_smart_api
    _check_auto_env_angel()
    if not _angel_smart_api:
        return []

    results = []
    now_ts = int(time.time() * 1000)

    try:
        for sym in symbols:
            token_info = ANGEL_SYMBOL_MAP.get(sym) or ANGEL_SYMBOL_MAP.get(f"{sym}.NS")
            if not token_info:
                continue
            try:
                resp = _angel_smart_api.ltpData(
                    token_info["exchange"],
                    token_info["tradingsymbol"],
                    token_info["symboltoken"]
                )
                if resp and isinstance(resp, dict) and resp.get("status") is not False and "data" in resp:
                    data = resp["data"]
                    price = round(float(data.get("ltp", 0)), 2)
                    prev_close = round(float(data.get("close", price) or price), 2)
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                    clean_sym = sym.replace("^", "").replace(".NS", "").replace(".BO", "")
                    results.append({
                        "symbol": clean_sym,
                        "full_symbol": sym,
                        "price": price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "volume": 0,
                        "ts": now_ts,
                        "source": "AngelOne SmartAPI",
                    })
            except Exception as e:
                logger.debug(f"Angel LTP error for {sym}: {e}")
                continue
    except Exception as e:
        logger.warning(f"Angel One batch fetch error: {e}")

    return results


def _download_yahoo_ticks_sync(symbols: List[str]) -> List[Dict]:
    """Fetch live quotes via Yahoo Finance (yfinance parallel batch download)."""
    if not symbols:
        return []

    results = []
    try:
        df = yf.download(symbols, period="5d", progress=False)
        if df is None or df.empty:
            return []

        now_ts = int(time.time() * 1000)

        for sym in symbols:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    if "Close" not in df or sym not in df["Close"]:
                        continue
                    c_series = df["Close"][sym].dropna()
                    v_series = df["Volume"][sym].dropna() if "Volume" in df and sym in df["Volume"] else None
                else:
                    c_series = df["Close"].dropna()
                    v_series = df["Volume"].dropna() if "Volume" in df else None

                if c_series.empty:
                    continue

                price = round(float(c_series.iloc[-1]), 2)
                prev_close = round(float(c_series.iloc[-2]), 2) if len(c_series) >= 2 else price
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                volume = int(v_series.iloc[-1]) if v_series is not None and not v_series.empty else 0
                clean_sym = sym.replace("^", "").replace(".NS", "").replace(".BO", "")

                results.append({
                    "symbol": clean_sym,
                    "full_symbol": sym,
                    "price": price,
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": volume,
                    "ts": now_ts,
                    "source": "Yahoo Finance",
                })
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Yahoo Finance batch download error: {e}")

    return results


def _fetch_ticks_combined_sync(symbols: List[str]) -> List[Dict]:
    """
    Combined real live market fetcher:
    1. Queries Angel One SmartAPI first if connected.
    2. Fills remaining or fallback symbols using Yahoo Finance.
    Both providers are strictly live exchange data.
    """
    results_map: Dict[str, Dict] = {}

    # 1. Try Angel One SmartAPI
    try:
        angel_ticks = _fetch_angel_ticks_sync(symbols)
        for t in angel_ticks:
            results_map[t["full_symbol"]] = t
    except Exception as e:
        logger.debug(f"Angel One fetch skipped: {e}")

    # 2. Check which symbols still need data
    missing_symbols = [s for s in symbols if s not in results_map]

    # 3. Fetch missing symbols via Yahoo Finance
    if missing_symbols:
        try:
            yahoo_ticks = _download_yahoo_ticks_sync(missing_symbols)
            for t in yahoo_ticks:
                results_map[t["full_symbol"]] = t
        except Exception as e:
            logger.debug(f"Yahoo Finance fallback skipped: {e}")

    return list(results_map.values())


def _fetch_historical_sync(symbol: str, period: str) -> List[Dict]:
    """Fetch 100% REAL historical candle data directly from Yahoo Finance."""
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period)
        if df is not None and not df.empty:
            df = df.reset_index()
            return [
                {
                    "date": str(row["Date"].date()) if hasattr(row["Date"], "date") else str(row["Date"])[:10],
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
                for _, row in df.iterrows()
            ]
    except Exception as e:
        logger.error(f"Historical fetch error for {symbol}: {e}")
    return []


def _fetch_info_sync(symbol: str) -> Dict:
    """Fetch real fundamental profile from exchange."""
    try:
        t = yf.Ticker(symbol)
        return t.info or {}
    except Exception as e:
        logger.error(f"Real info fetch error for {symbol}: {e}")
        return {}


class MarketDataService:
    def __init__(self):
        self._loop = None

    async def _run_sync(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, fn, *args)

    async def get_live_ticks(self) -> List[Dict]:
        """Returns 100% REAL LIVE tick data (Angel One + Yahoo Finance fallback)."""
        global _price_cache, _cache_ts
        now = time.time()
        if now - _cache_ts < _CACHE_TTL and _price_cache:
            return list(_price_cache.values())

        ticks = await self._run_sync(_fetch_ticks_combined_sync, WATCHLIST)
        if ticks:
            for t in ticks:
                _price_cache[t["symbol"]] = t
            _cache_ts = now
            return ticks
        return list(_price_cache.values())

    async def get_market_snapshot(self) -> Dict:
        """Returns 100% REAL LIVE indices (NIFTY 50, SENSEX, BANK NIFTY) and market movers."""
        indices = await self._run_sync(_fetch_ticks_combined_sync, [
            "^NSEI", "^BSESN", "^NSEBANK",
        ])
        movers = await self.get_live_ticks()
        return {
            "indices": indices,
            "movers": movers,
        }

    async def get_top_gainers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["change_pct"], reverse=True)[:10]

    async def get_top_losers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["change_pct"])[:10]

    async def get_volume_shakers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["volume"], reverse=True)[:10]

    async def get_historical(self, symbol: str, period: str = "1y") -> Dict:
        sym = symbol if ("." in symbol or "^" in symbol) else f"{symbol}.NS"
        hist = await self._run_sync(_fetch_historical_sync, sym, period)
        if len(hist) >= 2:
            start_p = hist[0]["close"]
            end_p = hist[-1]["close"]
            years = len(hist) / 252
            cagr = ((end_p / start_p) ** (1 / max(years, 0.01)) - 1) * 100 if start_p > 0 else 0
        else:
            cagr = 0
        return {"symbol": symbol, "history": hist, "cagr_pct": round(cagr, 2)}

    async def search_stocks(self, query: str) -> List[Dict]:
        query_up = query.upper()
        results = []
        for sym in ALL_SYMBOLS:
            name = sym.replace(".NS", "").replace(".BO", "")
            if query_up in name:
                results.append({"symbol": name, "full_symbol": sym})
        return results[:10]
