"""When a resource is available, and laying that out across the project.

A resource is on shift when its week says so and it is not on leave. Its week
is the one it inherited with its own lines applied, read in its own timezone,
or in the project's when it states none. Setting a scoreboard up
asks that question once per slot per resource -- half a million times each for
a year at minute resolution -- so the answer is derived arithmetically where it
can be, and a week of it is computed and tiled where the pattern repeats.

It repeats only where no daylight-saving change can move it, which depends on
the zone the resource's hours are read in and on the project's.
"""

from __future__ import annotations

from typing import Any

from scriptplan.core.project_calendar import global_closures, in_week, project_week
from scriptplan.core.timezones import is_utc
from scriptplan.scheduler.scoreboard import Scoreboard

__all__ = [
    "cache_shift_inputs",
    "init_scoreboard",
    "mark_shift_pattern",
    "on_shift",
    "on_shift_ignoring_leave",
]


def init_scoreboard(scenario: Any) -> None:
    """
    Initialize the scoreboard for this resource.

    The scoreboard tracks the availability and bookings for each time slot.
    """
    start = scenario.project.attributes.get("start")
    end = scenario.project.attributes.get("end")
    granularity = scenario.project.attributes.get("scheduleGranularity", 3600)

    if not start or not end:
        return

    if not hasattr(scenario, "_workingHours"):
        cache_shift_inputs(scenario)

    scenario.scoreboard = Scoreboard(start, end, granularity, 2)
    size = scenario.project.scoreboardSize()

    mark_shift_pattern(scenario, size, int(granularity))

    # Apply global vacations and leaves: they close the calendar for everyone.
    for leave in global_closures(scenario.project):
        if hasattr(leave, "interval"):
            start_idx = max(0, scenario.project.dateToIdx(leave.interval.start))
            end_idx = scenario.project.dateToIdx(leave.interval.end)
            for i in range(start_idx, min(end_idx, size)):
                sb = scenario.scoreboard[i]
                val = 0 if sb is None else (sb & 2)
                leave_type = (leave.type_idx if hasattr(leave, "type_idx") else 0) or 1
                scenario.scoreboard[i] = val | (leave_type << 2)

    # Apply the resource's own leaves, and those of the shift it works
    res_leaves = scenario._leaves
    if res_leaves:
        for leave in res_leaves:
            if hasattr(leave, "interval"):
                start_idx = scenario.project.dateToIdx(leave.interval.start)
                end_idx = scenario.project.dateToIdx(leave.interval.end)
                for i in range(start_idx, min(end_idx, size)):
                    sb = scenario.scoreboard[i]
                    if sb is not None:
                        leave_idx = (sb & 0x3C) >> 2
                        leave_type = leave.type_idx if hasattr(leave, "type_idx") else 0
                        if leave_type > leave_idx:
                            scenario.scoreboard[i] = (sb & 0x2) | (leave_type << 2)
                    else:
                        leave_type = leave.type_idx if hasattr(leave, "type_idx") else 0
                        scenario.scoreboard[i] = leave_type << 2


def mark_shift_pattern(scenario: Any, size: int, granularity: int) -> None:
    """Mark every slot the resource is on shift for.

    Written straight into the underlying list, because going through the
    scoreboard's item assignment is half a million calls per resource for
    a year at minute resolution and does nothing but the same store.

    A resource whose hours are in UTC repeats exactly every week, so one
    week is computed and the rest tiled from it. A resource in a zone that
    observes daylight saving does not repeat, and is asked slot by slot.
    """

    slots = scenario.scoreboard.sb
    # Leave is applied to the scoreboard separately, just below, and is
    # checked again at booking time; tiling a week that had a holiday in it
    # would repeat that holiday every week of the year.
    on_shift = scenario.onShiftIgnoringLeave

    # The pattern repeats weekly only if no daylight-saving change can move
    # it. That depends on the resource's own zone when it has working hours
    # of its own, and on the project's when it falls back to the default
    # calendar, so both have to be free of one.
    week_slots = (7 * 86400) // granularity
    periodic = (
        is_utc(getattr(scenario, "_timezone", None))
        and is_utc(scenario.project.attributes.get("timezone"))
        and week_slots
        and week_slots < size
    )
    if not periodic:
        for i in range(size):
            slots[i] = None if on_shift(i) else 2
        return

    week = [None if on_shift(i) else 2 for i in range(week_slots)]
    for offset in range(0, size, week_slots):
        end = min(offset + week_slots, size)
        slots[offset:end] = week[: end - offset]


def cache_shift_inputs(scenario: Any) -> None:
    """Read once per scheduling run what onShift would otherwise re-read.

    onShift is the scheduler's hottest question -- hundreds of thousands of
    calls for a project of any size -- and none of what it consults changes
    while a run is in progress.
    """
    scenario._vacations = global_closures(scenario.project)
    scenario._leaves = list(scenario.property.get("leaves", scenario.scenarioIdx) or [])
    # A resource's hours are meant in its own zone, or in the project's when
    # it states none. Read as UTC, a London resource on nine to five worked
    # ten to six all summer (issuedb #42).
    own_zone = scenario.property.get("timezone", scenario.scenarioIdx)
    scenario._timezone = own_zone or scenario.project.attributes.get("timezone")

    shift = scenario.property.get("shifts", scenario.scenarioIdx)
    if shift is not None:
        # A resource on a shift takes the shift's leave with its hours.
        scenario._leaves += shift.get("leaves", scenario.scenarioIdx) or []

    # The resource's week: what it inherited, with its own lines applied.
    # None means it never departed from the project's.
    working_hours = scenario.property.get("workinghours", scenario.scenarioIdx)
    if working_hours is None or not hasattr(working_hours, "onShift"):
        working_hours = None
        project_zone = scenario.project.attributes.get("timezone")
        if own_zone and str(own_zone) != str(project_zone) and not (is_utc(own_zone) and is_utc(project_zone)):
            # The project's week, worked in the resource's own zone.
            working_hours = project_week(scenario.project)
    scenario._workingHours = working_hours


def on_shift(scenario: Any, sb_idx: int) -> bool:
    """
    Check if the resource is on shift at the given time slot.

    Args:
        sb_idx: Scoreboard index

    Returns:
        True if on shift, False otherwise
    """
    if not hasattr(scenario, "_workingHours"):
        cache_shift_inputs(scenario)

    if scenario._vacations or scenario._leaves:
        date = scenario.project.idxToDate(sb_idx)
        # Global vacations and leaves override everything, then the resource's own leave.
        for away in (*scenario._vacations, *scenario._leaves):
            interval = getattr(away, "interval", None)
            if interval and interval.start <= date < interval.end:
                return False

    return on_shift_ignoring_leave(scenario, sb_idx)


def on_shift_ignoring_leave(scenario: Any, sb_idx: int) -> bool:
    """Whether the resource's working hours cover this slot.

    Leave is deliberately not consulted. The shift itself repeats every
    week, which lets a year of it be computed once; leave does not, and is
    applied separately.
    """
    if not hasattr(scenario, "_workingHours"):
        cache_shift_inputs(scenario)

    if scenario._workingHours is not None:
        on_shift: bool = scenario._workingHours.onShift(sb_idx, timezone=scenario._timezone)
        return on_shift

    # Default: the project's week. Its global leave is applied with the
    # resource's own, so that a holiday is not tiled into every week.
    return in_week(scenario.project, sb_idx)
