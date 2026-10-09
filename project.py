#!/usr/bin/env python
"""Task runner for the EOCRC-SEER study - operational automation only.

    python project.py status
    python project.py test
    python project.py baseline --archive "<first-run archive folder>"
    python project.py sensitivity exclude_rectal [--dry-run] [--rerun]
    python project.py sensitivity exclude_2019   [--dry-run] [--rerun]
    python project.py summarize [--out FILE]
    python project.py sensitivity-all [--out FILE]

This file computes nothing scientific. It checks guards, shells out to the
existing pipeline scripts exactly as a manual run would, and writes a
timestamped log plus a JSON record to logs/. If it were deleted, the study
would still run by hand; every log records the verbatim commands used.
Standard library only.
"""
import argparse
import sys
from pathlib import Path

from tools import guards, provenance, summarize
from tools.runlog import RunLog

ROOT = Path(__file__).resolve().parent
PYTEST = [sys.executable, "-m", "pytest", "tests/", "-q"]


# ================================================================== status
def cmd_status(args, argv) -> int:
    log = RunLog("status", argv)
    p = log.record["provenance"]
    mode = guards.base_mode()
    log.echo(f"\nbranch            {p['git_branch']}")
    log.echo(f"HEAD              {p['git_commit']}")
    log.echo(f"working tree      {'clean' if p['working_tree_clean'] else 'MODIFIED'}")
    for line in (p["working_tree_changes"] or [])[:15]:
        log.echo(f"                    {line}")
    log.echo(f"data mode         {mode} (raw SEER export "
             f"{'PRESENT' if guards.RAW_EXPORT.exists() else 'absent'})\n")
    ok = True
    ok &= log.check("frozen tag", *guards.check_frozen_tag())
    ok &= log.check("registered protocol unchanged", *guards.check_protocol_unchanged())
    ok &= log.check("horizon locked", *guards.check_horizon_locked())
    ok &= log.check("sensitivity rules recorded", *guards.check_changelog_rules_recorded())
    ok &= log.check("primary outputs", *guards.verify_primary_manifest(mode))
    sens_root = ROOT / "results" / "sensitivities"
    done = sorted(d.name for d in sens_root.iterdir()
                  if d.is_dir() and any(d.rglob("*.csv"))) if sens_root.exists() else []
    log.echo(f"\nsensitivity outputs present: {', '.join(done) if done else 'none'}")
    return log.finish(0 if ok else 1,
                      "STATUS OK" if ok else "STATUS: one or more checks FAILED (see above)")


# ================================================================== baseline
def cmd_baseline(args, argv) -> int:
    log = RunLog("baseline", argv)
    log.echo(f"\ncomparing primary outputs with archive: {args.archive}\n")
    ok, lines = guards.create_baseline(Path(args.archive))
    for ln in lines:
        log.echo(ln)
    return log.finish(0 if ok else 1, "BASELINE OK" if ok else "BASELINE NOT CREATED")


# ================================================================== test
def cmd_test(args, argv) -> int:
    log = RunLog("test", argv)
    rc = log.run(PYTEST, env_drop=("EOCRC_SENSITIVITY",))
    log.record["pytest"] = "passed" if rc == 0 else f"FAILED (exit {rc})"
    return log.finish(rc, "TESTS PASSED" if rc == 0 else "TESTS FAILED")


# ================================================================== sensitivity
HORIZON_NOTE = (
    "NOTE: the horizon is LOCKED at 60 months for every sensitivity (CHANGELOG "
    "v4.1.4, Rule 1). Any 36-month follow-up-adequacy warning printed by "
    "02_descriptives.py during this run is to be IGNORED. The protocol S9 "
    "fallback does not fire inside a sensitivity (Rule 2).")


