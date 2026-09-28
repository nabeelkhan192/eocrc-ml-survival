"""Capture git and environment provenance for a run record (read-only)."""
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> tuple[int, str]:
    """Run a read-only git command in the repo root; return (rc, stdout)."""
    try:
        proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True)
    except FileNotFoundError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def head_commit() -> str | None:
    rc, out = git("rev-parse", "HEAD")
    return out if rc == 0 else None


def branch() -> str | None:
    rc, out = git("rev-parse", "--abbrev-ref", "HEAD")
    return out if rc == 0 else None


def dirty_files() -> list[str] | None:
    """Tracked or untracked-but-not-ignored changes; None if git unavailable."""
    rc, out = git("status", "--porcelain")
    if rc != 0:
        return None
    return [line for line in out.splitlines() if line.strip()]


def snapshot() -> dict:
    dirty = dirty_files()
    return {
        "git_commit": head_commit(),
        "git_branch": branch(),
        "working_tree_clean": (dirty == []) if dirty is not None else None,
        "working_tree_changes": dirty,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
    }
