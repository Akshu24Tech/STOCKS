"""
IndiaStocks AI — Daily Live Analysis Engine
============================================
Run this script daily (via Windows Task Scheduler or manually).
It will:
  1. Fetch live OHLCV data for NIFTY 100 stocks from yfinance
  2. Run the same technical_score engine used in production
  3. Track performance of yesterday's recommendations vs. today's price
  4. Score every stock and classify signals
  5. Generate a rich HTML daily report saved to ./reports/
  6. Append a running CSV performance log for trend tracking

Usage:
    python daily_analysis_engine.py

Schedule (Windows Task Scheduler):
    Action: python C:\...\backend\daily_analysis_engine.py
    Trigger: Daily at 4:00 PM IST (after NSE close at 3:30 PM)
"""

import json
import os
import sys
import math
import datetime
import pandas as pd
import numpy as np
import yfinance as yf

# ─── Add backend dir to path so we can import recommender ───────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommender import technical_score, compute_5year_metrics, fundamental_score

# ─── Config ─────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR     = os.path.join(BASE_DIR, "reports")
HISTORY_FILE    = os.path.join(BASE_DIR, "daily_rec_history.json")
PERF_LOG_FILE   = os.path.join(BASE_DIR, "daily_perf_log.csv")
os.makedirs(REPORTS_DIR, exist_ok=True)

TODAY        = datetime.date.today().isoformat()
NOW_STR      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
REPORT_FILE  = os.path.join(REPORTS_DIR, f"report_{TODAY}.html")

# ─── NIFTY 100 Universe ──────────────────────────────────────────────────────
NIFTY_100 = [
    # Banking & Finance
    ("HDFCBANK",   "Banking"),    ("ICICIBANK",  "Banking"),    ("SBIN",       "Banking"),
    ("AXISBANK",   "Banking"),    ("KOTAKBANK",  "Banking"),    ("BAJFINANCE", "NBFC"),
    ("BAJAJFINSV", "NBFC"),       ("SHRIRAMFIN", "NBFC"),
    # IT
    ("TCS",        "IT"),         ("INFY",       "IT"),         ("WIPRO",      "IT"),
    ("HCLTECH",    "IT"),         ("TECHM",      "IT"),         ("PERSISTENT", "IT"),
    # FMCG & Consumer
    ("HINDUNILVR", "FMCG"),       ("ITC",        "FMCG"),       ("NESTLEIND",  "FMCG"),
    ("BRITANNIA",  "FMCG"),       ("MARICO",     "FMCG"),       ("DABUR",      "FMCG"),
    # Auto
    ("MARUTI",     "Auto"),       ("BAJAJ-AUTO", "Auto"),       ("EICHERMOT",  "Auto"),
    ("HEROMOTOCO", "Auto"),       ("M&M",        "Auto"),
    # Pharma
    ("SUNPHARMA",  "Pharma"),     ("DRREDDY",    "Pharma"),     ("CIPLA",      "Pharma"),
    ("DIVISLAB",   "Pharma"),     ("APOLLOHOSP", "Healthcare"),
    # Energy & Metals
    ("RELIANCE",   "Conglomerate"),("ONGC",      "Energy"),     ("BPCL",       "Energy"),
    ("NTPC",       "Energy"),     ("COALINDIA",  "Mining"),     ("TATASTEEL",  "Metals"),
    ("JSWSTEEL",   "Metals"),     ("HINDALCO",   "Metals"),
    # Capital Goods / Defence
    ("LT",         "Engineering"),("HAL",        "Defence"),    ("BEL",        "Defence"),
    ("POWERGRID",  "Utilities"),
    # Consumer Discretionary
    ("TITAN",      "Consumer"),   ("ASIANPAINT", "Consumer"),   ("TRENT",      "Retail"),
    ("GRASIM",     "Cement"),     ("ULTRACEMCO", "Cement"),     ("ADANIENT",   "Conglomerate"),
    # Miscellaneous
    ("BHARTIARTL", "Telecom"),    ("TATACONSUM", "FMCG"),
]

