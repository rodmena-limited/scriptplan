# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
"""
Cython-optimized time utility functions.

These are core date/index conversion functions used throughout scheduling.
"""

from cpython.datetime cimport datetime, timedelta

import cython


cpdef int project_date_to_idx(
    object date,
    object start,
    int granularity
):
    """
    Fast project date to index conversion.

    Args:
        date: Target datetime
        start: Project start datetime
        granularity: Schedule granularity in seconds

    Returns:
        Slot index
    """
    cdef double diff_seconds
    cdef int idx

    if start is None:
        return 0

    # Calculate difference
    try:
        diff_seconds = (date - start).total_seconds()
    except AttributeError:
        diff_seconds = <double>(date - start)

    idx = <int>(diff_seconds / <double>granularity)
    return idx


cpdef object project_idx_to_date(
    int idx,
    object start,
    int granularity
):
    """
    Fast project index to date conversion.

    Args:
        idx: Slot index
        start: Project start datetime
        granularity: Schedule granularity in seconds

    Returns:
        Datetime for the index, or None if start is None
    """
    cdef int seconds

    if start is None:
        return None

    seconds = idx * granularity
    return start + timedelta(seconds=seconds)


cpdef int scoreboard_size(
    object start,
    object end,
    int granularity
):
    """
    Calculate scoreboard size.

    Args:
        start: Project start datetime
        end: Project end datetime
        granularity: Schedule granularity in seconds

    Returns:
        Number of slots
    """
    cdef double diff_seconds
    cdef int size

    if start is None or end is None:
        return 0

    try:
        diff_seconds = (end - start).total_seconds()
    except AttributeError:
        diff_seconds = <double>(end - start)

    size = <int>(diff_seconds / <double>granularity) + 1
    return size


cpdef bint is_working_time_fast(
    int slot_idx,
    object start,
    int granularity,
    int daily_start_hour,
    int daily_end_hour
):
    """
    Fast working time check for default project hours.

    Args:
        slot_idx: Slot index to check
        start: Project start datetime
        granularity: Schedule granularity in seconds
        daily_start_hour: Daily work start hour (e.g., 9)
        daily_end_hour: Daily work end hour (e.g., 17)

    Returns:
        True if slot is within working hours
    """
    cdef int seconds
    cdef object dt
    cdef int hour
    cdef int weekday

    if start is None:
        return False

    # Get datetime for slot
    seconds = slot_idx * granularity
    dt = start + timedelta(seconds=seconds)

    # Get weekday (0=Monday, 6=Sunday)
    weekday = dt.weekday()

    # Weekend check
    if weekday >= 5:  # Saturday or Sunday
        return False

    # Hour check
    hour = dt.hour
    if hour < daily_start_hour or hour >= daily_end_hour:
        return False

    return True
