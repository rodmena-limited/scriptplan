"""A date the file states is either kept or refused, never quietly overridden.

Each case comes from a report that 0.10.1 scheduled silently and wrongly
(issuedb #21, #22, #24, #25). Each refusal is paired with the same plan made
feasible, which must still schedule.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

HEAD = """project d "D" 2026-11-02 +{weeks}w {{
  timingresolution 30min
  scheduling {mode}
}}
resource r1 "Analyst" {{
  workinghours mon - fri 8:30 - 17:30
  limits {{ dailymax 450min }}
}}
task g "Group" {{
  {parent}
  task a "A" {{ effort 240min allocate r1 {a} }}
  task b "B" {{ effort 480min allocate r1 depends !a {b} }}
  task m "Milestone" {{ milestone depends !b {m} }}
}}
taskreport out "out" {{ formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }}
"""


def plan(tmp_path: Path, *, mode: str = "asap", weeks: int = 4, parent: str = "", a: str = "", b: str = "", m: str = ""):
    path = tmp_path / "plan.tjp"
    path.write_text(HEAD.format(mode=mode, weeks=weeks, parent=parent, a=a, b=b, m=m))
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


@pytest.mark.parametrize(
    "where, kwargs",
    [("task", {"b": "end 2026-11-03-10:00"}), ("parent", {"parent": "end 2026-11-03-10:00"})],
)
def test_a_stated_end_that_cannot_be_met_is_refused(tmp_path: Path, where: str, kwargs: dict) -> None:
    code, output = plan(tmp_path, **kwargs)
    assert code != 0, output
    assert "must end by 2026-11-03 10:00:00" in output
    assert "2026-11-03 13:00:00" in output


def test_a_stated_end_that_can_be_met_is_kept(tmp_path: Path) -> None:
    code, output = plan(tmp_path, b="end 2026-11-03-17:30")
    assert code == 0, output
    assert "g.b,2026-11-02-12:30,2026-11-03-13:00" in output


def test_a_milestone_end_before_its_predecessor_is_refused(tmp_path: Path) -> None:
    code, output = plan(tmp_path, m="end 2026-11-03-10:00")
    assert code != 0, output
    assert "Task 'g.m' depends on 'g.b'" in output


def test_a_stated_date_outside_the_project_is_refused(tmp_path: Path) -> None:
    code, output = plan(tmp_path, mode="alap", weeks=1, parent="end 2026-11-20-17:30")
    assert code != 0, output
    assert "states end 2026-11-20 17:30:00, outside the project window" in output


def test_an_alap_start_that_cannot_be_kept_is_refused(tmp_path: Path) -> None:
    code, output = plan(tmp_path, mode="alap", parent="end 2026-11-06-17:30", a="start 2026-11-06-08:30")
    assert code != 0, output
    assert "may not start before 2026-11-06 08:30:00" in output


def test_an_alap_start_that_can_be_kept_is_kept(tmp_path: Path) -> None:
    code, output = plan(tmp_path, mode="alap", parent="end 2026-11-06-17:30", a="start 2026-11-04-08:30")
    assert code == 0, output
    assert "g.a,2026-11-05-13:00,2026-11-05-17:00" in output


def test_an_alap_deadline_too_early_names_the_deadline_not_the_window(tmp_path: Path) -> None:
    code, output = plan(tmp_path, mode="alap", parent="end 2026-11-02-12:00")
    assert code != 0, output
    assert "it must end by 2026-11-02 12:00:00, and there is not enough working time" in output
    assert "its successor 'g.b' could not be scheduled" in output
    assert "ran outside the project window" not in output
    assert "alap_degraded" not in output and "as early as possible instead" not in output


def test_a_start_after_the_project_is_refused_without_crashing(tmp_path: Path) -> None:
    # It used to raise IndexError from the scoreboard, reported as a parse error.
    code, output = plan(tmp_path, weeks=1, a="start 2026-11-20-08:30")
    assert code != 0, output
    assert "Task 'g.a' states start 2026-11-20 08:30:00, outside the project window" in output
    assert "parsing" not in output and "index" not in output.lower()
