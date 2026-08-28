"""
Fit all models, per age group, on the temporal training window; predict on
the held-out temporal test window; and generate transportability
predictions (frozen AO-trained models applied to the EO test set).

All data-dependent preprocessing is done by a FeatureBuilder fitted on the
relevant TRAINING window only, then frozen and persisted. Transported
predictions use the AO-fitted builder unchanged, so no EO information can
influence the AO model before the prespecified recalibration stage (07).

Models
------
1. cox_stage   Cox PH, summary stage only (the honest clinical baseline)
2. cox_full    Cox PH, all features (classical benchmark)
3. rsf         Random survival forest (REQUIRED on real data)
4. xgb_cox     XGBoost with survival:cox objective (risk score)
5. xgb_h       XGBoost classifier, death from CRC within HORIZON months
6. logit_h     Logistic regression on the same horizon task (calibration ref)

Hyperparameters (exact procedure, protocol S7):
  Tuning stage - within the group's 2010-2016 development cohort:
    1. seeded internal 80/20 train/validation split (identical for every
       candidate);
    2. a FeatureBuilder is fitted on the INNER-TRAIN 80% only and used to
       transform inner-train and inner-validation;
    3. for each max_depth in config.XGB_DEPTH_GRID, boost with early
       stopping on inner-validation; record best depth and best n_rounds.
  Final development model:
    4. a NEW FeatureBuilder is fitted on the FULL development cohort;
    5. the boosted model is REFIT on the full development cohort with the
       selected depth and the selected number of rounds (no early stopping,
       no validation data);
    6. this full pipeline is frozen, persisted, and applied unchanged to
       the temporal test cohort and (for AO) transported to EO test.
  Cox / logistic / RSF have no tuned hyperparameters: fitted once on the
  full development cohort with the same full-cohort FeatureBuilder.
Nothing outside the development window ever touches preprocessing, tuning,
early stopping, model selection, or final fitting.
"""
import warnings

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from lifelines import CoxPHFitter
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import (
    PREDS, MODELS, HORIZON_MONTHS, SEED, XGB_DEPTH_GRID, DATA_MODE,
)
from utils_features import load_cohort, slice_group, FeatureBuilder
from estimands import horizon_frame

warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from sksurv.ensemble import RandomSurvivalForest
    from sksurv.util import Surv
    HAS_SKSURV = True
except ImportError:
    HAS_SKSURV = False
    if DATA_MODE == "seer":
        raise SystemExit(
            "scikit-survival is REQUIRED for a real-data run (RSF is a "
            "protocol-specified model). Install it: pip install "
            "scikit-survival")
    print("scikit-survival not installed - skipping RSF "
          "(allowed in synthetic pipeline tests only).")


# --------------------------------------------------------------------- fits
def fit_cox(X: pd.DataFrame, T, E, penalizer: float = 0.1) -> CoxPHFitter:
    frame = X.copy()
    frame["T"], frame["E"] = T.values, E.values
    cph = CoxPHFitter(penalizer=penalizer)
    cph.fit(frame, duration_col="T", event_col="E")
    return cph


def tune_xgb_cox(tr: pd.DataFrame):
    """Tuning stage: inner split -> inner-train FeatureBuilder -> depth grid.
    Returns (best_depth, best_n_rounds). Uses NO data outside `tr`."""
    inner_tr, inner_val = train_test_split(
        tr, test_size=0.2, random_state=SEED, stratify=tr.css_event)
    fb_inner = FeatureBuilder().fit(inner_tr)          # inner-train only
    Xtr, Xval = fb_inner.transform(inner_tr), fb_inner.transform(inner_val)
    ytr = np.where(inner_tr.css_event == 1, inner_tr.survival_months,
                   -inner_tr.survival_months)
    yval = np.where(inner_val.css_event == 1, inner_val.survival_months,
                    -inner_val.survival_months)
    dtr, dval = xgb.DMatrix(Xtr, label=ytr), xgb.DMatrix(Xval, label=yval)
    best = (np.inf, None, None)
    for depth in XGB_DEPTH_GRID:
        params = dict(objective="survival:cox", eta=0.05, max_depth=depth,
                      subsample=0.8, colsample_bytree=0.8, seed=SEED,
                      eval_metric="cox-nloglik")
        res = {}
        booster = xgb.train(params, dtr, num_boost_round=600,
                            evals=[(dval, "val")], early_stopping_rounds=30,
                            evals_result=res, verbose_eval=False)
        score = min(res["val"]["cox-nloglik"])
        if score < best[0]:
            best = (score, depth, int(booster.best_iteration) + 1)
    print(f"    xgb_cox tuning: depth={best[1]}, n_rounds={best[2]} "
          f"(inner-val cox-nloglik={best[0]:.4f})")
    return best[1], best[2]


