"""
Central configuration for the EO-CRC explainable-ML survival study.

>>> EDIT THIS FILE FIRST when you plug in real SEER data. <<<
Everything else in src/ reads from here.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_SYNTHETIC = ROOT / "data" / "synthetic"

# Your SEER*Stat case-listing export (CSV, exported WITH LABELS, not codes).
# Never commit this file. See data/README.md for the exact export recipe.
RAW_FILE = DATA_RAW / "seer_crc_export.csv"

# Synthetic stand-in so the whole pipeline runs before SEER access arrives.
SYNTH_FILE = DATA_SYNTHETIC / "synthetic_seer_like.csv"

# ------------------------------------------------------------- data mode
# Outputs are strictly separated so synthetic pipeline tests can never be
# confused with real-data results. DATA_MODE is decided once, here, from
# the presence of the real export.
DATA_MODE = "seer" if RAW_FILE.exists() else "synthetic"

RESULTS = ROOT / "results" / DATA_MODE
PREDS = RESULTS / "preds"
MODELS = RESULTS / "models"
FIGURES = ROOT / "figures" / DATA_MODE
COHORT_FILE = DATA_PROCESSED / f"cohort_{DATA_MODE}.parquet"

for _p in (DATA_PROCESSED, DATA_SYNTHETIC, RESULTS, PREDS, MODELS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- column map
# canonical_name -> LIST of candidate column headers in YOUR SEER*Stat
# export, coalesced left-to-right (first non-missing value wins). Lists are
# required because several SEER variables changed names/derivations across
# diagnosis years (CS era 2004-2015 vs 2016+ vs 2018+ SSDI era); mapping a
# single-era column silently blanks the other years (e.g., mapping only
# "CS tumor size (2004-2015)" leaves every 2016+ tumor size missing).
# The canonical names on the LEFT must not change; edit only the RIGHT side
# to match your export's headers, and delete candidates you did not export.
# Headers below were verified against the Nov 2025 Sub (2000-2023)
# SEER*Stat case-listing dictionary on 2026-08-19 (data/README.md).
# SEER*Stat exports missing values as "Blank(s)" (or a space): the loader
# treats both as missing when coalescing.
COLUMN_MAP = {
    "patient_id":       ["Patient ID"],
    "age_dx":           ["Age recode with single ages and 85+"],
    "sex":              ["Sex"],
    "race_eth":         ["Race and origin recode (NHW, NHB, NHAIAN, NHAPI, Hispanic)"],
    "year_dx":          ["Year of diagnosis"],
    "primary_site":     ["Primary Site - labeled"],
    "histology_icdo3":  ["Histologic Type ICD-O-3"],
    # 2018+ grade: pathological preferred, clinical as fallback (SEER 2018+
    # codes 1-4 map to Grade I-IV; 9/A-D/H/L -> Unknown, see map_grade)
    "grade":            ["Grade Recode (thru 2017)",
                         "Grade Pathological (2018+)",
                         "Grade Clinical (2018+)"],
    "summary_stage":    ["Combined Summary Stage with Expanded Regional Codes (2004+)",
                         "Combined Summary Stage (2004+)"],
    "tumor_size_mm":    ["CS tumor size (2004-2015)",
                         "Tumor Size Summary (2016+)"],
    "nodes_examined":   ["Regional nodes examined (1988+)"],
    "nodes_positive":   ["Regional nodes positive (1988+)"],
    "cea":              ["CEA Pretreatment Interpretation Recode (2010+)"],
    "surgery":          ["RX Summ--Surg Prim Site (1998-2022)",
                         "RX Summ--Surg Prim Site (1998+)"],
    "radiation":        ["Radiation recode"],
    "chemo":            ["Chemotherapy recode (yes, no/unk)"],
    "survival_months":  ["Survival months"],
    "cod_cancer":       ["SEER cause-specific death classification"],
    "vital_status":     ["Vital status recode (study cutoff used)"],
}

# ---------------------------------------------------------------- cohort rules
MIN_AGE, MAX_AGE = 18, 84
EO_MAX_AGE = 49                      # early-onset: 18-49; average-onset: 50-84
TRAIN_YEARS = (2010, 2016)           # temporal validation design
TEST_YEARS = (2017, 2019)
MIN_SURVIVAL_MONTHS = 1              # exclude 0-month records (DCO-like noise)

# ---------------------------------------------------------------- modeling
HORIZON_MONTHS = 60                  # primary fixed horizon (see protocol S5:
                                     # the follow-up adequacy rule may flip
                                     # this to 36 BEFORE test unblinding)
TD_AUC_TIMES = [36, 60]              # time-dependent AUC evaluation points
SEED = 2026
BOOTSTRAP_N = 200                    # bootstrap iterations for CIs (paired)
DCA_THRESHOLDS = (0.05, 0.60, 0.01)  # decision-curve range: start, stop, step
XGB_DEPTH_GRID = [3, 4, 6]           # tuned on a seeded internal 80/20 split
                                     # within the training window only

# Feature sets used to build the design matrix (post-standardization names).
NUMERIC_FEATURES = [
    "age_dx", "tumor_size_mm", "nodes_examined", "nodes_positive",
    "node_ratio", "year_dx",
]
# Row-local indicator columns (derived per patient; involve no dataset-level
# statistics, so they are computed in 01_build_cohort without leakage).
INDICATOR_FEATURES = ["tumor_size_missing", "nodes_not_examined"]
CATEGORICAL_FEATURES = [
    "sex", "race_eth", "site_group", "histology", "grade",
    "summary_stage", "cea", "surgery", "chemo", "radiation",
]
STAGE_ONLY_FEATURES = ["summary_stage"]   # the honest clinical baseline
