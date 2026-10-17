"""How the time inside one slot is shared between tasks.

A slot is filled from both ends. Forward (asap) work takes time from the start
of the slot and backward (alap) work from its end, so whatever is still free is
the single gap between the two. Every booking therefore knows where it sits,
which is what lets a task that finishes mid-slot hand back exactly the time it
did not use, and lets the next task start where the last one stopped.

The engine used to keep one number per slot, the seconds used. A task that
finished mid-slot gave back "the slot minus what it used" whether it had booked
the whole slot or only the part an earlier task left, and every later task was
placed at the start of the slot. Three tasks of 40, 13 and 40 minutes on one
person at 60-minute resolution all started at 09:00, and the slot held 5580
seconds of work (issuedb #11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "SlotBooking",
    "finish_offset",
    "free_seconds",
    "release",
    "reserve",
    "slot_cursor",
]


@dataclass
class SlotBooking:
    """One resource's booking in one slot, for one task.

    ``offset`` is measured from the edge the work grows from: the start of the
    slot for forward work, its end for backward work. The booking occupies
    ``[offset, offset + seconds)`` from that edge.
    """

    resource: Any
    slot: int
    task: Any
    forward: bool
    offset: float
    seconds: float
    efficiency: float
    previous: Any

    @property
    def effort(self) -> float:
        """Effort this booking earns, in hours."""
        return self.seconds / 3600.0 * self.efficiency


def slot_cursor(rs: Any, idx: int, forward: bool) -> float:
    """Seconds already taken from the start (forward) or end (backward) of a slot."""
    cursors = rs.slotFrontUsed if forward else rs.slotBackUsed
    return float(cursors.get(idx, 0.0))


def free_seconds(rs: Any, idx: int) -> float:
    """Seconds of the slot that no booking holds."""
    # Asked for every candidate slot of every task: kept to two lookups.
    used: float = rs.slotFrontUsed.get(idx, 0.0) + rs.slotBackUsed.get(idx, 0.0)
    free: float = rs.slotLength - used
    return free if free > 0.0 else 0.0


def _set_cursor(rs: Any, idx: int, forward: bool, value: float) -> None:
    cursors = rs.slotFrontUsed if forward else rs.slotBackUsed
    cursors[idx] = value
    rs.slotSecondsUsed[idx] = rs.slotFrontUsed.get(idx, 0.0) + rs.slotBackUsed.get(idx, 0.0)


def reserve(
    rs: Any,
    idx: int,
    task: Any,
    *,
    forward: bool = True,
    force: bool = False,
    not_before: float = 0.0,
) -> SlotBooking | None:
    """Book as much of the slot as the slot and the limits allow.

    ``not_before`` keeps the booking that many seconds away from the edge it
    grows from: forward work out of the start of the slot, backward work out
    of its end. That is how a task that may not start before a moment, or may
    not end after one, is placed inside a slot. The time passed over is not
    booked to anyone.
    """
    if not force and not rs.available(idx):
        return None

    if rs.scoreboard is None:
        rs.initScoreboard()

    granted = free_seconds(rs, idx) if force else rs.limitAllowance(idx)
    offset = slot_cursor(rs, idx, forward)
    if not_before > offset:
        room = rs.slotLength - slot_cursor(rs, idx, not forward) - not_before
        granted = min(granted, room)
        offset = not_before
    if granted <= 0:
        return None

    duties = rs.property.get("duties", rs.scenarioIdx) or []
    if task not in duties:
        duties.append(task)

    efficiency = rs.property.get("efficiency", rs.scenarioIdx) or 1.0
    booking = SlotBooking(rs, idx, task, forward, offset, granted, efficiency, rs.scoreboard[idx])

    rs._effort += booking.effort
    rs.slotTaskUsage.setdefault(idx, []).append((task, granted))
    _set_cursor(rs, idx, forward, offset + granted)
    rs.scoreboard[idx] = task
    _count(booking, granted)
    _track_range(rs, idx, task)
    return booking


def release(booking: SlotBooking, keep: float) -> None:
    """Give back the part of ``booking`` beyond its first ``keep`` seconds.

    The released time is the end of the booking furthest from its edge, which
    is the time no later booking can have taken: release a task's bookings in
    the reverse of the order they were made.
    """
    keep = max(0.0, min(keep, booking.seconds))
    unused = booking.seconds - keep
    if unused <= 0:
        return
    rs, idx = booking.resource, booking.slot

    far_edge = booking.offset + booking.seconds
    cursor = slot_cursor(rs, idx, booking.forward)
    if abs(cursor - far_edge) > 1e-6:
        # Releasing time another booking sits on would hand it out twice.
        raise RuntimeError(
            f"slot {idx} of resource {rs.property.id}: cannot release {unused:.0f}s of "
            f"{booking.task.id}'s booking ending at {far_edge:.0f}s; the slot is filled to {cursor:.0f}s"
        )
    _set_cursor(rs, idx, booking.forward, far_edge - unused)

    usage = rs.slotTaskUsage.get(idx, [])
    for i in range(len(usage) - 1, -1, -1):
        if usage[i][0] is booking.task:
            if keep > 0:
                usage[i] = (booking.task, keep)
            else:
                del usage[i]
            break

    rs._effort -= unused / 3600.0 * booking.efficiency
    _count(booking, -unused)
    booking.seconds = keep
    if keep <= 0:
        _withdraw(booking)


def finish_offset(bookings: list[SlotBooking], needed: float) -> float:
    """Seconds from the slot edge at which ``bookings`` complete ``needed`` hours.

    Every resource works from the start of its own booking, so the work done by
    a moment T is the sum over bookings of efficiency x the part of the booking
    before T. That is non-decreasing in T, and the answer is where it first
    reaches ``needed``: the earliest moment the work is done.
    """
    if not bookings:
        return 0.0
    if needed <= 0:
        return min(b.offset for b in bookings)
    points = sorted({b.offset for b in bookings} | {b.offset + b.seconds for b in bookings})
    done = 0.0
    for lo, hi in zip(points, points[1:]):
        rate = sum(b.efficiency / 3600.0 for b in bookings if b.offset <= lo and b.offset + b.seconds >= hi)
        if rate <= 0:
            continue
        if done + rate * (hi - lo) >= needed:
            return lo + (needed - done) / rate
        done += rate * (hi - lo)
    return points[-1]


def _count(booking: SlotBooking, seconds: float) -> None:
    """Move every limit counter that sees this booking by ``seconds``."""
    rs, idx = booking.resource, booking.slot
    rid, scenario_idx = rs.property.id, rs.scenarioIdx
    holder = rs.property
    while holder is not None:
        limits = holder.get("limits", scenario_idx)
        if limits is not None and hasattr(limits, "inc"):
            _move(limits, idx, rid, seconds)
        holder = holder.parent
    if hasattr(booking.task, "data") and booking.task.data:
        holder = booking.task
        while holder is not None:
            limits = holder.get("limits", scenario_idx)
            if limits:
                _move(limits, idx, rid, seconds)
            holder = holder.parent


def _move(limits: Any, idx: int, rid: Any, seconds: float) -> None:
    if seconds >= 0:
        limits.inc(idx, rid, seconds=seconds)
    else:
        limits.dec(idx, rid, seconds=-seconds)


def _track_range(rs: Any, idx: int, task: Any) -> None:
    if rs.firstBookedSlot is None or rs.firstBookedSlot > idx:
        rs.firstBookedSlot = idx
    if task not in rs.firstBookedSlots or rs.firstBookedSlots[task] > idx:
        rs.firstBookedSlots[task] = idx
    if rs.lastBookedSlot is None or rs.lastBookedSlot < idx:
        rs.lastBookedSlot = idx
    if task not in rs.lastBookedSlots or rs.lastBookedSlots[task] < idx:
        rs.lastBookedSlots[task] = idx


def _withdraw(booking: SlotBooking) -> None:
    """Undo a booking the task turned out not to need at all."""
    rs, idx, task = booking.resource, booking.slot, booking.task
    if rs.scoreboard is not None and rs.scoreboard[idx] is task:
        rs.scoreboard[idx] = booking.previous
    if rs.slotTaskUsage.get(idx) == []:
        del rs.slotTaskUsage[idx]
    if not any(t is task for usage in rs.slotTaskUsage.values() for t, _ in usage):
        duties = rs.property.get("duties", rs.scenarioIdx) or []
        if task in duties:
            duties.remove(task)
