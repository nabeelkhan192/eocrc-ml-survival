"""
Evaluate all models: discrimination (Harrell C with bootstrap CIs,
time-dependent AUC where scikit-survival is available), horizon calibration
(plots, slope, offset-logistic intercept, Brier), and the PRIMARY
transportability analysis: paired-bootstrap deltas between the EO-trained
and the frozen AO-trained model on the identical EO test patients.

Calibration-in-the-large (CITL) is the intercept of a logistic regression
of the outcome on an offset of logit(p) (log-odds scale, standard
definition). The simple mean difference is reported separately as
obs_minus_exp (probability scale) - the two are NOT interchangeable.
"""
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines.utils import concordance_index
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from config import (
    PREDS, RESULTS, FIGURES, HORIZON_MONTHS, TD_AUC_TIMES, SEED, BOOTSTRAP_N,
)
from utils_features import load_cohort, slice_group, watermark

warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)

try:
    from sksurv.metrics import cumulative_dynamic_auc
    from sksurv.util import Surv
    HAS_SKSURV = True
except ImportError:
    HAS_SKSURV = False


def cindex_ci(T, E, risk, n_boot=BOOTSTRAP_N):
    """Harrell C (higher risk = shorter survival) with bootstrap 95% CI."""
    point = concordance_index(T, -risk, E)
    idx = np.arange(len(T))
    stats = []
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        try:
            stats.append(concordance_index(T[b], -risk[b], E[b]))
        except ZeroDivisionError:
            continue
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return point, lo, hi


def paired_delta_c(T, E, risk_a, risk_b, n_boot=BOOTSTRAP_N):
    """Paired bootstrap of Delta C = C(a) - C(b) on the SAME patients.

    Both models are re-scored on the identical patient resample, so the
    delta CI reflects between-model differences, not sampling noise added
    twice (per protocol S7 step 3). Seeded; B = config.BOOTSTRAP_N.
    """
    point = (concordance_index(T, -risk_a, E)
             - concordance_index(T, -risk_b, E))
    idx = np.arange(len(T))
    deltas = []
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        try:
            deltas.append(concordance_index(T[b], -risk_a[b], E[b])
                          - concordance_index(T[b], -risk_b[b], E[b]))
        except ZeroDivisionError:
            continue
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return point, lo, hi


def paired_delta_auc(y, p_a, p_b, n_boot=BOOTSTRAP_N):
    """Paired bootstrap of Delta AUC for the fixed-horizon models."""
    point = roc_auc_score(y, p_a) - roc_auc_score(y, p_b)
    idx = np.arange(len(y))
    deltas = []
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        if len(np.unique(y[b])) < 2:
            continue
        deltas.append(roc_auc_score(y[b], p_a[b])
                      - roc_auc_score(y[b], p_b[b]))
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return point, lo, hi


def paired_delta_td_auc(train_df, T, E, risk_a, risk_b, n_boot=BOOTSTRAP_N):
    """Paired bootstrap of Delta time-dependent (cumulative/dynamic) AUC =
    AUC_t(a) - AUC_t(b) at each t in TD_AUC_TIMES, on the SAME patients.

    Survival-model time-dependent AUC (Uno-type IPCW, scikit-survival) -
    NOT the ordinary fixed-horizon binary ROC AUC used for the classifier.
    Each replicate resamples patients once and scores BOTH models on that
    resample; the training-window survival distribution used for IPCW
    weights is held fixed. Replicates where the metric cannot be computed
    (e.g., no events before t) are skipped and the count is reported.
    Returns dict t -> (point, lo, hi, n_valid_replicates)."""
    if not HAS_SKSURV:
        return {t: (np.nan, np.nan, np.nan, 0) for t in TD_AUC_TIMES}
    s_train = Surv.from_arrays(train_df.css_event.astype(bool),
                               train_df.survival_months)

    def _aucs(idx):
        s_test = Surv.from_arrays(E[idx].astype(bool), T[idx])
        a, _ = cumulative_dynamic_auc(s_train, s_test, risk_a[idx], TD_AUC_TIMES)
        b, _ = cumulative_dynamic_auc(s_train, s_test, risk_b[idx], TD_AUC_TIMES)
        return np.asarray(a) - np.asarray(b)

    idx_all = np.arange(len(T))
    try:
        point = _aucs(idx_all)
    except Exception as exc:
        print(f"  paired td-AUC skipped: {exc}")
        return {t: (np.nan, np.nan, np.nan, 0) for t in TD_AUC_TIMES}
    deltas = []
    for _ in range(n_boot):
        b = rng.choice(idx_all, size=len(idx_all), replace=True)
        try:
            deltas.append(_aucs(b))
        except Exception:
            continue
    deltas = np.asarray(deltas)
    out = {}
    for j, t in enumerate(TD_AUC_TIMES):
        if len(deltas) == 0:
            out[t] = (float(point[j]), np.nan, np.nan, 0)
        else:
            lo, hi = np.percentile(deltas[:, j], [2.5, 97.5])
            out[t] = (float(point[j]), float(lo), float(hi), len(deltas))
    return out


