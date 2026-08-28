#!/usr/bin/env bash
# Run the full pipeline end-to-end.
# MODE is decided by the presence of data/raw/seer_crc_export.csv:
#   absent  -> SYNTHETIC pipeline test (outputs to results/synthetic/,
#              figures/synthetic/, every figure watermarked)
#   present -> REAL SEER analysis (outputs to results/seer/, figures/seer/)
# Synthetic data is never (re)generated when a real export is present.
set -e
cd "$(dirname "$0")"

if [ -f data/raw/seer_crc_export.csv ]; then
  echo "=============================================================="
  echo "  MODE: REAL SEER DATA  ->  results/seer/  figures/seer/"
  echo "=============================================================="
else
  echo "=============================================================="
  echo "  MODE: SYNTHETIC PIPELINE TEST  (no scientific conclusions)"
  echo "  ->  results/synthetic/  figures/synthetic/  (watermarked)"
  echo "=============================================================="
  python src/00_make_synthetic_data.py
fi

python src/01_build_cohort.py
python src/02_descriptives.py     # includes the follow-up adequacy rule:
                                  # review results/<mode>/followup_adequacy.csv
                                  # BEFORE interpreting horizon analyses
python src/03_models.py
python src/04_evaluate.py
python src/05_shap_explain.py
python src/06_decision_curves.py
python src/07_recalibration.py
echo ""
echo "Pipeline complete. See results/ and figures/ (per-mode subfolders)."
