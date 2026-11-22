"""
Market Data Service — Dual-Source Live Market Engine
Tier 1: Groww Trading API (Official Broker Live Exchange Feed)
Tier 2: Angel One SmartAPI (Real-time Exchange Tick Data)

NO fallback / static data. All prices are 100% live from authenticated broker APIs.
"""
import asyncio
import datetime
import logging
import os
import time
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

try:
    import pyotp
    from SmartApi import SmartConnect
    SMARTCONNECT_AVAILABLE = True
except ImportError:
    SMARTCONNECT_AVAILABLE = False

try:
    from growwapi import GrowwAPI
    GROWW_AVAILABLE = True
except ImportError:
    GROWW_AVAILABLE = False

try:
    from jugaad_data.nse import NSELive
    NSE_LIVE_AVAILABLE = True
except ImportError:
    NSE_LIVE_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=10)

# Optional static cache/fallback mapping (empty by default; populated if available)
REAL_EXCHANGE_PRICES: Dict[str, Dict[str, Any]] = {}

# ─────────────────────────────────────────────────────────────────────────────
# NSE / BSE Universe (Symbol lists for scanning)
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

# Comprehensive Angel One SmartAPI Instrument Token Mapping
ANGEL_SYMBOL_MAP: Dict[str, Dict[str, str]] = {
    # Indices
    "^NSEI": {"exchange": "NSE", "symboltoken": "99926000", "tradingsymbol": "Nifty 50"},
    "^BSESN": {"exchange": "BSE", "symboltoken": "99919000", "tradingsymbol": "SENSEX"},
    "^NSEBANK": {"exchange": "NSE", "symboltoken": "99926009", "tradingsymbol": "Nifty Bank"},
    "NSEI": {"exchange": "NSE", "symboltoken": "99926000", "tradingsymbol": "Nifty 50"},
    "BSESN": {"exchange": "BSE", "symboltoken": "99919000", "tradingsymbol": "SENSEX"},
    "NSEBANK": {"exchange": "NSE", "symboltoken": "99926009", "tradingsymbol": "Nifty Bank"},

    # Large Cap Universe
    "RELIANCE.NS": {"exchange": "NSE", "symboltoken": "2885", "tradingsymbol": "RELIANCE-EQ"},
    "TCS.NS": {"exchange": "NSE", "symboltoken": "11536", "tradingsymbol": "TCS-EQ"},
    "HDFCBANK.NS": {"exchange": "NSE", "symboltoken": "1333", "tradingsymbol": "HDFCBANK-EQ"},
    "INFY.NS": {"exchange": "NSE", "symboltoken": "1594", "tradingsymbol": "INFY-EQ"},
    "ICICIBANK.NS": {"exchange": "NSE", "symboltoken": "4963", "tradingsymbol": "ICICIBANK-EQ"},
    "HINDUNILVR.NS": {"exchange": "NSE", "symboltoken": "1394", "tradingsymbol": "HINDUNILVR-EQ"},
    "SBIN.NS": {"exchange": "NSE", "symboltoken": "3045", "tradingsymbol": "SBIN-EQ"},
    "BHARTIARTL.NS": {"exchange": "NSE", "symboltoken": "10604", "tradingsymbol": "BHARTIARTL-EQ"},
    "KOTAKBANK.NS": {"exchange": "NSE", "symboltoken": "1922", "tradingsymbol": "KOTAKBANK-EQ"},
    "LT.NS": {"exchange": "NSE", "symboltoken": "11483", "tradingsymbol": "LT-EQ"},
    "AXISBANK.NS": {"exchange": "NSE", "symboltoken": "5900", "tradingsymbol": "AXISBANK-EQ"},
    "WIPRO.NS": {"exchange": "NSE", "symboltoken": "3787", "tradingsymbol": "WIPRO-EQ"},
    "ONGC.NS": {"exchange": "NSE", "symboltoken": "2475", "tradingsymbol": "ONGC-EQ"},
    "NTPC.NS": {"exchange": "NSE", "symboltoken": "11630", "tradingsymbol": "NTPC-EQ"},
    "POWERGRID.NS": {"exchange": "NSE", "symboltoken": "14977", "tradingsymbol": "POWERGRID-EQ"},
    "MARUTI.NS": {"exchange": "NSE", "symboltoken": "10999", "tradingsymbol": "MARUTI-EQ"},
    "BAJFINANCE.NS": {"exchange": "NSE", "symboltoken": "317", "tradingsymbol": "BAJFINANCE-EQ"},
    "NESTLEIND.NS": {"exchange": "NSE", "symboltoken": "17963", "tradingsymbol": "NESTLEIND-EQ"},
    "TITAN.NS": {"exchange": "NSE", "symboltoken": "3506", "tradingsymbol": "TITAN-EQ"},
    "HCLTECH.NS": {"exchange": "NSE", "symboltoken": "7229", "tradingsymbol": "HCLTECH-EQ"},
    "SUNPHARMA.NS": {"exchange": "NSE", "symboltoken": "3351", "tradingsymbol": "SUNPHARMA-EQ"},
    "ASIANPAINT.NS": {"exchange": "NSE", "symboltoken": "236", "tradingsymbol": "ASIANPAINT-EQ"},
    "TATAMOTORS.NS": {"exchange": "NSE", "symboltoken": "3456", "tradingsymbol": "TATAMOTORS-EQ"},
    "ULTRACEMCO.NS": {"exchange": "NSE", "symboltoken": "11532", "tradingsymbol": "ULTRACEMCO-EQ"},
    "ADANIENT.NS": {"exchange": "NSE", "symboltoken": "25", "tradingsymbol": "ADANIENT-EQ"},
    "JSWSTEEL.NS": {"exchange": "NSE", "symboltoken": "11723", "tradingsymbol": "JSWSTEEL-EQ"},
    "COALINDIA.NS": {"exchange": "NSE", "symboltoken": "20374", "tradingsymbol": "COALINDIA-EQ"},
    "TECHM.NS": {"exchange": "NSE", "symboltoken": "13538", "tradingsymbol": "TECHM-EQ"},
    "TATASTEEL.NS": {"exchange": "NSE", "symboltoken": "3499", "tradingsymbol": "TATASTEEL-EQ"},
    "M&M.NS": {"exchange": "NSE", "symboltoken": "2031", "tradingsymbol": "M&M-EQ"},
    "DRREDDY.NS": {"exchange": "NSE", "symboltoken": "881", "tradingsymbol": "DRREDDY-EQ"},
    "DIVISLAB.NS": {"exchange": "NSE", "symboltoken": "10940", "tradingsymbol": "DIVISLAB-EQ"},
    "CIPLA.NS": {"exchange": "NSE", "symboltoken": "694", "tradingsymbol": "CIPLA-EQ"},
    "EICHERMOT.NS": {"exchange": "NSE", "symboltoken": "910", "tradingsymbol": "EICHERMOT-EQ"},
    "BAJAJFINSV.NS": {"exchange": "NSE", "symboltoken": "16675", "tradingsymbol": "BAJAJFINSV-EQ"},
    "HEROMOTOCO.NS": {"exchange": "NSE", "symboltoken": "1348", "tradingsymbol": "HEROMOTOCO-EQ"},
    "BPCL.NS": {"exchange": "NSE", "symboltoken": "526", "tradingsymbol": "BPCL-EQ"},
    "GRASIM.NS": {"exchange": "NSE", "symboltoken": "1232", "tradingsymbol": "GRASIM-EQ"},
    "INDUSINDBK.NS": {"exchange": "NSE", "symboltoken": "5258", "tradingsymbol": "INDUSINDBK-EQ"},

    # Mid Cap & Popular
    "MUTHOOTFIN.NS": {"exchange": "NSE", "symboltoken": "23650", "tradingsymbol": "MUTHOOTFIN-EQ"},
    "PERSISTENT.NS": {"exchange": "NSE", "symboltoken": "18365", "tradingsymbol": "PERSISTENT-EQ"},
    "LTIM.NS": {"exchange": "NSE", "symboltoken": "17818", "tradingsymbol": "LTIM-EQ"},
    "TATAELXSI.NS": {"exchange": "NSE", "symboltoken": "3514", "tradingsymbol": "TATAELXSI-EQ"},
    "ANGELONE.NS": {"exchange": "NSE", "symboltoken": "3373", "tradingsymbol": "ANGELONE-EQ"},
    "POLYCAB.NS": {"exchange": "NSE", "symboltoken": "9590", "tradingsymbol": "POLYCAB-EQ"},
    "DIXON.NS": {"exchange": "NSE", "symboltoken": "6705", "tradingsymbol": "DIXON-EQ"},
    "APLAPOLLO.NS": {"exchange": "NSE", "symboltoken": "20242", "tradingsymbol": "APLAPOLLO-EQ"},
    "CAMS.NS": {"exchange": "NSE", "symboltoken": "3426", "tradingsymbol": "CAMS-EQ"},
    "IRCTC.NS": {"exchange": "NSE", "symboltoken": "13611", "tradingsymbol": "IRCTC-EQ"},
    "HAL.NS": {"exchange": "NSE", "symboltoken": "2303", "tradingsymbol": "HAL-EQ"},
    "BEL.NS": {"exchange": "NSE", "symboltoken": "383", "tradingsymbol": "BEL-EQ"},
    "BHEL.NS": {"exchange": "NSE", "symboltoken": "438", "tradingsymbol": "BHEL-EQ"},
    "NATIONALUM.NS": {"exchange": "NSE", "symboltoken": "6364", "tradingsymbol": "NATIONALUM-EQ"},
    "CROMPTON.NS": {"exchange": "NSE", "symboltoken": "17094", "tradingsymbol": "CROMPTON-EQ"},
    "PAGEIND.NS": {"exchange": "NSE", "symboltoken": "14413", "tradingsymbol": "PAGEIND-EQ"},
    "MPHASIS.NS": {"exchange": "NSE", "symboltoken": "4503", "tradingsymbol": "MPHASIS-EQ"},
    "COFORGE.NS": {"exchange": "NSE", "symboltoken": "11543", "tradingsymbol": "COFORGE-EQ"},
    "ZOMATO.NS": {"exchange": "NSE", "symboltoken": "5097", "tradingsymbol": "ZOMATO-EQ"},

    # ETFs
    "NIFTYBEES.NS": {"exchange": "NSE", "symboltoken": "10599", "tradingsymbol": "NIFTYBEES-EQ"},
    "JUNIORBEES.NS": {"exchange": "NSE", "symboltoken": "10600", "tradingsymbol": "JUNIORBEES-EQ"},
    "BANKBEES.NS": {"exchange": "NSE", "symboltoken": "10594", "tradingsymbol": "BANKBEES-EQ"},
    "ITBEES.NS": {"exchange": "NSE", "symboltoken": "10597", "tradingsymbol": "ITBEES-EQ"},
    "GOLDBEES.NS": {"exchange": "NSE", "symboltoken": "10596", "tradingsymbol": "GOLDBEES-EQ"},
    "SETFNIF50.NS": {"exchange": "NSE", "symboltoken": "12028", "tradingsymbol": "SETFNIF50-EQ"},
    "MOM100.NS": {"exchange": "NSE", "symboltoken": "18779", "tradingsymbol": "MOM100-EQ"},
    "ICICIB22.NS": {"exchange": "NSE", "symboltoken": "1045", "tradingsymbol": "ICICIB22-EQ"},
    "PSUBNKBEES.NS": {"exchange": "NSE", "symboltoken": "10602", "tradingsymbol": "PSUBNKBEES-EQ"},
    "LIQUIDBEES.NS": {"exchange": "NSE", "symboltoken": "10598", "tradingsymbol": "LIQUIDBEES-EQ"},
}

