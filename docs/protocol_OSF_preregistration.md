# Study Protocol & Analysis Plan (for OSF Preregistration) — Version 4.1.1

**Title:** Age-group transportability of explainable machine-learning models
for cancer-specific survival in early-onset colorectal cancer: a temporally
validated U.S. SEER study

**Principal investigator / first & corresponding author:** Nabeel Ahmad
Khan, Pharm.D., M.S. (Biomedical Sciences — Pharmacology, University of
Alabama at Birmingham)
**Version:** 4.1.1 — final preregistration candidate (August 28, 2026; OSF registration pending)
**Registration type:** OSF open-ended preregistration
**Funding:** None. **Conflicts of interest:** None declared.
**Code repository:** https://github.com/nabeelkhan192/eocrc-ml-survival
(public; frozen OSF snapshot: annotated tag `v4.1.1-osf` — the exact commit
SHA is recorded in the OSF registration form)

**Version history.** v1.0 (Aug 12, 2026): initial draft. v2.0 (Aug 12,
2026): title and objective structure revised following a pre-registration
focused literature review (docs/literature_check_notes.md); the
transportability question was elevated to the primary objective and the
novelty statement narrowed accordingly. v3.0 (Aug 2026): pre-registration
methods audit — leakage-proof preprocessing specified (§7.0), the paired
bootstrap, calibration-intercept scale, hyperparameter procedure, the
fixed-horizon estimand, and the node-ratio definition made exact; all
materiality/adequacy thresholds explicitly labeled study-specific;
repository synchronized with this protocol. v4.0 (Aug 2026):
preregistration-candidate correction pass — follow-up-adequacy denominator
(event-free patients only), horizon boundary (event at T ≤ H), paired
Δtime-dependent AUC implemented, XGBoost tune-then-refit-on-full-cohort
procedure, SEER site/grade/surgery mapping made explicit, protocol promises
reconciled with code (H3 simplified, IBS removed, OS made descriptive,
Fine–Gray replaced by descriptive Aalen–Johansen incidence, recalibration
scope stated), unit-test suite added, research-use demonstration app added.
**Data-access disclosure (v4.1, Aug 19, 2026).** All protocol design and
pipeline testing through v4.0 used fabricated synthetic data only. On
Aug 19, 2026 — after v4.0 was finalized and before OSF registration — the
SEER case listing was downloaded and *only* the outcome-blind
cohort-construction stage (`src/01_build_cohort.py`: header mapping, label
vocabularies, inclusion counts) was run to validate the export schema. No
follow-up structure, outcome distribution, model, or performance metric
was inspected before registration; the mapping corrections this
surfaced (v4.1) are listed in the CHANGELOG. Synthetic results are never
presented as findings.
**v4.1.1 (Aug 28, 2026): provenance-correction pass (no methodological
changes).** (1) The pre-registration real-data disclosure was harmonized
across the protocol (§10) and README — an earlier, over-broad sentence
("no real SEER patient-level outcome data have been accessed") was
replaced by the accurate narrower claim below. (2) A real-data execution
gate was added: on real SEER data `run_all.sh` now stops after Stage 02 so
the prespecified follow-up-adequacy rule is applied and the primary
horizon locked before any model is fitted (`run_models.sh` runs Stages
03–07 afterward). (3) §7 transport wording was matched to the implemented
code: the models transported AO→EO are `cox_full`, `xgb_cox`, and `xgb_h`;
the stage-only Cox baseline and RSF are not transported. (4) Status
wording corrected from "registered/preregistered" to "preregistration
candidate" pending actual OSF registration. Environment lock file
(`requirements-lock.txt`, Python 3.11.9) included in the frozen snapshot.
(5) CHANGELOG header corrected and historical v4.0/v3.0 headings restored.
(6) H2 wording tightened: recalibration preserves ranking under
intercept-only and positive-slope updates (a slope <= 0 is reported, not
treated as success). (7) Descriptive OS Kaplan-Meier (S2) implemented in
stage 02. (8) Literature notes updated: Zhao journal version (Artif Intell
Med 2026;178:103426, PMID 42019107) replaces the arXiv-only entry; the
duplicate Korean-XAI entry retired against verified PMID 41066920.
(9) Reporting-checklist database example corrected to Nov 2025 Sub.

