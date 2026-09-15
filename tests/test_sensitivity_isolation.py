"""
Execution-safety tests for the prespecified sensitivity analyses.

These tests prove four things:
  1. with no sensitivity selected, every path is exactly what it was before
     the sensitivity layer existed (primary reproducibility is untouched);
  2. a sensitivity run cannot resolve to any primary path;
  3. each filter removes exactly the rows its protocol definition names, and
     nothing else;
  4. an unsupported sensitivity name hard-fails rather than improvising.

config.py reads the environment at import time, so each case runs in a
fresh subprocess. That is deliberate: it tests the real import path rather
than a reloaded module.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _probe(env_extra: dict, expr: str):
    """Import config in a subprocess with env_extra set; return (rc, out)."""
    import os

    env = dict(os.environ)
    env.pop("EOCRC_SENSITIVITY", None)
    env.update(env_extra)
    code = (
        "import sys, json; sys.path.insert(0, r'%s'); import config; "
        "print(json.dumps(%s))" % (SRC, expr)
    )
    proc = subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True)
    return proc


PATH_EXPR = ("dict(results=str(config.RESULTS), figures=str(config.FIGURES), "
             "cohort=str(config.COHORT_FILE), preds=str(config.PREDS), "
             "models=str(config.MODELS), mode=config.DATA_MODE, "
             "sensitivity=config.SENSITIVITY, "
             "primary_cohort=str(config.PRIMARY_COHORT_FILE))")


@pytest.fixture(scope="module")
def primary_paths():
    proc = _probe({}, PATH_EXPR)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# ---------------------------------------------------------------- 1. primary
def test_no_sensitivity_preserves_primary_paths(primary_paths):
    """Unset EOCRC_SENSITIVITY must reproduce the original layout exactly."""
    p = primary_paths
    base = p["mode"]
    assert p["sensitivity"] is None
    assert base in ("seer", "synthetic")
    assert p["results"] == str(ROOT / "results" / base)
    assert p["figures"] == str(ROOT / "figures" / base)
    assert p["cohort"] == str(ROOT / "data" / "processed" / f"cohort_{base}.parquet")
    assert p["preds"] == str(ROOT / "results" / base / "preds")
    assert p["models"] == str(ROOT / "results" / base / "models")
    assert p["cohort"] == p["primary_cohort"]
    assert "sensitivities" not in p["results"]
    assert "sensitivities" not in p["figures"]
    assert "sensitivities" not in p["cohort"]


def test_empty_sensitivity_string_is_treated_as_unset(primary_paths):
    proc = _probe({"EOCRC_SENSITIVITY": "   "}, PATH_EXPR)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == primary_paths


# ------------------------------------------------------------- 2. isolation
@pytest.mark.parametrize("mode", ["exclude_rectal", "exclude_2019"])
def test_sensitivity_paths_never_equal_primary(mode, primary_paths):
    proc = _probe({"EOCRC_SENSITIVITY": mode}, PATH_EXPR)
    assert proc.returncode == 0, proc.stderr
    s = json.loads(proc.stdout)

    assert s["sensitivity"] == mode
    assert s["mode"].endswith(f"_{mode}")

    for key in ("results", "figures", "cohort", "preds", "models"):
        assert s[key] != primary_paths[key], f"{key} collides with primary"

    # The primary cohort must remain addressable and unchanged, because the
    # builder reads it as input.
    assert s["primary_cohort"] == primary_paths["primary_cohort"]

    # Sensitivity outputs live under an explicitly namespaced directory.
    assert "sensitivities" in s["results"]
    assert "sensitivities" in s["figures"]
    assert "sensitivities" in s["cohort"]

    # Nothing may be written inside the primary results/figures trees.
    assert not s["results"].startswith(primary_paths["results"])
    assert not s["figures"].startswith(primary_paths["figures"])


# ---------------------------------------------------------- 3. filter logic
def _toy_cohort():
    return pd.DataFrame({
        "patient_id": range(1, 11),
        "site_group": ["Rectum", "Left colon", "Right colon", "Rectum",
                       "Colon, NOS/overlapping", "Left colon", "Rectum",
                       "Right colon", "Left colon", "Rectum"],
        "year_dx": [2010, 2013, 2016, 2017, 2018, 2019, 2019, 2015, 2019, 2012],
        "eo_group": ["EO", "AO"] * 5,
        "split": ["train"] * 3 + ["test"] * 3 + ["train", "train", "test", "train"],
        "css_event": [0, 1] * 5,
        "data_mode": ["seer"] * 10,
    })


def _load_filters():
    sys.path.insert(0, str(SRC))
    import importlib
    return importlib.import_module("08_make_sensitivity_cohort")


def test_exclude_rectal_removes_only_rectum():
    mod = _load_filters()
    df = _toy_cohort()
    out, rule = mod.filter_exclude_rectal(df)

    assert rule == 'site_group != "Rectum"'
    assert (out.site_group != "Rectum").all()
    # every non-rectal row survives, in original order
    expected = df[df.site_group != "Rectum"]
    pd.testing.assert_frame_equal(out, expected)
    # nothing other than site_group decided membership
    removed = df[~df.patient_id.isin(out.patient_id)]
    assert set(removed.site_group.unique()) == {"Rectum"}


def test_exclude_2019_removes_only_2019():
    mod = _load_filters()
    df = _toy_cohort()
    out, rule = mod.filter_exclude_2019(df)

    assert rule == "year_dx != 2019"
    assert (out.year_dx != 2019).all()
    expected = df[df.year_dx != 2019]
    pd.testing.assert_frame_equal(out, expected)
    removed = df[~df.patient_id.isin(out.patient_id)]
    assert set(removed.year_dx.unique()) == {2019}
    # training window is untouched: 2010-2016 rows all survive
    assert (out.year_dx <= 2016).sum() == (df.year_dx <= 2016).sum()


def test_filters_do_not_mutate_input():
    mod = _load_filters()
    df = _toy_cohort()
    before = df.copy()
    mod.filter_exclude_rectal(df)
    mod.filter_exclude_2019(df)
    pd.testing.assert_frame_equal(df, before)


def test_filter_table_matches_allowlist():
    """The FILTERS table and config's allow-list must never drift apart."""
    mod = _load_filters()
    sys.path.insert(0, str(SRC))
    import config
    assert set(mod.FILTERS) == set(config.ALLOWED_SENSITIVITIES)


