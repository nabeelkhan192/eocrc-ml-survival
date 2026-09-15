"""
Build a prespecified sensitivity cohort by filtering the PRIMARY analysis
cohort (protocol S8 items 2-6: "cohort-filter re-runs of the identical
pipeline (01->07); none introduces new modeling choices").

This script deliberately does NOT re-run 01_build_cohort.py. Cohort
construction - site mapping, histology restriction, staging, node-code
handling, outcome derivation, train/test split - is frozen and was executed
once for the primary analysis. A sensitivity analysis removes rows from that
frozen cohort; it does not rebuild it. Reading the primary parquet and
writing a separate file means 01_build_cohort.py is never touched and the
primary cohort file is never reopened for writing.

Supported filters (closed allow-list; see config.ALLOWED_SENSITIVITIES):

  exclude_rectal   site_group != "Rectum"
                   Rectum is defined by the frozen map_site() in
                   01_build_cohort.py as C19.9 rectosigmoid + C20.9 rectum,
                   matching protocol section 4 ("rectum C19.9/C20.9"). No
                   redefinition is applied here.

  exclude_2019     year_dx != 2019
                   Protocol S8 item (4), "excluding 2019 diagnoses (short
                   follow-up)". The training window is unchanged at
                   2010-2016; the temporal test window becomes 2017-2018.

Not implemented, by design: complete_case, covid_extension,
stage1_3_postop. Each requires an operational definition that the frozen
protocol does not fully determine. config.py hard-fails on those names
rather than improvising one.

Usage
-----
    EOCRC_SENSITIVITY=exclude_rectal python src/08_make_sensitivity_cohort.py

Writes data/processed/sensitivities/cohort_<mode>.parquet and
results/sensitivities/<mode>/sensitivity_cohort_flow.csv, then stops. Run
02-07 afterwards with the same environment variable set.
"""
import sys

import pandas as pd

from config import (
    SENSITIVITY, ALLOWED_SENSITIVITIES, PRIMARY_COHORT_FILE, COHORT_FILE,
    RESULTS, DATA_MODE, BASE_MODE,
)


def filter_exclude_rectal(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Drop rectal primaries as defined by the frozen map_site()."""
    mask = df["site_group"] != "Rectum"
    return df[mask], 'site_group != "Rectum"'


def filter_exclude_2019(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Drop 2019 diagnoses (protocol S8 item 4, short follow-up)."""
    mask = df["year_dx"] != 2019
    return df[mask], "year_dx != 2019"


FILTERS = {
    "exclude_rectal": filter_exclude_rectal,
    "exclude_2019": filter_exclude_2019,
}


def main() -> None:
    if SENSITIVITY is None:
        raise SystemExit(
            "No sensitivity selected. Set EOCRC_SENSITIVITY to one of: "
            + ", ".join(ALLOWED_SENSITIVITIES))

    # Defensive: config already validated the name, but the filter table and
    # the allow-list must never drift apart.
    if SENSITIVITY not in FILTERS:
        raise SystemExit(
            f"No filter implemented for {SENSITIVITY!r}. The allow-list in "
            "config.py and the FILTERS table in this file disagree - fix "
            "both before running.")

    if not PRIMARY_COHORT_FILE.exists():
        raise SystemExit(
            f"Primary cohort not found at {PRIMARY_COHORT_FILE}. Run the "
            "primary pipeline (01_build_cohort.py) first; a sensitivity "
            "analysis filters the primary cohort, it does not rebuild it.")

    if COHORT_FILE.resolve() == PRIMARY_COHORT_FILE.resolve():
        raise SystemExit(
            "REFUSING TO RUN: the sensitivity cohort path resolves to the "
            "primary cohort file. This would overwrite primary data.")

    if COHORT_FILE.exists() and "--force" not in sys.argv:
        raise SystemExit(
            f"{COHORT_FILE} already exists. Delete it or pass --force if you "
            "intend to rebuild this sensitivity cohort.")

    df = pd.read_parquet(PRIMARY_COHORT_FILE)
    n_before = len(df)

    out, rule = FILTERS[SENSITIVITY](df)
    out = out.copy()
    out["data_mode"] = DATA_MODE
    n_after = len(out)

    flow = pd.DataFrame(
        [
            {"step": f"Primary analysis cohort ({BASE_MODE})", "n": n_before},
            {"step": f"After sensitivity filter: {rule}", "n": n_after},
            {"step": "Removed by filter", "n": n_before - n_after},
        ]
    )
    flow.to_csv(RESULTS / "sensitivity_cohort_flow.csv", index=False)
    out.to_parquet(COHORT_FILE, index=False)

    print(f"\nSENSITIVITY: {SENSITIVITY}")
    print(f"  rule:      {rule}")
    print(f"  input:     {PRIMARY_COHORT_FILE}  (n={n_before:,})")
    print(f"  output:    {COHORT_FILE}  (n={n_after:,})")
    print(f"  removed:   {n_before - n_after:,}")
    print("\nGroup x split counts:")
    print(out.groupby(["eo_group", "split"]).size().unstack())
    print(f"\nWrote {RESULTS / 'sensitivity_cohort_flow.csv'}")
    print(
        "\nThe primary horizon is LOCKED at the value recorded in CHANGELOG "
        "v4.1.2. 02_descriptives.py recomputes follow-up adequacy on every "
        "run and may print the protocol S5 warning for this cohort; that "
        "warning MUST NOT be acted on for a sensitivity analysis. Changing "
        "the horizon per sensitivity would make the sensitivities "
        "incomparable with the primary result."
    )


if __name__ == "__main__":
    main()