def fit_xgb_cox(X: pd.DataFrame, T, E, depth: int, n_rounds: int):
    """Final refit on the FULL development cohort with fixed hyperparameters
    (no early stopping, no validation data)."""
    y = np.where(E.values == 1, T.values, -T.values)
    params = dict(objective="survival:cox", eta=0.05, max_depth=depth,
                  subsample=0.8, colsample_bytree=0.8, seed=SEED)
    return xgb.train(params, xgb.DMatrix(X, label=y),
                     num_boost_round=n_rounds)


def fit_rsf(X: pd.DataFrame, T, E):
    y = Surv.from_arrays(event=E.astype(bool).values, time=T.values)
    rsf = RandomSurvivalForest(
        n_estimators=300, min_samples_leaf=50, max_features="sqrt",
        n_jobs=-1, random_state=SEED)
    rsf.fit(X.values, y)
    return rsf


def tune_xgb_h(tr_h: pd.DataFrame):
    """Tuning stage for the fixed-horizon classifier (same protocol as
    tune_xgb_cox). Returns (best_depth, best_n_estimators)."""
    inner_tr, inner_val = train_test_split(
        tr_h, test_size=0.2, random_state=SEED, stratify=tr_h.y_h)
    fb_inner = FeatureBuilder().fit(inner_tr)
    Xtr, Xval = fb_inner.transform(inner_tr), fb_inner.transform(inner_val)
    best = (np.inf, None, None)
    for depth in XGB_DEPTH_GRID:
        clf = xgb.XGBClassifier(
            n_estimators=600, learning_rate=0.05, max_depth=depth,
            subsample=0.8, colsample_bytree=0.8, random_state=SEED,
            eval_metric="logloss", early_stopping_rounds=30)
        clf.fit(Xtr, inner_tr.y_h, eval_set=[(Xval, inner_val.y_h)],
                verbose=False)
        if clf.best_score < best[0]:
            best = (clf.best_score, depth, int(clf.best_iteration) + 1)
    print(f"    xgb_h{HORIZON_MONTHS} tuning: depth={best[1]}, "
          f"n_estimators={best[2]} (inner-val logloss={best[0]:.4f})")
    return best[1], best[2]


def fit_xgb_h(X: pd.DataFrame, y: pd.Series, depth: int,
              n_estimators: int) -> xgb.XGBClassifier:
    """Final refit on the FULL development cohort, fixed hyperparameters."""
    clf = xgb.XGBClassifier(
        n_estimators=n_estimators, learning_rate=0.05, max_depth=depth,
        subsample=0.8, colsample_bytree=0.8, random_state=SEED)
    clf.fit(X, y, verbose=False)
    return clf