# ─── Fetch + Score ───────────────────────────────────────────────────────────
def fetch_and_score(symbol: str, sector: str) -> dict | None:
    """Fetch 6-month OHLCV from yfinance and run the full scoring engine."""
    full_sym = f"{symbol}.NS"
    try:
        t = yf.Ticker(full_sym)
        hist = t.history(period="6mo")
        if hist.empty or len(hist) < 55:
            print(f"  [SKIP] {symbol} — insufficient data")
            return None

        closes  = hist["Close"]
        volumes = hist["Volume"]

        # ATR for volatility measurement
        high_low    = hist["High"] - hist["Low"]
        high_close  = (hist["High"] - hist["Close"].shift()).abs()
        low_close   = (hist["Low"]  - hist["Close"].shift()).abs()
        ranges      = pd.concat([high_low, high_close, low_close], axis=1)
        atr_14      = float(ranges.max(axis=1).rolling(14).mean().iloc[-1])

        ta          = technical_score(closes, volumes)
        h5          = compute_5year_metrics(closes)

        price_today = round(float(closes.iloc[-1]), 2)
        price_prev  = round(float(closes.iloc[-2]), 2) if len(closes) >= 2 else price_today
        day_chg_pct = round((price_today - price_prev) / price_prev * 100, 2) if price_prev else 0.0

        # RSI strength label
        rsi = ta["rsi"]
        rsi_label = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"

        return {
            "symbol":       symbol,
            "sector":       sector,
            "price":        price_today,
            "price_prev":   price_prev,
            "day_chg_pct":  day_chg_pct,
            "score":        ta["score"],
            "rating":       ta["rating"],
            "rsi":          rsi,
            "rsi_label":    rsi_label,
            "macd_bullish": ta["macd"]["bullish"],
            "macd_hist":    ta["macd"]["histogram"],
            "bb_pos_pct":   ta["bollinger"]["position_pct"],
            "above_ma200":  ta["moving_averages"]["above_ma200"],
            "above_ma50":   ta["moving_averages"]["above_ma50"],
            "golden_cross": ta["moving_averages"]["golden_cross"],
            "atr_14":       round(atr_14, 2),
            "1y_cagr":      h5["1y_cagr"],
            "volatility":   h5["annualized_volatility_5y"],
            "date":         TODAY,
        }
    except Exception as e:
        print(f"  [ERROR] {symbol}: {e}")
        return None


