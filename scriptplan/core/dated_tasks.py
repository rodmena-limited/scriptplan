"""Tasks whose dates the file states, and so need no placing.

A milestone with a date sits on it. A task with a start and an end of its own
and no effort, duration or length runs for exactly that period. Neither is
placed by the scheduler, but the second still uses the resources it allocates:
they are booked for every slot of the period in which they are on shift and
free, in the task's turn among the others, so a task ranked lower cannot take
the same hours (issuedb #36).
"""

from __future__ import annotations

from typing import Any

from scriptplan.core.task_placement import own_start

__all__ = ["hold_stated_period", "settle_dated_tasks"]


def settle_dated_tasks(project: Any, scIdx: int) -> None:
    """Mark as scheduled every leaf task whose dates need no placing.

    A milestone is either marked with the milestone attribute, or has a start
    or an end and no effort, duration or length.
    """
    for task in project.tasks:
        if not task.leaf():
            continue

        is_explicit_milestone = task.get("milestone", scIdx)
        effort = task.get("effort", scIdx) or 0
        duration = task.get("duration", scIdx) or 0
        length = task.get("length", scIdx) or 0
        start = task.get("start", scIdx)
        end = task.get("end", scIdx)

        # Implicit milestone: has start/end but no duration metrics
        is_implicit_milestone = (start or end) and effort == 0 and duration == 0 and length == 0

        if not (is_explicit_milestone or is_implicit_milestone):
            continue
        # Only mark as scheduled if we can set both dates
        # Milestones with dependencies but no dates need to go through normal scheduling
        if start and not end:
            if task.get("forward", scIdx) is not False and own_start(task.data[scIdx]) is None:
                # A start inherited from a container is an earliest
                # start: placed with the dependencies (issuedb #31).
                continue
            task[("end", scIdx)] = start
            task[("scheduled", scIdx)] = True
        elif end and not start:
            task[("start", scIdx)] = end
            task[("scheduled", scIdx)] = True
        elif start and end:
            if not is_explicit_milestone and start < end and task.get("allocate", scIdx):
                # Its resources are booked when its turn comes.
                task.data[scIdx].statedPeriod = True
            else:
                task[("scheduled", scIdx)] = True
        # else: milestone with no dates - let it be scheduled by the main loop


def hold_stated_period(task: Any, scIdx: int) -> bool:
    """Book a stated period's resources and mark the task scheduled.

    Returns False for any other task. Where a resource is already taken, the
    task keeps its dates and goes without it for those slots.
    """
    scenario = task.data[scIdx]
    if not getattr(scenario, "statedPeriod", False):
        return False
    scenario.statedPeriod = False

    project = task.project
    first = max(0, project.dateToIdx(task.get("start", scIdx)))
    last = min(project.scoreboardSize(), project.dateToIdx(task.get("end", scIdx)))
    for slot in range(first, last):
        scenario.currentSlotIdx = slot
        scenario.bookResources()

    scenario.scheduled = True
    task[("scheduled", scIdx)] = True
    return True
