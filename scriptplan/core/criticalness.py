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
  that follow it or follow a container it is inside.

Tasks are walked in declaration order, and a follower that was already walked
counts for what follows it, without its own criticalness. So where two tasks
lead into the same one, the first declared carries it and the second does not.
Schedules in this format have always been ordered that way, and a plan depends
on the order, so it is kept: the same file gives the same plan.

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

    followers = _followers(project, scIdx)
    paths: dict[int, float] = {}
    for task in project.tasks:
        _path(task, scIdx, followers, paths)
        task[("pathcriticalness", scIdx)] = paths[id(task)]


def _followers(project: Any, scIdx: int) -> dict[int, list[Any]]:
    """Predecessor -> the tasks that wait for it to end."""
    index: dict[int, list[Any]] = {}
    for task in project.tasks:
        for dep in task.get("depends", scIdx) or []:
            if isinstance(dep, dict):
                if dep.get("onstart"):
                    continue
                predecessor = dep.get("task")
            else:
                predecessor = getattr(dep, "task", dep)
            waiting = index.setdefault(id(predecessor), [])
            if task not in waiting:
                waiting.append(task)
    return index


def _path(task: Any, scIdx: int, followers: dict[int, list[Any]], paths: dict[int, float]) -> float:
    """What a path entering this task is worth to whoever leads into it.

    The first walk settles the task's path criticalness and returns it. A
    later walk returns it without the task's own criticalness.
    """
    own: float = task.get("criticalness", scIdx) or 0.0
    known = paths.get(id(task))
    if known is not None:
        return known - own
    # Settled before walking on, so a dependency loop, which is refused
    # elsewhere, cannot recurse here.
    paths[id(task)] = own

    heaviest = 0.0
    if task.leaf():
        holder = task
        while holder is not None:
            for follower in followers.get(id(holder), []):
                heaviest = max(heaviest, _path(follower, scIdx, followers, paths))
            holder = holder.parent
    else:
        # A container's path runs through its children.
        for child in task.children:
            heaviest = max(heaviest, _path(child, scIdx, followers, paths))

    paths[id(task)] = heaviest + own
    return heaviest + own
