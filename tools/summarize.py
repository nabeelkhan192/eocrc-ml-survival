"""Build one aggregate-only results file for review (read-only on results/).

Collects a fixed allow-list of aggregate tables for each sensitivity that has
been run, plus the primary tables for comparison, into a single text file.
Per-patient material (preds/, models/), table1.csv and anything not on the
allow-list are never read. Count columns are scanned for small cells.
Standard library only.
"""
import csv
import datetime as _dt
import io
from pathlib import Path

from tools import guards, provenance

ROOT = Path(__file__).resolve().parents[1]

# Order matters: this is the order tables appear in the review file.
AGGREGATE_TABLES = (
    "sensitivity_cohort_flow.csv",
    "followup_adequacy.csv",
    "transportability_paired.csv",
    "model_performance_horizon.csv",
    "model_performance_survival.csv",
    "h3_eo_paired_deltaC.csv",
    "recalibration.csv",
)
NEVER = ("preds", "models")
# SEER's usual convention is not to report statistics based on fewer than 16
# cases. Cells below this are flagged, not altered.
SMALL_CELL = 16


def _is_count_column(name: str) -> bool:
    n = name.strip().lower()
    return n in {"n", "count", "events", "n_events"} or n.startswith("n_")


def small_cells(rows: list[dict]) -> list[str]:
    hits = []
    for i, row in enumerate(rows, start=1):
        for col, val in row.items():
            if col is None or not _is_count_column(col):
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if 0 < v < SMALL_CELL:
                hits.append(f"row {i}, column {col!r} = {val}")
    return hits


def _safe_table(path: Path) -> Path:
    if path.name not in AGGREGATE_TABLES or any(p in NEVER for p in path.parts):
        raise PermissionError(f"refusing to read non-aggregate file: {path}")
    return path


def _render(path: Path) -> tuple[str, list[str]]:
    with open(_safe_table(path), newline="", encoding="utf-8") as fh:
        text = fh.read()
    rows = list(csv.DictReader(io.StringIO(text)))
    return text.rstrip("\n"), small_cells(rows)


def build(out_path: Path, mode: str | None = None) -> tuple[list[str], list[str]]:
    """Write the review file. Returns (sections written, small-cell warnings)."""
    mode = mode or guards.base_mode()
    guards.assert_not_protected(out_path)
    sections: list[tuple[str, Path]] = []
    for sens in guards.ALLOWED_SENSITIVITIES:
        sections.append((f"SENSITIVITY: {sens}",
                         ROOT / "results" / "sensitivities" / f"{mode}_{sens}"))
    sections.append(("PRIMARY (for comparison)", ROOT / "results" / mode))

    snap = provenance.snapshot()
    lines = [
        "EOCRC-SEER - aggregate results for review",
        f"generated {_dt.datetime.now(_dt.timezone.utc):%Y-%m-%d %H:%M} UTC  |  "
        f"commit {snap['git_commit']}  |  data mode {mode}",
        "Aggregate tables only. No per-patient predictions, fitted models or "
        "table1 are included.",
        "",
    ]
    written, warnings = [], []
    for title, folder in sections:
        lines += ["=" * 78, title, "=" * 78]
        if not folder.exists():
            lines += ["(not run yet)", ""]
            continue
        written.append(title)
        for name in AGGREGATE_TABLES:
            f = folder / name
            if not f.exists():
                continue
            body, hits = _render(f)
            lines += ["", f"--- {name}", body]
            warnings += [f"{title} / {name}: {h}" for h in hits]
        lines.append("")
    if warnings:
        lines[3:3] = ["", f"WARNING: {len(warnings)} count cell(s) below "
                      f"{SMALL_CELL}. Review before sharing outside your machine:"]
        lines[5:5] = [f"  {w}" for w in warnings] + [""]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return written, warnings
