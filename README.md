# Age-Group Transportability of Explainable ML Models for Cancer-Specific Survival in Early-Onset Colorectal Cancer

**A temporally validated U.S. SEER study: do survival models trained on
average-onset patients transport to early-onset patients — and can
recalibration repair them?**

Principal investigator: **Nabeel Ahmad Khan** (first & corresponding author)
Status: protocol preregistered (see `docs/protocol_OSF_preregistration.md`);
analysis code under development. Preprint: *forthcoming (medRxiv)*.

---

## Why this study

Colorectal cancer (CRC) has become the leading cause of cancer death among
U.S. adults under 50, and early-onset CRC (EO-CRC, age 18–49) is rising while
mortality falls for nearly every other major cancer in this age group. Yet
most prognostic models are developed on predominantly older cohorts. EO-CRC prognostic models exist
(see docs/literature_check_notes.md), but in a focused literature review
(Aug 2026) we identified, to our knowledge, no study that freezes an
average-onset-trained survival model, applies it to an identical
early-onset test set beside an EO-trained comparator, quantifies
degradation in discrimination **and** calibration against prespecified
criteria, and tests whether simple recalibration repairs it.
That frozen-model **age-group transportability** question is this study's
primary objective; interpretable EO-CRC model development and an EO-vs-AO
SHAP contrast are secondary. Full rationale, hypotheses, and analysis plan are
preregistered in `docs/protocol_OSF_preregistration.md`.

**No real SEER patient-level outcome data have been accessed or analyzed
during protocol development or repository testing.** All runs so far are
synthetic pipeline tests (unit tests, debugging, execution and null/sanity
checks); synthetic outputs are watermarked and never presented as
findings.

## Quickstart (no SEER data needed)

The pipeline runs end-to-end on a synthetic, SEER-like dataset so you can
verify everything works before data access is approved:

```bash
python -m venv .venv && source .venv/bin/activate   # or your preferred env
pip install -r requirements.txt
bash run_all.sh
```

Outputs land in `results/synthetic/` (tables) and `figures/synthetic/`
(KM curves, calibration, SHAP, decision curves, transportability,
recalibration). Real-data runs write to `results/seer/` and
`figures/seer/` instead — the two can never mix, and **synthetic outputs
are watermarked, are for pipeline testing only, and support no scientific
conclusions.**

## Research-use demonstration app

```bash
streamlit run app/app.py
```
Loads only the frozen models and audit tables for the current data mode
(a red banner = synthetic; green = SEER). Research use only; not medical
advice; not for clinical decision-making. See `app/app.py` header.

## Tests

```bash
python -m pytest tests -q
```
22 deterministic tests on toy data: train-only preprocessing, frozen
AO->EO transport, paired-bootstrap alignment, adequacy denominator,
horizon boundary, grade/site/surgery mapping, XGB full-cohort refit,
paired delta time-dependent AUC.

## Using real SEER data

Follow `data/README.md` exactly: request the (free) SEER Research Data tier,
build the documented SEER*Stat case listing, export with labels to
`data/raw/seer_crc_export.csv`, update `COLUMN_MAP` in `src/config.py`, and
rerun `bash run_all.sh`. **Never commit case-level SEER data** — the DUA
prohibits redistribution and the `.gitignore` enforces this.

## Repository map

```
docs/     preregistered protocol, reporting-checklist instructions
data/     SEER regeneration recipe (no case-level data is ever stored here)
src/      numbered pipeline: 00 synthetic → 01 cohort → 02 descriptives
          (incl. the follow-up adequacy rule) → 03 models → 04 evaluation
          (paired transportability bootstrap) → 05 SHAP → 06 decision
          curves → 07 recalibration of the frozen AO model
results/  generated tables, per mode: results/synthetic/ vs results/seer/
          (git-ignored)
figures/  generated figures, per mode; every synthetic-mode figure is
          watermarked "SYNTHETIC-DATA PIPELINE TEST" (git-ignored)
```

## Methods snapshot

Temporal validation (train 2010–2016, test 2017–2019); models: stage-only
Cox, full Cox, random survival forest, XGBoost (survival:cox), and 5-year
fixed-horizon XGBoost vs logistic regression; metrics: Harrell C with
bootstrap CIs, time-dependent AUC, calibration slope and offset-logistic
intercept with plots, Brier score, decision-curve net benefit;
transportability: frozen AO-trained models (including their AO-fitted
preprocessing) on the EO test set with paired-bootstrap deltas,
prespecified materiality criteria, and recalibration (intercept,
intercept+slope, Cox baseline re-estimation, lp-slope) fitted on EO
training data only; explainability: SHAP with EO-vs-AO contrast;
reporting per TRIPOD+AI and STROBE. All data-dependent preprocessing is
fitted on training windows only (see `src/utils_features.py`).

## Transparency

Initial code scaffolding was developed with AI assistance; all analytic
decisions, execution on real data, review, and interpretation are by the
authors, and AI assistance is disclosed in the manuscript per journal
policy. Issues and pull requests are welcome once the preprint is posted.

## License

Code: MIT (see `LICENSE`). SEER data are governed by the SEER DUA and are
not distributed here.
