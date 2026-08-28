# Literature Check Notes — Focused Pre-Registration Review (Aug 2026)

Purpose: record of the honesty check behind Protocol v2.0's narrowed
novelty claim. **Rule: every entry below must be opened and verified on
PubMed/the journal site by the PI before it is cited in any manuscript.**
The list originated from an AI-assisted search; two load-bearing entries
were independently verified on Aug 12, 2026 (marked VERIFIED). The rest
are UNVERIFIED until the PI confirms them.

## Verified anchors

| # | Citation | What it did | How we differ |
|---|---|---|---|
| A1 | **VERIFIED** — Yuan L, Wang L, Gao J, et al. OncoE25: an AI model for predicting postoperative prognosis in early-onset stage I–III colon and rectal cancer. J Transl Med. 2025;23(1):695. doi:10.1186/s12967-025-06663-4 | EO stage I–III postoperative CSS; SEER with **random 7:3 split**; 6 ML models, RSF chosen; external validation in 2 Chinese hospital EO cohorts; SHAP; DCA; online calculator | We: **temporal** validation; full-stage population incl. distant; **frozen AO-trained model applied to identical EO test set** with paired deltas; prespecified calibration-degradation criteria; recalibration-repair analysis. Cite and discuss explicitly — this is the closest paper. |
| A2 | **VERIFIED** — Zhao Y, Li C, Shu C, et al. Tackling small sample survival analysis via transfer learning: colorectal cancer prognosis. arXiv:2501.12421 (2025); journal version reportedly 2026 — confirm final citation | SEER stage I CRC (n=27,379) as **source**, fine-tuned to 728 West China Hospital patients; DeepSurv/DeepHit/Cox-CC/RSF + new transfer survival forest | Institution/country transfer with **fine-tuning**; not age-group transportability of frozen models, no EO focus, no calibration-repair framing. Distinguish in Discussion. |

## Verified in the v3.0 audit (Aug 2026)

| # | Citation | What it did | How we differ |
|---|---|---|---|
| A3 | **VERIFIED** — Li W, Liu J, Lan Y, Yu D, Zhang B. Development and validation of survival prediction tools in early and late onset colorectal cancer patients. Sci Rep. 2025;15(1):12864. doi:10.1038/s41598-025-95385-0. PMID 40229310 | Separate ML survival calculators for EOCRC and LOCRC (SEER-derived data 2010-2021 + small Chinese external cohort); classification-style AUC metrics | Builds one model per age group; does NOT freeze the older-onset model and apply it to EO patients, quantify a transport gap against prespecified criteria, or test recalibration; random split, not temporal. Cite in Discussion. |
| A4 | **VERIFIED (publisher page)** — Explainable AI for colorectal cancer mortality and risk factor prediction in Korea: a nationwide cancer cohort study. Int J Med Inform. 2025 (Korean NHIS-derived cancer cohort; LightGBM; SHAP; subgroup analysis by age at diagnosis) — likely the paper behind U4; confirm PMID before citing | XAI mortality prediction with SHAP across age-at-diagnosis subgroups (non-SEER, Korea) | Age-related SHAP differences are examined, so our H4 contrast is framed as descriptive/confirmatory, not novel; no frozen cross-age transport or recalibration analysis. |
| A5 | **VERIFIED** — Lee et al. Synthetic data improve survival status prediction models in early-onset colorectal cancer. JCO Clin Cancer Inform. 2024. PMID 38271642 | Synthetic-data augmentation for EOCRC survival-status models | Different question (data augmentation); confirms active EOCRC-ML field; no transport/recalibration framing. |

## Unverified entries from the AI-assisted search (PI must click each)

Statuses: U = unverified. Treat titles/PMIDs as possibly garbled until
opened. Known issue: original item [12] linked to a PubMed *funding
search URL*, not an article — locate the real paper or drop it.

