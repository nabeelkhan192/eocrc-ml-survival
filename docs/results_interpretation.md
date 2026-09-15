# Prespecified interpretation of real-data results

**Study:** Age-group transportability of explainable machine-learning models for cancer-specific
survival in early-onset colorectal cancer: a temporally validated U.S. SEER study
**Preregistration:** OSF 7g538 (29 Aug 2026), protocol archived in the immutable registration
**Analysis provenance:** gate decision `def6c29` → model execution `f7d5b6d` (14 Sep 2026)
**Prepared:** 14 Sep 2026

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

| Metric | Criterion (a) | Observed (EO − AO) | 95% CI | Verdict |
|---|---|---|---|---|
| Cox paired ΔC | ≥ 0.02, CI excl. 0 | **+0.0001** | −0.0014 to +0.0014 | not material |
| Cox paired Δtd-AUC @36m | ≥ 0.02, CI excl. 0 | +0.0012 | −0.0007 to +0.0028 | not material |
| Cox paired Δtd-AUC @60m | ≥ 0.02, CI excl. 0 | +0.0003 | −0.0015 to +0.0021 | not material |
| XGB-Cox paired ΔC | ≥ 0.02, CI excl. 0 | **−0.0014** | −0.0027 to −0.0003 | not material |
| XGB-Cox paired Δtd-AUC @36m | ≥ 0.02, CI excl. 0 | −0.0021 | −0.0034 to −0.0006 | not material |
| XGB-Cox paired Δtd-AUC @60m | ≥ 0.02, CI excl. 0 | −0.0010 | −0.0026 to +0.0007 | not material |
| XGB-h paired Δbinary ROC-AUC *(secondary)* | — | −0.0015 | −0.0033 to +0.0002 | not material |

Absolute discrimination on the identical EO test set: Cox EO-trained C = 0.845 (0.838–0.851),
Cox AO-trained frozen C = 0.844 (0.837–0.851); XGB-Cox EO-trained C = 0.852 (0.846–0.859),
AO-trained frozen C = 0.854 (0.849–0.859).

**Criterion (a) is not met by any model.** Two deltas have confidence intervals excluding zero
(XGB-Cox ΔC and Δtd-AUC @36m) and are therefore statistically detectable, but at 0.001–0.002 they
are roughly an order of magnitude below the materiality threshold, and both favour the *frozen
AO-trained* model. With 9,551 EO test patients and paired resampling, differences far too small to
matter are detectable; this is precisely the situation the prespecified threshold exists to handle.

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

Every model under-predicts 5-year cancer-specific death in the 2017–2019 test window, including
each model evaluated in its own population with no transport involved. The increment attributable
to crossing the age boundary is approximately +0.03 on the log-odds scale (AO-on-AO +0.384 versus
AO-on-EO +0.413), not the full +0.413.

**The prespecified criterion is satisfied. The inference that transport caused the miscalibration
is not supported by these data and must not be drawn.** The defensible statement is that absolute
risk calibration degraded in the later diagnosis window for every model, and that age-group
transport contributed little beyond that.

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
CITL remained at roughly 0.23–0.35 throughout, against a required ≤ 0.10. The two Cox variants
worsened the Brier score relative to the raw transported model.

Notable detail: an intercept-only update fitted and evaluated on the same data would drive CITL to
approximately zero by construction. Fitted on the EO *training* window, it moved test CITL only
from 0.413 to 0.296. The residual is what the training window fails to convey about the test
window — a train-to-test gap rather than an AO-to-EO gap, consistent with the pattern in the H1
qualification above.

Per §7.5, the transported XGB-Cox risk score is deliberately not recalibrated, since it is a
relative hazard without a baseline and its transport gap is a discrimination question. Its paired
ΔC was −0.0014: the one model excluded from recalibration on discrimination grounds turns out to
have no discrimination gap.

---

## H3 — EO-CRC model comparison

Paired ΔC-index versus the full-covariate Cox benchmark, identical EO test patients:

| Model | Paired ΔC vs Cox-full | 95% CI | CI excludes 0 | Magnitude ≥ 0.02 |
|---|---|---|---|---|
| Summary-stage-only Cox | **−0.0556** | −0.0600 to −0.0511 | yes | yes |
| XGB-Cox | +0.0078 | +0.0057 to +0.0100 | yes | no |
| Random survival forest | +0.0022 | +0.0005 to +0.0041 | yes | no |

Within-group C-index, EO test: Cox-full 0.845, stage-only Cox 0.789, XGB-Cox 0.852, RSF 0.847.
AO test for reference: 0.843, 0.787, 0.857, 0.851.

**H3 verdict.** The full clinicopathologic covariate set discriminates substantially better than
summary stage alone: a 0.056 C-index deficit for the stage-only model, exceeding the 0.02 benchmark
with a CI excluding zero. Nonlinear machine-learning models improve on the full Cox benchmark by
statistically detectable but immaterial margins (0.002–0.008). A +0.0078 C-index increment must not
be presented as a meaningful machine-learning advantage.

*Scope note: the 0.02 benchmark is defined in §7.4 for transportability degradation. Applying it to
H3 is by analogy rather than by direct prespecification, and should be described as such.*

---

## Prespecified descriptive analyses

**Decision-curve analysis** (EO temporal test set, horizon-observable subcohort, event prevalence
0.417): XGBoost and logistic models both exceed treat-all and treat-none across thresholds from
0.05 to 0.60, with XGBoost marginally above logistic. The curves cover EO-trained models only; no
transported-model comparison was produced. Whether a transported-model decision curve was
prespecified should be confirmed before the manuscript claims either its presence or its absence.

**Competing risks (Aalen-Johansen, descriptive).** Cancer-specific death incidence is similar
between groups, while other-cause death reaches approximately 0.28 in AO versus 0.065 in EO by
165 months. This supports the cancer-specific endpoint choice and explains why the overall-survival
curves diverge sharply while the cancer-specific curves do not.

**SHAP (model-attributed importance, descriptive only).** Both models rank summary stage, surgery,
node ratio, nodes examined, and CEA highest. `age_dx` ranks fourth in the AO model and does not
appear in the EO model's leading features, consistent with a compressed 18–49 age range. These are
attributions of the fitted models, not evidence of differing tumour biology, and the two scales are
not directly comparable.

---

## Limitations to carry into the manuscript

1. **The design cannot separate age-group shift from temporal shift.** Training is 2010–2016 and
   testing is 2017–2019 in both groups. The calibration findings are consistent with temporal
   drift affecting both populations rather than with age-group transport.
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

- No reanalysis, retuning, threshold change, or model respecification in response to what is
  reported above. The result stands as produced.
- No description of the discrimination finding as a machine-learning performance advantage.
- No attribution of transport degradation to tumour biology.
- No claim that recalibration succeeded, in any variant.
- No presentation of the truncation hypothesis as a finding.