def td_auc(train_df, T, E, risk):
    if not HAS_SKSURV:
        return {t: np.nan for t in TD_AUC_TIMES}
    s_train = Surv.from_arrays(train_df.css_event.astype(bool),
                               train_df.survival_months)
    s_test = Surv.from_arrays(E.astype(bool), T)
    try:
        aucs, _ = cumulative_dynamic_auc(s_train, s_test, risk, TD_AUC_TIMES)
        return dict(zip(TD_AUC_TIMES, aucs))
    except Exception as exc:  # times outside follow-up etc.
        print(f"  td-AUC skipped: {exc}")
        return {t: np.nan for t in TD_AUC_TIMES}


def calibration_metrics(y, p):
    """slope, CITL (offset-logistic intercept, log-odds scale),
    obs_minus_exp (probability scale), Brier."""
    y, p = np.asarray(y), np.asarray(p)
    eps = 1e-9
    logit_p = np.log(np.clip(p, eps, 1 - eps) / np.clip(1 - p, eps, 1 - eps))
    lr = LogisticRegression(penalty=None, max_iter=2000)
    lr.fit(logit_p.reshape(-1, 1), y)
    slope = float(lr.coef_[0][0])
    # CITL: intercept with slope fixed at 1 (offset model), via one Newton-
    # style refit: fit intercept-only logistic with logit_p as offset.
    citl = _offset_intercept(y, logit_p)
    obs_minus_exp = float(np.mean(y) - np.mean(p))
    return slope, citl, obs_minus_exp, brier_score_loss(y, p)


def _offset_intercept(y, offset, n_iter=50):
    """Intercept a of logit(P(y=1)) = a + offset, by Newton-Raphson."""
    a = 0.0
    for _ in range(n_iter):
        p = 1.0 / (1.0 + np.exp(-(a + offset)))
        grad = np.sum(y - p)
        hess = np.sum(p * (1 - p))
        if hess <= 0:
            break
        step = grad / hess
        a += step
        if abs(step) < 1e-10:
            break
    return float(a)


