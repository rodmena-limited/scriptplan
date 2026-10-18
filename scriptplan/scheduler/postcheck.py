"""Constraints checked after a scenario is scheduled.

Some constraints cannot be enforced while placing a task, only verified once
everything is placed: a maximum gap depends on where the successor ended up,
and a deadline on where the task itself did. Verifying them is the difference
between a constraint the file states and a constraint the schedule keeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from scriptplan.core.declared_dates import note_written

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
    _check_dependencies_kept(project, scenario_idx)
    _check_max_gaps(project, scenario_idx)
    _check_date_limits(project, scenario_idx)
    _check_stated_dates(project, scenario_idx)
    for task in project.tasks:
        scenario = task.data[scenario_idx] if task.data else None
        if scenario is not None:
            note_written(scenario)


def _check_dependencies_kept(project: Any, scenario_idx: int) -> None:
    """Every task starts after what it depends on, plus the gap the file states.

    Placement keeps this, except where the file fixes a start that a
    dependency contradicts; 0.10.1 then scheduled the task anyway, before its
    predecessor ended, and said nothing (issuedb #19). Checking every
    dependency of the finished schedule also catches any placement defect
    that would break one.
    """
    for task in project.tasks:
        scenario = task.data[scenario_idx] if task.leaf() and task.data else None
        if scenario is None or not task.get("scheduled", scenario_idx):
            continue
        start, end = task.get("start", scenario_idx), task.get("end", scenario_idx)
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            continue
        forward = task.get("forward", scenario_idx) is not False
        for dep in scenario.getAllDependencies():
            predecessor, options = _dependency_parts(dep)
            if predecessor is None or not predecessor.get("scheduled", scenario_idx):
                continue
            onstart = bool(options.get("onstart"))
            anchor = predecessor.get("start" if onstart else "end", scenario_idx)
            if not isinstance(anchor, datetime):
                continue
            gap = options.get("gapduration")
            if onstart and not forward:
                # Read for a backward task as: it must end before the predecessor starts.
                latest = anchor - timedelta(seconds=scenario._calendarSeconds(gap)) if gap else anchor
                if end > latest:
                    _dependency_error(project, task, predecessor, f"end by {latest}", f"ends at {end}")
                continue
            earliest = anchor + timedelta(seconds=scenario._calendarSeconds(gap)) if gap else anchor
            if options.get("gaplength"):
                earliest = scenario._advanceWorkingTime(anchor, scenario._workingSeconds(options["gaplength"]))
            if start < earliest:
                declared = _states_start(task, scenario_idx)
                _dependency_error(
                    project,
                    task,
                    predecessor,
                    f"start no earlier than {earliest}",
                    f"starts at {start}" + (", the start the file declares for it" if declared else ""),
                )


def _states_start(task: Any, scenario_idx: int) -> bool:
    try:
        attribute = task._get_scenario_attribute("start", scenario_idx)
    except (ValueError, KeyError, AttributeError):
        return False
    return bool(attribute.getProvided())


def _dependency_error(project: Any, task: Any, predecessor: Any, required: str, actual: str) -> None:
    project.error(
        "dependency_violated",
        f"Task '{task.fullId}' depends on '{predecessor.fullId}' and must {required}, but it "
        f"{actual}. This condition could not be met.",
        data=task.fullId,
    )


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


def _check_stated_dates(project: Any, scenario_idx: int) -> None:
    """The dates a file states for a task are kept.

    A stated end on a task scheduled as soon as possible was overwritten by
    wherever the work happened to finish (issuedb #21), and a stated start on
    a task scheduled as late as possible by wherever it had to begin
    (issuedb #24). Dates outside the project window are refused before
    scheduling (preflight.stated_dates_inside_window).
    """
    for task in project.tasks:
        scenario = task.data[scenario_idx] if task.data else None
        if scenario is None:
            continue
        stated_start = getattr(scenario, "declaredStart", None)
        stated_end = getattr(scenario, "declaredEnd", None)
        if not task.get("scheduled", scenario_idx):
            continue
        start, end = task.get("start", scenario_idx), task.get("end", scenario_idx)
        if isinstance(stated_end, datetime) and isinstance(end, datetime) and end > stated_end:
            project.error(
                "end_violated",
                f"Task '{task.fullId}' must end by {stated_end}, the end the file states for it, "
                f"but its work ends at {end}.",
                data=task.fullId,
            )
        if isinstance(stated_start, datetime) and isinstance(start, datetime) and start < stated_start:
            project.error(
                "start_violated",
                f"Task '{task.fullId}' may not start before {stated_start}, the start the file states "
                f"for it, but its work would have to start at {start} to be done in time.",
                data=task.fullId,
            )
