import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.allocation_plan import AllocationPlan
from scriptplan.core.task_placement import (
    finish_scheduling,
    place_slot,
    place_task,
    propagate_date,
    schedule_container,
)
from scriptplan.core.task_booking import (
    all_limits,
    book_resource,
    book_resources,
    first_bookable,
    inc_limits,
    limits_ok,
    precise_end_time,
    precise_end_time_and_release,
    record_effort_start,
)
from scriptplan.core.task_dependencies import (
    all_dependencies,
    max_gap_delayed_start,
    start_from_end,
    successor_earliest_start,
    successors,
    successors_with_max_gap,
)
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
        self._allocationPlan: Optional[AllocationPlan] = None
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
            # A top-level task takes the scenario's projection setting from the
            # project, which is an inherited value rather than one the file
            # stated on this task.
            previous_mode = getattr(self.project, "attributeMode", AttributeBase.mode())
            self.project.attributeMode = AttributeBase.INHERITED
            try:
                proj_scenario = (
                    self.project.scenario(self.scenarioIdx)
                    if hasattr(self.project, "scenario")
                    else None
                )
                proj_projection = proj_scenario.get("projection") if proj_scenario else None
                if proj_projection:
                    self.property[("projectionmode", self.scenarioIdx)] = proj_projection
            finally:
                self.project.attributeMode = previous_mode

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
        self._allocationPlan = None  # Re-read the allocations for this run

        # Track exact start time within a slot (for mid-slot dependency starts)
        # This is the number of seconds into the slot where we should start booking
        self.slotStartOffset = 0.0

        # Reset the counters of all limits of this task (not parent tasks).
        # This is critical - limits track usage per period and must be reset
        # before each scheduling run to avoid carrying over counts from
        # previous scenario scheduling.
        limits = self.property.get("limits", self.scenarioIdx)
        if limits:
            limits.prepare(int(self.project.attributes.get("scheduleGranularity", 3600)))

        self._discardComputedDates()

    # Attributes the scheduler works out for itself. A value the file provided
    # or a container passed down is kept; anything the previous run computed is
    # discarded, so a second schedule() starts from the same state as the first
    # and produces the same answer instead of skipping the work and losing the
    # bookings that went with it.
    COMPUTED_ATTRIBUTES = ("start", "end", "scheduled", "assignedresources")

    def _discardComputedDates(self) -> None:
        for name in self.COMPUTED_ATTRIBUTES:
            try:
                attribute = self.property._get_scenario_attribute(name, self.scenarioIdx)
            except (ValueError, KeyError):
                continue
            if not attribute.getProvided() and not attribute.getInherited():
                attribute.reset()

    def getAllDependencies(self) -> Any:
        return all_dependencies(self)

    def _getSuccessors(self) -> Any:
        return successors(self)

    def _getSuccessorsWithMaxGap(self) -> Any:
        return successors_with_max_gap(self)

    def _getSuccessorEarliestStart(self, successor: Any) -> Any:
        return successor_earliest_start(self, successor)

    def _computeMaxGapDelayedStart(self, earliest_start: datetime, effort: float) -> Any:
        return max_gap_delayed_start(self, earliest_start, effort)

    def _computeStartFromEnd(self, end_time: datetime, effort: float) -> Any:
        return start_from_end(self, end_time, effort)

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

    def bookResources(self) -> None:
        book_resources(self)

    def bookResource(self, resource: Any) -> float:
        return book_resource(self, resource)

    def _firstBookable(self, allocation: Any, slot_idx: int) -> Optional[Any]:
        return first_bookable(self, allocation, slot_idx)

    def _recordEffortStart(self) -> None:
        record_effort_start(self)

    def getAllLimits(self) -> list[Any]:
        return all_limits(self)

    def limitsOk(self, sbIdx: int, resource: Optional[Any] = None) -> bool:
        return limits_ok(self, sbIdx, resource)

    def incLimits(self, sbIdx: int, resource: Optional[Any] = None, seconds: Optional[float] = None) -> None:
        inc_limits(self, sbIdx, resource, seconds)

    def _calculatePreciseEndTimeAndRelease(
        self, required_effort: float, effort_before_slot: float, forward: bool
    ) -> tuple[datetime, float]:
        return precise_end_time_and_release(self, required_effort, effort_before_slot, forward)

    def _calculatePreciseEndTime(self, required_effort: float, effort_before_slot: float, forward: bool) -> datetime:
        return precise_end_time(self, required_effort, effort_before_slot, forward)

    def schedule(self) -> bool:
        return place_task(self)

    def scheduleSlot(self) -> bool:
        return place_slot(self)

    def propagateDate(self, date: datetime, atEnd: bool) -> None:
        propagate_date(self, date, atEnd)

    def finishScheduling(self) -> None:
        finish_scheduling(self)

    def scheduleContainer(self) -> None:
        schedule_container(self)

    def _slotSeconds(self) -> int:
        """Length of one scheduling slot, in seconds."""
        return int(self.project.attributes.get("scheduleGranularity", 3600))

    def _calendarSeconds(self, duration_str: Any) -> float:
        """Wall-clock seconds. `gapduration 2d` is 48 hours, weekend or not."""
        if not duration_str:
            return 0.0
        from scriptplan.core.units import parse_calendar_duration

        return parse_calendar_duration(duration_str)

    def _workingSeconds(self, duration_str: Any) -> float:
        """Working seconds. `gaplength 1d` is one working day."""
        if not duration_str:
            return 0.0
        from scriptplan.core.units import project_seconds, Duration

        return project_seconds(self.project, Duration(duration_str, Duration.WORKING))

    def _parse_duration(self, duration_str: Any) -> float:
        """Working time in hours (kept for callers that still think in hours)."""
        return self._workingSeconds(duration_str) / 3600.0

    def _advanceWorkingTime(self, start: datetime, seconds: float) -> datetime:
        """The moment ``seconds`` of *working* time after ``start``.

        Walks the calendar rather than the clock, so a gap that spans a weekend
        or a night is measured only in the hours somebody could have worked. A
        gap shorter than one slot lands inside a slot instead of being rounded
        away, which is how `gaplength 30min` used to become no gap at all.
        """
        from datetime import timedelta

        if seconds <= 0:
            return start

        slot_seconds = float(self.project.attributes.get("scheduleGranularity", 3600))
        idx = self.project.dateToIdx(start)
        slot_start = self.project.idxToDate(idx)
        offset = max(0.0, (start - slot_start).total_seconds()) if slot_start else 0.0
        upper = self.project.dateToIdx(self.project["end"])

        remaining = seconds
        while idx <= upper:
            if self.isWorkingTime(idx):
                available = slot_seconds - offset
                if remaining <= available:
                    moment = self.project.idxToDate(idx)
                    return moment + timedelta(seconds=offset + remaining)
                remaining -= available
            idx += 1
            offset = 0.0
        end_of_project: datetime = self.project["end"]
        return end_of_project

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
        """Whether any allocated resource could work in this slot.

        Used to find where a task can begin, so it asks only about the shift,
        not about whether the slot is already taken.
        """
        plan = self.allocationPlan()
        if not plan:
            result: bool = self.project.isWorkingTime(slotIdx)
            return result

        for allocation in plan:
            for resource in allocation.candidates():
                scenario = resource.data[self.scenarioIdx] if resource.data else None
                if scenario is None:
                    continue
                if scenario.scoreboard is None:
                    scenario.prepareScheduling()
                if scenario.onShift(slotIdx):
                    return True
        return False

    def _hasContiguousBlock(self, effort: float) -> bool:
        """Whether an unbroken run long enough for the task starts here.

        A task flagged `contiguous` cannot be split across a lunch break or a
        night, so it may only begin where the whole of it fits.
        """
        resources = self.allocationPlan().resources()
        if not resources:
            return self._checkProjectContiguousBlock(effort)

        resource = resources[0]
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            return self._checkProjectContiguousBlock(effort)
        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        efficiency = resource.get("efficiency", self.scenarioIdx) or 1.0
        slot_duration_hours = self._slotSeconds() / 3600.0
        slots_needed = (effort / efficiency) / slot_duration_hours

        consecutive = 0
        current = self.currentSlotIdx if self.currentSlotIdx is not None else 0
        limit = len(res_scenario.scoreboard) if res_scenario.scoreboard else 1000

        while current < limit and consecutive < slots_needed:
            if not res_scenario.available(current):
                return False
            consecutive += 1
            current += 1

        result_bool: bool = consecutive >= slots_needed
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

    def allocationPlan(self) -> "AllocationPlan":
        """The task's allocations, resolved once per scheduling run."""
        if getattr(self, "_allocationPlan", None) is None:
            self._allocationPlan = AllocationPlan.read(
                self.property.get("allocate", self.scenarioIdx), self._resolve_resource
            )
        return self._allocationPlan

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

    def _getResourcesForTask(self) -> list[Any]:
        """The Resource objects this task may book."""
        assigned = self.property.get("assignedresources", self.scenarioIdx) or []
        if assigned:
            return list(assigned)
        return self.allocationPlan().resources()

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
