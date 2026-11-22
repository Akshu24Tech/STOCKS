"""
IndiaStocks AI — Advanced Backtesting Engine v2
================================================
Improvements over v1:
  - Uses upgraded 9-indicator technical_score (ADX, Stochastic, OBV, ROC, Williams %R)
  - Passes real High/Low data to the scorer (no approximation)
  - Score-confidence based position sizing (stronger signal → more capital deployed)
  - Models transaction costs: 0.25% brokerage + 0.1% STT per trade
  - Computes Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate, Profit Factor
  - Generates a rich self-contained HTML report with per-stock and aggregate analysis
"""

import json
import os
import math
import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommender import technical_score

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TRANSACTION_COST_PCT = 0.0035   # 0.25% brokerage + 0.1% STT per trade (both sides)
RISK_FREE_RATE       = 0.065    # 6.5% annual Indian T-bill rate
INITIAL_CAPITAL      = 100_000.0

NIFTY_100_UNIVERSE = [
    ("RELIANCE","Conglomerate"), ("TCS","IT"),            ("HDFCBANK","Banking"),
    ("INFY","IT"),               ("ICICIBANK","Banking"),  ("SBIN","Banking"),
    ("BHARTIARTL","Telecom"),    ("ITC","FMCG"),           ("HINDUNILVR","FMCG"),
    ("LT","Engineering"),        ("BAJFINANCE","NBFC"),    ("AXISBANK","Banking"),
    ("KOTAKBANK","Banking"),     ("MARUTI","Auto"),         ("SUNPHARMA","Pharma"),
    ("M&M","Auto"),              ("ASIANPAINT","Consumer"), ("TITAN","Consumer"),
    ("NTPC","Energy"),           ("ULTRACEMCO","Cement"),   ("POWERGRID","Utilities"),
    ("BAJAJFINSV","NBFC"),       ("TATASTEEL","Metals"),    ("ADANIENT","Conglomerate"),
    ("COALINDIA","Mining"),      ("ONGC","Energy"),         ("WIPRO","IT"),
    ("HCLTECH","IT"),            ("NESTLEIND","FMCG"),      ("GRASIM","Cement"),
    ("TECHM","IT"),              ("JSWSTEEL","Metals"),     ("HINDALCO","Metals"),
    ("DRREDDY","Pharma"),        ("BAJAJ-AUTO","Auto"),     ("CIPLA","Pharma"),
    ("APOLLOHOSP","Healthcare"), ("TATACONSUM","FMCG"),     ("BRITANNIA","FMCG"),
    ("EICHERMOT","Auto"),        ("DIVISLAB","Pharma"),     ("BPCL","Energy"),
    ("HEROMOTOCO","Auto"),       ("SHRIRAMFIN","NBFC"),     ("TRENT","Retail"),
    ("BEL","Defence"),           ("HAL","Defence"),          ("TATAMOTORS","Auto"),
]