def cmd_sensitivity(args, argv) -> int:
    name = args.mode
    log = RunLog(f"sensitivity {name}", argv)

    # 1. closed allow-list - hard fail on anything else, before any check runs
    if name not in guards.ALLOWED_SENSITIVITIES:
        why = ("deliberately NOT implemented: its operational definition is not "
               "determined by the frozen protocol (see CHANGELOG v4.1.4)"
               if name in guards.DEFERRED_SENSITIVITIES else "unknown mode")
        return log.finish(2, f"REFUSED: sensitivity {name!r} is {why}. Allowed: "
                             + ", ".join(guards.ALLOWED_SENSITIVITIES) + ".")

    mode = guards.base_mode()
    data_mode = f"{mode}_{name}"
    sens_results = ROOT / "results" / "sensitivities" / data_mode
    sens_figures = ROOT / "figures" / "sensitivities" / data_mode
    sens_cohort = ROOT / "data" / "processed" / "sensitivities" / f"cohort_{data_mode}.parquet"
    for pth in (sens_results, sens_figures, sens_cohort):
        guards.assert_not_protected(pth)   # sensitivity targets must never be protected

    # 2. guards
    log.echo("\n--- pre-run checks")
    tree_clean = log.record["provenance"]["working_tree_clean"]
    ok = True
    ok &= log.check("working tree clean", bool(tree_clean),
                    "" if tree_clean else "commit or stash changes first")
    ok &= log.check("frozen tag", *guards.check_frozen_tag())
    ok &= log.check("registered protocol unchanged", *guards.check_protocol_unchanged())
    ok &= log.check("horizon locked", *guards.check_horizon_locked())
    ok &= log.check("sensitivity rules recorded", *guards.check_changelog_rules_recorded())
    primary_cohort = ROOT / "data" / "processed" / f"cohort_{mode}.parquet"
    ok &= log.check("primary cohort present", primary_cohort.exists(),
                    primary_cohort.relative_to(ROOT).as_posix())
    ok &= log.check("primary outputs", *guards.verify_primary_manifest(mode))
    already = sens_results.exists() and any(sens_results.rglob("*.csv"))
    ok &= log.check("no previous run of this sensitivity",
                    (not already) or args.rerun,
                    "outputs exist; pass --rerun to deliberately overwrite THIS "
                    "sensitivity's outputs" if already and not args.rerun else "")
    stages = guards.run_models_stages()
    ok &= log.check("stage list read from run_models.sh", len(stages) == 5,
                    ", ".join(Path(s).stem for s in stages))
    if not ok:
        return log.finish(1, "REFUSED: pre-run checks failed. Nothing was executed.")

    env = {"EOCRC_SENSITIVITY": name}
    builder = [sys.executable, "src/08_make_sensitivity_cohort.py"] + (
        ["--force"] if args.rerun else [])
    plan = [builder, [sys.executable, "src/02_descriptives.py"]] + [
        [sys.executable, s] for s in stages]

    if args.dry_run:
        log.echo("\n--- DRY RUN: commands that would execute (nothing run)")
        for cmd in plan:
            log.echo(f"  EOCRC_SENSITIVITY={name} " + " ".join(
                [Path(cmd[0]).name] + cmd[1:]))
        log.echo(f"\n{HORIZON_NOTE}")
        return log.finish(0, "DRY RUN OK: all checks passed.")

    # 3. tests must pass before any real execution
    log.echo("\n--- test suite")
    rc = log.run(PYTEST, env_drop=("EOCRC_SENSITIVITY",))
    log.record["pytest"] = "passed" if rc == 0 else f"FAILED (exit {rc})"
    if rc != 0:
        return log.finish(1, "REFUSED: tests failed. Nothing was executed.")

    # 4. execute, with primary outputs hashed before and after
    targets = guards.primary_output_targets(mode)
    before = guards.hash_outputs(targets)
    log.echo(f"\n--- executing ({len(before)} primary files hashed)\n{HORIZON_NOTE}")
    failed = None
    for cmd in plan:
        if log.run(cmd, env_extra=env) != 0:
            failed = Path(cmd[1]).name
            break

    after = guards.hash_outputs(targets)
    changes = guards.diff_hashes(before, after)
    log.echo("\n--- post-run checks")
    intact = log.check("primary outputs untouched by this run", not changes,
                       "; ".join(changes[:10]))
    if mode == "seer":
        intact &= log.check("primary outputs vs manifest",
                            *guards.verify_primary_manifest(mode))

    for pth in (sens_results, sens_figures, sens_cohort):
        if pth.exists():
            log.record["output_paths"].append(pth.relative_to(ROOT).as_posix())
    log.echo("outputs:\n  " + "\n  ".join(log.record["output_paths"]))
    log.echo("  (preds/ and models/ inside the results folder are per-patient: "
             "never share or commit)")
    log.echo(f"\n{HORIZON_NOTE}")

    if not intact:
        return log.finish(3, "ALERT: PRIMARY OUTPUTS CHANGED. Restore them from "
                             "the external first-run archive before anything else.")
    if failed:
        return log.finish(1, f"FAILED at {failed}. Primary outputs are intact.")
    return log.finish(0, f"SENSITIVITY {name} COMPLETE. Primary outputs intact.")


# ================================================================== summarize
DEFAULT_REVIEW_FILE = ROOT / "logs" / "sensitivity_results_for_review.txt"