---

## 1. Background and rationale

Colorectal cancer (CRC) mortality in U.S. adults younger than 50 has risen
by approximately 1% per year since 2005, and CRC is now the leading cause
of cancer death in this age group — first in men and second in women —
even as under-50 mortality declined for the other leading cancers [1]. The
proportion of CRC diagnosed before age 55 doubled from 11% in 1995 to 20%
in 2019 [3b], and adults aged 45-49 now account for half of all diagnoses
under 50 [3]. Early-onset CRC
(EO-CRC; diagnosis at age 18–49) differs from average-onset disease
(AO-CRC) in anatomic distribution, histology, and stage at presentation
[2].

Prognostic modeling in this population is an active field. EO-CRC-specific
prognostic tools have been reported, including SEER-based nomograms for
cancer-specific and conditional survival and, most recently, OncoE25 — a
machine-learning model for postoperative cancer-specific survival in stage
I–III early-onset colon and rectal cancer, developed on SEER with a random
train/test split, externally validated in two Chinese hospital cohorts,
interpreted with SHAP, and deployed as an online calculator [5]. Parallel
work has built separate survival calculators for early- and late-onset CRC
from the same registry frame [6], and related work has used transfer
learning to adapt SEER-trained CRC survival models to a smaller
single-institution cohort by fine-tuning [7].

**The gap this study addresses is narrower and, in a focused literature
review (August 2026), unaddressed:** although EO-CRC-specific prognostic
models and machine-learning survival models for CRC have been reported,
direct evaluation of whether survival models developed in average-onset
colorectal cancer retain discrimination and calibration when applied
**without refitting** to early-onset patients remains limited. To our
knowledge, no identified study froze an AO-trained model, applied it to an
identical early-onset test set alongside an EO-trained comparator,
quantified degradation in both discrimination and calibration against
prespecified criteria, and tested whether simple recalibration repairs the
deficit — under temporal validation, in a U.S. population-based full-stage
cohort. Because most clinical prediction tools young patients encounter
were developed on predominantly older cohorts, miscalibrated risk
estimates could misinform surveillance, trial referral, and shared
decision-making precisely where CRC deaths are rising. The broader
question — the generalizability of biomedical AI across age
subpopulations — extends beyond CRC. Reporting follows TRIPOD+AI [4].

*Investigator context:* this study extends the PI's prior work on machine
learning for gastrointestinal cancer outcome prediction [8] and artificial
intelligence in oncologic care [9] into an original, reproducible,
registry-based modeling contribution.

## 2. Objectives and hypotheses

**Primary objective — age-group transportability.** Quantify the change in
discrimination and calibration when cancer-specific survival models trained
on AO-CRC (age 50–84) are applied without refitting to EO-CRC (age 18–49)
test patients, relative to EO-trained models evaluated on the identical
patients, and determine whether simple recalibration mitigates observed
degradation.

- **H1 (transportability).** AO-trained models applied to EO test patients
  show degraded performance relative to EO-trained models on the same
  patients: lower discrimination (paired ΔC-index and paired
  Δ*survival-model time-dependent AUC* at 36 and 60 months for the survival
  models; paired Δ*fixed-horizon binary ROC AUC* for the secondary
  classifier — the two AUC types are never used interchangeably) and/or
  material miscalibration (calibration slope, calibration intercept) per
  the prespecified criteria in §7.