# --------------------------------------------------------------------- main
def main() -> None:
    df = load_cohort()
    fitted = {}

    for group in ["EO", "AO"]:
        tr = slice_group(df, group, "train")
        te = slice_group(df, group, "test")
        print(f"\n=== {group}: fitting on train (n={len(tr):,}) ===")

        fb = FeatureBuilder().fit(tr)
        fb.save(f"{group}_design")
        fb_stage = FeatureBuilder(stage_only=True).fit(tr)
        fb_stage.save(f"{group}_design_stage")

        X_tr, X_te = fb.transform(tr), fb.transform(te)
        Xs_tr, Xs_te = fb_stage.transform(tr), fb_stage.transform(te)
        T_tr, E_tr = tr.survival_months, tr.css_event

        cox_full = fit_cox(X_tr, T_tr, E_tr)
        cox_stage = fit_cox(Xs_tr, T_tr, E_tr, penalizer=0.01)
        d_cox, n_cox = tune_xgb_cox(tr)                 # tuning stage
        xgb_cox = fit_xgb_cox(X_tr, T_tr, E_tr, d_cox, n_cox)  # full refit
        rsf = fit_rsf(X_tr, T_tr, E_tr) if HAS_SKSURV else None
        tuned = dict(xgb_cox_depth=d_cox, xgb_cox_rounds=n_cox,
                     n_dev=len(tr))

        surv_preds = pd.DataFrame({
            "patient_id": te.patient_id,
            "T": te.survival_months,
            "E": te.css_event,
            "risk_cox_full": cox_full.predict_partial_hazard(X_te).values,
            "risk_cox_stage": cox_stage.predict_partial_hazard(Xs_te).values,
            "risk_xgb_cox": xgb_cox.predict(xgb.DMatrix(X_te)),
        })
        if rsf is not None:
            surv_preds["risk_rsf"] = rsf.predict(X_te.values)
        surv_preds.to_csv(PREDS / f"{group}_surv_test.csv", index=False)

        # ---- fixed-horizon models (secondary estimand; see horizon_frame)
        tr_h, te_h = horizon_frame(tr), horizon_frame(te)
        Xh_tr, Xh_te = fb.transform(tr_h), fb.transform(te_h)
        d_h, n_h = tune_xgb_h(tr_h)                     # tuning stage
        xgb_h = fit_xgb_h(Xh_tr, tr_h.y_h, d_h, n_h)    # full refit
        tuned.update(xgb_h_depth=d_h, xgb_h_estimators=n_h, n_dev_h=len(tr_h))
        pd.Series(tuned).to_json(MODELS / f"{group}_hyperparams.json")

        scaler = StandardScaler().fit(Xh_tr)
        logit = LogisticRegression(max_iter=2000, C=1.0)
        logit.fit(scaler.transform(Xh_tr), tr_h.y_h)

        pd.DataFrame({
            "patient_id": te_h.patient_id,
            "y_h": te_h.y_h,
            "p_xgb": xgb_h.predict_proba(Xh_te)[:, 1],
            "p_logit": logit.predict_proba(scaler.transform(Xh_te))[:, 1],
        }).to_csv(PREDS / f"{group}_h{HORIZON_MONTHS}_test.csv", index=False)

        xgb_h.save_model(MODELS / f"{group}_xgb_h{HORIZON_MONTHS}.json")
        joblib.dump(dict(cox_full=cox_full, cox_stage=cox_stage,
                         logit=logit, scaler=scaler),
                    MODELS / f"{group}_sk_models.joblib")
        xgb_cox.save_model(MODELS / f"{group}_xgb_cox.json")

        fitted[group] = dict(cox_full=cox_full, xgb_cox=xgb_cox,
                             xgb_h=xgb_h, fb=fb)
        print(f"  saved predictions + frozen models for {group}")

    # ---------------- transportability: frozen AO models on EO test -------
    # The AO FeatureBuilder (fitted on AO training data only) transforms the
    # EO test set: the transported model, INCLUDING its preprocessing, is
    # exactly the frozen AO pipeline. No EO parameter enters anywhere.
    print("\n=== Transportability: frozen AO-trained models on EO test ===")
    fb_ao = fitted["AO"]["fb"]
    eo_te = slice_group(df, "EO", "test")
    X_eo = fb_ao.transform(eo_te)
    trans = pd.DataFrame({
        "patient_id": eo_te.patient_id,
        "T": eo_te.survival_months,
        "E": eo_te.css_event,
        "risk_cox_AOtrained": fitted["AO"]["cox_full"]
            .predict_partial_hazard(X_eo).values,
        "risk_xgbcox_AOtrained": fitted["AO"]["xgb_cox"]
            .predict(xgb.DMatrix(X_eo)),
    })
    trans.to_csv(PREDS / "transport_surv_EOtest.csv", index=False)

    eo_te_h = horizon_frame(eo_te)
    Xh_eo = fb_ao.transform(eo_te_h)
    pd.DataFrame({
        "patient_id": eo_te_h.patient_id,
        "y_h": eo_te_h.y_h,
        "p_xgb_AOtrained": fitted["AO"]["xgb_h"].predict_proba(Xh_eo)[:, 1],
    }).to_csv(PREDS / f"transport_h{HORIZON_MONTHS}_EOtest.csv", index=False)

    print("Done. Predictions in", PREDS)


if __name__ == "__main__":
    main()
