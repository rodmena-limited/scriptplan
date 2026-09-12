"""Committing a task's work to resources, slot by slot.

 is person-time: every allocated resource that works in a slot
contributes its own time to the task. A mandatory allocation that cannot be
filled skips the slot entirely rather than booking the others, which is how a
task that needs two people together is expressed.

Limits narrow how much of a slot may be used, down to a part of one, so a cap
smaller than the slot size is honoured exactly rather than rounded away.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

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
                # all; stop rather than record partial progress.
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
    """Set the task's start at its first booking, honouring a mid-slot start."""

    forward = scenario.property.get("forward", scenario.scenarioIdx)
    if not forward:
        return
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    start_date = scenario.project.idxToDate(slot_idx)
    if start_date is not None and getattr(scenario, "slotStartOffset", 0) > 0:
        start_date = start_date + timedelta(seconds=scenario.slotStartOffset)
    scenario.property[("start", scenario.scenarioIdx)] = start_date


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

    # For the FIRST slot of this task, apply start offset from dependency
    # This marks the portion already used by predecessor as unavailable
    if hasattr(scenario, "slotStartOffset") and scenario.slotStartOffset > 0 and scenario.doneEffort == 0:
        # Mark the offset portion as used (by predecessor task)
        current_used = res_scenario.slotSecondsUsed.get(scenario.currentSlotIdx, 0.0)
        if current_used < scenario.slotStartOffset:
            res_scenario.slotSecondsUsed[scenario.currentSlotIdx] = scenario.slotStartOffset

    # Check if resource is available
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    if not res_scenario.available(slot_idx):
        return 0.0

    # Check task limits for this resource (including parent limits)
    if not limits_ok(scenario, slot_idx, resource):
        return 0.0

    # Book the resource - returns effort gained (accounts for partial slots)
    result_float: float = res_scenario.book(slot_idx, scenario.property)
    return result_float


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

    When a task completes within a slot, we need to determine exactly when
    within that slot the required effort was reached, rather than rounding
    to slot boundaries. The unused portion of the slot is released back to
    the resource for other tasks to use.

    Args:
        required_effort: Total effort required for the task (hours)
        effort_before_slot: Effort accumulated before the current slot (hours)
        forward: True for forward scheduling, False for backward

    Returns:
        tuple: (precise_end_datetime, seconds_used_in_slot)
    """

    # Get slot parameters
    slot_duration_seconds = scenario.project.attributes.get("scheduleGranularity", 3600)
    slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    slot_start = scenario.project.idxToDate(slot_idx)

    # Get the resource and its efficiency for this slot
    resource = getattr(scenario, "_lastBookedResource", None)
    efficiency = 1.0
    if resource:
        eff = resource.get("efficiency", scenario.scenarioIdx)
        if eff is not None:
            efficiency = eff
    else:
        # Fallback to allocations
        allocations = scenario.property.get("allocate", scenario.scenarioIdx) or []
        for alloc in allocations:
            if isinstance(alloc, str):
                for res in scenario.project.resources:
                    if res.id == alloc:
                        resource = res
                        break
            else:
                resource = alloc
            if resource:
                eff = resource.get("efficiency", scenario.scenarioIdx)
                if eff is not None:
                    efficiency = eff
                break

    # Calculate effort gained per second in this slot
    slot_duration_hours = slot_duration_seconds / 3600.0
    effort_per_slot = slot_duration_hours * efficiency
    effort_per_second = effort_per_slot / slot_duration_seconds

    # How much effort was needed in this final slot?
    effort_needed_in_slot = required_effort - effort_before_slot

    # How many seconds into the slot does that take?
    seconds_into_slot = effort_needed_in_slot / effort_per_second if effort_per_second > 0 else slot_duration_seconds

    # Clamp to slot duration (shouldn't exceed, but safety check)
    seconds_into_slot = min(seconds_into_slot, slot_duration_seconds)

    # Calculate the precise end time, rounded to nearest second
    # (Gold standard uses second-level precision)
    seconds_rounded = round(seconds_into_slot)

    if forward:
        # For forward scheduling, end time is offset from slot start
        if slot_start is not None:
            precise_end = slot_start + timedelta(seconds=seconds_rounded)
        else:
            precise_end = scenario.project["start"] + timedelta(seconds=seconds_rounded)
    else:
        # For backward scheduling, we're calculating the START time
        # The start is at the END of the slot minus unused time
        # If we used the whole slot, start is at slot_start
        # If we used part of it, start is later in the slot
        if slot_start is not None:
            slot_end = slot_start + timedelta(seconds=slot_duration_seconds)
            precise_end = slot_end - timedelta(seconds=seconds_rounded)
        else:
            precise_end = scenario.project["start"]

    # Release unused portion of the slot back to the resource
    seconds_unused = slot_duration_seconds - seconds_into_slot
    if seconds_unused > 0 and resource:
        res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
        if res_scenario:
            # Update the per-task usage record to reflect actual usage
            if scenario.currentSlotIdx in res_scenario.slotTaskUsage:
                # Find and update this task's entry
                for i, (task, _secs) in enumerate(res_scenario.slotTaskUsage[scenario.currentSlotIdx]):
                    if task == scenario.property:
                        res_scenario.slotTaskUsage[scenario.currentSlotIdx][i] = (task, seconds_into_slot)
                        break

            # Update total slotSecondsUsed to release unused time
            # Old value was full slot duration, new value is actual usage
            old_total = res_scenario.slotSecondsUsed.get(scenario.currentSlotIdx, slot_duration_seconds)
            # Subtract what was previously booked (full slot) and add actual usage
            res_scenario.slotSecondsUsed[scenario.currentSlotIdx] = (
                old_total - slot_duration_seconds + seconds_into_slot
            )

    return precise_end, seconds_into_slot


def precise_end_time(scenario: Any, required_effort: float, effort_before_slot: float, forward: bool) -> datetime:
    """
    Calculate the precise end time within the final slot based on fractional effort.
    (Legacy method - calls the new implementation)
    """
    end_time, _ = precise_end_time_and_release(scenario, required_effort, effort_before_slot, forward)
    return end_time
