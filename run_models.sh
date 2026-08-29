#!/usr/bin/env bash
# Stages 03-07: models, evaluation, SHAP, decision curves, recalibration.
# REAL SEER mode: refuses to run unless --horizon-locked is passed,
# confirming the Stage-02 follow-up-adequacy decision has been made and
# recorded in docs/CHANGELOG.md (see run_all.sh gate message).
# SYNTHETIC mode: runs without the flag (run_all.sh already covers the
# full synthetic pipeline; this script is a convenience re-run).
set -e
cd "$(dirname "$0")"

if [ -f data/raw/seer_crc_export.csv ] && [ "$1" != "--horizon-locked" ]; then
  echo "REAL SEER MODE: refusing to fit models."
  echo "Complete the Stage-02 gate first (bash run_all.sh), apply the"
  echo "adequacy rule, record the horizon decision in docs/CHANGELOG.md,"
  echo "then rerun:  bash run_models.sh --horizon-locked"
  exit 1
fi

python src/03_models.py
python src/04_evaluate.py
python src/05_shap_explain.py
python src/06_decision_curves.py
python src/07_recalibration.py
echo ""
echo "Stages 03-07 complete. See results/ and figures/ (per-mode subfolders)."
