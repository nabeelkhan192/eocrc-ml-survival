"""
Build the analysis cohort.

Priority: if a real SEER export exists at config.RAW_FILE, use it
(after renaming via COLUMN_MAP and standardizing values). Otherwise fall
back to the synthetic dataset so the pipeline stays runnable.

Outputs
-------
data/processed/cohort.parquet   analysis-ready cohort
results/cohort_flow.csv         STROBE-style exclusion flow counts
"""
import numpy as np
import pandas as pd

from config import (
    RAW_FILE, SYNTH_FILE, COHORT_FILE, COLUMN_MAP, RESULTS, DATA_MODE,
    MIN_AGE, MAX_AGE, EO_MAX_AGE, TRAIN_YEARS, TEST_YEARS,
    MIN_SURVIVAL_MONTHS,
)

# ---------------------------------------------------------------------------
# Value standardization for REAL SEER exports (export with LABELS, not codes).
# Unmapped values fall through to "Unknown"/NaN and are printed for audit —
# review that audit carefully the first time you run on real data.
# ---------------------------------------------------------------------------

ADENO_HISTOLOGIES = {
    # ICD-O-3 adenocarcinoma family used in most EO-CRC literature
    8140, 8141, 8143, 8144, 8145, 8147, 8210, 8211, 8220, 8221,
    8255, 8260, 8261, 8262, 8263, 8323, 8480, 8481, 8490,
}
MUCINOUS = {8480, 8481}
SIGNET = {8490}


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def map_site(site: pd.Series) -> np.ndarray:
    """ICD-O-3 primary site label -> anatomic group.

    Right colon: C18.0 cecum, C18.2 ascending, C18.3 hepatic flexure,
                 C18.4 transverse.
    Left colon:  C18.5 splenic flexure, C18.6 descending, C18.7 sigmoid.
    Rectum:      C19.9 rectosigmoid, C20.9 rectum.
    C18.8 (overlapping) and C18.9 (colon, NOS) carry NO laterality in the
    source variable, so they are kept as an explicit category rather than
    silently assigned to a side.
    """
    site = site.astype(str)
    return np.select(
        [
            site.str.contains(r"C18\.0|C18\.2|C18\.3|C18\.4|Cecum|Ascending|"
                              r"Hepatic|Transverse", case=False, na=False),
            site.str.contains(r"C18\.5|C18\.6|C18\.7|Splenic|Descending|"
                              r"Sigmoid colon", case=False, na=False),
            site.str.contains(r"C19|C20|Rectos|Rectum", case=False, na=False),
            site.str.contains(r"C18\.8|C18\.9|Overlapping|Colon, NOS|"
                              r"Large intestine, NOS", case=False, na=False),
        ],
        ["Right colon", "Left colon", "Rectum", "Colon, NOS/overlapping"],
        default="Colon, NOS/overlapping",   # unrecognized -> audited, not sided
    )


GRADE_LABELS = {
    # explicit normalized-label mapping (mutually exclusive by construction)
    "well differentiated; grade i": "Grade I",
    "grade i": "Grade I", "1": "Grade I",
    "moderately differentiated; grade ii": "Grade II",
    "grade ii": "Grade II", "2": "Grade II",
    "poorly differentiated; grade iii": "Grade III",
    "grade iii": "Grade III", "3": "Grade III",
    "undifferentiated; anaplastic; grade iv": "Grade IV",
    "grade iv": "Grade IV", "4": "Grade IV",
    # 2018+ Derived Summary Grade labels
    "well differentiated": "Grade I", "moderately differentiated": "Grade II",
    "poorly differentiated": "Grade III", "undifferentiated": "Grade IV",
    "anaplastic": "Grade IV",
    # SEER 2018+ grade codes as labels
    "g1": "Grade I", "g2": "Grade II", "g3": "Grade III", "g4": "Grade IV",
    # 2018+ SEER grade codes 9 (unknown), A-D (alternative 4-tier used by
    # non-CRC schemas), H/L (two-tier high/low: not convertible to a 4-tier
    # grade without assumption) are deliberately NOT mapped -> Unknown.
}


