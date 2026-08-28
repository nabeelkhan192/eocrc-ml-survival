"""
Generate a synthetic, SEER-*like* colorectal cancer dataset.

Purpose: let the entire pipeline run end-to-end (and be debugged) BEFORE
SEER access is approved. The data are fabricated with plausible clinical
effect directions (stage dominates, nodes/CEA/grade matter, surgery helps).
Nothing here is real; no scientific conclusion may be drawn from it.
"""
import numpy as np
import pandas as pd

from config import SYNTH_FILE, SEED

rng = np.random.default_rng(SEED)
N = 24_000
STUDY_CUTOFF_YEAR = 2022  # mimics a Nov-submission follow-up cutoff


def _choice(options, p, size):
    return rng.choice(options, size=size, p=p)


def main() -> None:
    # ------------------------------------------------ demographics & tumor
    eo = rng.random(N) < 0.35  # oversample early-onset for pipeline testing
    age = np.where(
        eo,
        rng.integers(18, 50, N),
        np.clip(rng.normal(66, 9, N).astype(int), 50, 84),
    )
    sex = _choice(["Male", "Female"], [0.53, 0.47], N)
    race = _choice(
        ["White", "Black", "Hispanic", "Asian/Pacific Islander", "Other/Unknown"],
        [0.60, 0.12, 0.16, 0.09, 0.03], N,
    )
    year = rng.integers(2010, 2020, N)
    site = np.where(
        rng.random(N) < np.where(eo, 0.62, 0.45),      # EO skews left/rectal
        _choice(["Left colon", "Rectum"], [0.45, 0.55], N),
        "Right colon",
    )
    site = np.where(rng.random(N) < 0.03, "Colon, NOS/overlapping", site)
    histology = _choice(
        ["Adenocarcinoma", "Mucinous", "Signet ring"],
        [0.86, 0.10, 0.04], N,
    )
    grade = _choice(
        ["Grade I", "Grade II", "Grade III", "Grade IV", "Unknown"],
        [0.08, 0.55, 0.25, 0.04, 0.08], N,
    )
    # EO presents at later stage (a well-described pattern)
    stage = np.where(
        eo,
        _choice(["Localized", "Regional", "Distant"], [0.28, 0.44, 0.28], N),
        _choice(["Localized", "Regional", "Distant"], [0.38, 0.40, 0.22], N),
    )
    size_mm = np.round(np.clip(rng.normal(45, 22, N), 2, 180), 0)
    size_mm[rng.random(N) < 0.12] = np.nan
    nodes_ex = np.clip(rng.poisson(15, N), 0, 60)
    base_pos = {"Localized": 0.02, "Regional": 0.25, "Distant": 0.35}
    p_pos = np.array([base_pos[s] for s in stage])
    nodes_pos = rng.binomial(nodes_ex, p_pos)
    cea = np.where(
        rng.random(N) < 0.25, "Unknown",
        np.where(rng.random(N) < np.where(stage == "Distant", 0.75, 0.35),
                 "Elevated", "Normal"),
    )
    surgery = np.where(
        stage == "Distant",
        _choice(["Yes", "No"], [0.55, 0.45], N),
        _choice(["Yes", "No"], [0.95, 0.05], N),
    )
    surgery = np.where(rng.random(N) < 0.02, "Unknown", surgery)
    chemo = np.where(
        stage == "Localized",
        _choice(["Yes", "No/Unknown"], [0.12, 0.88], N),
        _choice(["Yes", "No/Unknown"], [0.70, 0.30], N),
    )
    radiation = np.where(
        site == "Rectum",
        _choice(["Yes", "No/Unknown"], [0.55, 0.45], N),
        _choice(["Yes", "No/Unknown"], [0.05, 0.95], N),
    )

    # ------------------------------------------------ survival generation
    lp = (
        np.select(
            [stage == "Localized", stage == "Regional", stage == "Distant"],
            [0.0, 0.95, 2.30],
        )
        + np.select(
            [grade == "Grade III", grade == "Grade IV"], [0.35, 0.65], 0.0
        )
        + np.where(histology == "Signet ring", 0.55, 0.0)
        + np.where(histology == "Mucinous", 0.12, 0.0)
        + np.where(cea == "Elevated", 0.45, 0.0)
        + 1.10 * (nodes_pos / np.maximum(nodes_ex, 1))
        + 0.003 * np.nan_to_num(size_mm, nan=45.0)
        - 0.85 * (surgery == "Yes")
        - 0.15 * (chemo == "Yes")
        + 0.004 * (age - 60)
    )
    base_median = 220.0  # months, for lp == 0
    lam_css = np.log(2) / base_median * np.exp(lp)
    t_css = rng.exponential(1.0 / lam_css)

    lam_other = 0.00025 * np.exp(0.085 * (age - 50))  # background mortality
    t_other = rng.exponential(1.0 / np.maximum(lam_other, 1e-9))

    admin_cens = (STUDY_CUTOFF_YEAR - year) * 12 + rng.uniform(0, 12, N)
    ltfu = rng.uniform(6, 200, N)
    t_cens = np.minimum(admin_cens, ltfu)

    t_obs = np.minimum.reduce([t_css, t_other, t_cens])
    css_event = (t_obs == t_css).astype(int)
    os_event = ((t_obs == t_css) | (t_obs == t_other)).astype(int)
    surv_months = np.maximum(np.round(t_obs), 1).astype(int)

    df = pd.DataFrame(
        {
            "patient_id": np.arange(1, N + 1),
            "age_dx": age,
            "sex": sex,
            "race_eth": race,
            "year_dx": year,
            "site_group": site,
            "histology": histology,
            "grade": grade,
            "summary_stage": stage,
            "tumor_size_mm": size_mm,
            "nodes_examined": nodes_ex,
            "nodes_positive": nodes_pos,
            "cea": cea,
            "surgery": surgery,
            "chemo": chemo,
            "radiation": radiation,
            "survival_months": surv_months,
            "css_event": css_event,
            "os_event": os_event,
        }
    )
    SYNTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SYNTH_FILE, index=False)
    print(f"Synthetic dataset written: {SYNTH_FILE}  (n={len(df):,})")
    print(df.groupby(df.age_dx <= 49)["css_event"].agg(["count", "mean"]).rename(
        index={True: "EO (<=49)", False: "AO (50-84)"}))


if __name__ == "__main__":
    main()
