import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.allocation_plan import AllocationPlan
from scriptplan.core.property import AttributeBase
from scriptplan.core.scenario_data import ScenarioData
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
from scriptplan.core.task_placement import (
    finish_scheduling,
    place_slot,
    place_task,
    propagate_date,
    schedule_container,
)
from scriptplan.core.task_resources import (
    advance_working_time,
    allocated_time,
    cost_of,
    estimate_completion_time,
    has_contiguous_block,
    has_project_contiguous_block,
    is_resource_available,
    resources_for_task,
    select_best_resources,
)

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
        self.slotStartOffsetSlot: Optional[int] = None
        # Bookings made in the current slot, and where backward work ends
        self.slotBookings: list[Any] = []
        self.firstWorkSlot: Optional[int] = None
        self.workEnd: Optional[datetime] = None
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
        self._workSpecification: Optional[tuple[float, float, float, Any]] = None

        # Track exact start time within a slot (for mid-slot dependency starts)
        # This is the number of seconds into the slot where we should start
        # booking, and the one slot it applies to
        self.slotStartOffset = 0.0
        self.slotStartOffsetSlot = None
        self.slotBookings = []
        self.firstWorkSlot = None
        self.workEnd = None

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

    def workSpecification(self) -> tuple[float, float, float, Any]:
        """How much work this task is: (effort, length, duration, milestone).

        Read once per scheduling run. These come from the file and cannot
        change while the task is being placed, and the placement loop asks for
        them once per slot.
        """
        cached = getattr(self, "_workSpecification", None)
        if cached is None:
            cached = (
                self.property.get("effort", self.scenarioIdx) or 0,
                self.property.get("length", self.scenarioIdx) or 0,
                self.property.get("duration", self.scenarioIdx) or 0,
                self.property.get("milestone", self.scenarioIdx),
            )
            self._workSpecification = cached
        return cached

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
        from scriptplan.core.units import Duration, project_seconds

        return project_seconds(self.project, Duration(duration_str, Duration.WORKING))

    def _parse_duration(self, duration_str: Any) -> float:
        """Working time in hours (kept for callers that still think in hours)."""
        return self._workingSeconds(duration_str) / 3600.0

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

    def allocationPlan(self) -> "AllocationPlan":
        """The task's allocations, resolved once per scheduling run."""
        plan = getattr(self, "_allocationPlan", None)
        if plan is None:
            plan = AllocationPlan.read(
                self.property.get("allocate", self.scenarioIdx), self._resolve_resource
            )
            self._allocationPlan = plan
        return plan

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

    def _isResourceAvailable(self, slotIdx: int) -> bool:
        return is_resource_available(self, slotIdx)

    def _hasContiguousBlock(self, effort: float) -> bool:
        return has_contiguous_block(self, effort)

    def _checkProjectContiguousBlock(self, effort: float) -> bool:
        return has_project_contiguous_block(self, effort)

    def _selectBestResources(
        self, primary_resources: list[Any], alternative_resources: list[Any], effort: float
    ) -> list[Any]:
        return select_best_resources(self, primary_resources, alternative_resources, effort)

    def _estimateCompletionTime(self, resources: list[Any], effort: float) -> Optional[datetime]:
        return estimate_completion_time(self, resources, effort)

    def _getResourcesForTask(self) -> list[Any]:
        return resources_for_task(self)

    def _advanceWorkingTime(self, start: datetime, seconds: float) -> datetime:
        return advance_working_time(self, start, seconds)

    def getCost(self) -> float:
        return cost_of(self)

    def getAllocatedTime(self) -> float:
        return allocated_time(self)
