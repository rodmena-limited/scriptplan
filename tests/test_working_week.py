"""A block's week: what it inherits, and what a workinghours line changes (issuedb #42).

Until 0.11.0 the workinghours lines of a block stated its whole week: a day no
line named was not worked, and two lines for the same day added up. Other
schedulers of this format start each block from the week it inherits and let a
line replace the hours of the days it names. ScriptPlan now does the same.

Every expected date in the first two tests is the hour-level reference
scheduler's. The last test covers what only ScriptPlan accepts: a shift taken
with `workinghours <shift id>`, a resource timezone, a night shift.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT = 'taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }\n'
# 2025-06-02 is a Monday.
HEAD = 'project p "P" 2025-06-02 +2m {{ timezone "Etc/UTC" {hours} }}\n'


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


CASES = {
    "the_default_week_has_no_midday_break": (
        "",
        'resource r "R" {}\ntask t "T" { effort 20h allocate r }\ntask u "U" { effort 3h allocate r depends t }\n',
        ["t,2025-06-02-09:00,2025-06-04-13:00", "u,2025-06-04-13:00,2025-06-04-16:00"],
    ),
    "a_project_line_leaves_other_days_alone": (
        "workinghours mon 08:00 - 10:00",
        'resource r "R" {}\ntask t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-08:00,2025-06-05-11:00"],
    ),
    "a_resource_line_leaves_other_days_alone": (
        "",
        'resource r "R" { workinghours wed 10:00 - 12:00 }\ntask t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-09:00,2025-06-05-11:00"],
    ),
    "a_later_line_replaces_an_earlier_one": (
        "",
        'resource r "R" { workinghours mon - fri 09:00 - 12:00\n workinghours mon - fri 13:00 - 17:00 }\n'
        'task t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-13:00,2025-06-06-17:00"],
    ),
    "a_later_line_replaces_one_day_of_several": (
        "",
        'resource r "R" { workinghours mon - fri 09:00 - 12:00, 13:00 - 18:00\n workinghours wed 09:00 - 12:00 }\n'
        'task t "T" { effort 30h allocate r }\n',
        ["t,2025-06-02-09:00,2025-06-06-12:00"],
    ),
    "off_closes_the_days_it_names": (
        "",
        'resource r "R" { workinghours tue, thu off }\ntask t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-09:00,2025-06-06-13:00"],
    ),
    "a_sub_resource_starts_from_its_parents_week": (
        "",
        'resource g "G" { workinghours mon - fri 06:00 - 10:00\n  resource r "R" { workinghours wed 10:00 - 12:00 } }\n'
        'task t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-06:00,2025-06-09-08:00"],
    ),
    "a_sub_resource_declared_first_keeps_the_week_it_started_with": (
        "",
        'resource g "G" {\n  resource r "R" { }\n  workinghours mon - fri 06:00 - 10:00\n  resource q "Q" { }\n}\n'
        'task t "T" { effort 4h allocate r }\ntask u "U" { effort 4h allocate q }\n',
        ["t,2025-06-02-09:00,2025-06-02-13:00", "u,2025-06-02-06:00,2025-06-02-10:00"],
    ),
    "a_shift_starts_from_the_projects_week": (
        "workinghours mon - fri 07:00 - 11:00",
        'shift s "S" { workinghours wed 10:00 - 12:00 }\nresource r "R" { workinghours s }\n'
        'task t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-07:00,2025-06-09-09:00"],
    ),
    "a_resource_on_a_shift_works_the_shifts_whole_week": (
        "",
        'shift s "S" { workinghours wed 10:00 - 12:00 }\n'
        'resource r "R" { workinghours mon - sun 00:00 - 24:00\n workinghours s }\n'
        'task t "T" { effort 20h allocate r }\n',
        ["t,2025-06-02-09:00,2025-06-05-11:00"],
    ),
    "project_and_shift_lines_combine": (
        "workinghours fri off\n workinghours sat 10:00 - 12:00",
        'shift s "S" { workinghours mon off }\nresource r "R" { workinghours s }\nresource q "Q" { }\n'
        'task t "T" { effort 30h allocate r }\ntask u "U" { effort 30h allocate q }\n',
        ["t,2025-06-03-09:00,2025-06-10-13:00", "u,2025-06-02-09:00,2025-06-05-15:00"],
    ),
    "length_counts_the_projects_inherited_days": (
        "workinghours mon, wed, fri 09:00 - 17:00",
        'task t "T" { length 3d start 2025-06-04-09:00 }\n',
        ["t,2025-06-04-09:00,2025-06-06-17:00"],
    ),
}


@pytest.mark.parametrize("name", list(CASES))
def test_a_workinghours_line_replaces_the_days_it_names(tmp_path: Path, name: str) -> None:
    hours, body, rows = CASES[name]
    code, output = plan(tmp_path, HEAD.format(hours=hours) + body)
    assert code == 0, output
    for row in rows:
        assert row in output, output


def test_hours_are_read_in_the_projects_zone_when_the_resource_states_none(tmp_path: Path) -> None:
    # 0.10.3 read a resource's own hours as UTC: in London in June that is
    # ten to six. A resource with no hours of its own was already right.
    text = (
        'project p "P" 2025-06-02 +2m { timezone "Europe/London" }\n'
        'shift s "S" { workinghours mon - fri 09:00 - 17:00 }\n'
        'resource r "R" { workinghours mon - fri 09:00 - 17:00 }\n'
        'resource q "Q" { }\n'
        'resource x "X" { workinghours s }\n'
        'task t "T" { effort 8h allocate r }\ntask u "U" { effort 8h allocate q }\ntask v "V" { effort 8h allocate x }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for task in "tuv":
        assert f"{task},2025-06-02-09:00,2025-06-02-17:00" in output, output


def test_scriptplans_own_forms_follow_the_same_rule(tmp_path: Path) -> None:
    text = HEAD.format(hours="") + (
        'shift s "S" { workinghours mon - fri 07:00 - 11:00 }\n'
        # No hours of its own: the project's week, in Tokyo, is 00:00-08:00 UTC.
        'resource tk "Tokyo" { timezone "Asia/Tokyo" }\n'
        # The shift, then a line: Friday is off. A line, then the shift: the shift's week.
        'resource a "A" { workinghours s\n workinghours fri off }\n'
        'resource b "B" { workinghours fri off\n workinghours s }\n'
        # A night shift belongs to the day it starts on, in either order.
        'resource n1 "N1" { workinghours sun 22:00 - 06:00\n workinghours mon 09:00 - 17:00 }\n'
        'resource n2 "N2" { workinghours mon 09:00 - 17:00\n workinghours sun 22:00 - 06:00 }\n'
        'task t "T" { effort 8h allocate tk }\n'
        'task u "U" { effort 20h allocate a }\n'
        'task v "V" { effort 20h allocate b }\n'
        'task w1 "W1" { effort 10h allocate n1 start 2025-06-08-00:00 }\n'
        'task w2 "W2" { effort 10h allocate n2 start 2025-06-08-00:00 }\n'
    )
    code, output = plan(tmp_path, text)
    assert code == 0, output
    for row in (
        "t,2025-06-02-00:00,2025-06-02-08:00",
        "u,2025-06-02-07:00,2025-06-09-11:00",
        "v,2025-06-02-07:00,2025-06-06-11:00",
        "w1,2025-06-08-22:00,2025-06-09-11:00",
        "w2,2025-06-08-22:00,2025-06-09-11:00",
    ):
        assert row in output, output
