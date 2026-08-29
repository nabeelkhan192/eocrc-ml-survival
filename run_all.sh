#!/usr/bin/env bash
# Run the pipeline.
# MODE is decided by the presence of data/raw/seer_crc_export.csv:
#   absent  -> SYNTHETIC pipeline test: full pipeline 00-07 end-to-end
#              (outputs to results/synthetic/, figures watermarked)
#   present -> REAL SEER analysis: Stages 01-02 ONLY, then a hard stop at
#              the prespecified pre-model gate. Stages 03-07 run only via
#              run_models.sh after the horizon decision is recorded.
# Synthetic data is never (re)generated when a real export is present.
set -e
cd "$(dirname "$0")"

if [ -f data/raw/seer_crc_export.csv ]; then
  echo "=============================================================="
  echo "  MODE: REAL SEER DATA  ->  results/seer/  figures/seer/"
  echo "  This command runs ONLY Stage 01 (cohort) and Stage 02"
  echo "  (descriptives + follow-up adequacy), then stops."
  echo "=============================================================="
  python src/01_build_cohort.py
  python src/02_descriptives.py
  echo ""
  echo "=============================================================="
  echo "  REAL SEER PRE-MODEL GATE REACHED."
  echo ""
  echo "  Review results/seer/followup_adequacy.csv."
  echo ""
  echo "  Apply the preregistered adequacy rule:"
  echo "   * If share_of_event_free_with_followup_lt_horizon > 0.50 in"
  echo "     either the EO or AO temporal-test group at 60 months, set"
  echo "     the primary horizon to 36 months (HORIZON_MONTHS in"
  echo "     src/config.py)."
  echo "   * Otherwise retain 60 months."
  echo ""
  echo "  Also evaluate EO-training events per parameter (EPP) from the"
  echo "  Stage-02 descriptives; if EPP < 20, apply the protocol S9"
  echo "  deterministic feature-priority fallback."
  echo ""
  echo "  Record the decision in docs/CHANGELOG.md and lock the horizon"
  echo "  BEFORE running Stage 03 or any later analysis:"
  echo "      bash run_models.sh --horizon-locked"
  echo ""
  echo "  No model has been fitted or evaluated by this command."
  echo "=============================================================="
  exit 0
fi

echo "=============================================================="
echo "  MODE: SYNTHETIC PIPELINE TEST  (no scientific conclusions)"
echo "  ->  results/synthetic/  figures/synthetic/  (watermarked)"
echo "=============================================================="
python src/00_make_synthetic_data.py
python src/01_build_cohort.py
python src/02_descriptives.py
python src/03_models.py
python src/04_evaluate.py
python src/05_shap_explain.py
python src/06_decision_curves.py
python src/07_recalibration.py
echo ""
echo "Pipeline complete. See results/ and figures/ (per-mode subfolders)."
