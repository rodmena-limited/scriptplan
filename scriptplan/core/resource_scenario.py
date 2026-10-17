"""
ResourceScenario - Scenario-specific data for resources.

This module implements the ResourceScenario class which holds all
scenario-specific data for a Resource.
"""

import contextlib
from typing import TYPE_CHECKING, Any, Callable, Optional

from scriptplan.core.resource_availability import (
    cache_shift_inputs,
    init_scoreboard,
    mark_shift_pattern,
    on_shift,
    on_shift_ignoring_leave,
)
from scriptplan.core.resource_reporting import (
    allocated_slots,
    calc_criticalness,
    effective_work,
    finish_scheduling,
    free_slots,
    set_direct_reports,
    set_reports,
    set_reports_internal,
    tree_sum,
    tree_sum_recursive,
    work_slots,
)
from scriptplan.core.scenario_data import ScenarioData
from scriptplan.core.slot_ledger import SlotBooking, free_seconds, release, reserve
from scriptplan.scheduler.scoreboard import Scoreboard

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

        # A slot is filled from both ends (see slot_ledger): forward work takes
        # seconds from its start and backward work from its end.
        # slot_idx -> seconds taken from the start / from the end
        self.slotFrontUsed: dict[int, float] = {}
        self.slotBackUsed: dict[int, float] = {}
        # slot_idx -> seconds no longer free (front + back)
        self.slotSecondsUsed: dict[int, float] = {}
        # Length of one slot, read once per run rather than once per slot
        self.slotLength: float = float(self.project.attributes.get("scheduleGranularity", 3600))

        # Track which tasks used which slots and how much
        # slot_idx -> list of (task, seconds_used)
        # This allows multiple tasks to share a slot
        self.slotTaskUsage: dict[int, list[tuple[Any, float]]] = {}

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
        self.slotLength = float(self.project.attributes.get("scheduleGranularity", 3600))
        self.slotFrontUsed = {}
        self.slotBackUsed = {}
        self.slotSecondsUsed = {}
        self.slotTaskUsage = {}
        self.firstBookedSlot = None
        self.firstBookedSlots = {}
        self.lastBookedSlot = None
        self.lastBookedSlots = {}

        # Daily and weekly limits count periods in this resource's own
        # calendar, so a resource eight hours west reaches the end of its day
        # eight hours later than one in UTC.
        limits = self.property.get("limits", self.scenarioIdx)
        if limits is not None and hasattr(limits, "prepare"):
            limits.prepare(
                int(self.project.attributes.get("scheduleGranularity", 3600)),
                self.property.get("timezone", self.scenarioIdx),
            )

        self._cacheShiftInputs()

        if self.property.leaf():
            self.initScoreboard()

    def preScheduleCheck(self) -> None:
        """
        Pre-schedule validation check.
        """
        pass

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

        # A limit narrows how much of this slot may be used, down to nothing.
        return self.limitAllowance(sb_idx) > 0

    def limitAllowance(self, sb_idx: int) -> float:
        """Seconds of this slot the limits still permit, own and inherited.

        The result is capped by what is left of the slot, so it can be handed
        straight to a booking. A limit smaller than one slot yields part of a
        slot rather than zero.
        """
        allowance = self.getAvailableSecondsInSlot(sb_idx)
        holder: Optional[Any] = self.property
        while holder is not None:
            limits = holder.get("limits", self.scenarioIdx)
            if limits is not None and hasattr(limits, "remaining"):
                remaining = limits.remaining(sb_idx, self.property.id)
                if remaining is not None:
                    allowance = min(allowance, remaining)
            holder = holder.parent
        return max(0.0, allowance)

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

        Work booked from either end of the slot is not available.

        Args:
            sb_idx: Scoreboard index

        Returns:
            Available seconds in the slot (0 to slot_duration)
        """
        return free_seconds(self, sb_idx)

    def book(self, sb_idx: int, task: "Task", force: bool = False, forward: bool = True) -> float:
        """
        Book a time slot for a task.

        Args:
            sb_idx: Scoreboard index
            task: The task to book
            force: If True, overwrite existing booking
            forward: Fill the slot from its start (True) or its end (False)

        Returns:
            Effort gained from this booking (hours), or 0 if booking failed.
            This accounts for partial slot usage.
        """
        booking = self.reserve(sb_idx, task, force=force, forward=forward)
        return booking.effort if booking is not None else 0.0

    def reserve(
        self, sb_idx: int, task: "Task", force: bool = False, forward: bool = True, not_before: float = 0.0
    ) -> Optional[SlotBooking]:
        """Book what the slot and the limits allow, and say where it sits."""
        return reserve(self, sb_idx, task, forward=forward, force=force, not_before=not_before)

    def release(self, booking: SlotBooking, keep: float) -> None:
        """Hand back the part of a booking past its first ``keep`` seconds."""
        release(booking, keep)

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

    def initScoreboard(self) -> None:
        init_scoreboard(self)

    def _markShiftPattern(self, size: int, granularity: int) -> None:
        mark_shift_pattern(self, size, granularity)

    def _cacheShiftInputs(self) -> None:
        cache_shift_inputs(self)

    def onShift(self, sb_idx: int) -> bool:
        return on_shift(self, sb_idx)

    def onShiftIgnoringLeave(self, sb_idx: int) -> bool:
        return on_shift_ignoring_leave(self, sb_idx)

    def calcCriticalness(self) -> None:
        calc_criticalness(self)

    def setDirectReports(self) -> None:
        set_direct_reports(self)

    def setReports(self) -> None:
        set_reports(self)

    def setReports_i(self, reports: list[Any]) -> None:
        set_reports_internal(self, reports)

    def finishScheduling(self) -> None:
        finish_scheduling(self)

    def treeSum(self, start_idx: int, end_idx: int, *args: Any, block: Callable[[Any], float]) -> float:
        return tree_sum(self, start_idx, end_idx, *args, block=block)

    def treeSumR(
        self, cache_tag: str, start_idx: int, end_idx: int, *args: Any, block: Callable[[Any], float]
    ) -> float:
        return tree_sum_recursive(self, cache_tag, start_idx, end_idx, *args, block=block)

    def getEffectiveWork(self, start_idx: int, end_idx: int, task: Optional["Task"] = None) -> float:
        return effective_work(self, start_idx, end_idx, task)

    def getAllocatedSlots(self, start_idx: int, end_idx: int, task: Optional["Task"] = None) -> int:
        return allocated_slots(self, start_idx, end_idx, task)

    def getFreeSlots(self, start_idx: int, end_idx: int) -> int:
        return free_slots(self, start_idx, end_idx)

    def getWorkSlots(self, start_idx: int, end_idx: int) -> int:
        return work_slots(self, start_idx, end_idx)