def cmd_summarize(args, argv) -> int:
    log = RunLog("summarize", argv)
    out = Path(args.out) if args.out else DEFAULT_REVIEW_FILE
    written, warnings = summarize.build(out)
    log.record["output_paths"].append(str(out))
    log.echo(f"\nsections included: {', '.join(written) if written else 'none'}")
    for w in warnings:
        log.echo(f"  small cell: {w}")
    if not written:
        return log.finish(1, "NOTHING TO SUMMARIZE: no primary or sensitivity outputs found.")
    msg = f"REVIEW FILE WRITTEN: {out}"
    if warnings:
        msg += (f"\n{len(warnings)} count cell(s) below {summarize.SMALL_CELL} are "
                "flagged at the top of the file. Check them before sharing.")
    return log.finish(0, msg)


# ================================================================== sensitivity-all
# A sensitivity counts as completed only when the evaluation (stage 04) and
# recalibration (stage 07) tables both exist; an earlier run that stopped after
# the cohort filter or descriptives is "partial" and is completed, not skipped.
COMPLETE_MARKERS = ("transportability_paired.csv", "recalibration.csv")


def sensitivity_state(folder: Path) -> str:
    if not folder.exists() or not any(folder.rglob("*.csv")):
        return "none"
    if all((folder / m).exists() for m in COMPLETE_MARKERS):
        return "complete"
    return "partial"


def cmd_sensitivity_all(args, argv) -> int:
    """Run each allowed sensitivity that has not been run, then summarize.

    Never reruns a sensitivity that already has outputs (each is executed once);
    each run goes through the full guarded `sensitivity` command.
    """
    mode = guards.base_mode()
    results = {}
    for name in guards.ALLOWED_SENSITIVITIES:
        folder = ROOT / "results" / "sensitivities" / f"{mode}_{name}"
        state = sensitivity_state(folder)
        if state == "complete":
            print(f"\n=== {name}: already completed - skipped (never rerun automatically)")
            results[name] = "skipped (already completed)"
            continue
        if state == "partial":
            print(f"\n=== {name}: an earlier run stopped before the models finished "
                  "(cohort/descriptives only). Completing it; this overwrites only "
                  "this sensitivity's partial outputs.")
        else:
            print(f"\n=== {name}: running")
        sub = argparse.Namespace(mode=name, dry_run=False, rerun=(state == "partial"))
        rc = cmd_sensitivity(sub, ["project.py", "sensitivity", name])
        results[name] = "complete" if rc == 0 else f"FAILED (exit {rc})"
        if rc != 0:
            print(f"\nStopped: {name} did not complete. Nothing further was run.")
            break
    rc = 0 if all(not v.startswith("FAILED") for v in results.values()) else 1
    if rc == 0:
        rc = cmd_summarize(argparse.Namespace(out=args.out),
                           ["project.py", "summarize"] + (["--out", args.out] if args.out else []))
    print("\n=== SUMMARY")
    for k, v in results.items():
        print(f"  {k:16s} {v}")
    return rc


# ================================================================== main
def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # never crash on a console codepage
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(
        prog="project.py",
        description="EOCRC-SEER task runner (guards + logs; no scientific code).")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="read-only repo and integrity check (writes only its own log)")
    sub.add_parser("test", help="run the test suite")
    b = sub.add_parser("baseline", help="check primary outputs against the "
                       "first-run archive and record the integrity baseline")
    b.add_argument("--archive", required=True,
                   help="archive folder containing results/ and figures/")
    s = sub.add_parser("sensitivity", help="run one prespecified sensitivity analysis")
    s.add_argument("mode", help="exclude_rectal | exclude_2019")
    s.add_argument("--dry-run", action="store_true",
                   help="run all checks and print the commands, execute nothing")
    s.add_argument("--rerun", action="store_true",
                   help="deliberately overwrite a previous run of THIS sensitivity")
    sm = sub.add_parser("summarize", help="collect aggregate result tables "
                        "into one review file (no per-patient data)")
    sm.add_argument("--out", help="output file (default logs/sensitivity_results_for_review.txt)")
    sa = sub.add_parser("sensitivity-all", help="run every allowed sensitivity "
                        "not yet run, then summarize")
    sa.add_argument("--out", help="review file path (as for summarize)")
    args = ap.parse_args(argv)
    handler = {"status": cmd_status, "test": cmd_test, "baseline": cmd_baseline,
               "sensitivity": cmd_sensitivity, "summarize": cmd_summarize,
               "sensitivity-all": cmd_sensitivity_all}[args.command]
    try:
        return handler(args, ["project.py", *argv])
    except guards.ProtectedPathError as exc:
        print(exc, file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