| # | Claimed paper (year) | Claimed relevance | Status |
|---|---|---|---|
| U1 | 5-yr postoperative survival, stage III CRC, interpretable ML, SEER (2025) — PMID 40727467 | Methods overlap only | U |
| U2 | Competing risk + RSF, elderly stage I–III CRC (2025) — PMID 40624131 | Different population | U |
| U3 | Time-to-event ML for CRC survival: RSF/GBM/Cox-Time/N-MTLR (2023) — PMC10636616 | Survival-ML overlap | U |
| U4 | Explainable AI for CRC mortality; age-related differences in feature importance (2025) — PMID 41066920 | Overlaps our H4 (SHAP contrast) — if confirmed, cite and frame H4 as confirmatory/descriptive | U (priority) |
| U5 | SEER CRC survival prediction with imbalance methods (2025) — PMC12032297 | Prediction overlap | U |
| U6 | Immune-based EOCRC prognostic model (2026) — PMID 41608336 | Different data/question | U |
| U7 | ML prediction of EOCRC occurrence (2025) — PMID 41139529 | Risk of disease, not prognosis | U |
| U8 | EHR-based EOCRC detection <45 (2025) — PMID 40537065 | Detection, not prognosis | U |
| U9 | EOCRC prediction with ML/LLMs, prediagnosis data (2025) — PMID 41726501 | Detection, not prognosis | U |
| U10 | ML for nonlocalized early-onset T1 CRC (2025) — original link malformed (funding-search URL); find real citation | Different endpoint | U (fix link) |
| U11 | Metastatic EOCRC OS/CSS prediction models (2023) — PMID 37067609 | EOCRC survival prediction exists — supports narrowed claim | U |
| U12 | EOCRC cancer-specific survival nomogram, SEER (2022) — PMID 35524790 | Classical model, same endpoint | U |
| U13 | Conditional survival nomograms, stage I–III EOCRC (2023) — PMID 36385679 | Same population/outcome, different framework | U |
| U14 | EOCRC nomogram, LN metastasis + CSS, n=22,405, calibration + DCA (2023) — PMID 37183238 | Rigor-package overlap | U |

## Standing conclusions (Protocol v2.0)

1. Never claim ML survival prediction in EO-CRC is new — it is not (A1,
   U11–U14).
2. Never claim EO-vs-older comparison is new (A1) or that SHAP age
   contrasts are new (U4, pending verification).
3. The defensible novelty: **frozen AO-trained → identical EO test set →
   paired discrimination + calibration degradation → prespecified
   criteria → recalibration repair**, under temporal validation, in a
   U.S. full-stage population. No duplicate identified as of Aug 2026.
4. Re-run this search the week of manuscript submission — the field moves
   monthly.
5. v3.0 re-check (Aug 2026): searches across "EOCRC ML survival SEER",
   "transportability/external validation CRC survival", "OncoE25",
   "age-related SHAP CRC", and "frozen model early-onset" surfaced no
   study performing the frozen AO->EO transport + prespecified
   degradation criteria + recalibration under temporal validation.
   Standing conclusion 3 unchanged.

## v4.0 re-check — Aug 18, 2026

Search families run (web/PubMed-oriented): "early-onset colorectal cancer"
machine learning survival SEER; EOCRC vs late-onset parallel models;
frozen model transportability CRC survival; calibration recalibration
external validation CRC survival model; temporal validation SEER CRC
survival ML; transfer learning colorectal cancer prognosis 2026 (SEER ->
hospital, synthetic/source -> target); explainable ML CRC age subgroups.
Result: the Zhao et al. transfer-learning work remains located only as
arXiv:2501.12421 (no PubMed-indexed 2026 journal version confirmed by us -
PI to verify). Transfer-learning papers perform institution/domain
adaptation WITH fine-tuning on target data; none evaluates a FROZEN
AO-trained prognostic model transported without refitting into EO-CRC
with prespecified degradation criteria and recalibration under temporal
validation. Closest studies unchanged: OncoE25 (A1), Li 2025 (A3), Korean
XAI age subgroups (A4).

Approved wording: "To our knowledge, in a focused literature review, prior
work explicitly evaluating the transportability and recalibration of
survival machine-learning models developed in average-onset colorectal
cancer when applied without refitting to early-onset colorectal cancer
remains limited." Never: first / first-ever / unprecedented / unique / novel.
