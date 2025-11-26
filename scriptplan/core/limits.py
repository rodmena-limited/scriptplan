"""
Limits implementation for resource allocation constraints.

Implements the limit mechanism that can restrict resource allocation within
certain time periods (daily, weekly, etc.). Supports both upper and lower limits.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from scriptplan.core.project import Project
    from scriptplan.core.resource import Resource


class Limit:
    """
    A single limit constraint that tracks usage within time periods.

    Limits can be:
    - dailymax/dailymin: Limit per day
    - weeklymax/weeklymin: Limit per week
    - monthlymax/monthlymin: Limit per month
    - maximum/minimum: Limit for the entire interval

    Limits can optionally be restricted to specific resources.
    """

    def __init__(
        self,
        name: str,
        interval_start: datetime,
        interval_end: datetime,
        period: Union[int, float],
        value: int,
        upper: bool,
        resource: Optional["Resource"] = None,
        slot_duration: int = 3600,
    ) -> None:
        """
        Create a new Limit.

        Args:
            name: Limit type name ('dailymax', 'weeklymax', etc.)
            interval_start: Start of the interval (datetime)
            interval_end: End of the interval (datetime)
            period: Duration of each period in seconds (86400 for daily)
            value: The limit value in slots
            upper: True for upper limit, False for lower limit
            resource: Optional resource this limit applies to
            slot_duration: Duration of each scheduling slot in seconds (default 1 hour)
        """
        self.name = name
        self.interval_start = interval_start
        self.interval_end = interval_end
        self.period = period
        self.value = value
        self.upper = upper
        self.resource = resource
        self.slot_duration = slot_duration

        self._dirty = True
        self._scoreboard: list[int] = []
        self.reset()

    def copy(self) -> "Limit":
        """Return a deep copy of this limit."""
        return Limit(
            self.name,
            self.interval_start,
            self.interval_end,
            self.period,
            self.value,
            self.upper,
            self.resource,
            self.slot_duration,
        )

    def reset(self, index: Optional[int] = None) -> None:
        """
        Reset counters for all periods or a specific period.

        Args:
            index: If provided, reset only the counter for this scoreboard index
        """
        if not self._dirty:
            return

        if index is None:
            # Calculate number of periods in the interval
            total_seconds = (self.interval_end - self.interval_start).total_seconds()
            num_periods = max(1, int(total_seconds / self.period) + 1)
            self._scoreboard = [0] * num_periods
        else:
            # Reset only the specific period
            if self._contains(index):
                sb_idx = self._idx_to_sb_idx(index)
                if 0 <= sb_idx < len(self._scoreboard):
                    self._scoreboard[sb_idx] = 0

        self._dirty = False

    def _contains(self, index: int) -> bool:
        """Check if a scoreboard index falls within this limit's interval."""
        # Convert index to datetime for comparison
        # index is the project scoreboard index
        return True  # We'll check bounds in _idx_to_sb_idx

    def _idx_to_sb_idx(self, index: int) -> int:
        """
        Convert project scoreboard index to limit scoreboard index.

        The limit scoreboard has larger slots (e.g., one per day/week) while
        the project scoreboard has hourly slots.

        For weekly limits, uses ISO week boundaries (Monday-Sunday) rather than
        arbitrary 7-day chunks from project start. This ensures weeklymax resets
        properly on Monday regardless of when the project started.

        For daily limits, uses calendar day boundaries.
        """
        # Calculate the actual datetime for this slot
        slot_datetime = self.interval_start + timedelta(seconds=index * self.slot_duration)

        if self.period == 60 * 60 * 24 * 7:  # Weekly
            # Use ISO week number for proper Monday-Sunday week boundaries
            # isocalendar() returns (year, week_number, weekday)
            iso_year, iso_week, _ = slot_datetime.isocalendar()
            start_year, start_week, _ = self.interval_start.isocalendar()

            # Calculate week offset from project start
            # Account for year boundaries
            if iso_year == start_year:
                return iso_week - start_week
            else:
                # Handle year boundary - weeks from start year + weeks in new year
                # ISO week 1 of new year follows week 52 or 53 of previous year
                weeks_in_start_year = self.interval_start.replace(month=12, day=28).isocalendar()[1]
                return (weeks_in_start_year - start_week + 1) + (iso_week - 1) + 52 * (iso_year - start_year - 1)

        elif self.period == 60 * 60 * 24:  # Daily
            # Use calendar day boundaries
            start_date = self.interval_start.date()
            slot_date = slot_datetime.date()
            return (slot_date - start_date).days

        else:
            # For other periods, use simple division from project start
            slot_seconds = index * self.slot_duration
            return int(slot_seconds / self.period)

    def inc(self, index: int, resource: Optional["Resource"] = None) -> None:
        """
        Increment the counter if index matches the interval and resource.

        Args:
            index: Project scoreboard index
            resource: Resource being booked (for resource-specific limits)
        """
        # Check resource match:
        # If self.resource is None, always increment
        # If self.resource is set, only increment if it matches
        if self.resource is not None and self.resource != resource:
            return

        sb_idx = self._idx_to_sb_idx(index)
        if 0 <= sb_idx < len(self._scoreboard):
            self._dirty = True
            self._scoreboard[sb_idx] += 1

    def dec(self, index: int, resource: Optional["Resource"] = None) -> None:
        """
        Decrement the counter if index matches the interval and resource.

        Args:
            index: Project scoreboard index
            resource: Resource being unbooked (for resource-specific limits)
        """
        if self.resource is not None and self.resource != resource:
            return

        sb_idx = self._idx_to_sb_idx(index)
        if 0 <= sb_idx < len(self._scoreboard):
            self._dirty = True
            self._scoreboard[sb_idx] -= 1

    def ok(self, index: Optional[int], upper: bool, resource: Optional["Resource"] = None) -> bool:
        """
        Check if the counter is within the limit.

        Args:
            index: Project scoreboard index (or None to check all)
            upper: True to check upper limits, False for lower limits
            resource: Resource to check (for resource-specific limits)

        Returns:
            True if within limit, False if exceeded
        """
        # If this limit's type (upper/lower) doesn't match what we're checking, return True
        if self.upper != upper:
            return True

        # For resource-specific limits:
        # - If self.resource is set and doesn't match the provided resource, return True
        # - If self.resource is None, check regardless of resource (general limit)
        if self.resource is not None and self.resource != resource:
            return True

        if index is None:
            # Check all periods
            for count in self._scoreboard:
                if self.upper:
                    if count >= self.value:
                        return False
                else:
                    if count < self.value:
                        return False
            return True
        else:
            sb_idx = self._idx_to_sb_idx(index)
            if sb_idx < 0 or sb_idx >= len(self._scoreboard):
                return True  # Outside interval, OK

            count = self._scoreboard[sb_idx]
            if self.upper:
                return count < self.value
            else:
                return count >= self.value