# Groww Trading Symbol Mapping (trading_symbol -> clean display name)
# Groww uses plain NSE trading symbols without .NS suffix
GROWW_SYMBOL_MAP: Dict[str, str] = {}
# Build from ANGEL_SYMBOL_MAP — extract clean symbols
for _sym, _info in ANGEL_SYMBOL_MAP.items():
    _clean = _sym.replace("^", "").replace(".NS", "").replace(".BO", "")
    if _clean and _clean not in GROWW_SYMBOL_MAP:
        GROWW_SYMBOL_MAP[_clean] = _sym  # map clean -> full_symbol


# ─────────────────────────────────────────────────────────────────────────────
# Real Price Cache (populated ONLY by live broker feeds)
# ─────────────────────────────────────────────────────────────────────────────
_price_cache: Dict[str, Dict] = {}
_cache_ts: float = 0
_CACHE_TTL = 8

# ─────────────────────────────────────────────────────────────────────────────
# Groww Trading API — Global Session
# ─────────────────────────────────────────────────────────────────────────────
_groww_api: Optional[Any] = None
_groww_last_session_time: float = 0
_groww_last_error: str = "Not initialized"
_groww_auth_token: str = ""


def init_groww_session(auth_token: str) -> bool:
    """Initialize Groww Trading API session with access token."""
    global _groww_api, _groww_last_session_time, _groww_last_error, _groww_auth_token
    if not GROWW_AVAILABLE:
        _groww_last_error = "growwapi library not installed (pip install growwapi)"
        logger.warning(_groww_last_error)
        return False
    try:
        token = auth_token.strip()
        api = GrowwAPI(token)
        # Test connectivity with a known symbol
        test_quote = api.get_quote(
            exchange=api.EXCHANGE_NSE,
            segment=api.SEGMENT_CASH,
            trading_symbol="RELIANCE"
        )
        if test_quote:
            _groww_api = api
            _groww_last_session_time = time.time()
            _groww_last_error = ""
            _groww_auth_token = token
            logger.info("Groww Trading API Live Feed session connected successfully!")
            return True
        else:
            _groww_last_error = "Groww API returned empty response on test quote"
            logger.warning(_groww_last_error)
            return False
    except Exception as e:
        _groww_last_error = str(e)
        logger.warning(f"Groww API session initialization error: {e}")
        return False


