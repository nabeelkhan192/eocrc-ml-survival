"""Timestamped run log (.log) plus a JSON manifest (.json) for every command.

Logs go to logs/ (git-ignored). The runner never writes anywhere else; the
write target is checked against the protected-path list before every write.
"""
import datetime as _dt
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from tools import guards, provenance

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class RunLog:
    def __init__(self, command: str, argv: list[str]):
        guards.assert_not_protected(LOG_DIR)
        LOG_DIR.mkdir(exist_ok=True)
        stamp = _utc_stamp()
        base = f"{stamp}_{command.replace(' ', '_')}"
        n = 1
        while (LOG_DIR / f"{base}.log").exists():   # never overwrite a record
            n += 1
            base = f"{stamp}_{command.replace(' ', '_')}_{n}"
        self.log_path = LOG_DIR / f"{base}.log"
        self.json_path = LOG_DIR / f"{base}.json"
        self.record = {
            "command": command,
            "invocation": " ".join([Path(sys.executable).name, *argv]),
            "started_utc": stamp,
            "provenance": provenance.snapshot(),
            "shell_commands": [],
            "checks": {},
            "pytest": None,
            "output_paths": [],
            "exit_code": None,
            "message": "",
        }
        self._fh = open(self.log_path, "w", encoding="utf-8")
        self.echo(f"# {command}  |  log: {self.log_path.relative_to(ROOT)}")
        p = self.record["provenance"]
        self.echo(f"# commit {p['git_commit']}  branch {p['git_branch']}  "
                  f"clean={p['working_tree_clean']}  python {p['python_version']}")

    # ------------------------------------------------------------ output
    def echo(self, text: str = "") -> None:
        print(text, flush=True)
        self._fh.write(text + "\n")
        self._fh.flush()

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.record["checks"][name] = {"ok": bool(ok), "detail": detail}
        self.echo(f"[{'PASS' if ok else 'FAIL'}] {name}" +
                  (f" - {detail}" if detail else ""))
        return ok

    # ------------------------------------------------------------ running
    def run(self, args: list[str], env_extra: dict | None = None,
            env_drop: tuple[str, ...] = ()) -> int:
        """Run a subprocess from the repo root, streaming output into the log.

        The exact command (with any environment variable it sets) is recorded
        so it can be re-typed by hand.
        """
        env = dict(os.environ)
        for k in env_drop:
            env.pop(k, None)
        env.update(env_extra or {})
        # live, lossless streaming on Windows consoles too
        env.setdefault("PYTHONUNBUFFERED", "1")
        env["PYTHONIOENCODING"] = "utf-8"
        shown = " ".join(
            [f"{k}={v}" for k, v in (env_extra or {}).items()]
            + [shlex.quote(a) if " " in a else a for a in args])
        self.record["shell_commands"].append(shown)
        self.echo(f"\n$ {shown}")
        proc = subprocess.Popen(args, cwd=ROOT, env=env, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, bufsize=1,
                                encoding="utf-8", errors="replace")
        assert proc.stdout is not None
        for line in proc.stdout:
            self.echo(line.rstrip("\n"))
        rc = proc.wait()
        self.echo(f"# exit {rc}")
        return rc

    # ------------------------------------------------------------ finish
    def finish(self, exit_code: int, message: str = "") -> int:
        self.record["exit_code"] = exit_code
        self.record["message"] = message
        self.record["finished_utc"] = _utc_stamp()
        if message:
            self.echo(f"\n{message}")
        self.echo(f"# record: {self.json_path.relative_to(ROOT)}")
        self._fh.close()
        with open(self.json_path, "w", encoding="utf-8") as fh:
            json.dump(self.record, fh, indent=2)
        return exit_code
