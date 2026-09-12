"""Limits: how much of a period a resource or task may consume.

A limit is an amount of working time per period -- per calendar day, per ISO
week, per calendar month, or over the whole project. Two details matter and
both used to be wrong:

* **Limits count seconds, not slots.** Counting whole slots cannot express a
  cap smaller than the slot size, and rounding one down turns a 30-minute cap
  into no cap at all or into a total block, depending on which way it rounds.
* **A period is a period in the resource's own calendar.** A resource in Los
  Angeles reaches the end of its day eight hours after a resource in London
  does. Bucketing by UTC date lets a "4 hours a day" resource work five hours
  in one of its own days.

A limit admits a booking only when the whole booking fits, so a cap is never
exceeded by part of a slot.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scriptplan.core.project import Project
    from scriptplan.core.resource import Resource

__all__ = ["PERIOD_KINDS", "Limit", "Limits"]

# name -> (period kind, is an upper limit)
PERIOD_KINDS: dict[str, tuple[str, bool]] = {
    "dailymax": ("day", True),
    "dailymin": ("day", False),
    "weeklymax": ("week", True),
    "weeklymin": ("week", False),
    "monthlymax": ("month", True),
    "monthlymin": ("month", False),
    "maximum": ("interval", True),
    "minimum": ("interval", False),
}


def _zone(name: str | None) -> Any:
    if not name:
        return None
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # pragma: no cover - unknown zone falls back to UTC
        return None


class Limit:
    """One cap: an amount of time per period, optionally for one resource."""

    def __init__(
        self,
        name: str,
        interval_start: datetime,
        interval_end: datetime,
        period: int | float | str,
        value: int | float,
        upper: bool,
        resource: Resource | None = None,
        slot_duration: int = 3600,
        timezone: str | None = None,
    ) -> None:
        self.name = name
        self.interval_start = interval_start
        self.interval_end = interval_end
        # `period` is the period kind ("day"/"week"/"month"/"interval"). Numbers
        # are accepted for callers that still pass seconds.
        self.period = period if isinstance(period, str) else _period_kind_for_seconds(period)
        self.value = value  # seconds
        self.upper = upper
        self.resource = resource
        self.slot_duration = slot_duration
        self.timezone = timezone
        self._counters: dict[Any, float] = {}

    # -- construction ------------------------------------------------------

    def copy(self) -> Limit:
        return Limit(
            self.name,
            self.interval_start,
            self.interval_end,
            self.period,
            self.value,
            self.upper,
            self.resource,
            self.slot_duration,
            self.timezone,
        )

    def reset(self, index: int | None = None) -> None:
        """Clear the counters, or just the one covering ``index``."""
        if index is None:
            self._counters.clear()
        else:
            self._counters.pop(self._period_key(index), None)

    # -- period bucketing --------------------------------------------------

    def _slot_datetime(self, index: int) -> datetime:
        return self.interval_start + timedelta(seconds=index * self.slot_duration)

    def _period_key(self, index: int) -> Any:
        moment = self._slot_datetime(index)
        zone = _zone(self.timezone)
        if zone is not None:
            from datetime import timezone as _utc

            aware = moment.replace(tzinfo=_utc.utc) if moment.tzinfo is None else moment
            moment = aware.astimezone(zone)
        if self.period == "day":
            return moment.date()
        if self.period == "week":
            year, week, _ = moment.isocalendar()
            return (year, week)
        if self.period == "month":
            return (moment.year, moment.month)
        return "interval"

    def _contains(self, index: int) -> bool:
        """Whether ``index`` falls inside the limit's interval."""
        moment = self._slot_datetime(index)
        return self.interval_start <= moment < self.interval_end

    # -- counting ----------------------------------------------------------

    def _applies_to(self, resource: Any | None) -> bool:
        if self.resource is None:
            return True
        return self.resource == resource

    def inc(self, index: int, resource: Any | None = None, seconds: float | None = None) -> None:
        if not self._applies_to(resource) or not self._contains(index):
            return
        amount = self.slot_duration if seconds is None else seconds
        key = self._period_key(index)
        self._counters[key] = self._counters.get(key, 0.0) + amount

    def dec(self, index: int, resource: Any | None = None, seconds: float | None = None) -> None:
        if not self._applies_to(resource) or not self._contains(index):
            return
        amount = self.slot_duration if seconds is None else seconds
        key = self._period_key(index)
        self._counters[key] = self._counters.get(key, 0.0) - amount

    def used(self, index: int) -> float:
        return self._counters.get(self._period_key(index), 0.0)

    def ok(
        self,
        index: int | None,
        upper: bool,
        resource: Any | None = None,
        seconds: float | None = None,
    ) -> bool:
        """Whether a booking of ``seconds`` at ``index`` is within this limit.

        An upper limit admits the booking only if the whole of it fits, so the
        cap is never overshot by part of a slot.
        """
        if self.upper != upper or not self._applies_to(resource):
            return True

        if index is None:
            if self.upper:
                return all(used < self.value for used in self._counters.values())
            return all(used >= self.value for used in self._counters.values())

        if not self._contains(index):
            return True

        used = self.used(index)
        if self.upper:
            wanted = self.slot_duration if seconds is None else seconds
            return used + wanted <= self.value
        return used >= self.value

    def remaining(self, index: int, resource: Any | None = None) -> float | None:
        """Seconds still allowed in the period covering ``index``.

        None means this limit does not constrain that booking. A cap smaller
        than one slot returns a part of a slot rather than zero, so a resource
        held to 30 minutes a day works 30 minutes a day instead of not at all.
        """
        if not self.upper or not self._applies_to(resource) or not self._contains(index):
            return None
        return max(0.0, self.value - self.used(index))

    def shortfall(self) -> list[tuple[Any, float]]:
        """Periods that did not reach a lower limit, as (period, seconds)."""
        if self.upper:
            return []
        return [(key, self.value - used) for key, used in sorted(self._counters.items()) if used < self.value]