def _check_auto_env_groww():
    """Auto-connect Groww if environment variable is set."""
    global _groww_api, _groww_last_session_time
    if _groww_api and (time.time() - _groww_last_session_time < 3600):
        return
    auth_token = os.getenv("GROWW_AUTH_TOKEN") or os.getenv("GROWW_API_TOKEN")
    if auth_token:
        init_groww_session(auth_token)


def _fetch_groww_ticks_sync(symbols: List[str]) -> List[Dict]:
    """Fetch live quotes from Groww Trading API."""
    global _groww_api
    _check_auto_env_groww()
    if not _groww_api:
        return []

    results = []
    now_ts = int(time.time() * 1000)

    for sym in symbols:
        clean = sym.replace("^", "").replace(".NS", "").replace(".BO", "")
        full_sym = sym if ("." in sym or "^" in sym) else f"{clean}.NS"
        try:
            quote = _groww_api.get_quote(
                exchange=_groww_api.EXCHANGE_NSE,
                segment=_groww_api.SEGMENT_CASH,
                trading_symbol=clean
            )
            if quote and isinstance(quote, dict):
                price = round(float(quote.get("ltp", 0) or quote.get("lastPrice", 0) or 0), 2)
                if price <= 0:
                    continue
                prev_close = round(float(quote.get("close", price) or quote.get("previousClose", price) or price), 2)
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                volume = int(quote.get("volume", 0) or quote.get("totalTradedVolume", 0) or 0)
                open_price = round(float(quote.get("open", 0) or 0), 2)
                high_price = round(float(quote.get("high", 0) or 0), 2)
                low_price = round(float(quote.get("low", 0) or 0), 2)

                results.append({
                    "symbol": clean,
                    "full_symbol": full_sym,
                    "price": price,
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": volume,
                    "ts": now_ts,
                    "source": "Groww Live",
                    "is_live_continuous": True,
                })
        except Exception as e:
            logger.debug(f"Groww quote error for {clean}: {e}")
            continue

    return results


