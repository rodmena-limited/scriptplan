"""The project's time axis and its default working calendar.

Slots are UTC and fixed width. Turning a moment into a slot and back, sizing
the scoreboard, and deciding whether a slot is inside the default working day,
are all questions about the axis rather than about scheduling, so they live
here.

The calendar is the week the project's ``workinghours`` lines state, or weekdays
nine to five when it states none. It is read in the project's own timezone:
comparing the hour of a UTC slot against 9 to 17 puts a New York project's
working day five hours out. A global ``vacation`` or ``leaves`` closes it for
everyone, whatever the leave is called.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from scriptplan.core.timezones import from_utc
from scriptplan.scheduler.scoreboard import Scoreboard

# The default working calendar when the project declares none.
DEFAULT_WORK_START_HOUR = 9
DEFAULT_WORK_END_HOUR = 17

__all__ = [
    "DEFAULT_WORK_END_HOUR",
    "DEFAULT_WORK_START_HOUR",
    "add_project_hours",
    "date_to_idx",
    "global_closures",
    "idx_to_date",
    "in_project_hours",
    "in_week",
    "init_scoreboards",
    "is_default_working_time",
    "is_working_time",
    "scoreboard_size",
]


def add_project_hours(project: Any, spec: Any) -> None:
    """Record one ``workinghours`` line of the project block.

    The lines together state the project's whole week, as they do for a shift
    or a resource: a day no line names is not worked.
    """
    from scriptplan.core.working_hours import WorkingHours

    hours = project.attributes.get("workinghours")
    if not isinstance(hours, WorkingHours):
        hours = WorkingHours(project)
        project.attributes["workinghours"] = hours
    if isinstance(spec, dict):
        hours.set_hours(spec.get("days", []), spec.get("ranges", []))


def global_closures(project: Any) -> list[Any]:
    """Every global vacation and leave, which close the calendar for everyone."""
    return [*(project.attributes.get("vacations") or ()), *(project.attributes.get("leaves") or ())]


def init_scoreboards(project: Any) -> None:
    if not project.attributes["start"] or not project.attributes["end"]:
        return

    project.scoreboard = Scoreboard(
        project.attributes["start"], project.attributes["end"], project.attributes["scheduleGranularity"], 2
    )
    project.scoreboardNoLeaves = Scoreboard(
        project.attributes["start"], project.attributes["end"], project.attributes["scheduleGranularity"], 2
    )

    # A working slot is None. scoreboardNoLeaves is the bare week; scoreboard
    # is the week less every global vacation and leave.
    size: int = project.scoreboardSize()
    for i in range(size):
        if in_project_hours(project, project.idxToDate(i)):
            project.scoreboard[i] = None
            project.scoreboardNoLeaves[i] = None

    for away in global_closures(project):
        interval = getattr(away, "interval", None)
        if not interval:
            continue
        first = max(0, project.dateToIdx(interval.start))
        last = min(size, project.dateToIdx(interval.end))
        for i in range(first, last):
            if interval.start <= project.idxToDate(i) < interval.end:
                project.scoreboard[i] = 2


def in_project_hours(project: Any, date: Any | None) -> bool:
    """Whether a moment falls in the project's working week, leave aside.

    Slots are UTC and the week is meant in the project's own timezone, so the
    moment is read there.
    """
    if date is None:
        return False
    local = from_utc(date, project.attributes.get("timezone")) or date
    hours = project.attributes.get("workinghours")
    if hours is not None and hasattr(hours, "covers"):
        covered: bool = hours.covers(local)
        return covered
    if local.weekday() >= 5:  # Saturday or Sunday
        return False
    result: bool = DEFAULT_WORK_START_HOUR <= local.hour < DEFAULT_WORK_END_HOUR
    return result


def is_default_working_time(project: Any, date: Any | None) -> bool:
    """Whether a moment is project working time: in the week, and not closed."""
    if date is None:
        return False
    for away in global_closures(project):
        interval = getattr(away, "interval", None)
        if interval:
            if interval.start <= date < interval.end:
                return False
        elif hasattr(away, "contains") and away.contains(date):
            return False
    return in_project_hours(project, date)


def is_working_time(project: Any, sbIdx: int) -> bool:
    """Check if a scoreboard slot is working time."""
    if project.scoreboard is None:
        return is_default_working_time(project, project.idxToDate(sbIdx))
    result: Any = project.scoreboard[sbIdx]
    return result is None


def in_week(project: Any, sbIdx: int) -> bool:
    """Whether a slot is in the project's working week, leave aside."""
    if project.scoreboardNoLeaves is None:
        return in_project_hours(project, project.idxToDate(sbIdx))
    result: Any = project.scoreboardNoLeaves[sbIdx]
    return result is None


def scoreboard_size(project: Any) -> int:
    if project.scoreboard:
        size: int = project.scoreboard.size
        return size
    if project.attributes["start"] and project.attributes["end"]:
        try:
            diff_seconds: float = (project.attributes["end"] - project.attributes["start"]).total_seconds()
        except AttributeError:
            diff_seconds = float(project.attributes["end"] - project.attributes["start"])
        return int(diff_seconds / project.attributes["scheduleGranularity"]) + 1
    return 0


def date_to_idx(project: Any, date: Any, forceIntoProject: bool = True) -> int:
    if not project.attributes["start"]:
        return 0

    try:
        diff_seconds: float = (date - project.attributes["start"]).total_seconds()
    except AttributeError:
        diff_seconds = float(date - project.attributes["start"])

    idx: int = int(diff_seconds / project.attributes["scheduleGranularity"])
    return idx


def idx_to_date(project: Any, idx: int) -> Any | None:
    if not project.attributes["start"]:
        return None

    # Assuming idx is integer steps of scheduleGranularity from start
    seconds: int = idx * project.attributes["scheduleGranularity"]
    return project.attributes["start"] + timedelta(seconds=seconds)
