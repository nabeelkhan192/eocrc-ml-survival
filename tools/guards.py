"""Protected-path, integrity, and frozen-state checks (read-only).

Every function here only reads. None of them imports src/config.py, because
config.py creates directories and reads EOCRC_SENSITIVITY at import time;
the runner must be able to inspect the repo without side effects.
"""
import hashlib
import json
import re
from pathlib import Path

from tools import provenance

ROOT = Path(__file__).resolve().parents[1]

FROZEN_TAG = "v4.1.1-osf-final"
FROZEN_COMMIT = "a2c4869e02ec92254230d4c72a8a29fdd231592a"
PROTOCOL_FILE = "docs/protocol_OSF_preregistration.md"
RAW_EXPORT = ROOT / "data" / "raw" / "seer_crc_export.csv"
LOCKED_HORIZON = 60
ALLOWED_SENSITIVITIES = ("exclude_rectal", "exclude_2019")
DEFERRED_SENSITIVITIES = ("complete_case", "covid_extension", "stage1_3_postop")


class ProtectedPathError(RuntimeError):
    pass


# ---------------------------------------------------------------- mode
def base_mode() -> str:
    """Same rule as src/config.py BASE_MODE, evaluated without importing it."""
    return "seer" if RAW_EXPORT.exists() else "synthetic"


# ---------------------------------------------------------------- paths
def protected_paths(mode: str | None = None) -> list[Path]:
    mode = mode or base_mode()
    return [
        ROOT / "data" / "raw",
        ROOT / "results" / mode,          # includes preds/ and models/
        ROOT / "figures" / mode,
        ROOT / "data" / "processed" / f"cohort_{mode}.parquet",
        ROOT / PROTOCOL_FILE,
    ]


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_protected(path: Path) -> bool:
    path = Path(path)
    if any(_inside(path, p) for p in protected_paths("seer")
           + protected_paths("synthetic")):
        return True
    # per-patient predictions and fitted models, under any results root
    parts = path.resolve().parts
    return "results" in parts and ("preds" in parts or "models" in parts)


def assert_not_protected(path: Path) -> None:
    """Raise before the runner writes anything into a protected location."""
    if is_protected(path):
        raise ProtectedPathError(
            f"REFUSING TO WRITE: {path} is a protected path (primary outputs, "
            "raw DUA data, per-patient predictions/models, or the registered "
            "protocol).")


# ---------------------------------------------------------------- hashing
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def primary_output_targets(mode: str | None = None) -> list[Path]:
    mode = mode or base_mode()
    return [ROOT / "results" / mode, ROOT / "figures" / mode,
            ROOT / "data" / "processed" / f"cohort_{mode}.parquet"]


def hash_outputs(targets: list[Path]) -> dict[str, str]:
    """SHA-256 of every file under the given files/directories (relative keys)."""
    out: dict[str, str] = {}
    for t in targets:
        files = [t] if t.is_file() else sorted(p for p in t.rglob("*")
                                              if p.is_file()) if t.exists() else []
        for f in files:
            try:
                key = f.relative_to(ROOT).as_posix()
            except ValueError:
                key = f.as_posix()
            out[key] = _sha256(f)
    return out


def diff_hashes(before: dict, after: dict) -> list[str]:
    changes = []
    for k in sorted(set(before) | set(after)):
        if k not in after:
            changes.append(f"removed: {k}")
        elif k not in before:
            changes.append(f"added:   {k}")
        elif before[k] != after[k]:
            changes.append(f"changed: {k}")
    return changes


def manifest_path(mode: str | None = None) -> Path:
    return ROOT / "logs" / f"primary_manifest_{mode or base_mode()}.json"


def verify_primary_manifest(mode: str | None = None) -> tuple[bool, str]:
    """Real-data mode: verify primary outputs against the recorded baseline.

    Read-only. The baseline is created only by `project.py baseline`, after
    the primary outputs have been compared with the external first-run
    archive. Synthetic outputs are regenerated freely, so no persistent
    baseline is kept for them (before/after checks around each run still
    apply).
    """
    mode = mode or base_mode()
    if mode != "seer":
        return True, "synthetic mode - persistent baseline not used"
    mp = manifest_path(mode)
    if not mp.exists():
        return False, ("no baseline yet - run: python project.py baseline "
                       "--archive <first-run archive folder>")
    current = hash_outputs(primary_output_targets(mode))
    recorded = json.loads(mp.read_text(encoding="utf-8"))
    changes = diff_hashes(recorded, current)
    if changes:
        return False, ("PRIMARY OUTPUTS DIFFER FROM BASELINE - restore from "
                       "the external first-run archive:\n    "
                       + "\n    ".join(changes[:20]))
    return True, f"{len(current)} files match baseline"


def _archive_dir(archive: Path, kind: str, mode: str) -> Path | None:
    """Locate results/ or figures/ inside an archive copy (either layout)."""
    for cand in (archive / kind / mode, archive / kind):
        if cand.is_dir() and any(p.is_file() for p in cand.rglob("*")):
            return cand
    return None


def _archive_groups(archive: Path, mode: str) -> list[tuple[str, list[Path], Path | None]]:
    """(label, local folders, archive folder) pairs to compare.

    Split layout: results/ and figures/ each have their own archive folder.
    Flat layout: results/<mode>/ and figures/<mode>/ were copied together into
    a single <archive>/<mode>/ folder; both local folders are compared with it.
    """
    split = [(f"{kind}/{mode}", [ROOT / kind / mode], _archive_dir(archive, kind, mode))
             for kind in ("results", "figures")]
    flat = archive / mode
    if all(a is None for _, _, a in split) and flat.is_dir():
        return [(f"{mode} (flat archive)",
                 [ROOT / "results" / mode, ROOT / "figures" / mode], flat)]
    return split