class Limits:
    """
    A collection of Limit objects for a task or resource.

    Supports setting multiple limits and checking/incrementing them all at once.
    """

    def __init__(self, limits: Optional["Limits"] = None) -> None:
        """
        Create a new Limits collection.

        Args:
            limits: Optional existing Limits to copy from
        """
        self._limits: list[Limit] = []
        self.project: Optional[Project] = None

        if limits is not None:
            # Deep copy from existing
            for limit in limits._limits:
                self._limits.append(limit.copy())
            self.project = limits.project

    def copy(self) -> "Limits":
        """Return a deep copy of this Limits collection."""
        return Limits(self)

    def setProject(self, project: "Project") -> None:
        """Set the project reference."""
        if self._limits:
            raise RuntimeError("Cannot change project after limits have been set!")
        self.project = project

    def reset(self) -> None:
        """Reset all limit counters."""
        for limit in self._limits:
            limit.reset()

    def setLimit(
        self,
        name: str,
        value: Union[int, float],
        interval: Optional[tuple[datetime, datetime]] = None,
        resource: Optional["Resource"] = None,
    ) -> None:
        """
        Create or update a limit.

        Args:
            name: Limit type ('dailymax', 'weeklymax', etc.)
            value: Limit value in slots (e.g., 6 for 6 hours)
            interval: Optional (start, end) tuple for the limit interval
            resource: Optional resource this limit applies to
        """
        if self.project is None:
            raise RuntimeError("Project must be set before adding limits")

        # Use project interval if not specified
        if interval is None:
            interval_start = self.project["start"]
            interval_end = self.project["end"]
        else:
            interval_start, interval_end = interval

        # Determine period and slot duration based on project settings
        slot_duration: int = self.project.attributes.get("scheduleGranularity", 3600)

        # Convert value from hours to slots
        # e.g., 3.5h with 15-min (0.25h) slots = 14 slots
        slot_duration_hours = slot_duration / 3600.0
        value_in_slots = int(value / slot_duration_hours)

        period: float
        upper: bool
        if name == "dailymax":
            period = 60 * 60 * 24  # 1 day in seconds
            upper = True
        elif name == "dailymin":
            period = 60 * 60 * 24
            upper = False
        elif name == "weeklymax":
            period = 60 * 60 * 24 * 7  # 1 week in seconds
            upper = True
        elif name == "weeklymin":
            period = 60 * 60 * 24 * 7
            upper = False
        elif name == "monthlymax":
            period = 60 * 60 * 24 * 30  # ~1 month
            upper = True
        elif name == "monthlymin":
            period = 60 * 60 * 24 * 30
            upper = False
        elif name == "maximum":
            period = (interval_end - interval_start).total_seconds()
            upper = True
        elif name == "minimum":
            period = (interval_end - interval_start).total_seconds()
            upper = False
        else:
            raise ValueError(f"Unknown limit type: {name}")

        # Remove existing limit with same name + resource combination
        self._limits = [limit for limit in self._limits if not (limit.name == name and limit.resource == resource)]

        # Add new limit (using value_in_slots which is calculated from hours)
        self._limits.append(
            Limit(name, interval_start, interval_end, period, value_in_slots, upper, resource, slot_duration)
        )

    def inc(self, index: int, resource: Optional["Resource"] = None) -> None:
        """Increment all limit counters for the given index."""
        for limit in self._limits:
            limit.inc(index, resource)

    def dec(self, index: int, resource: Optional["Resource"] = None) -> None:
        """Decrement all limit counters for the given index."""
        for limit in self._limits:
            limit.dec(index, resource)

    def ok(self, index: Optional[int] = None, upper: bool = True, resource: Optional["Resource"] = None) -> bool:
        """
        Check if all limits are satisfied.

        Args:
            index: Scoreboard index to check (or None for all)
            upper: True to check upper limits, False for lower
            resource: Resource to check for resource-specific limits

        Returns:
            True if all limits are satisfied
        """
        return all(limit.ok(index, upper, resource) for limit in self._limits)

    def __bool__(self) -> bool:
        """Return True if there are any limits."""
        return len(self._limits) > 0

    def __len__(self) -> int:
        return len(self._limits)