def map_grade(grade: pd.Series) -> np.ndarray:
    """Normalize label, then exact-dictionary lookup; anything else (blank,
    'Unknown', 'Not applicable', 'B/T-cell', 9, etc.) -> 'Unknown'.
    Exact matching means 'Grade I' can never be triggered by 'Grade IV'."""
    norm = (grade.astype(str).str.strip().str.lower()
            .str.replace(r"\s+", " ", regex=True))
    return norm.map(GRADE_LABELS).fillna("Unknown").values


def map_surgery(surg: pd.Series) -> np.ndarray:
    """RX Summ--Surg Prim Site (labels or codes) -> Yes / No / Unknown.

    Code 00 or 'None' = No; codes 10-90 (any surgical procedure) = Yes;
    98 'not applicable'/'site-specific NA', 99 'unknown', blank -> Unknown.
    Unrecognized -> Unknown (never silently 'Yes')."""
    raw = surg.astype(str).str.strip()
    low = raw.str.lower()
    code = pd.to_numeric(raw.str.extract(r"^(\d{1,2})")[0], errors="coerce")
    is_no = (code == 0) | low.str.contains(r"^none|no surgery|not performed",
                                            regex=True, na=False)
    is_unknown = (code.isin([98, 99]) | low.isin(["", "nan", "unknown", "blank"])
                  | low.str.contains(r"unknown|not applicable|not documented",
                                     regex=True, na=False))
    is_yes = (~is_no & ~is_unknown
              & (code.between(10, 90) | low.str.contains(
                  r"resection|colectomy|excision|surgery, nos|local tumor|"
                  r"proctectomy|proctocolectomy|hemicolectomy|polypectomy|"
                  r"^yes", regex=True, na=False)))
    return np.select([is_no, is_yes], ["No", "Yes"], default="Unknown")


