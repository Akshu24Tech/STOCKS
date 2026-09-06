"""
Broker Integration Module
Supports: Zerodha Kite Connect, Upstox v2, Angel One SmartAPI, Groww/Generic CSV
"""
import io
import csv
import logging
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Zerodha Kite Connect
# ─────────────────────────────────────────────────────────────────────────────
class ZerodhaClient:
    BASE = "https://api.kite.trade"

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def get_holdings(self) -> List[Dict]:
        """Fetch equity holdings from Zerodha."""
        try:
            resp = requests.get(f"{self.BASE}/portfolio/holdings", headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("data", [])
            holdings = []
            for h in raw:
                qty = h.get("quantity", 0) + h.get("t1_quantity", 0)
                if qty <= 0:
                    continue
                holdings.append({
                    "symbol": h.get("tradingsymbol", ""),
                    "qty": qty,
                    "buy_price": round(h.get("average_price", 0), 2),
                    "current_price": round(h.get("last_price", 0), 2),
                    "pnl": round(h.get("pnl", 0), 2),
                    "source": "zerodha",
                    "isin": h.get("isin", ""),
                    "exchange": h.get("exchange", "NSE"),
                })
            return holdings
        except requests.RequestException as e:
            raise ValueError(f"Zerodha API error: {str(e)}")

    def get_positions(self) -> List[Dict]:
        """Fetch open positions (intraday + delivery) from Zerodha."""
        try:
            resp = requests.get(f"{self.BASE}/portfolio/positions", headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            positions = []
            for pos_type in ["net", "day"]:
                for p in data.get("data", {}).get(pos_type, []):
                    if p.get("quantity", 0) == 0:
                        continue
                    positions.append({
                        "symbol": p.get("tradingsymbol", ""),
                        "qty": p.get("quantity", 0),
                        "buy_price": round(p.get("average_price", 0), 2),
                        "current_price": round(p.get("last_price", 0), 2),
                        "pnl": round(p.get("pnl", 0), 2),
                        "source": "zerodha",
                        "type": pos_type,
                    })
            return positions
        except requests.RequestException as e:
            raise ValueError(f"Zerodha positions error: {str(e)}")

    @staticmethod
    def get_login_url(api_key: str) -> str:
        return f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"

    @staticmethod
    def exchange_token(api_key: str, api_secret: str, request_token: str) -> str:
        import hashlib
        checksum = hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode()).hexdigest()
        resp = requests.post(
            "https://api.kite.trade/session/token",
            data={"api_key": api_key, "request_token": request_token, "checksum": checksum},
            headers={"X-Kite-Version": "3"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["data"]["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# Upstox v2
# ─────────────────────────────────────────────────────────────────────────────
class UpstoxClient:
    BASE = "https://api.upstox.com/v2"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def get_holdings(self) -> List[Dict]:
        try:
            resp = requests.get(f"{self.BASE}/portfolio/long-term-holdings", headers=self.headers, timeout=10)
            resp.raise_for_status()
            raw = resp.json().get("data", [])
            holdings = []
            for h in raw:
                qty = h.get("quantity", 0)
                if qty <= 0:
                    continue
                symbol = h.get("trading_symbol", "")
                # Upstox uses NSE_EQ|SYMBOL format in instrument_token
                holdings.append({
                    "symbol": symbol,
                    "qty": qty,
                    "buy_price": round(h.get("average_price", 0), 2),
                    "current_price": round(h.get("last_price", 0), 2),
                    "pnl": round(h.get("pnl", 0), 2),
                    "source": "upstox",
                    "isin": h.get("isin", ""),
                    "exchange": h.get("exchange", "NSE"),
                })
            return holdings
        except requests.RequestException as e:
            raise ValueError(f"Upstox API error: {str(e)}")

    @staticmethod
    def get_login_url(api_key: str, redirect_uri: str = "http://localhost:8000/broker/upstox/callback") -> str:
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?client_id={api_key}&redirect_uri={redirect_uri}&response_type=code"
        )

    @staticmethod
    def exchange_token(api_key: str, api_secret: str, code: str,
                        redirect_uri: str = "http://localhost:8000/broker/upstox/callback") -> str:
        resp = requests.post(
            "https://api.upstox.com/v2/login/authorization/token",
            data={
                "code": code,
                "client_id": api_key,
                "client_secret": api_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token", "")


# ─────────────────────────────────────────────────────────────────────────────
# Angel One SmartAPI (Official SDK + pyotp TOTP generation)
# ─────────────────────────────────────────────────────────────────────────────
import pyotp
try:
    from SmartApi import SmartConnect
    SMARTCONNECT_AVAILABLE = True
except ImportError:
    SMARTCONNECT_AVAILABLE = False


class AngelOneClient:
    """
    Official Angel One SmartAPI client.
    Supports either live 6-digit TOTP code or TOTP Secret Key (from Angel One enable-totp page).
    """
    BASE_URLS = [
        "https://apiconnect.angelone.in",
        "https://apiconnect.angelbroking.com",
    ]

    def __init__(self, api_key: str, client_code: str, jwt_token: str, feed_token: str = ""):
        self.api_key = api_key
        self.client_code = client_code
        self.jwt_token = jwt_token
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": api_key,
        }

    @staticmethod
    def resolve_totp(totp_input: str) -> str:
        """Accepts either a 6-digit TOTP or a base32 TOTP secret key."""
        raw = str(totp_input or "").strip().replace(" ", "")
        if raw.isdigit() and len(raw) == 6:
            return raw
        try:
            totp_gen = pyotp.TOTP(raw.upper())
            code = totp_gen.now()
            logger.info("Generated live TOTP from secret key.")
            return str(code)
        except Exception as e:
            logger.warning(f"Failed to generate TOTP from secret: {e}")
            return raw

    @classmethod
    def connect_and_fetch_holdings(cls, api_key: str, client_code: str, pin: str, totp_or_secret: str) -> Dict[str, Any]:
        """
        Authenticates with Angel One SmartAPI and retrieves holdings.
        Returns: { 'status': 'success', 'holdings': [...], 'client_code': client_code, ... }
        """
        api_key = api_key.strip()
        client_code = client_code.strip()
        pin = pin.strip()
        totp_code = cls.resolve_totp(totp_or_secret)

        if not api_key:
            raise ValueError("Angel One API Key is required")
        if not client_code:
            raise ValueError("Angel One Client Code (User ID) is required")
        if not pin:
            raise ValueError("Angel One PIN / Password is required")
        if not totp_code:
            raise ValueError("TOTP code or Secret Key is required")

        # Try SmartConnect official SDK first
        if SMARTCONNECT_AVAILABLE:
            try:
                smart_api = SmartConnect(api_key=api_key)
                session = smart_api.generateSession(client_code, pin, totp_code)

                if session.get("status") is False:
                    msg = session.get("message") or session.get("errorcode") or "Authentication failed with SmartAPI"
                    raise ValueError(f"Angel One Login Error: {msg}")

                data = session.get("data", {})
                jwt_token = data.get("jwtToken", "")
                feed_token = data.get("feedToken", "")

                holdings_resp = None
                try:
                    holdings_resp = smart_api.allholding()
                except Exception as ex:
                    logger.info(f"allholding failed, trying holding(): {ex}")
                    holdings_resp = smart_api.holding()

                if not holdings_resp or holdings_resp.get("status") is False:
                    holdings_resp = smart_api.holding()

                raw_items = []
                if isinstance(holdings_resp, dict):
                    resp_data = holdings_resp.get("data")
                    if isinstance(resp_data, list):
                        raw_items = resp_data
                    elif isinstance(resp_data, dict):
                        raw_items = resp_data.get("holdings", []) or resp_data.get("allholding", []) or []
                elif isinstance(holdings_resp, list):
                    raw_items = holdings_resp

                holdings = cls._parse_angel_holdings(raw_items)
                return {
                    "status": "success",
                    "client_code": client_code,
                    "holdings": holdings,
                    "jwt_token": jwt_token,
                    "feed_token": feed_token,
                    "broker": "angel_one",
                }
            except ValueError:
                raise
            except Exception as e:
                logger.warning(f"SmartConnect SDK failed, falling back to REST: {e}")

        # Fallback to direct HTTP request
        return cls._direct_http_login_and_holdings(api_key, client_code, pin, totp_code)

    @classmethod
    def _direct_http_login_and_holdings(cls, api_key: str, client_code: str, pin: str, totp_code: str) -> Dict[str, Any]:
        last_error = None
        for base in cls.BASE_URLS:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-UserType": "USER",
                    "X-SourceID": "WEB",
                    "X-ClientLocalIP": "127.0.0.1",
                    "X-ClientPublicIP": "127.0.0.1",
                    "X-MACAddress": "00:00:00:00:00:00",
                    "X-PrivateKey": api_key,
                }
                login_resp = requests.post(
                    f"{base}/rest/auth/angelbroking/user/v1/loginByPassword",
                    json={"clientcode": client_code, "password": pin, "totp": totp_code},
                    headers=headers,
                    timeout=12,
                )
                res_json = login_resp.json()
                if not res_json.get("status", False):
                    msg = res_json.get("message") or res_json.get("errorcode") or "Login failed"
                    raise ValueError(f"Angel One: {msg}")

                data = res_json.get("data", {})
                jwt_token = data.get("jwtToken", "")
                feed_token = data.get("feedToken", "")
                headers["Authorization"] = f"Bearer {jwt_token}"

                h_resp = requests.get(
                    f"{base}/rest/secure/angelbroking/portfolio/v1/getAllHolding",
                    headers=headers,
                    timeout=12,
                )
                if h_resp.status_code != 200:
                    h_resp = requests.get(
                        f"{base}/rest/secure/angelbroking/portfolio/v1/getHolding",
                        headers=headers,
                        timeout=12,
                    )

                h_data = h_resp.json()
                raw_items = []
                if isinstance(h_data, dict):
                    inner = h_data.get("data")
                    if isinstance(inner, list):
                        raw_items = inner
                    elif isinstance(inner, dict):
                        raw_items = inner.get("holdings", []) or []

                holdings = cls._parse_angel_holdings(raw_items)
                return {
                    "status": "success",
                    "client_code": client_code,
                    "holdings": holdings,
                    "jwt_token": jwt_token,
                    "feed_token": feed_token,
                    "broker": "angel_one",
                }
            except ValueError:
                raise
            except Exception as e:
                last_error = str(e)
                continue

        raise ValueError(f"Angel One SmartAPI error: {last_error or 'Could not connect to Angel One'}")

    @staticmethod
    def _parse_angel_holdings(raw_items: List[Dict]) -> List[Dict]:
        holdings = []
        for h in raw_items:
            try:
                sym_raw = (
                    h.get("tradingsymbol")
                    or h.get("symbolname")
                    or h.get("tradingSymbol")
                    or h.get("symbol")
                    or ""
                )
                clean_sym = (
                    sym_raw.replace("-EQ", "")
                    .replace("-BE", "")
                    .replace(".NS", "")
                    .replace(".BO", "")
                    .strip()
                    .upper()
                )
                if not clean_sym:
                    continue

                qty = float(h.get("totalholdingqty") or h.get("quantity") or h.get("netqty") or 0)
                if qty <= 0:
                    continue

                buy_price = float(h.get("averageprice") or h.get("avgprice") or h.get("buyPrice") or 0)
                ltp = float(h.get("ltp") or h.get("close") or h.get("price") or buy_price)
                pnl = float(h.get("profitandloss") or h.get("pnl") or round((ltp - buy_price) * qty, 2))

                holdings.append({
                    "symbol": clean_sym,
                    "qty": qty,
                    "buy_price": round(buy_price, 2),
                    "current_price": round(ltp, 2),
                    "pnl": round(pnl, 2),
                    "source": "Angel One SmartAPI",
                    "isin": h.get("isin", ""),
                    "exchange": h.get("exchange", "NSE"),
                })
            except Exception as parse_err:
                logger.warning(f"Error parsing holding item {h}: {parse_err}")
                continue
        return holdings


# ─────────────────────────────────────────────────────────────────────────────
# Generic CSV Parser (Groww / CDSL CAS / Manual)
# ─────────────────────────────────────────────────────────────────────────────
class CSVPortfolioParser:
    """
    Accepts CSV files from Groww, Zerodha P&L, CDSL CAS, or custom format.
    Auto-detects columns.
    """

    SYMBOL_COLS  = ["symbol", "trading_symbol", "tradingsymbol", "stock", "scrip", "security", "instrument"]
    QTY_COLS     = ["quantity", "qty", "shares", "units", "net_quantity", "closing_balance"]
    PRICE_COLS   = ["buy_price", "average_price", "avg_price", "averageprice", "purchase_price", "cost_price", "invested_price"]

    @classmethod
    def _find_col(cls, headers: List[str], candidates: List[str]) -> Optional[str]:
        h_lower = [h.strip().lower().replace(" ", "_") for h in headers]
        for c in candidates:
            if c in h_lower:
                return headers[h_lower.index(c)]
        return None

    @classmethod
    def parse(cls, content: str, source: str = "csv") -> List[Dict]:
        reader = csv.DictReader(io.StringIO(content.strip()))
        headers = reader.fieldnames or []

        sym_col   = cls._find_col(list(headers), cls.SYMBOL_COLS)
        qty_col   = cls._find_col(list(headers), cls.QTY_COLS)
        price_col = cls._find_col(list(headers), cls.PRICE_COLS)

        if not sym_col:
            raise ValueError("Could not find symbol/stock column in CSV. Expected one of: " + ", ".join(cls.SYMBOL_COLS))
        if not qty_col:
            raise ValueError("Could not find quantity column in CSV. Expected one of: " + ", ".join(cls.QTY_COLS))

        holdings = []
        for row in reader:
            symbol = str(row.get(sym_col, "")).strip().upper()
            if not symbol or symbol == "SYMBOL":
                continue
            try:
                qty = float(str(row.get(qty_col, 0)).replace(",", "").strip() or 0)
            except ValueError:
                continue
            if qty <= 0:
                continue
            price = 0.0
            if price_col:
                try:
                    price = float(str(row.get(price_col, 0)).replace(",", "").replace("₹", "").strip() or 0)
                except ValueError:
                    price = 0.0
            holdings.append({
                "symbol": symbol,
                "qty": qty,
                "buy_price": round(price, 2),
                "current_price": 0.0,
                "pnl": 0.0,
                "source": source,
            })
        return holdings


# ─────────────────────────────────────────────────────────────────────────────
# Groww-specific CSV (exported from Groww app "Download Report")
# ─────────────────────────────────────────────────────────────────────────────
class GrowwParser(CSVPortfolioParser):
    """Handles Groww's specific CSV export format."""

    @classmethod
    def parse_groww(cls, content: str) -> List[Dict]:
        # Groww exports include metadata header rows; find the actual data start
        lines = content.splitlines()
        data_start = 0
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ["symbol", "stock", "instrument", "scheme"]):
                data_start = i
                break
        clean_content = "\n".join(lines[data_start:])
        holdings = cls.parse(clean_content, source="groww")
        return holdings
