"""
A working week: for each weekday, the intervals that are worked.

A block of the project file (the project, a shift, a resource) does not state
its week from nothing. It starts with the week it inherits, and each
``workinghours`` line replaces the hours of the days it names:

    workinghours mon - thu 08:00 - 18:00    # Friday keeps what it had
    workinghours fri off                    # now Friday is not worked

The project starts from weekdays nine to five. A shift starts from the
project's week. A resource starts from its parent resource's week, or from the
project's when it has no parent.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from scriptplan.core.timezones import is_utc

try:
    import zoneinfo

    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    try:
        import pytz  # noqa: F401 - used dynamically in _convert_to_timezone  # type: ignore[import-not-found]

        HAS_PYTZ = True
    except ImportError:
        HAS_PYTZ = False

if TYPE_CHECKING:
    from scriptplan.core.project import Project


# The week a project has until its own lines change it.
DEFAULT_WEEKDAYS = (0, 1, 2, 3, 4)
DEFAULT_HOURS = ((9, 0), (17, 0))


class WorkingHours:
    """The intervals worked on each day of the week."""

    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    DAY_MAP: ClassVar[dict[str, int]] = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

    def __init__(self, project: "Project") -> None:
        """An empty week. ``default_week`` and ``copy`` give one to start from."""
        self.project = project
        # What each weekday (0-6) was given, as ((hour, minute), (hour, minute))
        # pairs. An interval whose end is at or before its start runs past
        # midnight and belongs to the day it starts on.
        self._given: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
        # The same week cut at midnight, so each interval lies inside one day.
        # Derived from _given; this is what lookups read.
        self._hours: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
        # False until the week holds something; onShift then falls back to the
        # project's calendar.
        self._custom_hours_set = False

    @classmethod
    def default_week(cls, project: "Project") -> "WorkingHours":
        """Monday to Friday, nine to five."""
        week = cls(project)
        week._custom_hours_set = True
        for day in DEFAULT_WEEKDAYS:
            week._given[day] = [DEFAULT_HOURS]
        week._cut_at_midnight()
        return week

    def copy(self) -> "WorkingHours":
        """A week of its own with the same hours, for a block that inherits them."""
        week = WorkingHours(self.project)
        week._custom_hours_set = self._custom_hours_set
        week._given = {day: list(intervals) for day, intervals in self._given.items()}
        week._cut_at_midnight()
        return week

    def set_hours(self, days: list[str], ranges: list[tuple[str, str]]) -> None:
        """Apply one ``workinghours`` line: the named days get exactly these hours.

        Args:
            days: List of day names like ['mon', 'wed', 'fri']
            ranges: List of (start_time, end_time) tuples like [('08:15', '11:45')].
                Empty for ``off``: the named days are not worked.

        A day the line does not name keeps the hours it had. A night shift
        belongs to the day it starts on: "sun 22:00 - 06:00" is Sunday's, and
        a later line for Monday leaves Monday's early hours alone.
        """
        self._custom_hours_set = True

        time_intervals: list[tuple[tuple[int, int], tuple[int, int]]] = []
        for start_str, end_str in ranges:
            time_intervals.append((self._parse_time(start_str), self._parse_time(end_str)))

        for day in days:
            day_num = self.DAY_MAP.get(day.lower())
            if day_num is not None:
                self._given[day_num] = list(time_intervals)
        self._cut_at_midnight()

    def _cut_at_midnight(self) -> None:
        """Derive the same-day intervals lookups read from what each day was given.

        "fri 22:00 - 06:00" becomes Friday 22:00-24:00 plus Saturday
        00:00-06:00. Cutting here keeps a lookup a plain "is this minute
        inside one of today's intervals" question, with no need to consult
        the day before.
        """
        self._hours = {}
        for day_num in sorted(self._given):
            for (start_h, start_m), (end_h, end_m) in self._given[day_num]:
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m
                if end_minutes <= start_minutes:
                    self._add_interval(day_num, (start_h, start_m), (24, 0))
                    if end_minutes > 0:
                        self._add_interval((day_num + 1) % 7, (0, 0), (end_h, end_m))
                else:
                    self._add_interval(day_num, (start_h, start_m), (end_h, end_m))

    def _add_interval(
        self, day_num: int, start: tuple[int, int], end: tuple[int, int]
    ) -> None:
        """Record one same-day interval for a weekday."""
        self._hours.setdefault(day_num, []).append((start, end))

    def _parse_time(self, time_str: str) -> tuple[int, int]:
        """Parse a time string like '08:15' to (hour, minute) tuple."""
        parts = str(time_str).split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return (hour, minute)

    def onShift(self, slot_idx: int, timezone: Optional[str] = None) -> bool:
        """
        Check if a slot index is within working hours.

        Args:
            slot_idx: Scoreboard slot index
            timezone: Optional timezone string (e.g., "Asia/Tokyo"). If provided,
                     the UTC slot time is converted to local time before checking
                     working hours. This enables resources in different timezones
                     to have their shifts defined in local time.

        Returns:
            True if the slot is within working hours
        """
        # An empty week falls back to the project's
        if not self._custom_hours_set:
            from scriptplan.core.project_calendar import in_week

            return in_week(self.project, slot_idx)

        if not timezone or is_utc(timezone):
            # Slots are UTC and evenly spaced, so which weekday and which
            # minute of it a slot falls on is arithmetic. Building a datetime
            # per slot instead dominates the cost of setting up a scoreboard:
            # a year at one-minute slots asks this question half a million
            # times per resource.
            placement = self._utc_placement(slot_idx)
            if placement is None:
                return False
            weekday, slot_minutes = placement
            return self._within_hours(weekday, slot_minutes)

        # Any other zone needs the real conversion, because a zone that
        # observes daylight saving is not weekly-periodic. It is the same for
        # every resource in the zone, so it is worked out once per zone.
        placed = self._zone_placement(slot_idx, timezone)
        if placed is None:
            return False
        return self._within_hours(placed // 1440, placed % 1440)

    def _zone_placement(self, slot_idx: int, timezone: str) -> Optional[int]:
        """Weekday * 1440 + minute of day, in ``timezone``, for a slot."""
        project = self.project
        axis = (project.attributes.get("start"), int(project.attributes.get("scheduleGranularity", 3600)))
        cache: dict[str, Any] = project.__dict__.setdefault("_zone_placements", {})
        if cache.get("axis") != axis:
            # A run on a different start or slot size must not read the
            # placements of the run before it.
            cache.clear()
            cache["axis"] = axis
        slots: dict[int, int] = cache.setdefault(timezone, {})
        placed = slots.get(slot_idx)
        if placed is None:
            dt = project.idxToDate(slot_idx)
            if dt is None:
                return None
            local = self._convert_to_timezone(dt, timezone)
            if local is None:
                return None
            placed = slots[slot_idx] = local.weekday() * 1440 + local.hour * 60 + local.minute
        return placed

    def covers(self, local: datetime) -> bool:
        """Whether a moment, already in the zone the hours are meant in, is worked."""
        return self._within_hours(local.weekday(), local.hour * 60 + local.minute)

    def _within_hours(self, weekday: int, slot_minutes: int) -> bool:
        """Whether a minute of a weekday falls in a working interval.

        Intervals are normalised at definition time, so each lies inside its
        own day and this is a plain containment test.
        """
        intervals = self._hours.get(weekday)
        if not intervals:
            return False
        for (start_h, start_m), (end_h, end_m) in intervals:
            if start_h * 60 + start_m <= slot_minutes < end_h * 60 + end_m:
                return True
        return False

    def _utc_placement(self, slot_idx: int) -> Optional[tuple[int, int]]:
        """(weekday, minute of day) for a UTC slot, without building a date."""
        base = getattr(self, "_utc_base", None)
        granularity = int(self.project.attributes.get("scheduleGranularity", 3600))
        if base is None or base[2] != granularity:
            start = self.project.attributes.get("start")
            if start is None:
                return None
            base = (
                start.weekday(),
                start.hour * 60 + start.minute,
                granularity,
            )
            self._utc_base = base
        start_weekday, start_minute, _ = base

        minutes = start_minute + (slot_idx * granularity) // 60
        days, minute_of_day = divmod(minutes, 1440)
        return (start_weekday + days) % 7, minute_of_day

    def get_daily_hours(self, weekday: int) -> float:
        """
        Get total working hours for a specific weekday.

        Args:
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Total working hours as float
        """
        if weekday not in self._hours:
            return 0.0

        total_minutes = 0
        for (start_h, start_m), (end_h, end_m) in self._hours[weekday]:
            # Normalised intervals never wrap, so this cannot go negative.
            total_minutes += (end_h * 60 + end_m) - (start_h * 60 + start_m)

        return total_minutes / 60.0

    def clear_day(self, weekday: int) -> None:
        """Make one day unworked."""
        self._given[weekday] = []
        self._cut_at_midnight()

    def clear_all(self) -> None:
        """Make every day unworked."""
        self._given = {}
        self._cut_at_midnight()

    def _convert_to_timezone(self, dt: datetime, timezone_str: str) -> Optional[datetime]:
        """
        Convert a naive UTC datetime to the specified timezone.

        Args:
            dt: Naive datetime (assumed to be UTC)
            timezone_str: Timezone string like "Asia/Tokyo" or "America/New_York"

        Returns:
            Datetime in the local timezone, or None if conversion fails
        """
        if not timezone_str:
            return dt

        try:
            if HAS_ZONEINFO:
                # Python 3.9+ with zoneinfo
                from datetime import timezone as dt_timezone

                utc_dt = dt.replace(tzinfo=dt_timezone.utc)
                tz = zoneinfo.ZoneInfo(timezone_str)
                return utc_dt.astimezone(tz)
            elif HAS_PYTZ:
                # Fallback to pytz
                import pytz

                utc = pytz.UTC
                utc_dt = utc.localize(dt)
                pytz_tz: Any = pytz.timezone(timezone_str)
                result = utc_dt.astimezone(pytz_tz)
                return result.replace(tzinfo=None) if result else None
            else:
                # No timezone support - return as-is with a warning
                return dt
        except Exception:
            # Invalid timezone - return original datetime
            return dt
