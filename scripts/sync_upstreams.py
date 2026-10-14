#!/usr/bin/env python3
"""Reviewable upstream snapshots. Never executes code fetched from another repository."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "upstreams" / "sources.json"
CACHE = ROOT / ".upstreams"
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


class SyncError(RuntimeError):
    pass


def read_catalog(path: Path = CATALOG) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("sources"), list):
        raise SyncError("Unsupported or malformed sources.json")
    names = set()
    for source in data["sources"]:
        name, repo, branch, sha = (source.get(k) for k in ("name", "repo", "branch", "sha"))
        if not isinstance(name, str) or not SAFE.fullmatch(name) or name in names:
            raise SyncError(f"Invalid/duplicate source name: {name!r}")
        if not isinstance(repo, str) or not REPO.fullmatch(repo):
            raise SyncError(f"Invalid GitHub repository: {repo!r}")
        if not isinstance(branch, str) or not branch or branch.startswith("-") or any(c in branch for c in " ~^:?*[\\"):
            raise SyncError(f"Invalid upstream branch: {branch!r}")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise SyncError(f"Invalid SHA for {name}: {sha!r}")
        names.add(name)
    return data


def git(*args: str, cwd: Path | None = None) -> str:
    cmd = ["git", *args]
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if res.returncode:
        raise SyncError(f"git command failed ({res.returncode}): {' '.join(cmd)}\n{res.stderr.strip()}")
    return res.stdout.strip()


def url(source: dict) -> str:
    return f"https://github.com/{source['repo']}.git"


def remote_head(source: dict) -> str:
    ref = f"refs/heads/{source['branch']}"
    out = git("ls-remote", "--heads", url(source), ref)
    fields = out.split()
    if len(fields) != 2 or fields[1] != ref or not SHA.fullmatch(fields[0]):
        raise SyncError(f"Cannot resolve exact remote branch {source['name']}:{ref} (reply: {out!r})")
    return fields[0]


def select_sources(all_sources: list[dict], names: list[str], all_flag: bool) -> list[dict]:
    if all_flag and names:
        raise SyncError("Choose either --all or --name, not both")
    if not all_flag and not names:
        raise SyncError("fetch requires --name NAME (repeatable) or explicit --all")
    by_name = {s["name"]: s for s in all_sources}
    unknown = sorted(set(names) - by_name.keys())
    if unknown:
        raise SyncError(f"Unknown upstream name(s): {', '.join(unknown)}")
    return all_sources if all_flag else [by_name[name] for name in dict.fromkeys(names)]


def fetch_source(source: dict) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / source["name"]
    if dest.exists():
        if not (dest / ".git").is_dir():
            raise SyncError(f"{dest}: exists but is not a normal git clone; refusing overwrite")
        if git("status", "--porcelain", cwd=dest):
            raise SyncError(f"{dest}: uncommitted local work; refusing checkout")
        origin = git("remote", "get-url", "origin", cwd=dest)
        if origin.rstrip("/") != url(source):
            raise SyncError(f"{dest}: unexpected origin {origin!r}; refusing checkout")
        git("fetch", "--depth=1", "origin", f"refs/heads/{source['branch']}", cwd=dest)
        new_sha = git("rev-parse", "FETCH_HEAD", cwd=dest)
        git("checkout", "--detach", new_sha, cwd=dest)
    else:
        # --no-checkout ensures no upstream code is executed. Repo size may still be large.
        git("clone", "--filter=blob:none", "--depth=1", "--single-branch",
            "--branch", source["branch"], "--no-checkout", url(source), str(dest))
        new_sha = git("rev-parse", "HEAD", cwd=dest)
        git("checkout", "--detach", new_sha, cwd=dest)
    if not SHA.fullmatch(new_sha) or git("rev-parse", "HEAD", cwd=dest) != new_sha:
        raise SyncError(f"Unexpected git checkout for {source['name']}")
    return new_sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Only compare remote SHA; never download or modify files")
    fetch = sub.add_parser("fetch", help="Download selected refs into ignored .upstreams/")
    fetch.add_argument("--name", action="append", default=[], help="name in sources.json; repeatable")
    fetch.add_argument("--all", action="store_true", help="explicitly fetch all (can be many GB)")
    fetch.add_argument("--update-lock", action="store_true", help="advance sources.json SHA after fetch")
    args = parser.parse_args(argv)
    catalog = read_catalog()
    sources = catalog["sources"]

    if args.command == "check":
        errors = 0
        newer = 0
        for source in sources:
            try:
                sha = remote_head(source)
                status = "CURRENT" if sha == source["sha"] else "UPDATE_AVAILABLE"
                newer += sha != source["sha"]
                print(f"{source['name']:19} {status:18} pinned={source['sha'][:12]} remote={sha[:12]}")
            except (SyncError, OSError) as exc:
                errors += 1
                print(f"{source['name']:19} UNKNOWN (remote check failed): {exc}", file=sys.stderr)
        print(f"Sources: {len(sources)}, updates detected: {newer}, errors: {errors}")
        return 1 if errors else 0

    chosen = select_sources(sources, args.name, args.all)
    for source in chosen:
        original = source["sha"]
        new_sha = fetch_source(source)
        print(f"{source['name']}: pinned={original[:12]} fetched={new_sha[:12]} into .upstreams/{source['name']}")
        if args.update_lock:
            source["sha"] = new_sha
    if args.update_lock:
        import os
        import tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=CATALOG.parent,
                                         prefix=".sources-", suffix=".json", delete=False) as tmp:
            json.dump(catalog, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
            tmp_path = tmp.name
        os.replace(tmp_path, CATALOG)
        print("Lock advanced. BEFORE COMMIT: review diff and compatibility; no downstream code auto-merged.")
    else:
        print("Pinned SHAs unchanged. To review updates use: git -C .upstreams/NAME log -1 --stat")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SyncError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
