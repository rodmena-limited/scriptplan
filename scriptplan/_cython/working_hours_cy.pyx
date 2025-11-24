# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
"""
Cython-optimized working hours checking.

These functions handle time slot validation against working hour schedules.
"""

from cpython.datetime cimport datetime, timedelta

import cython


cpdef bint check_working_hours_fast(
    int slot_minutes,
    int weekday,
    dict hours_dict,
    bint check_cross_midnight
):
    """
    Fast check if slot is within working hours.

    Args:
        slot_minutes: Minutes from midnight (0-1439)
        weekday: Day of week (0=Monday, 6=Sunday)
        hours_dict: Dict mapping weekday to list of ((start_h, start_m), (end_h, end_m))
        check_cross_midnight: Whether to check previous day for cross-midnight shifts

    Returns:
        True if within working hours
    """
    cdef list intervals
    cdef tuple interval
    cdef tuple start_tuple, end_tuple
    cdef int start_h, start_m, end_h, end_m
    cdef int start_minutes, end_minutes
    cdef int prev_weekday
    cdef int i

    # Check if this day has working hours
    if weekday not in hours_dict:
        if not check_cross_midnight:
            return False
        # Fall through to cross-midnight check
    else:
        intervals = hours_dict[weekday]
        if not intervals:
            if not check_cross_midnight:
                return False
        else:
            # Check each interval
            for i in range(len(intervals)):
                interval = intervals[i]
                start_tuple = interval[0]
                end_tuple = interval[1]

                start_h = start_tuple[0]
                start_m = start_tuple[1]
                end_h = end_tuple[0]
                end_m = end_tuple[1]

                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                # Check for cross-midnight shift
                if end_minutes <= start_minutes:
                    # Working time: start_minutes <= slot < 1440 OR 0 <= slot < end_minutes
                    if slot_minutes >= start_minutes or slot_minutes < end_minutes:
                        return True
                else:
                    # Normal interval
                    if start_minutes <= slot_minutes < end_minutes:
                        return True

    # Check cross-midnight from previous day
    if check_cross_midnight:
        prev_weekday = (weekday - 1) % 7
        if prev_weekday in hours_dict:
            intervals = hours_dict[prev_weekday]
            for i in range(len(intervals)):
                interval = intervals[i]
                start_tuple = interval[0]
                end_tuple = interval[1]

                start_h = start_tuple[0]
                start_m = start_tuple[1]
                end_h = end_tuple[0]
                end_m = end_tuple[1]

                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                # If previous day had cross-midnight shift
                if end_minutes <= start_minutes and slot_minutes < end_minutes:
                    return True

    return False


cpdef int get_slot_minutes(int hour, int minute):
    """Convert hour and minute to minutes from midnight."""
    return hour * 60 + minute


cpdef tuple extract_time_components(object dt):
    """
    Extract hour, minute, and weekday from datetime.

    Returns:
        (hour, minute, weekday) tuple
    """
    return (dt.hour, dt.minute, dt.weekday())


cpdef float calculate_daily_hours(list intervals):
    """
    Calculate total working hours from interval list.

    Args:
        intervals: List of ((start_h, start_m), (end_h, end_m)) tuples

    Returns:
        Total hours as float
    """
    cdef int total_minutes = 0
    cdef tuple interval
    cdef tuple start_tuple, end_tuple
    cdef int start_h, start_m, end_h, end_m
    cdef int start_minutes, end_minutes
    cdef int i

    for i in range(len(intervals)):
        interval = intervals[i]
        start_tuple = interval[0]
        end_tuple = interval[1]

        start_h = start_tuple[0]
        start_m = start_tuple[1]
        end_h = end_tuple[0]
        end_m = end_tuple[1]

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        total_minutes += (end_minutes - start_minutes)

    return <float>total_minutes / 60.0