- **H2 (recalibration).** Recalibration of AO-trained models using EO
  training-window data only (§7 step 5) restores calibration to within the
  prespecified adequacy range in the EO test window. Recalibration is
  intended to correct calibration rather than discrimination:
  intercept-only updates preserve ranking, and positive-slope
  recalibration preserves ranking; therefore any substantive
  discrimination deficit generally requires model refitting rather than
  calibration adjustment — itself a reportable, decision-relevant
  finding. (A fitted slope <= 0 would not preserve ranking; should this
  occur it will be reported explicitly rather than treated as a
  calibration success.)

**Secondary objective — EO-CRC model development.**
- **H3.** In EO-CRC under temporal validation, each survival model
  (summary-stage-only Cox, random survival forest, gradient-boosted
  survival model) is compared with the full-covariate Cox benchmark on the
  identical EO test patients by **paired ΔC-index with 95% paired-bootstrap
  CI** (implemented; `results/<mode>/h3_eo_paired_deltaC.csv`). No other
  between-model comparison is prespecified and no direction is presupposed.

**Exploratory.**
- **H4.** The pattern of model-attributed feature contributions
  (mean |SHAP|) differs between EO- and AO-trained models (descriptive
  contrast; no formal test; SHAP scales are not directly comparable across
  models and no causal interpretation is made).

Additional prespecified descriptive outputs: overall survival
(Kaplan–Meier, descriptive only — no OS models are prespecified) and
Aalen–Johansen cumulative incidence of CRC death versus other-cause death
(descriptive competing-risk view); decision-curve net benefit of the
fixed-horizon risk models across threshold probabilities 5–60%
(prespecified exploratory range).

## 3. Design and data source

Retrospective population-based cohort study using the NCI SEER Research
Data. **Deterministic database rule (fixed before access):** the analysis
uses the newest eligible SEER Research Data incidence submission available
at the time of data access that covers the prespecified diagnosis years
(2010–2019 with follow-up), preferring the largest-registry variant; the
exact submission name is recorded verbatim in the repository CHANGELOG and
the manuscript before any outcome is tabulated. **Submission recorded (Aug 19, 2026):** *Incidence — SEER Research Data,
17 Registries, Nov 2025 Sub (2000–2023) — Linked To County Attributes —
Time Dependent (1990–2024) Income/Rurality, 1969–2024 Counties*. Access is via SEER*Stat under the SEER Research Data Use
Agreement. No data linkage will be performed, consistent with the DUA.

**Design distinctions from prior EO-CRC modeling (prespecified):** (a)
**temporal** validation (train 2010–2016, test 2017–2019) rather than a
random split, approximating prospective deployment; (b) the full
malignant-stage population (localized through distant), not restricted to
postoperative stage I–III; (c) the frozen-model AO→EO cross-application
and recalibration protocol of §7; (d) a U.S. population-based frame for
both age groups.

## 4. Population

