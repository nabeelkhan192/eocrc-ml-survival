# Prespecified interpretation of real-data results

**Study:** Age-group transportability of explainable machine-learning models for cancer-specific
survival in early-onset colorectal cancer: a temporally validated U.S. SEER study
**Preregistration:** OSF 7g538 (29 Aug 2026), protocol archived in the immutable registration
**Analysis provenance:** gate decision `def6c29` → model execution `f7d5b6d` (14 Sep 2026)
**Prepared:** 14 Sep 2026
**Scope:** primary Stages 03–07 results only. Prespecified sensitivity analyses (2)–(6), recorded as
*not yet executed* at v4.1.1, have not been audited for completion. This memo does not assert that
the full preregistered analysis is complete.

Every criterion below was fixed before any outcome data were analysed. Nothing in this document
changes the preregistered plan; it records the result of applying that plan.

---

## Prespecified criteria, as written

**Transportability degradation is material (protocol §7.4) if ANY of:**

| | Criterion |
|---|---|
| (a) | paired ΔC-index ≥ 0.02 favouring the EO-trained model, 95% CI excluding 0 |
| (b) | AO-trained calibration slope on EO test data outside 0.80–1.20 |
| (c) | \|CITL\| > 0.20 (log-odds scale) at the primary horizon |

**H1** is disjunctive as written: degraded discrimination **and/or** material miscalibration.

**Recalibration is adequate (H2)** only if calibration slope is within 0.90–1.10 **and**
\|CITL\| ≤ 0.10, in the EO test window, with all parameters fitted on EO training data only.

**Primary horizon:** 60 months, locked at the Stage-02 gate before any model was fitted.

---

## H1 — Transportability

### Discrimination limb

| Metric | Prespecified materiality threshold | Observed (EO − AO) | 95% CI | Assessment |
|---|---|---|---|---|
| Cox paired ΔC | §7.4(a): ≥ 0.02, CI excl. 0 | **+0.0001** | −0.0014 to +0.0014 | criterion (a) not met |
| XGB-Cox paired ΔC | §7.4(a): ≥ 0.02, CI excl. 0 | **−0.0014** | −0.0027 to −0.0003 | criterion (a) not met |
| Cox paired Δtd-AUC @36m | none defined in §7.4 | +0.0012 | −0.0007 to +0.0028 | near-zero difference |
| Cox paired Δtd-AUC @60m | none defined in §7.4 | +0.0003 | −0.0015 to +0.0021 | near-zero difference |
| XGB-Cox paired Δtd-AUC @36m | none defined in §7.4 | −0.0021 | −0.0034 to −0.0006 | near-zero difference |
| XGB-Cox paired Δtd-AUC @60m | none defined in §7.4 | −0.0010 | −0.0026 to +0.0007 | near-zero difference |
| XGB-h paired Δbinary ROC-AUC *(secondary)* | none defined in §7.4 | −0.0015 | −0.0033 to +0.0002 | near-zero difference |

§7.4(a) defines the 0.02 materiality threshold for the **paired ΔC-index only**. The paired
time-dependent AUC and the secondary binary ROC-AUC are prespecified discrimination measures under
H1, but no separate materiality threshold is defined for them in §7.4. They are reported here as
observed differences with confidence intervals, not judged against a 0.02 benchmark.

Absolute discrimination on the identical EO test set: Cox EO-trained C = 0.845 (0.838–0.851),
Cox AO-trained frozen C = 0.844 (0.837–0.851); XGB-Cox EO-trained C = 0.852 (0.846–0.859),
AO-trained frozen C = 0.854 (0.849–0.859).

**Criterion (a) is not met by either survival model.** The XGB-Cox paired ΔC confidence interval
excludes zero, but the observed difference (−0.0014) is far below the prespecified 0.02 materiality
threshold and favours the frozen AO-trained model. The Cox paired ΔC (+0.0001) has a confidence
interval spanning zero.

The paired time-dependent AUC differences are separately numerically very small (absolute
differences 0.0003–0.0021), some with confidence intervals excluding zero; no materiality threshold
was prespecified for these measures, so they are reported by magnitude and uncertainty rather than
classified. With 9,551 EO test patients and paired resampling, very small differences can be
statistically detectable. For paired ΔC, the prespecified materiality threshold prevents statistical
detectability from being conflated with the study-defined criterion for material transport
degradation.

### Calibration limb

Transported AO fixed-horizon classifier on EO test patients:

| Criterion | Threshold | Observed | Verdict |
|---|---|---|---|
| (b) calibration slope | outside 0.80–1.20 | **0.902** | within range — not met |
| (c) \|CITL\| | > 0.20 | **+0.413** | exceeds — **met** |

