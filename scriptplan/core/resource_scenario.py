"""
ResourceScenario - Scenario-specific data for resources.

This module implements the ResourceScenario class which holds all
scenario-specific data for a Resource.
"""

import contextlib
from typing import TYPE_CHECKING, Any, Callable, Optional

from scriptplan.core.scenario_data import ScenarioData
from scriptplan.scheduler.scoreboard import Scoreboard
from scriptplan.utils.data_cache import DataCache

if TYPE_CHECKING:
    from scriptplan.core.resource import Resource
    from scriptplan.core.task import Task


class ResourceScenario(ScenarioData):
    """
    Scenario-specific data for a Resource.

    This class holds all scenario-specific attributes and methods for resources,
    including scoreboard management, booking, and effort tracking.
    """

    def __init__(self, resource: "Resource", scenario_idx: int, attributes: Any):
        """
        Initialize ResourceScenario.

        Args:
            resource: The parent Resource
            scenario_idx: The scenario index
            attributes: Attribute definitions
        """
        super().__init__(resource, scenario_idx, attributes)

        # Scoreboard may be nil, a Task, or a bit vector encoded as an Integer
        # nil:        Value has not been determined yet.
        # Task:       A reference to a Task object
        # Bit 0:      Reserved
        # Bit 1:      0: Work time (as defined by working hours)
        #             1: No work time (as defined by working hours)
        # Bit 2 - 5:  See Leave class for actual values.
        # Bit 6 - 7:  Reserved
        # Bit 8:      0: No global override
        #             1: Override global setting
        self.scoreboard: Optional[Scoreboard] = None

        # The index of the earliest booked time slot
        self.firstBookedSlot: Optional[int] = None
        # Same but for each assigned resource
        self.firstBookedSlots: dict[Any, int] = {}
        # The index of the last booked time slot
        self.lastBookedSlot: Optional[int] = None
        # Same but for each assigned resource
        self.lastBookedSlots: dict[Any, int] = {}

        # First available slot of the resource
        self.minslot: Optional[int] = None
        # Last available slot of the resource
        self.maxslot: Optional[int] = None

        # Internal effort counter
        self._effort: float = 0.0

        # Track partial slot usage: slot_idx -> seconds_used
        # When a task ends mid-slot, this records how much of the slot was used
        # Subsequent tasks can use the remaining time in that slot
        self.slotSecondsUsed: dict[int, float] = {}

        # Track which tasks used which slots and how much
        # slot_idx -> list of (task, seconds_used)
        # This allows multiple tasks to share a slot
        self.slotTaskUsage: dict[int, list[tuple[Any, float]]] = {}

        # Data cache
        self.dCache = DataCache.instance()

        # Ensure required attributes exist
        required_attrs = [
            "alloctdeffort",
            "chargeset",
            "criticalness",
            "directreports",
            "duties",
            "efficiency",
            "effort",
            "limits",
            "managers",
            "rate",
            "reports",
            "shifts",
            "leaves",
            "leaveallowances",
            "workinghours",
        ]
        for attr in required_attrs:
            with contextlib.suppress(ValueError, KeyError, AttributeError):
                _ = self.property.get(attr, self.scenarioIdx)

    def prepareScheduling(self) -> None:
        """
        Initialize variables used during the scheduling process.

        This method must be called at the beginning of each scheduling run.
        """
        self._effort = 0.0
        if self.property.leaf():
            self.initScoreboard()

    def initScoreboard(self) -> None:
        """
        Initialize the scoreboard for this resource.

        The scoreboard tracks the availability and bookings for each time slot.
        """
        start = self.project.attributes.get("start")
        end = self.project.attributes.get("end")
        granularity = self.project.attributes.get("scheduleGranularity", 3600)

        if not start or not end:
            return

        self.scoreboard = Scoreboard(start, end, granularity, 2)
        size = self.project.scoreboardSize()

        # Initialize working hours
        for i in range(size):
            if not self.onShift(i):
                # Mark as non-working time (bit 1 set)
                self.scoreboard[i] = 2
            else:
                self.scoreboard[i] = None

        # Apply global leaves
        leaves = self.project.attributes.get("leaves", [])
        if leaves:
            for leave in leaves:
                if hasattr(leave, "interval"):
                    start_idx = self.project.dateToIdx(leave.interval.start)
                    end_idx = self.project.dateToIdx(leave.interval.end)
                    for i in range(start_idx, min(end_idx, size)):
                        sb = self.scoreboard[i]
                        val = 0 if sb is None else (sb & 2)
                        leave_type = leave.type_idx if hasattr(leave, "type_idx") else 0
                        self.scoreboard[i] = val | (leave_type << 2)

        # Apply resource-specific leaves
        res_leaves = self.property.get("leaves", self.scenarioIdx)
        if res_leaves:
            for leave in res_leaves:
                if hasattr(leave, "interval"):
                    start_idx = self.project.dateToIdx(leave.interval.start)
                    end_idx = self.project.dateToIdx(leave.interval.end)
                    for i in range(start_idx, min(end_idx, size)):
                        sb = self.scoreboard[i]
                        if sb is not None:
                            leave_idx = (sb & 0x3C) >> 2
                            leave_type = leave.type_idx if hasattr(leave, "type_idx") else 0
                            if leave_type > leave_idx:
                                self.scoreboard[i] = (sb & 0x2) | (leave_type << 2)
                        else:
                            leave_type = leave.type_idx if hasattr(leave, "type_idx") else 0
                            self.scoreboard[i] = leave_type << 2

    def calcCriticalness(self) -> None:
        """
        Calculate the criticalness of the resource.

        The criticalness is a measure for the probability that all allocations
        can be fulfilled. A value above 1.0 means that statistically some tasks
        will not get their resources.
        """
        if self.scoreboard is None:
            self.property["criticalness", self.scenarioIdx] = 0.0
        else:
            free_slots = sum(1 for slot in self.scoreboard if slot is None)
            allocated_effort = self.property.get("alloctdeffort", self.scenarioIdx) or 0

            if free_slots == 0:
                self.property["criticalness", self.scenarioIdx] = 1.0
            else:
                self.property["criticalness", self.scenarioIdx] = allocated_effort / free_slots

    def setDirectReports(self) -> None:
        """
        Set up the direct reports relationships based on managers.
        """
        managers = self.property.get("managers", self.scenarioIdx) or []
        new_managers = []

        for manager_id in managers:
            manager = self.project.resources.get(manager_id) if isinstance(manager_id, str) else manager_id  # type: ignore[attr-defined]

            if manager is None:
                self.error("resource_id_expected", f"{manager_id} is not a defined resource.")
                continue

            if not manager.leaf():
                self.error(
                    "manager_is_group",
                    f"Resource {self.property.fullId} has group {manager.fullId} assigned as manager.",
                )

            if manager == self.property:
                self.error("manager_is_self", f"Resource {self.property.fullId} cannot manage itself.")

            if self.property.leaf():
                direct_reports = manager.get("directreports", self.scenarioIdx) or []
                if self.property not in direct_reports:
                    direct_reports.append(self.property)

            new_managers.append(manager)

        # Update managers list with unique entries
        seen = set()
        unique_managers = []
        for m in new_managers:
            if m not in seen:
                unique_managers.append(m)
                seen.add(m)

        self.property["managers", self.scenarioIdx] = unique_managers

    def setReports(self) -> None:
        """
        Set up reporting relationships.
        """
        direct_reports = self.property.get("directreports", self.scenarioIdx)
        if not direct_reports:
            return

        managers = self.property.get("managers", self.scenarioIdx) or []
        for r in managers:
            if hasattr(r, "setReports_i"):
                r.setReports_i(self.scenarioIdx, [self.property])

    def preScheduleCheck(self) -> None:
        """
        Pre-schedule validation check.
        """
        pass

    def finishScheduling(self) -> None:
        """
        Finish scheduling housekeeping.

        This method is called after scheduling is completed to do housekeeping
        like updating parent resources with duties from children.
        """
        # Recursively descend into all child resources
        for resource in self.property.children:
            if hasattr(resource, "finishScheduling"):
                resource.finishScheduling(self.scenarioIdx)

        # Add parent tasks of each task to the duties list
        duties = self.property.get("duties", self.scenarioIdx) or []
        current_duties = list(duties)
        for task in current_duties:
            if hasattr(task, "ancestors"):
                for p_task in task.ancestors(True):
                    if p_task not in duties:
                        duties.append(p_task)

        # Add assigned tasks to parent resource duties
        parents = self.property.parents() if callable(self.property.parents) else self.property.parents
        for p_resource in parents or []:
            p_duties = p_resource.get("duties", self.scenarioIdx) or []
            for task in duties:
                if task not in p_duties:
                    p_duties.append(task)

    def available(self, sb_idx: int) -> bool:
        """
        Check if resource is available at the given time slot.

        A slot is available if:
        1. It's during working hours for this resource
        2. Not fully booked by another task, OR
        3. Partially used and has remaining time

        Args:
            sb_idx: Scoreboard index

        Returns:
            True if available (fully or partially), False otherwise
        """
        if self.scoreboard is None:
            return False

        # Check if slot is during working hours for this resource
        if not self.onShift(sb_idx):
            return False

        # Check if slot has any available time
        available_seconds = self.getAvailableSecondsInSlot(sb_idx)
        if available_seconds <= 0:
            return False

        # If scoreboard shows a booking but there's available time, it's a partial slot
        # that was released - allow booking
        if self.scoreboard[sb_idx] is not None and available_seconds < self.project.attributes.get(
            "scheduleGranularity", 3600
        ):
            # Partial slot available - allow it
            pass
        elif self.scoreboard[sb_idx] is not None:
            return False

        limits = self.property.get("limits", self.scenarioIdx)
        if limits and hasattr(limits, "ok") and not limits.ok(sb_idx):
            return False

        # Check parent resource limits (hierarchical limit propagation)
        # When a child resource is booked, parent limits must also be checked
        parent = self.property.parent
        while parent:
            parent_limits = parent.get("limits", self.scenarioIdx)
            if parent_limits and hasattr(parent_limits, "ok") and not parent_limits.ok(sb_idx):
                return False
            parent = parent.parent

        return True

    def booked(self, sb_idx: int) -> bool:
        """
        Check if resource is booked at the given time slot.

        Args:
            sb_idx: Scoreboard index

        Returns:
            True if booked for a task, False otherwise
        """
        if self.scoreboard is None:
            return False
        # Import here to avoid circular import
        from scriptplan.core.task import Task

        return isinstance(self.scoreboard[sb_idx], Task)

    def bookedTask(self, sb_idx: int) -> Optional["Task"]:
        """
        Get the task booked at the given time slot.

        Args:
            sb_idx: Scoreboard index

        Returns:
            The Task or None
        """
        from scriptplan.core.task import Task

        if self.scoreboard is None:
            return None
        sb = self.scoreboard[sb_idx]
        return sb if isinstance(sb, Task) else None

    def getAvailableSecondsInSlot(self, sb_idx: int) -> float:
        """
        Get the available seconds in a slot, accounting for partial usage.

        If a previous task ended mid-slot, only the remaining time is available.

        Args:
            sb_idx: Scoreboard index

        Returns:
            Available seconds in the slot (0 to slot_duration)
        """
        slot_duration: float = self.project.attributes.get("scheduleGranularity", 3600)
        seconds_used = self.slotSecondsUsed.get(sb_idx, 0.0)
        return float(max(0.0, slot_duration - seconds_used))

    def markSlotPartiallyUsed(self, sb_idx: int, seconds_used: float) -> None:
        """
        Record that a task used only part of a slot.

        This allows subsequent tasks to use the remaining time.

        Args:
            sb_idx: Scoreboard index
            seconds_used: Seconds of the slot that were used
        """
        current_used = self.slotSecondsUsed.get(sb_idx, 0.0)
        self.slotSecondsUsed[sb_idx] = current_used + seconds_used

    def book(self, sb_idx: int, task: "Task", force: bool = False) -> float:
        """
        Book a time slot for a task.

        Args:
            sb_idx: Scoreboard index
            task: The task to book
            force: If True, overwrite existing booking

        Returns:
            Effort gained from this booking (hours), or 0 if booking failed.
            This accounts for partial slot usage.
        """
        if not force and not self.available(sb_idx):
            return 0.0

        # Make sure task is in duties list
        duties = self.property.get("duties", self.scenarioIdx) or []
        if task not in duties:
            duties.append(task)

        # Initialize scoreboard if needed
        if self.scoreboard is None:
            self.initScoreboard()

        # Calculate effort based on available time in slot (for partial slots)
        self.project.attributes.get("scheduleGranularity", 3600)
        available_seconds = self.getAvailableSecondsInSlot(sb_idx)
        efficiency = self.property.get("efficiency", self.scenarioIdx) or 1.0

        # Effort = (available_seconds / 3600) * efficiency
        effort_gained = (available_seconds / 3600.0) * efficiency

        # Track effort
        self._effort += effort_gained

        # Track per-task slot usage for cost calculation
        if sb_idx not in self.slotTaskUsage:
            self.slotTaskUsage[sb_idx] = []
        self.slotTaskUsage[sb_idx].append((task, available_seconds))

        # Update total seconds used in this slot
        current_used = self.slotSecondsUsed.get(sb_idx, 0.0)
        self.slotSecondsUsed[sb_idx] = current_used + available_seconds

        # Update scoreboard (may be overwritten if multiple tasks share slot)
        if self.scoreboard is not None:
            self.scoreboard[sb_idx] = task

        # Update resource limits
        limits = self.property.get("limits", self.scenarioIdx)
        if limits and hasattr(limits, "inc"):
            limits.inc(sb_idx)

        # Propagate to parent resource limits (hierarchical limit propagation)
        # When a child resource is booked, parent limits must also be incremented
        parent = self.property.parent
        while parent:
            parent_limits = parent.get("limits", self.scenarioIdx)
            if parent_limits and hasattr(parent_limits, "inc"):
                parent_limits.inc(sb_idx)
            parent = parent.parent

        # Update task limits (including parent task limits)
        task_scenario = task.data[self.scenarioIdx] if hasattr(task, "data") and task.data else None
        if task_scenario and hasattr(task_scenario, "incLimits"):
            task_scenario.incLimits(sb_idx, self.property)

        # Track booked slot ranges
        if self.firstBookedSlot is None or self.firstBookedSlot > sb_idx:
            self.firstBookedSlot = sb_idx
            self.firstBookedSlots[task] = sb_idx
        elif task not in self.firstBookedSlots or self.firstBookedSlots[task] > sb_idx:
            self.firstBookedSlots[task] = sb_idx

        if self.lastBookedSlot is None or self.lastBookedSlot < sb_idx:
            self.lastBookedSlot = sb_idx
            self.lastBookedSlots[task] = sb_idx
        elif task not in self.lastBookedSlots or self.lastBookedSlots[task] < sb_idx:
            self.lastBookedSlots[task] = sb_idx

        return effort_gained

    def releasePartialSlot(self, sb_idx: int, seconds_to_release: float) -> None:
        """
        Release part of a slot back for other tasks to use.

        Called when a task ends mid-slot to make the remaining time available.

        Args:
            sb_idx: Scoreboard index
            seconds_to_release: Seconds to release back
        """
        slot_duration = self.project.attributes.get("scheduleGranularity", 3600)
        current_used = self.slotSecondsUsed.get(sb_idx, slot_duration)
        # Reduce the used time, making more available
        self.slotSecondsUsed[sb_idx] = max(0.0, current_used - seconds_to_release)
        # Clear the booking so another task can use it
        if self.scoreboard is not None:
            self.scoreboard[sb_idx] = None

    def bookedEffort(self) -> float:
        """
        Get the total booked effort for this resource.

        Returns:
            The effort value
        """
        if self.property.leaf():
            return self._effort
        else:
            effort = 0.0
            for r in self.property.kids():
                if r.data and r.data[self.scenarioIdx]:
                    effort += r.data[self.scenarioIdx].bookedEffort()
            return effort

    def onShift(self, sb_idx: int) -> bool:
        """
        Check if the resource is on shift at the given time slot.

        Args:
            sb_idx: Scoreboard index

        Returns:
            True if on shift, False otherwise
        """
        date = self.project.idxToDate(sb_idx)

        # First check global vacations - they override everything
        vacations = self.project.attributes.get("vacations", [])
        if vacations:
            for vac in vacations:
                if hasattr(vac, "interval") and vac.interval and vac.interval.start <= date < vac.interval.end:
                    return False

        # Check resource-level leaves/vacations
        leaves = self.property.get("leaves", self.scenarioIdx)
        if leaves:
            for leave in leaves:
                if hasattr(leave, "interval") and leave.interval and leave.interval.start <= date < leave.interval.end:
                    return False

        # Get resource's timezone for local time conversion
        # Working hours are defined in local time, but slots are in UTC
        resource_tz = self.property.get("timezone", self.scenarioIdx)

        # Check if resource has a shift reference
        shift = self.property.get("shifts", self.scenarioIdx)
        if shift:
            # Use the shift's working hours
            shift_wh = shift.get("workinghours", self.scenarioIdx)
            if shift_wh and hasattr(shift_wh, "onShift"):
                result: bool = shift_wh.onShift(sb_idx, timezone=resource_tz)
                return result

        # Check if resource has direct working hours
        workinghours = self.property.get("workinghours", self.scenarioIdx)
        if workinghours and hasattr(workinghours, "onShift"):
            result2: bool = workinghours.onShift(sb_idx, timezone=resource_tz)
            return result2

        # Default: use project's working time
        result3: bool = self.project.isWorkingTime(sb_idx)
        return result3

    def setReports_i(self, reports: list[Any]) -> None:
        """
        Internal method to set reports relationship.

        Args:
            reports: List of resources reporting to this one
        """
        if self.property in reports:
            self.error("manager_loop", f"Management loop detected. {self.property.fullId} has self in list of reports")

        current_reports = self.property.get("reports", self.scenarioIdx) or []
        for r in reports:
            if r not in current_reports:
                current_reports.append(r)

        managers = self.property.get("managers", self.scenarioIdx) or []
        for r in managers:
            if hasattr(r, "setReports_i"):
                r.setReports_i(self.scenarioIdx, current_reports)

    def treeSum(self, start_idx: int, end_idx: int, *args: Any, block: Callable[["ResourceScenario"], float]) -> float:
        """
        Generic tree iterator that recursively accumulates results.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index
            *args: Additional arguments
            block: Callable to execute on leaf nodes

        Returns:
            Accumulated sum
        """
        cache_tag = "treeSum"
        return self.treeSumR(cache_tag, start_idx, end_idx, *args, block=block)

    def treeSumR(
        self, cache_tag: str, start_idx: int, end_idx: int, *args: Any, block: Callable[["ResourceScenario"], float]
    ) -> float:
        """
        Recursive implementation of treeSum.

        Args:
            cache_tag: Cache key tag
            start_idx: Start scoreboard index
            end_idx: End scoreboard index
            *args: Additional arguments
            block: Callable to execute on leaf nodes

        Returns:
            Accumulated sum
        """
        if self.property.container:  # type: ignore[attr-defined]
            sum_val = 0.0
            for resource in self.property.kids():
                if resource.data and resource.data[self.scenarioIdx]:
                    res_scenario = resource.data[self.scenarioIdx]
                    sum_val += res_scenario.treeSumR(cache_tag, start_idx, end_idx, *args, block=block)
            return sum_val
        else:
            return block(self)

    def getEffectiveWork(self, start_idx: int, end_idx: int, task: Optional["Task"] = None) -> float:
        """
        Get the effective work done by this resource.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index
            task: Optional task filter

        Returns:
            Work in daily load units
        """
        duties = self.property.get("duties", self.scenarioIdx) or []
        if start_idx >= end_idx or (task and task not in duties):
            return 0.0

        def calculate(res_scen: "ResourceScenario") -> float:
            if res_scen.scoreboard is None:
                return 0.0
            allocated = res_scen.getAllocatedSlots(start_idx, end_idx, task)
            granularity = res_scen.project.attributes.get("scheduleGranularity", 3600)
            efficiency = res_scen.property.get("efficiency", res_scen.scenarioIdx) or 1.0
            daily_load: float = res_scen.project.convertToDailyLoad(allocated * granularity) * efficiency  # type: ignore[attr-defined]
            return daily_load

        return self.treeSum(start_idx, end_idx, task, block=calculate)

    def getAllocatedSlots(self, start_idx: int, end_idx: int, task: Optional["Task"] = None) -> int:
        """
        Count booked slots in the given range.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index
            task: Optional task filter

        Returns:
            Number of allocated slots
        """
        if self.scoreboard is None:
            return 0

        if start_idx >= end_idx:
            return 0

        from scriptplan.core.task import Task

        booked_slots = 0
        task_list = task.all() if task and hasattr(task, "all") else []

        actual_end = min(end_idx, len(self.scoreboard))
        for i in range(start_idx, actual_end):
            slot = self.scoreboard[i]
            if isinstance(slot, Task) and (task is None or slot in task_list or slot == task):
                booked_slots += 1

        return booked_slots

    def getFreeSlots(self, start_idx: int, end_idx: int) -> int:
        """
        Count free slots in the given range.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index

        Returns:
            Number of free slots
        """
        if self.scoreboard is None:
            return 0

        count = 0
        actual_end = min(end_idx, len(self.scoreboard))
        for i in range(start_idx, actual_end):
            if self.scoreboard[i] is None:
                count += 1
        return count

    def getWorkSlots(self, start_idx: int, end_idx: int) -> int:
        """
        Count work slots (free + allocated) in the given range.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index

        Returns:
            Number of work slots
        """
        from scriptplan.core.task import Task

        if self.scoreboard is None:
            return 0

        count = 0
        actual_end = min(end_idx, len(self.scoreboard))
        for i in range(start_idx, actual_end):
            slot = self.scoreboard[i]
            if slot is None or isinstance(slot, Task):
                count += 1
        return count
