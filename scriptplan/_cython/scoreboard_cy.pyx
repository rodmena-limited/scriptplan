# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
"""
Cython-optimized scoreboard operations.

These functions are hot paths called millions of times during scheduling.
"""

from cpython.datetime cimport datetime, timedelta
from libc.math cimport floor

import cython


@cython.cfunc
@cython.inline
def _total_seconds(td) -> cython.double:
    """Fast total_seconds calculation for timedelta."""
    cdef double days = <double>td.days
    cdef double seconds = <double>td.seconds
    cdef double microseconds = <double>td.microseconds
    return days * 86400.0 + seconds + microseconds / 1000000.0


cpdef int date_to_idx_fast(
    object date,
    object start_date,
    int resolution,
    int size,
    bint force_into_project
):
    """
    Fast date to scoreboard index conversion.

    Args:
        date: Target datetime
        start_date: Scoreboard start datetime
        resolution: Slot duration in seconds
        size: Scoreboard size
        force_into_project: If True, clamp to valid range

    Returns:
        Scoreboard index
    """
    cdef double diff_seconds
    cdef int idx

    # Calculate difference in seconds
    diff_seconds = _total_seconds(date - start_date)

    # Integer division for index
    idx = <int>(diff_seconds / <double>resolution)

    if force_into_project:
        if idx < 0:
            return 0
        if idx >= size:
            return size - 1

    return idx


cpdef object idx_to_date_fast(
    int idx,
    object start_date,
    int resolution,
    int size,
    bint force_into_project,
    object end_date
):
    """
    Fast scoreboard index to date conversion.

    Args:
        idx: Scoreboard index
        start_date: Scoreboard start datetime
        resolution: Slot duration in seconds
        size: Scoreboard size
        force_into_project: If True, clamp to valid range
        end_date: Scoreboard end datetime

    Returns:
        Datetime for the index
    """
    cdef int seconds

    if force_into_project:
        if idx < 0:
            return start_date
        if idx >= size:
            return end_date

    seconds = idx * resolution
    return start_date + timedelta(seconds=seconds)


cpdef list collect_intervals_fast(
    list sb,
    int start_idx,
    int end_idx,
    int s_idx,
    int e_idx,
    int min_duration_slots,
    int size,
    object start_date,
    int resolution,
    object predicate,
    object interval_class
):
    """
    Fast interval collection from scoreboard.

    Args:
        sb: Scoreboard list
        start_idx: Start index for scan
        end_idx: End index for scan
        s_idx: Original start index
        e_idx: Original end index
        min_duration_slots: Minimum interval duration in slots
        size: Scoreboard size
        start_date: Scoreboard start datetime
        resolution: Slot duration in seconds
        predicate: Callable to check slot values
        interval_class: TimeInterval class for creating results

    Returns:
        List of TimeInterval objects
    """
    cdef list intervals = []
    cdef int duration = 0
    cdef int start = 0
    cdef int idx = start_idx
    cdef int current_idx
    cdef object val
    cdef bint pred_result
    cdef int sb_len = len(sb)

    while idx <= end_idx:
        # Get value with boundary check
        if idx < sb_len:
            val = sb[idx]
        else:
            val = None

        # Check predicate
        pred_result = predicate(val) if idx < end_idx else False

        if pred_result:
            if start == 0:
                start = idx
            duration += 1
        else:
            if duration > 0:
                if duration >= min_duration_slots:
                    if start < s_idx:
                        start = s_idx
                    current_idx = idx
                    if current_idx > e_idx:
                        current_idx = e_idx

                    # Create interval
                    start_dt = start_date + timedelta(seconds=start * resolution)
                    end_dt = start_date + timedelta(seconds=current_idx * resolution)
                    intervals.append(interval_class(start_dt, end_dt))

                duration = 0
                start = 0

        idx += 1

    return intervals
