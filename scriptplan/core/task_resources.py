"""What a task's resources can do, and what that comes to.

Whether an allocated resource could work in a slot, whether a run long enough
for an uninterruptible task starts here, which of several candidates would
finish soonest, and afterwards what the work cost and how long it took.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

__all__ = [
    "select_best_resources",
    "estimate_completion_time",
    "is_resource_available",
    "has_contiguous_block",
    "has_project_contiguous_block",
    "cost_of",
    "allocated_time",
    "resources_for_task",
    "advance_working_time",
]


def select_best_resources(
    scenario: Any, primary_resources: list[Any], alternative_resources: list[Any], effort: float
) -> list[Any]:
    """
    Select the best resources for this task using smart routing.

    For tasks with alternatives, this compares completion times:
    - Path A: Wait for primary resource to become available
    - Path B: Start now with alternative resource

    The path that finishes earlier wins.

    Args:
        primary_resources: List of primary (preferred) resources
        alternative_resources: List of alternative (fallback) resources
        effort: Required effort in hours

    Returns:
        List of resources to book
    """
    if not primary_resources and not alternative_resources:
        return []

    # If no alternatives, use primary resources
    if not alternative_resources:
        return primary_resources

    # If no primaries, use alternatives
    if not primary_resources:
        return alternative_resources

    # Smart routing: compare completion times
    # Calculate when each path would complete the task

    primary_end = estimate_completion_time(scenario, primary_resources, effort)
    alternative_end = estimate_completion_time(scenario, alternative_resources, effort)

    # Choose the path that finishes earlier
    if alternative_end is not None and (primary_end is None or alternative_end < primary_end):
        # Store which resource was selected for reporting
        if not hasattr(scenario, "_selectedAlternative"):
            scenario._selectedAlternative = True
        return alternative_resources
    else:
        if not hasattr(scenario, "_selectedAlternative"):
            scenario._selectedAlternative = False
        return primary_resources


def estimate_completion_time(scenario: Any, resources: list[Any], effort: float) -> Optional[datetime]:
    """
    Estimate when a task would complete using the given resources.

    Args:
        resources: List of resources to use
        effort: Required effort in hours

    Returns:
        Estimated completion datetime or None if cannot complete
    """
    if not resources or effort <= 0:
        return None

    from datetime import timedelta

    # Get efficiency (use first resource's efficiency)
    resource = resources[0]
    efficiency = resource.get("efficiency", scenario.scenarioIdx) or 1.0

    # Duration = effort / efficiency
    effort / efficiency

    # Find the first available slot for this resource
    res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
    if res_scenario is None:
        return None

    if res_scenario.scoreboard is None:
        res_scenario.prepareScheduling()

    # Simulate scheduling to find completion time
    slot_duration = scenario.project.attributes.get("scheduleGranularity", 3600)
    effort_per_slot = (slot_duration / 3600.0) * efficiency

    remaining_effort = effort
    current_slot = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0

    # Safety limit to prevent infinite loops
    max_slots = len(res_scenario.scoreboard) if res_scenario.scoreboard else 1000

    while remaining_effort > 0 and current_slot < max_slots:
        if res_scenario.available(current_slot):
            remaining_effort -= effort_per_slot
        current_slot += 1

    if remaining_effort > 0:
        return None  # Cannot complete within project timeframe

    # Calculate the end time
    # current_slot is now one past the last booked slot
    end_slot = current_slot - 1
    end_date_result = scenario.project.idxToDate(end_slot)
    if end_date_result is not None:
        result: Optional[datetime] = end_date_result + timedelta(seconds=slot_duration)
        return result
    else:
        return None


def is_resource_available(scenario: Any, slotIdx: int) -> bool:
    """Whether any allocated resource could work in this slot.

    Used to find where a task can begin, so it asks only about the shift,
    not about whether the slot is already taken.
    """
    plan = scenario.allocationPlan()
    if not plan:
        result: bool = scenario.project.isWorkingTime(slotIdx)
        return result

    for allocation in plan:
        for resource in allocation.candidates():
            scenario = resource.data[scenario.scenarioIdx] if resource.data else None
            if scenario is None:
                continue
            if scenario.scoreboard is None:
                scenario.prepareScheduling()
            if scenario.onShift(slotIdx):
                return True
    return False


def has_contiguous_block(scenario: Any, effort: float) -> bool:
    """Whether an unbroken run long enough for the task starts here.

    A task flagged `contiguous` cannot be split across a lunch break or a
    night, so it may only begin where the whole of it fits.
    """
    resources = scenario.allocationPlan().resources()
    if not resources:
        return has_project_contiguous_block(scenario, effort)

    resource = resources[0]
    res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
    if res_scenario is None:
        return has_project_contiguous_block(scenario, effort)
    if res_scenario.scoreboard is None:
        res_scenario.prepareScheduling()

    efficiency = resource.get("efficiency", scenario.scenarioIdx) or 1.0
    slot_duration_hours = scenario._slotSeconds() / 3600.0
    slots_needed = (effort / efficiency) / slot_duration_hours

    consecutive = 0
    current = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    limit = len(res_scenario.scoreboard) if res_scenario.scoreboard else 1000

    while current < limit and consecutive < slots_needed:
        if not res_scenario.available(current):
            return False
        consecutive += 1
        current += 1

    result_bool: bool = consecutive >= slots_needed
    return result_bool


def has_project_contiguous_block(scenario: Any, effort: float) -> bool:
    """
    Fallback check for contiguous block using project working time.
    """
    slot_duration_sec = scenario.project.attributes.get("scheduleGranularity", 3600)
    slot_duration_hours = slot_duration_sec / 3600.0
    slots_needed = effort / slot_duration_hours

    consecutive_count = 0
    current_slot = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
    max_slots = 1000

    while current_slot < max_slots and consecutive_count < slots_needed:
        if scenario.project.isWorkingTime(current_slot):
            if consecutive_count == 0 and current_slot != scenario.currentSlotIdx:
                return False
            consecutive_count += 1
            current_slot += 1
        else:
            if consecutive_count > 0:
                return False
            else:
                return False

    result_bool: bool = consecutive_count >= slots_needed
    return result_bool


def cost_of(scenario: Any) -> float:
    """
    Calculate the cost for this task based on allocated time and resource rates.

    Cost is calculated as: allocated_time x resource_rate
    where allocated_time is the actual duration (not effort).

    For efficiency > 1.0, allocated_time < effort
    For efficiency < 1.0, allocated_time > effort

    Returns:
        The total cost for this task
    """
    total_cost = 0.0

    # Get resources for this task
    resources = resources_for_task(scenario)

    for resource in resources:
        # Get the resource's scenario data
        res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
        if res_scenario is None:
            continue

        # Get resource rate
        rate = resource.get("rate", scenario.scenarioIdx) or 0.0
        if rate == 0.0:
            continue

        # Use slotTaskUsage to get exact time used by this task
        allocated_seconds = 0.0
        for _slot_idx, task_list in res_scenario.slotTaskUsage.items():
            for task, seconds in task_list:
                if task == scenario.property:
                    allocated_seconds += seconds

        allocated_hours = allocated_seconds / 3600.0
        total_cost += allocated_hours * rate

    return total_cost


def allocated_time(scenario: Any) -> float:
    """
    Calculate the total allocated time (duration) for this task.

    This is the actual calendar time spent on the task, which differs
    from effort when resource efficiency != 1.0.

    Returns:
        The allocated time in hours
    """
    total_allocated = 0.0

    # Get resources for this task
    resources = resources_for_task(scenario)

    for resource in resources:
        # Get the resource's scenario data
        res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
        if res_scenario is None or res_scenario.scoreboard is None:
            continue

        # Count slots booked for this task by this resource
        booked_slots = 0
        for i in range(len(res_scenario.scoreboard)):
            if res_scenario.scoreboard[i] == scenario.property:
                booked_slots += 1

        # Calculate allocated time in hours
        granularity = scenario.project.attributes.get("scheduleGranularity", 3600)
        allocated_hours = booked_slots * granularity / 3600.0
        total_allocated += allocated_hours

    return total_allocated


def resources_for_task(scenario: Any) -> list[Any]:
    """The Resource objects this task may book."""
    assigned = scenario.property.get("assignedresources", scenario.scenarioIdx) or []
    if assigned:
        return list(assigned)
    return scenario.allocationPlan().resources()


def advance_working_time(scenario: Any, start: datetime, seconds: float) -> datetime:
    """The moment ``seconds`` of *working* time after ``start``.

    Walks the calendar rather than the clock, so a gap that spans a weekend
    or a night is measured only in the hours somebody could have worked. A
    gap shorter than one slot lands inside a slot instead of being rounded
    away, which is how `gaplength 30min` used to become no gap at all.
    """
    from datetime import timedelta

    if seconds <= 0:
        return start

    slot_seconds = float(scenario.project.attributes.get("scheduleGranularity", 3600))
    idx = scenario.project.dateToIdx(start)
    slot_start = scenario.project.idxToDate(idx)
    offset = max(0.0, (start - slot_start).total_seconds()) if slot_start else 0.0
    upper = scenario.project.dateToIdx(scenario.project["end"])

    remaining = seconds
    while idx <= upper:
        if scenario.isWorkingTime(idx):
            available = slot_seconds - offset
            if remaining <= available:
                moment = scenario.project.idxToDate(idx)
                return moment + timedelta(seconds=offset + remaining)
            remaining -= available
        idx += 1
        offset = 0.0
    end_of_project: datetime = scenario.project["end"]
    return end_of_project
