"""Tests for the operational automation layer (project.py, tools/).

They prove that the runner refuses what it must refuse: unsupported or
deferred sensitivity modes, writes into protected paths, commits that touch
protected paths or rewrite CHANGELOG history; that its stage list cannot
drift from run_models.sh; and that output hashing detects any change.
No test runs the pipeline or touches real data.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import guards, precommit_check  # noqa: E402


# ------------------------------------------------------------ allow-list
def _run_project(*args):
    env_py = [sys.executable, str(ROOT / "project.py"), *args]
    return subprocess.run(env_py, cwd=ROOT, capture_output=True, text=True)


@pytest.mark.parametrize("mode", ["complete_case", "covid_extension",
                                  "stage1_3_postop", "made_up_mode"])
def test_unsupported_sensitivity_hard_fails(mode):
    proc = _run_project("sensitivity", mode, "--dry-run")
    assert proc.returncode == 2
    assert "REFUSED" in proc.stdout


def test_runner_allowlist_matches_config():
    text = (ROOT / "src" / "config.py").read_text(encoding="utf-8")
    m = re.search(r"^ALLOWED_SENSITIVITIES\s*=\s*\(([^)]*)\)", text, re.MULTILINE)
    config_modes = tuple(re.findall(r'"(\w+)"', m.group(1)))
    assert config_modes == guards.ALLOWED_SENSITIVITIES
    assert not set(guards.DEFERRED_SENSITIVITIES) & set(config_modes)


# ------------------------------------------------------------ protected paths
@pytest.mark.parametrize("rel", [
    "results/seer/transportability_paired.csv",
    "results/seer/preds/eo_test.parquet",
    "figures/seer/calibration.png",
    "data/processed/cohort_seer.parquet",
    "data/raw/seer_crc_export.csv",
    "docs/protocol_OSF_preregistration.md",
    "results/sensitivities/seer_exclude_rectal/preds/x.parquet",
    "results/sensitivities/seer_exclude_2019/models/cox.joblib",
])
def test_protected_paths_refused(rel):
    with pytest.raises(guards.ProtectedPathError):
        guards.assert_not_protected(ROOT / rel)


@pytest.mark.parametrize("rel", [
    "logs/run.log",
    "results/sensitivities/seer_exclude_rectal/table1.csv",
    "figures/sensitivities/seer_exclude_2019/km.png",
    "data/processed/sensitivities/cohort_seer_exclude_2019.parquet",
])
def test_sensitivity_and_log_paths_allowed(rel):
    guards.assert_not_protected(ROOT / rel)   # must not raise


# ------------------------------------------------------------ frozen state
def test_stage_list_read_from_run_models():
    stages = guards.run_models_stages()
    assert [Path(s).stem[:2] for s in stages] == ["03", "04", "05", "06", "07"]
    assert all((ROOT / s).exists() for s in stages)


def test_horizon_locked_at_60():
    assert guards.locked_horizon() == 60
    assert guards.check_horizon_locked()[0]


# ------------------------------------------------------------ hashing
def test_hash_diff_detects_change_add_remove(tmp_path):
    (tmp_path / "a.csv").write_text("1")
    (tmp_path / "b.csv").write_text("2")
    before = guards.hash_outputs([tmp_path])
    assert guards.diff_hashes(before, guards.hash_outputs([tmp_path])) == []
    (tmp_path / "a.csv").write_text("changed")
    (tmp_path / "b.csv").unlink()
    (tmp_path / "c.csv").write_text("3")
    kinds = sorted(c.split(":")[0] for c in
                   guards.diff_hashes(before, guards.hash_outputs([tmp_path])))
    assert kinds == ["added", "changed", "removed"]


# ------------------------------------------------------------ pre-commit
@pytest.mark.parametrize("path", [
    "data/raw/seer_crc_export.csv", "data/processed/cohort_seer.parquet",
    "results/seer/preds/eo.parquet", "figures/seer/x.png", "logs/a.log",
    "docs/protocol_OSF_preregistration.md", "anywhere/model.joblib",
    "notes/SEER_CRC_EXPORT_copy.csv", "data\\raw\\file.csv",
])
def test_precommit_blocks_protected(path):
    assert precommit_check.blocked_paths([path])


@pytest.mark.parametrize("path", [
    "data/raw/.gitkeep", "data/processed/.gitkeep", "src/config.py",
    "docs/CHANGELOG.md", "tools/guards.py", "README.md",
])
def test_precommit_allows_ordinary(path):
    assert not precommit_check.blocked_paths([path])


def test_precommit_changelog_append_only():
    appended = "--- a/docs/CHANGELOG.md\n+++ b/docs/CHANGELOG.md\n@@ -2,0 +3,2 @@\n+## v4.1.5\n+new\n"
    edited = "--- a/docs/CHANGELOG.md\n+++ b/docs/CHANGELOG.md\n@@ -5 +5 @@\n-old line\n+new line\n"
    assert precommit_check.changelog_history_edits(appended) == []
    assert precommit_check.changelog_history_edits(edited) == ["-old line"]


# ------------------------------------------------------------ baseline
def _fake_repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "results" / "seer" / "preds").mkdir(parents=True)
    (root / "figures" / "seer").mkdir(parents=True)
    (root / "results" / "seer" / "table1.csv").write_text("t1")
    (root / "results" / "seer" / "preds" / "p.parquet").write_text("p")
    (root / "figures" / "seer" / "km.png").write_text("km")
    monkeypatch.setattr(guards, "ROOT", root)
    return root


def _archive_copy(root, arch):
    import shutil
    for kind in ("results", "figures"):
        shutil.copytree(root / kind, arch / kind)


def test_status_check_never_creates_baseline(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch)
    ok, detail = guards.verify_primary_manifest("seer")
    assert not ok and "no baseline" in detail
    assert not (root / "logs").exists()


def test_baseline_created_only_when_identical_to_archive(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch)
    arch = tmp_path / "archive"
    _archive_copy(root, arch)
    (root / "results" / "seer" / "table1.csv").write_text("edited after archive")
    ok, lines = guards.create_baseline(arch, "seer")
    assert not ok and any("DIFFERENT" in ln for ln in lines)
    assert not guards.manifest_path("seer").exists()

    (root / "results" / "seer" / "table1.csv").write_text("t1")
    ok, _ = guards.create_baseline(arch, "seer")
    assert ok and guards.manifest_path("seer").exists()
    assert guards.verify_primary_manifest("seer")[0]
    ok, lines = guards.create_baseline(arch, "seer")       # never overwritten
    assert not ok and "already exists" in lines[0]

    (root / "figures" / "seer" / "km.png").write_text("tampered")
    ok, detail = guards.verify_primary_manifest("seer")
    assert not ok and "km.png" in detail


def test_baseline_fails_when_archived_file_missing(tmp_path, monkeypatch):
    root = _fake_repo(tmp_path, monkeypatch)
    arch = tmp_path / "archive"
    _archive_copy(root, arch)
    (root / "figures" / "seer" / "km.png").unlink()
    ok, lines = guards.create_baseline(arch, "seer")
    assert not ok and any("MISSING locally" in ln for ln in lines)


def test_baseline_accepts_flat_archive(tmp_path, monkeypatch):
    # results/seer/ and figures/seer/ copied together into one archive/seer/
    import shutil
    root = _fake_repo(tmp_path, monkeypatch)
    arch = tmp_path / "archive"
    shutil.copytree(root / "results" / "seer", arch / "seer")
    shutil.copytree(root / "figures" / "seer", arch / "seer", dirs_exist_ok=True)
    (root / "figures" / "seer" / "km.png").write_text("edited after archive")
    ok, lines = guards.create_baseline(arch, "seer")
    assert not ok and any("DIFFERENT" in ln and "km.png" in ln for ln in lines)
    assert not guards.manifest_path("seer").exists()

    (root / "figures" / "seer" / "km.png").write_text("km")
    ok, _ = guards.create_baseline(arch, "seer")
    assert ok and guards.verify_primary_manifest("seer")[0]


# ------------------------------------------------------------ summarize
from tools import summarize  # noqa: E402


def test_summarize_never_reads_per_patient_or_table1(tmp_path):
    for bad in ("preds/eo.csv", "models/x.csv", "table1.csv", "cohort.parquet"):
        p = tmp_path / bad
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("a\n1\n")
        with pytest.raises(PermissionError):
            summarize._render(p)


def test_small_cells_flagged_only_in_count_columns():
    rows = [{"step": "x", "n": "12"}, {"step": "y", "n": "500"},
            {"group": "EO", "n_event_free": "3", "brier": "0.15", "cindex": "5"}]
    hits = summarize.small_cells(rows)
    assert len(hits) == 2
    assert any("'n' = 12" in h for h in hits)
    assert any("n_event_free" in h for h in hits)


def test_summarize_output_never_protected(tmp_path):
    with pytest.raises(guards.ProtectedPathError):
        summarize.build(ROOT / "results" / "seer" / "review.txt")


def test_summarize_treats_empty_sensitivity_folder_as_not_run(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "results" / "sensitivities" / "seer_exclude_2019" / "preds").mkdir(parents=True)
    (root / "results" / "sensitivities" / "seer_exclude_rectal").mkdir(parents=True)
    (root / "results" / "sensitivities" / "seer_exclude_rectal" / "recalibration.csv").write_text("family,model\nh,x\n")
    (root / "results" / "seer").mkdir(parents=True)
    monkeypatch.setattr(summarize, "ROOT", root)
    monkeypatch.setattr(guards, "ROOT", root)
    written, _ = summarize.build(tmp_path / "review.txt", mode="seer")
    text = (tmp_path / "review.txt").read_text()
    assert written == ["SENSITIVITY: exclude_rectal"]
    assert text.count("not run yet") == 2          # exclude_2019 and primary (both empty)


# ------------------------------------------------------------ sensitivity state
def test_sensitivity_state_none_partial_complete(tmp_path):
    import project
    d = tmp_path / "seer_exclude_rectal"
    assert project.sensitivity_state(d) == "none"
    (d / "preds").mkdir(parents=True)
    assert project.sensitivity_state(d) == "none"          # empty dirs only
    (d / "sensitivity_cohort_flow.csv").write_text("step,n\n")
    assert project.sensitivity_state(d) == "partial"       # builder ran, models did not
    (d / "followup_adequacy.csv").write_text("g\n")
    assert project.sensitivity_state(d) == "partial"
    (d / "transportability_paired.csv").write_text("m\n")
    assert project.sensitivity_state(d) == "partial"       # stage 07 still missing
    (d / "recalibration.csv").write_text("m\n")
    assert project.sensitivity_state(d) == "complete"
