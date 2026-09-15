# Changelog

## v4.1.2 — Sep 14, 2026 (Stage-02 pre-model gate closed; no methodological changes)

Stages 01-02 executed on the real SEER export (Nov 2025 Sub, 2000-2023). No model has been
fitted or evaluated as of this entry. Cohort flow reproduced the counts recorded at
preregistration exactly: 216,975 eligible; EO 20,781 train / 9,551 test; AO 130,728 train /
55,915 test.

### Follow-up adequacy (protocol S5 rule, evaluated at the 60-month horizon)

| group | split | n | event-free | reverse-KM median FU (mo) | share event-free with FU < horizon | horizon-observable share |
|---|---|---|---|---|---|---|
| AO | test | 55,915 | 39,931 | 62.0 | 0.475 | 0.661 |
| EO | test | 9,551 | 6,652 | 63.0 | 0.441 | 0.693 |
| AO | train | 130,728 | 86,501 | 110.0 | 0.168 | 0.889 |
| EO | train | 20,781 | 13,176 | 119.0 | 0.084 | 0.947 |

**HORIZON DECISION.** The prespecified trigger (>0.50 of event-free temporal-test patients with
follow-up shorter than the horizon, in either group) did not fire. Primary horizon RETAINED AT
60 MONTHS; HORIZON_MONTHS in src/config.py unchanged and now locked. The AO test share (0.475)
falls near the threshold; the rule was fixed before this quantity was observed and was applied
as written, and proximity to the threshold was not treated as grounds for reconsideration. Paired
delta time-dependent AUC remains prespecified at both 36 and 60 months (v4.0 item 3) and is
unaffected by this decision.

### EPP (protocol S9, EO training window)

7,605 cancer-specific events among 20,781 EO training patients.

The denominator was audited against the frozen implementation rather than inferred.
src/utils_features.py builds the design matrix via pd.get_dummies(..., drop_first=True), so each
categorical contributes k-1 parameters. A targeted search of src/utils_features.py and
src/03_models.py found no polynomial terms, spline transformers, or interaction terms, so no
further expansion occurs.

Parameter count: 6 numeric (age_dx, tumor_size_mm, nodes_examined, nodes_positive, node_ratio,
year_dx) + 2 indicators (tumor_size_missing, nodes_not_examined) + 22 from the 10 categoricals at
k-1 observed levels (sex 1, race_eth 4, site_group 3, histology 2, grade 4, summary_stage 2,
cea 2, surgery 2, chemo 1, radiation 1) = 30.

**EPP = 7,605 / 30 = 253.5.** Threshold (>=20) satisfied by a wide margin; also satisfied under
full one-hot encoding (40 parameters, EPP = 190.1) and for any prespecified subset. The S9
deterministic feature-priority fallback is NOT triggered; the full candidate feature set is
retained. A naive count over the 18 raw feature names would have given EPP = 423 and was not used.

### Stage-01 data-quality audit (real export)

Unknown shares: summary stage 3.7%, grade 19.2%, CEA 43.3%, surgery 0.3%. Colon NOS/overlapping
site share 3.1%. The elevated grade-Unknown share is consistent with the 2018+ grade-coding change
documented at v4.1.

### Notes

- Stage 02 emitted a lifelines warning that tied event times were resolved by random jittering in
  the Aalen-Johansen estimator. The fitter is instantiated with a fixed seed
  (AalenJohansenFitter(calculate_variance=False, seed=0)), so the jitter is deterministic and the
  curves are reproducible. These curves are descriptive; no prespecified inference depends on them.
- Environment: .venv, Python 3.11.9, per requirements-lock.txt.

**Pre-model gate CLOSED.** Stages 03-07 may now run via `run_models.sh --horizon-locked`.

## v4.1.1 — Aug 28, 2026 (provenance-correction pass; no methodological changes)

### Disclosure accuracy
- Replaced the over-broad sentence "No real SEER patient-level outcome
  data have been accessed or analyzed during protocol development or
  repository testing" (README and protocol S10) with the accurate
  narrower disclosure: on Aug 19, 2026 the authorized SEER export was
  accessed solely for outcome-blind schema and cohort-construction
  validation (Stage 01); no follow-up distribution, event distribution,
  model fitting, predictions, or performance metrics were inspected
  before preregistration.
- Status wording corrected repository-wide from "preregistered" to
  "final preregistration candidate; OSF registration pending". The OSF
  DOI, date, and URL will be added to README after actual registration
  (the frozen registered artifact itself is never retroactively edited).

### Real-data execution gate
- run_all.sh: with a real export present, now runs ONLY Stages 01-02 and
  stops at a conspicuous PRE-MODEL GATE (adequacy rule + EPP check +
  CHANGELOG recording), fitting no model. Synthetic mode still runs the
  full pipeline end-to-end.
- run_models.sh (new): Stages 03-07; in real mode refuses to run without
  the explicit --horizon-locked flag.

### Protocol-code concordance
- Protocol S7 transport wording now names the implemented transported
  set exactly: cox_full, xgb_cox, xgb_h (AO-fitted preprocessing frozen);
  cox_stage and RSF are within-group comparators only and are not
  transported.
- Protocol S9 clarified: cancer-specific event counts were not inspected
  pre-registration; EPP is evaluated at the Stage-02 gate, with the
  deterministic priority-order fallback (stage, nodes, histology, grade,
  size, age) retained unchanged.

### Implementation completeness
- src/02_descriptives.py: added `os_plot` — the descriptive overall-survival
  Kaplan-Meier prespecified in protocol S2 (OS descriptive only; no OS model
  prespecified). The concordance table previously deferred this to the
  real-data stage; it is now implemented and runs in both modes. No new
  analytic choice introduced.
- Concordance table rows for EPP and sensitivity analyses (2)-(6) now
  explicitly read *NOT yet executed* rather than implying completion.

### Post-registration decision log (completed at the Stage-02 gate)
- HORIZON DECISION: 2026-09-14 — share_of_event_free_with_followup_lt_horizon
  (EO test) = 0.441, (AO test) = 0.475; rule fired: no; primary horizon
  locked at 60 months. EPP (EO train) = 253.5 (7,605 events / 30 parameters);
  fallback applied: no. Full detail recorded under v4.1.2 above.

Per protocol §13, every deviation or revision is recorded here with date
and rationale. Entries through v4.0 preceded access to real SEER data.
Version 4.1 records the August 19, 2026 outcome-blind Stage 01 schema and
cohort-construction validation on the authorized SEER export. No follow-up
distribution, outcome/event distribution, model fitting, predictions, or
performance metrics were inspected before preregistration.

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



## v4.0 — Aug 18, 2026 (preregistration-candidate correction pass)

Entries in this section predate access to real SEER data; synthetic
pipeline tests only. Nothing here was tuned on synthetic numerical
results.

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



## v3.0 — Aug 13, 2026 (pre-registration methods audit)

Entries in this section predate access to real SEER data.

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
