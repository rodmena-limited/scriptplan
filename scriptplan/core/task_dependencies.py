"""Questions a task asks about the tasks around it.

Which tasks come before this one, which come after, when the ones after could
start, and how far back this one has to move to keep a maximum gap. All of it
is reading the dependency graph rather than placing anything, so it lives
apart from the scheduling itself.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from scriptplan.core.allocation_plan import AllocationPlan

__all__ = [
    "all_dependencies",
    "max_gap_delayed_start",
    "start_from_end",
    "successor_earliest_start",
    "successors",
    "successors_with_max_gap",
]


def all_dependencies(scenario: Any) -> list[Any]:
    """
    Get all dependencies including inherited ones from parent containers.

    In TaskJuggler, child tasks inherit dependencies from their parent
    containers. For example, if a container 'software' depends on 'spec',
    all children of 'software' (database, gui, backend) also depend on 'spec'.
    """
    all_deps: list[Any] = []

    # Get own dependencies
    own_deps = scenario.property.get("depends", scenario.scenarioIdx) or []
    all_deps.extend(own_deps)

    # Get parent dependencies (recursively up the tree)
    parent = scenario.property.parent
    while parent:
        parent_deps = parent.get("depends", scenario.scenarioIdx) or []
        all_deps.extend(parent_deps)
        parent = parent.parent

    return all_deps


def successors(scenario: Any) -> list[Any]:
    """
    Get all tasks that depend on this task (successors).

    These are tasks T where T's dependencies include this task.
    """
    successors = []
    for task in scenario.project.tasks:
        if not task.leaf():
            continue
        deps = task.get("depends", scenario.scenarioIdx) or []
        for dep in deps:
            if isinstance(dep, dict):
                pred = dep.get("task")
            elif hasattr(dep, "task"):
                pred = dep.task
            else:
                pred = dep

            if pred is scenario.property:
                successors.append(task)
                break

    return successors


def successors_with_max_gap(scenario: Any) -> list[tuple[Any, Any, Any]]:
    """
    Get successors that have maxgapduration constraint on this task.

    Returns list of (task, maxgapduration, gapduration) tuples.
    """
    result = []
    for task in scenario.project.tasks:
        if not task.leaf():
            continue
        deps = task.get("depends", scenario.scenarioIdx) or []
        for dep in deps:
            if isinstance(dep, dict):
                pred = dep.get("task")
                maxgap = dep.get("maxgapduration")
                gap = dep.get("gapduration")
            elif hasattr(dep, "task"):
                pred = dep.task
                maxgap = getattr(dep, "maxgapduration", None)
                gap = getattr(dep, "gapduration", None)
            else:
                pred = dep
                maxgap = None
                gap = None

            if pred is scenario.property and maxgap:
                result.append((task, maxgap, gap))
                break
    return result


def successor_earliest_start(scenario: Any, successor: Any) -> datetime:
    """
    Find the earliest time a successor task can start based on its resource availability.

    Returns datetime of earliest available slot.
    """

    # Get successor's allocations
    allocations = successor.get("allocate", scenario.scenarioIdx)
    if not allocations:
        # No allocations - use project working time
        start_idx = scenario.project.dateToIdx(scenario.project["start"])
        end_idx = scenario.project.dateToIdx(scenario.project["end"])
        for idx in range(start_idx, end_idx):
            if scenario.project.isWorkingTime(idx):
                result = scenario.project.idxToDate(idx)
                if result is not None:
                    result_dt: datetime = result
                    return result_dt
        result_end: datetime = scenario.project["end"]
        return result_end

    plan = AllocationPlan.read(allocations, scenario._resolve_resource)
    resources = plan.resources()
    if not resources:
        result_start_1: datetime = scenario.project["start"]
        return result_start_1
    resource = resources[0]

    # Get resource's scenario data
    res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
    if res_scenario is None:
        result_start_2: datetime = scenario.project["start"]
        return result_start_2

    # Initialize scoreboard if needed
    if res_scenario.scoreboard is None:
        res_scenario.prepareScheduling()

    # Find earliest slot where resource is on shift
    start_idx = scenario.project.dateToIdx(scenario.project["start"])
    end_idx = scenario.project.dateToIdx(scenario.project["end"])
    for idx in range(start_idx, end_idx):
        if res_scenario.onShift(idx):
            result = scenario.project.idxToDate(idx)
            if result is not None:
                result_shift: datetime = result
                return result_shift

    result_end_2: datetime = scenario.project["end"]
    return result_end_2


def max_gap_delayed_start(scenario: Any, earliest_start: datetime, effort: float) -> datetime:
    """
    Compute delayed start time based on maxgapduration constraints from successors.

    If any successor has maxgapduration, we need to ensure this task ends
    late enough that the gap doesn't exceed maxgapduration.

    Args:
        earliest_start: The earliest time this task could start (from dependencies)
        effort: The effort required for this task

    Returns:
        Delayed start time (datetime), or earliest_start if no delay needed
    """

    successors_with_maxgap = successors_with_max_gap(scenario, )
    if not successors_with_maxgap:
        return earliest_start

    delayed_start = earliest_start

    for successor, maxgap_str, gap_str in successors_with_maxgap:
        # Find when successor can start
        successor_earliest = successor_earliest_start(scenario, successor)

        # Both maxgapduration and gapduration are calendar time.
        maxgap_hours = scenario._calendarSeconds(maxgap_str) / 3600.0
        gap_hours = scenario._calendarSeconds(gap_str) / 3600.0 if gap_str else 0.0
        scenario._lastMaxGapHours = maxgap_hours

        # This task must end no more than maxgap_hours before successor can start
        # Required end time: successor_earliest - gap_hours (to satisfy gapduration)
        # But end time must be >= successor_earliest - maxgap_hours (to satisfy maxgapduration)
        # So we want end time between (successor_earliest - maxgap_hours) and (successor_earliest - gap_hours)
        # Ideally, end exactly at successor_earliest - gap_hours to minimize gap

        desired_end = successor_earliest - timedelta(hours=gap_hours)

        # Work backwards from desired_end to find required start
        # For effort-based tasks, we need 'effort' hours of work before desired_end
        if effort > 0:
            required_start = start_from_end(scenario, desired_end, effort)
            if required_start > delayed_start:
                delayed_start = required_start

    return delayed_start


def start_from_end(scenario: Any, end_time: datetime, effort: float) -> datetime:
    """
    Given an end time and required effort, compute when to start.

    Walks backwards from end_time counting working hours until effort is met.

    Args:
        end_time: Desired end time (datetime)
        effort: Required effort in hours

    Returns:
        Required start time (datetime)
    """

    # The first allocated resource decides which calendar to walk back over.
    resources = scenario.allocationPlan().resources()
    resource = resources[0] if resources else None

    end_idx = scenario.project.dateToIdx(end_time)
    start_idx = scenario.project.dateToIdx(scenario.project["start"])

    # Count backwards from end_idx
    working_slots = 0
    current_idx = end_idx - 1  # Start from slot before end

    while current_idx >= start_idx and working_slots < effort:
        if resource:
            res_scenario = resource.data[scenario.scenarioIdx] if resource.data else None
            if res_scenario:
                if res_scenario.scoreboard is None:
                    res_scenario.prepareScheduling()
                if res_scenario.onShift(current_idx):
                    working_slots += 1
            else:
                if scenario.project.isWorkingTime(current_idx):
                    working_slots += 1
        else:
            if scenario.project.isWorkingTime(current_idx):
                working_slots += 1
        current_idx -= 1

    result = scenario.project.idxToDate(current_idx + 1)
    assert result is not None
    result_dt_4: datetime = result
    return result_dt_4
