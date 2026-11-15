"""Who gets a contended resource, and what a task books (issuedb #36, #37, #39).

Until 0.10.3 a task with a stated start and end booked none of the resources
it allocated, a task's criticalness was never computed, so equal priorities
fell back to declaration order, allocating a group failed, and a lower limit
was counted and never reported.

Every expected date is the hour-level reference scheduler's.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT = 'taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }\n'
HEAD = 'project "R" 2026-12-01 +1m { timezone "Europe/London" }\n'
ALWAYS = 'resource r "R" { workinghours mon - sun 00:00 - 24:00 }\n'
DESK = 'resource desk "Desk" { workinghours mon - fri 09:00 - 17:00 }\n'


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


def booked_hours(text: str) -> dict[str, float]:
    from scriptplan.parser.tjp_parser import ProjectFileParser

    project = ProjectFileParser().parse(text)
    return {task.id: task.data[0].getAllocatedTime() for task in project.tasks}


def test_a_stated_period_holds_its_resource_against_a_lower_priority(tmp_path: Path) -> None:
    text = HEAD + ALWAYS + (
        'task a "A" { priority 600 start 2026-12-03-18:00 end 2026-12-03-20:00 allocate r }\n'
        'task w "W" { effort 1h allocate r start 2026-12-03-18:00 }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "a,2026-12-03-18:00,2026-12-03-20:00" in output
    assert "w,2026-12-03-20:00,2026-12-03-21:00" in output


def test_overlapping_stated_periods_share_the_resource_without_double_booking() -> None:
    text = HEAD + ALWAYS + (
        'task a "A" { start 2026-12-03-18:00 end 2026-12-03-20:00 allocate r }\n'
        'task b "B" { start 2026-12-03-19:00 end 2026-12-03-21:00 allocate r }\n'
        'task c "C" { start 2026-12-03-20:00 end 2026-12-03-21:00 allocate r }\n'
    )
    # a holds 18:00-20:00, b gets the hour that is left, c gets nothing.
    assert booked_hours(text) == {"a": 2.0, "b": 1.0, "c": 0.0}


def test_an_effort_task_is_placed_before_a_duration_task_of_the_same_priority(tmp_path: Path) -> None:
    text = HEAD + ALWAYS + (
        'task a "A" { duration 2h allocate r start 2026-12-03-18:00 }\n'
        'task w "W" { effort 1h allocate r start 2026-12-03-18:00 }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "w,2026-12-03-18:00,2026-12-03-19:00" in output


FOUR = (
    'task t0 "T0" {{ effort 4h allocate desk {extra} }}\n'
    'task t1 "T1" {{ effort 1h allocate desk {extra} }}\n'
    'task t2 "T2" {{ effort 4h allocate desk {extra} }}\n'
)


@pytest.mark.parametrize(
    "desk, extra, rows",
    [
        (
            DESK,
            "",
            ["t0,2026-10-19-09:00,2026-10-19-13:00", "t2,2026-10-19-13:00,2026-10-19-17:00", "t1,2026-10-20-09:00,2026-10-20-10:00"],
        ),
        (
            DESK,
            "scheduling alap end 2026-10-23-17:00",
            ["t0,2026-10-23-13:00,2026-10-23-17:00", "t2,2026-10-23-09:00,2026-10-23-13:00", "t1,2026-10-22-16:00,2026-10-22-17:00"],
        ),
        (
            DESK.replace(" }", " limits { dailymax 6h } }"),
            "",
            ["t0,2026-10-19-09:00,2026-10-19-13:00", "t2,2026-10-19-13:00,2026-10-20-11:00", "t1,2026-10-20-11:00,2026-10-20-12:00"],
        ),
    ],
    ids=["forward", "backward", "daily_cap"],
)
def test_equal_priorities_are_placed_larger_effort_first(tmp_path: Path, desk: str, extra: str, rows: list[str]) -> None:
    text = 'project "K" 2026-10-19 +2w { timezone "Etc/UTC" }\n' + desk + FOUR.format(extra=extra)
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for row in rows:
        assert row in output


def test_a_task_with_work_behind_it_is_placed_before_a_larger_task_without(tmp_path: Path) -> None:
    text = 'project "K" 2025-01-06 +2w { timezone "Etc/UTC" }\n' + DESK + (
        'task a "A" { start 2025-01-06 effort 3h allocate desk }\n'
        'task b "B" { start 2025-01-06 effort 1h allocate desk }\n'
        'task c "C" { depends !a effort 2h allocate desk }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for row in ("a,2025-01-06-09:00,2025-01-06-12:00", "c,2025-01-06-12:00,2025-01-06-14:00", "b,2025-01-06-14:00,2025-01-06-15:00"):
        assert row in output


def test_allocating_a_group_books_every_member(tmp_path: Path) -> None:
    text = 'project p "P" 2025-01-06 +3m { timezone "Etc/UTC" }\n' + (
        'resource r "R" {\n  resource a "A" { workinghours mon - fri 9:00 - 17:00 }\n'
        '  resource b "B" { workinghours mon - fri 9:00 - 17:00 }\n}\n'
        'task t "T" { effort 16h allocate r }\ntask u "U" { effort 8h allocate a }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "t,2025-01-06-09:00,2025-01-06-17:00" in output
    assert "u,2025-01-07-09:00,2025-01-07-17:00" in output


def test_limits_inside_an_allocation_are_refused(tmp_path: Path) -> None:
    text = 'project p "P" 2025-01-06 +3m { timezone "Etc/UTC" }\n' + DESK + (
        'task t "T" { effort 16h allocate desk { limits { dailymax 4h } } }\n'
    )
    code, output = plan(tmp_path, text)
    assert code != 0, output
    assert "allocate { limits { ... } } is not supported" in output
    assert "Error trying to process rule" not in output


def test_a_missed_minimum_is_a_warning_the_report_command_shows(tmp_path: Path) -> None:
    text = 'project p "P" 2025-01-06 +3m { timezone "Etc/UTC" }\n' + (
        'resource r "R" { workinghours mon - fri 9:00 - 17:00 limits { dailymin 6h } }\n'
        'task t "T" { effort 4h allocate r }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "Warning: Resource 'r' was booked for less than its dailymin in 1 period; the largest shortfall is 2.00 hours." in output
    assert "t,2025-01-06-09:00,2025-01-06-13:00" in output


def test_a_minimum_that_is_met_draws_no_warning(tmp_path: Path) -> None:
    text = 'project p "P" 2025-01-06 +3m { timezone "Etc/UTC" }\n' + (
        'resource r "R" { workinghours mon - fri 9:00 - 17:00 limits { dailymin 4h } }\n'
        'task t "T" { effort 8h allocate r }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "Warning" not in output


DIAMOND = {
    "a": 'task a "A" { start 2025-01-06 effort 2h allocate desk }\n',
    "b": 'task b "B" { start 2025-01-06 effort 3h allocate desk }\n',
}


@pytest.mark.parametrize("order", ["ab", "ba"])
def test_a_shared_follower_counts_for_both_tasks_that_lead_into_it(tmp_path: Path, order: str) -> None:
    # ScriptPlan's own rule (issuedb #44). 0.10.3 counted c for whichever of a
    # and b the file declared first, so a went first when it was declared
    # first, though b is the larger. Now c counts for both and b goes first
    # in either order.
    text = 'project "K" 2025-01-06 +2w { timezone "Etc/UTC" }\n' + DESK + DIAMOND[order[0]] + DIAMOND[order[1]] + (
        'task c "C" { depends a, b effort 8h allocate desk }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for row in ("b,2025-01-06-09:00,2025-01-06-12:00", "a,2025-01-06-12:00,2025-01-06-14:00", "c,2025-01-06-14:00,2025-01-07-14:00"):
        assert row in output, output


def test_a_chain_of_twelve_hundred_tasks_schedules(tmp_path: Path) -> None:
    # 0.10.3 walked the chain by recursion and stopped with "maximum recursion
    # depth exceeded" at about a thousand tasks (issuedb #46).
    tasks = ['task t0 "T0" { effort 1h allocate desk }'] + [
        f'task t{i} "T{i}" {{ effort 1h allocate desk depends t{i - 1} }}' for i in range(1, 1200)
    ]
    text = 'project "K" 2025-01-06 +2y { timezone "Etc/UTC" }\n' + DESK + "\n".join(tasks) + "\n"
    code, output = plan(tmp_path, text)
    assert code == 0, output[-400:]
    # 1,200 hours at 40 a week is thirty weeks: the last hour is Friday 1 August.
    assert "t1199,2025-08-01-16:00,2025-08-01-17:00" in output
