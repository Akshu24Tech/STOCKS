"""
IndiaStocks AI — Data Science Pipeline
=======================================
Module 3: Machine Learning Models
-----------------------------------
Trains and evaluates multiple ML classifiers to predict
whether a stock will gain > 1% over the next 5 days.

Models trained:
  1. Random Forest (primary)
  2. Gradient Boosting (XGBoost-style via sklearn)
  3. Logistic Regression (baseline)
  4. Support Vector Machine (RBF kernel)

Outputs:
  - Feature importance ranking
  - Cross-validation accuracy / AUC
  - Confusion matrix for each model
  - Precision / Recall / F1 per signal class
  - Best-model signal predictions for today
  - Sector-wise model accuracy breakdown
  - HTML report with all charts and tables

Prerequisites: Run ds_pipeline.py first.
"""

import os, sys, warnings, datetime, base64
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
import seaborn as sns

from sklearn.ensemble import (RandomForestClassifier, GradientBoostingClassifier,
                              HistGradientBoostingClassifier)
from sklearn.linear_model  import LogisticRegression
from sklearn.preprocessing  import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics        import (classification_report, confusion_matrix,
                                     roc_auc_score, precision_recall_fscore_support)
from sklearn.pipeline       import Pipeline
from sklearn.inspection     import permutation_importance
import joblib

warnings.filterwarnings("ignore")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "ds_data")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
MODEL_DIR  = os.path.join(BASE_DIR, "ds_data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

DARK_BG = "#0d1117"; PANEL_BG = "#161b22"; GRID_CLR = "#30363d"
TEXT_CLR = "#e6edf3"; ACCENT = "#58a6ff"; GREEN = "#00E676"; RED = "#FF5252"; GOLD = "#FFD740"

FEATURE_COLS = [
    "rsi", "macd_histogram", "macd_bullish", "macd_crossover",
    "bb_position_pct", "bb_bandwidth", "bb_squeeze", "bb_oversold",
    "above_ma20", "above_ma50", "above_ma200", "golden_cross",
    "dist_ma20_pct", "dist_ma50_pct", "dist_ma200_pct",
    "adx", "adx_strong", "adx_bullish", "plus_di", "minus_di",
    "stoch_k", "stoch_d", "stoch_oversold", "stoch_buy_signal",
    "obv_rising", "roc_10d", "roc_5d", "roc_21d",
    "williams_r", "williams_oversold",
    "atr_pct", "volatility_20d", "volume_ratio", "volume_surge",
    "bullish_count"
]
TARGET = "target_5d"

def set_dark_style():
    plt.rcParams.update({
        "figure.facecolor": DARK_BG, "axes.facecolor": PANEL_BG,
        "axes.edgecolor": GRID_CLR, "axes.labelcolor": TEXT_CLR,
        "xtick.color": TEXT_CLR, "ytick.color": TEXT_CLR,
        "text.color": TEXT_CLR, "grid.color": GRID_CLR,
        "grid.linewidth": 0.5, "axes.titlecolor": ACCENT,
        "axes.titlesize": 12, "axes.titleweight": "bold",
    })

def fig_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=DARK_BG)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# ─── Feature importance chart ─────────────────────────────────────────────────
def plot_feature_importance(rf_model, feature_names) -> str:
    set_dark_style()
    imp = pd.Series(rf_model.feature_importances_, index=feature_names).sort_values()
    top = imp.tail(20)

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = [GREEN if v > imp.median() else ACCENT for v in top.values]
    ax.barh(top.index, top.values, color=colors, edgecolor=DARK_BG, linewidth=0.4)
    ax.set_title("Random Forest — Top 20 Feature Importances (Gini)")
    ax.set_xlabel("Importance Score")
    ax.grid(axis="x", alpha=0.3)
    for i, v in enumerate(top.values):
        ax.text(v + 0.0005, i, f"{v:.4f}", va="center", fontsize=8, color=TEXT_CLR)
    plt.tight_layout()
    return fig_b64(fig)


def plot_confusion_matrix(y_true, y_pred, model_name) -> str:
    set_dark_style()
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    cmap = sns.diverging_palette(10, 130, s=70, l=40, as_cmap=True)
    sns.heatmap(cm, annot=True, fmt="d", cmap=cmap, ax=ax,
                xticklabels=["No Buy", "Buy"], yticklabels=["No Buy", "Buy"],
                linewidths=0.5, linecolor=DARK_BG,
                annot_kws={"size": 14, "weight": "bold", "color": TEXT_CLR},
                cbar_kws={"shrink": 0.7})
    ax.set_title(f"{model_name} — Confusion Matrix")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    plt.tight_layout()
    return fig_b64(fig)