def calibration_plot(entries, title, path):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
    for label, y, p, color in entries:
        frac, mean_p = calibration_curve(y, p, n_bins=10, strategy="quantile")
        ax.plot(mean_p, frac, "o-", color=color, label=label)
    ax.set_xlabel(f"Predicted {HORIZON_MONTHS//12}-yr CRC-death probability")
    ax.set_ylabel("Observed proportion")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=.25)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    df = load_cohort()
    rows = []

    # ------------------------------------------------ survival models
    for group in ["EO", "AO"]:
        tr = slice_group(df, group, "train")
        preds = pd.read_csv(PREDS / f"{group}_surv_test.csv")
        T, E = preds["T"].values, preds["E"].values
        for model in [c for c in preds.columns if c.startswith("risk_")]:
            risk = preds[model].values
            c, lo, hi = cindex_ci(T, E, risk)
            aucs = td_auc(tr, T, E, risk)
            rows.append(dict(
                group=group, model=model.replace("risk_", ""),
                cindex=round(c, 3), ci=f"({lo:.3f}-{hi:.3f})",
                **{f"tdAUC_{t}m": round(aucs[t], 3) for t in TD_AUC_TIMES}))
            print(f"{group:>3} {model:<22} C={c:.3f} ({lo:.3f}-{hi:.3f})")

    # ------------------------------------------------ H3: EO paired dC vs full Cox
    eo_p = pd.read_csv(PREDS / "EO_surv_test.csv")
    Te, Ee = eo_p["T"].values, eo_p["E"].values
    h3 = []
    for col in [c for c in eo_p.columns
                if c.startswith("risk_") and c != "risk_cox_full"]:
        d, lo, hi = paired_delta_c(Te, Ee, eo_p[col].values,
                                   eo_p.risk_cox_full.values)
        h3.append(dict(model=col.replace("risk_", ""),
                       paired_dC_vs_cox_full=round(d, 4),
                       ci=f"({lo:.4f}-{hi:.4f})"))
        print(f" H3 EO {col:<16} dC vs cox_full = {d:+.4f} ({lo:+.4f},{hi:+.4f})")
    pd.DataFrame(h3).to_csv(RESULTS / "h3_eo_paired_deltaC.csv", index=False)

    # ------------------------------------------------ horizon models
    calib_rows = []
    for group in ["EO", "AO"]:
        h = pd.read_csv(PREDS / f"{group}_h{HORIZON_MONTHS}_test.csv")
        entries = []
        for model, color in [("p_xgb", "#c0392b"), ("p_logit", "#2c3e50")]:
            slope, citl, ome, brier = calibration_metrics(h.y_h, h[model])
            auc = roc_auc_score(h.y_h, h[model])
            calib_rows.append(dict(group=group, model=model, AUC=round(auc, 3),
                                   brier=round(brier, 4),
                                   calib_slope=round(slope, 3),
                                   citl_logit=round(citl, 3),
                                   obs_minus_exp=round(ome, 4)))
            entries.append((model.replace("p_", "").upper(), h.y_h,
                            h[model], color))
        calibration_plot(entries,
                         f"{group}: {HORIZON_MONTHS//12}-yr calibration "
                         "(temporal test set)",
                         FIGURES / f"calibration_{group}.png")

    # ------------------------------------------------ transportability
    print("\n--- PRIMARY: transportability on the identical EO test set ---")
    eo_surv = pd.read_csv(PREDS / "EO_surv_test.csv")
    trans_surv = pd.read_csv(PREDS / "transport_surv_EOtest.csv")
    assert (eo_surv.patient_id.values
            == trans_surv.patient_id.values).all(), \
        "EO-trained and AO-trained predictions are not patient-aligned"
    tr_eo = slice_group(df, "EO", "train")
    T, E = eo_surv["T"].values, eo_surv["E"].values
    trows = []

    pairs = [
        ("Cox", eo_surv.risk_cox_full.values,
         trans_surv.risk_cox_AOtrained.values),
        ("XGB-Cox", eo_surv.risk_xgb_cox.values,
         trans_surv.risk_xgbcox_AOtrained.values),
    ]
    for name, r_eo, r_ao in pairs:
        for label, risk in [(f"{name} EO-trained", r_eo),
                            (f"{name} AO-trained (frozen)", r_ao)]:
            c, lo, hi = cindex_ci(T, E, risk)
            aucs = td_auc(tr_eo, T, E, risk)
            trows.append(dict(model=label, cindex=round(c, 3),
                              ci=f"({lo:.3f}-{hi:.3f})",
                              **{f"tdAUC_{t}m": round(aucs[t], 3)
                                 for t in TD_AUC_TIMES}))
            print(f"  {label:<28} C={c:.3f} ({lo:.3f}-{hi:.3f})")
        dc, dlo, dhi = paired_delta_c(T, E, r_eo, r_ao)
        trows.append(dict(model=f"{name} paired dC (EO - AO)",
                          cindex=round(dc, 4), ci=f"({dlo:.4f}-{dhi:.4f})",
                          **{f"tdAUC_{t}m": np.nan for t in TD_AUC_TIMES}))
        print(f"  {name} paired dC = {dc:+.4f} ({dlo:+.4f} to {dhi:+.4f}) "
              f"[materiality: dC >= 0.02, CI excl. 0]")
        dta = paired_delta_td_auc(tr_eo, T, E, r_eo, r_ao)
        row = dict(model=f"{name} paired d-tdAUC (EO - AO)", cindex=np.nan,
                   ci="")
        for t, (pt, lo, hi, nv) in dta.items():
            row[f"tdAUC_{t}m"] = round(pt, 4) if pt == pt else np.nan
            row[f"tdAUC_{t}m_ci"] = f"({lo:.4f}-{hi:.4f}) n_boot={nv}"
            print(f"  {name} paired d-tdAUC@{t}m = {pt:+.4f} "
                  f"({lo:+.4f} to {hi:+.4f}; {nv} valid replicates)")
        trows.append(row)

    # horizon-model transport: paired AUC delta + calibration of each
    eo_h = pd.read_csv(PREDS / f"EO_h{HORIZON_MONTHS}_test.csv")
    trans_h = pd.read_csv(PREDS / f"transport_h{HORIZON_MONTHS}_EOtest.csv")
    m = eo_h.merge(trans_h, on=["patient_id", "y_h"])
    for label, p in [("XGB-h EO-trained", m.p_xgb),
                     ("XGB-h AO-trained (frozen)", m.p_xgb_AOtrained)]:
        slope, citl, ome, brier = calibration_metrics(m.y_h, p)
        auc = roc_auc_score(m.y_h, p)
        trows.append(dict(model=label, cindex=np.nan, ci="",
                          **{f"tdAUC_{t}m": np.nan for t in TD_AUC_TIMES},
                          AUC=round(auc, 3), brier=round(brier, 4),
                          calib_slope=round(slope, 3),
                          citl_logit=round(citl, 3),
                          obs_minus_exp=round(ome, 4)))
        print(f"  {label:<28} AUC={auc:.3f} slope={slope:.2f} "
              f"CITL={citl:+.3f} O-E={ome:+.4f}")
    da, dalo, dahi = paired_delta_auc(m.y_h.values, m.p_xgb.values,
                                      m.p_xgb_AOtrained.values)
    trows.append(dict(model="XGB-h paired d-binaryROC-AUC (EO - AO)",
                      cindex=np.nan, ci="",
                      **{f"tdAUC_{t}m": np.nan for t in TD_AUC_TIMES},
                      AUC=round(da, 4),
                      brier=np.nan,
                      calib_slope=np.nan, citl_logit=np.nan,
                      obs_minus_exp=np.nan))
    print(f"  XGB-h paired d-binary-ROC-AUC = {da:+.4f} ({dalo:+.4f} to "
          f"{dahi:+.4f})  [fixed-horizon classifier, secondary]")

    calibration_plot(
        [("EO-trained", m.y_h, m.p_xgb, "#c0392b"),
         ("AO-trained (frozen)", m.y_h, m.p_xgb_AOtrained, "#7f8c8d")],
        "Transportability: horizon calibration in EO patients",
        FIGURES / "calibration_transport_EO.png")

    pd.DataFrame(rows).to_csv(RESULTS / "model_performance_survival.csv",
                              index=False)
    pd.DataFrame(calib_rows).to_csv(
        RESULTS / "model_performance_horizon.csv", index=False)
    pd.DataFrame(trows).to_csv(RESULTS / "transportability_paired.csv",
                               index=False)
    print(f"\nWrote 3 results tables to {RESULTS}/ and calibration figures "
          f"to {FIGURES}/")


if __name__ == "__main__":
    main()