def standardize_real_seer(df: pd.DataFrame) -> pd.DataFrame:
    """Map a labeled SEER*Stat export onto the canonical schema."""
    out = pd.DataFrame()
    out["patient_id"] = df["patient_id"]

    # Age: "Age recode with single ages and 85+" exports like "43 years"
    out["age_dx"] = _num(df["age_dx"].astype(str).str.extract(r"(\d+)")[0])

    out["sex"] = df["sex"].astype(str).str.strip()

    # SEER labels are "Non-Hispanic White", "Hispanic (All Races)", etc.
    # "Non-Hispanic ..." contains the substring "Hispanic", so Hispanic must
    # be tested as a prefix, never as a substring.
    race = df["race_eth"].astype(str).str.strip()
    is_hisp = race.str.match(r"^Hispanic", case=False)
    is_nh = race.str.match(r"^Non-Hispanic", case=False)
    out["race_eth"] = np.select(
        [
            is_hisp,
            is_nh & race.str.contains("White", case=False, na=False),
            is_nh & race.str.contains("Black", case=False, na=False),
            is_nh & race.str.contains("Asian|Pacific", case=False, na=False),
        ],
        ["Hispanic", "White", "Black", "Asian/Pacific Islander"],
        default="Other/Unknown",   # NH AI/AN, NH Unknown race
    )

    out["year_dx"] = _num(df["year_dx"])

    # Primary site label -> site_group; appendix (C18.1) must be excluded
    site = df["primary_site"].astype(str)
    out["_appendix"] = site.str.contains("C18.1|Appendix", case=False, na=False)
    # keep only C18.x, C19.9, C20.9 (e.g. C26.0 "Intestinal tract, NOS" is
    # not colorectal and is excluded, not silently grouped)
    out["_colorectal"] = site.str.match(r"^C(18\.\d|19\.9|20\.9)", case=False)
    out["site_group"] = map_site(site)

    hist = _num(df["histology_icdo3"])
    out["_adeno"] = hist.isin(ADENO_HISTOLOGIES)
    out["histology"] = np.select(
        [hist.isin(SIGNET), hist.isin(MUCINOUS)],
        ["Signet ring", "Mucinous"],
        default="Adenocarcinoma",
    )

    out["grade"] = map_grade(df["grade"])

    stage = df["summary_stage"].astype(str)
    out["summary_stage"] = np.select(
        [
            stage.str.contains("Localized", case=False, na=False),
            stage.str.contains("Regional", case=False, na=False),
            stage.str.contains("Distant", case=False, na=False),
        ],
        ["Localized", "Regional", "Distant"],
        default="Unknown",
    )

    # CS tumor size: 989/990-999 style codes are non-size flags -> NaN
    size = _num(df["tumor_size_mm"])
    out["tumor_size_mm"] = size.where((size > 0) & (size < 989))

    # SEER special codes. Examined: 00-90 count; 95 (aspiration only),
    # 96/97 (nodes removed, number unknown) = examined, count unknown -> NaN
    # count (train-median imputed) but NOT "not examined"; 98 = no nodes
    # examined -> 0; 99 unknown -> NaN. Positive: 00-90 count; 95/97
    # positive, number unknown -> NaN; 98 no nodes examined -> 0; 99 -> NaN.
    ex = _num(df["nodes_examined"])
    out["nodes_examined"] = np.where(ex == 98, 0, ex.where(ex < 90))
    po = _num(df["nodes_positive"])
    out["nodes_positive"] = np.where(po == 98, 0, po.where(po < 90))

    cea = df["cea"].astype(str)
    out["cea"] = np.select(
        [
            cea.str.contains("negative|normal|within", case=False, na=False),
            cea.str.contains("positive|elevated", case=False, na=False),
        ],
        ["Normal", "Elevated"],
        default="Unknown",
    )

    out["surgery"] = map_surgery(df["surgery"])
    # Radiation and chemotherapy recodes are dichotomous IN SEER ITSELF
    # ("Yes" vs "No/Unknown" - the registry does not separate the two), so
    # the "No/Unknown" label is faithful to the source, not a collapse we
    # introduce. Documented in Limitations.
    out["radiation"] = np.where(
        df["radiation"].astype(str).str.contains("Beam|isotope|implant|radiation, NOS|Yes",
                                                 case=False, na=False),
        "Yes", "No/Unknown",
    )
    out["chemo"] = np.where(
        df["chemo"].astype(str).str.contains("Yes", case=False, na=False),
        "Yes", "No/Unknown",
    )

    out["survival_months"] = _num(df["survival_months"])

    cod = df["cod_cancer"].astype(str)
    out["css_event"] = cod.str.contains(
        "Dead (attributable to this cancer dx)", regex=False, na=False
    ).astype(int)
    out["os_event"] = df["vital_status"].astype(str).str.contains(
        "Dead", case=False, na=False).astype(int)

    # Audit anything that fell through to defaults
    for col in ["summary_stage", "grade", "cea", "surgery"]:
        unk = (out[col] == "Unknown").mean()
        print(f"  audit: {col:14s} Unknown share = {unk:5.1%}")
    nos = (out["site_group"] == "Colon, NOS/overlapping").mean()
    print(f"  audit: site_group      Colon NOS/overlapping share = {nos:5.1%}")
    return out


