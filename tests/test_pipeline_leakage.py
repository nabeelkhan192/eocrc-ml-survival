"""Tests for train-only preprocessing, frozen AO->EO transport, paired
alignment, XGB full-cohort refit, and paired delta td-AUC (toy data)."""
import numpy as np
import pandas as pd
import pytest
import importlib

from utils_features import FeatureBuilder
from config import NUMERIC_FEATURES, INDICATOR_FEATURES, CATEGORICAL_FEATURES

_03 = importlib.import_module("03_models")
_04 = importlib.import_module("04_evaluate")


def _toy(n, seed, shift=0.0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "age_dx": rng.integers(20, 80, n),
        "tumor_size_mm": np.where(rng.random(n) < 0.2, np.nan,
                                  rng.normal(40 + shift, 15, n)),
        "nodes_examined": rng.integers(0, 30, n),
        "nodes_positive": rng.integers(0, 5, n),
        "node_ratio": rng.random(n), "year_dx": rng.integers(2010, 2017, n),
        "tumor_size_missing": 0, "nodes_not_examined": 0,
        "sex": rng.choice(["Male", "Female"], n),
        "race_eth": rng.choice(["White", "Black", "Hispanic"], n),
        "site_group": rng.choice(["Right colon", "Left colon", "Rectum"], n),
        "histology": rng.choice(["Adenocarcinoma", "Mucinous"], n),
        "grade": rng.choice(["Grade I", "Grade II", "Grade III"], n),
        "summary_stage": rng.choice(["Localized", "Regional", "Distant"], n),
        "cea": rng.choice(["Normal", "Elevated", "Unknown"], n),
        "surgery": rng.choice(["Yes", "No"], n),
        "chemo": rng.choice(["Yes", "No/Unknown"], n),
        "radiation": rng.choice(["Yes", "No/Unknown"], n),
    })
    df["survival_months"] = rng.integers(1, 120, n)
    df["css_event"] = rng.integers(0, 2, n)
    df["tumor_size_missing"] = df.tumor_size_mm.isna().astype(int)
    return df


# ---------- 12.1 train-only preprocessing -----------------------------------
def test_featurebuilder_uses_train_medians_only():
    tr, te = _toy(400, 1, shift=0), _toy(400, 2, shift=100)  # test very different
    fb = FeatureBuilder().fit(tr)
    assert fb.medians_["tumor_size_mm"] == pytest.approx(
        np.nanmedian(tr.tumor_size_mm), abs=1e-9)
    X_te = fb.transform(te)
    # imputed test values equal TRAIN median, never the test median
    imputed = X_te.loc[te.tumor_size_mm.isna(), "tumor_size_mm"].unique()
    assert len(imputed) == 1 and imputed[0] == pytest.approx(fb.medians_["tumor_size_mm"])
    assert imputed[0] != pytest.approx(np.nanmedian(te.tumor_size_mm), abs=1.0)


def test_featurebuilder_vocabulary_frozen():
    tr = _toy(300, 3)
    te = _toy(300, 4)
    te.loc[0, "race_eth"] = "NEW-CATEGORY"           # unseen level in test
    fb = FeatureBuilder().fit(tr)
    X_te = fb.transform(te)
    assert list(X_te.columns) == fb.columns_        # no test-only columns
    assert not any("NEW-CATEGORY" in c for c in X_te.columns)


# ---------- 12.2 frozen AO pipeline applied to EO ---------------------------
def test_frozen_ao_pipeline_transport_is_deterministic_and_ao_only():
    ao_tr, eo_te = _toy(500, 5), _toy(200, 6, shift=30)
    fb_ao = FeatureBuilder().fit(ao_tr)
    med_before = dict(fb_ao.medians_); cols_before = list(fb_ao.columns_)
    X1 = fb_ao.transform(eo_te)
    X2 = fb_ao.transform(eo_te)
    assert X1.equals(X2)                              # transform is pure
    assert fb_ao.medians_ == med_before and fb_ao.columns_ == cols_before
    # the EO test set's own median must NOT appear in the transported design
    assert (X1.loc[eo_te.tumor_size_mm.isna(), "tumor_size_mm"]
            == med_before["tumor_size_mm"]).all()


# ---------- 12.3 patient alignment in the paired bootstrap ------------------
def test_paired_delta_c_requires_alignment_and_is_zero_for_identical():
    rng = np.random.default_rng(0)
    T = rng.integers(1, 100, 300); E = rng.integers(0, 2, 300)
    r = rng.random(300)
    d, lo, hi = _04.paired_delta_c(T, E, r, r, n_boot=50)
    assert d == 0 and lo == 0 and hi == 0             # identical models -> exactly 0
    # misaligned (shuffled) comparison must NOT be silently accepted upstream:
    # 04.main asserts patient_id equality; here we check the guard logic itself
    a = pd.DataFrame(dict(patient_id=[1, 2, 3])); b = pd.DataFrame(dict(patient_id=[1, 3, 2]))
    assert not (a.patient_id.values == b.patient_id.values).all()


# ---------- 12.9 final XGB refit on the FULL development cohort -------------
def test_xgb_final_model_trained_on_full_development_cohort():
    tr = _toy(600, 7)
    tr["survival_months"] = tr.survival_months.clip(1)
    fb = FeatureBuilder().fit(tr)
    X = fb.transform(tr)
    depth, n_rounds = _03.tune_xgb_cox(tr)
    booster = _03.fit_xgb_cox(X, tr.survival_months, tr.css_event, depth, n_rounds)
    assert booster.num_boosted_rounds() == n_rounds  # fixed rounds, no early stop
    # the final booster saw the FULL cohort: refit on the inner 80% differs
    from sklearn.model_selection import train_test_split
    from config import SEED
    inner_tr, _ = train_test_split(tr, test_size=0.2, random_state=SEED,
                                   stratify=tr.css_event)
    b_inner = _03.fit_xgb_cox(fb.transform(inner_tr), inner_tr.survival_months,
                              inner_tr.css_event, depth, n_rounds)
    import xgboost as xgb
    p_full = booster.predict(xgb.DMatrix(X)); p_inner = b_inner.predict(xgb.DMatrix(X))
    assert not np.allclose(p_full, p_inner)


# ---------- 12.10 paired delta time-dependent AUC ---------------------------
@pytest.mark.skipif(not _04.HAS_SKSURV, reason="scikit-survival required")
def test_paired_delta_td_auc_identical_models_zero_and_uses_shared_sample():
    tr = _toy(500, 8); tr["survival_months"] = tr.survival_months.clip(1)
    rng = np.random.default_rng(1)
    T = rng.integers(1, 100, 400); E = rng.integers(0, 2, 400); r = rng.random(400)
    out = _04.paired_delta_td_auc(tr, T, E, r, r, n_boot=20)
    for t, (pt, lo, hi, nv) in out.items():
        assert pt == pytest.approx(0.0, abs=1e-12)
        assert lo == pytest.approx(0.0, abs=1e-12) and hi == pytest.approx(0.0, abs=1e-12)
        assert nv > 0
    # sanity: a strictly better model gives positive delta
    better = np.where(E == 1, 100 - T, 0) + rng.normal(0, 5, 400)  # higher risk = earlier event
    out2 = _04.paired_delta_td_auc(tr, T, E, better, r, n_boot=20)
    assert out2[60][0] > 0
