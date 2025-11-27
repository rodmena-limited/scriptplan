"""
WorkingHours class for managing per-resource working hour schedules.

This class handles irregular working hours like "08:15 - 11:45, 13:15 - 16:30"
for specific days of the week.
"""

from datetime import datetime, time, timedelta


class WorkingHours:
    """
    Manages working hours for a resource.

    Working hours are defined as time intervals for each day of the week.
    For example:
        Mon, Wed, Fri: 08:15 - 11:45, 13:15 - 16:30
        Tue, Thu: 09:00 - 10:30, 14:45 - 16:00
    """

    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    DAY_MAP = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }

    def __init__(self, project):
        """
        Initialize working hours.

        Args:
            project: Project reference for time conversion
        """
        self.project = project
        # Dict mapping weekday (0-6) to list of (start_time, end_time) tuples
        # Times are stored as (hour, minute) tuples
        self._hours = {}
        # Start with empty hours - will be populated by set_hours()
        # If no hours are set, onShift will fall back to project default
        self._custom_hours_set = False

    def set_hours(self, days, ranges):
        """
        Set working hours for specific days.

        Args:
            days: List of day names like ['mon', 'wed', 'fri']
            ranges: List of (start_time, end_time) tuples like [('08:15', '11:45')]
        """
        self._custom_hours_set = True

        # Convert day names to weekday numbers
        day_nums = []
        for day in days:
            day_lower = day.lower()
            if day_lower in self.DAY_MAP:
                day_nums.append(self.DAY_MAP[day_lower])

        # Handle day ranges like "mon - fri"
        if len(day_nums) == 0:
            return

        # Parse time ranges to (hour, minute) tuples
        time_intervals = []
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

    def _parse_time(self, time_str):
        """Parse a time string like '08:15' to (hour, minute) tuple."""
        parts = str(time_str).split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return (hour, minute)

    def onShift(self, slot_idx):
        """
        Check if a slot index is within working hours.

        Args:
            slot_idx: Scoreboard slot index

        Returns:
            True if the slot is within working hours
        """
        # If no custom hours set, fall back to project default
        if not self._custom_hours_set:
            return self.project.isWorkingTime(slot_idx)

        # Get datetime for this slot
        dt = self.project.idxToDate(slot_idx)
        if dt is None:
            return False

        weekday = dt.weekday()

        # Check if this day has working hours defined
        if weekday not in self._hours or not self._hours[weekday]:
            # No working hours defined for this day = not working
            return False

        slot_time = (dt.hour, dt.minute)

        # Check if slot falls within any working interval
        for (start_h, start_m), (end_h, end_m) in self._hours[weekday]:
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            slot_minutes = slot_time[0] * 60 + slot_time[1]

            # Slot is within interval if: start <= slot < end
            if start_minutes <= slot_minutes < end_minutes:
                return True

        return False

    def get_daily_hours(self, weekday):
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
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            total_minutes += (end_minutes - start_minutes)

        return total_minutes / 60.0

    def clear_day(self, weekday):
        """Clear working hours for a specific day."""
        if weekday in self._hours:
            self._hours[weekday] = []

    def clear_all(self):
        """Clear all working hours."""
        self._hours = {}
