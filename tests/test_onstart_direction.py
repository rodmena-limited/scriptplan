"""`onstart` holds a task's start to another task's start (issuedb #43).

Until 0.11.0 ScriptPlan read `depends X { onstart }` on a task scheduled as
late as possible as "finish before X starts". No other scheduler of this
format reads it so: the file is refused there, and `precedes X` is how
finish-before-start is written.

Every expected date, and each refusal, is the hour-level reference scheduler's.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT = 'taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }\n'
HEAD = (
    'project p "P" 2025-07-01 +1m { timezone "Etc/UTC" }\n'
    'resource m "M" { workinghours mon - fri 08:00 - 16:00 }\n'
    'resource n "N" { workinghours mon - fri 08:00 - 16:00 }\n'
)
REFUSAL = "An onstart dependency needs a task scheduled as soon as possible"


def plan(tmp_path: Path, text: str) -> tuple[int, str]:
    path = tmp_path / "plan.tjp"
    path.write_text(text + REPORT)
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
    "tasks, refused, predecessor",
    [
        (
            'task pack "Pack" { scheduling alap end 2025-07-18-16:00 effort 8h allocate m }\n'
            'task b "B" { effort 16h allocate m depends pack { onstart } scheduling alap end 2025-07-17-16:00 }\n',
            "b",
            "pack",
        ),
        (
            'task b "B" { start 2025-07-14-08:00 effort 8h allocate m }\n'
            'task g "G" { depends b { onstart }\n'
            '  task c "C" { effort 8h allocate n }\n'
            '  task d "D" { effort 8h allocate n end 2025-07-25-16:00 scheduling alap } }\n',
            "g.d",
            "b",
        ),
    ],
    ids=["its_own", "inherited_from_a_container"],
)
def test_onstart_on_a_backward_task_is_refused(tmp_path: Path, tasks: str, refused: str, predecessor: str) -> None:
    code, output = plan(tmp_path, HEAD + tasks)
    assert code != 0, output
    assert f"Task '{refused}' is scheduled as late as possible and depends on '{predecessor}' {{ onstart }}" in output
    assert REFUSAL in output
    assert output.count(REFUSAL) == 1


def test_onstart_is_refused_when_the_project_schedules_backward(tmp_path: Path) -> None:
    text = (
        'project d "D" 2026-11-02 +4w { timezone "Etc/UTC" scheduling alap }\n'
        'resource r1 "Analyst" { workinghours mon - fri 8:30 - 17:30 }\n'
        'task g "Group" {\n  end 2026-11-06-17:30\n'
        '  task a "A" { effort 4h allocate r1 }\n'
        '  task b "B" { effort 8h allocate r1 depends !a { onstart } }\n}\n'
    )
    code, output = plan(tmp_path, text)
    assert code != 0, output
    assert "Task 'g.b' is scheduled as late as possible and depends on 'g.a' { onstart }" in output


def test_onstart_on_a_forward_task_is_start_to_start(tmp_path: Path) -> None:
    text = HEAD + (
        'task b "B" { start 2025-07-14-08:00 effort 8h allocate m }\n'
        'task a "A" { effort 16h allocate n depends b { onstart } }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "a,2025-07-14-08:00,2025-07-15-16:00" in output


def test_a_forward_task_may_start_with_a_backward_one(tmp_path: Path) -> None:
    # pack is placed backward from its end. The tasks that start with it are
    # placed forward from its start, and do not bound where it ends.
    text = HEAD + (
        'task pack "Pack" { scheduling alap end 2025-07-18-16:00 effort 8h allocate m }\n'
        'task b "B" { effort 16h allocate n depends pack { onstart } }\n'
        'task c "C" { effort 4h allocate n depends pack { onstart gapduration 2h } }\n'
        'task g "G" { depends pack { onstart }\n  task d "D" { effort 2h allocate m } }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for row in (
        "pack,2025-07-18-08:00,2025-07-18-16:00",
        "b,2025-07-18-08:00,2025-07-21-16:00",
        "c,2025-07-22-08:00,2025-07-22-12:00",
        "g.d,2025-07-21-08:00,2025-07-21-10:00",
    ):
        assert row in output


def test_precedes_is_how_a_backward_task_finishes_before_another_starts(tmp_path: Path) -> None:
    text = HEAD + (
        'task b "B" { end 2025-07-18-16:00 scheduling alap effort 8h allocate m }\n'
        'task a "A" { effort 16h allocate n precedes b }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "a,2025-07-16-08:00,2025-07-17-16:00" in output
    assert "b,2025-07-18-08:00,2025-07-18-16:00" in output
