"""Constraints checked after a scenario is scheduled.

Some constraints cannot be enforced while placing a task, only verified once
everything is placed: a maximum gap depends on where the successor ended up,
and a deadline on where the task itself did. Verifying them is the difference
between a constraint the file states and a constraint the schedule keeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

__all__ = ["run_post_checks"]


def _dependency_parts(dep: Any) -> tuple[Any | None, dict[str, Any]]:
    """The predecessor and the options recorded with a dependency."""
    if isinstance(dep, dict):
        return dep.get("task"), dep
    if hasattr(dep, "task"):
        return dep.task, {
            name: getattr(dep, name, None)
            for name in ("gapduration", "gaplength", "maxgapduration", "maxgaplength")
        }
    return dep, {}


def _describe(delta: timedelta) -> str:
    hours = delta.total_seconds() / 3600.0
    if hours >= 48:
        return f"{hours / 24:.1f} days"
    return f"{hours:.1f} hours"


def run_post_checks(project: Any, scenario_idx: int) -> None:
    """Report every stated constraint the finished schedule does not keep."""
    _check_max_gaps(project, scenario_idx)
    _check_date_limits(project, scenario_idx)


def _check_max_gaps(project: Any, scenario_idx: int) -> None:
    from scriptplan.core.units import Duration, parse_calendar_duration, project_seconds

    for task in project.tasks:
        if not task.leaf():
            continue
        start = task.get("start", scenario_idx)
        if not isinstance(start, datetime):
            continue
        for dep in task.get("depends", scenario_idx) or []:
            predecessor, options = _dependency_parts(dep)
            if predecessor is None:
                continue
            calendar_limit = options.get("maxgapduration")
            working_limit = options.get("maxgaplength")
            if not calendar_limit and not working_limit:
                continue
            predecessor_end = predecessor.get("end", scenario_idx)
            if not isinstance(predecessor_end, datetime):
                continue
            achieved = start - predecessor_end
            if calendar_limit:
                allowed = timedelta(seconds=parse_calendar_duration(calendar_limit))
                label = f"maxgapduration {calendar_limit}"
            else:
                allowed = timedelta(
                    seconds=project_seconds(project, Duration(str(working_limit), Duration.WORKING))
                )
                label = f"maxgaplength {working_limit}"
            if achieved > allowed:
                project.error(
                    "maxgap_violated",
                    f"Task '{task.fullId}' must start no more than {label} after "
                    f"'{predecessor.fullId}' ends, but the gap is {_describe(achieved)} "
                    f"({predecessor_end} to {start}). Something the successor needs was "
                    f"not free in time.",
                    data=task.fullId,
                )


def _check_date_limits(project: Any, scenario_idx: int) -> None:
    checks: tuple[tuple[str, str, Callable[[datetime, datetime], bool], str], ...] = (
        ("maxstart", "start", lambda actual, limit: actual > limit, "start no later than"),
        ("minstart", "start", lambda actual, limit: actual < limit, "start no earlier than"),
        ("maxend", "end", lambda actual, limit: actual > limit, "end no later than"),
        ("minend", "end", lambda actual, limit: actual < limit, "end no earlier than"),
    )
    for task in project.tasks:
        if not task.leaf():
            continue
        for attribute, actual_name, violated, phrase in checks:
            try:
                limit = task.get(attribute, scenario_idx)
            except (ValueError, KeyError, AttributeError):
                continue
            actual = task.get(actual_name, scenario_idx)
            if not isinstance(limit, datetime) or not isinstance(actual, datetime):
                continue
            if violated(actual, limit):
                project.error(
                    f"{attribute}_violated",
                    f"Task '{task.fullId}' was required to {phrase} {limit}, "
                    f"but it {actual_name}s at {actual}.",
                    data=task.fullId,
                )