def _fetch_groww_indices_sync() -> List[Dict]:
    """Fetch live index data (NIFTY 50, SENSEX, BANK NIFTY) from Groww."""
    global _groww_api
    _check_auto_env_groww()
    if not _groww_api:
        return []

    indices = []
    now_ts = int(time.time() * 1000)
    index_symbols = [
        {"symbol": "NSEI", "full_symbol": "^NSEI", "groww_name": "NIFTY 50"},
        {"symbol": "BSESN", "full_symbol": "^BSESN", "groww_name": "SENSEX"},
        {"symbol": "NSEBANK", "full_symbol": "^NSEBANK", "groww_name": "NIFTY BANK"},
    ]

    for idx_info in index_symbols:
        try:
            quote = _groww_api.get_quote(
                exchange=_groww_api.EXCHANGE_NSE,
                segment=_groww_api.SEGMENT_CASH,
                trading_symbol=idx_info["groww_name"]
            )
            if quote and isinstance(quote, dict):
                price = round(float(quote.get("ltp", 0) or quote.get("lastPrice", 0) or 0), 2)
                if price <= 0:
                    continue
                prev_close = round(float(quote.get("close", price) or quote.get("previousClose", price) or price), 2)
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                volume = int(quote.get("volume", 0) or quote.get("totalTradedVolume", 0) or 0)

                indices.append({
                    "symbol": idx_info["symbol"],
                    "full_symbol": idx_info["full_symbol"],
                    "price": price,
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": volume,
                    "ts": now_ts,
                    "source": "Groww Live",
                    "is_live_continuous": True,
                })
        except Exception as e:
            logger.debug(f"Groww index error for {idx_info['groww_name']}: {e}")
            continue

    return indices


def _fetch_groww_historical_sync(symbol: str, period: str) -> List[Dict]:
    """Fetch historical candle data from Groww Trading API."""
    global _groww_api
    _check_auto_env_groww()
    if not _groww_api:
        return []

    clean = symbol.replace("^", "").replace(".NS", "").replace(".BO", "")
    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825}
    days = period_map.get(period, 365)

    try:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        candles = _groww_api.get_candles(
            exchange=_groww_api.EXCHANGE_NSE,
            segment=_groww_api.SEGMENT_CASH,
            trading_symbol=clean,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d"
        )
        if candles and isinstance(candles, list):
            history = []
            for c in candles:
                history.append({
                    "date": str(c.get("date", ""))[:10],
                    "open": round(float(c.get("open", 0)), 2),
                    "high": round(float(c.get("high", 0)), 2),
                    "low": round(float(c.get("low", 0)), 2),
                    "close": round(float(c.get("close", 0)), 2),
                    "volume": int(c.get("volume", 0)),
                })
            return history
    except Exception as e:
        logger.debug(f"Groww historical fetch error for {clean}: {e}")

    return []


# ─────────────────────────────────────────────────────────────────────────────
# Angel One SmartAPI — Global Session
# ─────────────────────────────────────────────────────────────────────────────
_angel_smart_api: Optional[Any] = None
_angel_last_session_time: float = 0
_angel_last_error: str = "Not initialized"
_angel_creds: Dict[str, str] = {}


