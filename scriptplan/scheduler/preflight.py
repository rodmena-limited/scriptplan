"""Pre-flight validation run before a scenario is scheduled.

A malformed project is rejected here, with an exception naming what is wrong,
rather than being handed to the scheduler and emerging as an unexplained
"deadlock" warning after the fact.

The checks in this module are structural: they depend only on how the tasks
reference each other, never on resource availability or the calendar.
"""

from __future__ import annotations

from typing import Any

from scriptplan.core.exceptions import CircularDependencyError

__all__ = [
    "check_no_cycles",
    "dependency_of",
    "find_dependency_cycle",
    "iter_dependencies",
    "stated_dates_inside_window",
]


def stated_dates_inside_window(project: Any, scenario_idx: int) -> bool:
    """Report every start or end a task states outside the project window.

    Checked before scheduling: a start after the window used to crash the
    scheduler with an index error reported as a parse error, and an end after
    it was clamped and the milestone dated outside the project (issuedb #22).
    Returns True when every stated date is inside.
    """
    window_start, window_end = project.attributes["start"], project.attributes["end"]
    inside = True
    for task in project.tasks:
        scenario = task.data[scenario_idx] if task.data else None
        for name in ("start", "end"):
            stated = getattr(scenario, "declared" + name.capitalize(), None)
            if stated is not None and not window_start <= stated <= window_end:
                inside = False
                project.error(
                    "date_outside_window",
                    f"Task '{task.fullId}' states {name} {stated}, outside the project window "
                    f"({window_start} to {window_end}).",
                    data=task.fullId,
                )
    return inside


def dependency_of(dep: Any) -> Any | None:
    """Return the predecessor task in a dependency entry.

    A dependency is stored either as the task itself or as a mapping carrying
    the gap and onstart/onend options alongside it.
    """
    if isinstance(dep, dict):
        return dep.get("task")
    if hasattr(dep, "task"):
        return dep.task
    return dep


def _is_onstart(dep: Any) -> bool:
    """True for a dependency that constrains starts rather than the finish chain."""
    if isinstance(dep, dict):
        return bool(dep.get("onstart"))
    return bool(getattr(dep, "onstart", False))


def iter_dependencies(task: Any, scenario_idx: int, finish_to_start_only: bool = False) -> list[Any]:
    """Predecessors of ``task``, including those inherited from its containers.

    With ``finish_to_start_only`` the ``onstart`` dependencies are left out.
    Those relate the two tasks' *starts*, so they do not form part of the
    finish-to-start chain that a forward pass can deadlock on, and counting
    them would report a loop where the schedule is satisfiable.
    """
    found: list[Any] = []
    node: Any | None = task
    while node is not None:
        for dep in node.get("depends", scenario_idx) or []:
            if finish_to_start_only and _is_onstart(dep):
                continue
            predecessor = dependency_of(dep)
            if predecessor is not None:
                found.append(predecessor)
        node = node.parent
    return found


def find_dependency_cycle(tasks: Any, scenario_idx: int) -> list[str] | None:
    """Return one finish-to-start dependency cycle, or None if there is none.

    Only finish-to-start edges are followed. A complete loop check would work
    over (task, start|end) pairs, so that a mixture of onstart and ordinary
    dependencies is judged on the constraint each one actually imposes; that
    belongs with the scheduling engine and is not done here.

    Iterative depth-first search with three-colour marking, so a project with a
    long chain cannot exhaust the interpreter's stack.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[int, int] = {}
    on_stack: list[Any] = []

    def task_id(node: Any) -> str:
        return getattr(node, "fullId", None) or getattr(node, "id", None) or repr(node)

    for root in tasks:
        if colour.get(id(root), WHITE) != WHITE:
            continue
        # Each frame is (node, iterator over its remaining predecessors).
        stack: list[tuple[Any, Any]] = [(root, iter(iter_dependencies(root, scenario_idx, finish_to_start_only=True)))]
        colour[id(root)] = GREY
        on_stack.append(root)

        while stack:
            node, pending = stack[-1]
            advanced = False
            for predecessor in pending:
                state = colour.get(id(predecessor), WHITE)
                if state == GREY:
                    # predecessor is an ancestor of node: report that loop
                    start = next(
                        (i for i, entry in enumerate(on_stack) if entry is predecessor),
                        0,
                    )
                    return [task_id(entry) for entry in on_stack[start:]] + [task_id(predecessor)]
                if state == WHITE:
                    colour[id(predecessor)] = GREY
                    on_stack.append(predecessor)
                    stack.append((predecessor, iter(iter_dependencies(predecessor, scenario_idx, finish_to_start_only=True))))
                    advanced = True
                    break
            if not advanced:
                colour[id(node)] = BLACK
                stack.pop()
                if on_stack and on_stack[-1] is node:
                    on_stack.pop()
    return None


def check_no_cycles(tasks: Any, scenario_idx: int) -> None:
    """Raise CircularDependencyError if the dependency graph has a cycle."""
    cycle = find_dependency_cycle(tasks, scenario_idx)
    if cycle is not None:
        raise CircularDependencyError(
            "Circular dependency: " + " -> ".join(cycle),
            task_id=cycle[0],
            dependency_id=cycle[-1],
        )