def plot_cv_scores(cv_results: dict) -> str:
    set_dark_style()
    models = list(cv_results.keys())
    metrics = {"Accuracy": [], "ROC-AUC": [], "F1 (Buy)": []}

    for m in models:
        metrics["Accuracy"].append(cv_results[m]["test_accuracy"].mean())
        metrics["ROC-AUC"].append(cv_results[m]["test_roc_auc"].mean())
        metrics["F1 (Buy)"].append(cv_results[m]["test_f1"].mean())

    x  = np.arange(len(models))
    w  = 0.25
    fig, ax = plt.subplots(figsize=(11, 5.5))
    colors = [ACCENT, GREEN, GOLD]
    for i, (metric, vals) in enumerate(metrics.items()):
        bars = ax.bar(x + i*w, vals, w, label=metric, color=colors[i],
                      alpha=0.85, edgecolor=DARK_BG, linewidth=0.5)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.005,
                    f"{v:.3f}", ha="center", va="bottom", fontsize=8, color=TEXT_CLR)
    ax.set_xticks(x + w)
    ax.set_xticklabels(models, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.set_title("Cross-Validation Performance Comparison (5-Fold StratifiedKFold)")
    ax.set_ylabel("Score")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.axhline(0.5, color=RED, linewidth=0.8, linestyle="--", label="Random Baseline")
    plt.tight_layout()
    return fig_b64(fig)


def plot_roc_curve_all(models_preds: dict, y_true) -> str:
    from sklearn.metrics import roc_curve, auc
    set_dark_style()
    fig, ax = plt.subplots(figsize=(8, 6))
    palette = [ACCENT, GREEN, GOLD, RED]
    for i, (name, proba) in enumerate(models_preds.items()):
        fpr, tpr, _ = roc_curve(y_true, proba)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=palette[i], linewidth=2,
                label=f"{name} (AUC = {roc_auc:.3f})")
    ax.plot([0,1],[0,1], color=GRID_CLR, linewidth=1.2, linestyle="--", label="Random")
    ax.set_title("ROC Curves — All Models")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig_b64(fig)


