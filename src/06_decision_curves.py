"""
Decision-curve analysis (net benefit) for the 5-year CRC-death models on
the EO temporal test set (prespecified exploratory threshold range; the
horizon follows config.HORIZON_MONTHS and the protocol S5 adequacy rule).

Net benefit at threshold pt:  NB = TP/n - FP/n * pt/(1-pt)
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import PREDS, RESULTS, FIGURES, HORIZON_MONTHS, DCA_THRESHOLDS
from utils_features import watermark


def net_benefit(y: np.ndarray, p: np.ndarray, thresholds: np.ndarray):
    n = len(y)
    out = []
    for t in thresholds:
        pred_pos = p >= t
        tp = np.sum(pred_pos & (y == 1))
        fp = np.sum(pred_pos & (y == 0))
        out.append(tp / n - fp / n * t / (1 - t))
    return np.array(out)


def main() -> None:
    start, stop, step = DCA_THRESHOLDS
    thresholds = np.arange(start, stop + 1e-9, step)

    h = pd.read_csv(PREDS / f"EO_h{HORIZON_MONTHS}_test.csv")
    y = h.y_h.values
    prevalence = y.mean()

    curves = {
        "XGBoost": net_benefit(y, h.p_xgb.values, thresholds),
        "Logistic": net_benefit(y, h.p_logit.values, thresholds),
        "Treat all": prevalence - (1 - prevalence)
                     * thresholds / (1 - thresholds),
        "Treat none": np.zeros_like(thresholds),
    }

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"XGBoost": "#c0392b", "Logistic": "#2c3e50",
              "Treat all": "#95a5a6", "Treat none": "#bdc3c7"}
    for label, nb in curves.items():
        ax.plot(thresholds, nb, label=label, color=colors[label],
                lw=2 if label in ("XGBoost", "Logistic") else 1.2,
                ls="-" if label in ("XGBoost", "Logistic") else "--")
    ax.set_ylim(-0.02, max(prevalence * 1.15, 0.05))
    ax.set_xlabel("Threshold probability of CRC death within "
                  f"{HORIZON_MONTHS//12} years")
    ax.set_ylabel("Net benefit")
    ax.set_title("Decision-curve analysis - early-onset CRC, temporal test set")
    ax.legend()
    ax.grid(alpha=.25)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "decision_curve_EO.png", dpi=200)
    plt.close(fig)

    pd.DataFrame({"threshold": thresholds, **curves}).to_csv(
        RESULTS / "decision_curve_EO.csv", index=False)
    print(f"Wrote {FIGURES/'decision_curve_EO.png'} and "
          f"{RESULTS/'decision_curve_EO.csv'} "
          f"(event prevalence in horizon subcohort: {prevalence:.3f})")


if __name__ == "__main__":
    main()
