"""Which way round a task is scheduled, and rolling containers up.

Backward scheduling needs to know, before any task is placed, which tasks end
at a fixed point and which take their end from a successor. Containers need
their dates recomputed as their children are placed. Both are bookkeeping over
the task tree rather than scheduling decisions, so they live here and leave
Project holding the loop itself.

Each function takes the project as its first argument; they were methods, and
Project still calls them as such through thin wrappers.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "mark_task_alap",
    "propagate_alap_mode",
    "propagate_container_end_dates",
    "update_container_task_status",
]


def iter_own_and_inherited(task: Any, scIdx: int) -> list[Any]:
    """The dependency entries of a task and of every container it is inside."""
    entries: list[Any] = []
    node: Any | None = task
    while node is not None:
        entries.extend(node.get("depends", scIdx) or [])
        node = node.parent
    return entries


def propagate_container_end_dates(self: Any, scIdx: int) -> None:
    """
    Propagate container task end dates to their leaf children as constraints.

    In ALAP mode, if a container has an end date, only the "terminal" tasks
    (those with no successors within the container) should get the end constraint.
    Other tasks will get their end constraints from their successors.

    A task is terminal when nothing waits for it to end. A task that depends
    on it `{ onstart }` waits for its start, so it does not count.
    """
    has_fs_successor: set[Any] = set()  # predecessors in finish-to-start dependencies

    for task in self.tasks:
        if not task.leaf():
            continue
        for dep in task.get("depends", scIdx) or []:
            if isinstance(dep, dict):
                pred = dep.get("task")
                onstart = dep.get("onstart", False)
            elif hasattr(dep, "task"):
                pred = dep.task
                onstart = getattr(dep, "onstart", False)
            else:
                pred = dep
                onstart = False

            if pred and hasattr(pred, "fullId") and not onstart:
                has_fs_successor.add(pred.fullId)

    def propagate_end_to_children(task: Any, container_end: Any | None) -> None:
        """Recursively propagate end constraint down the task tree."""
        task_end = task.get("end", scIdx)
        # Use the most restrictive (earliest) end date
        effective_end = task_end if task_end else container_end

        if task.leaf():
            # Leaf task - apply the constraint if ALAP, no explicit end,
            # AND the task is terminal
            forward = task.get("forward", scIdx)
            task_id = task.fullId if hasattr(task, "fullId") else None

            is_terminal = task_id not in has_fs_successor

            if forward is False and not task_end and container_end and is_terminal:
                task[("end", scIdx)] = container_end
        else:
            # Container - propagate to children
            for child in task.children:
                propagate_end_to_children(child, effective_end)

    # Start from root tasks (no parent)
    for task in self.tasks:
        if task.parent is None:
            task_end = task.get("end", scIdx)
            if task_end:
                propagate_end_to_children(task, task_end)


def update_container_task_status(self: Any, scIdx: int) -> None:
    """Mark container tasks as scheduled when all their children are scheduled.

    Also compute start/end dates for container tasks based on children. The
    pass repeats until no container changes: tasks come in declaration order,
    outer containers first, so a single pass left a container two levels up
    unscheduled, and a task that depended on it waited for ever (issuedb #33).
    """
    while _mark_finished_containers(self, scIdx):
        pass


def _mark_finished_containers(self: Any, scIdx: int) -> bool:
    """One pass of update_container_task_status; True if it marked a container."""
    marked = False
    for task in self.tasks:
        if task.leaf():
            continue  # Skip leaf tasks

        if task.get("scheduled", scIdx):
            continue  # Already scheduled

        # Check if all children are scheduled
        children = task.children
        if not children:
            continue

        all_scheduled = all(child.get("scheduled", scIdx) for child in children)
        if not all_scheduled:
            continue

        # All children scheduled - mark container as scheduled
        # Compute start/end from children
        min_start: Any | None = None
        max_end: Any | None = None
        for child in children:
            child_start = child.get("start", scIdx)
            child_end = child.get("end", scIdx)
            if child_start and (min_start is None or child_start < min_start):
                min_start = child_start
            if child_end and (max_end is None or child_end > max_end):
                max_end = child_end

        if min_start:
            task[("start", scIdx)] = min_start
        if max_end:
            task[("end", scIdx)] = max_end
        task[("scheduled", scIdx)] = True
        marked = True
    return marked


def propagate_alap_mode(self: Any, scIdx: int) -> None:
    """
    Propagate ALAP scheduling mode backward through dependency chains.

    When task B depends on task A, and B is ALAP with a fixed end date,
    task A should also be scheduled ALAP (as late as possible) to allow
    B to meet its deadline.

    This implements "backward propagation" of ALAP constraints:
    1. Find all ALAP tasks with fixed end dates (anchor tasks)
    2. For each anchor, traverse its dependencies backward
    3. Mark predecessor tasks as ALAP and set their end constraint
       to the dependent task's calculated start
    """
    # Build reverse dependency map: task -> list of tasks that depend on it
    reverse_deps: dict[Any, list[Any]] = {}  # predecessor_id -> [successor tasks]
    for task in self.tasks:
        if not task.leaf():
            continue
        deps = task.get("depends", scIdx) or []
        for dep in deps:
            # Extract the predecessor task from dependency
            if isinstance(dep, dict):
                pred = dep.get("task")
            elif hasattr(dep, "task"):
                pred = dep.task
            else:
                pred = dep

            if pred:
                pred_id = pred.fullId if hasattr(pred, "fullId") else id(pred)
                if pred_id not in reverse_deps:
                    reverse_deps[pred_id] = []
                reverse_deps[pred_id].append(task)

    # Find ALAP anchor tasks (ALAP with fixed end)
    alap_anchors: list[Any] = []
    for task in self.tasks:
        if not task.leaf():
            continue
        forward = task.get("forward", scIdx)
        end = task.get("end", scIdx)
        if forward is False and end:  # ALAP with fixed end
            alap_anchors.append(task)

    # Propagate ALAP backward from each anchor
    # Use BFS to traverse dependency chains
    processed: set[Any] = set()
    for anchor in alap_anchors:
        anchor_id = anchor.fullId if hasattr(anchor, "fullId") else id(anchor)
        processed.add(anchor_id)

        # Get dependencies of the anchor (tasks that must finish before anchor starts)
        deps = anchor.get("depends", scIdx) or []
        for dep in deps:
            if isinstance(dep, dict):
                pred = dep.get("task")
            elif hasattr(dep, "task"):
                pred = dep.task
            else:
                pred = dep

            if not pred:
                continue

            pred_id = pred.fullId if hasattr(pred, "fullId") else id(pred)
            if pred_id in processed:
                continue

            # Mark predecessor as ALAP
            # It should finish as late as possible while still allowing the anchor to start
            mark_task_alap(self, pred, scIdx, processed, reverse_deps)


def mark_task_alap(self: Any, task: Any, scIdx: int, processed: set[Any], reverse_deps: dict[Any, list[Any]]) -> None:
    """
    Mark a task as ALAP and propagate to its predecessors.

    Args:
        task: The task to mark as ALAP
        scIdx: Scenario index
        processed: Set of already processed task IDs
        reverse_deps: Map of task ID -> list of successor tasks
    """
    task_id = task.fullId if hasattr(task, "fullId") else id(task)
    if task_id in processed:
        return
    processed.add(task_id)

    # Only process leaf tasks
    if not task.leaf():
        return

    # Check if task is already explicitly ASAP with a fixed start
    # In that case, don't override
    forward = task.get("forward", scIdx)
    start = task.get("start", scIdx)
    if forward is True and start:
        # Explicitly ASAP with start date - don't change
        return

    # A task that starts when another starts is placed forwards from that
    # start. Turning it backward would leave its onstart dependency unheld.
    if any(isinstance(dep, dict) and dep.get("onstart") for dep in iter_own_and_inherited(task, scIdx)):
        return

    # Mark as ALAP (forward=False)
    task[("forward", scIdx)] = False

    # Now propagate to predecessors of this task
    deps = task.get("depends", scIdx) or []
    for dep in deps:
        if isinstance(dep, dict):
            pred = dep.get("task")
        elif hasattr(dep, "task"):
            pred = dep.task
        else:
            pred = dep

        if pred:
            mark_task_alap(self, pred, scIdx, processed, reverse_deps)
