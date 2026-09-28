#!/usr/bin/env python
"""Pre-commit safety check: block commits that touch protected paths.

Blocks, even for force-added files (`git add -f`):
  * data/raw/ and data/processed/ contents (SEER data under the DUA)
  * results/ and figures/ (outputs; per-patient predictions live there)
  * any .parquet, .joblib, or the SEER export by name
  * logs/ (run records stay local)
  * docs/protocol_OSF_preregistration.md (the registered artifact)
  * removed or edited lines in docs/CHANGELOG.md (history is append-only)

Standalone, standard library only, so the git hook can call it with any
Python 3. Enable once per clone:  git config core.hooksPath .githooks
"""
import fnmatch
import subprocess
import sys

ALLOWED = {"data/raw/.gitkeep", "data/processed/.gitkeep"}
BLOCKED_PREFIXES = ("data/raw/", "data/processed/", "results/", "figures/", "logs/")
BLOCKED_GLOBS = ("*.parquet", "*.joblib", "*seer_crc_export*")
PROTOCOL = "docs/protocol_OSF_preregistration.md"
CHANGELOG = "docs/CHANGELOG.md"


def blocked_paths(paths: list[str]) -> list[str]:
    bad = []
    for p in paths:
        p = p.replace("\\", "/")
        if p in ALLOWED:
            continue
        if (p == PROTOCOL or p.startswith(BLOCKED_PREFIXES)
                or any(fnmatch.fnmatch(p.lower(), g) for g in BLOCKED_GLOBS)):
            bad.append(p)
    return bad


def changelog_history_edits(diff_u0: str) -> list[str]:
    """Lines removed from CHANGELOG.md in a -U0 diff (pure additions are fine)."""
    return [ln for ln in diff_u0.splitlines()
            if ln.startswith("-") and not ln.startswith("---")]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def main() -> int:
    staged = [ln for ln in _git("diff", "--cached", "--name-only",
                                "--no-renames").splitlines() if ln.strip()]
    problems = [f"protected path staged: {p}" for p in blocked_paths(staged)]
    if CHANGELOG in staged:
        edits = changelog_history_edits(
            _git("diff", "--cached", "-U0", "--", CHANGELOG))
        problems += [f"CHANGELOG history edited (append new entries only): {e[:90]}"
                     for e in edits[:5]]
    if problems:
        print("\nPRE-COMMIT BLOCKED - EOCRC-SEER safety check\n", file=sys.stderr)
        for pr in problems:
            print(f"  x {pr}", file=sys.stderr)
        print("\nUnstage with:  git restore --staged <path>\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