# ------------------------------------------------------------ 4. hard-fail
@pytest.mark.parametrize("bad", [
    "complete_case", "covid_extension", "stage1_3_postop",
    "EXCLUDE_RECTAL", "exclude-rectal", "exclude_rectal2", "seer",
    "../../etc", "",
])
def test_unsupported_sensitivity_hard_fails(bad):
    if bad.strip() == "":
        pytest.skip("empty string is covered by the unset-equivalence test")
    proc = _probe({"EOCRC_SENSITIVITY": bad}, "dict(x=1)")
    assert proc.returncode != 0, f"{bad!r} should have hard-failed"
    assert "Unsupported EOCRC_SENSITIVITY" in (proc.stderr + proc.stdout)


@pytest.mark.parametrize("padded", ["exclude_rectal ", " exclude_2019",
                                    "\texclude_rectal\n"])
def test_surrounding_whitespace_is_tolerated(padded):
    """A stray space from a shell copy-paste is stripped, not improvised on:
    the stripped value must still be an exact allow-list match."""
    proc = _probe({"EOCRC_SENSITIVITY": padded},
                  "dict(s=config.SENSITIVITY)")
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["s"] == padded.strip()


def test_deferred_sensitivities_are_not_in_allowlist():
    """Sensitivities needing a post-registration definition stay out until
    that definition is recorded."""
    sys.path.insert(0, str(SRC))
    import config
    for name in ("complete_case", "covid_extension", "stage1_3_postop"):
        assert name not in config.ALLOWED_SENSITIVITIES
