"""Two defects trace found in 0.10.2 (issuedb #30 and #31).

0.10.2 bound a "!" reference whose scope is a task to a task elsewhere in the
project when that scope had no such child, and dated a milestone at a start
inherited from its container even when a predecessor had not finished.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

HEAD = 'project p "p" 2026-11-02 +2w { timingresolution 60min }\n'
RESOURCE = 'resource r "R" { workinghours mon - fri 9:00 - 17:00 }\n'


def plan(tmp_path: Path, text: str) -> tuple[int, str]:
    path = tmp_path / "plan.tjp"
    path.write_text(text + 'taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }\n')
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
    "elsewhere",
    ['task x "X" { duration 1d }\n', 'task h "H" {\n  task x "X" { duration 1d }\n}\n'],
    ids=["top_level_task", "other_branch"],
)
def test_a_bang_reference_names_a_child_of_its_scope_or_nothing(tmp_path: Path, elsewhere: str) -> None:
    text = HEAD + 'task g "G" {\n  task b "B" { duration 1d depends !x }\n}\n' + elsewhere
    code, output = plan(tmp_path, text)
    assert code != 0, output
    assert "task 'g.b' depends on '!x', which names no task from where it is written" in output


def test_a_reference_that_reaches_the_top_level_binds_the_only_match(tmp_path: Path) -> None:
    # "!!pack" from delivery.b reaches the top level, where there is no pack.
    text = HEAD + 'task delivery "D" {\n  task pack "P" { duration 1d }\n  task b "B" { duration 1d depends !!pack }\n}\n'
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "delivery.b,2026-11-03-00:00,2026-11-04-00:00" in output


def test_an_inherited_start_holds_a_milestone_until_its_predecessor_ends(tmp_path: Path) -> None:
    text = HEAD + RESOURCE + (
        'task g "G" {\n  start 2026-11-02-09:00\n'
        '  task a "A" { effort 8h allocate r }\n  task m "M" { milestone depends !a }\n}\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "g.a,2026-11-02-09:00,2026-11-02-17:00" in output
    assert "g.m,2026-11-02-17:00,2026-11-02-17:00" in output


def test_an_inherited_start_later_than_the_predecessor_still_holds(tmp_path: Path) -> None:
    text = HEAD + RESOURCE + (
        'task a "A" { effort 8h allocate r }\n'
        'task g "G" {\n  start 2026-11-03-12:00\n  task m "M" { milestone depends a }\n}\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "g.m,2026-11-03-12:00,2026-11-03-12:00" in output


def test_a_milestone_start_of_its_own_is_still_fixed(tmp_path: Path) -> None:
    text = HEAD + RESOURCE + (
        'task g "G" {\n  task a "A" { effort 8h allocate r start 2026-11-02-09:00 }\n'
        '  task m "M" { milestone start 2026-11-02-09:00 depends !a }\n}\n'
    )
    code, output = plan(tmp_path, text)
    assert code != 0, output
    assert "Task 'g.m' depends on 'g.a' and must start no earlier than 2026-11-02 17:00:00" in output
