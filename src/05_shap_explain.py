"""
SHAP explainability for the 5-year XGBoost models, including the
EO-vs-AO prognostic-pattern contrast (a core exploratory analysis of
the study).
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from config import MODELS, RESULTS, FIGURES, HORIZON_MONTHS, SEED
from utils_features import load_cohort, slice_group, FeatureBuilder, watermark

rng = np.random.default_rng(SEED)
MAX_SHAP_N = 3000  # subsample test set for speed


def shap_for_group(df, group):
    clf = xgb.XGBClassifier()
    clf.load_model(MODELS / f"{group}_xgb_h{HORIZON_MONTHS}.json")
    fb = FeatureBuilder.load(f"{group}_design")  # same frozen preprocessing

    te = slice_group(df, group, "test")
    X = fb.transform(te)
    if len(X) > MAX_SHAP_N:
        X = X.iloc[rng.choice(len(X), MAX_SHAP_N, replace=False)]

    explainer = shap.TreeExplainer(clf)
    sv = explainer.shap_values(X)

    fig = plt.figure(figsize=(8, 6))
    shap.summary_plot(sv, X, show=False, max_display=15)
    plt.title(f"{group}: model-attributed importance (SHAP) - "
              f"{HORIZON_MONTHS//12}-yr CRC death")
    watermark(fig)
    plt.tight_layout()
    fig.savefig(FIGURES / f"shap_summary_{group}.png", dpi=200,
                bbox_inches="tight")
    plt.close("all")

    mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=X.columns,
                         name=group)
    return mean_abs


def main() -> None:
    df = load_cohort()
    importances = {g: shap_for_group(df, g) for g in ["EO", "AO"]}
    imp = pd.concat(importances, axis=1).fillna(0.0)
    imp["EO_rank"] = imp["EO"].rank(ascending=False).astype(int)
    imp["AO_rank"] = imp["AO"].rank(ascending=False).astype(int)
    imp = imp.sort_values("EO", ascending=False)
    imp.to_csv(RESULTS / "shap_mean_abs_importance.csv")

    top = imp.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ypos = np.arange(len(top))
    ax.barh(ypos + 0.2, top["EO"], height=0.4, label="EO-trained model",
            color="#c0392b")
    ax.barh(ypos - 0.2, top["AO"], height=0.4, label="AO-trained model",
            color="#2c3e50")
    ax.set_yticks(ypos)
    ax.set_yticklabels(top.index, fontsize=8)
    ax.set_xlabel("Mean |SHAP value| (model-attributed importance; scales "
                  "are not directly comparable across models)")
    ax.set_title("Model-attributed importance: EO- vs AO-trained models")
    ax.legend()
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "shap_eo_vs_ao_contrast.png", dpi=200)
    plt.close(fig)
    print(f"Wrote SHAP figures to {FIGURES}/ and importance table to "
          f"{RESULTS/'shap_mean_abs_importance.csv'}")


if __name__ == "__main__":
    main()
