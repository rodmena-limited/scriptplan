"""What the scheduler does when a task cannot be placed, and what it says.

A task that runs out of project before its work is done, a chain whose tasks
wait for each other, and a task whose successor already failed each end the
attempt to place that task. The messages name the moment the task could not
meet, so the reader can tell a deadline that is too early from a project
window that is too short.
"""

from __future__ import annotations

from typing import Any

__all__ = ["break_deadlock", "report_unscheduled"]


def report_unscheduled(project: Any, task: Any, scenario_idx: int, reason: str) -> None:
    """Record why one task could not be placed, naming the task."""
    task_id = getattr(task, "fullId", None) or getattr(task, "id", None) or repr(task)
    detail = reason
    if reason == "ran outside the project window":
        detail = _runaway_detail(project, task, scenario_idx)
    project.scheduleErrors.append((task_id, detail))
    project.error("unscheduled_task", f"Task '{task_id}' could not be scheduled: {detail}", data=task_id)


def _runaway_detail(project: Any, task: Any, scenario_idx: int) -> str:
    start, end = project.attributes["start"], project.attributes["end"]
    if (task.get("effort", scenario_idx) or 0) > 0 and not task.get("allocate", scenario_idx):
        # Nothing can do the work, however long the project is.
        return "it has effort but no resource is allocated to do it"
    scenario = task.data[scenario_idx] if task.data else None
    latest = getattr(scenario, "latestEnd", None)
    if task.get("forward", scenario_idx) is False and latest is not None:
        # Placed backwards from a deadline: the deadline is what cannot be
        # met, not the project window (issuedb #25).
        return (
            f"it must end by {latest}, and there is not enough working time between the "
            f"project start ({start}) and then"
        )
    return (
        f"ran outside the project window ({start} to {end}); it needs more time or more "
        "resource availability than the project allows"
    )


def break_deadlock(project: Any, tasks: list[Any], failed: list[Any], scenario_idx: int) -> Any:
    """Unblock a stuck schedule by one task, if a task can be decided.

    A task scheduled as late as possible waits to learn when its successors
    start. A task scheduled as early as possible waits to learn when its
    predecessors finish. Put one of each in a chain with no fixed end and they
    wait for each other for ever.

    A backward task whose successor could not be scheduled has no moment to
    end by, so it is reported as unschedulable too, and returned so the caller
    can count it as failed. Scheduling it forwards would book it after the
    deadline its successor failed to meet (issuedb #25).

    A backward task with no end of its own, and no successor that can give it
    one, has nothing to be late against. It is scheduled forwards instead, and
    the reader is told, which beats reporting a deadlock and scheduling
    nothing. Returns True when that happened, None when nothing can be decided.
    """
    for task in tasks:
        if task.get("forward", scenario_idx) is not False:
            continue
        scenario = task.data[scenario_idx] if task.data else None
        successors = scenario._getSuccessors() if scenario is not None else []
        broken = next((s for s in successors if s in failed), None)
        if broken is not None:
            report_unscheduled(
                project, task, scenario_idx, f"its successor '{broken.fullId}' could not be scheduled"
            )
            return task
        if task.get("end", scenario_idx):
            continue
        if any(successor.get("scheduled", scenario_idx) for successor in successors):
            continue
        task[("forward", scenario_idx)] = True
        project.warning(
            "alap_degraded",
            f"Task '{task.fullId}' asks to be scheduled as late as possible, but nothing "
            f"fixes when it must end: it has no end date and no scheduled successor. "
            f"It has been scheduled as early as possible instead. Give it an end date, "
            f"or a successor that has one, to schedule it backwards.",
        )
        return True
    return None