def _period_kind_for_seconds(period: int | float) -> str:
    """Map a legacy period expressed in seconds onto a period kind."""
    if period >= 60 * 60 * 24 * 28:
        return "month"
    if period >= 60 * 60 * 24 * 7:
        return "week"
    if period >= 60 * 60 * 24:
        return "day"
    return "interval"


class Limits:
    """The limits declared on one task or resource."""

    def __init__(self, limits: Limits | None = None) -> None:
        self._limits: list[Limit] = []
        self.project: Project | None = None
        self.timezone: str | None = None

        if limits is not None:
            self._limits = [limit.copy() for limit in limits._limits]
            self.project = limits.project
            self.timezone = limits.timezone

    def copy(self) -> Limits:
        return Limits(self)

    def setProject(self, project: Project) -> None:
        if self._limits:
            raise RuntimeError("Cannot change project after limits have been set!")
        self.project = project

    def setTimeZone(self, timezone: str | None) -> None:
        """Count periods in this zone's calendar.

        Called once the owning resource's timezone is known, which is after the
        limits themselves have been read.
        """
        self.timezone = timezone
        for limit in self._limits:
            limit.timezone = timezone

    def prepare(self, slot_duration: int, timezone: str | None = None) -> None:
        """Ready the counters for a scheduling run.

        The slot size is settled after the limits are read -- it can be derived
        from the times the project uses -- so it is applied here rather than at
        the moment the limit was declared.
        """
        if timezone is not None:
            self.setTimeZone(timezone)
        for limit in self._limits:
            limit.slot_duration = slot_duration
        self.reset()

    def reset(self) -> None:
        for limit in self._limits:
            limit.reset()

    def setLimit(
        self,
        name: str,
        value: int | float,
        interval: tuple[datetime, datetime] | None = None,
        resource: Resource | None = None,
    ) -> None:
        """Declare a limit of ``value`` hours per period."""
        if self.project is None:
            raise RuntimeError("Project must be set before adding limits")
        if name not in PERIOD_KINDS:
            raise ValueError(
                f"Unknown limit type: {name}. Expected one of {', '.join(sorted(PERIOD_KINDS))}."
            )

        interval_start, interval_end = interval if interval else (self.project["start"], self.project["end"])
        slot_duration: int = self.project.attributes.get("scheduleGranularity", 3600)
        period_kind, upper = PERIOD_KINDS[name]

        self._limits = [
            limit for limit in self._limits if not (limit.name == name and limit.resource == resource)
        ]
        self._limits.append(
            Limit(
                name,
                interval_start,
                interval_end,
                period_kind,
                float(value) * 3600.0,
                upper,
                resource,
                slot_duration,
                self.timezone,
            )
        )

    def inc(self, index: int, resource: Resource | None = None, seconds: float | None = None) -> None:
        for limit in self._limits:
            limit.inc(index, resource, seconds)

    def dec(self, index: int, resource: Resource | None = None, seconds: float | None = None) -> None:
        for limit in self._limits:
            limit.dec(index, resource, seconds)

    def ok(
        self,
        index: int | None = None,
        upper: bool = True,
        resource: Resource | None = None,
        seconds: float | None = None,
    ) -> bool:
        return all(limit.ok(index, upper, resource, seconds) for limit in self._limits)

    def remaining(self, index: int, resource: Resource | None = None) -> float | None:
        """The tightest amount of time still allowed at ``index``."""
        allowances = [
            value
            for value in (limit.remaining(index, resource) for limit in self._limits)
            if value is not None
        ]
        return min(allowances) if allowances else None

    def lowerLimitShortfalls(self) -> list[tuple[str, Any, float]]:
        """Every period that fell short of a lower limit."""
        found: list[tuple[str, Any, float]] = []
        for limit in self._limits:
            for period, missing in limit.shortfall():
                found.append((limit.name, period, missing))
        return found

    def __bool__(self) -> bool:
        return len(self._limits) > 0

    def __len__(self) -> int:
        return len(self._limits)
