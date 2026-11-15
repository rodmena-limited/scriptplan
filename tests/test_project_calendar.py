"""The project calendar: its working hours and the leave that closes it (issuedb #35).

Siambr found that 0.10.2 parsed a project's `workinghours` and never applied
it, and that a global `leaves` did not close the calendar `length` counts in.
A shift's `leaves` was dropped when parsed. No fixture set any of the three,
so nothing could fail.

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


DECEMBER = 'project "R" 2026-12-01 +1m {{ timezone "Europe/London" {hours} }}\n'


@pytest.mark.parametrize(
    "hours, end",
    [
        ("workinghours mon - sat 09:00 - 17:00", "2026-12-05-17:00"),
        ("workinghours mon - fri 08:00 - 16:00", "2026-12-08-09:00"),
        ("workinghours mon - fri 00:00 - 24:00", "2026-12-04-09:00"),
        ("", "2026-12-07-17:00"),
    ],
    ids=["mon_to_sat", "eight_to_four", "round_the_clock", "default_week"],
)
@pytest.mark.parametrize(
    "body",
    ['resource r "R" {}\ntask t "T" { effort 3d allocate r start 2026-12-03-09:00 }\n', 'task t "T" { length 3d start 2026-12-03-09:00 }\n'],
    ids=["resource_without_hours", "length"],
)
def test_the_project_working_hours_are_the_calendar(tmp_path: Path, hours: str, end: str, body: str) -> None:
    code, output = plan(tmp_path, DECEMBER.format(hours=hours) + body)
    assert code == 0, output
    assert f"t,2026-12-03-09:00,{end}" in output


@pytest.mark.parametrize(
    "closure, end",
    [
        ('leaves holiday "Christmas" 2026-12-25', "2026-12-29-17:00"),
        ('leaves annual "Shutdown" 2026-12-25', "2026-12-29-17:00"),
        ('vacation "Christmas" 2026-12-25', "2026-12-29-17:00"),
        ('leaves holiday "Half day" 2026-12-24-13:00 - 2026-12-24-17:00', "2026-12-29-13:00"),
        ('leaves holiday "Christmas" 2026-12-25 - 2026-12-29', "2026-12-30-17:00"),
        ("", "2026-12-28-17:00"),
    ],
    ids=["holiday", "any_leave_type", "vacation", "part_of_a_day", "several_days", "none"],
)
def test_a_global_leave_closes_the_calendar_length_counts_in(tmp_path: Path, closure: str, end: str) -> None:
    text = DECEMBER.format(hours="") + closure + '\ntask t "T" { length 3d start 2026-12-24-09:00 }\n'
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert f"t,2026-12-24-09:00,{end}" in output


def test_a_gaplength_does_not_count_a_global_holiday(tmp_path: Path) -> None:
    text = DECEMBER.format(hours="") + (
        'leaves holiday "Christmas" 2026-12-25\n'
        'task g "G" { duration 1d start 2026-12-24-00:00 }\n'
        'task h "H" { depends g { gaplength 1d } duration 1h }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    # g ends at midnight on the 25th; the eight working hours after it are Monday the 28th.
    assert "h,2026-12-28-17:00,2026-12-28-18:00" in output


@pytest.mark.parametrize("closure", ['vacation "V" 2026-12-08', 'leaves holiday "V" 2026-12-08'], ids=["vacation", "leaves"])
def test_a_holiday_in_the_first_week_is_not_repeated_every_week(tmp_path: Path, closure: str) -> None:
    # 0.10.2 tiled the first week's vacation across the project for a resource
    # on the default hours in a UTC project, and ended the effort on the 23rd.
    text = (
        'project "R" 2026-12-07 +2m { timezone "Etc/UTC" }\n' + closure + '\nresource r "R" {}\n'
        'task t "T" { effort 10d allocate r start 2026-12-07-09:00 }\n'
        'task l "L" { length 10d start 2026-12-07-09:00 }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    assert "t,2026-12-07-09:00,2026-12-21-17:00" in output
    assert "l,2026-12-07-09:00,2026-12-21-17:00" in output


def test_a_shift_leave_holds_for_a_resource_on_the_shift(tmp_path: Path) -> None:
    text = (
        'project "R" 2026-12-01 +2m { timezone "Europe/London" dailyworkinghours 8 }\n'
        'shift council "Council" { workinghours mon - sat 09:00 - 17:00\n leaves holiday 2026-12-23 }\n'
        'resource r1 "R1" { workinghours council }\n'
        'task t "T" { effort 5d allocate r1 start 2026-12-19-00:00 }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    # Sat 19, Mon 21, Tue 22, Thu 24, Fri 25: the 23rd is the shift's holiday.
    assert "t,2026-12-19-09:00,2026-12-25-17:00" in output


@pytest.mark.parametrize("line", ["leaves holiday", "leaves annual", "vacation"])
def test_each_leave_line_is_stored_once(line: str) -> None:
    # 0.10.2 stored every earlier leave again with each line: 2^N - 1 entries
    # for N lines, and twenty of them took a minute to schedule (issuedb #40).
    from scriptplan.parser.tjp_parser import ProjectFileParser

    days = "\n".join(f"  {line} 2027-01-{day:02d}" for day in range(4, 24))
    text = (
        'project p "P" 2026-11-01 +5m { timezone "Europe/London" }\n'
        'resource r "R" { workinghours mon - fri 09:00 - 17:00\n' + days + "\n}\n"
        'task t "T" { effort 30d allocate r end 2027-02-15-09:00 scheduling alap }\n'
    )
    # Counted before scheduling: a million entries would not schedule in a test's lifetime.
    unscheduled = ProjectFileParser().parse(text, schedule=False)
    assert len(next(iter(unscheduled.resources)).get("leaves", 0)) == 20
    project = ProjectFileParser().parse(text)
    task = next(iter(project.tasks))
    # Ten working days in February and five in late January; 4 to 23 January
    # are away; the other fifteen are 14 December to 1 January.
    assert f"{task.get('start', 0):%Y-%m-%d-%H:%M}" == "2026-12-14-09:00"
    assert f"{task.get('end', 0):%Y-%m-%d-%H:%M}" == "2027-02-12-17:00"
