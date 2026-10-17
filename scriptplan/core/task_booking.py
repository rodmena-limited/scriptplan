"""Committing a task's work to resources, slot by slot.

`effort` is person-time: every allocated resource that works in a slot
contributes its own time to the task. A mandatory allocation that cannot be
filled skips the slot entirely rather than booking the others, which is how a
task that needs two people together is expressed.

Limits narrow how much of a slot may be used, down to a part of one, so a cap
smaller than the slot size is honoured exactly rather than rounded away.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from scriptplan.core.slot_ledger import finish_offset

__all__ = [
    "all_limits",
    "book_resource",
    "book_resources",
    "first_bookable",
    "inc_limits",
    "limits_ok",
    "precise_end_time",
    "precise_end_time_and_release",
    "record_effort_start",
]


def book_resources(scenario: Any) -> None:
    """Book what can be booked in the current slot.

    `effort` is person-time: every allocated resource that works in this
    slot contributes its own time to it, so a task of 16 hours of effort
    with two resources available takes one eight-hour day. A mandatory
    allocation must be bookable or the slot is skipped entirely, which is
    how a task that needs two people together is expressed.
    """
    plan = scenario.allocationPlan()
    if not plan:
        return

    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    effort = scenario.property.get("effort", scenario.scenarioIdx) or 0
    # Where in this slot each booking sits, for settling a mid-slot finish.
    scenario.slotBookings = []

    # Every mandatory allocation must be satisfiable before anything is
    # booked, so a slot is never half-committed to a task that cannot use it.
    chosen: list[tuple[Any, Any]] = []
    for allocation in plan:
        resource = first_bookable(scenario, allocation, slot_idx)
        if resource is None:
            if allocation.mandatory:
                return
            continue
        chosen.append((allocation, resource))

    if not chosen:
        return

    booked_any = False
    gained_total = 0.0
    remaining = (effort - scenario.doneEffort) if effort > 0 else None

    for allocation, resource in chosen:
        if remaining is not None and remaining <= 0:
            break
        gained = book_resource(scenario, resource)
        if gained <= 0:
            if allocation.mandatory:
                # A mandatory resource turned out not to be bookable after
                # all; stop rather than record partial progress, and give
                # back what was booked so no one's time is spent on nothing.
                for booking in reversed(scenario.slotBookings):
                    booking.resource.release(booking, 0.0)
                scenario.slotBookings = []
                return
            continue
        booked_any = True
        gained_total += gained
        if remaining is not None:
            remaining -= gained
        if allocation.persistent:
            allocation.locked = resource
        scenario._lastBookedResource = resource
        scenario._lastBookedSlot = scenario.currentSlotIdx

    if booked_any:
        if effort > 0 and scenario.doneEffort == 0:
            record_effort_start(scenario)
        scenario.doneEffort += gained_total


def first_bookable(scenario: Any, allocation: Any, slot_idx: int) -> Any | None:
    """The first candidate for this allocation that is free in this slot."""
    for resource in allocation.candidates():
        resource_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
        if resource_scenario is None:
            continue
        if resource_scenario.scoreboard is None:
            resource_scenario.prepareScheduling()
        if not resource_scenario.available(slot_idx):
            continue
        if not limits_ok(scenario, slot_idx, resource):
            continue
        return resource
    return None


def record_effort_start(scenario: Any) -> None:
    """Record where the task's work begins, to the second.

    Work begins where the first bookings sit, which is after whatever earlier
    tasks or a predecessor left of the slot. Forward work starts at the
    earliest of them. Backward work is placed from its end, so its first
    bookings are its last work, and they set when it ends.
    """
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    slot_start = scenario.project.idxToDate(slot_idx)
    if slot_start is None:
        return
    bookings = getattr(scenario, "slotBookings", None) or []
    # Reported to the second, rounded the same way as the end of whatever
    # task's work this follows, so the two dates meet exactly.
    offset = round(min((b.offset for b in bookings), default=0.0))
    if scenario.property.get("forward", scenario.scenarioIdx):
        scenario.property[("start", scenario.scenarioIdx)] = slot_start + timedelta(seconds=offset)
    else:
        slot_seconds = scenario.project.attributes.get("scheduleGranularity", 3600)
        scenario.workEnd = slot_start + timedelta(seconds=slot_seconds - offset)
    scenario.firstWorkSlot = slot_idx


def book_resource(scenario: Any, resource: Any) -> float:
    """
    Try to book a single resource for the current slot.

    Args:
        resource: The resource to book

    Returns:
        Effort gained from this booking (hours), or 0 if booking failed.
        This accounts for partial slot availability.
    """
    # Get the resource's scenario data
    res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
    if res_scenario is None:
        return 0.0

    # Initialize resource scoreboard if needed
    if res_scenario.scoreboard is None:
        res_scenario.prepareScheduling()

    # Check task limits for this resource (including parent limits); the
    # resource's own availability is checked by reserve()
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    if not limits_ok(scenario, slot_idx, resource):
        return 0.0

    # A predecessor that ends mid-slot keeps this task out of the first part
    # of that one slot. Later slots are free from their start.
    not_before = 0.0
    if slot_idx == getattr(scenario, "slotStartOffsetSlot", None):
        not_before = scenario.slotStartOffset

    forward = bool(scenario.property.get("forward", scenario.scenarioIdx))
    booking = res_scenario.reserve(slot_idx, scenario.property, forward=forward, not_before=not_before)
    if booking is None:
        return 0.0
    scenario.slotBookings.append(booking)
    effort_gained: float = booking.effort
    return effort_gained


def all_limits(scenario: Any) -> list[Any]:
    """
    Collect limits from this task and all parent tasks.
    Returns a list of Limits objects.
    """
    all_limits = []
    task: Any | None = scenario.property
    while task is not None:
        limits = task.get("limits", scenario.scenarioIdx)
        if limits:
            all_limits.append(limits)
        task = task.parent
    return all_limits


def limits_ok(scenario: Any, sbIdx: int, resource: Any | None = None) -> bool:
    """
    Check if all task limits (including parent limits) are satisfied.

    Args:
        sbIdx: Scoreboard index to check
        resource: Resource to check (for resource-specific limits)

    Returns:
        True if all limits are satisfied
    """
    for limits in all_limits(scenario):
        if not limits.ok(sbIdx, upper=True, resource=resource.id if resource else None):
            return False
    return True


def inc_limits(scenario: Any, sbIdx: int, resource: Any | None = None, seconds: float | None = None) -> None:
    """
    Increment all task limit counters (including parent limits).

    Args:
        sbIdx: Scoreboard index
        resource: Resource being booked (for resource-specific limits)
        seconds: Time actually booked, so a partial slot consumes a
            partial allowance rather than a whole one.
    """
    for limits in all_limits(scenario):
        limits.inc(sbIdx, resource=resource.id if resource else None, seconds=seconds)


def precise_end_time_and_release(
    scenario: Any, required_effort: float, effort_before_slot: float, forward: bool
) -> tuple[datetime, float]:
    """
    Calculate the precise end time within the final slot and release unused time.

    The task's work in its final slot sits where its bookings there sit: after
    whatever earlier tasks left of the slot, on each resource. It finishes at
    the earliest moment that work covers what was still needed, and each
    resource gets back only the part of its own booking past that moment.

    Args:
        required_effort: Total effort required for the task (hours)
        effort_before_slot: Effort accumulated before the current slot (hours)
        forward: True for forward scheduling, False for backward

    Returns:
        tuple: (the end for forward work or the start for backward work,
                seconds from the slot edge the work grew from)
    """
    slot_seconds = scenario.project.attributes.get("scheduleGranularity", 3600)
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    slot_start = scenario.project.idxToDate(slot_idx)
    if slot_start is None:
        slot_start = scenario.project["start"]

    # The ledger keeps the exact moment, so rounding never accumulates along
    # a chain of tasks; only the reported date is rounded to the second.
    bookings = list(getattr(scenario, "slotBookings", None) or [])
    reach_exact = finish_offset(bookings, required_effort - effort_before_slot)
    for booking in reversed(bookings):
        booking.resource.release(booking, reach_exact - booking.offset)
    reach = round(reach_exact)

    if getattr(scenario, "firstWorkSlot", None) == slot_idx:
        # The task started in this slot too, so its start may have been set
        # by a booking it turned out not to need.
        working = [b for b in bookings if b.seconds > 0]
        if working:
            scenario.slotBookings = working
            record_effort_start(scenario)

    seconds_from_start = reach if forward else slot_seconds - reach
    return slot_start + timedelta(seconds=seconds_from_start), float(reach)


def precise_end_time(scenario: Any, required_effort: float, effort_before_slot: float, forward: bool) -> datetime:
    """
    Calculate the precise end time within the final slot based on fractional effort.
    (Legacy method - calls the new implementation)
    """
    end_time, _ = precise_end_time_and_release(scenario, required_effort, effort_before_slot, forward)
    return end_time
