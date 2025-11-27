"""
ResourceScenario - Scenario-specific data for resources.

This module implements the ResourceScenario class which holds all
scenario-specific data for a Resource.
"""

from typing import TYPE_CHECKING, Optional, List, Any, Dict, Callable

from rodmena_resource_management.core.scenario_data import ScenarioData
from rodmena_resource_management.scheduler.scoreboard import Scoreboard
from rodmena_resource_management.utils.data_cache import DataCache
from rodmena_resource_management.core.leave import Leave
from rodmena_resource_management.core.booking import Booking
from rodmena_resource_management.utils.time import TimeInterval

if TYPE_CHECKING:
    from rodmena_resource_management.core.resource import Resource
    from rodmena_resource_management.core.task import Task


class ResourceScenario(ScenarioData):
    """
    Scenario-specific data for a Resource.

    This class holds all scenario-specific attributes and methods for resources,
    including scoreboard management, booking, and effort tracking.
    """

    def __init__(self, resource: 'Resource', scenario_idx: int, attributes: Any):
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
        self.firstBookedSlots: Dict[Any, int] = {}
        # The index of the last booked time slot
        self.lastBookedSlot: Optional[int] = None
        # Same but for each assigned resource
        self.lastBookedSlots: Dict[Any, int] = {}

        # First available slot of the resource
        self.minslot: Optional[int] = None
        # Last available slot of the resource
        self.maxslot: Optional[int] = None

        # Internal effort counter
        self._effort = 0

        # Data cache
        self.dCache = DataCache.instance()

        # Ensure required attributes exist
        required_attrs = [
            'alloctdeffort', 'chargeset', 'criticalness', 'directreports',
            'duties', 'efficiency', 'effort', 'limits', 'managers', 'rate',
            'reports', 'shifts', 'leaves', 'leaveallowances', 'workinghours'
        ]
        for attr in required_attrs:
            try:
                _ = self.property.get(attr, self.scenarioIdx)
            except (ValueError, KeyError, AttributeError):
                pass

    def prepareScheduling(self) -> None:
        """
        Initialize variables used during the scheduling process.

        This method must be called at the beginning of each scheduling run.
        """
        self._effort = 0
        if self.property.leaf():
            self.initScoreboard()

    def initScoreboard(self) -> None:
        """
        Initialize the scoreboard for this resource.

        The scoreboard tracks the availability and bookings for each time slot.
        """
        start = self.project.attributes.get('start')
        end = self.project.attributes.get('end')
        granularity = self.project.attributes.get('scheduleGranularity', 3600)

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
        leaves = self.project.attributes.get('leaves', [])
        if leaves:
            for leave in leaves:
                if hasattr(leave, 'interval'):
                    start_idx = self.project.dateToIdx(leave.interval.start)
                    end_idx = self.project.dateToIdx(leave.interval.end)
                    for i in range(start_idx, min(end_idx, size)):
                        sb = self.scoreboard[i]
                        val = 0 if sb is None else (sb & 2)
                        leave_type = leave.type_idx if hasattr(leave, 'type_idx') else 0
                        self.scoreboard[i] = val | (leave_type << 2)

        # Apply resource-specific leaves
        res_leaves = self.property.get('leaves', self.scenarioIdx)
        if res_leaves:
            for leave in res_leaves:
                if hasattr(leave, 'interval'):
                    start_idx = self.project.dateToIdx(leave.interval.start)
                    end_idx = self.project.dateToIdx(leave.interval.end)
                    for i in range(start_idx, min(end_idx, size)):
                        sb = self.scoreboard[i]
                        if sb is not None:
                            leave_idx = (sb & 0x3C) >> 2
                            leave_type = leave.type_idx if hasattr(leave, 'type_idx') else 0
                            if leave_type > leave_idx:
                                self.scoreboard[i] = (sb & 0x2) | (leave_type << 2)
                        else:
                            leave_type = leave.type_idx if hasattr(leave, 'type_idx') else 0
                            self.scoreboard[i] = leave_type << 2

    def calcCriticalness(self) -> None:
        """
        Calculate the criticalness of the resource.

        The criticalness is a measure for the probability that all allocations
        can be fulfilled. A value above 1.0 means that statistically some tasks
        will not get their resources.
        """
        if self.scoreboard is None:
            self.property.set_scenario_attr('criticalness', self.scenarioIdx, 0.0)
        else:
            free_slots = sum(1 for slot in self.scoreboard if slot is None)
            allocated_effort = self.property.get('alloctdeffort', self.scenarioIdx) or 0

            if free_slots == 0:
                self.property.set_scenario_attr('criticalness', self.scenarioIdx, 1.0)
            else:
                self.property.set_scenario_attr('criticalness', self.scenarioIdx,
                                               allocated_effort / free_slots)

    def setDirectReports(self) -> None:
        """
        Set up the direct reports relationships based on managers.
        """
        managers = self.property.get('managers', self.scenarioIdx) or []
        new_managers = []

        for manager_id in managers:
            manager = self.project.resource(manager_id) if isinstance(manager_id, str) else manager_id

            if manager is None:
                self.error('resource_id_expected',
                          f"{manager_id} is not a defined resource.")
                continue

            if not manager.leaf():
                self.error('manager_is_group',
                          f"Resource {self.property.fullId} has group "
                          f"{manager.fullId} assigned as manager.")

            if manager == self.property:
                self.error('manager_is_self',
                          f"Resource {self.property.fullId} cannot manage itself.")

            if self.property.leaf():
                direct_reports = manager.get('directreports', self.scenarioIdx) or []
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

        self.property.set_scenario_attr('managers', self.scenarioIdx, unique_managers)

    def setReports(self) -> None:
        """
        Set up reporting relationships.
        """
        direct_reports = self.property.get('directreports', self.scenarioIdx)
        if not direct_reports:
            return

        managers = self.property.get('managers', self.scenarioIdx) or []
        for r in managers:
            if hasattr(r, 'setReports_i'):
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
            resource.finishScheduling(self.scenarioIdx)

        # Add parent tasks of each task to the duties list
        duties = self.property.get('duties', self.scenarioIdx) or []
        current_duties = list(duties)
        for task in current_duties:
            if hasattr(task, 'ancestors'):
                for p_task in task.ancestors(True):
                    if p_task not in duties:
                        duties.append(p_task)

        # Add assigned tasks to parent resource duties
        parents = self.property.parents() if callable(self.property.parents) else self.property.parents
        for p_resource in (parents or []):
            p_duties = p_resource.get('duties', self.scenarioIdx) or []
            for task in duties:
                if task not in p_duties:
                    p_duties.append(task)

    def available(self, sb_idx: int) -> bool:
        """
        Check if resource is available at the given time slot.

        Args:
            sb_idx: Scoreboard index

        Returns:
            True if available, False otherwise
        """
        if self.scoreboard is None:
            return False
        if self.scoreboard[sb_idx] is not None:
            return False

        limits = self.property.get('limits', self.scenarioIdx)
        if limits and hasattr(limits, 'ok') and not limits.ok(sb_idx):
            return False

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
        from rodmena_resource_management.core.task import Task
        return isinstance(self.scoreboard[sb_idx], Task)

    def bookedTask(self, sb_idx: int) -> Optional['Task']:
        """
        Get the task booked at the given time slot.

        Args:
            sb_idx: Scoreboard index

        Returns:
            The Task or None
        """
        from rodmena_resource_management.core.task import Task
        if self.scoreboard is None:
            return None
        sb = self.scoreboard[sb_idx]
        return sb if isinstance(sb, Task) else None

    def book(self, sb_idx: int, task: 'Task', force: bool = False) -> bool:
        """
        Book a time slot for a task.

        Args:
            sb_idx: Scoreboard index
            task: The task to book
            force: If True, overwrite existing booking

        Returns:
            True if booking succeeded, False otherwise
        """
        if not force and not self.available(sb_idx):
            return False

        # Make sure task is in duties list
        duties = self.property.get('duties', self.scenarioIdx) or []
        if task not in duties:
            duties.append(task)

        # Initialize scoreboard if needed
        if self.scoreboard is None:
            self.initScoreboard()

        self.scoreboard[sb_idx] = task

        # Track effort
        efficiency = self.property.get('efficiency', self.scenarioIdx) or 1.0
        self._effort += efficiency

        # Update limits
        limits = self.property.get('limits', self.scenarioIdx)
        if limits and hasattr(limits, 'inc'):
            limits.inc(sb_idx)

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

        return True

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
        shifts = self.property.get('shifts', self.scenarioIdx)
        if shifts and hasattr(shifts, 'assigned') and shifts.assigned(sb_idx):
            return shifts.onShift(sb_idx)
        else:
            workinghours = self.property.get('workinghours', self.scenarioIdx)
            if workinghours and hasattr(workinghours, 'onShift'):
                return workinghours.onShift(sb_idx)
        # Default: assume working hours (9-5 equivalent check would go here)
        return True

    def setReports_i(self, reports: List) -> None:
        """
        Internal method to set reports relationship.

        Args:
            reports: List of resources reporting to this one
        """
        if self.property in reports:
            self.error('manager_loop',
                      f"Management loop detected. {self.property.fullId} "
                      "has self in list of reports")

        current_reports = self.property.get('reports', self.scenarioIdx) or []
        for r in reports:
            if r not in current_reports:
                current_reports.append(r)

        managers = self.property.get('managers', self.scenarioIdx) or []
        for r in managers:
            if hasattr(r, 'setReports_i'):
                r.setReports_i(self.scenarioIdx, current_reports)

    def treeSum(self, start_idx: int, end_idx: int, *args,
                block: Callable[['ResourceScenario'], float]) -> float:
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

    def treeSumR(self, cache_tag: str, start_idx: int, end_idx: int, *args,
                 block: Callable[['ResourceScenario'], float]) -> float:
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
        if self.property.container():
            sum_val = 0.0
            for resource in self.property.kids():
                if resource.data and resource.data[self.scenarioIdx]:
                    res_scenario = resource.data[self.scenarioIdx]
                    sum_val += res_scenario.treeSumR(cache_tag, start_idx, end_idx,
                                                    *args, block=block)
            return sum_val
        else:
            return block(self)

    def getEffectiveWork(self, start_idx: int, end_idx: int,
                        task: Optional['Task'] = None) -> float:
        """
        Get the effective work done by this resource.

        Args:
            start_idx: Start scoreboard index
            end_idx: End scoreboard index
            task: Optional task filter

        Returns:
            Work in daily load units
        """
        duties = self.property.get('duties', self.scenarioIdx) or []
        if start_idx >= end_idx or (task and task not in duties):
            return 0.0

        def calculate(res_scen: 'ResourceScenario') -> float:
            if res_scen.scoreboard is None:
                return 0.0
            allocated = res_scen.getAllocatedSlots(start_idx, end_idx, task)
            granularity = res_scen.project.attributes.get('scheduleGranularity', 3600)
            efficiency = res_scen.property.get('efficiency', res_scen.scenarioIdx) or 1.0
            return res_scen.project.convertToDailyLoad(allocated * granularity) * efficiency

        return self.treeSum(start_idx, end_idx, task, block=calculate)

    def getAllocatedSlots(self, start_idx: int, end_idx: int,
                         task: Optional['Task'] = None) -> int:
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

        from rodmena_resource_management.core.task import Task

        booked_slots = 0
        task_list = task.all() if task and hasattr(task, 'all') else []

        actual_end = min(end_idx, len(self.scoreboard))
        for i in range(start_idx, actual_end):
            slot = self.scoreboard[i]
            if isinstance(slot, Task):
                if task is None or slot in task_list or slot == task:
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
        from rodmena_resource_management.core.task import Task

        if self.scoreboard is None:
            return 0

        count = 0
        actual_end = min(end_idx, len(self.scoreboard))
        for i in range(start_idx, actual_end):
            slot = self.scoreboard[i]
            if slot is None or isinstance(slot, Task):
                count += 1
        return count
