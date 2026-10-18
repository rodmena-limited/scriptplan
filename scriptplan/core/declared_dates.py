"""The start and end a file states for a task, kept apart from what a run writes.

The scheduler writes a task's computed start and end back into the same
attributes the file stated them in. Anything that needs the statement itself
-- a backward task bounded by its successor's stated start, a check that a
stated end was met -- would otherwise read the previous run's result on the
second run, and scheduling twice would not give the same answer (issuedb #14,
#21, #24).
"""

from __future__ import annotations

from typing import Any

__all__ = ["note_written", "remember_declared"]

NAMES = ("start", "end")


def remember_declared(scenario: Any) -> None:
    """Keep each stated date, unless what the attribute holds is our own last result."""
    written = getattr(scenario, "_writtenDates", {})
    for name in NAMES:
        try:
            attribute = scenario.property._get_scenario_attribute(name, scenario.scenarioIdx)
        except (ValueError, KeyError):
            setattr(scenario, _slot(name), None)
            continue
        stated = attribute.getProvided() or attribute.getInherited()
        current = scenario.property.get(name, scenario.scenarioIdx) if stated else None
        if current is None or current != written.get(name):
            # First run, or the caller changed it since: that is the declaration.
            setattr(scenario, _slot(name), current)
    scenario._writtenDates = {}


def note_written(scenario: Any) -> None:
    """Record the dates this run left in stated attributes, to recognise them next run."""
    scenario._writtenDates = {
        name: scenario.property.get(name, scenario.scenarioIdx)
        for name in NAMES
        if getattr(scenario, _slot(name), None) is not None
    }


def _slot(name: str) -> str:
    return "declared" + name.capitalize()
