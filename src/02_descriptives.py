"""Table 1 (EO vs AO) and Kaplan-Meier cancer-specific survival curves."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from lifelines import KaplanMeierFitter

import numpy as np

from config import (
    RESULTS, FIGURES, NUMERIC_FEATURES, CATEGORICAL_FEATURES, HORIZON_MONTHS,
)
from utils_features import load_cohort, watermark
from estimands import event_free_short_followup_share, ADEQUACY_TRIGGER


def table1(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in NUMERIC_FEATURES:
        for g in ["EO", "AO"]:
            s = df.loc[df.eo_group == g, col]
            rows.append([col, "median [IQR]", g,
                         f"{s.median():.1f} [{s.quantile(.25):.1f}-"
                         f"{s.quantile(.75):.1f}]"])
    for col in CATEGORICAL_FEATURES:
        for level, sub in df.groupby(col, observed=True):
            for g in ["EO", "AO"]:
                n_g = (df.eo_group == g).sum()
                n = ((sub.eo_group == g)).sum()
                rows.append([col, str(level), g, f"{n:,} ({n / n_g:.1%})"])
    out = (pd.DataFrame(rows, columns=["variable", "level", "group", "value"])
           .pivot_table(index=["variable", "level"], columns="group",
                        values="value", aggfunc="first"))
    return out


def followup_adequacy(df: pd.DataFrame) -> pd.DataFrame:
    """Protocol S5 follow-up adequacy rule - computed BEFORE any model is
    evaluated, from follow-up structure alone.

    For each group x split: reverse-Kaplan-Meier median follow-up, and the
    share of event-free patients whose follow-up is shorter than the primary
    horizon. If the test window cannot observe the 60-month horizon without
    event-enriched selection, the prespecified rule flips the primary
    horizon for calibration/DCA to 36 months (recorded in the CHANGELOG
    before test-window performance is unblinded).
    """
    kmf = KaplanMeierFitter()
    rows = []
    for (g, sp), sub in df.groupby(["eo_group", "split"]):
        kmf.fit(sub.survival_months, 1 - sub.css_event)  # reverse KM
        med = kmf.median_survival_time_
        # DENOMINATOR = event-free patients only (protocol S5, exact wording)
        short = event_free_short_followup_share(
            sub.survival_months, sub.css_event, HORIZON_MONTHS)
        n_ef = int((sub.css_event == 0).sum())
        observable = ((sub.survival_months >= HORIZON_MONTHS)
                      | ((sub.css_event == 1)
                         & (sub.survival_months <= HORIZON_MONTHS))).mean()
        rows.append(dict(group=g, split=sp, n=len(sub), n_event_free=n_ef,
                         reverse_km_median_followup_months=round(float(med), 1),
                         share_of_event_free_with_followup_lt_horizon=round(float(short), 3),
                         share_horizon_observable=round(float(observable), 3)))
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "followup_adequacy.csv", index=False)
    print("\nFollow-up adequacy (protocol S5 rule - review BEFORE modeling):")
    print(out.to_string(index=False))
    flag = out[(out.split == "test")
               & (out.share_of_event_free_with_followup_lt_horizon
                  > ADEQUACY_TRIGGER)]
    if len(flag):
        print(f"  WARNING: >{ADEQUACY_TRIGGER:.0%} of EVENT-FREE test "
              f"patients have follow-up "
              f"< {HORIZON_MONTHS} months in {list(flag.group)}. Per protocol "
              f"S5, make 36 months the primary horizon for calibration/DCA "
              f"and record the decision in the CHANGELOG now.")
    return out


def cumulative_incidence(df: pd.DataFrame) -> None:
    """Descriptive competing-risks view (protocol S8 item 1): Aalen-Johansen
    cumulative incidence of CRC death vs other-cause death, EO and AO.
    No Fine-Gray regression is prespecified."""
    from lifelines import AalenJohansenFitter
    fig, ax = plt.subplots(figsize=(7, 5))
    rows = []
    for g, color in [("EO", "#c0392b"), ("AO", "#2c3e50")]:
        sub = df[df.eo_group == g]
        ev = np.where(sub.css_event == 1, 1,
                      np.where(sub.os_event == 1, 2, 0))
        for cause, ls, label in [(1, "-", "CRC death"),
                                 (2, "--", "other-cause death")]:
            ajf = AalenJohansenFitter(calculate_variance=False, seed=0)
            ajf.fit(sub.survival_months.values, ev, event_of_interest=cause)
            ajf.plot(ax=ax, color=color, ls=ls, label=f"{g}: {label}")
            cif = ajf.cumulative_density_
            for t in (36, 60):
                v = cif[cif.index <= t].iloc[-1, 0] if (cif.index <= t).any() else np.nan
                rows.append(dict(group=g, cause=label, months=t,
                                 cumulative_incidence=round(float(v), 4)))
    ax.set_xlabel("Months since diagnosis")
    ax.set_ylabel("Cumulative incidence")
    ax.set_title("Competing risks: CRC death vs other-cause death (Aalen-Johansen)")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "cumulative_incidence_competing.png", dpi=200)
    plt.close(fig)
    pd.DataFrame(rows).to_csv(RESULTS / "cumulative_incidence.csv", index=False)


def km_plot(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    kmf = KaplanMeierFitter()
    for g, color in [("EO", "#c0392b"), ("AO", "#2c3e50")]:
        sub = df[df.eo_group == g]
        kmf.fit(sub.survival_months, sub.css_event,
                label=f"{g} (n={len(sub):,})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color)
    ax.set_xlabel("Months since diagnosis")
    ax.set_ylabel("Cancer-specific survival probability")
    ax.set_title("Cancer-specific survival: early-onset vs average-onset CRC")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=.25)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "km_css_eo_vs_ao.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    eo = df[df.eo_group == "EO"]
    for stage, color in [("Localized", "#27ae60"), ("Regional", "#f39c12"),
                         ("Distant", "#c0392b")]:
        sub = eo[eo.summary_stage == stage]
        if len(sub) == 0:
            continue
        kmf.fit(sub.survival_months, sub.css_event,
                label=f"{stage} (n={len(sub):,})")
        kmf.plot_survival_function(ax=ax, ci_show=False, color=color)
    ax.set_xlabel("Months since diagnosis")
    ax.set_ylabel("Cancer-specific survival probability")
    ax.set_title("Early-onset CRC: survival by summary stage")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=.25)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "km_css_eo_by_stage.png", dpi=200)
    plt.close(fig)


def os_plot(df: pd.DataFrame) -> None:
    """Descriptive overall-survival KM (protocol S2: OS is descriptive only;
    no OS model is prespecified)."""
    fig, ax = plt.subplots(figsize=(7, 5))
    kmf = KaplanMeierFitter()
    for g, color in [("EO", "#c0392b"), ("AO", "#2c3e50")]:
        sub = df[df.eo_group == g]
        kmf.fit(sub.survival_months, sub.os_event,
                label=f"{g} (n={len(sub):,})")
        kmf.plot_survival_function(ax=ax, ci_show=True, color=color)
    ax.set_xlabel("Months since diagnosis")
    ax.set_ylabel("Overall survival probability")
    ax.set_title("Overall survival (descriptive): early-onset vs average-onset CRC")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=.25)
    watermark(fig)
    fig.tight_layout()
    fig.savefig(FIGURES / "km_os_eo_vs_ao.png", dpi=200)
    plt.close(fig)


def main() -> None:
    df = load_cohort()
    t1 = table1(df)
    t1.to_csv(RESULTS / "table1.csv")
    followup_adequacy(df)
    km_plot(df)
    os_plot(df)
    cumulative_incidence(df)
    print(f"Wrote {RESULTS/'table1.csv'} and 3 KM figures to {FIGURES}/")


if __name__ == "__main__":
    main()
