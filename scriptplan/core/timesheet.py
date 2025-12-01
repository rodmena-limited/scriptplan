"""TimeSheets module for tracking work reports.

Contains TimeSheetRecord, TimeSheet, and TimeSheets classes for
managing time tracking and work reporting.
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from scriptplan.utils.message_handler import MessageHandler

if TYPE_CHECKING:
    pass


class TimeSheetRecord(MessageHandler):
    """Holds work-related bits of a time sheet specific to a single Task.

    For effort-based tasks, stores the remaining effort.
    For other tasks, stores the expected end date.
    For all tasks, stores the completed work during the reporting time frame.
    """

    def __init__(self, time_sheet: "TimeSheet", task: Any) -> None:
        """Create a new TimeSheetRecord.

        Args:
            time_sheet: The TimeSheet this record belongs to.
            task: Task object for existing tasks or ID string for new tasks.
        """
        self._task = task
        self._time_sheet = time_sheet
        time_sheet.add_record(self)

        self._work: Optional[int] = None  # Measured in time slots
        self._remaining: Optional[int] = None  # Measured in time slots
        self._expected_end: Any = None
        self._name: Optional[str] = None  # For new tasks
        self._status: Any = None  # JournalEntry reference
        self._priority: int = 0
        self.sourceFileInfo: Any = None

    @property
    def task(self) -> Any:
        return self._task

    @property
    def work(self) -> Optional[int]:
        return self._work

    @work.setter
    def work(self, value: Union[int, float]) -> None:
        """Set work value. Integer is slots, Float is percentage (0.0-1.0)."""
        if isinstance(value, int):
            self._work = value
        else:
            # Percentage value
            self._work = self._time_sheet.percentToSlots(value)

    @property
    def remaining(self) -> Optional[int]:
        return self._remaining

    @remaining.setter
    def remaining(self, value: Optional[int]) -> None:
        self._remaining = value

    @property
    def expectedEnd(self) -> Any:
        return self._expected_end

    @expectedEnd.setter
    def expectedEnd(self, value: Any) -> None:
        self._expected_end = value

    @property
    def status(self) -> Any:
        return self._status

    @status.setter
    def status(self, value: Any) -> None:
        self._status = value

    @property
    def priority(self) -> int:
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        self._priority = value

    @property
    def name(self) -> Optional[str]:
        return self._name

    @name.setter
    def name(self, value: Optional[str]) -> None:
        self._name = value

    def check(self) -> None:
        """Perform consistency checks on the record."""
        scIdx = self._time_sheet.scenarioIdx
        taskId = self.taskId

        # All records must have a 'work' attribute
        if self._work is None:
            self.error(
                "ts_no_work",
                f"The time sheet record for task {taskId} must "
                "have a 'work' attribute to specify how much was done "
                "for this task during the reported period.",
            )

        # Check if task is an existing Task object or a string ID
        if hasattr(self._task, "fullId"):
            # Existing task
            effort = self._task.get("effort", scIdx) if hasattr(self._task, "get") else 0
            if effort and effort > 0:
                if not self._remaining:
                    self.error(
                        "ts_no_remaining",
                        f"The time sheet record for task {taskId} must "
                        "have a 'remaining' attribute to specify how much "
                        "effort is left for this task.",
                    )
            else:
                if not self._expected_end:
                    self.error(
                        "ts_no_expected_end",
                        f"The time sheet record for task {taskId} must "
                        "have an 'end' attribute to specify the expected end "
                        "of this task.",
                    )
        else:
            # New task
            if self._remaining is None and self._expected_end is None:
                self.error("ts_no_rem_or_end", f"New task {taskId} requires either a 'remaining' or a 'end' attribute.")

        if self._work and self._work >= self._time_sheet.daysToSlots(1) and self._status is None:
            self.error(
                "ts_no_status_work", f"You must specify a status for task {taskId}. It was worked on for a day or more."
            )

        if self._status and hasattr(self._status, "headline") and not self._status.headline:
            self.error("ts_no_headline", f"You must provide a headline for the status of task {taskId}")

    def warnOnDelta(self, startIdx: int, endIdx: int) -> None:
        """Warn about differences between planned and actual work."""
        if self._task is None:
            return

        resource = self._time_sheet.resource
        project = resource.project if hasattr(resource, "project") else None
        if not project:
            return

        if isinstance(self._task, str):
            # New task request
            remaining_str: str
            if self._remaining is not None:
                remaining_str = f"Remaining: {self._time_sheet.slotsToDays(self._remaining)}d"
            else:
                remaining_str = f"End: {self._expected_end}"
            work_days = self._time_sheet.slotsToDays(self._work) if self._work else 0
            self.warning(
                "ts_res_new_task",
                f"{resource.name} is requesting a new task:\n"
                f"  ID: {self._task}\n"
                f"  Name: {self._name}\n"
                f"  Work: {work_days}d  "
                f"{remaining_str}",
            )
            return

        # Compare actual vs planned work
        scenarioIdx = self._time_sheet.scenarioIdx
        if hasattr(self._task, "getEffectiveWork"):
            plannedWork = self._task.getEffectiveWork(scenarioIdx, startIdx, endIdx, resource)
            scheduleGranularity = project.get("scheduleGranularity", 3600) if hasattr(project, "get") else 3600
            work_val = self._work if self._work else 0
            work: float
            if hasattr(project, "convertToDailyLoad"):
                work = project.convertToDailyLoad(work_val * scheduleGranularity)
            else:
                work = float(work_val)

            if work != plannedWork:
                direction = "less" if work < plannedWork else "more"
                self.warning(
                    "ts_res_work_delta",
                    f"{resource.name} worked {direction} on {self._task.fullId}\n{work}d instead of {plannedWork}d",
                )

    @property
    def taskId(self) -> str:
        """Return the task ID."""
        if hasattr(self._task, "fullId"):
            return str(self._task.fullId)
        return str(self._task)

    def actualWorkPercent(self) -> float:
        """Return reported work as percentage (0.0 - 100.0) of average working time."""
        if self._work is None:
            return 0.0
        total = self._time_sheet.totalGrossWorkingSlots
        if total == 0:
            return 0.0
        return (float(self._work) / total) * 100.0

    def planWorkPercent(self) -> float:
        """Return planned work as percentage (0.0 - 100.0) of average working time."""
        resource = self._time_sheet.resource
        if not hasattr(resource, "project"):
            return 0.0

        project = resource.project
        scenarioIdx = self._time_sheet.scenarioIdx
        interval = self._time_sheet.interval

        if hasattr(project, "dateToIdx"):
            startIdx = project.dateToIdx(interval.start)
            endIdx = project.dateToIdx(interval.end)
        else:
            return 0.0

        if hasattr(resource, "getAllocatedSlots"):
            allocated = resource.getAllocatedSlots(scenarioIdx, startIdx, endIdx, self._task)
            total = self._time_sheet.totalGrossWorkingSlots
            if total == 0:
                return 0.0
            return (float(allocated) / total) * 100.0
        return 0.0

    def actualRemaining(self) -> float:
        """Return reported remaining effort in days."""
        if self._remaining is None:
            return 0.0
        resource = self._time_sheet.resource
        if not hasattr(resource, "project"):
            return float(self._remaining)

        project = resource.project
        scheduleGranularity = project.get("scheduleGranularity", 3600) if hasattr(project, "get") else 3600
        if hasattr(project, "convertToDailyLoad"):
            result = project.convertToDailyLoad(self._remaining * scheduleGranularity)
            return float(result)
        return float(self._remaining)

    def planRemaining(self) -> float:
        """Return remaining effort according to plan."""
        resource = self._time_sheet.resource
        if not hasattr(resource, "project") or not hasattr(self._task, "getEffectiveWork"):
            return 0.0

        project = resource.project
        scenarioIdx = self._time_sheet.scenarioIdx

        if hasattr(project, "dateToIdx"):
            startIdx = project.dateToIdx(project.get("now"))
            endIdx = project.dateToIdx(self._task.get("end", scenarioIdx))
            result = self._task.getEffectiveWork(scenarioIdx, startIdx, endIdx, resource)
            return float(result)
        return 0.0

    def actualEnd(self) -> Any:
        """Return reported expected end of task."""
        return self._expected_end

    def planEnd(self) -> Any:
        """Return planned end of task."""
        if hasattr(self._task, "get"):
            return self._task.get("end", self._time_sheet.scenarioIdx)
        return None


class TimeSheet(MessageHandler):
    """Stores work-related bits of a time sheet.

    Holds TimeSheetRecord objects for each task.
    Always bound to an existing Resource.
    """

    def __init__(self, resource: Any, interval: Any, scenarioIdx: int) -> None:
        """Create a new TimeSheet.

        Args:
            resource: The Resource this time sheet belongs to.
            interval: The time interval covered by this time sheet.
            scenarioIdx: The scenario index.
        """
        if not resource:
            raise ValueError("Illegal resource")
        self._resource = resource

        if interval is None:
            raise ValueError("Interval undefined")
        self._interval = interval

        if scenarioIdx is None:
            raise ValueError("Scenario index undefined")
        self._scenarioIdx = scenarioIdx

        self.sourceFileInfo: Any = None
        self._percentageUsed = False
        self._records: list[TimeSheetRecord] = []

    @property
    def resource(self) -> Any:
        return self._resource

    @property
    def interval(self) -> Any:
        return self._interval

    @property
    def scenarioIdx(self) -> int:
        return self._scenarioIdx

    @property
    def records(self) -> list[TimeSheetRecord]:
        return self._records

    def add_record(self, record: TimeSheetRecord) -> None:
        """Add a TimeSheetRecord to this time sheet."""
        for r in self._records:
            if r.task == record.task:
                self.error("ts_duplicate_task", f"Duplicate records for task {r.taskId}")
        self._records.append(record)

    def __lshift__(self, record: TimeSheetRecord) -> "TimeSheet":
        """Add a record using << operator."""
        self.add_record(record)
        return self

    def check(self) -> None:
        """Perform consistency checks on all records."""
        totalSlots = 0
        for record in self._records:
            record.check()
            if record.work:
                totalSlots += record.work

        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project:
            return

        trackingScenarioIdx = project.get("trackingScenarioIdx") if hasattr(project, "get") else None
        if not trackingScenarioIdx:
            self.error("ts_no_tracking_scenario", "No trackingscenario has been defined.")
            return

        efficiency = self._resource.get("efficiency", self._scenarioIdx) if hasattr(self._resource, "get") else 1.0
        if efficiency and efficiency > 0.0:
            targetSlots = self.totalNetWorkingSlots
            delta = 1  # Acceptable rounding error

            if totalSlots < (targetSlots - delta):
                self.error(
                    "ts_work_too_low",
                    f"The total work to be reported for this time sheet "
                    f"is {self._workWithUnit(targetSlots)} but only "
                    f"{self._workWithUnit(totalSlots)} were reported.",
                )

            if totalSlots > (targetSlots + delta):
                self.error(
                    "ts_work_too_high",
                    f"The total work to be reported for this time sheet "
                    f"is {self._workWithUnit(targetSlots)} but "
                    f"{self._workWithUnit(totalSlots)} were reported.",
                )
        else:
            if totalSlots > 0:
                self.error("ts_work_not_null", "The reported work for non-working resources must be 0.")

    def warnOnDelta(self) -> None:
        """Warn about all delta differences in records."""
        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project or not hasattr(project, "dateToIdx"):
            return

        startIdx = project.dateToIdx(self._interval.start)
        endIdx = project.dateToIdx(self._interval.end)

        for record in self._records:
            record.warnOnDelta(startIdx, endIdx)

    @property
    def totalGrossWorkingSlots(self) -> int:
        """Compute total potential working time slots during report period."""
        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project:
            return 0

        # Calculate weeks in report
        duration = self._interval.end - self._interval.start
        if hasattr(duration, "total_seconds"):
            weeksToReport = duration.total_seconds() / (60 * 60 * 24 * 7)
        else:
            weeksToReport = float(duration) / (60 * 60 * 24 * 7)

        weeklyWorkingDays = getattr(project, "weeklyWorkingDays", 5)
        return self.daysToSlots(int(weeklyWorkingDays * weeksToReport))

    @property
    def totalNetWorkingSlots(self) -> int:
        """Compute total actual working time slots of the Resource."""
        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project or not hasattr(project, "dateToIdx"):
            return 0

        startIdx = project.dateToIdx(self._interval.start)
        endIdx = project.dateToIdx(self._interval.end)

        allocated = 0
        free = 0
        if hasattr(self._resource, "getAllocatedSlots"):
            allocated = self._resource.getAllocatedSlots(self._scenarioIdx, startIdx, endIdx, None)
        if hasattr(self._resource, "getFreeSlots"):
            free = self._resource.getFreeSlots(self._scenarioIdx, startIdx, endIdx)

        return allocated + free

    def percentToSlots(self, value: float) -> int:
        """Convert allocation percentage to time slots."""
        self._percentageUsed = True
        return int(self.totalGrossWorkingSlots * value)

    def slotsToPercent(self, slots: int) -> float:
        """Compute what percent the slots are of total working slots."""
        total = self.totalGrossWorkingSlots
        if total == 0:
            return 0.0
        return float(slots) / total

    def slotsToDays(self, slots: int) -> float:
        """Convert slots to days."""
        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project:
            return float(slots)

        scheduleGranularity = project.get("scheduleGranularity", 3600) if hasattr(project, "get") else 3600
        dailyWorkingHours = getattr(project, "dailyWorkingHours", 8)
        return slots * scheduleGranularity / (60 * 60 * dailyWorkingHours)

    def daysToSlots(self, days: int) -> int:
        """Convert days to slots."""
        project = self._resource.project if hasattr(self._resource, "project") else None
        if not project:
            return days

        dailyWorkingHours = getattr(project, "dailyWorkingHours", 8)
        scheduleGranularity = project.get("scheduleGranularity", 3600) if hasattr(project, "get") else 3600
        return int((days * 60 * 60 * dailyWorkingHours) / scheduleGranularity)

    def _workWithUnit(self, slots: int) -> str:
        """Format work with appropriate unit."""
        if self._percentageUsed:
            return f"{int(self.slotsToPercent(slots) * 100.0)}%"
        else:
            return f"{self.slotsToDays(slots)} days"


class TimeSheets(list[TimeSheet]):
    """Collection of all time sheets for a project."""

    def __init__(self) -> None:
        super().__init__()

    def check(self) -> None:
        """Check all time sheets."""
        for sheet in self:
            sheet.check()

    def warnOnDelta(self) -> None:
        """Warn about deltas in all time sheets."""
        for sheet in self:
            sheet.warnOnDelta()
