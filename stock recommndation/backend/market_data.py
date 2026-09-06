"""
Market Data Service — Live tick data via yfinance streaming + NSE snapshot
"""
import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

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
    "POLYCAB.NS", "DIXON.NS", "APLAPOLLO.NS", "AAPL.NS", "CAMS.NS",
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

# Cache: symbol → {price, prev_close, ...}
_price_cache: Dict[str, Dict] = {}
_cache_ts: float = 0
_CACHE_TTL = 5  # seconds


def _fetch_ticks_sync(symbols: List[str]) -> List[Dict]:
    """Synchronously fetch latest prices via yfinance (thread pool)."""
    results = []
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if not t:
                    continue
                info = t.fast_info
                price = getattr(info, "last_price", None)
                prev_close = getattr(info, "previous_close", None)
                if price is None:
                    continue
                change = price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0
                volume = getattr(info, "three_month_average_volume", 0) or 0
                results.append({
                    "symbol": sym.replace(".NS", "").replace(".BO", ""),
                    "full_symbol": sym,
                    "price": round(price, 2),
                    "prev_close": round(prev_close or 0, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": int(volume),
                    "ts": int(__import__("time").time() * 1000),
                })
            except Exception:
                pass
    except Exception as e:
        logger.error(f"yfinance batch error: {e}")
    return results


def _fetch_historical_sync(symbol: str, period: str) -> List[Dict]:
    t = yf.Ticker(symbol)
    df = t.history(period=period)
    if df.empty:
        return []
    df = df.reset_index()
    return [
        {
            "date": str(row["Date"].date()),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]),
        }
        for _, row in df.iterrows()
    ]


def _fetch_info_sync(symbol: str) -> Dict:
    try:
        t = yf.Ticker(symbol)
        info = t.info
        return info
    except Exception:
        return {}


class MarketDataService:
    def __init__(self):
        self._loop = None

    async def _run_sync(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, fn, *args)

    async def get_live_ticks(self) -> List[Dict]:
        """Returns tick data for the watchlist."""
        global _price_cache, _cache_ts
        import time
        now = time.time()
        if now - _cache_ts < _CACHE_TTL and _price_cache:
            return list(_price_cache.values())
        ticks = await self._run_sync(_fetch_ticks_sync, WATCHLIST)
        _price_cache = {t["symbol"]: t for t in ticks}
        _cache_ts = now
        return ticks

    async def get_market_snapshot(self) -> Dict:
        # Indices
        indices = await self._run_sync(_fetch_ticks_sync, [
            "^NSEI", "^BSESN", "^NSEBANK",
        ])
        movers = await self._run_sync(_fetch_ticks_sync, WATCHLIST)
        return {
            "indices": indices,
            "movers": movers,
        }

    async def get_top_gainers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["change_pct"], reverse=True)[:10]

    async def get_top_losers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["change_pct"])[:10]

    async def get_volume_shakers(self) -> List[Dict]:
        data = await self._run_sync(_fetch_ticks_sync, NSE_LARGE_CAP[:20])
        return sorted(data, key=lambda x: x["volume"], reverse=True)[:10]

    async def get_historical(self, symbol: str, period: str = "1y") -> Dict:
        sym = symbol if "." in symbol else f"{symbol}.NS"
        hist = await self._run_sync(_fetch_historical_sync, sym, period)
        # Calculate CAGR
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
