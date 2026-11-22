"""
IndiaStocks AI — Data Science Pipeline
=======================================
Module 2: Exploratory Data Analysis (EDA)
------------------------------------------
Runs statistical EDA on the feature matrix:
  - Descriptive statistics per feature
  - Pearson correlation matrix (features vs. 5-day return)
  - Statistical hypothesis tests (t-test: RSI < 30 → positive return?)
  - Sector-wise return distribution
  - Signal co-occurrence heatmap
  - Generates a self-contained HTML EDA report with embedded charts

Prerequisites: Run ds_pipeline.py first to generate ds_data/feature_matrix.csv
"""

import os, sys, warnings, json, base64
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from io import BytesIO
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from scipy import stats
import datetime

warnings.filterwarnings("ignore")

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "ds_data")
REPORT_DIR= os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

DARK_BG   = "#0d1117"
PANEL_BG  = "#161b22"
GRID_CLR  = "#30363d"
TEXT_CLR  = "#e6edf3"
ACCENT    = "#58a6ff"
GREEN     = "#00E676"
RED       = "#FF5252"
GOLD      = "#FFD740"

def set_dark_style():
    plt.rcParams.update({
        "figure.facecolor":  DARK_BG,
        "axes.facecolor":    PANEL_BG,
        "axes.edgecolor":    GRID_CLR,
        "axes.labelcolor":   TEXT_CLR,
        "xtick.color":       TEXT_CLR,
        "ytick.color":       TEXT_CLR,
        "text.color":        TEXT_CLR,
        "grid.color":        GRID_CLR,
        "grid.linewidth":    0.5,
        "font.family":       "DejaVu Sans",
        "axes.titlecolor":   ACCENT,
        "axes.titlesize":    13,
        "axes.titleweight":  "bold",
    })

def fig_to_b64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# ─── EDA Functions ────────────────────────────────────────────────────────────
def plot_target_distribution(df) -> str:
    set_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle("Target Variable Distribution", fontsize=14, color=ACCENT, y=1.01)

    # Binary target
    vc = df["target_5d"].value_counts().sort_index()
    bars = axes[0].bar(["No Buy (0)", "Buy Signal (1)"], vc.values,
                        color=[RED, GREEN], edgecolor=GRID_CLR, linewidth=0.8, width=0.5)
    for bar, val in zip(bars, vc.values):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                     f"{val:,}\n({val/len(df)*100:.1f}%)", ha="center", va="bottom",
                     color=TEXT_CLR, fontsize=11, fontweight="bold")
    axes[0].set_title("5-Day Return > 1%? (Binary)")
    axes[0].set_ylabel("Count")
    axes[0].grid(axis="y", alpha=0.4)

    # 3-class target
    vc3 = df["target_bin"].value_counts()
    palette = {"buy": GREEN, "hold": GOLD, "sell": RED}
    for label, count in vc3.items():
        axes[1].bar(label.upper(), count, color=palette.get(label, ACCENT),
                    edgecolor=GRID_CLR, linewidth=0.8, width=0.5)
        axes[1].text(list(vc3.keys()).index(label), count + 50,
                     f"{count:,}\n({count/len(df)*100:.1f}%)", ha="center", va="bottom",
                     color=TEXT_CLR, fontsize=11, fontweight="bold")
    axes[1].set_title("5-Day Return Bin (Buy/Hold/Sell)")
    axes[1].set_ylabel("Count")
    axes[1].grid(axis="y", alpha=0.4)

    plt.tight_layout()
    return fig_to_b64(fig)


def plot_indicator_distributions(df) -> str:
    set_dark_style()
    indicators = ["rsi", "macd_histogram", "bb_position_pct", "adx",
                  "stoch_k", "roc_10d", "williams_r", "atr_pct", "volume_ratio"]
    labels = ["RSI (14)", "MACD Histogram", "BB Position %", "ADX (14)",
              "Stoch %K", "ROC (10d) %", "Williams %R", "ATR %", "Volume Ratio"]
    fig, axes = plt.subplots(3, 3, figsize=(15, 11))
    fig.suptitle("Technical Indicator Distributions", fontsize=14, color=ACCENT, y=1.01)

    buy_mask  = df["target_5d"] == 1
    sell_mask = df["target_5d"] == 0

    for ax, col, lbl in zip(axes.flat, indicators, labels):
        ax.hist(df.loc[sell_mask, col].dropna(), bins=40, alpha=0.5,
                color=RED, label="No Buy", density=True)
        ax.hist(df.loc[buy_mask, col].dropna(), bins=40, alpha=0.6,
                color=GREEN, label="Buy", density=True)
        ax.set_title(lbl)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    return fig_to_b64(fig)


