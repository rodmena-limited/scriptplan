"""Duration parsing: one table, used everywhere.

TaskJuggler distinguishes two kinds of duration and ScriptPlan must too:

* **calendar** time runs on the wall clock. ``1d`` is 24 hours whether or not
  anyone is working. ``duration`` and ``gapduration`` are calendar time.
* **working** time runs on the project's working calendar. ``1d`` is one
  working day, which is ``dailyworkinghours`` long. ``effort``, ``length`` and
  ``gaplength`` are working time.

The unit letters are the same in both: ``min`` minutes, ``h`` hours, ``d``
days, ``w`` weeks, ``m`` **months**, ``y`` years. ``m`` is months, never
minutes -- writing ``30m`` when you meant ``30min`` is a factor of about
44,000, so the two are kept strictly apart.
"""

from __future__ import annotations

import re
from typing import Union

__all__ = [
    "DEFAULT_DAILY_WORKING_HOURS",
    "DEFAULT_YEARLY_WORKING_DAYS",
    "WEEKS_PER_YEAR",
    "DurationError",
    "parse_calendar_duration",
    "parse_working_duration",
    "parse_working_hours",
    "parse_time_of_day",
    "split_duration",
    "Duration",
    "project_seconds",
    "project_hours",
]

DEFAULT_DAILY_WORKING_HOURS = 8.0
# Weeks in a year, and the working days in one, kept as exact expressions
# rather than the decimals TaskJuggler prints (52.1429 and 260.714). Those are
# the same numbers truncated, and truncating them makes a week 39.99992 hours
# instead of 40, which shows up as a task ending a second early.
WEEKS_PER_YEAR = 365.0 / 7.0
DEFAULT_YEARLY_WORKING_DAYS = WEEKS_PER_YEAR * 5.0

# Calendar seconds per unit. Months and years follow TaskJuggler's
# rule_calendarDuration: a month is 30.4167 days, a year is 365 days.
_CALENDAR_SECONDS = {
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "w": 7 * 86400.0,
    "m": 30.4167 * 86400.0,
    "y": 365 * 86400.0,
}

_DURATION = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(min|[hdwmy])?\s*$", re.IGNORECASE)


class DurationError(ValueError):
    """Raised when a duration cannot be read."""


def split_duration(text: Union[str, int, float]) -> tuple[float, str]:
    """Split ``"30min"`` into ``(30.0, "min")``.

    A bare number means hours, which is how the .tjp grammar reads a duration
    with no unit.
    """
    if isinstance(text, (int, float)):
        return float(text), "h"
    match = _DURATION.match(str(text))
    if not match:
        raise DurationError(
            f"{text!r} is not a duration. Expected a number and one of "
            f"min, h, d, w, m (months), y -- for example '30min', '4h', '2d'."
        )
    amount = float(match.group(1))
    unit = (match.group(2) or "h").lower()
    return amount, unit


def parse_calendar_duration(text: Union[str, int, float]) -> float:
    """Seconds of wall-clock time. ``2d`` is 172800, weekend or not."""
    amount, unit = split_duration(text)
    return amount * _CALENDAR_SECONDS[unit]


def parse_working_duration(
    text: Union[str, int, float],
    daily_working_hours: float = DEFAULT_DAILY_WORKING_HOURS,
    yearly_working_days: float = DEFAULT_YEARLY_WORKING_DAYS,
) -> float:
    """Seconds of working time.

    With the defaults (8 hours a day, 260.714 working days a year) this gives
    the familiar 1d = 8h, 1w = 40h, 1m = 173.8h, 1y = 2085.7h.
    """
    amount, unit = split_duration(text)
    day = daily_working_hours * 3600.0
    per_unit = {
        "min": 60.0,
        "h": 3600.0,
        "d": day,
        "w": day * yearly_working_days / WEEKS_PER_YEAR,
        "m": day * yearly_working_days / 12.0,
        "y": day * yearly_working_days,
    }
    return amount * per_unit[unit]


def parse_working_hours(
    text: Union[str, int, float],
    daily_working_hours: float = DEFAULT_DAILY_WORKING_HOURS,
    yearly_working_days: float = DEFAULT_YEARLY_WORKING_DAYS,
) -> float:
    """Working time expressed in hours, the unit efforts are stored in."""
    return parse_working_duration(text, daily_working_hours, yearly_working_days) / 3600.0


def parse_time_of_day(text: str) -> int:
    """``"08:13"`` to minutes past midnight."""
    parts = str(text).split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        raise DurationError(f"{text!r} is not a time of day; expected HH:MM") from None
    return hour * 60 + minute


class Duration:
    """A duration as written in the file, with the kind of time it counts.

    The conversion needs ``dailyworkinghours`` and ``yearlyworkingdays``, which
    belong to the project and are not known while the grammar is being
    transformed. So the text and its kind travel together and are resolved once
    the project exists.
    """

    __slots__ = ("text", "kind")

    CALENDAR = "calendar"
    WORKING = "working"

    def __init__(self, text: Union[str, int, float], kind: str) -> None:
        self.text = text
        self.kind = kind
        # Fail at parse time on an unreadable duration rather than at use.
        split_duration(text)

    def seconds(
        self,
        daily_working_hours: float = DEFAULT_DAILY_WORKING_HOURS,
        yearly_working_days: float = DEFAULT_YEARLY_WORKING_DAYS,
    ) -> float:
        if self.kind == Duration.CALENDAR:
            return parse_calendar_duration(self.text)
        return parse_working_duration(self.text, daily_working_hours, yearly_working_days)

    def hours(
        self,
        daily_working_hours: float = DEFAULT_DAILY_WORKING_HOURS,
        yearly_working_days: float = DEFAULT_YEARLY_WORKING_DAYS,
    ) -> float:
        return self.seconds(daily_working_hours, yearly_working_days) / 3600.0

    def __repr__(self) -> str:
        return f"Duration({self.text!r}, {self.kind})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return (str(self.text), self.kind) == (str(other.text), other.kind)

    def __hash__(self) -> int:
        return hash((str(self.text), self.kind))


def project_seconds(project: object, value: object) -> float:
    """Resolve a Duration against a project's working-hours settings."""
    attributes = getattr(project, "attributes", {})
    daily = attributes.get("dailyworkinghours") or DEFAULT_DAILY_WORKING_HOURS
    yearly = attributes.get("yearlyworkingdays") or DEFAULT_YEARLY_WORKING_DAYS
    if isinstance(value, Duration):
        return value.seconds(float(daily), float(yearly))
    return parse_calendar_duration(value)  # type: ignore[arg-type]


def project_hours(project: object, value: object) -> float:
    """Resolve a Duration to hours against a project's settings."""
    return project_seconds(project, value) / 3600.0
