"""A finished schedule must keep every dependency, or say that it cannot.

A task declared to start before its predecessor ends used to be scheduled at its
declared start anyway, with no warning and exit status 0 (issuedb #19).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CONFLICT = """project p "p" 2026-10-19 +1w {
  timingresolution 60min
}
resource r0 "R0" { workinghours mon - fri 9:00 - 17:00 }
resource r1 "R1" { workinghours mon - fri 9:00 - 17:00 }
task a "A" { effort 3h allocate r0 }
task b "B" { start 2026-10-19-10:00 depends a effort 1h allocate r1 }
taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }
"""


def run_plan(tmp_path: Path, text: str) -> subprocess.CompletedProcess:
    path = tmp_path / "project.tjp"
    path.write_text(text)
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    return subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", str(path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
        timeout=300,
    )


def test_a_declared_start_before_its_predecessor_ends_is_refused(tmp_path: Path) -> None:
    done = run_plan(tmp_path, CONFLICT)
    output = done.stdout + done.stderr
    assert done.returncode != 0, f"expected a non-zero exit, got 0:\n{output}"
    assert "Task 'b' depends on 'a'" in output
    assert "2026-10-19 12:00:00" in output and "2026-10-19 10:00:00" in output


def test_the_same_plan_without_the_conflict_is_accepted(tmp_path: Path) -> None:
    done = run_plan(tmp_path, CONFLICT.replace("start 2026-10-19-10:00 ", "start 2026-10-19-12:00 "))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "b,2026-10-19-12:00,2026-10-19-13:00" in done.stdout


@pytest.mark.parametrize(
    "variant, edit",
    [
        ("milestone", ("effort 1h allocate r1", "milestone")),
        ("gap", ("depends a", "depends a { gapduration 600min }")),
    ],
)
def test_an_own_start_before_the_dependency_is_refused_for_every_kind(tmp_path: Path, variant: str, edit) -> None:
    done = run_plan(tmp_path, CONFLICT.replace(*edit))
    assert done.returncode != 0, done.stdout + done.stderr
    assert "Task 'b' depends on 'a'" in done.stdout + done.stderr
