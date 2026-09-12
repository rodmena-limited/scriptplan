#!/usr/bin/env python3
"""Fail when a source file grows past the size it can be held in one head.

500 lines is the point to refactor; 550 is the point past which a file may not
go. Generated artefacts, fixtures and data blobs are exempt: the limit is about
code someone has to read.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOFT_LIMIT = 500
HARD_LIMIT = 550

ROOT = Path(__file__).resolve().parent.parent
SEARCHED = ("scriptplan", "audit")
EXEMPT_SUFFIXES = (".c", ".lark", ".json", ".csv", ".txt")


def source_files() -> list[Path]:
    found: list[Path] = []
    for area in SEARCHED:
        for path in (ROOT / area).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            if path.suffix in EXEMPT_SUFFIXES:
                continue
            found.append(path)
    return sorted(found)


def main() -> int:
    over_hard: list[tuple[Path, int]] = []
    over_soft: list[tuple[Path, int]] = []
    for path in source_files():
        lines = len(path.read_text().splitlines())
        if lines > HARD_LIMIT:
            over_hard.append((path, lines))
        elif lines > SOFT_LIMIT:
            over_soft.append((path, lines))

    for path, lines in over_soft:
        print(f"warning: {path.relative_to(ROOT)} is {lines} lines (refactor before {HARD_LIMIT})")
    for path, lines in over_hard:
        print(f"error:   {path.relative_to(ROOT)} is {lines} lines (limit {HARD_LIMIT})")

    if over_hard:
        print(f"\n{len(over_hard)} file(s) over the {HARD_LIMIT}-line limit")
        return 1
    print(f"all {len(source_files())} source files within {HARD_LIMIT} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
