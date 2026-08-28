# CHANGELOG

Per protocol §13, every deviation or revision is recorded here with date
and rationale. No SEER data has been requested or accessed as of any entry
below; all changes precede outcome observation.

## v4.1 — Aug 19, 2026 (real-export schema validation; STILL PRE-REGISTRATION)

**Disclosure.** The PI downloaded the SEER case listing (Nov 2025 Sub,
2000-2023; 248,490 rows, dx 2010-2019, age 18-84) on 2026-08-19 — after
protocol v4.0 was finalized but BEFORE OSF registration. On that date ONLY
the outcome-blind cohort-construction stage (src/01_build_cohort.py) was
run, to validate header mapping and label vocabularies. No follow-up
structure (02), no model, no performance metric and no outcome distribution
was inspected; the stage-01 outcome-rate print was removed for this reason.
Register on OSF before running 02+.

Defects found only because real labels were seen (all fixed + tested):
- Coalescer treated the SEER*Stat missing token "Blank(s)" as a value ->
  2018+ rows would have inherited "Blank(s)" grade from the pre-2018 column.
- Race recode: "Non-Hispanic White/Black/API" contain the substring
  "Hispanic" -> every non-Hispanic patient was being coded Hispanic.
- Grade 2018+: exported as Grade Pathological/Clinical (2018+), not the
  Derived Summary Grade; COLUMN_MAP updated; codes 9/A-D/H/L -> Unknown
  (documented; 2018+ grade Unknown share is materially higher than pre-2018).
- Summary stage & surgery headers differ from the v3 guess; updated.
- Site: C26.0 "Intestinal tract, NOS" appears in the export -> explicit
  colorectal-site inclusion step added (not silently grouped).
- Node special codes 95-99 handled per SEER definitions (98 -> 0 examined;
  95/96/97/99 -> count unknown, imputed; not flagged "not examined").
- Removed the CSS-event-rate print from stage 01 (outcome-blind stage).



Still before SEER access; synthetic pipeline tests only. Nothing here was
tuned on synthetic numerical results.

1. Follow-up adequacy trigger: denominator corrected to event-free patients
   only (was: share of ALL patients who are event-free AND short); moved to
   src/estimands.py; unit test compares against the old quantity.
2. Horizon boundary: event BY H = T <= H; observable = (E=1 & T<=H) | T>=H;
   single implementation in src/estimands.py used by 03 and 07; boundary
   unit test (H-1, H, H+1, censored<H, event-free>H, event-free==H).
3. Paired delta survival-model time-dependent AUC (Uno/IPCW,
   scikit-survival) implemented at 36/60 mo with shared patient resamples,
   percentile CI, valid-replicate count; clearly separated from the
   fixed-horizon binary ROC AUC (relabelled in outputs).
4. XGBoost: tuning uses an inner-train-only FeatureBuilder; the final model
   is REFIT on the full development cohort with the selected depth and
   rounds (previously the early-stopped inner-80% model was shipped);
   hyperparameters persisted per group.
5. SEER mapping: C18.8/C18.9 -> explicit "Colon, NOS/overlapping" (never
   sided); grade via exact normalized-label dictionary (Grade I can no
   longer be triggered by Grade IV); surgery -> Yes/No/Unknown with 98/99/
   blank/unrecognized as Unknown; radiation/chemo documented as SEER-native
   dichotomies.
6. Protocol<->code reconciliation: H3 = paired dC vs full Cox (implemented);
   IBS removed from prespecified metrics; OS = descriptive KM only;
   Fine-Gray removed, replaced by descriptive Aalen-Johansen incidence
   (implemented); recalibration scope stated per model.
7. References: [7] re-checked Aug 18 2026 - journal version NOT confirmed,
   remains arXiv with VERIFY flag; other flags retained (not fabricated).
9. SEER database wording: deterministic rule only; example marked
   illustrative + verify.
10. Ethics wording: authorized-access SEER terms; institutional
   requirements followed; no overstated IRB exemption.
