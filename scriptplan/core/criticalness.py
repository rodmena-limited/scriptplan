"""How contended each task is, which decides who is placed first.

Tasks of equal priority are placed in order of path criticalness, highest
first. The idea is that work competing for scarce people should be placed
before work that could go anywhere:

- a resource's criticalness is the effort asked of it divided by the time it
  has; above 1.0, some task will statistically go without it;
- a task's criticalness is its effort times the mean criticalness of the
  resources it may use. A task with no effort, or no one allocated, has none.
  A milestone gets a small one that follows its priority;
- a task's path criticalness is its own plus the heaviest path among the tasks
  that wait for it, or for a container it is inside. A container's path is
  its heaviest child's.

Where two tasks lead into the same one, it counts in full for both, so the
result does not depend on the order the file declares them in. (0.10.3
counted it for the first declared only, as another scheduler of this format
does. That scheduler's own notes describe the full count.)

Computed once per scheduling run, before the first task is placed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["compute_criticalness"]

# Priority 500 gives a milestone a criticalness of 1.0.
_MILESTONE_PRIORITY_UNIT = 500.0


def compute_criticalness(project: Any, scIdx: int) -> None:
    """Set criticalness on every resource and task, and pathcriticalness on every task."""
    slot_hours = float(project.attributes.get("scheduleGranularity", 3600)) / 3600.0

    # Effort asked of each resource, in slots. A task that may use any of
    # several asks each for an equal share.
    asked: dict[int, float] = {}
    candidates: dict[int, list[Any]] = {}
    for task in project.tasks:
        if not task.leaf():
            continue
        effort = (task.get("effort", scIdx) or 0) / slot_hours
        people = task.data[scIdx].allocationPlan().resources() if effort > 0 else []
        candidates[id(task)] = people
        for resource in people:
            asked[id(resource)] = asked.get(id(resource), 0.0) + effort / len(people)

    for resource in project.resources:
        scenario = resource.data[scIdx] if resource.data else None
        board = getattr(scenario, "scoreboard", None)
        if board is None:
            value = 0.0
        else:
            free = sum(1 for slot in board if slot is None)
            value = asked.get(id(resource), 0.0) / free if free else 1.0
        resource[("criticalness", scIdx)] = value

    for task in project.tasks:
        people = candidates.get(id(task), [])
        if task.leaf() and task.get("milestone", scIdx):
            value = (task.get("priority", scIdx) or 0) / _MILESTONE_PRIORITY_UNIT
        elif people:
            effort = (task.get("effort", scIdx) or 0) / slot_hours
            mean = sum(r.get("criticalness", scIdx) or 0.0 for r in people) / len(people)
            value = effort * mean
        else:
            value = 0.0
        task[("criticalness", scIdx)] = value

    paths = _path_criticalness(project, scIdx, _followers(project, scIdx))
    for task in project.tasks:
        task[("pathcriticalness", scIdx)] = paths[id(task)]


def _followers(project: Any, scIdx: int) -> dict[int, list[Any]]:
    """Predecessor -> the tasks that wait for it, to end or `{ onstart }` to start."""
    index: dict[int, list[Any]] = {}
    for task in project.tasks:
        for dep in task.get("depends", scIdx) or []:
            predecessor = dep.get("task") if isinstance(dep, dict) else getattr(dep, "task", dep)
            waiting = index.setdefault(id(predecessor), [])
            if task not in waiting:
                waiting.append(task)
    return index


def _onward(task: Any, followers: dict[int, list[Any]]) -> list[Any]:
    """Where a path goes after this task."""
    if not task.leaf():
        # A container's path runs through its children.
        return list(task.children)
    onward: list[Any] = []
    holder = task
    while holder is not None:
        onward.extend(followers.get(id(holder), []))
        holder = holder.parent
    return onward


def _path_criticalness(project: Any, scIdx: int, followers: dict[int, list[Any]]) -> dict[int, float]:
    """Each task's own criticalness plus the heaviest path that leaves it.

    A depth-first walk on an explicit stack. Recursing instead ran out of
    stack on a chain of a thousand tasks (issuedb #46).
    """
    paths: dict[int, float] = {}
    heaviest: dict[int, float] = {}
    for root in project.tasks:
        if id(root) in heaviest:
            continue
        heaviest[id(root)] = 0.0
        stack: list[tuple[Any, Any]] = [(root, iter(_onward(root, followers)))]
        while stack:
            task, pending = stack[-1]
            entered = False
            for following in pending:
                if id(following) in paths:
                    heaviest[id(task)] = max(heaviest[id(task)], paths[id(following)])
                elif id(following) not in heaviest:
                    heaviest[id(following)] = 0.0
                    stack.append((following, iter(_onward(following, followers))))
                    entered = True
                    break
                # Otherwise it is still open below us: a dependency loop,
                # which is refused elsewhere and adds nothing here.
            if entered:
                continue
            stack.pop()
            own: float = task.get("criticalness", scIdx) or 0.0
            paths[id(task)] = heaviest[id(task)] + own
            if stack:
                above = stack[-1][0]
                heaviest[id(above)] = max(heaviest[id(above)], paths[id(task)])
    return paths