def plot_correlation_heatmap(df) -> str:
    set_dark_style()
    feature_cols = [
        "rsi", "macd_histogram", "macd_bullish", "bb_position_pct", "bb_bandwidth",
        "above_ma20", "above_ma50", "above_ma200", "golden_cross",
        "dist_ma20_pct", "dist_ma50_pct", "dist_ma200_pct",
        "adx", "adx_bullish", "stoch_k", "stoch_buy_signal",
        "obv_rising", "roc_10d", "roc_5d", "roc_21d",
        "williams_r", "atr_pct", "volatility_20d", "volume_ratio",
        "bullish_count", "fwd_5d_return"
    ]
    corr = df[feature_cols].corr()
    fig, ax = plt.subplots(figsize=(16, 13))
    cmap = sns.diverging_palette(10, 130, s=80, l=40, as_cmap=True)
    mask = np.zeros_like(corr, dtype=bool)
    mask[np.triu_indices_from(mask)] = True
    sns.heatmap(corr, mask=mask, cmap=cmap, center=0, annot=False,
                linewidths=0.3, linecolor=DARK_BG, ax=ax,
                cbar_kws={"shrink": 0.7})
    ax.set_title("Feature Correlation Matrix (lower triangle)", pad=14)
    ax.tick_params(labelsize=8)
    plt.tight_layout()
    return fig_to_b64(fig)


def plot_feature_vs_return(df) -> str:
    set_dark_style()
    features = ["rsi", "macd_histogram", "bb_position_pct", "adx", "roc_10d", "bullish_count"]
    labels   = ["RSI (14)", "MACD Histogram", "BB Position %", "ADX (14)", "ROC 10d %", "Bullish Count"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle("Feature vs. 5-Day Forward Return", fontsize=14, color=ACCENT, y=1.01)

    for ax, col, lbl in zip(axes.flat, features, labels):
        x = df[col].dropna()
        y = df.loc[x.index, "fwd_5d_return"]
        # Scatter with density colour
        ax.scatter(x, y, alpha=0.07, s=4, color=ACCENT)
        # Trend line
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, p(xs), color=GOLD, linewidth=1.5, label=f"r={np.corrcoef(x,y)[0,1]:.3f}")
        ax.axhline(0, color=GRID_CLR, linewidth=0.8, linestyle="--")
        ax.set_xlabel(lbl, fontsize=9)
        ax.set_ylabel("5d Fwd Return %", fontsize=9)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.25)

    plt.tight_layout()
    return fig_to_b64(fig)


def plot_sector_returns(df) -> str:
    set_dark_style()
    sector_returns = df.groupby("sector")["fwd_5d_return"].agg(["mean", "std", "count"]).reset_index()
    sector_returns = sector_returns[sector_returns["count"] > 50].sort_values("mean")

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [GREEN if v >= 0 else RED for v in sector_returns["mean"]]
    bars = ax.barh(sector_returns["sector"], sector_returns["mean"],
                   xerr=sector_returns["std"] / np.sqrt(sector_returns["count"]),
                   color=colors, alpha=0.85, edgecolor=DARK_BG, linewidth=0.5,
                   error_kw={"ecolor": TEXT_CLR, "capsize": 3, "linewidth": 1})
    ax.axvline(0, color=GRID_CLR, linewidth=1)
    for i, (_, row) in enumerate(sector_returns.iterrows()):
        ax.text(row["mean"] + (0.05 if row["mean"] >= 0 else -0.05),
                i, f"{row['mean']:.2f}%", va="center",
                ha="left" if row["mean"] >= 0 else "right",
                color=TEXT_CLR, fontsize=9)
    ax.set_title("Avg 5-Day Forward Return by Sector (±SEM)", pad=12)
    ax.set_xlabel("Mean 5-Day Return (%)")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    return fig_to_b64(fig)


