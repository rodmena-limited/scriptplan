"""Pre-flight validation run before a scenario is scheduled.

A malformed project is rejected here, with an exception naming what is wrong,
rather than being handed to the scheduler and emerging as an unexplained
"deadlock" warning after the fact.

The checks in this module are structural: they depend only on how the tasks
reference each other, never on resource availability or the calendar.
"""

from __future__ import annotations

from typing import Any, Optional

from scriptplan.core.exceptions import CircularDependencyError

__all__ = ["dependency_of", "iter_dependencies", "find_dependency_cycle", "check_no_cycles"]


def dependency_of(dep: Any) -> Optional[Any]:
    """Return the predecessor task in a dependency entry.

    A dependency is stored either as the task itself or as a mapping carrying
    the gap and onstart/onend options alongside it.
    """
    if isinstance(dep, dict):
        return dep.get("task")
    if hasattr(dep, "task"):
        return dep.task
    return dep


def iter_dependencies(task: Any, scenario_idx: int) -> list[Any]:
    """Predecessors of ``task``, including those inherited from its containers."""
    found: list[Any] = []
    node: Optional[Any] = task
    while node is not None:
        for dep in node.get("depends", scenario_idx) or []:
            predecessor = dependency_of(dep)
            if predecessor is not None:
                found.append(predecessor)
        node = node.parent
    return found


def find_dependency_cycle(tasks: Any, scenario_idx: int) -> Optional[list[str]]:
    """Return one dependency cycle as a list of task ids, or None if acyclic.

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
        stack: list[tuple[Any, Any]] = [(root, iter(iter_dependencies(root, scenario_idx)))]
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
                    stack.append((predecessor, iter(iter_dependencies(predecessor, scenario_idx))))
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