def compute_advanced_metrics(capital_history: list, trades: list, initial_capital: float, years: float = 2.0) -> dict:
    """Compute Sharpe, Sortino, Max Drawdown, Win Rate, Profit Factor."""
    if not capital_history or len(capital_history) < 2:
        return {}

    values = np.array(capital_history, dtype=float)
    daily_returns = np.diff(values) / values[:-1]

    # Sharpe Ratio (annualised)
    daily_rf = RISK_FREE_RATE / 252
    excess   = daily_returns - daily_rf
    sharpe   = float(np.mean(excess) / (np.std(excess) + 1e-9) * np.sqrt(252)) if len(excess) > 1 else 0.0

    # Sortino Ratio (only downside deviation)
    downside = excess[excess < 0]
    sortino  = float(np.mean(excess) / (np.std(downside) + 1e-9) * np.sqrt(252)) if len(downside) > 0 else sharpe

    # Maximum Drawdown
    peak      = np.maximum.accumulate(values)
    drawdowns = (values - peak) / peak * 100
    max_dd    = float(np.min(drawdowns))

    # Win Rate & Profit Factor
    closed = [t for t in trades if t["type"] not in ("BUY",)]
    wins   = [t for t in closed if t.get("pnl_pct", 0) > 0]
    losses = [t for t in closed if t.get("pnl_pct", 0) < 0]
    win_rate  = len(wins) / len(closed) * 100 if closed else 0
    gross_win = sum(t.get("pnl_pct", 0) for t in wins)
    gross_loss= abs(sum(t.get("pnl_pct", 0) for t in losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    return {
        "sharpe":        round(sharpe, 3),
        "sortino":       round(sortino, 3),
        "max_drawdown":  round(max_dd, 2),
        "win_rate":      round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "total_trades":  len(closed),
        "winning_trades": len(wins),
        "losing_trades":  len(losses),
    }


def run_backtest(symbol: str, sector: str, years: str = "2y", initial_capital: float = INITIAL_CAPITAL):
    full_sym = f"{symbol}.NS"
    print(f"  [{symbol}] Fetching Close, High, Low, Volume for last {years}...")

    t = yf.Ticker(full_sym)
    hist = t.history(period=years)
    if hist.empty or len(hist) < 55:
        print(f"  [{symbol}] Insufficient data, skipping.")
        return None

    closes  = hist["Close"]
    highs   = hist["High"]
    lows    = hist["Low"]
    volumes = hist["Volume"]

    # ATR for dynamic trailing stop
    tr     = pd.concat([highs-lows, (highs-closes.shift()).abs(), (lows-closes.shift()).abs()], axis=1).max(axis=1)
    atr    = tr.rolling(14).mean()

    capital       = initial_capital
    position      = 0
    entry_price   = 0.0
    peak_price    = 0.0
    entry_score   = 0.0
    capital_curve = []   # daily portfolio value
    trades        = []

    for i in range(50, len(closes)):
        date          = hist.index[i]
        price         = float(closes.iloc[i])
        cur_atr       = float(atr.iloc[i]) if not np.isnan(atr.iloc[i]) else price * 0.015

        # Compute score with real H/L data
        ta = technical_score(
            closes.iloc[:i+1],
            volumes.iloc[:i+1],
            highs.iloc[:i+1],
            lows.iloc[:i+1],
        )
        rating    = ta["rating"]
        score     = ta["score"]
        confidence= ta.get("confidence", 70.0)

        portfolio_value = capital + position * price
        capital_curve.append(portfolio_value)

        if position > 0:
            peak_price = max(peak_price, price)

            trailing_stop  = peak_price - 2.5 * cur_atr
            hard_stop      = entry_price * 0.94
            tech_sell      = rating == "Sell"

            exit_reason = None
            if price <= hard_stop:       exit_reason = "Stop Loss (Fixed -6%)"
            elif price <= trailing_stop: exit_reason = "Stop Loss (ATR Trail)"
            elif tech_sell:              exit_reason = "Sell (Technical)"

            if exit_reason:
                gross_revenue = position * price
                cost          = gross_revenue * TRANSACTION_COST_PCT  # STT+brokerage on sell
                revenue       = gross_revenue - cost
                capital      += revenue
                pnl_pct       = (price - entry_price) / entry_price * 100

                trades.append({
                    "date":    date.strftime("%Y-%m-%d"),
                    "type":    exit_reason,
                    "price":   round(price, 2),
                    "shares":  position,
                    "pnl_pct": round(pnl_pct, 2),
                    "rating":  rating,
                })
                position    = 0
                entry_price = 0.0
                peak_price  = 0.0

        elif rating in ("Buy", "Strong Buy") and position == 0:
            # Score-confidence based position sizing: deploy 60–100% of capital
            allocation = min(1.0, 0.60 + (confidence / 100) * 0.40)
            invest     = capital * allocation
            shares     = int(invest // price)

            if shares > 0:
                cost        = shares * price * (1 + TRANSACTION_COST_PCT)  # brokerage on buy
                if cost > capital:
                    shares  = int((capital / (price * (1 + TRANSACTION_COST_PCT))))
                    cost    = shares * price * (1 + TRANSACTION_COST_PCT)

                if shares > 0:
                    capital    -= cost
                    position   += shares
                    entry_price = price
                    peak_price  = price
                    entry_score = score

                    trades.append({
                        "date":       date.strftime("%Y-%m-%d"),
                        "type":       "BUY",
                        "price":      round(price, 2),
                        "shares":     shares,
                        "score":      score,
                        "confidence": confidence,
                        "rating":     rating,
                        "allocation": round(allocation * 100, 1),
                    })

    # Close any open position at end
    final_price = float(closes.iloc[-1])
    if position > 0:
        gross  = position * final_price
        revenue = gross - gross * TRANSACTION_COST_PCT
        capital += revenue
        trades.append({
            "date":    hist.index[-1].strftime("%Y-%m-%d"),
            "type":    "SELL (END)",
            "price":   round(final_price, 2),
            "shares":  position,
            "pnl_pct": round((final_price - entry_price) / entry_price * 100, 2),
            "rating":  "END",
        })
        capital_curve.append(capital)

    # Calculate benchmark
    start_price    = float(closes.iloc[50])
    bh_return      = (final_price - start_price) / start_price * 100
    strat_return   = (capital - initial_capital) / initial_capital * 100
    alpha          = strat_return - bh_return

    adv_metrics = compute_advanced_metrics(capital_curve, trades, initial_capital)

    return {
        "symbol":           symbol,
        "sector":           sector,
        "initial_capital":  initial_capital,
        "final_capital":    round(capital, 2),
        "strategy_return":  round(strat_return, 2),
        "bh_return":        round(bh_return, 2),
        "alpha":            round(alpha, 2),
        "trades_count":     len([t for t in trades if t["type"] not in ("BUY",)]),
        "sharpe":           adv_metrics.get("sharpe", 0),
        "sortino":          adv_metrics.get("sortino", 0),
        "max_drawdown":     adv_metrics.get("max_drawdown", 0),
        "win_rate":         adv_metrics.get("win_rate", 0),
        "profit_factor":    adv_metrics.get("profit_factor", 0),
        "winning_trades":   adv_metrics.get("winning_trades", 0),
        "losing_trades":    adv_metrics.get("losing_trades", 0),
        "recent_trades":    trades[-8:],
    }


def generate_html_report(results: list, run_date: str) -> str:
    """Generate a self-contained dark-mode HTML report."""

    def rcolor(v, good_pos=True):
        if v is None: return "#aaa"
        return ("#00E676" if v >= 0 else "#FF5252") if good_pos else ("#FF5252" if v >= 0 else "#00E676")

    def fmt(v, suffix="%", decimals=2):
        if v is None: return "N/A"
        sign = "+" if float(v) >= 0 else ""
        return f"{sign}{float(v):.{decimals}f}{suffix}"

    profitable = [r for r in results if r["strategy_return"] > 0]
    alpha_positive = [r for r in results if r["alpha"] > 0]
    avg_strat   = sum(r["strategy_return"] for r in results) / len(results)
    avg_bh      = sum(r["bh_return"] for r in results) / len(results)
    avg_alpha   = avg_strat - avg_bh
    avg_sharpe  = sum(r["sharpe"] for r in results) / len(results)
    avg_wr      = sum(r["win_rate"] for r in results) / len(results)
    avg_dd      = sum(r["max_drawdown"] for r in results) / len(results)

    # Sort by alpha descending for main table
    sorted_res = sorted(results, key=lambda x: -x["alpha"])

    rows = ""
    for r in sorted_res:
        sr_c  = rcolor(r["strategy_return"])
        bh_c  = rcolor(r["bh_return"])
        al_c  = rcolor(r["alpha"])
        sh_c  = rcolor(r["sharpe"])
        dd_c  = rcolor(r["max_drawdown"], good_pos=False)
        wr_c  = rcolor(r["win_rate"] - 50)
        rows += f"""<tr>
            <td><b>{r['symbol']}</b></td>
            <td style="color:#8b949e;font-size:.85em">{r['sector']}</td>
            <td style="color:{sr_c};font-weight:600">{fmt(r['strategy_return'])}</td>
            <td style="color:{bh_c};font-weight:600">{fmt(r['bh_return'])}</td>
            <td style="color:{al_c};font-weight:700">{fmt(r['alpha'])}</td>
            <td style="color:{sh_c}">{r['sharpe']:.2f}</td>
            <td style="color:{rcolor(r['sortino'])}">{r['sortino']:.2f}</td>
            <td style="color:{dd_c}">{fmt(r['max_drawdown'])}</td>
            <td style="color:{wr_c}">{r['win_rate']:.1f}%</td>
            <td>{r['profit_factor']:.2f}x</td>
            <td>{r['trades_count']}</td>
            <td>{r['winning_trades']}W / {r['losing_trades']}L</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IndiaStocks AI — Backtest Report v2 | {run_date}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}}
  .header{{background:linear-gradient(135deg,#161b22,#0d1117);padding:36px 40px;border-bottom:1px solid #30363d}}
  .header h1{{font-size:2em;font-weight:800;color:#58a6ff}}
  .header p{{color:#8b949e;margin-top:4px;font-size:.95em}}
  .container{{max-width:1500px;margin:0 auto;padding:28px 20px}}
  .section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:28px}}
  .section h2{{font-size:1.15em;font-weight:700;color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:18px}}
  .kpi-row{{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:18px}}
  .kpi{{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:16px 22px;flex:1;min-width:130px;text-align:center}}
  .kpi .val{{font-size:1.8em;font-weight:800}}
  .kpi .lbl{{font-size:.78em;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-top:3px}}
  table{{width:100%;border-collapse:collapse;font-size:.85em}}
  th{{background:#0d1117;color:#8b949e;padding:9px 12px;text-align:left;border-bottom:1px solid #30363d;font-weight:600;font-size:.78em;text-transform:uppercase;position:sticky;top:0;z-index:1}}
  td{{padding:8px 12px;border-bottom:1px solid #21262d;vertical-align:middle}}
  tr:hover{{background:#1c2128}}
  .badge{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.78em;font-weight:700}}
  .scroll{{overflow-x:auto}}
  .indicator-table td,.indicator-table th{{padding:7px 14px}}
  .footer{{text-align:center;color:#8b949e;font-size:.82em;padding:20px;border-top:1px solid #30363d;margin-top:10px}}
</style>
</head>
<body>
<div class="header">
  <h1>IndiaStocks AI — Advanced Backtest Report <span style="color:#30363d;font-size:.6em">v2</span></h1>
  <p>Generated: {run_date} &nbsp;|&nbsp; Stocks: {len(results)} NIFTY 100 &nbsp;|&nbsp;
     Engine: 9-indicator scoring (RSI, MACD+Crossover, BB, MA/EMA, ADX, Stochastic, OBV, ROC, Williams %R) &nbsp;|&nbsp;
     Backtest period: 2 years &nbsp;|&nbsp; Transaction costs modelled: 0.35% per round trip</p>
</div>
<div class="container">

<!-- Aggregate KPIs -->
<div class="section">
  <h2>Aggregate Performance — {len(results)} Stocks</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="val">{len(results)}</div><div class="lbl">Stocks Tested</div></div>
    <div class="kpi"><div class="val" style="color:{rcolor(avg_strat)}">{fmt(avg_strat)}</div><div class="lbl">Avg Strategy Return</div></div>
    <div class="kpi"><div class="val" style="color:{rcolor(avg_bh)}">{fmt(avg_bh)}</div><div class="lbl">Avg Buy & Hold</div></div>
    <div class="kpi"><div class="val" style="color:{rcolor(avg_alpha)}">{fmt(avg_alpha)}</div><div class="lbl">Avg Alpha</div></div>
    <div class="kpi"><div class="val" style="color:{rcolor(avg_sharpe)}">{avg_sharpe:.2f}</div><div class="lbl">Avg Sharpe Ratio</div></div>
    <div class="kpi"><div class="val" style="color:{rcolor(avg_wr-50)}">{avg_wr:.1f}%</div><div class="lbl">Avg Win Rate</div></div>
    <div class="kpi"><div class="val" style="color:#FF5252">{avg_dd:.1f}%</div><div class="lbl">Avg Max Drawdown</div></div>
    <div class="kpi"><div class="val" style="color:#00E676">{len(profitable)}</div><div class="lbl">Profitable Stocks</div></div>
    <div class="kpi"><div class="val" style="color:#58a6ff">{len(alpha_positive)}</div><div class="lbl">Beat Buy & Hold</div></div>
  </div>
</div>

<!-- Full Results Table -->
<div class="section">
  <h2>Per-Stock Backtest Results (sorted by Alpha)</h2>
  <div class="scroll">
  <table>
    <thead><tr>
      <th>Symbol</th><th>Sector</th>
      <th>Strategy Ret</th><th>Buy&Hold Ret</th><th>Alpha</th>
      <th>Sharpe</th><th>Sortino</th><th>Max Drawdown</th>
      <th>Win Rate</th><th>Profit Factor</th>
      <th>Trades</th><th>W/L Split</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>

<!-- Methodology -->
<div class="section">
  <h2>Scoring Engine — 9 Indicators Used</h2>
  <table class="indicator-table">
    <thead><tr><th>#</th><th>Indicator</th><th>Formula</th><th>Signal Logic</th><th>Max Score Impact</th></tr></thead>
    <tbody>
      <tr><td>1</td><td><b>RSI (14-day)</b></td><td>100 - 100/(1+AvgGain/AvgLoss)</td><td>&lt;30=Oversold (+15), &lt;40 (+8), &gt;70=Overbought (-12), &gt;60 (-4)</td><td>±15</td></tr>
      <tr><td>2</td><td><b>MACD + Fresh Crossover</b></td><td>EMA12-EMA26, Signal=EMA9, Hist=MACD-Sig</td><td>Crossover (+15), Bullish (+8), Bearish (-7)</td><td>±15</td></tr>
      <tr><td>3</td><td><b>Bollinger Bands (20,2)</b></td><td>MA20 ± 2σ; pos% = (price-lower)/(upper-lower)</td><td>&lt;10% pos (+12), &lt;20% (+7), &gt;90% (-10), &gt;80% (-5)</td><td>±12</td></tr>
      <tr><td>4</td><td><b>MA20/50/200 + EMA9 + Golden/Death Cross</b></td><td>SMA & EMA rolling means</td><td>Above MA200 filter (-15), Golden Cross (+10), Death Cross (-8), EMA9 (+4)</td><td>±22</td></tr>
      <tr><td>5</td><td><b>ADX (14-day)</b></td><td>ADX = EMA(|+DI - -DI|/(+DI+-DI)×100)</td><td>ADX&gt;25 with +DI&gt;-DI (+10), with -DI&gt;+DI (-8)</td><td>±10</td></tr>
      <tr><td>6</td><td><b>Stochastic %K/%D (14,3)</b></td><td>%K = (Close-Low14)/(High14-Low14)×100</td><td>%K&lt;20 turning up (+10), %K&gt;80 turning down (-10)</td><td>±10</td></tr>
      <tr><td>7</td><td><b>OBV Trend</b></td><td>OBV = cumsum(sign(ΔClose) × Volume)</td><td>OBV above 20-day MA (+5), below (-3)</td><td>±5</td></tr>
      <tr><td>8</td><td><b>Rate of Change (10-day)</b></td><td>ROC = (Close - Close[10]) / Close[10] × 100</td><td>&gt;8% (+8), &gt;3% (+4), &lt;-8% (-8), &lt;-3% (-4)</td><td>±8</td></tr>
      <tr><td>9</td><td><b>Williams %R (14-day)</b></td><td>%R = (High14-Close)/(High14-Low14)×-100</td><td>≤-80 oversold (+8), ≥-20 overbought (-6)</td><td>±8</td></tr>
      <tr><td>10</td><td><b>Volume Surge</b></td><td>Ratio = 5-day avg / 20-day avg</td><td>&gt;1.5× (+7), &gt;1.2× (+4), &lt;0.5× (-3)</td><td>±7</td></tr>
    </tbody>
  </table>
</div>

<!-- Risk Management -->
<div class="section">
  <h2>Risk Management in Backtesting</h2>
  <table class="indicator-table">
    <thead><tr><th>Rule</th><th>Implementation</th><th>Purpose</th></tr></thead>
    <tbody>
      <tr><td><b>ATR Trailing Stop</b></td><td>Sell if price ≤ PeakPrice − 2.5 × ATR(14)</td><td>Locks in profits on momentum stocks; adapts to volatility</td></tr>
      <tr><td><b>Fixed Hard Stop</b></td><td>Sell if price ≤ Entry × 0.94 (−6%)</td><td>Catastrophic loss prevention on day-1 breakout failures</td></tr>
      <tr><td><b>Technical Exit</b></td><td>Sell when engine rating drops to "Sell"</td><td>Exits on fundamental/momentum deterioration</td></tr>
      <tr><td><b>Confidence Sizing</b></td><td>Deploy 60–100% capital based on signal confidence</td><td>Bets more on high-confidence signals; reduces risk on weak ones</td></tr>
      <tr><td><b>Transaction Costs</b></td><td>0.25% brokerage + 0.1% STT per side = 0.35% per round trip</td><td>Realistic simulation of real brokerage friction</td></tr>
      <tr><td><b>200-day MA Filter</b></td><td>−15 pts penalty if stock below 200-day MA</td><td>Prevents buying assets in long-term downtrends</td></tr>
    </tbody>
  </table>
</div>

</div>
<div class="footer">IndiaStocks AI Advanced Backtest Engine v2 &nbsp;|&nbsp; {run_date} &nbsp;|&nbsp; Data: Yahoo Finance &nbsp;|&nbsp; NOT financial advice</div>
</body>
</html>"""


def main():
    run_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*65}")
    print(f"IndiaStocks AI — Advanced Backtesting Engine v2")
    print(f"Date: {run_date}  |  Stocks: {len(NIFTY_100_UNIVERSE)}")
    print(f"{'='*65}\n")

    results = []
    for symbol, sector in NIFTY_100_UNIVERSE:
        res = run_backtest(symbol, sector, years="2y")
        if res:
            results.append(res)

    if not results:
        print("No results obtained.")
        return

    # Aggregate stats
    avg_strat  = sum(r["strategy_return"] for r in results) / len(results)
    avg_bh     = sum(r["bh_return"] for r in results) / len(results)
    avg_sharpe = sum(r["sharpe"] for r in results) / len(results)
    avg_wr     = sum(r["win_rate"] for r in results) / len(results)
    profitable = [r for r in results if r["strategy_return"] > 0]
    alpha_pos  = [r for r in results if r["alpha"] > 0]

    print(f"\n{'='*65}")
    print(f"ADVANCED NIFTY 100 BACKTEST RESULTS — ENGINE v2")
    print(f"{'='*65}")
    print(f"Stocks tested          : {len(results)}")
    print(f"Profitable strategies  : {len(profitable)} / {len(results)}")
    print(f"Beat Buy & Hold (alpha): {len(alpha_pos)} / {len(results)}")
    print(f"Avg Strategy Return    : {avg_strat:+.2f}%")
    print(f"Avg Buy & Hold Return  : {avg_bh:+.2f}%")
    print(f"Avg Alpha              : {avg_strat - avg_bh:+.2f}%")
    print(f"Avg Sharpe Ratio       : {avg_sharpe:.3f}")
    print(f"Avg Win Rate           : {avg_wr:.1f}%")
    print(f"{'='*65}\n")
    print("Top 10 Stocks by Alpha:")
    for r in sorted(results, key=lambda x: -x["alpha"])[:10]:
        print(f"  {r['symbol']:<14} Strat: {r['strategy_return']:+6.1f}%  B&H: {r['bh_return']:+6.1f}%  Alpha: {r['alpha']:+7.2f}%  Sharpe: {r['sharpe']:.2f}  WinRate: {r['win_rate']:.0f}%")

    # Save JSON
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_v2_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull JSON saved: {json_path}")

    # Generate HTML report
    html = generate_html_report(results, run_date)
    html_path = os.path.join(REPORT_DIR, f"backtest_v2_{datetime.date.today().isoformat()}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML Report saved: {html_path}")


if __name__ == "__main__":
    main()
