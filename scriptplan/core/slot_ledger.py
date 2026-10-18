"""How the time inside one slot is shared between tasks.

Each booking holds an interval of its slot. Forward (asap) work takes the
earliest free time at or after the moment it may begin, and backward (alap)
work takes the latest free time at or before the moment it must end. A task
that finishes mid-slot hands back the part of its own interval it did not use,
and time a task skips to honour a mid-slot start or end stays free for every
other task.

0.10.0 kept one number per slot, the seconds used. A task that finished mid-slot
gave back "the slot minus what it used" whether it had booked the whole slot or
only the part an earlier task left, so three tasks of 40, 13 and 40 minutes on
one person at 60-minute resolution all started at 09:00 (issuedb #11). 0.10.1
kept two cursors per slot, which can only describe free time between them, so
the time a task skipped at a mid-slot bound was lost to everyone (issuedb #17).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "SlotBooking",
    "finish_offset",
    "free_seconds",
    "release",
    "reserve",
]


@dataclass
class SlotBooking:
    """One stretch of one resource's slot, booked for one task.

    ``offset`` is measured from the edge the work grows from: the start of the
    slot for forward work, its end for backward work, so the booking covers
    ``[offset, offset + seconds)`` counted from that edge. ``span`` is the
    ``[start, end, task]`` entry, in seconds from the start of the slot, that
    the resource keeps for it.
    """

    resource: Any
    slot: int
    task: Any
    forward: bool
    offset: float
    seconds: float
    efficiency: float
    previous: Any
    span: list[Any] = field(default_factory=list)

    @property
    def effort(self) -> float:
        """Effort this booking earns, in hours."""
        return self.seconds / 3600.0 * self.efficiency


def free_seconds(rs: Any, idx: int) -> float:
    """Seconds of the slot that no booking holds."""
    # Asked for every candidate slot of every task, so it is one lookup.
    free: float = rs.slotLength - rs.slotSecondsUsed.get(idx, 0.0)
    return free if free > 0.0 else 0.0


def _gaps(spans: list[list[Any]], lo: float, hi: float) -> list[tuple[float, float]]:
    """Free stretches of ``[lo, hi)`` around the occupied ``spans``, earliest first."""
    gaps, at = [], lo
    for start, end, _ in spans:
        if end <= at:
            continue
        if start >= hi:
            break
        if start > at:
            gaps.append((at, start))
        at = max(at, end)
    if at < hi:
        gaps.append((at, hi))
    return gaps


def reserve(
    rs: Any,
    idx: int,
    task: Any,
    *,
    forward: bool = True,
    force: bool = False,
    not_before: float = 0.0,
) -> list[SlotBooking]:
    """Book as much of the slot as the slot and the limits allow.

    ``not_before`` keeps the booking that many seconds away from the edge it
    grows from: forward work out of the start of the slot, backward work out
    of its end. That is how a task that may not start before a moment, or may
    not end after one, is placed inside a slot. The time it skips is left
    free. Each free stretch taken is one booking.
    """
    if not force and not rs.available(idx):
        return []

    if rs.scoreboard is None:
        rs.initScoreboard()

    budget = free_seconds(rs, idx) if force else rs.limitAllowance(idx)
    if budget <= 0:
        return []

    length = rs.slotLength
    spans = rs.slotIntervals.setdefault(idx, [])
    gaps = _gaps(spans, not_before, length) if forward else _gaps(spans, 0.0, length - not_before)[::-1]
    efficiency = rs.property.get("efficiency", rs.scenarioIdx) or 1.0
    previous = rs.scoreboard[idx]

    bookings = []
    for start, end in gaps:
        take = min(budget, end - start)
        if take <= 0:
            break
        span = [start, start + take, task] if forward else [end - take, end, task]
        offset = span[0] if forward else length - span[1]
        bookings.append(SlotBooking(rs, idx, task, forward, offset, take, efficiency, previous, span))
        spans.append(span)
        rs.scoreboard[idx] = task
        budget -= take
    if not bookings:
        if not spans:
            del rs.slotIntervals[idx]
        return []
    spans.sort(key=lambda s: s[0])

    duties = rs.property.get("duties", rs.scenarioIdx) or []
    if task not in duties:
        duties.append(task)
    booked = sum(b.seconds for b in bookings)
    rs._effort += booked / 3600.0 * efficiency
    rs.slotSecondsUsed[idx] = rs.slotSecondsUsed.get(idx, 0.0) + booked
    _add_usage(rs, idx, task, booked)
    _count(bookings[0], booked)
    _track_range(rs, idx, task)
    return bookings


def release(booking: SlotBooking, keep: float) -> None:
    """Give back the part of ``booking`` beyond its first ``keep`` seconds.

    The part kept is the one nearest the edge the work grows from, so a task
    that finishes early keeps the time it worked and frees what follows. Only
    the booking's own interval shrinks, so no other booking can be affected.
    """
    keep = max(0.0, min(keep, booking.seconds))
    unused = booking.seconds - keep
    if unused <= 0:
        return
    rs, idx, span = booking.resource, booking.slot, booking.span
    if booking.forward:
        span[1] = span[0] + keep
    else:
        span[0] = span[1] - keep

    rs.slotSecondsUsed[idx] = rs.slotSecondsUsed.get(idx, 0.0) - unused
    _add_usage(rs, idx, booking.task, -unused)
    rs._effort -= unused / 3600.0 * booking.efficiency
    _count(booking, -unused)
    booking.seconds = keep
    if keep <= 0:
        _withdraw(booking)


def finish_offset(bookings: list[SlotBooking], needed: float) -> float:
    """Seconds from the slot edge at which ``bookings`` complete ``needed`` hours.

    Every resource works through its own bookings from the edge the work grows
    from, so the work done by a moment T is the sum over bookings of efficiency
    x the part of the booking before T. That is non-decreasing in T, and the
    answer is where it first reaches ``needed``: the earliest moment the work
    is done.
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


def _add_usage(rs: Any, idx: int, task: Any, seconds: float) -> None:
    """Move ``task``'s share of the slot in ``slotTaskUsage`` by ``seconds``."""
    usage = rs.slotTaskUsage.setdefault(idx, [])
    for i, (holder, held) in enumerate(usage):
        if holder is task:
            total = held + seconds
            if total > 1e-9:
                usage[i] = (task, total)
            else:
                del usage[i]
            break
    else:
        if seconds > 0:
            usage.append((task, seconds))
    if not usage:
        del rs.slotTaskUsage[idx]


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
    spans = rs.slotIntervals.get(idx, [])
    spans[:] = [s for s in spans if s is not booking.span]
    if not spans:
        rs.slotIntervals.pop(idx, None)
    still_here = any(s[2] is task for s in spans)
    if not still_here and rs.scoreboard is not None and rs.scoreboard[idx] is task:
        rs.scoreboard[idx] = booking.previous
    if not any(t is task for usage in rs.slotTaskUsage.values() for t, _ in usage):
        duties = rs.property.get("duties", rs.scenarioIdx) or []
        if task in duties:
            duties.remove(task)