Also: AUC 0.901, Brier 0.1246, observed − expected +0.0442.

### H1 verdict

**Supported**, on the calibration limb only, via criterion (c). Discrimination transported
essentially without loss; absolute risk calibration of the transported model met the prespecified
material-miscalibration criterion.

### Required qualification

The §7.4 criteria assess the transported AO model against absolute thresholds. They contain no
comparison against the EO-trained model's own calibration. On the identical patients:

| Model | Population | CITL | Exceeds 0.20? |
|---|---|---|---|
| XGB, EO-trained | EO test | +0.300 | yes |
| XGB, AO-trained (frozen) | EO test | +0.413 | yes |
| XGB, AO-trained | AO test | +0.384 | yes |
| Logistic, EO-trained | EO test | +0.444 | yes |
| Logistic, AO-trained | AO test | +0.418 | yes |

Every fixed-horizon model shown above under-predicts 5-year cancer-specific death in the 2017–2019
test window, including models evaluated in their own age group without cross-age transport. The
primary transported survival-model evaluation (full Cox and XGB-Cox) did not report fixed-horizon
CITL, and those outputs are therefore not included in this table. RSF was a within-group comparator
and was not transported under the preregistered analysis plan. Descriptively, the AO model's
CITL differs by approximately 0.03 on the log-odds scale between its own test population (+0.384)
and the EO test population (+0.413), against an overall level of miscalibration roughly an order of
magnitude larger.

**The prespecified criterion is satisfied. The inference that transport caused the miscalibration is
not supported by these data and must not be drawn.** No causal contribution is quantified here; the
design does not support decomposing the observed CITL into transport and non-transport components.
The defensible statement is that substantial calibration-in-the-large error was present in the
temporal test window across the fixed-horizon models evaluated here, including models evaluated
within their own age group, so age-group transport cannot be identified as the sole explanation.

---

## H2 — Recalibration

All parameters fitted on EO training-window data only; evaluated once in the EO test window.
Adequacy requires slope 0.90–1.10 **and** \|CITL\| ≤ 0.10.

| Family | Variant | Slope | CITL | Brier | Adequate |
|---|---|---|---|---|---|
| horizon | AO raw (frozen) | 0.902 | +0.413 | 0.1246 | **No** |
| horizon | AO + intercept | 0.902 | +0.296 | 0.1233 | **No** |
| horizon | AO + intercept & slope | 0.945 | +0.294 | 0.1232 | **No** |
| cox | AO Breslow baseline re-estimated | 1.352 | +0.235 | 0.1344 | **No** |
| cox | AO lp-slope (b = 1.220) + baseline | 1.081 | +0.345 | 0.1341 | **No** |

**H2 verdict: not supported.** No variant met the prespecified adequacy range. Slope was brought
into range by the intercept-and-slope update (0.945) and by lp-slope recalibration (1.081), but
CITL remained at roughly 0.23–0.35 throughout, against a required ≤ 0.10.

Brier scores are reported per variant in the table above. They are **not** comparable across the
horizon (XGBoost) and Cox families, which use different models and different absolute-risk
constructions. The preregistered transport evaluation did not define a raw transported Cox
absolute-risk prediction at the fixed horizon: Cox transport was assessed through its relative-hazard
discrimination measures, while the recalibration stage estimated new baseline hazards from EO
training data (§7.5). Consequently there is no un-recalibrated transported Cox row against which the
two Cox variants could be compared, and only the three horizon-family rows form a valid within-model
recalibration sequence (0.1246 → 0.1233 → 0.1232).

Notable detail: an intercept-only update fitted and evaluated on the same data would drive CITL
toward zero by construction. When the update was fitted on the EO training window and evaluated
prospectively in the EO temporal test window, CITL decreased from +0.413 to +0.296 but did not reach
the prespecified adequacy range. This residual miscalibration cannot be uniquely attributed to
either age-group transport or temporal change. The underlying prediction model remained AO-trained,
while recalibration parameters were estimated from EO training data and evaluated in a later EO test
window; residual transport-related model mismatch, temporal change, case-mix differences, coding
changes, model misspecification, and the composition of the horizon-observable subcohort may all
contribute.

Per §7.5, the transported XGB-Cox output is a relative-hazard risk score without an estimated
baseline, and was therefore not included in the absolute-risk recalibration procedures. Its paired
ΔC was −0.0014, providing no evidence of a material discrimination loss under the prespecified
transportability criterion.

---

## H3 — EO-CRC model comparison

Paired ΔC-index versus the full-covariate Cox benchmark, identical EO test patients:

| Model | Paired ΔC vs Cox-full | 95% CI | CI excludes 0 |
|---|---|---|---|
| Summary-stage-only Cox | **−0.0556** | −0.0600 to −0.0511 | yes |
| XGB-Cox | +0.0078 | +0.0057 to +0.0100 | yes |
| Random survival forest | +0.0022 | +0.0005 to +0.0041 | yes |