# ─── Track Yesterday's Performance ──────────────────────────────────────────
def load_yesterday() -> list[dict]:
    """Load yesterday's recommendations if they exist."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE) as f:
        data = json.load(f)
    # Return the most recent date's entries that is NOT today
    dates = sorted(set(d["date"] for d in data), reverse=True)
    prev_date = next((d for d in dates if d != TODAY), None)
    if not prev_date:
        return []
    return [d for d in data if d["date"] == prev_date]


def compute_signal_performance(yesterday: list[dict], today_map: dict) -> list[dict]:
    """Compare yesterday's signals to today's price and compute 1-day return."""
    results = []
    for rec in yesterday:
        sym = rec["symbol"]
        if sym not in today_map:
            continue
        today_price = today_map[sym]["price"]
        entry_price = rec["price"]
        pnl_pct     = round((today_price - entry_price) / entry_price * 100, 2)
        results.append({
            "symbol":       sym,
            "signal_given": rec["rating"],
            "entry_price":  entry_price,
            "exit_price":   today_price,
            "pnl_pct":      pnl_pct,
            "signal_date":  rec["date"],
        })
    return results


# ─── Save History ────────────────────────────────────────────────────────────
def save_history(today_results: list[dict]):
    existing = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            existing = json.load(f)
    # Remove today's entries if re-running
    existing = [e for e in existing if e["date"] != TODAY]
    existing.extend(today_results)
    # Keep only last 30 days of data
    cutoff = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    existing = [e for e in existing if e["date"] >= cutoff]
    with open(HISTORY_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def append_perf_log(perf_records: list[dict]):
    rows = []
    for r in perf_records:
        correct = (r["signal_given"] in ["Buy", "Strong Buy"] and r["pnl_pct"] > 0) or \
                  (r["signal_given"] == "Sell" and r["pnl_pct"] < 0)
        rows.append({
            "date": TODAY,
            "symbol": r["symbol"],
            "signal": r["signal_given"],
            "pnl_pct": r["pnl_pct"],
            "correct": correct
        })
    df = pd.DataFrame(rows)
    if os.path.exists(PERF_LOG_FILE):
        df.to_csv(PERF_LOG_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(PERF_LOG_FILE, index=False)


# ─── HTML Report Generator ───────────────────────────────────────────────────
def rating_color(rating: str) -> str:
    return {"Strong Buy": "#00E676", "Buy": "#69F0AE", "Hold": "#FFD740", "Sell": "#FF5252"}.get(rating, "#aaa")

def rating_badge(rating: str) -> str:
    color = rating_color(rating)
    return f'<span style="background:{color};color:#111;padding:2px 10px;border-radius:12px;font-weight:700;font-size:0.8em;">{rating}</span>'

def chg_color(val: float) -> str:
    return "#00E676" if val >= 0 else "#FF5252"

def pct_fmt(val: float) -> str:
    sign = "+" if val >= 0 else ""
    color = chg_color(val)
    return f'<span style="color:{color};font-weight:600;">{sign}{val:.2f}%</span>'

def bool_icon(val: bool) -> str:
    return "✅" if val else "❌"

def generate_html(today_results: list, perf_records: list, read_perf_log: pd.DataFrame | None) -> str:
    total         = len(today_results)
    strong_buys   = [r for r in today_results if r["rating"] == "Strong Buy"]
    buys          = [r for r in today_results if r["rating"] == "Buy"]
    holds         = [r for r in today_results if r["rating"] == "Hold"]
    sells         = [r for r in today_results if r["rating"] == "Sell"]
    avg_score     = round(sum(r["score"] for r in today_results) / total, 1) if total else 0
    market_mood   = "Bullish" if avg_score > 58 else "Bearish" if avg_score < 45 else "Neutral"
    mood_color    = "#00E676" if market_mood == "Bullish" else "#FF5252" if market_mood == "Bearish" else "#FFD740"

    # Sector summary
    sector_map: dict[str, list] = {}
    for r in today_results:
        sector_map.setdefault(r["sector"], []).append(r["score"])
    sector_rows = ""
    for sec, scores in sorted(sector_map.items(), key=lambda x: -sum(x[1])/len(x[1])):
        avg = round(sum(scores)/len(scores), 1)
        sector_rows += f"<tr><td>{sec}</td><td>{len(scores)}</td><td><b style='color:{mood_color}'>{avg}</b></td></tr>"

    # Yesterday's signal performance table
    perf_html = "<p style='color:#888'>No previous day signals to evaluate yet.</p>"
    if perf_records:
        correct_count  = sum(1 for p in perf_records if
                             (p["signal_given"] in ["Buy","Strong Buy"] and p["pnl_pct"] > 0) or
                             (p["signal_given"] == "Sell" and p["pnl_pct"] < 0))
        accuracy       = round(correct_count / len(perf_records) * 100, 1)
        avg_pnl        = round(sum(p["pnl_pct"] for p in perf_records) / len(perf_records), 2)

        rows = ""
        for p in sorted(perf_records, key=lambda x: -abs(x["pnl_pct"])):
            correct_icon = "✅" if (p["signal_given"] in ["Buy","Strong Buy"] and p["pnl_pct"] > 0) or \
                                   (p["signal_given"] == "Sell" and p["pnl_pct"] < 0) else "❌"
            rows += f"""<tr>
                <td><b>{p['symbol']}</b></td>
                <td>{rating_badge(p['signal_given'])}</td>
                <td>Rs {p['entry_price']}</td>
                <td>Rs {p['exit_price']}</td>
                <td>{pct_fmt(p['pnl_pct'])}</td>
                <td style='text-align:center'>{correct_icon}</td>
            </tr>"""

        perf_html = f"""
            <div class="stat-row">
                <div class="stat-card"><div class="stat-val">{len(perf_records)}</div><div class="stat-label">Signals Tracked</div></div>
                <div class="stat-card"><div class="stat-val" style="color:{chg_color(accuracy - 50)}">{accuracy}%</div><div class="stat-label">Signal Accuracy</div></div>
                <div class="stat-card"><div class="stat-val" style="color:{chg_color(avg_pnl)}">{'+' if avg_pnl>=0 else ''}{avg_pnl}%</div><div class="stat-label">Avg 1-Day Return</div></div>
            </div>
            <table class="data-table">
                <thead><tr><th>Symbol</th><th>Signal</th><th>Entry Price</th><th>Today's Price</th><th>1-Day Return</th><th>Correct?</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>"""

    # Cumulative accuracy from log
    cumulative_html = ""
    if read_perf_log is not None and not read_perf_log.empty:
        total_correct = read_perf_log["correct"].sum()
        total_signals = len(read_perf_log)
        cum_acc = round(total_correct / total_signals * 100, 1)
        cum_pnl = round(read_perf_log["pnl_pct"].mean(), 2)
        cumulative_html = f"""
        <div class="section">
            <h2>Cumulative Signal Performance (All Time)</h2>
            <div class="stat-row">
                <div class="stat-card"><div class="stat-val">{total_signals}</div><div class="stat-label">Total Signals Logged</div></div>
                <div class="stat-card"><div class="stat-val" style="color:{chg_color(cum_acc-50)}">{cum_acc}%</div><div class="stat-label">Cumulative Accuracy</div></div>
                <div class="stat-card"><div class="stat-val" style="color:{chg_color(cum_pnl)}">{'+' if cum_pnl>=0 else ''}{cum_pnl}%</div><div class="stat-label">Avg Return/Signal</div></div>
            </div>
        </div>"""

    # Main stock table — sorted by score
    stock_rows = ""
    for r in sorted(today_results, key=lambda x: -x["score"]):
        stock_rows += f"""<tr>
            <td><b>{r['symbol']}</b></td>
            <td><span style='color:#888;font-size:0.85em'>{r['sector']}</span></td>
            <td>Rs {r['price']}</td>
            <td>{pct_fmt(r['day_chg_pct'])}</td>
            <td><b>{r['score']}</b></td>
            <td>{rating_badge(r['rating'])}</td>
            <td style='color:{"#00E676" if r["rsi"]<30 else "#FF5252" if r["rsi"]>70 else "#aaa"}'>{r['rsi']} ({r['rsi_label']})</td>
            <td>{'🟢' if r['macd_bullish'] else '🔴'} {r['macd_hist']:+.2f}</td>
            <td>{r['bb_pos_pct']:.0f}%</td>
            <td>{bool_icon(r['above_ma200'])}</td>
            <td>{bool_icon(r['golden_cross'])}</td>
            <td>{r['atr_14']}</td>
            <td>{r['1y_cagr']:+.1f}%</td>
        </tr>"""

    # Action list
    action_rows = ""
    for r in strong_buys + buys:
        action_rows += f"<li><b>{r['symbol']}</b> ({r['sector']}) — {rating_badge(r['rating'])} | Score: {r['score']} | RSI: {r['rsi']} | Price: Rs {r['price']}</li>"
    for r in sells:
        action_rows += f"<li><b>{r['symbol']}</b> ({r['sector']}) — {rating_badge(r['rating'])} | Score: {r['score']} | RSI: {r['rsi']} | Price: Rs {r['price']}</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IndiaStocks AI — Daily Report {TODAY}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #e6edf3; line-height: 1.6; }}
  .header {{ background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); padding: 36px 40px; border-bottom: 1px solid #30363d; }}
  .header h1 {{ font-size: 2em; font-weight: 800; color: #58a6ff; }}
  .header p {{ color: #8b949e; margin-top: 4px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 30px 20px; }}
  .section {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; margin-bottom: 28px; }}
  .section h2 {{ font-size: 1.2em; font-weight: 700; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 18px; }}
  .stat-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
  .stat-card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 10px; padding: 18px 24px; flex: 1; min-width: 140px; text-align: center; }}
  .stat-val {{ font-size: 2em; font-weight: 800; color: #e6edf3; }}
  .stat-label {{ font-size: 0.8em; color: #8b949e; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .mood-badge {{ display: inline-block; padding: 6px 20px; border-radius: 20px; font-size: 1.1em; font-weight: 700; margin-top: 8px; background: {mood_color}22; color: {mood_color}; border: 1px solid {mood_color}55; }}
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.88em; }}
  .data-table th {{ background: #0d1117; color: #8b949e; padding: 10px 12px; text-align: left; border-bottom: 1px solid #30363d; font-weight: 600; font-size: 0.82em; text-transform: uppercase; position: sticky; top: 0; }}
  .data-table td {{ padding: 9px 12px; border-bottom: 1px solid #21262d; vertical-align: middle; }}
  .data-table tr:hover {{ background: #1c2128; }}
  .table-wrapper {{ overflow-x: auto; }}
  .sector-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  .sector-table td, .sector-table th {{ padding: 8px 14px; border-bottom: 1px solid #21262d; }}
  .sector-table th {{ color: #8b949e; font-size: 0.8em; text-transform: uppercase; }}
  ul.action-list {{ list-style: none; padding: 0; }}
  ul.action-list li {{ padding: 10px 16px; border-left: 3px solid #30363d; margin-bottom: 8px; background: #0d1117; border-radius: 0 8px 8px 0; }}
  .footer {{ text-align: center; color: #8b949e; font-size: 0.82em; padding: 24px; border-top: 1px solid #30363d; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <h1>📊 IndiaStocks AI — Daily Analysis Report</h1>
  <p>Generated: {NOW_STR} IST &nbsp;|&nbsp; Universe: {total} stocks (NIFTY 100 subset) &nbsp;|&nbsp; Data source: Yahoo Finance (yfinance)</p>
</div>
<div class="container">

  <!-- Market Overview -->
  <div class="section">
    <h2>Market Overview</h2>
    <div class="stat-row">
      <div class="stat-card"><div class="stat-val">{total}</div><div class="stat-label">Stocks Analyzed</div></div>
      <div class="stat-card"><div class="stat-val" style="color:#00E676">{len(strong_buys)}</div><div class="stat-label">Strong Buy</div></div>
      <div class="stat-card"><div class="stat-val" style="color:#69F0AE">{len(buys)}</div><div class="stat-label">Buy</div></div>
      <div class="stat-card"><div class="stat-val" style="color:#FFD740">{len(holds)}</div><div class="stat-label">Hold</div></div>
      <div class="stat-card"><div class="stat-val" style="color:#FF5252">{len(sells)}</div><div class="stat-label">Sell</div></div>
      <div class="stat-card"><div class="stat-val">{avg_score}</div><div class="stat-label">Avg Technical Score</div></div>
    </div>
    <div>Market Mood: <span class="mood-badge">{market_mood}</span></div>
  </div>

  <!-- Yesterday's Signal Performance -->
  <div class="section">
    <h2>Yesterday's Signal Performance (Live Tracking)</h2>
    {perf_html}
  </div>

  {cumulative_html}

  <!-- Today's Action List -->
  <div class="section">
    <h2>Today's Actionable Signals</h2>
    <ul class="action-list">{action_rows if action_rows else '<li style="color:#8b949e">No strong buy or sell signals today.</li>'}</ul>
  </div>

  <!-- Sector Summary -->
  <div class="section">
    <h2>Sector Summary (Avg Technical Score)</h2>
    <table class="sector-table">
      <thead><tr><th>Sector</th><th>Stocks</th><th>Avg Score</th></tr></thead>
      <tbody>{sector_rows}</tbody>
    </table>
  </div>

  <!-- Full Stock Data -->
  <div class="section">
    <h2>Full NIFTY 100 Stock Scores ({TODAY})</h2>
    <p style="color:#8b949e;font-size:0.85em;margin-bottom:14px;">
      <b>Data evaluated per stock:</b> Daily Close (RSI/MACD/BB/MA), High+Low (ATR trailing stop), Volume (surge signal) &nbsp;|&nbsp;
      <b>Score = Baseline 50 + RSI ± MACD ± BB ± MA trend ± Volume</b>
    </p>
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Sector</th><th>Price</th><th>Day %</th>
            <th>Score</th><th>Rating</th><th>RSI (14)</th>
            <th>MACD</th><th>BB Pos%</th>
            <th>Above MA200</th><th>Golden Cross</th>
            <th>ATR(14)</th><th>1Y CAGR</th>
          </tr>
        </thead>
        <tbody>{stock_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Methodology Note -->
  <div class="section">
    <h2>Evaluation Methodology</h2>
    <table class="sector-table">
      <thead><tr><th>Indicator</th><th>Formula / Source</th><th>Score Impact</th></tr></thead>
      <tbody>
        <tr><td>RSI (14)</td><td>100 - [100/(1+AvgGain/AvgLoss)] over 14 days</td><td>+15 if &lt;30, -10 if &gt;70, +5 if neutral</td></tr>
        <tr><td>MACD (12,26,9)</td><td>EMA(12)-EMA(26), Signal=EMA(9) of MACD</td><td>+10 if histogram&gt;0, -5 if &lt;0</td></tr>
        <tr><td>Bollinger Bands (20,2)</td><td>Price position as % of band width</td><td>+10 if &lt;20%, -5 if &gt;80%</td></tr>
        <tr><td>MA20/50/200</td><td>Simple rolling mean</td><td>+3 each if price above; +8 for Golden Cross</td></tr>
        <tr><td>Trend Filter (MA200)</td><td>Price below 200-day MA</td><td><b>-15 pts penalty</b> (anti-falling-knife)</td></tr>
        <tr><td>Volume Surge</td><td>5-day avg / 20-day avg &gt; 1.2</td><td>+5 if confirmed</td></tr>
        <tr><td>ATR Trailing Stop</td><td>Highest Price - 2.5 × 14-day ATR</td><td>Used in live tracking exit logic</td></tr>
      </tbody>
    </table>
  </div>

</div>
<div class="footer">
  IndiaStocks AI Daily Analysis Engine &nbsp;|&nbsp; Report for {TODAY} &nbsp;|&nbsp;
  Data from Yahoo Finance &nbsp;|&nbsp; NOT financial advice
</div>
</body>
</html>"""


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"IndiaStocks AI — Daily Analysis Engine")
    print(f"Date: {TODAY}  |  Time: {NOW_STR}")
    print(f"{'='*60}\n")

    # 1. Load yesterday's recommendations
    yesterday = load_yesterday()
    print(f"Loaded {len(yesterday)} records from yesterday's recommendations.\n")

    # 2. Fetch and score today's stocks
    today_results = []
    for symbol, sector in NIFTY_100:
        print(f"  [{symbol}] Fetching daily Close, High, Low, Volume data...")
        result = fetch_and_score(symbol, sector)
        if result:
            today_results.append(result)

    print(f"\nScored {len(today_results)} stocks successfully.")

    # 3. Build a today lookup map
    today_map = {r["symbol"]: r for r in today_results}

    # 4. Track yesterday's performance
    perf_records = compute_signal_performance(yesterday, today_map)
    if perf_records:
        correct = sum(1 for p in perf_records
                      if (p["signal_given"] in ["Buy","Strong Buy"] and p["pnl_pct"] > 0)
                      or (p["signal_given"] == "Sell" and p["pnl_pct"] < 0))
        print(f"\nYesterday's signal accuracy: {correct}/{len(perf_records)} = {round(correct/len(perf_records)*100,1)}%")

    # 5. Save today's results as new history
    save_history(today_results)
    print(f"Saved today's {len(today_results)} recommendations to history.")

    # 6. Append to cumulative perf log
    if perf_records:
        append_perf_log(perf_records)
        print(f"Appended {len(perf_records)} records to performance log.")

    # 7. Read cumulative perf log
    perf_log_df = None
    if os.path.exists(PERF_LOG_FILE):
        perf_log_df = pd.read_csv(PERF_LOG_FILE)

    # 8. Generate HTML report
    html = generate_html(today_results, perf_records, perf_log_df)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nReport saved: {REPORT_FILE}")
    print("\nTop Signals Today:")
    sorted_res = sorted(today_results, key=lambda x: -x["score"])
    for r in sorted_res[:10]:
        sign = "+" if r["day_chg_pct"] >= 0 else ""
        print(f"  {r['symbol']:<14} {r['rating']:<12} Score: {r['score']:<6} RSI: {r['rsi']:<6} Day: {sign}{r['day_chg_pct']}%")

    print(f"\nDone. Open: {REPORT_FILE}")


if __name__ == "__main__":
    main()
