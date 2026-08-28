"""Deterministic unit tests for the v4 corrections (toy data only)."""
import numpy as np
import pandas as pd
import pytest

from estimands import (horizon_labels, horizon_frame,
                       event_free_short_followup_share)
import importlib
_01 = importlib.import_module("01_build_cohort")
map_grade, map_site, map_surgery = _01.map_grade, _01.map_site, _01.map_surgery


# ---------- 2. prediction-horizon boundary ----------------------------------
def test_horizon_boundary_h60():
    H = 60
    #        event H-1, event at H, event H+1, censored <H, event-free >H, event-free ==H
    T = np.array([59,       60,          61,        30,          90,           60])
    E = np.array([1,        1,           1,         0,           0,            0])
    obs, y = horizon_labels(T, E, H)
    assert obs.tolist() == [True, True, True, False, True, True]
    assert y.tolist()   == [1,    1,    0,    0,     0,    0]
    # censored-before-H patient is excluded from the observable frame
    df = pd.DataFrame(dict(survival_months=T, css_event=E))
    hf = horizon_frame(df, H)
    assert len(hf) == 5 and hf.y_h.sum() == 2


# ---------- 1. follow-up adequacy denominator = event-free only -------------
def test_adequacy_denominator_event_free_only():
    # 4 event-free (3 short, 1 long) + 6 events (all short follow-up).
    T = np.array([10, 20, 30, 90,   5, 5, 5, 5, 5, 5])
    E = np.array([0,  0,  0,  0,    1, 1, 1, 1, 1, 1])
    share = event_free_short_followup_share(T, E, H=60)
    assert share == pytest.approx(3 / 4)          # NOT 3/10 (all-patient denominator)
    wrong = ((E == 0) & (T < 60)).mean()
    assert wrong == pytest.approx(0.3)             # the old (incorrect) quantity
    assert np.isnan(event_free_short_followup_share([1, 2], [1, 1], 60))


# ---------- 5B. grade parsing: mutually exclusive ---------------------------
@pytest.mark.parametrize("label,expected", [
    ("Well differentiated; Grade I", "Grade I"),
    ("Moderately differentiated; Grade II", "Grade II"),
    ("Poorly differentiated; Grade III", "Grade III"),
    ("Undifferentiated; anaplastic; Grade IV", "Grade IV"),
    ("Grade IV", "Grade IV"), ("Grade I", "Grade I"),
    ("Unknown", "Unknown"), ("", "Unknown"), ("Blank(s)", "Unknown"),
    ("Not applicable", "Unknown"), ("G3", "Grade III"),
])
def test_grade_mapping(label, expected):
    assert map_grade(pd.Series([label]))[0] == expected


def test_grade_I_never_captures_IV():
    out = map_grade(pd.Series(["Grade IV", "Grade I", "Grade II", "Grade III"]))
    assert list(out) == ["Grade IV", "Grade I", "Grade II", "Grade III"]


# ---------- 5A. site: C18.8/C18.9 not silently sided ------------------------
def test_site_nos_and_overlapping():
    s = pd.Series(["C18.8-Overlapping lesion of colon", "C18.9-Colon, NOS",
                   "C18.7-Sigmoid colon", "C18.0-Cecum",
                   "C19.9-Rectosigmoid junction", "C20.9-Rectum, NOS",
                   "C18.5-Splenic flexure of colon", "something weird"])
    out = list(map_site(s))
    assert out[0] == "Colon, NOS/overlapping"
    assert out[1] == "Colon, NOS/overlapping"
    assert out[2] == "Left colon" and out[3] == "Right colon"
    assert out[4] == "Rectum" and out[5] == "Rectum" and out[6] == "Left colon"
    assert out[7] == "Colon, NOS/overlapping"      # unrecognized is not sided


# ---------- 5C. surgery: unknown != yes -------------------------------------
def test_surgery_unknown_handling():
    s = pd.Series(["00-None; no surgery of primary site", "30-Partial colectomy",
                   "99-Unknown if surgery performed", "98-Site-specific NA",
                   "", "Blank(s)", "gibberish", "Yes"])
    out = list(map_surgery(s))
    assert out == ["No", "Yes", "Unknown", "Unknown", "Unknown", "Unknown",
                   "Unknown", "Yes"]


# ---------- race recode: "Non-Hispanic X" must never become Hispanic --------
def test_race_recode_prefix_logic():
    import importlib
    std = importlib.import_module("01_build_cohort").standardize_real_seer
    n = 6
    df = pd.DataFrame({
        "patient_id": range(n), "age_dx": ["45 years"] * n, "sex": ["Male"] * n,
        "race_eth": ["Non-Hispanic White", "Non-Hispanic Black",
                     "Hispanic (All Races)", "Non-Hispanic Asian or Pacific Islander",
                     "Non-Hispanic American Indian/Alaska Native", "Non-Hispanic Unknown Race"],
        "year_dx": [2015] * n, "primary_site": ["C18.7-Sigmoid colon"] * n,
        "histology_icdo3": ["8140"] * n, "grade": ["2"] * n,
        "summary_stage": ["Localized only"] * n, "tumor_size_mm": ["030"] * n,
        "nodes_examined": ["12", "98", "97", "99", "05", "00"],
        "nodes_positive": ["01", "98", "97", "99", "00", "00"],
        "cea": ["CEA positive/elevated"] * n, "surgery": ["30"] * n,
        "radiation": ["None/Unknown"] * n, "chemo": ["Yes"] * n,
        "survival_months": ["0012"] * n,
        "cod_cancer": ["Alive or dead of other cause"] * n,
        "vital_status": ["Alive"] * n,
    })
    out = std(df)
    assert list(out.race_eth) == ["White", "Black", "Hispanic",
                                  "Asian/Pacific Islander", "Other/Unknown",
                                  "Other/Unknown"]
    # node special codes: 98 -> 0 (not examined); 97/99 -> NaN (count unknown)
    assert list(out.nodes_examined[[0, 1]]) == [12, 0]
    assert np.isnan(out.nodes_examined[2]) and np.isnan(out.nodes_examined[3])
    assert out.nodes_positive[1] == 0 and np.isnan(out.nodes_positive[2])