**Inclusion:** first malignant primary colorectal adenocarcinoma (ICD-O-3
sites C18.0, C18.2–C18.9, C19.9, C20.9; adenocarcinoma histology family
including mucinous 8480–8481 and signet-ring 8490; the exact ICD-O-3 code
list implemented in `src/01_build_cohort.py` is verified against the
submission's documentation before the cohort is locked); microscopically
confirmed; diagnosis years 2010–2019; age 18–84 at diagnosis; known
summary stage; survival follow-up ≥ 1 month.
**Exclusion:** appendiceal primaries (C18.1); diagnosis by death
certificate or autopsy only; unknown survival time; second or later
primaries (implemented as sequence number 0 or 1 in the SEER*Stat
selection statement; see data/README.md).
**Groups:** EO-CRC = age 18–49; AO-CRC = age 50–84 (identical thresholds
in protocol, code — `config.EO_MAX_AGE` — and all documentation).

If the newest submission includes diagnosis year 2020+, the primary window
remains 2010–2019 and any extension is a prespecified sensitivity analysis
(COVID-era diagnosis disruption).

## 5. Outcomes

- **Primary:** cancer-specific survival (CSS) — time origin: diagnosis;
  event: death attributed to the index cancer per the SEER cause-specific
  death classification; censoring: death from other causes or alive at the
  study cutoff (competing-risk sensitivity in §8).
- **Secondary:** overall survival (event: death from any cause).
- **Fixed horizons** for classification-style models and clinical-utility
  analyses: 60 months (primary), 36 months. **Fixed-horizon estimand
  (explicitly secondary; mathematically exact):** *CRC death by H months*
  = CSS event with T ≤ H (an event exactly at H counts as an event by H).
  *Observable population* = patients whose H-month status is known: event
  by H (E = 1, T ≤ H) **or** followed at least to H (T ≥ H); event-free
  patients with T < H are excluded (status at H unknown). One
  implementation (`src/estimands.py: horizon_labels/horizon_frame`) is
  imported by every script and covered by boundary unit tests (event at
  H−1, H, H+1; censored before H; event-free beyond H).
- **Note on 2018+ grade:** the 2018+ SEER grade variables (pathological,
then clinical) use codes 1–4 (mapped to Grade I–IV) plus 9, A–D, H, L,
which are not convertible to a four-tier grade without assumption and are
mapped to Unknown; the Unknown share is therefore higher for 2018–2019
diagnoses (test window). Grade Unknown enters models as its own category;
this is stated in Limitations. **Follow-up adequacy rule (prespecified,
implemented):**
  `src/02_descriptives.py` writes `followup_adequacy.csv` (reverse
  Kaplan–Meier median follow-up and the share of event-free patients with
  follow-up shorter than the horizon, per group × split) **before any
  model is fitted or evaluated**. **Exact rule:** among *event-free*
  patients only (denominator = event-free patients), compute the share
  with follow-up < 60 months; if that share exceeds 0.50 in either group's
  test window, the 36-month horizon becomes primary for calibration and
  decision-curve analyses (`src/estimands.py:
  event_free_short_followup_share`; unit-tested against the all-patient
  denominator). This decision is made from follow-up structure alone, before
  unblinding any test-window model performance, and is recorded in the
  repository CHANGELOG.

## 6. Candidate predictors

**Core set (year-stable):** age, sex, race/ethnicity recode, year of
diagnosis, anatomic subsite group (right colon C18.0/C18.2–C18.4; left
colon C18.5–C18.7; rectum C19.9/C20.9; **colon NOS/overlapping C18.8–C18.9
kept as an explicit fourth category because the source carries no
laterality**),
histologic subtype (adenocarcinoma / mucinous / signet ring), grade,
combined summary stage, tumor size, regional nodes examined, regional
nodes positive, node-positivity ratio, surgery of primary site, radiation
(recode), chemotherapy (recode).
**Grade:** mapped by exact normalized-label dictionary (never substring
matching) to Grade I–IV / Unknown across the pre-2018 and 2018+ grade
variables. **Surgery of primary site:** Yes / No / Unknown (SEER codes 98–99,
blanks, and unrecognized labels are Unknown, never Yes). Radiation and
chemotherapy recodes are dichotomous in SEER itself ("Yes" vs
"No/Unknown"); this is faithful to the source and stated in Limitations.
Unknown levels enter models as their own dummy category via the
train-fitted encoder.
**Node-positivity ratio (exact definition):** nodes positive / nodes
examined, defined only when nodes examined > 0; when no nodes were
examined the ratio is missing and an explicit `nodes_not_examined`
indicator is set (not-examined is not treated as ratio 0).
**Year-spanning variables:** several SEER variables changed names or
derivations across the 2004–2015 CS era, 2016+, and the 2018+ SSDI era
(notably tumor size and grade). Each canonical predictor maps to an
ordered list of era-specific source columns coalesced first-non-missing
(`COLUMN_MAP`, `src/config.py`), with a printed per-variable coverage
audit on the first real-data run; the 2016+/2018+ header names were
verified against the Nov 2025 Sub case-listing dictionary on Aug 19, 2026
(see data/README.md and CHANGELOG v4.1).
**Biomarker extension set (availability-dependent; prespecified as a
secondary model):** pretreatment CEA interpretation; and for later
diagnosis years, MSI, KRAS, perineural invasion, tumor deposits.
**Notes:** SEER chemotherapy/radiation variables under-ascertain treatment
and are used strictly as prognostic covariates, never for treatment-effect
inference; this is stated in Limitations. All predictors reflect
information available at or around diagnosis/initial course of therapy;
no post-baseline information (e.g., recurrence) is available in SEER or
used.

**Missing data:** category-level "Unknown" retained for categorical
variables; continuous variables median-imputed **with medians estimated on
the relevant training window only** (see §7.0) plus a row-local
missingness indicator; complete-case sensitivity analysis; if
biomarker-set missingness exceeds 40%, that model is reported as
exploratory.

## 7. Statistical and machine-learning analysis

**7.0 Leakage protections (binding for every analysis).** All
data-dependent preprocessing — imputation medians, dummy-variable
vocabulary, and removal of training-constant columns — is fitted on the
relevant group's **training window only**, frozen, persisted, and reused
unchanged for every downstream transform (`FeatureBuilder`,
`src/utils_features.py`). Hyperparameter selection uses an internal split
of the training window only. The temporal test window (2017–2019) is
never used for any fitting, selection, imputation, or recalibration step.
For the transportability analysis, the frozen AO pipeline — including its
AO-fitted preprocessing — is applied to EO test patients; no EO
information of any kind influences the AO model before the prespecified
recalibration stage (step 5), which uses EO **training-window** data only.
Test-window metrics are computed once.

**Validation design:** temporal split — training on diagnosis years
2010–2016, held-out testing on 2017–2019. Temporal validation is used
because it approximates prospective deployment (a model built on past
patients applied to future ones) and is a stronger test than a random
split of the same years.

**Hyperparameters (exact procedure, per age group):** *Tuning stage* —
within the 2010–2016 development cohort: (1) seeded internal 80/20
train/validation split (identical for all candidates); (2) preprocessing
(`FeatureBuilder`) fitted on the inner-training 80% only and used to
transform both inner sets; (3) for each maximum depth in the prespecified
grid {3, 4, 6}, boosting with early stopping on inner-validation, recording
the best depth and its number of boosting rounds. *Final development
model* — (4) a new `FeatureBuilder` is fitted on the **full** development
cohort; (5) the boosted model is **refit on the full development cohort**
with the selected depth and number of rounds (no early stopping, no
validation data); (6) this complete pipeline is frozen, persisted
(`results/<mode>/models/`, incl. `*_hyperparams.json`), and applied
unchanged to the temporal test cohort and, for AO, transported to EO test.
Cox, logistic and RSF models have no tuned hyperparameters and are fitted
once on the full development cohort with the same full-cohort
`FeatureBuilder`. All other settings are fixed in `src/config.py` /
`src/03_models.py`. No temporal-test or transported-EO information touches
preprocessing, tuning, early stopping, model selection, or final fitting
(unit-tested).

**Models (per age group):** (a) Cox PH, summary stage only (clinical
floor); (b) Cox PH, all core predictors (main classical benchmark); (c)
random survival forest (**required**; a real-data run aborts if
scikit-survival is unavailable); (d) gradient-boosted survival model
(XGBoost, survival:cox); (e) fixed-horizon gradient-boosted classifier
with logistic-regression comparator (calibration reference).

**Performance metrics:** *primary* — Harrell concordance index (paired
bootstrap for between-model deltas; see below) and calibration slope +
calibration intercept at the primary horizon; *secondary/supporting* —
survival-model time-dependent (cumulative/dynamic, IPCW) AUC at 36 and
60 months, fixed-horizon binary ROC AUC (classifier only), Brier score at
the horizon, calibration plots (deciles), decision-curve net benefit
(thresholds 5–60%, exploratory). *Integrated Brier score is not
prespecified* (removed in v4.0 because it was not implemented; documented
in CHANGELOG). **Calibration intercept (CITL)
is defined as the intercept of a logistic regression of the observed
outcome on an offset of logit(predicted risk) — log-odds scale. The
simple observed-minus-expected mean difference (probability scale) is
reported separately and is not interchangeable with CITL.** Bootstrap:
seeded, B = 200 iterations, percentile 95% CIs.

**Transportability protocol (primary analysis).**
1. For each model prespecified for AO→EO transport — the full-covariate
   Cox (`cox_full`), the XGB-Cox risk score (`xgb_cox`), and the
   fixed-horizon XGBoost classifier (`xgb_h`) — freeze the AO-trained
   model, including its AO-fitted preprocessing (no re-estimation of any
   parameter). The stage-only Cox baseline (`cox_stage`) and RSF are
   fitted as within-group comparators only and are not transported.
2. Apply it to the identical EO temporal-test patients used to evaluate
   the EO-trained comparator (patient alignment asserted in code).
3. Report **paired** differences (EO-trained minus AO-trained on the same
   patients): ΔC-index and Δ*survival-model time-dependent AUC* at 36 and
   60 months for the survival models (Cox, XGB-Cox), and Δ*fixed-horizon
   binary ROC AUC* for the classifier, each with 95% paired-bootstrap CIs
   — every bootstrap resample of patients re-scores *both* models before
   differencing (seed 2026, B = 200; replicates where a metric cannot be
   computed are skipped and the valid count reported); plus calibration
   slope, CITL, observed-minus-expected, and Brier score for each model.
4. **Prespecified materiality criteria (study-specific interpretive
   benchmarks, fixed before data access; not literature-derived
   thresholds):** transportability degradation is material if any of —
   (a) paired ΔC-index ≥ 0.02 favoring the EO-trained model with 95% CI
   excluding 0; (b) AO-trained calibration slope on EO test data outside
   0.80–1.20; (c) |CITL| > 0.20 (log-odds scale) at the primary horizon.
5. **Recalibration (all parameters fitted on EO training-window data
   only; implemented in `src/07_recalibration.py`). Scope:** the
   transported AO *fixed-horizon XGBoost classifier* receives (i) an
   intercept-only update via offset logistic regression and (ii) logistic
   intercept-and-slope recalibration; the transported AO *full-covariate
   Cox model* receives (iii) re-estimation of the Breslow baseline hazard
   on EO training data with frozen AO covariate effects and (iv) van
   Houwelingen-type linear-predictor slope recalibration with a
   re-estimated baseline. The transported AO XGB-Cox risk score (a
   relative hazard without a baseline) is *not* recalibrated — its
   transport gap is a discrimination question answered by the paired
   ΔC/Δtd-AUC; RSF is not transported. Recalibrated models are evaluated
   once on the EO test window. **Recalibration adequacy (study-specific benchmarks):**
   slope 0.90–1.10 and |CITL| ≤ 0.10 (log-odds) at the primary horizon.

**Explainability:** SHAP (TreeExplainer) global summaries and dependence
plots on the temporal test sets; EO-vs-AO mean-|SHAP| contrast reported
as *model-attributed importance* (descriptive; scales not directly
comparable across models; no causal interpretation).

## 8. Sensitivity analyses

(1) Competing risks: Aalen–Johansen cumulative incidence of CRC death
versus other-cause death, EO and AO, reported descriptively alongside the
Kaplan–Meier CSS curves (`src/02_descriptives.py`); *no Fine–Gray
regression is prespecified* (removed in v4.0 — the previous wording
implied a modeling analysis the pipeline did not implement); (2)
complete-case analysis; (3) excluding rectal primaries; (4) excluding
2019 diagnoses (short follow-up); (5) COVID-era extension if applicable
(§4); (6) transportability analysis repeated in the stage I–III
postoperative subgroup to enable direct discussion against prior stage
I–III models [5]. Items (2)–(6) are prespecified cohort-filter re-runs of
the identical pipeline (01→07); none introduces new modeling choices.

## 9. Sample size justification

No formal power calculation; the design is limited by registry size. The
outcome-blind cohort construction of Aug 19, 2026 (see data-access
disclosure) yielded 216,975 eligible patients: EO 20,781 train / 9,551
test; AO 130,728 train / 55,915 test (final STROBE flow diagram at
analysis);
cancer-specific event counts were not inspected before registration, so
events-per-parameter (EPP) is evaluated after registration, at the
Stage-02 gate, from the Stage-02 descriptives. If EO training events per
candidate parameter fall below 20, the feature set is reduced
deterministically by the prespecified clinical priority order — stage,
nodes, histology, grade, size, age — retaining features in that order
until EPP ≥ 20, following prediction-model sample-size guidance [10].

## 10. Reporting, ethics, and data governance

Reported per **TRIPOD+AI** [4] and STROBE (completed checklists submitted
as supplements). The study uses de-identified, population-based registry
data from the SEER Research Data, which require registration/authorized
access and agreement to the SEER Research Data Use Agreement; the project
will use these data strictly under the applicable SEER terms. Because the
data are de-identified and no linkage or re-identification is attempted,
the study is not expected to require IRB review under the common
interpretation of de-identified registry research; the PI will confirm and
follow the applicable institutional requirements before analysis rather
than assuming an exemption. SEER DUA terms are honored throughout: no
case-level data redistribution, no linkage, required acknowledgments
included. All
analysis code is public (GitHub) with environment specification;
case-level data are regenerable by any SEER-credentialed researcher via
the documented SEER*Stat session (data/README.md). Repository outputs are
strictly separated by mode (`results/synthetic/` vs `results/seer/`);
synthetic-mode figures are watermarked and support no scientific
conclusion. **Pre-registration real-data access disclosure.** On August 19, 2026,
after the principal study design and analysis plan had been developed
using synthetic data, the authorized SEER case-level export was accessed
solely for outcome-blind schema and cohort-construction validation
(Stage 01 only): source-header mapping, label-vocabulary inspection,
verification of inclusion/exclusion logic, coding-era compatibility, and
aggregate cohort counts. No follow-up distribution, cancer-specific event
distribution, other outcome distribution, model fitting, model
predictions, discrimination or calibration metrics, SHAP results,
hypothesis-test results, or other model-performance results were
inspected before preregistration; coding and schema corrections from this
validation are documented in the CHANGELOG. Stage 02 (run after
registration) inspects only the limited follow-up/event-support
information required by the prespecified adequacy rule; no
model-performance or hypothesis-result information is examined before the
primary horizon is locked. Synthetic
data are used only for unit tests, pipeline testing, debugging, execution
checks and null/sanity checks, and are never presented as findings.

## 11. Dissemination plan

medRxiv preprint at manuscript completion (with public code release);
submission to a peer-reviewed indexed journal (candidate venues: JCO
Clinical Cancer Informatics; JMIR Cancer / JMIR Medical Informatics; BMC
Medical Informatics and Decision Making; PLOS Digital Health; Scientific
Reports); conference abstract (e.g., AMIA Annual Symposium or IEEE
BHI/BIBM). A research-use **demonstration** app (`app/app.py`, Streamlit) accompanies
the repository; it loads only the frozen models and audit tables, never
refits, and displays the data mode (synthetic vs SEER) as a persistent
banner. The app is a research-use-only model-exploration tool:
it is not medical advice, is not intended for clinical decision-making,
is not a validated or approved clinical decision-support system, its
outputs depend on the population and data source used for development,
and prospective/external clinical validation would be required before any
clinical use. These statements appear verbatim in the app interface and
repository.

## 12. Timeline

Weeks 1–2 data access and cohort curation; weeks 3–4 modeling and
evaluation; week 5 figures and manuscript; week 6 internal review,
preprint, and code release; weeks 7–8 journal and abstract submission.

## 13. Amendments

Any deviation from this plan will be recorded in the repository CHANGELOG
with date and rationale, and substantive deviations disclosed in the
manuscript. Preregistration constrains silent changes, not transparent,
justified ones.

## 14. Future extensions (out of scope here)

Multimodal extension integrating molecular data (e.g., TCGA colorectal
cohorts) toward biomarker discovery; external validation on an independent
clinical cohort with a collaborating institution.

---

### References

[1] Siegel RL, Wagle NS, Jemal A. Leading cancer deaths in people younger
than 50 years. JAMA. 2026;335(7):632-634. doi:10.1001/jama.2025.25467.
PMID 41569583.
[2] Jayakrishnan T, Ng K. Early-onset gastrointestinal cancers: a review.
JAMA. 2025;334(15):1373-1385. doi:10.1001/jama.2025.10218. PMID 40674064.
[3] American Cancer Society. Mortality under 50 declines for 4 of 5
leading cancers in U.S., but colorectal now top cancer killer, new ACS
study finds [press release]. January 22, 2026. ACS newsroom, cancer.org.
[3b] Siegel RL, Wagle NS, Cercek A, Smith RA, Jemal A. Colorectal cancer
statistics, 2023. CA Cancer J Clin. 2023;73(3):233-254.
doi:10.3322/caac.21772.
[4] Collins GS, et al. TRIPOD+AI statement: updated guidance for reporting
clinical prediction models that use regression or machine learning
methods. BMJ. 2024;385:e078378.
[5] Yuan L, Wang L, Gao J, et al. OncoE25: an AI model for predicting
postoperative prognosis in early-onset stage I–III colon and rectal
cancer — a population-based study using SEER with dual-center cohort
validation. J Transl Med. 2025;23(1):695. doi:10.1186/s12967-025-06663-4.
PMID 40545536. [verified Aug 2026]
[6] Li W, Liu J, Lan Y, Yu D, Zhang B. Development and validation of
survival prediction tools in early and late onset colorectal cancer
patients. Sci Rep. 2025;15(1):12864. doi:10.1038/s41598-025-95385-0.
PMID 40229310. [verified Aug 2026]
[7] Zhao Y, Li C, Shu C, Wu Q, Li H, Xu C, Li T, Wang Z, Luo Z, He Y.
Tackling small sample survival analysis via transfer learning: a study of
colorectal cancer prognosis. Artif Intell Med. 2026;178:103426.
doi:10.1016/j.artmed.2026.103426. PMID 42019107.
[8] Rasheed A, Khan NA, Naseem Y, Mushtaq HA, Elfeki ASAM. The role of
machine learning in predicting outcomes of gastrointestinal cancer. J Med
Health Sci Rev. 2025;2(2):5215. (Khan NA, corresponding author.)
[9] Ibadin FE, Khan NA, Mangrio SNA, Sharif M, Kumar S, Zuluaga Zuluaga M,
Omana Contreras NJ. Artificial intelligence in ENT: optimizing surgical
outcomes in thyroid cancer treatment. SEEJPH. 2025;XXVI(S3):446-460.
[10] Riley RD, Ensor J, Snell KIE, Harrell FE Jr, Martin GP, Reitsma JB,
Moons KGM, Collins G, van Smeden M. Calculating the sample size required
for developing a clinical prediction model. BMJ. 2020;368:m441.
doi:10.1136/bmj.m441. PMID 32188600.

*Additional competing and adjacent studies are catalogued with
verification status in docs/literature_check_notes.md; every entry must be
independently verified on PubMed before citation in the manuscript.*