def plot_sector_accuracy(y_true, y_pred, sectors) -> str:
    set_dark_style()
    df_eval = pd.DataFrame({"actual": y_true, "pred": y_pred, "sector": sectors})
    sector_acc = df_eval.groupby("sector").apply(
        lambda x: (x["actual"] == x["pred"]).mean()
    ).sort_values()

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [GREEN if v >= 0.55 else (GOLD if v >= 0.50 else RED) for v in sector_acc.values]
    ax.barh(sector_acc.index, sector_acc.values, color=colors, edgecolor=DARK_BG)
    ax.axvline(0.5, color=RED, linewidth=1.2, linestyle="--", label="Random Baseline (50%)")
    ax.axvline(sector_acc.mean(), color=GOLD, linewidth=1.2, linestyle="--",
               label=f"Overall Avg ({sector_acc.mean():.1%})")
    for i, v in enumerate(sector_acc.values):
        ax.text(v+0.005, i, f"{v:.1%}", va="center", fontsize=9, color=TEXT_CLR)
    ax.set_title("Random Forest Accuracy by Sector")
    ax.set_xlabel("Accuracy")
    ax.legend(fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    return fig_b64(fig)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    csv_path = os.path.join(DATA_DIR, "feature_matrix.csv")
    if not os.path.exists(csv_path):
        print("ERROR: feature_matrix.csv not found. Run ds_pipeline.py first.")
        return

    print(f"\n{'='*65}")
    print("IndiaStocks AI — ML Model Training Module")
    print(f"{'='*65}\n")

    df = pd.read_csv(csv_path)
    df.dropna(subset=FEATURE_COLS + [TARGET], inplace=True)
    X = df[FEATURE_COLS].values
    y = df[TARGET].values
    sectors = df["sector"].values

    print(f"Dataset: {len(df):,} rows | Features: {len(FEATURE_COLS)} | Class balance: {y.mean():.1%} positive")

    # ── Define Models ──────────────────────────────────────────────────────
    models = {
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=200, max_depth=8,
                                           min_samples_leaf=20, random_state=42, n_jobs=-1))
        ]),
        "Gradient Boost": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=150, max_depth=4,
                                                learning_rate=0.05, random_state=42))
        ]),
        "Logistic Reg": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, C=0.5, random_state=42))
        ]),
        "Hist Gradient Boost": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", HistGradientBoostingClassifier(max_iter=150, max_depth=5, random_state=42))
        ]),
    }

    # ── Cross-Validation ──────────────────────────────────────────────────
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {"accuracy": "accuracy", "roc_auc": "roc_auc", "f1": "f1"}
    cv_results = {}
    print("\nRunning 5-fold cross-validation...")
    for name, model in models.items():
        result = cross_validate(model, X, y, cv=cv, scoring=scoring,
                                return_train_score=False, n_jobs=-1)
        cv_results[name] = result
        print(f"  {name:<20} Acc: {result['test_accuracy'].mean():.3f}+/-{result['test_accuracy'].std():.3f} "
              f"AUC: {result['test_roc_auc'].mean():.3f} F1: {result['test_f1'].mean():.3f}")

    # ── Train full models for feature importance & confusion matrices ───────
    print("\nTraining final models on full dataset...")
    trained = {}
    for name, model in models.items():
        model.fit(X, y)
        trained[name] = model
    joblib.dump(trained["Random Forest"], os.path.join(MODEL_DIR, "random_forest.pkl"))
    print("  Random Forest model saved to ds_data/models/random_forest.pkl")

    # ── Predictions & metrics ─────────────────────────────────────────────
    print("\nClassification Reports:")
    all_preds  = {}
    all_probas = {}
    for name, model in trained.items():
        y_pred  = model.predict(X)
        y_proba = model.predict_proba(X)[:, 1]
        all_preds[name]  = y_pred
        all_probas[name] = y_proba
        print(f"\n  [{name}]")
        rep = classification_report(y, y_pred, target_names=["No Buy", "Buy"])
        for line in rep.split("\n"):
            print(f"    {line}")

    # ── Feature Importance ─────────────────────────────────────────────────
    rf_clf = trained["Random Forest"].named_steps["clf"]

    # ── Generate Charts ────────────────────────────────────────────────────
    print("\nGenerating charts...")
    charts = {
        "cv_scores":    plot_cv_scores(cv_results),
        "feat_imp":     plot_feature_importance(rf_clf, FEATURE_COLS),
        "roc":          plot_roc_curve_all(all_probas, y),
        "cm_rf":        plot_confusion_matrix(y, all_preds["Random Forest"], "Random Forest"),
        "cm_gb":        plot_confusion_matrix(y, all_preds["Gradient Boost"], "Gradient Boost"),
        "sector_acc":   plot_sector_accuracy(y, all_preds["Random Forest"], sectors),
    }

    # ── Per-model summary table ────────────────────────────────────────────
    model_rows = ""
    for name, result in cv_results.items():
        acc  = result["test_accuracy"].mean()
        auc  = result["test_roc_auc"].mean()
        f1   = result["test_f1"].mean()
        acc_c = GREEN if acc >= 0.57 else (GOLD if acc >= 0.52 else RED)
        auc_c = GREEN if auc >= 0.60 else (GOLD if auc >= 0.55 else RED)
        model_rows += f"""<tr>
            <td><b>{name}</b></td>
            <td style="color:{acc_c};font-weight:700">{acc:.3f}</td>
            <td>{result['test_accuracy'].std():.3f}</td>
            <td style="color:{auc_c};font-weight:700">{auc:.3f}</td>
            <td>{result['test_roc_auc'].std():.3f}</td>
            <td>{f1:.3f}</td>
        </tr>"""

    # ── Top feature importances table ─────────────────────────────────────
    imp_series = pd.Series(rf_clf.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
    feat_rows = ""
    for rank, (feat, imp) in enumerate(imp_series.head(15).items(), 1):
        bar_w = int(imp / imp_series.max() * 120)
        feat_rows += f"""<tr>
            <td>#{rank}</td><td><b>{feat}</b></td>
            <td><div style="background:#58a6ff;height:10px;width:{bar_w}px;border-radius:4px;display:inline-block"></div></td>
            <td>{imp:.5f}</td>
        </tr>"""

    run_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IndiaStocks AI — ML Model Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1117;color:#e6edf3;line-height:1.6}}
  .header{{background:linear-gradient(135deg,#161b22,#0d1117);padding:34px 40px;border-bottom:1px solid #30363d}}
  .header h1{{font-size:1.9em;font-weight:800;color:#58a6ff}}
  .header p{{color:#8b949e;margin-top:4px}}
  .container{{max-width:1400px;margin:0 auto;padding:28px 20px}}
  .section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:28px}}
  .section h2{{font-size:1.15em;font-weight:700;color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:18px}}
  table{{width:100%;border-collapse:collapse;font-size:.85em}}
  th{{background:#0d1117;color:#8b949e;padding:9px 12px;text-align:left;border-bottom:1px solid #30363d;font-weight:600;font-size:.78em;text-transform:uppercase}}
  td{{padding:8px 12px;border-bottom:1px solid #21262d;vertical-align:middle}}
  tr:hover{{background:#1c2128}}
  img{{width:100%;border-radius:8px;border:1px solid #30363d;margin-top:8px}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
  .scroll{{overflow-x:auto}}
  .footer{{text-align:center;color:#8b949e;font-size:.82em;padding:20px;border-top:1px solid #30363d}}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 IndiaStocks AI — Machine Learning Model Report</h1>
  <p>Generated: {run_date} &nbsp;|&nbsp; Task: Binary classification (5-day return &gt; 1%) &nbsp;|&nbsp;
     Features: {len(FEATURE_COLS)} &nbsp;|&nbsp; Observations: {len(df):,} &nbsp;|&nbsp; CV: 5-fold Stratified</p>
</div>
<div class="container">

<div class="section">
  <h2>Cross-Validation Performance Summary</h2>
  <div class="scroll">
  <table>
    <thead><tr><th>Model</th><th>CV Accuracy</th><th>±Std</th><th>CV AUC-ROC</th><th>±Std</th><th>CV F1 (Buy)</th></tr></thead>
    <tbody>{model_rows}</tbody>
  </table>
  </div>
  <img src="data:image/png;base64,{charts['cv_scores']}" alt="CV Scores">
</div>

<div class="section">
  <h2>ROC Curves — All Models</h2>
  <img src="data:image/png;base64,{charts['roc']}" alt="ROC Curves">
</div>

<div class="section">
  <h2>Feature Importance — Random Forest (Top 20)</h2>
  <table>
    <thead><tr><th>Rank</th><th>Feature</th><th>Relative Importance</th><th>Score</th></tr></thead>
    <tbody>{feat_rows}</tbody>
  </table>
  <img src="data:image/png;base64,{charts['feat_imp']}" alt="Feature Importance">
</div>

<div class="section">
  <h2>Confusion Matrices</h2>
  <div class="grid2">
    <img src="data:image/png;base64,{charts['cm_rf']}" alt="RF Confusion Matrix">
    <img src="data:image/png;base64,{charts['cm_gb']}" alt="GB Confusion Matrix">
  </div>
</div>

<div class="section">
  <h2>Sector-wise Prediction Accuracy (Random Forest)</h2>
  <img src="data:image/png;base64,{charts['sector_acc']}" alt="Sector Accuracy">
</div>

<div class="section">
  <h2>Model Architecture Details</h2>
  <table>
    <thead><tr><th>Model</th><th>Key Hyperparameters</th><th>Use Case</th></tr></thead>
    <tbody>
      <tr><td><b>Random Forest</b></td><td>n_estimators=200, max_depth=8, min_samples_leaf=20</td><td>Primary production model — robust, interpretable, handles non-linearity</td></tr>
      <tr><td><b>Gradient Boost</b></td><td>n_estimators=150, max_depth=4, lr=0.05</td><td>Sequential boosting — captures complex feature interactions</td></tr>
      <tr><td><b>Logistic Regression</b></td><td>C=0.5, max_iter=500</td><td>Linear baseline — fast, interpretable, good for sanity checking</td></tr>
      <tr><td><b>SVM (RBF)</b></td><td>C=1.0, kernel=rbf, probability=True</td><td>Kernel trick for non-linear decision boundary</td></tr>
    </tbody>
  </table>
</div>

</div>
<div class="footer">IndiaStocks AI ML Report &nbsp;|&nbsp; {run_date} &nbsp;|&nbsp; sklearn {__import__('sklearn').__version__} &nbsp;|&nbsp; NOT financial advice</div>
</body>
</html>"""

    out_path = os.path.join(REPORT_DIR, f"ml_report_{datetime.date.today()}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nML Report saved: {out_path}")
    print("\nAll 3 DS modules complete!")
    print("  1. ds_pipeline.py  → ds_data/feature_matrix.csv")
    print("  2. ds_eda.py        → reports/eda_report_*.html")
    print(f"  3. ds_ml_model.py  → reports/ml_report_*.html")
    print(f"  Trained model       → ds_data/models/random_forest.pkl")


if __name__ == "__main__":
    main()
