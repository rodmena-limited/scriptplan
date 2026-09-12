"""The project's time axis and its default working calendar.

Slots are UTC and fixed width. Turning a moment into a slot and back, sizing
the scoreboard, and deciding whether a slot is inside the default working day,
are all questions about the axis rather than about scheduling, so they live
here.

The default calendar -- weekdays, nine to five -- is read in the project's own
timezone. Comparing the hour of a UTC slot against 9 to 17 puts a New York
project's working day five hours out.
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
    "date_to_idx",
    "idx_to_date",
    "init_scoreboards",
    "is_default_working_time",
    "is_working_time",
    "scoreboard_size",
]


def init_scoreboards(project: Any) -> None:
    if not project.attributes["start"] or not project.attributes["end"]:
        return

    project.scoreboard = Scoreboard(
        project.attributes["start"], project.attributes["end"], project.attributes["scheduleGranularity"], 2
    )
    project.scoreboardNoLeaves = Scoreboard(
        project.attributes["start"], project.attributes["end"], project.attributes["scheduleGranularity"], 2
    )

    # Initialize working time slots - mark working hours as None
    # Default working hours: Mon-Fri, 9am-5pm
    size: int = project.scoreboardSize()
    project.attributes["scheduleGranularity"]

    for i in range(size):
        date = project.idxToDate(i)
        if is_default_working_time(project, date):
            project.scoreboard[i] = None
            project.scoreboardNoLeaves[i] = None


def is_default_working_time(project: Any, date: Any | None) -> bool:
    """Whether a slot falls in the project's default working hours.

    Slots are UTC; the default calendar (weekdays, 9am to 5pm) is meant in
    the project's own timezone, so the slot is read there. Comparing the
    hour of a UTC slot against 9-17 puts a New York project's working day
    five hours out.
    """
    if date is None:
        return False
    # Check global vacations, which are stored in UTC like the slot.
    vacations = project.attributes.get("vacations", [])
    for vac in vacations:
        if hasattr(vac, "interval") and vac.interval:
            if vac.interval.start <= date < vac.interval.end:
                return False
        elif hasattr(vac, "contains") and vac.contains(date):
            return False

    local = from_utc(date, project.attributes.get("timezone")) or date
    if local.weekday() >= 5:  # Saturday or Sunday
        return False
    result: bool = DEFAULT_WORK_START_HOUR <= local.hour < DEFAULT_WORK_END_HOUR
    return result


def is_working_time(project: Any, sbIdx: int) -> bool:
    """Check if a scoreboard slot is working time."""
    if project.scoreboard is None:
        return is_default_working_time(project, project.idxToDate(sbIdx))
    result: Any = project.scoreboard[sbIdx]
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