def apply_inclusion(df: pd.DataFrame, real: bool) -> tuple[pd.DataFrame, list]:
    flow = [("Records in source extract", len(df))]

    if real:
        df = df[df.pop("_colorectal")]
        flow.append(("Colorectal primary site (C18.x, C19.9, C20.9)", len(df)))
        df = df[~df.pop("_appendix")]
        flow.append(("After excluding appendiceal primaries (C18.1)", len(df)))
        df = df[df.pop("_adeno")]
        flow.append(("After restricting to adenocarcinoma histologies", len(df)))

    df = df[df["age_dx"].between(MIN_AGE, MAX_AGE)]
    flow.append((f"Age {MIN_AGE}-{MAX_AGE} at diagnosis", len(df)))

    df = df[df["year_dx"].between(TRAIN_YEARS[0], TEST_YEARS[1])]
    flow.append((f"Diagnosis years {TRAIN_YEARS[0]}-{TEST_YEARS[1]}", len(df)))

    df = df[df["summary_stage"].isin(["Localized", "Regional", "Distant"])]
    flow.append(("Known summary stage", len(df)))

    df = df[df["survival_months"].notna()
            & (df["survival_months"] >= MIN_SURVIVAL_MONTHS)]
    flow.append((f"Survival follow-up >= {MIN_SURVIVAL_MONTHS} month", len(df)))

    return df.copy(), flow


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    """Row-local derivations only.

    NO dataset-level statistic (median, mean, vocabulary) is computed here:
    all data-dependent preprocessing lives in utils_features.FeatureBuilder,
    which is fitted on training-window data only. Everything below uses
    information from the same patient row, so it cannot leak across splits.
    """
    df["eo_group"] = np.where(df["age_dx"] <= EO_MAX_AGE, "EO", "AO")

    # Node ratio is defined only when nodes were actually examined. Zero or
    # missing nodes_examined means "not examined", which is NOT the same as
    # a ratio of 0 - it becomes missing plus an explicit indicator, and the
    # missing ratio is imputed later by the train-fitted FeatureBuilder.
    examined = df["nodes_examined"]                     # NaN = count unknown
    df["nodes_not_examined"] = (examined.fillna(-1) == 0).astype(int)
    df["node_ratio"] = np.where(
        (examined > 0) & df["nodes_positive"].notna(),
        (df["nodes_positive"] / examined.replace(0, np.nan)).clip(0, 1),
        np.nan,
    )
    # unknown counts stay NaN here; FeatureBuilder imputes train medians

    # Missingness indicator is row-local; the imputation VALUE is not, so
    # imputation happens in FeatureBuilder (train medians only).
    df["tumor_size_missing"] = df["tumor_size_mm"].isna().astype(int)

    df["split"] = np.where(
        df["year_dx"] <= TRAIN_YEARS[1], "train", "test")
    df["data_mode"] = DATA_MODE
    return df


def main() -> None:
    if RAW_FILE.exists():
        print(f"Real SEER export found: {RAW_FILE}")
        raw = pd.read_csv(RAW_FILE, low_memory=False)
        df_in, missing = pd.DataFrame(), []
        for canon, candidates in COLUMN_MAP.items():
            present = [c for c in candidates if c in raw.columns]
            if not present:
                missing.append(f"{canon}: none of {candidates}")
                continue
            # Coalesce left-to-right across era-specific source columns and
            # print a coverage audit (share of non-missing after coalescing).
            def _clean(c):
                c = c.astype(str).str.strip()
                return c.mask(c.isin(["", "nan", "Blank(s)"]))
            col = _clean(raw[present[0]])
            for extra in present[1:]:
                col = col.where(col.notna(), _clean(raw[extra]))
            df_in[canon] = col
            print(f"  map: {canon:16s} <- {present}  "
                  f"non-missing={col.notna().mean():5.1%}")
        if missing:
            raise SystemExit(
                "These COLUMN_MAP entries matched no header in your export - "
                "fix src/config.py:\n  " + "\n  ".join(missing))
        df = standardize_real_seer(df_in)
        real = True
    else:
        print(f"No real export at {RAW_FILE}; using SYNTHETIC data "
              f"({SYNTH_FILE}). Run src/00 first if this file is missing.")
        df = pd.read_csv(SYNTH_FILE)
        real = False

    print(f"\nDATA MODE: {DATA_MODE.upper()}")
    df, flow = apply_inclusion(df, real=real)
    df = derive_features(df)

    pd.DataFrame(flow, columns=["step", "n"]).to_csv(
        RESULTS / "cohort_flow.csv", index=False)
    df.to_parquet(COHORT_FILE, index=False)

    print("\nCohort flow:")
    for step, n in flow:
        print(f"  {n:>8,}  {step}")
    print("\nGroup x split counts:")
    print(df.groupby(["eo_group", "split"]).size().unstack())
    # (No outcome statistics are printed at this stage: cohort construction
    #  is outcome-blind; follow-up structure is reviewed in 02.)
    print(f"\nSaved: {COHORT_FILE}")


if __name__ == "__main__":
    main()
