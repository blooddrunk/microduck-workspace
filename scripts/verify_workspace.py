#!/usr/bin/env python3
"""Offline validation of the roadmap, Markdown internal links, and pinned upstreams."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "ROADMAP.md", "CHECKLIST.md",
    "docs/00_START_HERE.md", "docs/01_BOARD_BOOT.md",
    "docs/02_SERVO_IMU.md", "docs/03_POWER_INTEGRATION.md",
    "docs/04_SIM_TRAINING.md", "docs/05_EVIDENCE_AND_SOURCES.md",
    "records/TEMPLATE.md", "upstreams/sources.json",
]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def internal_link_errors() -> list[str]:
    issues = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            issues.append(f"Missing required file: {rel}")
    for markdown in ROOT.rglob("*.md"):
        if any(part.startswith(".") and part != "." for part in markdown.relative_to(ROOT).parts):
            continue
        if markdown.relative_to(ROOT).parts[0] in {"microduck", "microduck_rl", "policies"}:
            continue
        text = markdown.read_text(encoding="utf-8")
        for link in LINK_RE.findall(text):
            target = unquote(link.strip().split("#", 1)[0].split("?", 1)[0])
            if not target or target.startswith(("https://", "http://", "mailto:", "tel:", "data:")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if target.startswith("/"):
                issues.append(f"{markdown.relative_to(ROOT)}: absolute local link {link}")
                continue
            result = (markdown.parent / target).resolve()
            if not result.is_relative_to(ROOT.resolve()) or not result.exists():
                issues.append(f"{markdown.relative_to(ROOT)}: broken link {link}")
    return issues


def main() -> int:
    issues = internal_link_errors()
    try:
        from sync_upstreams import read_catalog
        data = read_catalog()
        if len(data["sources"]) < 7:
            issues.append("Expected at least 7 documented upstreams")
        print(f"Validated {len(data['sources'])} pinned upstream sources.")
    except Exception as exc:
        issues.append(f"Upstream catalog: {exc}")
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print(f"PASS: {len(REQUIRED)} required files + local Markdown links + upstream SHA formats")
    print("SCOPE: static documentation only; NO electrical, physical or runtime verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
