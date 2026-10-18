"""Placing work that is measured in time rather than in effort.

A milestone is a moment, `duration` is calendar time and `length` is working
time. None of them depends on how much a resource gets done, so each is placed
by counting time from the moment it may begin, or, scheduled backwards, from
the moment it must end, to the second, even when that moment falls inside a
slot.

Before 0.10.2 these were counted in whole slots from the top of a slot. A
duration task after a predecessor that ended at 09:40 was reported from 09:00,
and an alap milestone before a task starting at 16:00 sat at 15:00
(issuedb #13, #14).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

__all__ = ["entry_moment", "finish_span", "slot_share"]


def entry_moment(scenario: Any, slot_idx: int, forward: bool) -> datetime:
    """Where placement begins in ``slot_idx``: the start of forward work, the end of backward work.

    That is the slot's leading edge, moved in by the entry offset when the
    moment the task may begin (or must end) fell inside this slot.
    """
    project = scenario.project
    offset = scenario.slotStartOffset if slot_idx == scenario.slotStartOffsetSlot else 0.0
    if forward:
        moment: datetime = project.idxToDate(slot_idx) + timedelta(seconds=round(offset))
    else:
        moment = project.idxToDate(slot_idx + 1) - timedelta(seconds=round(offset))
    return moment


def slot_share(scenario: Any) -> float:
    """Seconds of the current slot that count towards a duration or length.

    All of it, except in the entry slot, where the part on the wrong side of
    the entry moment does not belong to the task.
    """
    seconds = float(scenario._slotSeconds())
    if scenario.currentSlotIdx == scenario.slotStartOffsetSlot:
        seconds -= scenario.slotStartOffset
    return seconds


def finish_span(scenario: Any, overshoot: float, forward: bool) -> datetime:
    """Close the span inside the current slot, ``overshoot`` seconds before its far edge.

    The count went ``overshoot`` seconds past what the task needed, so the
    task ends that much before the end of the slot (forward), or starts that
    much after its start (backward). Its resources keep only the part of
    their bookings in this slot that falls inside the task's window.
    """
    slot_seconds = float(scenario._slotSeconds())
    reach = slot_seconds - overshoot
    for booking in reversed(getattr(scenario, "slotBookings", None) or []):
        booking.resource.release(booking, reach - booking.offset)
    slot_start = scenario.project.idxToDate(scenario.currentSlotIdx)
    seconds = round(reach) if forward else round(overshoot)
    moment: datetime = slot_start + timedelta(seconds=seconds)
    return moment
