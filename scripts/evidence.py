"""Private, local evidence bundles. Raw output may contain secrets; never auto-publish."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def run(command, timeout=20):
    started = timestamp()
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout=timeout, env={**os.environ, "LC_ALL": "C", "SYSTEMD_COLORS": "0"})
        return dict(command=command, time_utc=started, returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr, error=None)
    except (OSError, subprocess.TimeoutExpired) as exc:
        # Partial timeout output is intentionally omitted; failure remains explicit.
        return dict(command=command, time_utc=started, returncode=None,
                    stdout="", stderr="", error=type(exc).__name__)


def source_version():
    head = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    dirty = run(["git", "-C", str(ROOT), "status", "--porcelain"])
    files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
             for folder in ("scripts", "templates") for p in sorted((ROOT / folder).rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts}
    return dict(commit=head["stdout"].strip() or "UNKNOWN",
                dirty=bool(dirty["stdout"]) if dirty["returncode"] == 0 else None,
                file_sha256=files)


class Bundle:
    def __init__(self, output, scope):
        self.path = Path(output)
        # Never mix previous runs or overwrite operator evidence.
        self.path.mkdir(parents=True, mode=0o700, exist_ok=False)
        (self.path / "raw").mkdir(mode=0o700)
        self.metadata = dict(schema_version=1, time_utc=timestamp(), scope=scope,
                             invocation=sys.argv, source=source_version(),
                             privacy="LOCAL ONLY: inspect raw logs for Wi-Fi passwords, tokens, IP/MAC, serials, host/user names before sharing")
        self.checks = []

    def add(self, name, result, status, reason):
        if status not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError("Invalid evidence status")
        raw = self.path / "raw" / f"{len(self.checks):02d}.json"
        self.write(raw, result)
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        self.checks.append(dict(name=name, status=status, reason=reason,
                                command=result.get("command"), time_utc=result.get("time_utc"),
                                raw=str(raw.relative_to(self.path)), sha256=digest))

    @staticmethod
    def write(path, data):
        with open(path, "x", encoding="utf-8") as stream:
            os.chmod(path, 0o600)
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")

    def finish(self, extra=None):
        status = "FAIL" if any(c["status"] == "FAIL" for c in self.checks) else (
            "BLOCKED" if any(c["status"] == "BLOCKED" for c in self.checks) else "PASS")
        self.write(self.path / "summary.json", {**self.metadata, "status": status,
                   "checks": self.checks, **(extra or {})})
        print(f"{status}: {self.path / 'summary.json'}")
        return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[status]