11. Explicit no-real-data statement in protocol and README.
12. tests/ added (22 tests). 13. Clean synthetic run exit 0.
+ app/app.py research-use demonstration (Streamlit), mode banner,
  frozen models only; requirements updated.



### Scientific / protocol
- Novelty language softened to "to our knowledge"; two additional adjacent
  studies verified and cited (Li 2025 Sci Rep EO/LO calculators; Zhao
  transfer-learning distinguished); literature notes updated.
- Calibration intercept (CITL) defined exactly: offset-logistic intercept,
  log-odds scale; observed-minus-expected reported separately. Materiality
  and adequacy thresholds re-stated on the log-odds scale and explicitly
  labeled study-specific interpretive benchmarks.
- Fixed-horizon estimand defined (conditional on observability) and
  explicitly secondary; survival models primary.
- H3 reworded neutrally (comparison, no presupposed direction).
- Hyperparameter procedure made exact and identical to code: depth grid
  {3,4,6} on a seeded internal 80/20 training split with early stopping
  (ambiguous "internal split / 5-fold CV" wording removed).
- Follow-up adequacy rule given an operational trigger (>50% of
  event-free test patients with follow-up < horizon) and implemented in
  code before any modeling stage.
- Node-positivity ratio defined only when nodes examined > 0, with an
  explicit nodes_not_examined indicator.
- Deterministic database-submission rule stated in §3.
- Second-primary exclusion tied to the SEER*Stat sequence-number
  selection and documented.
- Web-app language: research-use-only demonstration, with explicit
  non-clinical-use statements.
- References: unverifiable items flagged [VERIFY BEFORE PREREGISTRATION];
  nothing fabricated.

### Code (leakage & correctness)
- **Leakage eliminated:** cohort-level tumor-size median imputation
  removed from 01_build_cohort; all data-dependent preprocessing
  (imputation medians, dummy vocabulary, train-constant column drops)
  moved into FeatureBuilder, fitted on the relevant training window only,
  frozen, persisted (results/<mode>/models/*_features.json), and reused
  for every transform including the AO->EO transport.
- **Paired bootstrap implemented** (04_evaluate): patient-level paired
  resampling (seed 2026, B=200) for delta-C and delta-AUC between the
  EO-trained and frozen AO-trained model on the identical EO test set;
  patient alignment asserted.
- **Recalibration implemented** (new 07_recalibration): offset-logistic
  intercept-only; logistic intercept+slope; Cox Breslow-baseline
  re-estimation with frozen AO coefficients; lp-slope (van Houwelingen)
  recalibration — all fitted on EO training data only, evaluated once on
  the EO test window.
- **CITL corrected:** offset-logistic intercept (Newton-Raphson);
  mean-difference reported separately as obs_minus_exp.
- **Hyperparameter grid implemented** exactly as prespecified.
- **RSF is a hard requirement on real data** (real run aborts without
  scikit-survival; synthetic test mode warns only).
- **COLUMN_MAP coalescing:** each canonical variable maps to an ordered
  list of era-specific SEER columns (tumor size 2004-2015 vs 2016+; grade
  thru-2017 vs 2018+), coalesced first-non-missing with a printed
  coverage audit — mapping a single-era column no longer silently blanks
  other diagnosis years.
- **Follow-up adequacy table** written by 02_descriptives before any
  model stage, with the prespecified 36-month trigger warning.

### Operational safety
- Outputs strictly separated: results/{synthetic|seer}/ and
  figures/{synthetic|seer}/; cohort files carry a data_mode column;
  every synthetic-mode figure watermarked "SYNTHETIC-DATA PIPELINE TEST".
- run_all.sh prints a prominent mode banner and never regenerates
  synthetic data when a real export is present.
- Stale generated outputs removed from version control; results/ and
  figures/ remain git-ignored.

## v2.0 — Aug 12, 2026
Title/objectives restructured after the focused literature review;
transportability elevated to the primary objective.

## v1.0 — Aug 12, 2026
Initial draft.
