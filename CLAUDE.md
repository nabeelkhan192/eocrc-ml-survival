# EOCRC-SEER transportability study — working rules

This is a **preregistered** study. The analysis plan was frozen and publicly registered on OSF
(7g538) on 29 Aug 2026 before any outcome data were analysed. The value of this project is its
provenance chain, not its speed. Read these rules before doing anything.

## Never touch

- `docs/protocol_OSF_preregistration.md` — the registered artifact. Never edit, for any reason.
- Anything at tag `v4.1.1-osf-final` (commit `a2c4869`).
- `data/raw/` — SEER data held under a Data Use Agreement. Never read into a commit, never copy,
  never print case-level rows.
- `results/*/preds/` and `results/*/models/` — per-patient predictions and fitted models. Never
  commit, never include in any package or summary.
- Thresholds, hypotheses, predictor definitions, the 60-month horizon, model specifications,
  bootstrap settings, or recalibration procedures. All frozen.

## Never do

- Never run the pipeline (`run_all.sh`, `run_models.sh`, any `src/0*.py`) unless explicitly asked
  in that message. These consume real patient data and write real results.
- Never commit or push. Propose changes; the human commits.
- Never re-run an analysis because a result looks wrong, surprising, or disappointing. A null
  result is a result. Retuning after seeing outcomes destroys the study.
- Never edit `docs/CHANGELOG.md` history. Append new dated entries only.
- Never reinterpret a prespecified criterion. If a rule's wording is ambiguous, say so and stop.

## Always do

- Read a file before editing it. Never patch from a fragment or from memory.
- Show the full diff before suggesting a commit.
- Run `python -m pytest tests/ -q` after any change to `src/` or `tests/`. 43 tests must pass.
- Say plainly when you are unsure, when you lack information, or when a request would cross one
  of the rules above. Stopping is always the right answer over guessing.
- Prefer the smallest change that works. This codebase is frozen; every diff line is a liability.

## Environment

- Windows. Run in `.venv` (Python 3.11.9), never conda `base` (which has drifted to 3.14).
  Activate: `.venv\Scripts\activate` (cmd) or `source .venv/Scripts/activate` (Git Bash).
- `src/` modules use flat imports, so scripts need `sys.path.insert(0, 'src')`.
- `run_all.sh` auto-detects mode from the presence of `data/raw/seer_crc_export.csv`. With the
  real export present it runs stages 01-02 only and hard-stops at the pre-model gate. That stop
  is deliberate. Do not automate across it.
- `EOCRC_SENSITIVITY=<mode>` routes all output to `results/sensitivities/<mode>/`. Allowed modes
  are `exclude_rectal` and `exclude_2019` only; everything else hard-fails by design.

## Current state (Sept 2026)

Primary analysis complete and interpreted. Commit chain: `a2c4869` (frozen preregistration) →
`def6c29` (pre-model gate decision, made before any model ran) → `f7d5b6d` (execution
provenance) → `0377af2`/`151cedd` (primary-results interpretation) → `a22ad8d` (sensitivity
execution-safety layer).

Outstanding: a v4.1.4 CHANGELOG entry for `a22ad8d`; a recorded decision that the horizon stays
locked at 60 months for all sensitivity analyses; a rule for whether the protocol S9 fallback may
fire inside a sensitivity. No sensitivity analysis has been run on real data.

## Good tasks for you

CI workflows, pre-commit hooks, the `tools/` automation layer, documentation, manuscript
drafting, reading code and explaining it, writing tests.

## Bad tasks for you

Anything that changes what gets computed, decides a scientific question, or executes the pipeline
without being asked in that specific message.