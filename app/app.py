"""
EO-CRC transportability explorer — RESEARCH-USE-ONLY demonstration app.

Loads the frozen models produced by the pipeline (results/<mode>/models/)
and shows, for a hypothetical patient profile, the horizon CRC-death risk
from (1) the EO-trained model, (2) the frozen AO-trained model transported
unchanged, and (3) the AO model after EO-train-only recalibration. It also
displays the pipeline's audit tables and figures.

It never fits anything, never touches raw data, and refuses to render
without an explicit statement of the data mode (SYNTHETIC vs SEER).

Run:  streamlit run app/app.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import (DATA_MODE, MODELS, RESULTS, FIGURES, HORIZON_MONTHS,   # noqa: E402
                    EO_MAX_AGE, MIN_AGE, MAX_AGE, TRAIN_YEARS, TEST_YEARS)
from utils_features import FeatureBuilder                                 # noqa: E402

DISCLAIMER = (
    "**Research use only.** This is a model-exploration demonstration built "
    "from a preregistered methods study. It is **not medical advice**, is "
    "**not intended for clinical decision-making**, and is **not a validated "
    "or approved clinical decision-support system**. Its outputs depend on "
    "the population and data source used for development; prospective and "
    "external clinical validation would be required before any clinical use."
)

st.set_page_config(page_title="EO-CRC transportability explorer",
                   page_icon="🧭", layout="wide")

# ------------------------------------------------------------- mode banner
if DATA_MODE == "synthetic":
    st.error("**SYNTHETIC-DATA MODE** — the models loaded below were fitted on "
             "fabricated, SEER-*like* data for pipeline testing. Every number "
             "on this page is scientifically meaningless. This banner turns "
             "green only when the pipeline has been run on a real SEER export.")
else:
    st.success("**SEER MODE** — models fitted on the SEER Research Data export "
               "documented in data/README.md. Case-level data are never "
               "displayed or stored by this app.")
st.warning(DISCLAIMER)

st.title("Early-onset CRC: does an average-onset survival model transport?")
st.caption(
    f"Frozen models: EO-trained (age {MIN_AGE}–{EO_MAX_AGE}) and AO-trained "
    f"(age {EO_MAX_AGE+1}–{MAX_AGE}), development years "
    f"{TRAIN_YEARS[0]}–{TRAIN_YEARS[1]}, temporal test {TEST_YEARS[0]}–"
    f"{TEST_YEARS[1]}. Horizon: {HORIZON_MONTHS} months.")


# ------------------------------------------------------------- load frozen artifacts
@st.cache_resource(show_spinner=False)
def load_artifacts():
    import joblib
    import xgboost as xgb
    need = [MODELS / "EO_design_features.json", MODELS / "AO_design_features.json",
            MODELS / f"EO_xgb_h{HORIZON_MONTHS}.json",
            MODELS / f"AO_xgb_h{HORIZON_MONTHS}.json",
            MODELS / "AO_sk_models.joblib", MODELS / "recalibration_params.json"]
    missing = [str(p.relative_to(ROOT)) for p in need if not p.exists()]
    if missing:
        return None, missing
    fb_eo, fb_ao = FeatureBuilder.load("EO_design"), FeatureBuilder.load("AO_design")
    eo_h, ao_h = xgb.XGBClassifier(), xgb.XGBClassifier()
    eo_h.load_model(MODELS / f"EO_xgb_h{HORIZON_MONTHS}.json")
    ao_h.load_model(MODELS / f"AO_xgb_h{HORIZON_MONTHS}.json")
    ao_sk = joblib.load(MODELS / "AO_sk_models.joblib")
    recal = json.loads((MODELS / "recalibration_params.json").read_text())
    return dict(fb_eo=fb_eo, fb_ao=fb_ao, eo_h=eo_h, ao_h=ao_h,
                cox_ao=ao_sk["cox_full"], recal=recal), []


art, missing = load_artifacts()
if art is None:
    st.info("No frozen models found for this data mode. Run the pipeline "
            "first (`bash run_all.sh`), then reload. Missing: "
            + ", ".join(missing))
    st.stop()


def _logit(p, eps=1e-9):
    p = np.clip(p, eps, 1 - eps); return np.log(p / (1 - p))


def _sig(z):
    return 1 / (1 + np.exp(-z))


tab_pt, tab_res, tab_about = st.tabs(
    ["Patient profile", "Study tables & figures", "About / how to read"])

# ------------------------------------------------------------- patient profile
with tab_pt:
    st.subheader("Hypothetical patient profile")
    st.caption("Enter a profile to see how the three models score it. Inputs "
               "are the registry-style predictors the models were built on; "
               "nothing is stored.")
    c1, c2, c3 = st.columns(3)
    with c1:
        age = st.number_input("Age at diagnosis", MIN_AGE, MAX_AGE, 42)
        sex = st.selectbox("Sex", ["Male", "Female"])
        race = st.selectbox("Race/ethnicity (SEER recode)",
                            ["White", "Black", "Hispanic",
                             "Asian/Pacific Islander", "Other/Unknown"])
        year = st.number_input("Year of diagnosis", TRAIN_YEARS[0],
                               TEST_YEARS[1], TEST_YEARS[0])
        site = st.selectbox("Anatomic subsite", ["Right colon", "Left colon",
                                                 "Rectum", "Colon, NOS/overlapping"])
    with c2:
        stage = st.selectbox("Combined summary stage",
                             ["Localized", "Regional", "Distant"])
        hist = st.selectbox("Histology", ["Adenocarcinoma", "Mucinous", "Signet ring"])
        grade = st.selectbox("Grade", ["Grade I", "Grade II", "Grade III",
                                       "Grade IV", "Unknown"])
        size_known = st.checkbox("Tumor size known", True)
        size = st.number_input("Tumor size (mm)", 1, 300, 45,
                               disabled=not size_known)
    with c3:
        n_ex = st.number_input("Regional nodes examined", 0, 90, 15)
        n_pos = st.number_input("Regional nodes positive", 0, 90, 0)
        cea = st.selectbox("Pretreatment CEA", ["Normal", "Elevated", "Unknown"])
        surg = st.selectbox("Surgery of primary site", ["Yes", "No", "Unknown"])
        chemo = st.selectbox("Chemotherapy (SEER recode)", ["Yes", "No/Unknown"])
        rad = st.selectbox("Radiation (SEER recode)", ["Yes", "No/Unknown"])

    n_pos = min(n_pos, n_ex) if n_ex > 0 else n_pos
    row = pd.DataFrame([dict(
        age_dx=age, sex=sex, race_eth=race, year_dx=year, site_group=site,
        histology=hist, grade=grade, summary_stage=stage,
        tumor_size_mm=(size if size_known else np.nan),
        tumor_size_missing=int(not size_known),
        nodes_examined=n_ex, nodes_positive=n_pos,
        nodes_not_examined=int(n_ex <= 0),
        node_ratio=(n_pos / n_ex if n_ex > 0 else np.nan),
        cea=cea, surgery=surg, chemo=chemo, radiation=rad)])

    p_eo = float(art["eo_h"].predict_proba(art["fb_eo"].transform(row))[:, 1][0])
    p_ao = float(art["ao_h"].predict_proba(art["fb_ao"].transform(row))[:, 1][0])
    rc = art["recal"]["xgb_h_intercept_slope"]
    p_ao_recal = float(_sig(rc["intercept"] + rc["slope"] * _logit(p_ao)))
    lp = float(np.log(art["cox_ao"].predict_partial_hazard(
        art["fb_ao"].transform(row)).values[0]))
    cb = art["recal"]["cox_baseline"]
    p_cox_recal = float(1 - np.exp(-cb["H0_at_horizon"] * np.exp(lp - cb["lp_center"])))

    st.markdown("---")
    yrs = HORIZON_MONTHS // 12
    if age > EO_MAX_AGE:
        st.info(f"This profile is age {age} — outside the early-onset range "
                f"({MIN_AGE}–{EO_MAX_AGE}). The transport question is about "
                "EO patients; scores are shown for completeness only.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"EO-trained model · {yrs}-yr CRC-death risk", f"{p_eo:.1%}")
    m2.metric("AO-trained, transported frozen", f"{p_ao:.1%}",
              delta=f"{(p_ao - p_eo)*100:+.1f} pts vs EO", delta_color="off")
    m3.metric("AO-trained + EO-train recalibration (int.+slope)",
              f"{p_ao_recal:.1%}", delta=f"{(p_ao_recal - p_eo)*100:+.1f} pts vs EO",
              delta_color="off")
    m4.metric("AO Cox, EO-train baseline re-estimated", f"{p_cox_recal:.1%}",
              delta=f"{(p_cox_recal - p_eo)*100:+.1f} pts vs EO", delta_color="off")
    st.caption(
        "The gap between column 1 and column 2 is the *transportability* "
        "question for this one profile; column 3/4 show whether the "
        "prespecified recalibration (fitted on EO training data only) closes "
        "it. Population-level answers, with paired confidence intervals, are "
        "on the next tab — a single profile cannot support any conclusion.")

# ------------------------------------------------------------- study tables
with tab_res:
    st.subheader(f"Pipeline outputs — mode: {DATA_MODE.upper()}")
    if DATA_MODE == "synthetic":
        st.error("These tables come from fabricated data and support no "
                 "scientific conclusion. Expected pattern on synthetic data: "
                 "paired transport deltas ≈ 0 (EO and AO share one generating "
                 "process).")
    tables = {
        "Follow-up adequacy (protocol §5 — read BEFORE modeling)": "followup_adequacy.csv",
        "PRIMARY: paired transportability (EO-trained vs frozen AO-trained, identical EO test patients)": "transportability_paired.csv",
        "Recalibration of the frozen AO model (fitted on EO train, evaluated on EO test)": "recalibration.csv",
        "H3: EO paired ΔC vs full Cox": "h3_eo_paired_deltaC.csv",
        "Survival-model discrimination (Harrell C, td-AUC)": "model_performance_survival.csv",
        "Fixed-horizon model calibration (secondary estimand)": "model_performance_horizon.csv",
        "Competing risks — Aalen–Johansen cumulative incidence": "cumulative_incidence.csv",
        "SHAP: model-attributed importance (EO vs AO; scales not comparable)": "shap_mean_abs_importance.csv",
        "Cohort flow": "cohort_flow.csv",
    }
    for title, fn in tables.items():
        f = RESULTS / fn
        with st.expander(title, expanded=fn.startswith("transportability")):
            if f.exists():
                st.dataframe(pd.read_csv(f), width='stretch')
            else:
                st.write(f"`{fn}` not generated yet.")
    st.markdown("#### Figures")
    figs = sorted(FIGURES.glob("*.png"))
    if not figs:
        st.write("No figures generated yet.")
    cols = st.columns(2)
    for i, f in enumerate(figs):
        cols[i % 2].image(str(f), caption=f.name, width='stretch')

# ------------------------------------------------------------- about
with tab_about:
    st.subheader("What this app is — and is not")
    st.markdown(DISCLAIMER)
    st.markdown(f"""