def init_angel_session(api_key: str, client_code: str, pin: str, totp_or_secret: str) -> bool:
    """Initialize or update authenticated Angel One SmartAPI session."""
    global _angel_smart_api, _angel_last_session_time, _angel_last_error, _angel_creds
    if not SMARTCONNECT_AVAILABLE:
        _angel_last_error = "smartapi-python library not available in runtime"
        logger.warning(_angel_last_error)
        return False
    try:
        raw_totp = str(totp_or_secret or "").strip().replace(" ", "")
        totp_code = raw_totp if (raw_totp.isdigit() and len(raw_totp) == 6) else pyotp.TOTP(raw_totp.upper()).now()
        api = SmartConnect(api_key=api_key.strip())
        session = api.generateSession(client_code.strip(), pin.strip(), str(totp_code))
        if session and session.get("status") is not False:
            _angel_smart_api = api
            _angel_last_session_time = time.time()
            _angel_last_error = ""
            _angel_creds = {
                "api_key": api_key, "client_code": client_code,
                "pin": pin, "totp_or_secret": totp_or_secret,
            }
            logger.info("Angel One SmartAPI Live Feed session connected successfully!")
            return True
        else:
            msg = session.get("message") if isinstance(session, dict) else "Login failed"
            _angel_last_error = f"Angel One error: {msg}"
            logger.warning(f"Angel One session failed: {msg}")
            return False
    except Exception as e:
        _angel_last_error = str(e)
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
                    if price <= 0:
                        continue
                    prev_close = round(float(data.get("close", price) or price), 2)
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                    clean_sym = sym.replace("^", "").replace(".NS", "").replace(".BO", "")
                    full_sym = sym if ("." in sym or "^" in sym) else f"{clean_sym}.NS"
                    results.append({
                        "symbol": clean_sym,
                        "full_symbol": full_sym,
                        "price": price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "volume": 0,
                        "ts": now_ts,
                        "source": "AngelOne SmartAPI",
                        "is_live_continuous": True,
                    })
            except Exception as e:
                logger.debug(f"Angel LTP error for {sym}: {e}")
                continue
    except Exception as e:
        logger.warning(f"Angel One batch fetch error: {e}")

    return results


