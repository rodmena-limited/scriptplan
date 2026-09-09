"""Choosing the slot size when the file does not state one.

Scheduling advances in fixed slots. Too coarse and a task declared to start at
09:30 starts at 09:00, and a shift that runs 08:13 to 11:59 is credited with
whole hours it does not have. Too fine and a year-long project holds hundreds
of thousands of slots per resource for no gain.

So the slot size is derived from the times the project actually uses: the
common divisor of every time of day it mentions. A project written to the hour
keeps hour-long slots and the speed that goes with them; one that mentions
09:30 gets half-hours; one that mentions 08:13 gets minutes. `timingresolution`
overrides this whenever the author wants to decide for themselves.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Iterator

__all__ = ["derive_resolution", "MINIMUM_SECONDS", "MAXIMUM_SECONDS"]

MINIMUM_SECONDS = 60
MAXIMUM_SECONDS = 3600

_DATE_ATTRIBUTES = ("start", "end", "maxend", "maxstart", "minend", "minstart")


def _minutes_of_day(moment: Any) -> Any:
    if not isinstance(moment, datetime):
        return None
    return moment.hour * 60 + moment.minute


def _task_offsets(project: Any) -> Iterator[int]:
    for task in project.tasks:
        for name in _DATE_ATTRIBUTES:
            try:
                value = task.get(name, 0)
            except (ValueError, KeyError, AttributeError):
                continue
            minutes = _minutes_of_day(value)
            if minutes is not None:
                yield minutes


def _working_hour_offsets(project: Any) -> Iterator[int]:
    for holder in list(project.resources) + list(project.shifts):
        for name in ("workinghours", "shifts"):
            try:
                hours = holder.get(name, 0)
            except (ValueError, KeyError, AttributeError):
                continue
            if hours is None:
                continue
            if not hasattr(hours, "_hours") and hasattr(hours, "get"):
                try:
                    hours = hours.get("workinghours", 0)
                except (ValueError, KeyError, AttributeError):
                    continue
            for intervals in getattr(hours, "_hours", {}).values():
                for (start_h, start_m), (end_h, end_m) in intervals:
                    yield start_h * 60 + start_m
                    yield end_h * 60 + end_m


def _leave_offsets(project: Any) -> Iterator[int]:
    for holder in list(project.resources):
        try:
            leaves = holder.get("leaves", 0) or []
        except (ValueError, KeyError, AttributeError):
            continue
        for leave in leaves:
            interval = getattr(leave, "interval", None)
            for edge in (getattr(interval, "start", None), getattr(interval, "end", None)):
                minutes = _minutes_of_day(edge)
                if minutes is not None:
                    yield minutes


def derive_resolution(project: Any) -> int:
    """The largest slot size, in seconds, that lands on every time used."""
    divisor = MAXIMUM_SECONDS // 60  # in minutes
    for minutes in (
        *_task_offsets(project),
        *_working_hour_offsets(project),
        *_leave_offsets(project),
    ):
        if minutes:
            divisor = math.gcd(divisor, minutes)
        if divisor <= 1:
            break
    seconds = max(MINIMUM_SECONDS, min(MAXIMUM_SECONDS, divisor * 60))
    return seconds
