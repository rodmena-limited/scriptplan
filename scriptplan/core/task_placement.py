"""Placing one task: where it starts, how far it gets each slot, where it ends.

A forward task walks the calendar from its earliest possible start; a backward
one walks back from its latest possible end. Either way it asks for one slot at
a time, books what it can, and stops when the work is done -- or runs out of
project, which is a failure worth reporting rather than a schedule worth
believing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

__all__ = [
    "enter_at",
    "finish_scheduling",
    "place_slot",
    "place_task",
    "propagate_date",
    "schedule_container",
]


def place_task(scenario: Any) -> bool:
    if scenario.scheduled:
        return True

    # Determine start slot
    forward = scenario.property.get("forward", scenario.scenarioIdx)
    effort = scenario.property.get("effort", scenario.scenarioIdx) or 0
    allocations = scenario.property.get("allocate", scenario.scenarioIdx)

    if scenario.currentSlotIdx is None:
        if forward:
            start_date = scenario.property.get("start", scenario.scenarioIdx)
            if start_date:
                scenario.currentSlotIdx = enter_at(scenario, start_date, forward=True)
            else:
                # ASAP mode, start at project start or after dependencies
                # Check ALL dependencies (including inherited) to find the earliest start
                earliest_start = scenario.project["start"]
                for dep in scenario.getAllDependencies():
                    # dep can be a dict with 'task' key (new format with gap),
                    # or a Task object directly (old format)
                    if isinstance(dep, dict):
                        t = dep.get("task")
                        gapduration = dep.get("gapduration")
                        gaplength = dep.get("gaplength")
                        onstart = dep.get("onstart", False)
                    elif hasattr(dep, "task"):
                        t = dep.task
                        gapduration = getattr(dep, "gapduration", None)
                        gaplength = getattr(dep, "gaplength", None)
                        onstart = getattr(dep, "onstart", False)
                    else:
                        t = dep
                        gapduration = None
                        gaplength = None
                        onstart = False

                    if not t:
                        continue

                    # Use start time if onstart, otherwise use end time (finish-to-start)
                    dep_time = t.get("start", scenario.scenarioIdx) if onstart else t.get("end", scenario.scenarioIdx)
                    if dep_time:
                        # Add gap if specified
                        if gapduration:
                            dep_time = dep_time + timedelta(
                                seconds=scenario._calendarSeconds(gapduration)
                            )
                        elif gaplength:
                            dep_time = scenario._advanceWorkingTime(
                                dep_time, scenario._workingSeconds(gaplength)
                            )
                        if dep_time > earliest_start:
                            earliest_start = dep_time

                # Check for maxgapduration constraints from successors
                # If a successor has maxgapduration, we may need to delay our start
                # so that we end close enough for the successor to meet the constraint
                if effort > 0:
                    delayed_start = scenario._computeMaxGapDelayedStart(earliest_start, effort)
                    if delayed_start > earliest_start:
                        earliest_start = delayed_start

                # If earliest_start is mid-slot, the time before it in that
                # slot must not be booked: the predecessor is still running.
                scenario.currentSlotIdx = enter_at(scenario, earliest_start, forward=True)
        else:
            # ALAP (backward) scheduling
            end_date = scenario.property.get("end", scenario.scenarioIdx)

            if not end_date:
                # No explicit end - derive from:
                # 1. Predecessors with onstart deps (our END <= their START)
                # 2. Successors (tasks depending on this - our END <= their START)
                latest_end = scenario.project["end"]  # Default to project end

                # Check onstart dependencies - our END must be before predecessor's START
                # with gapduration subtracted if specified
                for dep in scenario.getAllDependencies():
                    if isinstance(dep, dict):
                        onstart = dep.get("onstart", False)
                        pred = dep.get("task")
                        gapduration = dep.get("gapduration")
                    elif hasattr(dep, "task"):
                        onstart = getattr(dep, "onstart", False)
                        pred = dep.task
                        gapduration = getattr(dep, "gapduration", None)
                    else:
                        onstart = False
                        pred = dep
                        gapduration = None

                    if onstart and pred:
                        pred_start = pred.get("start", scenario.scenarioIdx)
                        if pred_start:
                            # Apply gapduration - A must end (gapduration) before B starts
                            if gapduration:
                                pred_start = pred_start - timedelta(
                                    seconds=scenario._calendarSeconds(gapduration)
                                )
                            if pred_start < latest_end:
                                latest_end = pred_start

                # Also check successors (finish-to-start deps)
                successors = scenario._getSuccessors()
                for successor in successors:
                    succ_start = successor.get("start", scenario.scenarioIdx)
                    if succ_start and succ_start < latest_end:
                        latest_end = succ_start

                end_date = latest_end

            if end_date:
                # For ALAP, start from the slot the end date falls in, or the
                # one before it when the end is on a slot boundary
                scenario.currentSlotIdx = enter_at(scenario, end_date, forward=False)
                # Find the last working slot
                # For effort tasks with allocations, check resource availability
                # (respects resource timezone and working hours)
                lowerLimit = scenario.project.dateToIdx(scenario.project["start"])
                if effort > 0 and allocations:
                    while scenario.currentSlotIdx > lowerLimit and not scenario._isResourceAvailable(scenario.currentSlotIdx):
                        scenario.currentSlotIdx -= 1
                else:
                    while scenario.currentSlotIdx > lowerLimit and not scenario.isWorkingTime(scenario.currentSlotIdx):
                        scenario.currentSlotIdx -= 1
            else:
                # ALAP mode, end at project end
                scenario.currentSlotIdx = scenario.project.dateToIdx(scenario.project["end"]) - 1
                # Find the last working slot
                lowerLimit = scenario.project.dateToIdx(scenario.project["start"])
                if effort > 0 and allocations:
                    while scenario.currentSlotIdx > lowerLimit and not scenario._isResourceAvailable(scenario.currentSlotIdx):
                        scenario.currentSlotIdx -= 1
                else:
                    while scenario.currentSlotIdx > lowerLimit and not scenario.isWorkingTime(scenario.currentSlotIdx):
                        scenario.currentSlotIdx -= 1

    # For effort tasks with allocations, don't set start yet - it will be set
    # when first resource is booked. For non-effort tasks, find first working slot.
    # Exception: milestones happen at the exact dependency end time (no need for working slot)
    milestone = scenario.property.get("milestone", scenario.scenarioIdx)
    duration = scenario.property.get("duration", scenario.scenarioIdx) or 0
    length = scenario.property.get("length", scenario.scenarioIdx) or 0
    is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)
    if (
        forward
        and not scenario.property.get("start", scenario.scenarioIdx)
        and not is_milestone
        and (effort == 0 or not allocations)
    ):
        # Non-effort task: find first working slot and set start
        upperLimit = scenario.project.dateToIdx(scenario.project["end"])
        while scenario.currentSlotIdx < upperLimit and not scenario.isWorkingTime(scenario.currentSlotIdx):
            scenario.currentSlotIdx += 1
        scenario.property[("start", scenario.scenarioIdx)] = scenario.project.idxToDate(scenario.currentSlotIdx)
    # For effort tasks, start will be set in bookResources() on first booking

    # Record starting position for forward scheduling
    start_slot_idx = scenario.currentSlotIdx
    # For ALAP, track the first slot where we actually book (not just the constraint position)
    first_booked_slot = None

    delta = 1 if forward else -1
    lowerLimit = scenario.project.dateToIdx(scenario.project["start"])
    upperLimit = scenario.project.dateToIdx(scenario.project["end"])

    previous_effort = scenario.doneEffort
    while place_slot(scenario):
        # Track first booked slot for ALAP (when effort actually increases)
        if not forward and first_booked_slot is None and scenario.doneEffort > previous_effort:
            first_booked_slot = scenario.currentSlotIdx
        previous_effort = scenario.doneEffort

        scenario.currentSlotIdx += delta
        if scenario.currentSlotIdx < lowerLimit or scenario.currentSlotIdx > upperLimit:
            scenario.isRunAway = True
            return False

    # Set start/end dates based on scheduling direction
    if forward:
        # For forward scheduling: start is at the beginning, end is at current position
        if not scenario.property.get("start", scenario.scenarioIdx):
            scenario.property[("start", scenario.scenarioIdx)] = scenario.project.idxToDate(start_slot_idx)
    else:
        # For backward scheduling:
        # - first_booked_slot = the actual first slot where we booked (latest, near the end)
        # - currentSlotIdx = last slot scheduled (the earliest slot we booked)
        # The task starts at the beginning of currentSlotIdx
        # and ends after the first booked slot

        # Set start time (the earliest slot we worked in)
        # currentSlotIdx is the last (earliest) slot we booked
        actual_start = scenario.project.idxToDate(scenario.currentSlotIdx)
        if not scenario.property.get("start", scenario.scenarioIdx):
            scenario.property[("start", scenario.scenarioIdx)] = actual_start

        # Set end time
        # For ALAP, end is based on the actual first booking, not the constraint position
        # The constraint tells us when to end BY, but actual end is when work finishes
        # Use first_booked_slot if we actually booked something, else fall back to start_slot_idx
        end_slot = first_booked_slot if first_booked_slot is not None else start_slot_idx
        actual_end = scenario.project.idxToDate(end_slot + 1)
        # Work placed after another backward task in the same slot ends
        # where that task's work begins, not at the slot boundary.
        if scenario.workEnd is not None:
            actual_end = scenario.workEnd
        # For effort-based tasks, always use the calculated end (when work actually completes)
        # even if an explicit end constraint was specified (that's just the deadline, not the actual end)
        effort = scenario.property.get("effort", scenario.scenarioIdx) or 0
        if effort > 0 or not scenario.property.get("end", scenario.scenarioIdx):
            scenario.property[("end", scenario.scenarioIdx)] = actual_end

    scenario.scheduled = True
    scenario.property[("scheduled", scenario.scenarioIdx)] = True
    return True


def enter_at(scenario: Any, moment: datetime, forward: bool) -> int:
    """The slot to begin placing work in, given a moment that may fall inside one.

    The part of that slot on the wrong side of ``moment`` is kept out of this
    task's bookings: the part before it for forward work, the part after it
    for backward work. The offset is measured from the edge the work grows
    from and applies to that one slot only.
    """
    idx: int = scenario.project.dateToIdx(moment)
    slot_start = scenario.project.idxToDate(idx)
    into = (moment - slot_start).total_seconds() if slot_start is not None else 0.0
    scenario.slotStartOffset = 0.0
    scenario.slotStartOffsetSlot = None
    if into <= 0:
        return idx if forward else idx - 1
    scenario.slotStartOffset = into if forward else scenario._slotSeconds() - into
    scenario.slotStartOffsetSlot = idx
    return idx


def place_slot(scenario: Any) -> bool:
    # Determine duration type
    # :effortTask, :lengthTask, :durationTask, :startEndTask, or milestone

    # How much work the task represents does not change while it is being
    # placed, and place_slot runs once per slot, so it is read once per run.
    effort, length, duration, milestone = scenario.workSpecification()

    # We need state tracking for done effort/duration
    if not hasattr(scenario, "doneEffort"):
        scenario.doneEffort = 0
    if not hasattr(scenario, "doneDuration"):
        scenario.doneDuration = 0
    if not hasattr(scenario, "doneLength"):
        scenario.doneLength = 0

    forward = scenario.property.get("forward", scenario.scenarioIdx)

    # A task with no effort/duration/length is a milestone (zero duration task)
    # This includes tasks that only have dependencies but no work
    start_date = scenario.property.get("start", scenario.scenarioIdx)
    end_date = scenario.property.get("end", scenario.scenarioIdx)
    is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)

    if is_milestone:
        # Milestone: set end = start (zero duration)
        if forward:
            if start_date:
                scenario.property[("end", scenario.scenarioIdx)] = start_date
            else:
                # No start date - use current slot (set by dependency calculation),
                # at the moment inside it where the predecessor finished
                slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
                date = scenario.project.idxToDate(slot_idx)
                if slot_idx == scenario.slotStartOffsetSlot:
                    date = date + timedelta(seconds=round(scenario.slotStartOffset))
                scenario.property[("start", scenario.scenarioIdx)] = date
                scenario.property[("end", scenario.scenarioIdx)] = date
        else:
            if end_date:
                scenario.property[("start", scenario.scenarioIdx)] = end_date
            else:
                slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
                date = scenario.project.idxToDate(slot_idx)
                scenario.property[("start", scenario.scenarioIdx)] = date
                scenario.property[("end", scenario.scenarioIdx)] = date
        return False

    if effort > 0:
        # Check for contiguous flag - task cannot be split across breaks
        flags = scenario.property.get("flags", scenario.scenarioIdx) or []
        if "contiguous" in flags and scenario.doneEffort == 0 and not scenario._hasContiguousBlock(effort):
            # Skip this slot - no contiguous block starts here
            return True  # Continue to next slot

        # Store effort before booking to calculate fraction used in final slot
        effort_before = scenario.doneEffort
        scenario.bookResources()

        if scenario.doneEffort >= effort:
            # Finished - calculate precise end time within the final slot
            # and release unused time for other tasks
            end_date, _seconds_used = scenario._calculatePreciseEndTimeAndRelease(effort, effort_before, forward)
            assert end_date is not None
            propagate_date(scenario, end_date, forward)
            return False
    elif duration > 0:
        # duration is calendar time: every slot counts towards it, whether
        # or not anyone is working in it.
        scenario.bookResources()
        scenario.doneDuration += scenario._slotSeconds()
        if scenario.doneDuration >= duration:
            slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
            date = scenario.project.idxToDate(slot_idx + (1 if forward else 0))
            assert date is not None
            propagate_date(scenario, date, forward)
            return False
    elif length > 0:
        # length is working time: only slots inside the working calendar
        # count, so a length task stretches across weekends and holidays.
        scenario.bookResources()
        slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
        if scenario.isWorkingTime(slot_idx):
            scenario.doneLength += scenario._slotSeconds()
        if scenario.doneLength >= length:
            date = scenario.project.idxToDate(slot_idx + (1 if forward else 0))
            assert date is not None
            propagate_date(scenario, date, forward)
            return False
    else:
        # startEndTask - has both start and end dates explicitly set
        scenario.bookResources()
        # Check if reached end/start
        target_date = end_date if forward else start_date
        slot_idx = scenario.currentSlotIdx if scenario.currentSlotIdx is not None else 0
        if target_date and (
            (forward and slot_idx >= scenario.project.dateToIdx(target_date))
            or (not forward and slot_idx <= scenario.project.dateToIdx(target_date))
        ):
            return False

    return True


def propagate_date(scenario: Any, date: datetime, atEnd: bool) -> None:
    attr = "end" if atEnd else "start"
    scenario.property[(attr, scenario.scenarioIdx)] = date
    # Propagate to dependencies?


def finish_scheduling(scenario: Any) -> None:
    """
    Finish scheduling for this task.
    For container tasks, compute start/end from children.
    """
    # Children first: a container's dates come from theirs.
    for child in scenario.property.children:
        child_scenario = child.data[scenario.scenarioIdx] if child.data else None
        if child_scenario is not None:
            finish_scheduling(child_scenario)

    # For container tasks, set dates from children
    if not scenario.property.leaf():
        schedule_container(scenario)


def schedule_container(scenario: Any) -> None:
    """
    Compute and set start/end dates for a container task based on its children.
    """
    if scenario.scheduled or scenario.property.leaf():
        return

    n_start = None
    n_end = None

    for child in scenario.property.children:
        child_scenario = child.data[scenario.scenarioIdx] if child.data else None
        if not child_scenario:
            continue

        # Abort if a child has not been scheduled
        if not child.get("scheduled", scenario.scenarioIdx):
            return

        child_start = child.get("start", scenario.scenarioIdx)
        child_end = child.get("end", scenario.scenarioIdx)

        if child_start is None or child_end is None:
            return

        if n_start is None or child_start < n_start:
            n_start = child_start
        if n_end is None or child_end > n_end:
            n_end = child_end

    # Set the container dates
    current_start = scenario.property.get("start", scenario.scenarioIdx)
    current_end = scenario.property.get("end", scenario.scenarioIdx)

    if n_start and (current_start is None or current_start > n_start):
        scenario.property[("start", scenario.scenarioIdx)] = n_start

    if n_end and (current_end is None or current_end < n_end):
        scenario.property[("end", scenario.scenarioIdx)] = n_end

    if n_start and n_end:
        scenario.scheduled = True
        scenario.property[("scheduled", scenario.scenarioIdx)] = True
