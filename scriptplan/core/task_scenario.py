import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.property import AttributeBase
from scriptplan.core.scenario_data import ScenarioData

if TYPE_CHECKING:
    from scriptplan.core.property import PropertyTreeNode

# Default working hours: 9am-5pm (0-indexed: hours 9-16 are working)
DEFAULT_WORK_START_HOUR = 9
DEFAULT_WORK_END_HOUR = 17  # 5pm, so hours 9,10,11,12,13,14,15,16 are working (8 hours)


class TaskScenario(ScenarioData):
    def __init__(self, task: "PropertyTreeNode", scenarioIdx: int, attributes: dict[str, Any]) -> None:
        super().__init__(task, scenarioIdx, attributes)
        self.isRunAway: bool = False
        self.hasDurationSpec: bool = False
        self.scheduled: bool = False
        self.currentSlotIdx: Optional[int] = None
        self.doneDuration: int = 0
        self.doneLength: int = 0
        self.doneEffort: float = 0.0
        self.slotStartOffset: float = 0.0
        self._selectedResources: Optional[list[Any]] = None
        self._lastBookedResource: Optional[Any] = None
        self._lastBookedSlot: Optional[int] = None

        # Ensure required attributes exist
        required_attrs = [
            "allocate",
            "assignedresources",
            "booking",
            "charge",
            "chargeset",
            "complete",
            "competitors",
            "criticalness",
            "depends",
            "duration",
            "effort",
            "effortdone",
            "effortleft",
            "end",
            "forward",
            "gauge",
            "length",
            "maxend",
            "maxstart",
            "minend",
            "minstart",
            "milestone",
            "pathcriticalness",
            "precedes",
            "priority",
            "projectionmode",
            "responsible",
            "scheduled",
            "shifts",
            "start",
            "status",
        ]

        for attr in required_attrs:
            with contextlib.suppress(ValueError):
                _ = self.property[(attr, self.scenarioIdx)]

        if not self.property.parent:
            mode = AttributeBase.mode()
            AttributeBase.setMode(1)

            proj_scenario = self.project.scenario(self.scenarioIdx) if hasattr(self.project, "scenario") else None
            proj_projection = proj_scenario.get("projection") if proj_scenario else None
            if proj_projection:
                self.property[("projectionmode", self.scenarioIdx)] = proj_projection

            AttributeBase.setMode(mode)

    def prepareScheduling(self) -> None:
        """
        Reset all scheduling related data prior to scheduling.
        Called once per scenario before scheduling begins.
        """
        self.isRunAway = False
        self.currentSlotIdx = None
        self.doneDuration = 0
        self.doneLength = 0
        self.doneEffort = 0.0
        self.scheduled = False
        self._selectedResources = None  # Reset alternative resource selection

        # Track exact start time within a slot (for mid-slot dependency starts)
        # This is the number of seconds into the slot where we should start booking
        self.slotStartOffset = 0.0

        # Reset the counters of all limits of this task (not parent tasks).
        # This is critical - limits track usage per period and must be reset
        # before each scheduling run to avoid carrying over counts from
        # previous scenario scheduling.
        limits = self.property.get("limits", self.scenarioIdx)
        if limits:
            limits.reset()

    def getAllDependencies(self) -> list[Any]:
        """
        Get all dependencies including inherited ones from parent containers.

        In TaskJuggler, child tasks inherit dependencies from their parent
        containers. For example, if a container 'software' depends on 'spec',
        all children of 'software' (database, gui, backend) also depend on 'spec'.
        """
        all_deps: list[Any] = []

        # Get own dependencies
        own_deps = self.property.get("depends", self.scenarioIdx) or []
        all_deps.extend(own_deps)

        # Get parent dependencies (recursively up the tree)
        parent = self.property.parent
        while parent:
            parent_deps = parent.get("depends", self.scenarioIdx) or []
            all_deps.extend(parent_deps)
            parent = parent.parent

        return all_deps

    def readyForScheduling(self) -> bool:
        """
        Check if task is ready for scheduling.

        For ASAP (forward) scheduling: check if all dependencies are scheduled.
        For ALAP (backward) scheduling: check if all successors (tasks that depend on this)
        are scheduled, so we can use their start times as our end constraint.
        """
        forward = self.property.get("forward", self.scenarioIdx)

        if forward is False:
            # ALAP scheduling - check successors
            # A task is ready when all tasks that depend on it are scheduled
            # (so we know when this task must end)
            return self._alapReadyForScheduling()
        else:
            # ASAP scheduling - check dependencies
            return self._asapReadyForScheduling()

    def _asapReadyForScheduling(self) -> bool:
        """Check if all dependencies are scheduled (for ASAP mode)."""
        for dep in self.getAllDependencies():
            if isinstance(dep, dict):
                t = dep.get("task")
            elif hasattr(dep, "task"):
                t = dep.task
            else:
                t = dep

            if t and not t.get("scheduled", self.scenarioIdx):
                return False

        return True

    def _alapReadyForScheduling(self) -> bool:
        """
        Check if task is ready for ALAP scheduling.

        For ALAP, a task is ready when:
        1. It has an explicit end date (anchor), OR
        2. All tasks that depend on this task (successors) are scheduled
           (so we can derive our end from their start), OR
        3. For onstart dependencies: the predecessor must be scheduled first
           (so we can derive our end from their start)
        """
        # If task has explicit end date, it's an anchor - always ready
        if self.property.get("end", self.scenarioIdx):
            return True

        # Check onstart dependencies - we need predecessor scheduled to know their start
        # For ALAP with `depends X { onstart }`, this task's END depends on X's START
        for dep in self.getAllDependencies():
            if isinstance(dep, dict):
                onstart = dep.get("onstart", False)
                pred = dep.get("task")
            elif hasattr(dep, "task"):
                onstart = getattr(dep, "onstart", False)
                pred = dep.task
            else:
                onstart = False
                pred = dep

            if onstart and pred and not pred.get("scheduled", self.scenarioIdx):
                # Predecessor not scheduled yet - we can't derive our end
                return False

        # Check if all successors are scheduled (for finish-to-start deps)
        successors = self._getSuccessors()
        if not successors:
            # No successors and no explicit end - use project end as default
            # (unless we have onstart deps, which we checked above)
            return True

        return all(successor.get("scheduled", self.scenarioIdx) for successor in successors)

    def _getSuccessors(self) -> list[Any]:
        """
        Get all tasks that depend on this task (successors).

        These are tasks T where T's dependencies include this task.
        """
        successors = []
        for task in self.project.tasks:
            if not task.leaf():
                continue
            deps = task.get("depends", self.scenarioIdx) or []
            for dep in deps:
                if isinstance(dep, dict):
                    pred = dep.get("task")
                elif hasattr(dep, "task"):
                    pred = dep.task
                else:
                    pred = dep

                if pred is self.property:
                    successors.append(task)
                    break

        return successors

    def _getSuccessorsWithMaxGap(self) -> list[tuple[Any, Any, Any]]:
        """
        Get successors that have maxgapduration constraint on this task.

        Returns list of (task, maxgapduration, gapduration) tuples.
        """
        result = []
        for task in self.project.tasks:
            if not task.leaf():
                continue
            deps = task.get("depends", self.scenarioIdx) or []
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

                if pred is self.property and maxgap:
                    result.append((task, maxgap, gap))
                    break
        return result

    def _getSuccessorEarliestStart(self, successor: Any) -> datetime:
        """
        Find the earliest time a successor task can start based on its resource availability.

        Returns datetime of earliest available slot.
        """

        # Get successor's allocations
        allocations = successor.get("allocate", self.scenarioIdx)
        if not allocations:
            # No allocations - use project working time
            start_idx = self.project.dateToIdx(self.project["start"])
            end_idx = self.project.dateToIdx(self.project["end"])
            for idx in range(start_idx, end_idx):
                if self.project.isWorkingTime(idx):
                    result = self.project.idxToDate(idx)
                    if result is not None:
                        result_dt: datetime = result
                        return result_dt
            result_end: datetime = self.project["end"]
            return result_end

        # Normalize allocations
        alloc_data = allocations
        if isinstance(allocations, list) and len(allocations) == 1 and isinstance(allocations[0], dict):
            alloc_data = allocations[0]

        if isinstance(alloc_data, dict):
            resource_ids = alloc_data.get("resources", [])
        elif isinstance(alloc_data, list):
            resource_ids = alloc_data
        else:
            resource_ids = [alloc_data]

        # Get the primary resource
        resource = None
        for res_id in resource_ids:
            resource = self._resolve_resource(res_id)
            if resource:
                break

        if not resource:
            result_start_1: datetime = self.project["start"]
            return result_start_1

        # Get resource's scenario data
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            result_start_2: datetime = self.project["start"]
            return result_start_2

        # Initialize scoreboard if needed
        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        # Find earliest slot where resource is on shift
        start_idx = self.project.dateToIdx(self.project["start"])
        end_idx = self.project.dateToIdx(self.project["end"])
        for idx in range(start_idx, end_idx):
            if res_scenario.onShift(idx):
                result = self.project.idxToDate(idx)
                if result is not None:
                    result_shift: datetime = result
                    return result_shift

        result_end_2: datetime = self.project["end"]
        return result_end_2

    def _computeMaxGapDelayedStart(self, earliest_start: datetime, effort: float) -> datetime:
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
        from datetime import timedelta

        successors_with_maxgap = self._getSuccessorsWithMaxGap()
        if not successors_with_maxgap:
            return earliest_start

        delayed_start = earliest_start

        for successor, maxgap_str, gap_str in successors_with_maxgap:
            # Find when successor can start
            successor_earliest = self._getSuccessorEarliestStart(successor)

            # Parse maxgapduration
            self._parse_duration(maxgap_str)
            gap_hours = self._parse_duration(gap_str) if gap_str else 0

            # This task must end no more than maxgap_hours before successor can start
            # Required end time: successor_earliest - gap_hours (to satisfy gapduration)
            # But end time must be >= successor_earliest - maxgap_hours (to satisfy maxgapduration)
            # So we want end time between (successor_earliest - maxgap_hours) and (successor_earliest - gap_hours)
            # Ideally, end exactly at successor_earliest - gap_hours to minimize gap

            desired_end = successor_earliest - timedelta(hours=gap_hours)

            # Work backwards from desired_end to find required start
            # For effort-based tasks, we need 'effort' hours of work before desired_end
            if effort > 0:
                required_start = self._computeStartFromEnd(desired_end, effort)
                if required_start > delayed_start:
                    delayed_start = required_start

        return delayed_start

    def _computeStartFromEnd(self, end_time: datetime, effort: float) -> datetime:
        """
        Given an end time and required effort, compute when to start.

        Walks backwards from end_time counting working hours until effort is met.

        Args:
            end_time: Desired end time (datetime)
            effort: Required effort in hours

        Returns:
            Required start time (datetime)
        """

        # Get allocations to determine resource working hours
        allocations = self.property.get("allocate", self.scenarioIdx)

        # Normalize allocations
        alloc_data = allocations
        if allocations and isinstance(allocations, list) and len(allocations) == 1 and isinstance(allocations[0], dict):
            alloc_data = allocations[0]

        resource = None
        if alloc_data:
            if isinstance(alloc_data, dict):
                resource_ids = alloc_data.get("resources", [])
            elif isinstance(alloc_data, list):
                resource_ids = alloc_data
            else:
                resource_ids = [alloc_data]

            for res_id in resource_ids:
                resource = self._resolve_resource(res_id)
                if resource:
                    break

        end_idx = self.project.dateToIdx(end_time)
        start_idx = self.project.dateToIdx(self.project["start"])

        # Count backwards from end_idx
        working_slots = 0
        current_idx = end_idx - 1  # Start from slot before end

        while current_idx >= start_idx and working_slots < effort:
            if resource:
                res_scenario = resource.data[self.scenarioIdx] if resource.data else None
                if res_scenario:
                    if res_scenario.scoreboard is None:
                        res_scenario.prepareScheduling()
                    if res_scenario.onShift(current_idx):
                        working_slots += 1
                else:
                    if self.project.isWorkingTime(current_idx):
                        working_slots += 1
            else:
                if self.project.isWorkingTime(current_idx):
                    working_slots += 1
            current_idx -= 1

        result = self.project.idxToDate(current_idx + 1)
        assert result is not None
        result_dt_4: datetime = result
        return result_dt_4

    def schedule(self) -> bool:
        if self.scheduled:
            return True

        # Determine start slot
        forward = self.property.get("forward", self.scenarioIdx)
        effort = self.property.get("effort", self.scenarioIdx) or 0
        allocations = self.property.get("allocate", self.scenarioIdx)

        if self.currentSlotIdx is None:
            if forward:
                start_date = self.property.get("start", self.scenarioIdx)
                if start_date:
                    self.currentSlotIdx = self.project.dateToIdx(start_date)
                else:
                    # ASAP mode, start at project start or after dependencies
                    # Check ALL dependencies (including inherited) to find the earliest start
                    earliest_start = self.project["start"]
                    for dep in self.getAllDependencies():
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
                        dep_time = t.get("start", self.scenarioIdx) if onstart else t.get("end", self.scenarioIdx)
                        if dep_time:
                            # Add gap if specified
                            if gapduration:
                                # gapduration is calendar time (e.g., "4h" = 4 hours)
                                gap_hours = self._parse_duration(gapduration)
                                from datetime import timedelta

                                dep_time = dep_time + timedelta(hours=gap_hours)
                            elif gaplength:
                                # gaplength is working time - need to find next working slot after gap
                                gap_hours = self._parse_duration(gaplength)
                                gap_slots = int(gap_hours)  # Each slot is 1 hour
                                dep_time_idx = self.project.dateToIdx(dep_time)
                                # Skip gap_slots of working time
                                working_slots = 0
                                while working_slots < gap_slots:
                                    if self.isWorkingTime(dep_time_idx):
                                        working_slots += 1
                                    dep_time_idx += 1
                                dep_time = self.project.idxToDate(dep_time_idx)
                            if dep_time > earliest_start:
                                earliest_start = dep_time

                    # Check for maxgapduration constraints from successors
                    # If a successor has maxgapduration, we may need to delay our start
                    # so that we end close enough for the successor to meet the constraint
                    if effort > 0:
                        delayed_start = self._computeMaxGapDelayedStart(earliest_start, effort)
                        if delayed_start > earliest_start:
                            earliest_start = delayed_start

                    # Convert earliest_start to slot index
                    # If earliest_start is mid-slot, track the offset so we don't
                    # book time that overlaps with the predecessor
                    slot_idx = self.project.dateToIdx(earliest_start)
                    slot_start = self.project.idxToDate(slot_idx)
                    if earliest_start > slot_start:
                        # earliest_start is mid-slot - calculate offset in seconds
                        offset_seconds = (earliest_start - slot_start).total_seconds()
                        self.slotStartOffset = offset_seconds
                    else:
                        self.slotStartOffset = 0.0
                    self.currentSlotIdx = slot_idx
            else:
                # ALAP (backward) scheduling
                end_date = self.property.get("end", self.scenarioIdx)

                if not end_date:
                    # No explicit end - derive from:
                    # 1. Predecessors with onstart deps (our END <= their START)
                    # 2. Successors (tasks depending on this - our END <= their START)
                    latest_end = self.project["end"]  # Default to project end

                    # Check onstart dependencies - our END must be before predecessor's START
                    # with gapduration subtracted if specified
                    for dep in self.getAllDependencies():
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
                            pred_start = pred.get("start", self.scenarioIdx)
                            if pred_start:
                                # Apply gapduration - A must end (gapduration) before B starts
                                if gapduration:
                                    gap_hours = self._parse_duration(gapduration)
                                    from datetime import timedelta

                                    pred_start = pred_start - timedelta(hours=gap_hours)
                                if pred_start < latest_end:
                                    latest_end = pred_start

                    # Also check successors (finish-to-start deps)
                    successors = self._getSuccessors()
                    for successor in successors:
                        succ_start = successor.get("start", self.scenarioIdx)
                        if succ_start and succ_start < latest_end:
                            latest_end = succ_start

                    end_date = latest_end

                if end_date:
                    # For ALAP, start from the last working slot BEFORE the end date
                    self.currentSlotIdx = self.project.dateToIdx(end_date) - 1
                    # Find the last working slot
                    # For effort tasks with allocations, check resource availability
                    # (respects resource timezone and working hours)
                    lowerLimit = self.project.dateToIdx(self.project["start"])
                    if effort > 0 and allocations:
                        while self.currentSlotIdx > lowerLimit and not self._isResourceAvailable(self.currentSlotIdx):
                            self.currentSlotIdx -= 1
                    else:
                        while self.currentSlotIdx > lowerLimit and not self.isWorkingTime(self.currentSlotIdx):
                            self.currentSlotIdx -= 1
                else:
                    # ALAP mode, end at project end
                    self.currentSlotIdx = self.project.dateToIdx(self.project["end"]) - 1
                    # Find the last working slot
                    lowerLimit = self.project.dateToIdx(self.project["start"])
                    if effort > 0 and allocations:
                        while self.currentSlotIdx > lowerLimit and not self._isResourceAvailable(self.currentSlotIdx):
                            self.currentSlotIdx -= 1
                    else:
                        while self.currentSlotIdx > lowerLimit and not self.isWorkingTime(self.currentSlotIdx):
                            self.currentSlotIdx -= 1

        # For effort tasks with allocations, don't set start yet - it will be set
        # when first resource is booked. For non-effort tasks, find first working slot.
        # Exception: milestones happen at the exact dependency end time (no need for working slot)
        milestone = self.property.get("milestone", self.scenarioIdx)
        duration = self.property.get("duration", self.scenarioIdx) or 0
        length = self.property.get("length", self.scenarioIdx) or 0
        is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)
        if (
            forward
            and not self.property.get("start", self.scenarioIdx)
            and not is_milestone
            and (effort == 0 or not allocations)
        ):
            # Non-effort task: find first working slot and set start
            upperLimit = self.project.dateToIdx(self.project["end"])
            while self.currentSlotIdx < upperLimit and not self.isWorkingTime(self.currentSlotIdx):
                self.currentSlotIdx += 1
            self.property[("start", self.scenarioIdx)] = self.project.idxToDate(self.currentSlotIdx)
        # For effort tasks, start will be set in bookResources() on first booking

        # Record starting position for forward scheduling
        start_slot_idx = self.currentSlotIdx
        # For ALAP, track the first slot where we actually book (not just the constraint position)
        first_booked_slot = None

        delta = 1 if forward else -1
        lowerLimit = self.project.dateToIdx(self.project["start"])
        upperLimit = self.project.dateToIdx(self.project["end"])

        previous_effort = self.doneEffort
        while self.scheduleSlot():
            # Track first booked slot for ALAP (when effort actually increases)
            if not forward and first_booked_slot is None and self.doneEffort > previous_effort:
                first_booked_slot = self.currentSlotIdx
            previous_effort = self.doneEffort

            self.currentSlotIdx += delta
            if self.currentSlotIdx < lowerLimit or self.currentSlotIdx > upperLimit:
                self.isRunAway = True
                return False

        # Set start/end dates based on scheduling direction
        if forward:
            # For forward scheduling: start is at the beginning, end is at current position
            if not self.property.get("start", self.scenarioIdx):
                self.property[("start", self.scenarioIdx)] = self.project.idxToDate(start_slot_idx)
        else:
            # For backward scheduling:
            # - first_booked_slot = the actual first slot where we booked (latest, near the end)
            # - currentSlotIdx = last slot scheduled (the earliest slot we booked)
            # The task starts at the beginning of currentSlotIdx
            # and ends after the first booked slot

            # Set start time (the earliest slot we worked in)
            # currentSlotIdx is the last (earliest) slot we booked
            actual_start = self.project.idxToDate(self.currentSlotIdx)
            if not self.property.get("start", self.scenarioIdx):
                self.property[("start", self.scenarioIdx)] = actual_start

            # Set end time
            # For ALAP, end is based on the actual first booking, not the constraint position
            # The constraint tells us when to end BY, but actual end is when work finishes
            # Use first_booked_slot if we actually booked something, else fall back to start_slot_idx
            end_slot = first_booked_slot if first_booked_slot is not None else start_slot_idx
            actual_end = self.project.idxToDate(end_slot + 1)
            # For effort-based tasks, always use the calculated end (when work actually completes)
            # even if an explicit end constraint was specified (that's just the deadline, not the actual end)
            effort = self.property.get("effort", self.scenarioIdx) or 0
            if effort > 0 or not self.property.get("end", self.scenarioIdx):
                self.property[("end", self.scenarioIdx)] = actual_end

        self.scheduled = True
        self.property[("scheduled", self.scenarioIdx)] = True
        return True

    def scheduleSlot(self) -> bool:
        # Determine duration type
        # :effortTask, :lengthTask, :durationTask, :startEndTask, or milestone

        effort = self.property.get("effort", self.scenarioIdx) or 0
        length = self.property.get("length", self.scenarioIdx) or 0
        duration = self.property.get("duration", self.scenarioIdx) or 0
        milestone = self.property.get("milestone", self.scenarioIdx)

        # We need state tracking for done effort/duration
        if not hasattr(self, "doneEffort"):
            self.doneEffort = 0
        if not hasattr(self, "doneDuration"):
            self.doneDuration = 0
        if not hasattr(self, "doneLength"):
            self.doneLength = 0

        forward = self.property.get("forward", self.scenarioIdx)

        # A task with no effort/duration/length is a milestone (zero duration task)
        # This includes tasks that only have dependencies but no work
        start_date = self.property.get("start", self.scenarioIdx)
        end_date = self.property.get("end", self.scenarioIdx)
        is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)

        if is_milestone:
            # Milestone: set end = start (zero duration)
            if forward:
                if start_date:
                    self.property[("end", self.scenarioIdx)] = start_date
                else:
                    # No start date - use current slot (set by dependency calculation)
                    slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
                    date = self.project.idxToDate(slot_idx)
                    self.property[("start", self.scenarioIdx)] = date
                    self.property[("end", self.scenarioIdx)] = date
            else:
                if end_date:
                    self.property[("start", self.scenarioIdx)] = end_date
                else:
                    slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
                    date = self.project.idxToDate(slot_idx)
                    self.property[("start", self.scenarioIdx)] = date
                    self.property[("end", self.scenarioIdx)] = date
            return False

        if effort > 0:
            # Check for contiguous flag - task cannot be split across breaks
            flags = self.property.get("flags", self.scenarioIdx) or []
            if "contiguous" in flags and self.doneEffort == 0 and not self._hasContiguousBlock(effort):
                # Skip this slot - no contiguous block starts here
                return True  # Continue to next slot

            # Store effort before booking to calculate fraction used in final slot
            effort_before = self.doneEffort
            self.bookResources()

            if self.doneEffort >= effort:
                # Finished - calculate precise end time within the final slot
                # and release unused time for other tasks
                end_date, _seconds_used = self._calculatePreciseEndTimeAndRelease(effort, effort_before, forward)
                assert end_date is not None
                self.propagateDate(end_date, forward)
                return False
        elif duration > 0:
            self.bookResources()  # Even if just duration, might use resources?
            self.doneDuration += 1
            if self.doneDuration >= duration:
                slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
                date = self.project.idxToDate(slot_idx + (1 if forward else 0))
                assert date is not None
                self.propagateDate(date, forward)
                return False
        else:
            # startEndTask - has both start and end dates explicitly set
            self.bookResources()
            # Check if reached end/start
            target_date = end_date if forward else start_date
            slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
            if target_date and (
                (forward and slot_idx >= self.project.dateToIdx(target_date))
                or (not forward and slot_idx <= self.project.dateToIdx(target_date))
            ):
                return False

        return True

    def _calculatePreciseEndTimeAndRelease(
        self, required_effort: float, effort_before_slot: float, forward: bool
    ) -> tuple[datetime, float]:
        """
        Calculate the precise end time within the final slot and release unused time.

        When a task completes within a slot, we need to determine exactly when
        within that slot the required effort was reached, rather than rounding
        to slot boundaries. The unused portion of the slot is released back to
        the resource for other tasks to use.

        Args:
            required_effort: Total effort required for the task (hours)
            effort_before_slot: Effort accumulated before the current slot (hours)
            forward: True for forward scheduling, False for backward

        Returns:
            tuple: (precise_end_datetime, seconds_used_in_slot)
        """
        from datetime import timedelta

        # Get slot parameters
        slot_duration_seconds = self.project.attributes.get("scheduleGranularity", 3600)
        slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
        slot_start = self.project.idxToDate(slot_idx)

        # Get the resource and its efficiency for this slot
        resource = getattr(self, "_lastBookedResource", None)
        efficiency = 1.0
        if resource:
            eff = resource.get("efficiency", self.scenarioIdx)
            if eff is not None:
                efficiency = eff
        else:
            # Fallback to allocations
            allocations = self.property.get("allocate", self.scenarioIdx) or []
            for alloc in allocations:
                if isinstance(alloc, str):
                    for res in self.project.resources:
                        if res.id == alloc:
                            resource = res
                            break
                else:
                    resource = alloc
                if resource:
                    eff = resource.get("efficiency", self.scenarioIdx)
                    if eff is not None:
                        efficiency = eff
                    break

        # Calculate effort gained per second in this slot
        slot_duration_hours = slot_duration_seconds / 3600.0
        effort_per_slot = slot_duration_hours * efficiency
        effort_per_second = effort_per_slot / slot_duration_seconds

        # How much effort was needed in this final slot?
        effort_needed_in_slot = required_effort - effort_before_slot

        # How many seconds into the slot does that take?
        if effort_per_second > 0:
            seconds_into_slot = effort_needed_in_slot / effort_per_second
        else:
            seconds_into_slot = slot_duration_seconds

        # Clamp to slot duration (shouldn't exceed, but safety check)
        seconds_into_slot = min(seconds_into_slot, slot_duration_seconds)

        # Calculate the precise end time, rounded to nearest second
        # (Gold standard uses second-level precision)
        seconds_rounded = round(seconds_into_slot)

        if forward:
            # For forward scheduling, end time is offset from slot start
            if slot_start is not None:
                precise_end = slot_start + timedelta(seconds=seconds_rounded)
            else:
                precise_end = self.project["start"] + timedelta(seconds=seconds_rounded)
        else:
            # For backward scheduling, we're calculating the START time
            # The start is at the END of the slot minus unused time
            # If we used the whole slot, start is at slot_start
            # If we used part of it, start is later in the slot
            if slot_start is not None:
                slot_end = slot_start + timedelta(seconds=slot_duration_seconds)
                precise_end = slot_end - timedelta(seconds=seconds_rounded)
            else:
                precise_end = self.project["start"]

        # Release unused portion of the slot back to the resource
        seconds_unused = slot_duration_seconds - seconds_into_slot
        if seconds_unused > 0 and resource:
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario:
                # Update the per-task usage record to reflect actual usage
                if self.currentSlotIdx in res_scenario.slotTaskUsage:
                    # Find and update this task's entry
                    for i, (task, _secs) in enumerate(res_scenario.slotTaskUsage[self.currentSlotIdx]):
                        if task == self.property:
                            res_scenario.slotTaskUsage[self.currentSlotIdx][i] = (task, seconds_into_slot)
                            break

                # Update total slotSecondsUsed to release unused time
                # Old value was full slot duration, new value is actual usage
                old_total = res_scenario.slotSecondsUsed.get(self.currentSlotIdx, slot_duration_seconds)
                # Subtract what was previously booked (full slot) and add actual usage
                res_scenario.slotSecondsUsed[self.currentSlotIdx] = (
                    old_total - slot_duration_seconds + seconds_into_slot
                )

        return precise_end, seconds_into_slot

    def _calculatePreciseEndTime(self, required_effort: float, effort_before_slot: float, forward: bool) -> datetime:
        """
        Calculate the precise end time within the final slot based on fractional effort.
        (Legacy method - calls the new implementation)
        """
        end_time, _ = self._calculatePreciseEndTimeAndRelease(required_effort, effort_before_slot, forward)
        return end_time

    def _parse_duration(self, duration_str: Any) -> float:
        """
        Parse a duration string like '4h', '2d', '1w', '30min' into hours.
        """
        if not duration_str:
            return 0
        import re

        # Match formats: 29min, 4h, 2d, 1w, 3m (months), 1y
        match = re.match(r"(\d+(?:\.\d+)?)\s*(min|h|d|w|m|y)?", str(duration_str).lower())
        if not match:
            return 0
        num = float(match.group(1))
        unit = match.group(2) or "h"
        multipliers = {"min": 1 / 60, "h": 1, "d": 8, "w": 40, "m": 160, "y": 1920}
        return num * multipliers.get(unit, 1)

    def isWorkingTime(self, slotIdx: int) -> bool:
        """
        Check if a slot index falls within working hours.

        Delegates to project.isWorkingTime which checks:
        - Weekday (Mon-Fri)
        - Working hours (9am-5pm default)
        - Global vacations
        - Shift-specific schedules

        Returns True if the slot is during working time.
        """
        result: bool = self.project.isWorkingTime(slotIdx)
        return result

    def _isResourceAvailable(self, slotIdx: int) -> bool:
        """
        Check if any allocated resource is available at the given slot.

        For effort-based tasks with allocations, this checks the actual resource
        availability (considering their timezone and working hours) rather than
        the project's default working hours.

        Args:
            slotIdx: Scoreboard index to check

        Returns:
            True if at least one allocated resource is available
        """
        allocations = self.property.get("allocate", self.scenarioIdx)
        if not allocations:
            # No allocations - fall back to project working time
            result: bool = self.project.isWorkingTime(slotIdx)
            return result

        # Parse allocations - handle both simple list and dict with alternatives
        resource_ids = []

        # Normalize allocations
        alloc_data = allocations
        if isinstance(allocations, list) and len(allocations) == 1 and isinstance(allocations[0], dict):
            alloc_data = allocations[0]

        if isinstance(alloc_data, dict):
            resource_ids = alloc_data.get("resources", [])
            # Also include alternatives
            alternatives = alloc_data.get("options", {}).get("alternative", [])
            resource_ids = resource_ids + alternatives
        elif isinstance(alloc_data, list):
            resource_ids = alloc_data
        else:
            resource_ids = [alloc_data]

        # Check each allocated resource
        for alloc in resource_ids:
            resource = self._resolve_resource(alloc)
            if resource is None:
                continue

            # Get resource's scenario data
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario is None:
                continue

            # Initialize scoreboard if needed
            if res_scenario.scoreboard is None:
                res_scenario.prepareScheduling()

            # Check if resource is on shift at this slot
            if res_scenario.onShift(slotIdx):
                return True

        return False

    def _hasContiguousBlock(self, effort: float) -> bool:
        """
        Check if there's a contiguous block of working time starting from current slot
        that can fit the required effort.

        For contiguous (atomic) tasks, we need to ensure the task won't be split
        across breaks (like lunch breaks). The entire effort must fit in one
        continuous working period.

        Args:
            effort: Required effort in hours

        Returns:
            True if a contiguous block large enough exists starting at current slot
        """

        # Get allocations to check resource availability
        allocations = self.property.get("allocate", self.scenarioIdx)
        if not allocations:
            # No allocations - check project working time
            return self._checkProjectContiguousBlock(effort)

        # Normalize allocations
        alloc_data = allocations
        if isinstance(allocations, list) and len(allocations) == 1 and isinstance(allocations[0], dict):
            alloc_data = allocations[0]

        if isinstance(alloc_data, dict):
            resource_ids = alloc_data.get("resources", [])
        elif isinstance(alloc_data, list):
            resource_ids = alloc_data
        else:
            resource_ids = [alloc_data]

        # Get the first resource (for contiguous check, we use primary resource's availability)
        resource = None
        for res_id in resource_ids:
            resource = self._resolve_resource(res_id)
            if resource:
                break

        if not resource:
            return self._checkProjectContiguousBlock(effort)

        # Get resource's scenario data
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            return self._checkProjectContiguousBlock(effort)

        # Initialize scoreboard if needed
        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        # Get efficiency
        efficiency = resource.get("efficiency", self.scenarioIdx) or 1.0

        # Calculate required duration (hours of actual clock time)
        required_duration = effort / efficiency

        # Get slot duration in hours
        slot_duration_sec = self.project.attributes.get("scheduleGranularity", 3600)
        slot_duration_hours = slot_duration_sec / 3600.0

        # Calculate how many consecutive slots we need
        slots_needed = required_duration / slot_duration_hours

        # Check if we have that many consecutive working slots starting from current
        consecutive_count = 0
        current_slot = self.currentSlotIdx if self.currentSlotIdx is not None else 0
        max_slots = len(res_scenario.scoreboard) if res_scenario.scoreboard else 1000

        while current_slot < max_slots and consecutive_count < slots_needed:
            if res_scenario.available(current_slot):
                if consecutive_count == 0 and current_slot != self.currentSlotIdx:
                    # Gap before first available - not contiguous from current
                    return False
                consecutive_count += 1
                current_slot += 1
            else:
                # Hit a break/unavailable slot
                if consecutive_count > 0:
                    # Already started counting but hit a break - not enough contiguous
                    return False
                else:
                    # Haven't found starting slot yet - not available at current
                    return False

        result_bool: bool = consecutive_count >= slots_needed
        return result_bool

    def _checkProjectContiguousBlock(self, effort: float) -> bool:
        """
        Fallback check for contiguous block using project working time.
        """
        slot_duration_sec = self.project.attributes.get("scheduleGranularity", 3600)
        slot_duration_hours = slot_duration_sec / 3600.0
        slots_needed = effort / slot_duration_hours

        consecutive_count = 0
        current_slot = self.currentSlotIdx if self.currentSlotIdx is not None else 0
        max_slots = 1000

        while current_slot < max_slots and consecutive_count < slots_needed:
            if self.project.isWorkingTime(current_slot):
                if consecutive_count == 0 and current_slot != self.currentSlotIdx:
                    return False
                consecutive_count += 1
                current_slot += 1
            else:
                if consecutive_count > 0:
                    return False
                else:
                    return False

        result_bool: bool = consecutive_count >= slots_needed
        return result_bool

    def _resolve_resource(self, alloc: Any) -> Optional[Any]:
        """
        Resolve a resource allocation to an actual Resource object.

        Args:
            alloc: Either a resource ID string or a Resource object

        Returns:
            The Resource object or None if not found
        """
        if isinstance(alloc, str):
            # Try indexed lookup first
            resource = self.project.resources.get(alloc) if hasattr(self.project.resources, "get") else None
            if resource is None:
                # Fall back to iteration
                for res in self.project.resources:
                    if res.id == alloc:
                        return res
            return resource
        return alloc

    def _selectBestResources(
        self, primary_resources: list[Any], alternative_resources: list[Any], effort: float
    ) -> list[Any]:
        """
        Select the best resources for this task using smart routing.

        For tasks with alternatives, this compares completion times:
        - Path A: Wait for primary resource to become available
        - Path B: Start now with alternative resource

        The path that finishes earlier wins.

        Args:
            primary_resources: List of primary (preferred) resources
            alternative_resources: List of alternative (fallback) resources
            effort: Required effort in hours

        Returns:
            List of resources to book
        """
        if not primary_resources and not alternative_resources:
            return []

        # If no alternatives, use primary resources
        if not alternative_resources:
            return primary_resources

        # If no primaries, use alternatives
        if not primary_resources:
            return alternative_resources

        # Smart routing: compare completion times
        # Calculate when each path would complete the task

        primary_end = self._estimateCompletionTime(primary_resources, effort)
        alternative_end = self._estimateCompletionTime(alternative_resources, effort)

        # Choose the path that finishes earlier
        if alternative_end is not None and (primary_end is None or alternative_end < primary_end):
            # Store which resource was selected for reporting
            if not hasattr(self, "_selectedAlternative"):
                self._selectedAlternative = True
            return alternative_resources
        else:
            if not hasattr(self, "_selectedAlternative"):
                self._selectedAlternative = False
            return primary_resources

    def _estimateCompletionTime(self, resources: list[Any], effort: float) -> Optional[datetime]:
        """
        Estimate when a task would complete using the given resources.

        Args:
            resources: List of resources to use
            effort: Required effort in hours

        Returns:
            Estimated completion datetime or None if cannot complete
        """
        if not resources or effort <= 0:
            return None

        from datetime import timedelta

        # Get efficiency (use first resource's efficiency)
        resource = resources[0]
        efficiency = resource.get("efficiency", self.scenarioIdx) or 1.0

        # Duration = effort / efficiency
        effort / efficiency

        # Find the first available slot for this resource
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            return None

        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        # Simulate scheduling to find completion time
        slot_duration = self.project.attributes.get("scheduleGranularity", 3600)
        effort_per_slot = (slot_duration / 3600.0) * efficiency

        remaining_effort = effort
        current_slot = self.currentSlotIdx if self.currentSlotIdx is not None else 0

        # Safety limit to prevent infinite loops
        max_slots = len(res_scenario.scoreboard) if res_scenario.scoreboard else 1000

        while remaining_effort > 0 and current_slot < max_slots:
            if res_scenario.available(current_slot):
                remaining_effort -= effort_per_slot
            current_slot += 1

        if remaining_effort > 0:
            return None  # Cannot complete within project timeframe

        # Calculate the end time
        # current_slot is now one past the last booked slot
        end_slot = current_slot - 1
        end_date_result = self.project.idxToDate(end_slot)
        if end_date_result is not None:
            result: Optional[datetime] = end_date_result + timedelta(seconds=slot_duration)
            return result
        else:
            return None

    def bookResources(self) -> None:
        """
        Book resources for the current slot and accumulate effort.

        This method attempts to book allocated resources for the current time slot.
        For effort-based tasks with multiple allocations, ALL resources must be
        available before any are booked (they work together as a team).

        For continuous time scheduling, effort is tracked based on actual available
        time in slots (accounting for partial slot usage by other tasks).

        Supports alternative resources: if primary is unavailable, tries alternatives.
        Smart routing picks the resource that finishes the task earliest.
        """
        # Get allocations
        allocations = self.property.get("allocate", self.scenarioIdx)
        if not allocations:
            return

        effort = self.property.get("effort", self.scenarioIdx) or 0

        # Parse allocations - handle both simple list and dict with alternatives
        primary_resources = []
        alternative_resources = []

        # Normalize allocations - can be list of strings, list containing dict, or dict
        alloc_data = allocations
        if isinstance(allocations, list) and len(allocations) == 1 and isinstance(allocations[0], dict):
            # List containing a single dict with options
            alloc_data = allocations[0]

        if isinstance(alloc_data, dict):
            # New format with options: {'resources': [...], 'options': {...}}
            resource_ids = alloc_data.get("resources", [])
            options = alloc_data.get("options", {})
            alternative_ids = options.get("alternative", [])

            for res_id in resource_ids:
                resource = self._resolve_resource(res_id)
                if resource:
                    primary_resources.append(resource)

            for res_id in alternative_ids:
                resource = self._resolve_resource(res_id)
                if resource:
                    alternative_resources.append(resource)
        elif isinstance(alloc_data, list):
            # Simple list format
            for alloc in alloc_data:
                resource = self._resolve_resource(alloc)
                if resource:
                    primary_resources.append(resource)
        else:
            # Single resource
            resource = self._resolve_resource(alloc_data)
            if resource:
                primary_resources.append(resource)

        # Determine which resources to try booking
        # Smart routing: pick the resource that can complete the task earliest
        # Only select once at the beginning of scheduling (when no effort done yet)
        if not hasattr(self, "_selectedResources") or self._selectedResources is None:
            self._selectedResources = self._selectBestResources(primary_resources, alternative_resources, effort)
        resources_to_book = self._selectedResources

        if not resources_to_book:
            return

        # For effort-based tasks with multiple resources, ALL must be available
        # (they work together as a team - can't progress if any member is unavailable)
        if effort > 0 and len(resources_to_book) > 1:
            all_available = True
            for resource in resources_to_book:
                res_scenario = resource.data[self.scenarioIdx] if resource.data else None
                if res_scenario is None:
                    all_available = False
                    break
                if res_scenario.scoreboard is None:
                    res_scenario.prepareScheduling()
                slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
                if not res_scenario.available(slot_idx):
                    all_available = False
                    break
                # Also check task limits
                if not self.limitsOk(slot_idx, resource):
                    all_available = False
                    break

            if not all_available:
                # Can't book - one or more resources unavailable
                return

        # Now book all resources (or single resource for non-team tasks)
        booked_any = False
        total_effort_this_slot = 0.0
        for resource in resources_to_book:
            effort_gained = self.bookResource(resource)
            if effort_gained > 0:
                booked_any = True
                # Track maximum effort from any single resource (not sum)
                # For multi-resource effort tasks, we count clock time not person-hours
                total_effort_this_slot = max(total_effort_this_slot, effort_gained)

                # Store the resource and slot for potential partial release later
                if not hasattr(self, "_lastBookedResource"):
                    self._lastBookedResource = None
                    self._lastBookedSlot = None
                self._lastBookedResource = resource
                self._lastBookedSlot = self.currentSlotIdx

        if booked_any:
            # For effort-based tasks, set start date on first booking
            if effort > 0 and self.doneEffort == 0:
                forward = self.property.get("forward", self.scenarioIdx)
                if forward:
                    # Use exact start time (including mid-slot offset from dependency)
                    from datetime import timedelta

                    slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
                    start_date = self.project.idxToDate(slot_idx)
                    if start_date is not None and hasattr(self, "slotStartOffset") and self.slotStartOffset > 0:
                        start_date = start_date + timedelta(seconds=self.slotStartOffset)
                    self.property[("start", self.scenarioIdx)] = start_date

            # Accumulate effort (counted once per slot, not per resource)
            self.doneEffort += total_effort_this_slot

    def getAllLimits(self) -> list[Any]:
        """
        Collect limits from this task and all parent tasks.
        Returns a list of Limits objects.
        """
        all_limits = []
        task: Optional[Any] = self.property
        while task is not None:
            limits = task.get("limits", self.scenarioIdx)
            if limits:
                all_limits.append(limits)
            task = task.parent
        return all_limits

    def limitsOk(self, sbIdx: int, resource: Optional[Any] = None) -> bool:
        """
        Check if all task limits (including parent limits) are satisfied.

        Args:
            sbIdx: Scoreboard index to check
            resource: Resource to check (for resource-specific limits)

        Returns:
            True if all limits are satisfied
        """
        for limits in self.getAllLimits():
            if not limits.ok(sbIdx, upper=True, resource=resource.id if resource else None):
                return False
        return True

    def incLimits(self, sbIdx: int, resource: Optional[Any] = None) -> None:
        """
        Increment all task limit counters (including parent limits).

        Args:
            sbIdx: Scoreboard index
            resource: Resource being booked (for resource-specific limits)
        """
        for limits in self.getAllLimits():
            limits.inc(sbIdx, resource=resource.id if resource else None)

    def bookResource(self, resource: Any) -> float:
        """
        Try to book a single resource for the current slot.

        Args:
            resource: The resource to book

        Returns:
            Effort gained from this booking (hours), or 0 if booking failed.
            This accounts for partial slot availability.
        """
        # Get the resource's scenario data
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            return 0.0

        # Initialize resource scoreboard if needed
        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        # For the FIRST slot of this task, apply start offset from dependency
        # This marks the portion already used by predecessor as unavailable
        if hasattr(self, "slotStartOffset") and self.slotStartOffset > 0 and self.doneEffort == 0:
            # Mark the offset portion as used (by predecessor task)
            current_used = res_scenario.slotSecondsUsed.get(self.currentSlotIdx, 0.0)
            if current_used < self.slotStartOffset:
                res_scenario.slotSecondsUsed[self.currentSlotIdx] = self.slotStartOffset

        # Check if resource is available
        slot_idx = self.currentSlotIdx if self.currentSlotIdx is not None else 0
        if not res_scenario.available(slot_idx):
            return 0.0

        # Check task limits for this resource (including parent limits)
        if not self.limitsOk(slot_idx, resource):
            return 0.0

        # Book the resource - returns effort gained (accounts for partial slots)
        result_float: float = res_scenario.book(slot_idx, self.property)
        return result_float

    def propagateDate(self, date: datetime, atEnd: bool) -> None:
        attr = "end" if atEnd else "start"
        self.property[(attr, self.scenarioIdx)] = date
        # Propagate to dependencies?

    def finishScheduling(self) -> None:
        """
        Finish scheduling for this task.
        For container tasks, compute start/end from children.
        """
        # Recursively process children first
        for child in self.property.children:
            child_scenario = child.data[self.scenarioIdx] if child.data else None
            if child_scenario and hasattr(child_scenario, "finishScheduling"):
                child_scenario.finishScheduling()

        # For container tasks, set dates from children
        if not self.property.leaf():
            self.scheduleContainer()

    def scheduleContainer(self) -> None:
        """
        Compute and set start/end dates for a container task based on its children.
        """
        if self.scheduled or self.property.leaf():
            return

        n_start = None
        n_end = None

        for child in self.property.children:
            child_scenario = child.data[self.scenarioIdx] if child.data else None
            if not child_scenario:
                continue

            # Abort if a child has not been scheduled
            if not child.get("scheduled", self.scenarioIdx):
                return

            child_start = child.get("start", self.scenarioIdx)
            child_end = child.get("end", self.scenarioIdx)

            if child_start is None or child_end is None:
                return

            if n_start is None or child_start < n_start:
                n_start = child_start
            if n_end is None or child_end > n_end:
                n_end = child_end

        # Set the container dates
        current_start = self.property.get("start", self.scenarioIdx)
        current_end = self.property.get("end", self.scenarioIdx)

        if n_start and (current_start is None or current_start > n_start):
            self.property[("start", self.scenarioIdx)] = n_start

        if n_end and (current_end is None or current_end < n_end):
            self.property[("end", self.scenarioIdx)] = n_end

        if n_start and n_end:
            self.scheduled = True
            self.property[("scheduled", self.scenarioIdx)] = True

    def _getResourcesForTask(self) -> list[Any]:
        """
        Get the actual Resource objects for this task.

        Looks up resources from either 'assignedresources' (if populated)
        or 'allocate' (resource IDs), resolving them to Resource objects.

        Returns:
            List of Resource objects
        """
        resources = []

        # Try assignedresources first
        assigned = self.property.get("assignedresources", self.scenarioIdx) or []
        if assigned:
            return assigned

        # Fall back to allocate (which may contain IDs or resource objects)
        allocate = self.property.get("allocate", self.scenarioIdx) or []
        for res in allocate:
            if isinstance(res, str):
                # Look up resource by ID
                for resource in self.project.resources:
                    if resource.id == res:
                        resources.append(resource)
                        break
            else:
                # Already a resource object
                resources.append(res)

        return resources

    def getCost(self) -> float:
        """
        Calculate the cost for this task based on allocated time and resource rates.

        Cost is calculated as: allocated_time x resource_rate
        where allocated_time is the actual duration (not effort).

        For efficiency > 1.0, allocated_time < effort
        For efficiency < 1.0, allocated_time > effort

        Returns:
            The total cost for this task
        """
        total_cost = 0.0

        # Get resources for this task
        resources = self._getResourcesForTask()

        for resource in resources:
            # Get the resource's scenario data
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario is None:
                continue

            # Get resource rate
            rate = resource.get("rate", self.scenarioIdx) or 0.0
            if rate == 0.0:
                continue

            # Use slotTaskUsage to get exact time used by this task
            allocated_seconds = 0.0
            for _slot_idx, task_list in res_scenario.slotTaskUsage.items():
                for task, seconds in task_list:
                    if task == self.property:
                        allocated_seconds += seconds

            allocated_hours = allocated_seconds / 3600.0
            total_cost += allocated_hours * rate

        return total_cost

    def getAllocatedTime(self) -> float:
        """
        Calculate the total allocated time (duration) for this task.

        This is the actual calendar time spent on the task, which differs
        from effort when resource efficiency != 1.0.

        Returns:
            The allocated time in hours
        """
        total_allocated = 0.0

        # Get resources for this task
        resources = self._getResourcesForTask()

        for resource in resources:
            # Get the resource's scenario data
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario is None or res_scenario.scoreboard is None:
                continue

            # Count slots booked for this task by this resource
            booked_slots = 0
            for i in range(len(res_scenario.scoreboard)):
                if res_scenario.scoreboard[i] == self.property:
                    booked_slots += 1

            # Calculate allocated time in hours
            granularity = self.project.attributes.get("scheduleGranularity", 3600)
            allocated_hours = booked_slots * granularity / 3600.0
            total_allocated += allocated_hours

        return total_allocated
