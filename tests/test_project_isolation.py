"""Two projects in one process must not affect each other.

ScriptPlan is a library: a service parses many projects in one interpreter.
State that lives on the class rather than on the project is how one project's
schedule comes to depend on which other project was parsed just before it.
"""

from __future__ import annotations

import contextlib
import io

from scriptplan.core.property import AttributeBase
from scriptplan.parser.tjp_parser import ProjectFileParser

UTC_PROJECT = """project p "P" 2025-01-06 +3m { timezone "Etc/UTC" now 2025-01-06 }
resource r "R" { workinghours mon-fri 9:00-17:00 }
task parent "Parent" { priority 100
  task child "Child" { priority 900 start 2025-01-06 effort 8h allocate r }
  task sibling "Sibling" { start 2025-01-06 effort 8h allocate r }
}
"""

TOKYO_PROJECT = """project other "Other" 2025-01-06 +1m { timezone "Asia/Tokyo" now 2025-01-06 }
resource r "R" { timezone "Asia/Tokyo" workinghours mon-fri 9:00-17:00 }
task a "A" { effort 2d allocate r }
"""


def _parse(text: str):
    noise = io.StringIO()
    with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(noise):
        return ProjectFileParser().parse(text)


def _snapshot(project) -> dict:
    return {
        task.fullId: (
            task.get("start", 0),
            task.get("end", 0),
            task.get("priority", 0),
            task.provided("priority", 0),
        )
        for task in project.tasks
    }


def test_parsing_another_project_does_not_change_this_one() -> None:
    alone = _snapshot(_parse(UTC_PROJECT))
    _parse(TOKYO_PROJECT)
    again = _snapshot(_parse(UTC_PROJECT))
    assert alone == again


def test_a_child_keeps_its_own_priority_rather_than_inheriting() -> None:
    project = _parse(UTC_PROJECT)
    rows = _snapshot(project)
    # The child states its own priority, so it is 'provided' and survives
    # inheritance; the sibling states none and takes the parent's.
    assert rows["parent.child"][2] == 900
    assert rows["parent.child"][3] is True
    assert rows["parent.sibling"][2] == 100
    assert rows["parent.sibling"][3] is False


def test_attribute_mode_belongs_to_the_project_not_the_process() -> None:
    first = _parse(UTC_PROJECT)
    second = _parse(TOKYO_PROJECT)
    assert first.attributeMode == AttributeBase.PROVIDED
    assert second.attributeMode == AttributeBase.PROVIDED

    # Changing one project's mode must not be visible to the other, nor leak
    # into the process-wide fallback.
    first.attributeMode = AttributeBase.COMPUTED
    assert second.attributeMode == AttributeBase.PROVIDED
    assert AttributeBase.mode() == AttributeBase.PROVIDED


def test_scheduling_restores_the_mode_even_when_it_fails() -> None:
    broken = """project p "P" 2025-01-06 +1w { timezone "Etc/UTC" now 2025-01-06 }
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 10d allocate r }
"""
    noise = io.StringIO()
    with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(noise):
        project = ProjectFileParser().parse(broken, schedule=False)
        scheduled = project.schedule()
    assert scheduled is False, "a task that cannot fit must be reported"
    assert project.attributeMode == AttributeBase.PROVIDED
