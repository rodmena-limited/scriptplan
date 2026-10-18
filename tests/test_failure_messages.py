"""A task that cannot be placed is reported with the reason that applies to it."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT = """project d "D" 2026-11-02 +1w {{ timingresolution 30min }}
resource r1 "Analyst" {{ workinghours mon - fri 8:30 - 17:30 }}
task g "Group" {{
  {parent}
  task a "A" {{ effort {effort} {allocate} }}
}}
"""


def plan(tmp_path: Path, *, effort: str, parent: str = "", allocate: str = "") -> tuple[int, str]:
    path = tmp_path / "plan.tjp"
    path.write_text(PROJECT.format(parent=parent, effort=effort, allocate=allocate))
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    done = subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", str(path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
        timeout=300,
    )
    return done.returncode, done.stdout + done.stderr


def test_effort_with_no_resource_says_so(tmp_path: Path) -> None:
    code, output = plan(tmp_path, effort="2h")
    assert code != 0, output
    assert "Task 'g.a' could not be scheduled: it has effort but no resource is allocated to do it" in output
    assert "ran outside the project window" not in output
    assert "Error: Error:" not in output


def test_effort_that_does_not_fit_names_the_window(tmp_path: Path) -> None:
    # The allocation is inherited from the parent, so the task has a resource.
    code, output = plan(tmp_path, effort="100h", parent="allocate r1")
    assert code != 0, output
    assert "Task 'g.a' could not be scheduled: ran outside the project window" in output
    assert "no resource is allocated" not in output