def plot_rsi_regime_returns(df) -> str:
    set_dark_style()
    bins   = [0, 20, 30, 40, 50, 60, 70, 80, 100]
    labels = ["0-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-100"]
    df2    = df.copy()
    df2["rsi_bin"] = pd.cut(df2["rsi"], bins=bins, labels=labels)
    grouped = df2.groupby("rsi_bin", observed=True)["fwd_5d_return"].agg(["mean","sem","count"])

    fig, ax = plt.subplots(figsize=(11, 5))
    colors = [GREEN if v >= 0 else RED for v in grouped["mean"]]
    ax.bar(grouped.index.astype(str), grouped["mean"],
           yerr=grouped["sem"], color=colors, alpha=0.85,
           edgecolor=DARK_BG, linewidth=0.5,
           error_kw={"ecolor": TEXT_CLR, "capsize": 4})
    ax.axhline(0, color=GRID_CLR)
    for i, (idx, row) in enumerate(grouped.iterrows()):
        ax.text(i, row["mean"] + row["sem"] + 0.05, f"n={int(row['count'])}", ha="center",
                fontsize=8, color=TEXT_CLR)
    ax.set_title("Avg 5-Day Return by RSI Zone — Does RSI < 30 predict gains?")
    ax.set_xlabel("RSI Bucket")
    ax.set_ylabel("Mean 5-Day Return (%)")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    return fig_to_b64(fig)


def plot_bullish_count_returns(df) -> str:
    set_dark_style()
    grouped = df.groupby("bullish_count")["fwd_5d_return"].agg(["mean","sem","count"])
    fig, ax = plt.subplots(figsize=(10, 5))
    colors  = [GREEN if v >= 0 else RED for v in grouped["mean"]]
    ax.bar(grouped.index.astype(str), grouped["mean"],
           yerr=grouped["sem"], color=colors, alpha=0.85,
           edgecolor=DARK_BG, linewidth=0.5,
           error_kw={"ecolor": TEXT_CLR, "capsize": 4})
    ax.axhline(0, color=GRID_CLR)
    for i, (idx, row) in enumerate(grouped.iterrows()):
        ax.text(i, row["mean"] + row["sem"] + 0.05, f"n={int(row['count'])}", ha="center",
                fontsize=9, color=TEXT_CLR)
    ax.set_title("Avg 5-Day Return vs. Number of Bullish Indicator Signals Firing")
    ax.set_xlabel("Count of Bullish Signals (0 = all bearish, 9 = all bullish)")
    ax.set_ylabel("Mean 5-Day Return (%)")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    return fig_to_b64(fig)


# ─── Hypothesis Testing ───────────────────────────────────────────────────────
def run_hypothesis_tests(df) -> list[dict]:
    """T-tests: Does each binary signal significantly predict positive returns?"""
    tests = [
        ("RSI < 30 (Oversold)",        df["rsi_oversold"] == 1),
        ("MACD Bullish Cross",          df["macd_crossover"] == 1),
        ("BB Below Lower Band",         df["bb_oversold"] == 1),
        ("Above MA200",                 df["above_ma200"] == 1),
        ("Golden Cross (MA50>MA200)",   df["golden_cross"] == 1),
        ("ADX Strong Uptrend",          df["adx_bullish"] == 1),
        ("Stochastic Buy Signal",       df["stoch_buy_signal"] == 1),
        ("OBV Rising",                  df["obv_rising"] == 1),
        ("Williams %R Oversold",        df["williams_oversold"] == 1),
        ("Volume Surge (>1.5x)",        df["volume_surge"] == 1),
        ("5+ Bullish Signals",          df["bullish_count"] >= 5),
        ("All 3 MAs Bullish",           (df["above_ma20"]+df["above_ma50"]+df["above_ma200"]) == 3),
    ]
    results = []
    for label, mask in tests:
        group_signal = df.loc[mask,  "fwd_5d_return"].dropna()
        group_rest   = df.loc[~mask, "fwd_5d_return"].dropna()
        if len(group_signal) < 20:
            continue
        t_stat, p_val = stats.ttest_ind(group_signal, group_rest, equal_var=False)
        significant   = p_val < 0.05
        results.append({
            "Signal":     label,
            "N (Signal)": len(group_signal),
            "N (Rest)":   len(group_rest),
            "Mean Ret (Signal) %": round(float(group_signal.mean()), 3),
            "Mean Ret (Rest) %":   round(float(group_rest.mean()),   3),
            "Diff %":   round(float(group_signal.mean() - group_rest.mean()), 3),
            "T-Stat":   round(t_stat, 3),
            "P-Value":  round(p_val, 4),
            "Significant": "✅ Yes" if significant else "❌ No",
        })
    return results


