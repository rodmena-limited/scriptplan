"""What a resource's schedule adds up to, and who reports to whom.

Counting booked, free and working slots, converting them into the load units a
report shows, and the manager/report relationships between resources. None of
it decides anything while scheduling; it is read afterwards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from scriptplan.core.resource_scenario import ResourceScenario
    from scriptplan.core.task import Task

__all__ = [
    "allocated_slots",
    "calc_criticalness",
    "effective_work",
    "finish_scheduling",
    "free_slots",
    "set_direct_reports",
    "set_reports",
    "set_reports_internal",
    "tree_sum",
    "tree_sum_recursive",
    "work_slots",
]


def effective_work(scenario: Any, start_idx: int, end_idx: int, task: Task | None = None) -> float:
    """
    Get the effective work done by this resource.

    Args:
        start_idx: Start scoreboard index
        end_idx: End scoreboard index
        task: Optional task filter

    Returns:
        Work in daily load units
    """
    duties = scenario.property.get("duties", scenario.scenarioIdx) or []
    if start_idx >= end_idx or (task and task not in duties):
        return 0.0

    def calculate(res_scen: ResourceScenario) -> float:
        if res_scen.scoreboard is None:
            return 0.0
        allocated = res_scen.getAllocatedSlots(start_idx, end_idx, task)
        granularity = res_scen.project.attributes.get("scheduleGranularity", 3600)
        efficiency = res_scen.property.get("efficiency", res_scen.scenarioIdx) or 1.0
        daily_load: float = res_scen.project.convertToDailyLoad(allocated * granularity) * efficiency  # type: ignore[attr-defined]
        return daily_load

    return tree_sum(scenario, start_idx, end_idx, task, block=calculate)


def allocated_slots(scenario: Any, start_idx: int, end_idx: int, task: Task | None = None) -> int:
    """
    Count booked slots in the given range.

    Args:
        start_idx: Start scoreboard index
        end_idx: End scoreboard index
        task: Optional task filter

    Returns:
        Number of allocated slots
    """
    if scenario.scoreboard is None:
        return 0

    if start_idx >= end_idx:
        return 0

    from scriptplan.core.task import Task

    booked_slots = 0
    task_list = task.all() if task and hasattr(task, "all") else []

    actual_end = min(end_idx, len(scenario.scoreboard))
    for i in range(start_idx, actual_end):
        slot = scenario.scoreboard[i]
        if isinstance(slot, Task) and (task is None or slot in task_list or slot == task):
            booked_slots += 1

    return booked_slots


def free_slots(scenario: Any, start_idx: int, end_idx: int) -> int:
    """
    Count free slots in the given range.

    Args:
        start_idx: Start scoreboard index
        end_idx: End scoreboard index

    Returns:
        Number of free slots
    """
    if scenario.scoreboard is None:
        return 0

    count = 0
    actual_end = min(end_idx, len(scenario.scoreboard))
    for i in range(start_idx, actual_end):
        if scenario.scoreboard[i] is None:
            count += 1
    return count


def work_slots(scenario: Any, start_idx: int, end_idx: int) -> int:
    """
    Count work slots (free + allocated) in the given range.

    Args:
        start_idx: Start scoreboard index
        end_idx: End scoreboard index

    Returns:
        Number of work slots
    """
    from scriptplan.core.task import Task

    if scenario.scoreboard is None:
        return 0

    count = 0
    actual_end = min(end_idx, len(scenario.scoreboard))
    for i in range(start_idx, actual_end):
        slot = scenario.scoreboard[i]
        if slot is None or isinstance(slot, Task):
            count += 1
    return count


def tree_sum(scenario: Any, start_idx: int, end_idx: int, *args: Any, block: Callable[[Any], float]) -> float:
    """
    Generic tree iterator that recursively accumulates results.

    Args:
        start_idx: Start scoreboard index
        end_idx: End scoreboard index
        *args: Additional arguments
        block: Callable to execute on leaf nodes

    Returns:
        Accumulated sum
    """
    cache_tag = "treeSum"
    return tree_sum_recursive(scenario, cache_tag, start_idx, end_idx, *args, block=block)


def tree_sum_recursive(
    scenario: Any, cache_tag: str, start_idx: int, end_idx: int, *args: Any, block: Callable[[Any], float]
) -> float:
    """
    Recursive implementation of treeSum.

    Args:
        cache_tag: Cache key tag
        start_idx: Start scoreboard index
        end_idx: End scoreboard index
        *args: Additional arguments
        block: Callable to execute on leaf nodes

    Returns:
        Accumulated sum
    """
    if scenario.property.container:
        sum_val = 0.0
        for resource in scenario.property.kids():
            if resource.data and resource.data[scenario.scenarioIdx]:
                res_scenario = resource.data[scenario.scenarioIdx]
                sum_val += tree_sum_recursive(
                    res_scenario, cache_tag, start_idx, end_idx, *args, block=block
                )
        return sum_val
    else:
        return block(scenario)


def calc_criticalness(scenario: Any) -> None:
    """
    Calculate the criticalness of the resource.

    The criticalness is a measure for the probability that all allocations
    can be fulfilled. A value above 1.0 means that statistically some tasks
    will not get their resources.
    """
    if scenario.scoreboard is None:
        scenario.property["criticalness", scenario.scenarioIdx] = 0.0
    else:
        free_slots = sum(1 for slot in scenario.scoreboard if slot is None)
        allocated_effort = scenario.property.get("alloctdeffort", scenario.scenarioIdx) or 0

        if free_slots == 0:
            scenario.property["criticalness", scenario.scenarioIdx] = 1.0
        else:
            scenario.property["criticalness", scenario.scenarioIdx] = allocated_effort / free_slots


def set_direct_reports(scenario: Any) -> None:
    """
    Set up the direct reports relationships based on managers.
    """
    managers = scenario.property.get("managers", scenario.scenarioIdx) or []
    new_managers = []

    for manager_id in managers:
        manager = (
            scenario.project.resources.get(manager_id)
            if isinstance(manager_id, str)
            else manager_id
        )

        if manager is None:
            scenario.error("resource_id_expected", f"{manager_id} is not a defined resource.")
            continue

        if not manager.leaf():
            scenario.error(
                "manager_is_group",
                f"Resource {scenario.property.fullId} has group {manager.fullId} assigned as manager.",
            )

        if manager == scenario.property:
            scenario.error("manager_is_self", f"Resource {scenario.property.fullId} cannot manage itscenario.")

        if scenario.property.leaf():
            direct_reports = manager.get("directreports", scenario.scenarioIdx) or []
            if scenario.property not in direct_reports:
                direct_reports.append(scenario.property)

        new_managers.append(manager)

    # Update managers list with unique entries
    seen = set()
    unique_managers = []
    for m in new_managers:
        if m not in seen:
            unique_managers.append(m)
            seen.add(m)

    scenario.property["managers", scenario.scenarioIdx] = unique_managers


def set_reports(scenario: Any) -> None:
    """
    Set up reporting relationships.
    """
    direct_reports = scenario.property.get("directreports", scenario.scenarioIdx)
    if not direct_reports:
        return

    managers = scenario.property.get("managers", scenario.scenarioIdx) or []
    for r in managers:
        if hasattr(r, "setReports_i"):
            r.setReports_i(scenario.scenarioIdx, [scenario.property])


def set_reports_internal(scenario: Any, reports: list[Any]) -> None:
    """
    Internal method to set reports relationship.

    Args:
        reports: List of resources reporting to this one
    """
    if scenario.property in reports:
        scenario.error("manager_loop", f"Management loop detected. {scenario.property.fullId} has self in list of reports")

    current_reports = scenario.property.get("reports", scenario.scenarioIdx) or []
    for r in reports:
        if r not in current_reports:
            current_reports.append(r)

    managers = scenario.property.get("managers", scenario.scenarioIdx) or []
    for r in managers:
        if hasattr(r, "setReports_i"):
            r.setReports_i(scenario.scenarioIdx, current_reports)


def finish_scheduling(scenario: Any) -> None:
    """
    Finish scheduling housekeeping.

    This method is called after scheduling is completed to do housekeeping
    like updating parent resources with duties from children.
    """
    # Recursively descend into all child resources
    for resource in scenario.property.children:
        if hasattr(resource, "finishScheduling"):
            resource.finishScheduling(scenario.scenarioIdx)

    # Add parent tasks of each task to the duties list
    duties = scenario.property.get("duties", scenario.scenarioIdx) or []
    current_duties = list(duties)
    for task in current_duties:
        if hasattr(task, "ancestors"):
            for p_task in task.ancestors(True):
                if p_task not in duties:
                    duties.append(p_task)

    # Add assigned tasks to parent resource duties
    parents = scenario.property.parents() if callable(scenario.property.parents) else scenario.property.parents
    for p_resource in parents or []:
        p_duties = p_resource.get("duties", scenario.scenarioIdx) or []
        for task in duties:
            if task not in p_duties:
                p_duties.append(task)