def compare_to_archive(local: list[Path], archived: Path) -> dict[str, list[str]]:
    """Compare every file under the local folders (read as one) with an archive
    folder by SHA-256 (relative paths). A relative path present in more than
    one local folder is reported as a collision, never silently merged."""
    def rel_hashes(base: Path) -> dict[str, str]:
        return {f.relative_to(base).as_posix(): _sha256(f)
                for f in sorted(base.rglob("*")) if f.is_file()}
    a = rel_hashes(archived)
    b: dict[str, str] = {}
    collisions: list[str] = []
    for base in local:
        for k, v in (rel_hashes(base) if base.exists() else {}).items():
            if k in b:
                collisions.append(k)
            b[k] = v
    return {
        "mismatch": sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
        "missing_locally": sorted(a.keys() - b.keys()),
        "not_in_archive": sorted(b.keys() - a.keys()),
        "collision": sorted(collisions),
        "matched": sorted(k for k in a.keys() & b.keys() if a[k] == b[k]),
    }


def create_baseline(archive: Path, mode: str | None = None) -> tuple[bool, list[str]]:
    """Check primary outputs against the archive; record the baseline only if
    every archived file is present locally and byte-identical."""
    mode = mode or base_mode()
    lines: list[str] = []
    mp = manifest_path(mode)
    if mp.exists():
        return False, [f"baseline already exists ({mp.relative_to(ROOT).as_posix()}); "
                       "it is never overwritten by the runner"]
    if mode != "seer":
        return False, ["baseline applies to real-data (SEER) mode only"]
    ok = True
    for label, local, arch in _archive_groups(Path(archive), mode):
        if arch is None:
            ok = False
            kind = label.split("/")[0]
            lines.append(f"{label}: no files found in the archive under "
                         f"{kind}/{mode}/, {kind}/ or {mode}/")
            continue
        r = compare_to_archive(local, arch)
        lines.append(f"{label}: {len(r['matched'])} files identical to archive")
        for k in r["mismatch"]:
            ok = False
            lines.append(f"  DIFFERENT from archive: {label}: {k}")
        for k in r["missing_locally"]:
            ok = False
            lines.append(f"  in archive but MISSING locally: {label}: {k}")
        for k in r["collision"]:
            ok = False
            lines.append(f"  in both results/{mode}/ and figures/{mode}/ (ambiguous "
                         f"against a flat archive): {k}")
        for k in r["not_in_archive"]:
            lines.append(f"  note - not in archive (baselined as-is): {label}: {k}")
    if not ok:
        lines.append("Baseline NOT created. Restore the differing files from the "
                     "archive, then run this again.")
        return False, lines
    current = hash_outputs(primary_output_targets(mode))
    mp.parent.mkdir(exist_ok=True)
    mp.write_text(json.dumps(current, indent=2), encoding="utf-8")
    lines.append(f"Baseline created: {len(current)} files "
                 f"({mp.relative_to(ROOT).as_posix()}). Every later run verifies against it.")
    return True, lines


# ---------------------------------------------------------------- frozen state
def check_frozen_tag() -> tuple[bool, str]:
    rc, out = provenance.git("rev-parse", f"{FROZEN_TAG}^{{commit}}")
    if rc != 0:
        return False, f"tag {FROZEN_TAG} not found locally (run: git fetch --tags)"
    if out != FROZEN_COMMIT:
        return False, f"tag {FROZEN_TAG} points to {out[:7]}, expected a2c4869"
    return True, f"{FROZEN_TAG} -> a2c4869"


def check_protocol_unchanged() -> tuple[bool, str]:
    """Registered protocol identical to the frozen tag, in HEAD and working tree."""
    rc, _ = provenance.git("diff", "--quiet", FROZEN_TAG, "--", PROTOCOL_FILE)
    if rc == 0:
        return True, "identical to frozen tag"
    if rc == 1:
        return False, f"{PROTOCOL_FILE} differs from {FROZEN_TAG}"
    return False, "could not compare (is the frozen tag fetched?)"


def locked_horizon() -> int | None:
    text = (ROOT / "src" / "config.py").read_text(encoding="utf-8")
    m = re.search(r"^HORIZON_MONTHS\s*=\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def check_horizon_locked() -> tuple[bool, str]:
    h = locked_horizon()
    return (h == LOCKED_HORIZON,
            f"HORIZON_MONTHS = {h} (locked value {LOCKED_HORIZON}, CHANGELOG v4.1.2)")


def check_changelog_rules_recorded() -> tuple[bool, str]:
    text = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    ok = "## v4.1.4" in text
    return ok, ("v4.1.4 sensitivity rules recorded" if ok else
                "CHANGELOG v4.1.4 (horizon lock + S9 rule) not recorded - "
                "commit it before any sensitivity run")


def run_models_stages() -> list[str]:
    """Stage scripts run_models.sh executes, in order (single source of truth)."""
    text = (ROOT / "run_models.sh").read_text(encoding="utf-8")
    return re.findall(r"^python (src/0\d_[\w]+\.py)\s*$", text, re.MULTILINE)
