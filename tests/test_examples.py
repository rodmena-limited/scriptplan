"""Conformance: every showcase project schedules to its independently derived answer.

examples/showcase/<name>.tjp and examples/edge_cases/<name>.tjp are projects;
<name>.expected.csv beside each holds the start
and end of every task in it, worked out by hand from the file and the
documented semantics, without running ScriptPlan; <name>.expected.md shows the
arithmetic. This runs each project through the `plan` CLI in a fresh process,
as a user would, and compares every task to the second.

This is not the golden snapshot in tests/golden. A snapshot records what the
engine produced last time and catches change; these files record what the
engine should produce and catch error. 0.10.1 passed every snapshot while
placing an alap duration task after the task that follows it (issuedb #13).
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = REPO_ROOT / "examples" / "showcase"
EDGE_CASES = REPO_ROOT / "examples" / "edge_cases"
FOLDERS = (SHOWCASE, EDGE_CASES)
# Run the same answers against an installed release instead of this checkout:
#   SCRIPTPLAN_EXAMPLES_PYTHON=/path/to/venv/bin/python pytest tests/test_examples.py
PYTHON = os.environ.get("SCRIPTPLAN_EXAMPLES_PYTHON")
REPORT = 'taskreport conformance "conformance" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M:%S" }\n'
REPORT_BLOCK = re.compile(
    r"(?m)^[ \t]*(taskreport|resourcereport|textreport|tracereport|icalreport|export|navigator)\b[^{\n]*\{"
)


def projects() -> list[str]:
    return sorted(
        f"{folder.name}/{p.name[: -len('.expected.csv')]}" for folder in FOLDERS for p in folder.glob("*.expected.csv")
    )


def without_reports(text: str) -> str:
    """The project with its own report blocks removed, so one known report replaces them."""
    out, at = [], 0
    for match in REPORT_BLOCK.finditer(text):
        if match.start() < at:
            continue
        out.append(text[at : match.start()])
        depth, i = 0, match.end() - 1
        while i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                break
            i += 1
        at = i + 1
    out.append(text[at:])
    return "".join(out)


def expected(name: str) -> dict[str, tuple[str, str]]:
    rows = {}
    with open(REPO_ROOT / "examples" / f"{name}.expected.csv") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if row and row[0] != "id":
                rows[row[0]] = (row[1], row[2])
    return rows


def scheduled(name: str) -> dict[str, tuple[str, str]]:
    """Every task's dates as the CLI reports them, in the project's timezone."""
    text = without_reports((REPO_ROOT / "examples" / f"{name}.tjp").read_text()) + "\n" + REPORT
    directory = tempfile.mkdtemp(prefix="scriptplan_example_")
    path = os.path.join(directory, os.path.basename(name) + ".tjp")
    with open(path, "w") as handle:
        handle.write(text)
    env = dict(os.environ)
    if PYTHON is None:
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [PYTHON or sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", path],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
        # Not the checkout: `python -m` imports from the working directory
        # first, which would test this tree even when PYTHON names a release.
        cwd=directory,
    )
    assert done.returncode == 0, f"{name}: plan report failed:\n{done.stdout}\n{done.stderr}"
    lines = [line for line in done.stdout.splitlines() if line.count(",") >= 2]
    rows = {}
    for row in csv.reader(io.StringIO("\n".join(lines))):
        if row and row[0] != "Id":
            rows[row[0]] = (row[1], row[2])
    return rows


def test_every_example_project_has_an_expected_answer() -> None:
    have = {f"{folder.name}/{p.stem}" for folder in FOLDERS for p in folder.glob("*.tjp")}
    assert have == set(projects()), f"projects without expected.csv: {sorted(have - set(projects()))}"


@pytest.mark.parametrize("name", projects())
def test_example_project_schedules_as_derived(name: str) -> None:
    want, got = expected(name), scheduled(name)
    wrong = [
        f"  {task}: expected {want.get(task)}, got {got.get(task)}"
        for task in sorted(set(want) | set(got))
        if want.get(task) != got.get(task)
    ]
    assert not wrong, f"{name}: {len(wrong)} of {len(want)} tasks differ from the derived answer:\n" + "\n".join(wrong)
