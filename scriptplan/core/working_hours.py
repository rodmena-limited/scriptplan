"""
WorkingHours class for managing per-resource working hour schedules.

This class handles irregular working hours like "08:15 - 11:45, 13:15 - 16:30"
for specific days of the week.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Optional

# Try to import Cython-optimized functions
try:
    from scriptplan._cython.working_hours_cy import (
        calculate_daily_hours,
        check_working_hours_fast,
    )

    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False

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


class WorkingHours:
    """
    Manages working hours for a resource.

    Working hours are defined as time intervals for each day of the week.
    For example:
        Mon, Wed, Fri: 08:15 - 11:45, 13:15 - 16:30
        Tue, Thu: 09:00 - 10:30, 14:45 - 16:00
    """

    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    DAY_MAP: ClassVar[dict[str, int]] = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

    def __init__(self, project: "Project") -> None:
        """
        Initialize working hours.

        Args:
            project: Project reference for time conversion
        """
        self.project = project
        # Dict mapping weekday (0-6) to list of (start_time, end_time) tuples
        # Times are stored as (hour, minute) tuples
        self._hours: dict[int, list[tuple[tuple[int, int], tuple[int, int]]]] = {}
        # Start with empty hours - will be populated by set_hours()
        # If no hours are set, onShift will fall back to project default
        self._custom_hours_set = False

    def set_hours(self, days: list[str], ranges: list[tuple[str, str]]) -> None:
        """
        Set working hours for specific days.

        Args:
            days: List of day names like ['mon', 'wed', 'fri']
            ranges: List of (start_time, end_time) tuples like [('08:15', '11:45')]
        """
        self._custom_hours_set = True

        # Convert day names to weekday numbers
        day_nums: list[int] = []
        for day in days:
            day_lower = day.lower()
            if day_lower in self.DAY_MAP:
                day_nums.append(self.DAY_MAP[day_lower])

        # Handle day ranges like "mon - fri"
        if len(day_nums) == 0:
            return

        # Parse time ranges to (hour, minute) tuples
        time_intervals: list[tuple[tuple[int, int], tuple[int, int]]] = []
        for start_str, end_str in ranges:
            start_h, start_m = self._parse_time(start_str)
            end_h, end_m = self._parse_time(end_str)
            time_intervals.append(((start_h, start_m), (end_h, end_m)))

        # Set hours for each day
        # NOTE: Multiple workinghours directives for the same resource will
        # result in multiple calls. The behavior depends on whether days overlap:
        # - Different days: each gets its own time intervals
        # - Same day called multiple times: extends (adds more intervals)
        for day_num in day_nums:
            if day_num not in self._hours:
                self._hours[day_num] = []
            # Extend with new intervals (allows multiple non-contiguous ranges per day)
            self._hours[day_num].extend(time_intervals)

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
        # If no custom hours set, fall back to project default
        if not self._custom_hours_set:
            return self.project.isWorkingTime(slot_idx)

        # Get datetime for this slot (in UTC)
        dt = self.project.idxToDate(slot_idx)
        if dt is None:
            return False

        # Convert UTC time to resource's local timezone if specified
        if timezone:
            dt = self._convert_to_timezone(dt, timezone)
            if dt is None:
                return False

        weekday = dt.weekday()

        # Check if this day has working hours defined
        if weekday not in self._hours or not self._hours[weekday]:
            # No working hours defined for this day = not working
            return False

        slot_minutes = dt.hour * 60 + dt.minute

        # Use Cython-optimized version if available
        if _USE_CYTHON:
            return bool(check_working_hours_fast(slot_minutes, weekday, self._hours, True))

        # Check if slot falls within any working interval
        for (start_h, start_m), (end_h, end_m) in self._hours[weekday]:
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            # Check for cross-midnight shift (e.g., 22:00 - 06:00)
            if end_minutes <= start_minutes:
                # This interval crosses midnight
                # Working time is: start_minutes <= slot < 1440 OR 0 <= slot < end_minutes
                if slot_minutes >= start_minutes or slot_minutes < end_minutes:
                    return True
            else:
                # Normal interval within same day
                if start_minutes <= slot_minutes < end_minutes:
                    return True

        # Also check if we're in the early morning part of a cross-midnight shift from previous day
        prev_weekday = (weekday - 1) % 7
        if self._hours.get(prev_weekday):
            for (start_h, start_m), (end_h, end_m) in self._hours[prev_weekday]:
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                # If previous day had a cross-midnight shift
                if end_minutes <= start_minutes and slot_minutes < end_minutes:
                    # Check if current slot is in the morning part (0 <= slot < end)
                    return True

        return False

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

        # Use Cython-optimized version if available
        if _USE_CYTHON:
            return float(calculate_daily_hours(self._hours[weekday]))

        total_minutes = 0
        for (start_h, start_m), (end_h, end_m) in self._hours[weekday]:
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            total_minutes += end_minutes - start_minutes

        return total_minutes / 60.0

    def clear_day(self, weekday: int) -> None:
        """Clear working hours for a specific day."""
        if weekday in self._hours:
            self._hours[weekday] = []

    def clear_all(self) -> None:
        """Clear all working hours."""
        self._hours = {}

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
