"""
Recalibration of the frozen AO-trained models using EO TRAINING-window data
only, evaluated once on the EO temporal test window (protocol S7 step 5).

SCOPE (exactly what is recalibrated):
  * AO fixed-horizon XGBoost classifier (xgb_h)  -> methods (i), (ii)
  * AO full-covariate Cox (cox_full)              -> methods (iii), (iv)
  The AO XGB-Cox risk score is a relative hazard without a baseline hazard
  and is NOT recalibrated (its transport gap is a discrimination question,
  answered by the paired dC / d-tdAUC). RSF is not transported.

Fixed-horizon model (AO xgb_h applied to EO):
  (i)  intercept-only update: logit(p') = logit(p) + a, a fitted by
       offset logistic regression on EO train (calibration-in-the-large
       correction);
  (ii) logistic intercept-and-slope: logit(p') = a + b*logit(p).

Cox-type model (AO cox_full applied to EO):
  (iii) baseline re-estimation: keep the frozen AO covariate effects
        (linear predictor lp), re-estimate the Breslow baseline cumulative
        hazard on EO TRAIN, predict horizon risk 1 - exp(-H0(h)*exp(lp));
  (iv)  additionally, van Houwelingen-type linear-predictor slope
        recalibration: fit Cox(lp) on EO train -> slope b, use b*lp with a
        re-estimated baseline.

Rank-based discrimination is unchanged by the monotone maps (i)-(iii) by
construction; (iv) is also monotone for b > 0. The scientific payoff is
whether CALIBRATION is repaired (recalibration adequacy: slope 0.90-1.10
and |CITL| <= 0.10 on the log-odds scale, study-specific benchmarks).

Everything fitted here uses EO train only. The EO test window is touched
exactly once, at the end, for evaluation.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from lifelines import CoxPHFitter

from config import (
    PREDS, MODELS, RESULTS, FIGURES, HORIZON_MONTHS, SEED,
)
from utils_features import load_cohort, slice_group, FeatureBuilder, watermark
from estimands import horizon_frame, horizon_labels

# reuse metric code from evaluation stage
import importlib
_04 = importlib.import_module("04_evaluate")
calibration_metrics = _04.calibration_metrics
_offset_intercept = _04._offset_intercept
calibration_plot = _04.calibration_plot


def _logit(p, eps=1e-9):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def breslow_baseline(T, E, lp):
    """Breslow estimate of the baseline cumulative hazard H0(t) given a
    FROZEN linear predictor lp (no coefficient re-estimation)."""
    order = np.argsort(T)
    T, E, lp = np.asarray(T)[order], np.asarray(E)[order], np.asarray(lp)[order]
    exp_lp = np.exp(lp - lp.mean())  # center for numerical stability
    # risk-set sums via reverse cumulative sum
    rev_cum = np.cumsum(exp_lp[::-1])[::-1]
    times, H0, h = [], [], 0.0
    i = 0
    n = len(T)
    while i < n:
        t = T[i]
        j = i
        d = 0
        while j < n and T[j] == t:
            d += E[j]
            j += 1
        if d > 0:
            h += d / rev_cum[i]
            times.append(t)
            H0.append(h)
        i = j
    return np.asarray(times), np.asarray(H0), float(lp.mean())


def risk_at(times, H0, horizon, lp, lp_center):
    """P(event <= horizon | lp) = 1 - exp(-H0(horizon) * exp(lp - center))."""
    idx = np.searchsorted(times, horizon, side="right") - 1
    H = H0[idx] if idx >= 0 else 0.0
    return 1.0 - np.exp(-H * np.exp(np.asarray(lp) - lp_center))


def main() -> None:
    df = load_cohort()
    eo_tr = slice_group(df, "EO", "train")
    eo_te = slice_group(df, "EO", "test")

    fb_ao = FeatureBuilder.load("AO_design")
    ao_models = joblib.load(MODELS / "AO_sk_models.joblib")
    ao_xgb_h = xgb.XGBClassifier()
    ao_xgb_h.load_model(MODELS / f"AO_xgb_h{HORIZON_MONTHS}.json")

    rows = []

    # =============== fixed-horizon recalibration (i)-(ii) =================
    tr_h, te_h = horizon_frame(eo_tr), horizon_frame(eo_te)
    p_tr = ao_xgb_h.predict_proba(fb_ao.transform(tr_h))[:, 1]
    p_te = ao_xgb_h.predict_proba(fb_ao.transform(te_h))[:, 1]
    y_tr, y_te = tr_h.y_h.values, te_h.y_h.values

    # (i) intercept-only, fitted on EO TRAIN
    a = _offset_intercept(y_tr, _logit(p_tr))
    p_int = _sigmoid(_logit(p_te) + a)

    # (ii) intercept + slope, fitted on EO TRAIN
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(penalty=None, max_iter=2000)
    lr.fit(_logit(p_tr).reshape(-1, 1), y_tr)
    p_is = lr.predict_proba(_logit(p_te).reshape(-1, 1))[:, 1]

    entries = []
    for label, p, color in [
        ("AO raw (frozen)", p_te, "#7f8c8d"),
        ("AO + intercept", p_int, "#f39c12"),
        ("AO + intercept&slope", p_is, "#27ae60"),
    ]:
        slope, citl, ome, brier = calibration_metrics(y_te, p)
        rows.append(dict(family="horizon", model=label,
                         calib_slope=round(slope, 3),
                         citl_logit=round(citl, 3),
                         obs_minus_exp=round(ome, 4), brier=round(brier, 4),
                         adequate=(0.90 <= slope <= 1.10)
                                  and (abs(citl) <= 0.10)))
        entries.append((label, y_te, p, color))
        print(f"  horizon {label:<24} slope={slope:.2f} CITL={citl:+.3f} "
              f"Brier={brier:.4f}")
    # EO-trained comparator for context
    eo_h_preds = pd.read_csv(PREDS / f"EO_h{HORIZON_MONTHS}_test.csv")
    entries.append(("EO-trained", eo_h_preds.y_h, eo_h_preds.p_xgb,
                    "#c0392b"))
    calibration_plot(entries,
                     "Recalibration of frozen AO model in EO patients",
                     FIGURES / "calibration_recalibrated_EO.png")

    # =============== Cox-type recalibration (iii)-(iv) ====================
    cox_ao: CoxPHFitter = ao_models["cox_full"]
    lp_tr = np.log(cox_ao.predict_partial_hazard(
        fb_ao.transform(eo_tr)).values)
    lp_te = np.log(cox_ao.predict_partial_hazard(
        fb_ao.transform(eo_te)).values)
    T_tr, E_tr = eo_tr.survival_months.values, eo_tr.css_event.values
    T_te, E_te = eo_te.survival_months.values, eo_te.css_event.values

    # (iii) frozen coefficients, EO-train Breslow baseline
    times, H0, center = breslow_baseline(T_tr, E_tr, lp_tr)
    p_base = risk_at(times, H0, HORIZON_MONTHS, lp_te, center)

    # (iv) lp-slope recalibration on EO train, then re-estimated baseline
    slope_frame = pd.DataFrame({"lp": lp_tr, "T": T_tr, "E": E_tr})
    cph_slope = CoxPHFitter()
    cph_slope.fit(slope_frame, duration_col="T", event_col="E")
    b = float(cph_slope.params_["lp"])
    times_b, H0_b, center_b = breslow_baseline(T_tr, E_tr, b * lp_tr)
    p_slope = risk_at(times_b, H0_b, HORIZON_MONTHS, b * lp_te, center_b)
    print(f"  cox lp-slope on EO train: b = {b:.3f} "
          "(b < 1 indicates overfitted/over-dispersed AO effects in EO)")

    # evaluate horizon risks among horizon-observable EO test patients
    obs_mask, y_all = horizon_labels(T_te, E_te, HORIZON_MONTHS)
    y_obs = y_all[obs_mask]
    for label, p in [("Cox AO baseline re-est", p_base[obs_mask]),
                     ("Cox AO lp-slope + baseline", p_slope[obs_mask])]:
        slope, citl, ome, brier = calibration_metrics(y_obs, p)
        rows.append(dict(family="cox", model=label,
                         calib_slope=round(slope, 3),
                         citl_logit=round(citl, 3),
                         obs_minus_exp=round(ome, 4), brier=round(brier, 4),
                         adequate=(0.90 <= slope <= 1.10)
                                  and (abs(citl) <= 0.10),
                         lp_slope_b=round(b, 3)))
        print(f"  cox    {label:<26} slope={slope:.2f} CITL={citl:+.3f} "
              f"Brier={brier:.4f}")

    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "recalibration.csv", index=False)
    # Persist the EO-train-fitted recalibration parameters so the demo app
    # can apply them without refitting (they are fitted on EO TRAIN only).
    import json
    H0_h = float(H0[np.searchsorted(times, HORIZON_MONTHS, side="right") - 1]) \
        if (times <= HORIZON_MONTHS).any() else 0.0
    H0b_h = float(H0_b[np.searchsorted(times_b, HORIZON_MONTHS, side="right") - 1]) \
        if (times_b <= HORIZON_MONTHS).any() else 0.0
    (MODELS / "recalibration_params.json").write_text(json.dumps(dict(
        horizon_months=HORIZON_MONTHS,
        xgb_h_intercept_only=a,
        xgb_h_intercept_slope=dict(intercept=float(lr.intercept_[0]),
                                   slope=float(lr.coef_[0][0])),
        cox_baseline=dict(H0_at_horizon=H0_h, lp_center=center),
        cox_lp_slope=dict(b=b, H0_at_horizon=H0b_h, lp_center=center_b),
        fitted_on="EO training window only",
    ), indent=2))
    print(f"\nWrote {RESULTS/'recalibration.csv'} and "
          f"{FIGURES/'calibration_recalibrated_EO.png'}")
    print("Note: discrimination is unchanged by these monotone updates; "
          "any C-index gap persists by construction (protocol H2).")


if __name__ == "__main__":
    main()