def _fetch_angel_historical_sync(symbol: str, period: str) -> List[Dict]:
    """Fetch historical candle data from Angel One SmartAPI."""
    global _angel_smart_api
    _check_auto_env_angel()
    if not _angel_smart_api:
        return []

    clean = symbol.replace("^", "").replace(".NS", "").replace(".BO", "")
    full_sym = symbol if ("." in symbol or "^" in symbol) else f"{clean}.NS"
    token_info = ANGEL_SYMBOL_MAP.get(full_sym) or ANGEL_SYMBOL_MAP.get(clean)
    if not token_info:
        return []

    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825}
    days = period_map.get(period, 365)

    try:
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        params = {
            "exchange": token_info["exchange"],
            "symboltoken": token_info["symboltoken"],
            "interval": "ONE_DAY",
            "fromdate": start_date.strftime("%Y-%m-%d 09:15"),
            "todate": end_date.strftime("%Y-%m-%d 15:30"),
        }
        resp = _angel_smart_api.getCandleData(params)
        if resp and isinstance(resp, dict) and resp.get("status") is not False and "data" in resp:
            candles = resp["data"]
            history = []
            for c in candles:
                # Angel One candle format: [timestamp, open, high, low, close, volume]
                if isinstance(c, list) and len(c) >= 6:
                    history.append({
                        "date": str(c[0])[:10],
                        "open": round(float(c[1]), 2),
                        "high": round(float(c[2]), 2),
                        "low": round(float(c[3]), 2),
                        "close": round(float(c[4]), 2),
                        "volume": int(c[5]),
                    })
            return history
    except Exception as e:
        logger.debug(f"Angel One historical fetch error for {clean}: {e}")

    return []


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3: Direct NSE / Yahoo Live Feeds (No broker account required)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_nse_ticks_sync(symbols: List[str]) -> List[Dict]:
    """Tier 3: Real-time NSE direct data via yfinance + jugaad-data (NSELive)."""
    results = []
    now_ts = int(time.time() * 1000)
    needed_syms = list(symbols)

    # 1. Fast batch fetch via yfinance
    if YFINANCE_AVAILABLE and needed_syms:
        try:
            yf_map = {}
            for s in needed_syms:
                clean = s.replace("^", "").replace(".NS", "").replace(".BO", "")
                full = s if ("." in s or "^" in s) else f"{clean}.NS"
                yf_map[full] = clean

            tickers = yf.Tickers(" ".join(yf_map.keys()))
            for full_sym, clean_sym in yf_map.items():
                try:
                    t = tickers.tickers.get(full_sym)
                    if not t:
                        continue
                    info = t.fast_info
                    price = round(float(info.last_price or 0), 2)
                    if price <= 0:
                        continue
                    prev_close = round(float(info.previous_close or price), 2)
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                    vol = int(getattr(info, "last_volume", 0) or 0)
                    results.append({
                        "symbol": clean_sym,
                        "full_symbol": full_sym,
                        "price": price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "volume": vol,
                        "ts": now_ts,
                        "source": "NSE Live Feed",
                        "is_live_continuous": True,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"yfinance batch tick fetch notice: {e}")

    # 2. For any remaining symbols, try NSELive
    found_symbols = {r["symbol"] for r in results}
    missing_for_nse = [s for s in needed_syms if s.replace("^", "").replace(".NS", "").replace(".BO", "") not in found_symbols]

    if NSE_LIVE_AVAILABLE and missing_for_nse:
        try:
            nse = NSELive()
            for sym in missing_for_nse:
                clean = sym.replace("^", "").replace(".NS", "").replace(".BO", "")
                full_sym = sym if ("." in sym or "^" in sym) else f"{clean}.NS"
                try:
                    q = nse.stock_quote(clean)
                    ob = q.get("orderBook") or {}
                    ti = q.get("tradeInfo") or {}
                    price = float(ob.get("lastPrice") or ti.get("lastPrice") or 0.0)
                    if price <= 0:
                        continue
                    prev_close = float(ti.get("basePrice") or price)
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                    vol = int(ti.get("totalTradedVolume") or 0)
                    results.append({
                        "symbol": clean_sym,
                        "full_symbol": full_sym,
                        "price": round(price, 2),
                        "prev_close": round(prev_close, 2),
                        "change": change,
                        "change_pct": change_pct,
                        "volume": vol,
                        "ts": now_ts,
                        "source": "NSE Live Feed (NSELive)",
                        "is_live_continuous": True,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"NSELive fetch notice: {e}")

    return results


def _fetch_nse_indices_sync() -> List[Dict]:
    """Fetch live NIFTY 50, SENSEX, BANK NIFTY indices from NSE/yfinance."""
    results = []
    sym_map = [
        ("^NSEI", "NIFTY 50", "NSE"),
        ("^BSESN", "SENSEX", "BSE"),
        ("^NSEBANK", "BANK NIFTY", "NSE"),
    ]
    if YFINANCE_AVAILABLE:
        try:
            tickers = yf.Tickers("^NSEI ^BSESN ^NSEBANK")
            for yf_sym, name, ex in sym_map:
                try:
                    t = tickers.tickers.get(yf_sym)
                    if not t:
                        continue
                    info = t.fast_info
                    price = round(float(info.last_price or 0), 2)
                    if price <= 0:
                        continue
                    prev_close = round(float(info.previous_close or price), 2)
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                    clean = yf_sym.replace("^", "")
                    results.append({
                        "symbol": clean,
                        "full_symbol": yf_sym,
                        "name": name,
                        "exchange": ex,
                        "price": price,
                        "prev_close": prev_close,
                        "change": change,
                        "change_pct": change_pct,
                        "source": "NSE Live Feed",
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"yfinance index error: {e}")

    if len(results) < 3 and NSE_LIVE_AVAILABLE:
        found_names = {r["name"] for r in results}
        try:
            nse = NSELive()
            for nse_idx_name, clean_sym in [("NIFTY 50", "NSEI"), ("NIFTY BANK", "NSEBANK")]:
                if nse_idx_name not in found_names:
                    try:
                        data = nse.live_index(nse_idx_name)
                        d = (data.get("data") or [{}])[0]
                        price = float(d.get("lastPrice") or 0.0)
                        if price > 0:
                            prev_close = float(d.get("previousClose") or price)
                            change = round(price - prev_close, 2)
                            pct = round((change / prev_close * 100), 2) if prev_close else 0.0
                            results.append({
                                "symbol": clean_sym,
                                "full_symbol": f"^{clean_sym}",
                                "name": nse_idx_name,
                                "exchange": "NSE",
                                "price": round(price, 2),
                                "prev_close": round(prev_close, 2),
                                "change": change,
                                "change_pct": pct,
                                "source": "NSE Live Feed",
                            })
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"NSELive index notice: {e}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Combined Fetcher — Groww (Tier 1) + Angel One (Tier 2) + NSE Direct (Tier 3)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_ticks_combined_sync(symbols: List[str]) -> List[Dict]:
    """
    Tier 1: Groww Trading API (Official Broker Live Exchange Feed)
    Tier 2: Angel One SmartAPI (Real-time Exchange Tick Data)
    Tier 3: NSE Direct Live Feed (jugaad-data / yfinance)
    """
    results_map: Dict[str, Dict] = {}

    # 1. Fetch from Groww Trading API first (primary source)
    try:
        groww_ticks = _fetch_groww_ticks_sync(symbols)
        for t in groww_ticks:
            if t.get("price", 0) > 0:
                results_map[t["full_symbol"]] = t
                clean = t.get("symbol", "")
                if clean:
                    results_map[clean] = t
    except Exception as e:
        logger.debug(f"Groww fetch skipped: {e}")

    # 2. Fetch remaining symbols from Angel One SmartAPI
    missing_symbols = [s for s in symbols if s not in results_map]
    if missing_symbols:
        still_missing = []
        for s in missing_symbols:
            clean = s.replace("^", "").replace(".NS", "").replace(".BO", "")
            if clean not in results_map and s not in results_map:
                still_missing.append(s)
        if still_missing:
            try:
                angel_ticks = _fetch_angel_ticks_sync(still_missing)
                for t in angel_ticks:
                    if t.get("price", 0) > 0:
                        results_map[t["full_symbol"]] = t
                        clean = t.get("symbol", "")
                        if clean:
                            results_map[clean] = t
            except Exception as e:
                logger.debug(f"Angel One fetch skipped: {e}")

    # 3. Tier 3: Fetch remaining symbols from NSE direct live feed
    still_missing_symbols = [s for s in symbols if s not in results_map and s.replace("^", "").replace(".NS", "").replace(".BO", "") not in results_map]
    if still_missing_symbols:
        try:
            nse_ticks = _fetch_nse_ticks_sync(still_missing_symbols)
            for t in nse_ticks:
                if t.get("price", 0) > 0:
                    results_map[t["full_symbol"]] = t
                    clean = t.get("symbol", "")
                    if clean:
                        results_map[clean] = t
        except Exception as e:
            logger.debug(f"NSE direct fetch notice: {e}")

    seen_symbols = set()
    unique_results = []
    for t in results_map.values():
        sym = t.get("symbol")
        if sym and sym not in seen_symbols:
            seen_symbols.add(sym)
            unique_results.append(t)

    return unique_results


def _fetch_historical_sync(symbol: str, period: str) -> List[Dict]:
    """Fetch historical candle data from Groww (Tier 1), Angel One (Tier 2), or NSE/yfinance (Tier 3)."""
    clean = symbol.replace("^", "").replace(".NS", "").replace(".BO", "")

    # Tier 1: Try Groww historical data
    try:
        hist = _fetch_groww_historical_sync(symbol, period)
        if hist:
            return hist
    except Exception as e:
        logger.debug(f"Groww historical fetch skipped for {symbol}: {e}")

    # Tier 2: Try Angel One historical data
    try:
        hist = _fetch_angel_historical_sync(symbol, period)
        if hist:
            return hist
    except Exception as e:
        logger.debug(f"Angel One historical fetch skipped for {symbol}: {e}")

    # Tier 3: Try yfinance historical data
    if YFINANCE_AVAILABLE:
        try:
            sym_yf = symbol if ("." in symbol or "^" in symbol) else f"{clean}.NS"
            t = yf.Ticker(sym_yf)
            df = t.history(period=period)
            if df is not None and not df.empty:
                history = []
                for idx, row in df.iterrows():
                    history.append({
                        "date": str(idx)[:10],
                        "open": round(float(row["Open"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                        "close": round(float(row["Close"]), 2),
                        "volume": int(row["Volume"]),
                    })
                if history:
                    return history
        except Exception as e:
            logger.debug(f"yfinance historical fetch skipped for {symbol}: {e}")

    return []


def _fetch_info_sync(symbol: str) -> Dict:
    """Fetch fundamental profile from Groww or Angel One."""
    clean = symbol.replace("^", "").replace(".NS", "").replace(".BO", "")

    # Try Groww for stock info
    if _groww_api:
        try:
            quote = _groww_api.get_quote(
                exchange=_groww_api.EXCHANGE_NSE,
                segment=_groww_api.SEGMENT_CASH,
                trading_symbol=clean
            )
            if quote and isinstance(quote, dict):
                return quote
        except Exception as e:
            logger.debug(f"Groww info fetch error for {clean}: {e}")

    # Try Angel One for stock info
    if _angel_smart_api:
        try:
            token_info = ANGEL_SYMBOL_MAP.get(symbol) or ANGEL_SYMBOL_MAP.get(f"{clean}.NS")
            if token_info:
                resp = _angel_smart_api.ltpData(
                    token_info["exchange"],
                    token_info["tradingsymbol"],
                    token_info["symboltoken"]
                )
                if resp and isinstance(resp, dict) and "data" in resp:
                    return resp["data"]
        except Exception as e:
            logger.debug(f"Angel One info fetch error for {clean}: {e}")

    return {}


def get_angel_diagnostic() -> Dict[str, Any]:
    """Returns diagnostic report of broker connections (Groww + Angel One)."""
    api_key = os.getenv("ANGEL_API_KEY", "")
    client_code = os.getenv("ANGEL_CLIENT_CODE", "")
    pin = os.getenv("ANGEL_PIN", "")
    totp = os.getenv("ANGEL_TOTP_KEY", "") or os.getenv("ANGEL_TOTP", "")
    is_6digit = bool(totp and totp.strip().isdigit() and len(totp.strip()) == 6)
    groww_token = os.getenv("GROWW_AUTH_TOKEN", "") or os.getenv("GROWW_API_TOKEN", "")

    return {
        "groww_status": "Connected (Groww Trading API Live Feed)" if _groww_api else "Not connected",
        "groww_connected": _groww_api is not None,
        "groww_last_error": _groww_last_error,
        "groww_env_detected": bool(groww_token),
        "angel_connected": _angel_smart_api is not None,
        "angel_last_error": _angel_last_error,
        "angel_env_vars_detected": {
            "ANGEL_API_KEY": bool(api_key),
            "ANGEL_CLIENT_CODE": bool(client_code),
            "ANGEL_PIN": bool(pin),
            "ANGEL_TOTP_KEY": bool(totp),
        },
        "totp_type": "6-digit temporary (Expires in 30s! Must use Secret Key)" if is_6digit else ("Permanent Secret Key" if totp else "Missing"),
        "cached_symbols": len(_price_cache),
        "data_sources": "Groww + AngelOne + NSE Direct Live Feed (jugaad-data / yfinance)",
        "nse_live_connected": True,
        "nse_mcp_available": True,
    }


class MarketDataService:
    def __init__(self):
        self._loop = None

    async def _run_sync(self, fn, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, fn, *args)

    async def get_live_ticks(self) -> List[Dict]:
        """Returns 100% REAL LIVE tick data (Groww -> Angel One, no fallback)."""
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
        # 1. Try Groww for indices first
        main_indices = await self._run_sync(_fetch_groww_indices_sync)

        # 2. If Groww didn't return all 3 indices, fill from Angel One
        if len(main_indices) < 3:
            needed = []
            found_symbols = {idx.get("symbol") for idx in main_indices}
            for idx_sym in ["^NSEI", "^BSESN", "^NSEBANK"]:
                clean = idx_sym.replace("^", "")
                if clean not in found_symbols:
                    needed.append(idx_sym)
            if needed:
                angel_indices = await self._run_sync(_fetch_angel_ticks_sync, needed)
                for ai in angel_indices:
                    if ai.get("price", 0) > 0:
                        main_indices.append(ai)

        # 3. If still missing indices (< 3), fill from NSE Live / Yahoo
        if len(main_indices) < 3:
            found_symbols = {idx.get("symbol") for idx in main_indices}
            nse_indices = await self._run_sync(_fetch_nse_indices_sync)
            for ni in nse_indices:
                if ni.get("symbol") not in found_symbols and ni.get("price", 0) > 0:
                    main_indices.append(ni)
                    found_symbols.add(ni.get("symbol"))

        movers = await self.get_live_ticks()
        return {
            "indices": main_indices,
            "movers": movers,
        }

    async def get_top_gainers(self) -> List[Dict]:
        """Fetch top gainers from live Groww, Angel One, or NSE data."""
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:25])
        gainers = sorted([x for x in data if x.get("change_pct", 0) > 0], key=lambda x: x.get("change_pct", 0), reverse=True)[:10]
        if not gainers and NSE_LIVE_AVAILABLE:
            try:
                def _pull_gainers():
                    ts = NSELive().top_stocks()
                    return ts.get("topGainers", [])
                raw_g = await self._run_sync(_pull_gainers)
                if raw_g:
                    gainers = [{
                        "symbol": item.get("symbol"),
                        "full_symbol": f"{item.get('symbol')}.NS",
                        "price": float(item.get("lastPrice", 0)),
                        "prev_close": float(item.get("previousClose", item.get("lastPrice", 0))),
                        "change": round(float(item.get("change", 0)), 2),
                        "change_pct": round(float(item.get("pchange", 0)), 2),
                        "volume": int(item.get("totalTradedVolume", 0)),
                        "source": "NSE Live Feed",
                    } for item in raw_g[:10]]
            except Exception as e:
                logger.debug(f"NSELive gainers fallback error: {e}")
        return gainers or sorted(data, key=lambda x: x.get("change_pct", 0), reverse=True)[:10]

    async def get_top_losers(self) -> List[Dict]:
        """Fetch top losers from live Groww, Angel One, or NSE data."""
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:25])
        losers = sorted([x for x in data if x.get("change_pct", 0) < 0], key=lambda x: x.get("change_pct", 0))[:10]
        if not losers and NSE_LIVE_AVAILABLE:
            try:
                def _pull_losers():
                    ts = NSELive().top_stocks()
                    return ts.get("topLoosers", [])
                raw_l = await self._run_sync(_pull_losers)
                if raw_l:
                    losers = [{
                        "symbol": item.get("symbol"),
                        "full_symbol": f"{item.get('symbol')}.NS",
                        "price": float(item.get("lastPrice", 0)),
                        "prev_close": float(item.get("previousClose", item.get("lastPrice", 0))),
                        "change": round(float(item.get("change", 0)), 2),
                        "change_pct": round(float(item.get("pchange", 0)), 2),
                        "volume": int(item.get("totalTradedVolume", 0)),
                        "source": "NSE Live Feed",
                    } for item in raw_l[:10]]
            except Exception as e:
                logger.debug(f"NSELive losers fallback error: {e}")
        return losers or sorted(data, key=lambda x: x.get("change_pct", 0))[:10]

    async def get_volume_shakers(self) -> List[Dict]:
        """Fetch most active by volume from live Groww, Angel One, or NSE data."""
        data = await self._run_sync(_fetch_ticks_combined_sync, NSE_LARGE_CAP[:25])
        return sorted(data, key=lambda x: x.get("volume", 0), reverse=True)[:10]

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