**Study question.** Do explainable ML survival models trained on
average-onset colorectal cancer (age {EO_MAX_AGE+1}–{MAX_AGE}) transport,
frozen, to early-onset patients (age {MIN_AGE}–{EO_MAX_AGE}), and does
recalibration repair any gap? Temporal validation: develop
{TRAIN_YEARS[0]}–{TRAIN_YEARS[1]}, test {TEST_YEARS[0]}–{TEST_YEARS[1]}.

**How to read the patient tab.** All three scores are for the same
hypothetical profile at the {HORIZON_MONTHS}-month horizon (CRC death by
{HORIZON_MONTHS} months, i.e. event at T ≤ {HORIZON_MONTHS}). Column 1 is
the model built on early-onset patients. Column 2 is the average-onset
model applied unchanged — its own preprocessing included — which is the
transportability experiment. Columns 3–4 apply the recalibration
parameters that were fitted on early-onset *training* data only.

**What the app never does.** It never refits a model, never reads raw
SEER files, never stores inputs, and never mixes synthetic and SEER
outputs (they live in separate `results/` folders and the banner states
which one is loaded).

**Provenance.** Protocol: `docs/protocol_OSF_preregistration.md` (v4.0).
Every prespecified analysis maps to a script in
`docs/protocol_code_concordance.md`. Code: MIT. SEER data: governed by
the SEER Research Data Use Agreement; never redistributed.
""")