# ─── HTML Report Generator ────────────────────────────────────────────────────
def build_html(df, charts: dict, h_tests: list, desc_stats: pd.DataFrame) -> str:
    total_rows = len(df)
    buy_rate   = df["target_5d"].mean() * 100
    run_date   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Descriptive stats table
    key_features = ["rsi","macd_histogram","bb_position_pct","adx","stoch_k",
                    "roc_10d","williams_r","atr_pct","volume_ratio","bullish_count"]
    ds = desc_stats.loc[key_features, ["mean","std","min","25%","50%","75%","max"]].round(3)
    stat_rows = ""
    for feat, row in ds.iterrows():
        stat_rows += f"<tr><td><b>{feat}</b></td>"
        for v in row.values:
            stat_rows += f"<td>{v:.3f}</td>"
        stat_rows += "</tr>"

    # Hypothesis test table
    h_rows = ""
    for h in h_tests:
        sig_color = "#00E676" if "Yes" in h["Significant"] else "#FF5252"
        diff_color = "#00E676" if h["Diff %"] > 0 else "#FF5252"
        h_rows += f"""<tr>
            <td><b>{h['Signal']}</b></td>
            <td>{h['N (Signal)']:,}</td>
            <td style="color:{('#00E676' if h['Mean Ret (Signal) %'] >= 0 else '#FF5252')};font-weight:600">{h['Mean Ret (Signal) %']:+.3f}%</td>
            <td>{h['Mean Ret (Rest) %']:+.3f}%</td>
            <td style="color:{diff_color};font-weight:700">{h['Diff %']:+.3f}%</td>
            <td>{h['T-Stat']}</td>
            <td>{h['P-Value']}</td>
            <td style="color:{sig_color};font-weight:700">{h['Significant']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IndiaStocks AI — EDA Report | {run_date}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}}
  .header{{background:linear-gradient(135deg,#161b22,#0d1117);padding:34px 40px;border-bottom:1px solid #30363d}}
  .header h1{{font-size:1.9em;font-weight:800;color:#58a6ff}}
  .header p{{color:#8b949e;margin-top:4px}}
  .container{{max-width:1400px;margin:0 auto;padding:28px 20px}}
  .section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:28px}}
  .section h2{{font-size:1.15em;font-weight:700;color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:18px}}
  .kpi-row{{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:18px}}
  .kpi{{background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:16px 22px;flex:1;min-width:130px;text-align:center}}
  .kpi .val{{font-size:1.8em;font-weight:800;color:#e6edf3}}
  .kpi .lbl{{font-size:.78em;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-top:3px}}
  table{{width:100%;border-collapse:collapse;font-size:.85em}}
  th{{background:#0d1117;color:#8b949e;padding:9px 12px;text-align:left;border-bottom:1px solid #30363d;font-weight:600;font-size:.78em;text-transform:uppercase}}
  td{{padding:8px 12px;border-bottom:1px solid #21262d;vertical-align:middle}}
  tr:hover{{background:#1c2128}}
  img{{width:100%;border-radius:8px;border:1px solid #30363d;margin-top:8px}}
  .scroll{{overflow-x:auto}}
  .footer{{text-align:center;color:#8b949e;font-size:.82em;padding:20px;border-top:1px solid #30363d}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 IndiaStocks AI — Exploratory Data Analysis (EDA)</h1>
  <p>Generated: {run_date} &nbsp;|&nbsp; Observations: {total_rows:,} &nbsp;|&nbsp;
     Universe: {df['symbol'].nunique()} NIFTY 100 stocks &nbsp;|&nbsp;
     Features: {len(df.columns)} &nbsp;|&nbsp; Target: 5-day forward return &gt; 1%</p>
</div>
<div class="container">

<!-- Overview KPIs -->
<div class="section">
  <h2>Dataset Overview</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="val">{total_rows:,}</div><div class="lbl">Total Observations</div></div>
    <div class="kpi"><div class="val">{df['symbol'].nunique()}</div><div class="lbl">Stocks</div></div>
    <div class="kpi"><div class="val">{df['sector'].nunique()}</div><div class="lbl">Sectors</div></div>
    <div class="kpi"><div class="val">{len(df.columns)}</div><div class="lbl">Features</div></div>
    <div class="kpi"><div class="val" style="color:#00E676">{buy_rate:.1f}%</div><div class="lbl">Buy Signal Rate</div></div>
    <div class="kpi"><div class="val">{df['date'].min()} – {df['date'].max()}</div><div class="lbl">Date Range</div></div>
  </div>
</div>

<!-- Target Distribution -->
<div class="section">
  <h2>Target Variable Distribution</h2>
  <img src="data:image/png;base64,{charts['target_dist']}" alt="Target Distribution">
</div>

<!-- Indicator Distributions -->
<div class="section">
  <h2>Technical Indicator Distributions (Buy vs. No-Buy days)</h2>
  <img src="data:image/png;base64,{charts['indicator_dist']}" alt="Indicator Distributions">
</div>

<!-- Feature vs Return scatter -->
<div class="section">
  <h2>Feature vs. 5-Day Forward Return</h2>
  <img src="data:image/png;base64,{charts['scatter']}" alt="Feature vs Return Scatterplots">
</div>

<!-- RSI Regime -->
<div class="section">
  <h2>RSI Zone Analysis — Does Oversold RSI Predict Positive Returns?</h2>
  <img src="data:image/png;base64,{charts['rsi_regime']}" alt="RSI Zone Returns">
</div>

<!-- Bullish count -->
<div class="section">
  <h2>Multi-Signal Confluence — More Bullish Signals = Higher Returns?</h2>
  <img src="data:image/png;base64,{charts['bullish_count']}" alt="Bullish Count Returns">
</div>

<!-- Sector returns -->
<div class="section">
  <h2>Sector-Wise Average 5-Day Return</h2>
  <img src="data:image/png;base64,{charts['sector']}" alt="Sector Returns">
</div>

<!-- Correlation heatmap -->
<div class="section">
  <h2>Feature Correlation Matrix</h2>
  <img src="data:image/png;base64,{charts['corr']}" alt="Correlation Heatmap">
</div>

<!-- Hypothesis tests -->
<div class="section">
  <h2>Statistical Hypothesis Tests (Welch T-Test, α=0.05)</h2>
  <p style="color:#8b949e;font-size:.85em;margin-bottom:12px">
    <b>H₀</b>: Mean 5-day return when signal fires = mean return when it doesn't fire. &nbsp;
    <b>H₁</b>: Signal days have significantly different returns. &nbsp;
    Significant = P-value &lt; 0.05 → reject H₀.
  </p>
  <div class="scroll">
  <table>
    <thead><tr>
      <th>Signal</th><th>N (Signal)</th>
      <th>Mean Ret (Signal)</th><th>Mean Ret (Rest)</th>
      <th>Difference</th><th>T-Stat</th><th>P-Value</th><th>Significant?</th>
    </tr></thead>
    <tbody>{h_rows}</tbody>
  </table>
  </div>
</div>

<!-- Descriptive stats -->
<div class="section">
  <h2>Descriptive Statistics — Key Features</h2>
  <div class="scroll">
  <table>
    <thead><tr><th>Feature</th><th>Mean</th><th>Std</th><th>Min</th><th>25%</th><th>Median</th><th>75%</th><th>Max</th></tr></thead>
    <tbody>{stat_rows}</tbody>
  </table>
  </div>
</div>

</div>
<div class="footer">
  IndiaStocks AI EDA Report &nbsp;|&nbsp; {run_date} &nbsp;|&nbsp;
  Features engineered from Yahoo Finance OHLCV data &nbsp;|&nbsp; NOT financial advice
</div>
</body>
</html>"""


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    csv_path = os.path.join(DATA_DIR, "feature_matrix.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: Feature matrix not found at {csv_path}")
        print("Run ds_pipeline.py first.")
        return

    print(f"\n{'='*65}")
    print("IndiaStocks AI — EDA Module")
    print(f"{'='*65}\n")

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows × {len(df.columns)} columns")
    print(f"Stocks: {sorted(df['symbol'].unique())}")

    # Generate charts
    print("\nGenerating charts...")
    charts = {
        "target_dist":     plot_target_distribution(df),
        "indicator_dist":  plot_indicator_distributions(df),
        "corr":            plot_correlation_heatmap(df),
        "scatter":         plot_feature_vs_return(df),
        "sector":          plot_sector_returns(df),
        "rsi_regime":      plot_rsi_regime_returns(df),
        "bullish_count":   plot_bullish_count_returns(df),
    }
    print(f"Generated {len(charts)} chart panels")

    # Hypothesis tests
    print("\nRunning hypothesis tests...")
    h_tests = run_hypothesis_tests(df)
    print(f"Completed {len(h_tests)} hypothesis tests")
    for h in h_tests:
        marker = "✅" if "Yes" in h["Significant"] else "  "
        print(f"  {marker} {h['Signal']:<40} Diff: {h['Diff %']:+.3f}%  p={h['P-Value']:.4f}")

    # Descriptive stats
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    desc_stats = df[num_cols].describe().T

    # Build & save report
    html = build_html(df, charts, h_tests, desc_stats)
    out_path = os.path.join(REPORT_DIR, f"eda_report_{datetime.date.today()}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nEDA Report saved: {out_path}")
    print("Next → run: python ds_ml_model.py")


if __name__ == "__main__":
    main()