Within-group C-index, EO test: Cox-full 0.845, stage-only Cox 0.789, XGB-Cox 0.852, RSF 0.847.
AO test for reference: 0.843, 0.787, 0.857, 0.851.

**H3 result.** The full clinicopathologic Cox model discriminated substantially better than the
summary-stage-only model, with a paired C-index difference of −0.0556 for stage-only Cox. XGB-Cox
and random survival forest showed statistically detectable but small improvements over the full Cox
benchmark (+0.0078 and +0.0022 respectively). H3 prespecified neither a directional hypothesis nor a
materiality threshold, so these differences are reported by magnitude and uncertainty rather than
classified using the §7.4 transportability threshold. A +0.0078 C-index increment should be characterised
as a small improvement in discrimination, and should not be described as a large or clinically
meaningful machine-learning advantage without an external clinical benchmark.

*Scope note: H3 is preregistered as a comparison by paired ΔC-index with 95% paired-bootstrap CI,
without a directional hypothesis or its own materiality threshold. The §7.4 0.02 benchmark is
defined for transportability degradation only and is deliberately not applied here. Any later use of
it in an H3 context would be post hoc and by analogy, and must be labelled as such.*

---

## Prespecified descriptive analyses

**Decision-curve analysis** (EO temporal test set, horizon-observable subcohort, event prevalence
0.417): XGBoost and logistic models both exceed treat-all and treat-none across thresholds from
0.05 to 0.60, with XGBoost marginally above logistic. The curves cover EO-trained models only; no
transported-model comparison was produced. Whether a transported-model decision curve was
prespecified should be confirmed before the manuscript claims either its presence or its absence.

**Competing risks (Aalen-Johansen, descriptive).** Cancer-specific death incidence is similar
between groups, while other-cause death reaches approximately 0.28 in AO versus 0.065 in EO by
165 months. This illustrates the distinction between the cancer-specific and overall-survival
endpoints, and why the two age groups differ far more on overall survival than on cancer-specific
survival. The endpoint was prespecified before these curves were observed; they are reported as
description, not as retrospective justification of that choice.

**SHAP (model-attributed importance, descriptive only).** Both models rank summary stage, surgery,
node ratio, nodes examined, and CEA highest. `age_dx` ranks fourth in the AO model and does not
appear in the EO model's leading features, consistent with a compressed 18–49 age range. These are
attributions of the fitted models, not evidence of differing tumour biology, and the two scales are
not directly comparable.

---

## Limitations to carry into the manuscript

1. **Temporal shift confounds the absolute calibration criterion, not the paired discrimination
   comparison.** The paired ΔC and Δtd-AUC comparisons place the EO-trained and frozen AO-trained
   models on the identical EO test patients, so they isolate the effect of the training population
   reasonably well. The §7.4(c) criterion, by contrast, is an absolute threshold applied after a
   2010–2016 to 2017–2019 temporal shift affecting both groups. An AO-on-EO CITL failure can
   therefore reflect temporal drift as well as, or instead of, age-group transport — a reading
   supported by the EO-trained model's own CITL of +0.300.
2. **Horizon-observable share falls sharply between windows** (0.889 and 0.947 in training versus
   0.661 and 0.693 in test). Calibration is evaluated only among horizon-observable test patients.
   Whether this selection contributes to the observed under-prediction is a *post-hoc candidate
   explanation, not prespecified and not tested here.* It must be labelled as such wherever it
   appears.
3. **Materiality thresholds are study-specific interpretive benchmarks**, fixed in advance but not
   literature-derived or clinically validated. They should never be described as established
   clinical cutoffs.
4. **Grade coding changes at 2018**, and unknown-grade share is 19.2% overall, materially higher in
   the later window. CEA is unknown in 43.3%.
5. **Transport is assessed for the models named in §7 only** — cox_full, xgb_cox, and xgb_h.
   Stage-only Cox and RSF are within-group comparators and were not transported.
6. **SHAP attributions are descriptive** and carry no causal interpretation.

---

## What must not be done with these results

- No result-driven retuning, threshold change, model respecification, or unplanned reanalysis in
  response to what is reported above. The primary result stands as produced. This does **not**
  restrict prespecified sensitivity and secondary analyses still required by the frozen protocol:
  completing those is execution of the plan, not reanalysis, and their provenance is documented
  separately.
- No description of the discrimination finding as a machine-learning performance advantage.
- No attribution of transport degradation to tumour biology.
- No claim that recalibration succeeded, in any variant.
- No presentation of the truncation hypothesis as a finding.
