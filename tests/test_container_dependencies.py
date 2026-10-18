"""A dependency on a container holds for every task inside it (issuedb #32).

Trace found that a container depending on another with a gap never scheduled
its children, in 0.10.1 and 0.10.2. Inheriting the dependency copied the task
it named, so the child waited for a copy that was never scheduled. Scheduled
backwards, a task inside a container was not bounded by a successor that
depended on the container, and 0.10.1 placed it after that successor.

The forward answers are the hour-level reference scheduler's. The backward
ones are worked out by hand: it cannot bound a task from a `depends`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT = """project x "x" 2026-11-09 +2w {{
  timingresolution 30min
  {mode}
}}
resource r "R" {{ workinghours mon - fri 8:30 - 17:30 }}
task p "P" {{
  task p1 "p1" {{ effort 60min allocate r }}
}}
task q "Q" {{
  {q_lines}
  {children}
}}
taskreport out "out" {{ formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }}
"""
CHILD = 'task c "C" { effort 60min allocate r }'


def plan(tmp_path: Path, *, q_lines: str, children: str = CHILD, mode: str = "") -> tuple[int, str]:
    path = tmp_path / "plan.tjp"
    path.write_text(PROJECT.format(mode=mode, q_lines=q_lines, children=children))
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
    "q_lines, children, expected",
    [
        ("depends p { gapduration 30min }", CHILD, ["q.c,2026-11-09-10:00,2026-11-09-11:00"]),
        ("depends p { gaplength 90min }", CHILD, ["q.c,2026-11-09-11:00,2026-11-09-12:00"]),
        ("depends p { onstart }", 'task c "C" { duration 60min }', ["q.c,2026-11-09-08:30,2026-11-09-09:30"]),
        (
            "depends p { gapduration 30min }",
            'task s "S" {\n    ' + CHILD + "\n  }",
            ["q.s.c,2026-11-09-10:00,2026-11-09-11:00"],
        ),
        (
            "depends p { gapduration 30min }",
            CHILD + '\n  task d "D" { effort 30min allocate r depends !c }',
            ["q.c,2026-11-09-10:00,2026-11-09-11:00", "q.d,2026-11-09-11:00,2026-11-09-11:30"],
        ),
    ],
    ids=["gapduration", "gaplength", "onstart", "nested_child", "two_children"],
)
def test_a_container_dependency_with_options_holds_for_its_children(
    tmp_path: Path, q_lines: str, children: str, expected: list[str]
) -> None:
    code, output = plan(tmp_path, q_lines=q_lines, children=children)
    assert code == 0, output
    assert "p.p1,2026-11-09-08:30,2026-11-09-09:30" in output
    for row in expected:
        assert row in output


@pytest.mark.parametrize(
    "dependency, p1",
    [("depends p { gapduration 30min }", "p.p1,2026-11-09-15:00,2026-11-09-16:00"), ("depends p", "p.p1,2026-11-09-15:30,2026-11-09-16:30")],
    ids=["with_gap", "without_gap"],
)
def test_a_backward_task_is_bounded_by_a_successor_of_its_container(tmp_path: Path, dependency: str, p1: str) -> None:
    code, output = plan(tmp_path, q_lines=f"end 2026-11-09-17:30\n  {dependency}", mode="scheduling alap")
    assert code == 0, output
    assert "q.c,2026-11-09-16:30,2026-11-09-17:30" in output
    assert p1 in output


def test_a_broken_container_dependency_is_reported_once_with_the_declared_start(tmp_path: Path) -> None:
    code, output = plan(
        tmp_path,
        q_lines="depends p { gapduration 30min }",
        children='task c "C" { effort 60min allocate r start 2026-11-09-08:30 }',
    )
    assert code != 0, output
    message = (
        "Task 'q.c' depends on 'p' and must start no earlier than 2026-11-09 10:00:00, but it starts at "
        "2026-11-09 09:30:00, because the file declares a start of 2026-11-09 08:30:00 for it."
    )
    assert output.count(message) == 1, output


NESTED = """project x "x" 2026-11-09 +2w {{
  timingresolution 30min
  {mode}
}}
resource r "R" {{ workinghours mon - fri 8:30 - 17:30 }}
task p "P" {{
  task m "M" {{
    {inner}
  }}
  {sibling}
}}
{successor}
taskreport out "out" {{ formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }}
"""
LEAF_W = 'task w "W" { effort 60min allocate r }'


def nested(tmp_path: Path, *, successor: str, inner: str = LEAF_W, sibling: str = "", mode: str = "") -> tuple[int, str]:
    text = NESTED.format(mode=mode, inner=inner, sibling=sibling, successor=successor)
    path = tmp_path / "plan.tjp"
    path.write_text(text)
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


S_AFTER_P = 'task s "S" {\n  depends p\n  effort 60min\n  allocate r\n}'


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"successor": S_AFTER_P}, ["p,2026-11-09-08:30,2026-11-09-09:30", "s,2026-11-09-09:30,2026-11-09-10:30"]),
        (
            {"successor": S_AFTER_P, "inner": 'task k "K" {\n      ' + LEAF_W + "\n    }"},
            ["p.m.k.w,2026-11-09-08:30,2026-11-09-09:30", "s,2026-11-09-09:30,2026-11-09-10:30"],
        ),
        (
            {"successor": S_AFTER_P.replace("depends p", "depends p { gapduration 30min }")},
            ["s,2026-11-09-10:00,2026-11-09-11:00"],
        ),
        (
            {
                "successor": 'task q "Q" {\n  depends p { gapduration 30min }\n'
                '  task s "S" { effort 60min allocate r }\n  task t "T" { effort 30min allocate r depends !s }\n}'
            },
            ["q.s,2026-11-09-10:00,2026-11-09-11:00", "q.t,2026-11-09-11:00,2026-11-09-11:30"],
        ),
        (
            {"successor": S_AFTER_P, "sibling": 'task n "N" {\n    task v "V" { effort 30min allocate r depends !!m }\n  }'},
            ["p,2026-11-09-08:30,2026-11-09-10:00", "p.n.v,2026-11-09-09:30,2026-11-09-10:00", "s,2026-11-09-10:00,2026-11-09-11:00"],
        ),
    ],
    ids=["two_levels", "three_levels", "two_levels_with_gap", "container_after_nested", "nested_sibling_branch"],
)
def test_a_dependency_on_a_nested_container_waits_for_its_last_task(tmp_path: Path, kwargs: dict, expected: list[str]) -> None:
    # issuedb #33: the outer container was never marked done, so its successor never started.
    code, output = nested(tmp_path, **kwargs)
    assert code == 0, output
    for row in expected:
        assert row in output


def test_a_backward_task_deep_inside_a_container_is_bounded_by_its_successor(tmp_path: Path) -> None:
    code, output = nested(
        tmp_path, successor=S_AFTER_P.replace("depends p", "depends p\n  end 2026-11-09-17:30"), mode="scheduling alap"
    )
    assert code == 0, output
    assert "p.m.w,2026-11-09-15:30,2026-11-09-16:30" in output
    assert "s,2026-11-09-16:30,2026-11-09-17:30" in output


PRECEDES = """project x "x" 2026-11-09 +2w {{
  timingresolution 30min
}}
resource r "R" {{ workinghours mon - fri 8:30 - 17:30 }}
task a "A" {{ {mode} effort 60min allocate r precedes b {{ {option} }} }}
task b "B" {{ {mode} effort 60min allocate r {b_end} }}
taskreport out "out" {{ formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }}
"""


@pytest.mark.parametrize(
    "mode, option, b_end, rows",
    [
        ("", "gapduration 30min", "", ["a,2026-11-09-08:30,2026-11-09-09:30", "b,2026-11-09-10:00,2026-11-09-11:00"]),
        (
            "scheduling alap",
            "gapduration 30min",
            "end 2026-11-10-10:30",
            ["a,2026-11-09-17:00,2026-11-10-09:00", "b,2026-11-10-09:30,2026-11-10-10:30"],
        ),
        (
            "scheduling alap",
            "gaplength 90min",
            "end 2026-11-10-10:30",
            ["a,2026-11-09-15:00,2026-11-09-16:00", "b,2026-11-10-09:30,2026-11-10-10:30"],
        ),
    ],
    ids=["forward_gapduration", "backward_gapduration", "backward_gaplength"],
)
def test_precedes_keeps_its_gap(tmp_path: Path, mode: str, option: str, b_end: str, rows: list[str]) -> None:
    # issuedb #34: precedes used to drop its options, so b started the moment a ended.
    path = tmp_path / "plan.tjp"
    path.write_text(PRECEDES.format(mode=mode, option=option, b_end=b_end))
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    done = subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", str(path)],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=300,
    )
    output = done.stdout + done.stderr
    assert done.returncode == 0, output
    for row in rows:
        assert row in output


def test_precedes_with_onend_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "plan.tjp"
    path.write_text(PRECEDES.format(mode="", option="onend", b_end=""))
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    done = subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", str(path)],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=300,
    )
    output = done.stdout + done.stderr
    assert done.returncode != 0, output
    assert "task 'a' precedes 'b' { onend }" in output
