"""
IndiaStocks AI — Data Science Pipeline
=======================================
Module 1: Data Collection & Feature Engineering
------------------------------------------------
Fetches 2 years of OHLCV data for NIFTY 100 stocks,
engineers 30+ ML-ready features from all 9 technical
indicators, and saves a clean feature matrix as CSV.

Run order:
  1. ds_pipeline.py         ← this file (data + features)
  2. ds_eda.py              ← EDA, correlations, hypothesis tests
  3. ds_ml_model.py         ← ML models, feature importance, signals
"""

import os, sys, warnings
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommender import (compute_rsi, compute_macd, compute_bollinger,
                          compute_moving_averages, compute_adx,
                          compute_stochastic, compute_obv_trend,
                          compute_roc, compute_williams_r)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "ds_data")
os.makedirs(DATA_DIR, exist_ok=True)

NIFTY_100 = [
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
    ("BEL","Defence"),           ("HAL","Defence"),
]

# ─── Feature Engineering ─────────────────────────────────────────────────────
def engineer_features(hist: pd.DataFrame, symbol: str, sector: str) -> pd.DataFrame:
    """
    Given OHLCV DataFrame, generate a row per trading day with
    30+ ML-ready features. The ML target is:
      target_5d:  Will 5-day forward return exceed +1%?  (1 = Yes, 0 = No)
      target_bin: One-of-three: 'buy' / 'hold' / 'sell'  based on 5d return
    """
    closes  = hist["Close"]
    highs   = hist["High"]
    lows    = hist["Low"]
    volumes = hist["Volume"]
    opens   = hist["Open"]

    rows = []
    min_window = 55  # need at least 55 days for indicators to warm up

    for i in range(min_window, len(closes) - 6):  # -6 leaves room for 5d forward return
        c = closes.iloc[:i+1]
        h = highs.iloc[:i+1]
        l = lows.iloc[:i+1]
        v = volumes.iloc[:i+1]

        # ── Price-based features ─────────────────────────────────────────
        price      = float(closes.iloc[i])
        prev_close = float(closes.iloc[i-1])
        day_return = (price - prev_close) / prev_close * 100

        # ── Technical Indicator Features ─────────────────────────────────
        rsi   = compute_rsi(c)
        macd  = compute_macd(c)
        bb    = compute_bollinger(c)
        mas   = compute_moving_averages(c)
        adx   = compute_adx(h, l, c)
        stoch = compute_stochastic(h, l, c)
        obv   = compute_obv_trend(c, v)
        roc   = compute_roc(c, 10)
        wr    = compute_williams_r(h, l, c)

        # ── Volatility features ───────────────────────────────────────────
        tr     = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr14  = float(tr.rolling(14).mean().iloc[-1]) if not tr.empty else price * 0.01
        atr_pct = atr14 / price * 100  # ATR as % of price (normalized)

        returns_20 = c.pct_change().tail(20).dropna()
        volatility_20d = float(returns_20.std() * np.sqrt(252) * 100) if len(returns_20) > 2 else 20.0

        # ── Volume features ───────────────────────────────────────────────
        vol_5d   = float(v.tail(5).mean())
        vol_20d  = float(v.tail(20).mean())
        vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1.0

        # ── Price momentum features ────────────────────────────────────────
        roc_5d  = compute_roc(c, 5)
        roc_21d = compute_roc(c, 21)

        # ── Distance-from-MA features (normalized) ─────────────────────────
        ma20  = mas["ma20"]
        ma50  = mas["ma50"]
        ma200 = mas["ma200"]
        dist_ma20  = (price - ma20)  / ma20  * 100
        dist_ma50  = (price - ma50)  / ma50  * 100
        dist_ma200 = (price - ma200) / ma200 * 100

        # ── Bollinger Band squeeze ─────────────────────────────────────────
        bb_squeeze = bb["bandwidth"] < 10  # Tight band = upcoming breakout

        # ── Forward return (TARGET) ────────────────────────────────────────
        fwd_5d_price  = float(closes.iloc[i + 5])
        fwd_5d_return = (fwd_5d_price - price) / price * 100

        target_5d = 1 if fwd_5d_return >= 1.0 else 0
        if fwd_5d_return >= 1.5:
            target_bin = "buy"
        elif fwd_5d_return <= -1.0:
            target_bin = "sell"
        else:
            target_bin = "hold"

        rows.append({
            # ── Metadata ──────────────────────────────────────────────────
            "date":        hist.index[i].strftime("%Y-%m-%d"),
            "symbol":      symbol,
            "sector":      sector,
            "price":       round(price, 2),
            "day_return":  round(day_return, 3),

            # ── RSI features ──────────────────────────────────────────────
            "rsi":             rsi,
            "rsi_oversold":    int(rsi < 30),
            "rsi_overbought":  int(rsi > 70),
            "rsi_zone":        "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",

            # ── MACD features ─────────────────────────────────────────────
            "macd_histogram":  macd["histogram"],
            "macd_bullish":    int(macd["bullish"]),
            "macd_crossover":  int(macd["crossover"]),

            # ── Bollinger Band features ───────────────────────────────────
            "bb_position_pct": bb["position_pct"],
            "bb_bandwidth":    bb["bandwidth"],
            "bb_squeeze":      int(bb_squeeze),
            "bb_oversold":     int(bb["position_pct"] < 20),
            "bb_overbought":   int(bb["position_pct"] > 80),

            # ── Moving average features ────────────────────────────────────
            "above_ma20":     int(mas["above_ma20"]),
            "above_ma50":     int(mas["above_ma50"]),
            "above_ma200":    int(mas["above_ma200"]),
            "golden_cross":   int(mas["golden_cross"]),
            "dist_ma20_pct":  round(dist_ma20, 3),
            "dist_ma50_pct":  round(dist_ma50, 3),
            "dist_ma200_pct": round(dist_ma200, 3),

            # ── ADX features ──────────────────────────────────────────────
            "adx":             adx["adx"],
            "adx_strong":      int(adx["trend_strong"]),
            "adx_bullish":     int(adx["trend_strong"] and adx["plus_di"] > adx["minus_di"]),
            "plus_di":         adx["plus_di"],
            "minus_di":        adx["minus_di"],

            # ── Stochastic features ───────────────────────────────────────
            "stoch_k":         stoch["k"],
            "stoch_d":         stoch["d"],
            "stoch_oversold":  int(stoch["oversold"]),
            "stoch_overbought":int(stoch["overbought"]),
            "stoch_buy_signal":int(stoch["oversold"] and stoch["k"] > stoch["d"]),

            # ── OBV features ──────────────────────────────────────────────
            "obv_rising":      int(obv["obv_rising"]),

            # ── Momentum features ─────────────────────────────────────────
            "roc_10d":         roc,
            "roc_5d":          roc_5d,
            "roc_21d":         roc_21d,
            "williams_r":      wr,
            "williams_oversold": int(wr <= -80),

            # ── Volatility features ───────────────────────────────────────
            "atr_pct":         round(atr_pct, 3),
            "volatility_20d":  round(volatility_20d, 2),

            # ── Volume features ───────────────────────────────────────────
            "volume_ratio":    round(vol_ratio, 3),
            "volume_surge":    int(vol_ratio > 1.5),

            # ── Composite signal counts ───────────────────────────────────
            "bullish_count":   sum([
                int(rsi < 40), int(macd["bullish"]), int(bb["position_pct"] < 30),
                int(mas["above_ma200"]), int(adx["trend_strong"] and adx["plus_di"] > adx["minus_di"]),
                int(stoch["oversold"]), int(obv["obv_rising"]), int(roc > 2), int(wr <= -60)
            ]),

            # ── Targets ───────────────────────────────────────────────────
            "fwd_5d_return":   round(fwd_5d_return, 3),
            "target_5d":       target_5d,
            "target_bin":      target_bin,
        })

    return pd.DataFrame(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*65}")
    print("IndiaStocks AI — Data Science Pipeline: Feature Engineering")
    print(f"{'='*65}\n")

    all_frames = []

    for symbol, sector in NIFTY_100:
        print(f"  [{symbol}] Downloading OHLCV (2y)...")
        try:
            t    = yf.Ticker(f"{symbol}.NS")
            hist = t.history(period="2y")
            if hist.empty or len(hist) < 60:
                print(f"  [{symbol}] Insufficient data, skipping.")
                continue
            df = engineer_features(hist, symbol, sector)
            if not df.empty:
                all_frames.append(df)
                print(f"  [{symbol}] -> {len(df)} rows, {len(df.columns)} features")
        except Exception as e:
            print(f"  [{symbol}] ERROR: {e}")

    if not all_frames:
        print("No data collected.")
        return

    master_df = pd.concat(all_frames, ignore_index=True)
    master_df.dropna(inplace=True)

    # Save
    csv_path = os.path.join(DATA_DIR, "feature_matrix.csv")
    master_df.to_csv(csv_path, index=False)

    print(f"\n{'='*65}")
    print(f"Feature matrix saved: {csv_path}")
    print(f"Shape: {master_df.shape[0]:,} rows × {master_df.shape[1]} columns")
    print(f"Stocks included: {master_df['symbol'].nunique()}")
    print(f"Date range: {master_df['date'].min()} -> {master_df['date'].max()}")
    print(f"\nTarget distribution (5-day, 1% threshold):")
    vc = master_df["target_5d"].value_counts()
    print(f"  Buy signals (1): {vc.get(1, 0):,}  ({vc.get(1, 0)/len(master_df)*100:.1f}%)")
    print(f"  No-buy   (0): {vc.get(0, 0):,}  ({vc.get(0, 0)/len(master_df)*100:.1f}%)")
    print(f"\nBin target distribution:")
    for lbl, cnt in master_df["target_bin"].value_counts().items():
        print(f"  {lbl:6}: {cnt:,} ({cnt/len(master_df)*100:.1f}%)")
    print(f"{'='*65}\n")
    print("Next -> run: python ds_eda.py")


if __name__ == "__main__":
    main()
