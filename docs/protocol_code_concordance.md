# Protocol-to-Code Concordance (Version 4.0)

Every prespecified analysis and where it is implemented. "§" = section of
docs/protocol_OSF_preregistration.md. Items marked *real-data stage* are
prespecified but only executable once SEER counts exist; nothing in this
repository claims they have already run.

| Prespecified element | Protocol | Implementation |
|---|---|---|
| Cohort inclusion/exclusion, ages 18-84, years 2010-2019, stage known, survival >= 1 mo | §4 | src/01_build_cohort.py apply_inclusion; config MIN_AGE/MAX_AGE/TRAIN_YEARS/TEST_YEARS/MIN_SURVIVAL_MONTHS |
| First-primary restriction (sequence 0/1) | §4 | SEER*Stat selection statement, data/README.md step 4 |
| EO = 18-49 / AO = 50-84 | §4 | config.EO_MAX_AGE; 01 derive_features |
| ICD-O-3 site/histology family | §4 | 01 ADENO_HISTOLOGIES / site handling (verify against dictionary before lock) |
| CSS outcome definition, censoring | §5 | 01 css_event / os_event construction |
| Fixed-horizon estimand: event = T <= H; observable = (E=1 & T<=H) or T>=H; secondary | §5, §7 | src/estimands.py horizon_labels/horizon_frame (single source; imported by 03, 07); tests/test_estimands_and_mapping.py::test_horizon_boundary_h60 |
| Follow-up adequacy rule (denominator = event-free patients; trigger > 0.50 in test) before any modeling | §5 | src/estimands.py event_free_short_followup_share; 02 followup_adequacy -> followup_adequacy.csv; test_adequacy_denominator_event_free_only |
| Year-spanning variable coalescing + coverage audit | §6 | config.COLUMN_MAP lists; 01 coalescing loader |
| Node ratio only when examined > 0 + indicator | §6 | 01 derive_features |
| Site groups incl. explicit Colon NOS/overlapping (C18.8/C18.9) | §6 | 01 map_site; test_site_nos_and_overlapping |
| Grade exact-dictionary mapping | §6 | 01 map_grade / GRADE_LABELS; test_grade_mapping, test_grade_I_never_captures_IV |
| Surgery Yes/No/Unknown (unknown never Yes) | §6 | 01 map_surgery; test_surgery_unknown_handling |
| Train-only imputation/encoding/constant-drop | §7.0 | utils_features.FeatureBuilder (fit on train; persisted) |
| Temporal split 2010-2016 / 2017-2019 | §7 | config.TRAIN_YEARS/TEST_YEARS; 01 split column |
| Models: stage-only Cox, full Cox, RSF (required on real data), XGB-Cox, fixed-horizon XGB + logistic | §7 | 03 fit_cox / fit_rsf (hard-fail on real data) / fit_xgb_cox / fit_xgb_h |
| XGB tune (inner-train FeatureBuilder, depth grid, early stopping) then REFIT on full development cohort with fixed depth/rounds | §7 | 03 tune_xgb_cox/fit_xgb_cox, tune_xgb_h/fit_xgb_h; *_hyperparams.json; test_xgb_final_model_trained_on_full_development_cohort |
| C-index + bootstrap CI; td-AUC 36/60 | §7 | 04 cindex_ci, td_auc -> model_performance_survival.csv |
| Calibration slope, CITL (offset-logistic), obs-minus-exp, Brier, decile plots | §7 | 04 calibration_metrics, calibration_plot -> model_performance_horizon.csv |
| PRIMARY paired transportability: frozen AO model incl. AO preprocessing, identical EO test; paired dC; paired d survival-model td-AUC @36/60; paired d binary ROC AUC (classifier) | §7 steps 1-3 | 03 transport block (fb_ao.transform); 04 paired_delta_c / paired_delta_td_auc / paired_delta_auc -> transportability_paired.csv; tests test_paired_delta_c_*, test_paired_delta_td_auc_* |
| H3: EO paired dC of each survival model vs full Cox | §2 H3 | 04 H3 block -> h3_eo_paired_deltaC.csv |
| Materiality criteria (study-specific labels) | §7 step 4 | protocol text; continuous outputs in 04/07 tables |
| Recalibration SCOPE: AO xgb_h -> (i) intercept, (ii) intercept+slope; AO cox_full -> (iii) baseline re-est, (iv) lp-slope; XGB-Cox/RSF not recalibrated; EO-train-only fitting | §7 step 5 | src/07_recalibration.py -> recalibration.csv, recalibration_params.json, figure |
| SHAP model-attributed importance + EO/AO contrast, scale caveat | §7, H4 | src/05_shap_explain.py -> shap_* figures, shap_mean_abs_importance.csv |
| DCA, exploratory 5-60% range, horizon-linked | §2, §7 | config.DCA_THRESHOLDS, HORIZON_MONTHS; src/06_decision_curves.py |
| Untouched test window | §7.0 | FeatureBuilder train-only fit; 03 internal-split tuning; 07 EO-train-only recalibration |
| Mode separation synthetic vs real | §10 | config.DATA_MODE routing; data_mode column; run_all.sh banners; watermarks |
| Events-per-parameter check / feature-reduction order | §9 | *real-data stage*; reduction order fixed in §9 |
| Competing risks: Aalen-Johansen cumulative incidence (descriptive; NO Fine-Gray) | §2, §8(1) | 02 cumulative_incidence -> cumulative_incidence.csv + figure |
| Overall survival: descriptive only (KM); no OS models prespecified | §2 | 01 os_event; KM in 02 (add OS curve at real-data stage from same function) |
| Integrated Brier score | — | NOT prespecified (removed v4.0; documented) |
| Sensitivity analyses (2)-(6): complete-case, rectal-excluded, 2019-excluded, COVID extension, stage I-III subgroup | §8 | *real-data stage*: documented cohort-filter re-runs of 01->07 |
| Research-use demonstration app (frozen models only; mode banner) | §11 | app/app.py; smoke-tested via streamlit AppTest |
| Unit tests for all v4 fixes | §7.0, §5, §6 | tests/ (23 tests, pytest) |
| TRIPOD+AI / STROBE checklists | §10 | docs/reporting_checklists.md (complete at manuscript stage) |
