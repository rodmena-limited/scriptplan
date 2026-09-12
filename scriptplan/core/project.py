from datetime import timedelta
from typing import Any, Optional, Union

from scriptplan.core.journal import Journal

from scriptplan.core.property import (
    AlertLevelDefinitions,
    AttributeBase,
    AttributeDefinition,
    BooleanAttribute,
    ColumnListAttribute,
    DateAttribute,
    FlagListAttribute,
    FloatAttribute,
    FormatListAttribute,
    IntegerAttribute,
    LeaveList,
    LeaveListAttribute,
    ListAttribute,
    LogicalExpressionAttribute,
    PropertyAttribute,
    PropertySet,
    RealFormat,
    ResourceListAttribute,
    RichTextAttribute,
    ScenarioListAttribute,
    ShiftAssignmentsAttribute,
    SortListAttribute,
    StringAttribute,
    SymbolAttribute,
    SymbolListAttribute,
    TaskDepListAttribute,
)
from scriptplan.core.project_attributes import (
    define_account_attributes,
    define_report_attributes,
    define_resource_attributes,
    define_scenario_attributes,
    define_shift_attributes,
    define_task_attributes,
)
from scriptplan.core.project_calendar import (
    date_to_idx,
    idx_to_date,
    init_scoreboards,
    is_default_working_time,
    is_working_time,
    scoreboard_size,
)
from scriptplan.core.project_tree import (
    propagate_alap_mode,
    propagate_container_end_dates,
    update_container_task_status,
)
from scriptplan.core.scenario import Scenario
from scriptplan.core.timezones import from_utc
from scriptplan.core.timesheet import TimeSheets
from scriptplan.scheduler.scoreboard import Scoreboard
from scriptplan.utils.data_cache import FileList
from scriptplan.scheduler.postcheck import run_post_checks
from scriptplan.scheduler.preflight import check_no_cycles
from scriptplan.utils.message_handler import MessageHandler, get_message_handler_instance
from scriptplan.utils.time import TjTime


# The default working calendar when the project declares none: weekdays,
# nine to five, in the project's own timezone.
DEFAULT_WORK_START_HOUR = 9
DEFAULT_WORK_END_HOUR = 17


class Project(MessageHandler):
    """
    This class implements objects that hold all project properties. Project
    generally consist of resources, tasks and a number of other optional
    properties.
    """

    def __init__(self, id: Optional[str], name: str, version: str) -> None:
        self.id: Optional[str] = id
        self.name: str = name
        self.version: str = version

        # How attribute values set from here on are recorded. Scoped to this
        # project so that building or scheduling another one in the same
        # process cannot mislabel this one's attributes.
        self.attributeMode: int = AttributeBase.PROVIDED

        self.attributes: dict[str, Any] = {
            "alertLevels": AlertLevelDefinitions(),
            "auxdir": "",
            "copyright": None,
            "costaccount": None,
            "currency": "EUR",
            "currencyFormat": RealFormat(["-", "", "", ",", 2]),
            "dailyworkinghours": 8.0,
            "end": None,
            "markdate": None,
            "flags": [],
            "journal": Journal(self),
            "limits": None,
            "leaves": LeaveList(),
            "loadUnit": "days",
            "name": name,
            "navigators": {},
            "now": TjTime().align(3600),
            "numberFormat": RealFormat(["-", "", "", ".", 1]),
            "priority": 500,
            "projectid": id or "prj",
            "projectids": [id] if id else ["prj"],
            "rate": 0.0,
            "revenueaccount": None,
            "scheduleGranularity": self.maxScheduleGranularity(),
            "shortTimeFormat": "%H:%M",
            "start": None,
            "timeFormat": "%Y-%m-%d",
            "timeOffId": None,
            "timeOffName": None,
            "timingresolution": 60 * 60,
            "timezone": TjTime.timeZone(),
            "trackingscenario": None,
            "version": version,
            "weekStartsMonday": False,
            "workinghours": None,
            "yearlyworkingdays": 260.714,
            "yresolution": 1,
        }

        self.accounts: PropertySet = PropertySet(self, True)
        self._define_account_attributes()

        self.shifts: PropertySet = PropertySet(self, True)
        self._define_shift_attributes()

        self.resources: PropertySet = PropertySet(self, False)
        self._define_resource_attributes()

        self.tasks: PropertySet = PropertySet(self, False)
        self._define_task_attributes()

        self.reports: PropertySet = PropertySet(self, False)
        self._define_report_attributes()

        self.scenarios: PropertySet = PropertySet(self, True)
        self._define_scenario_attributes()

        # Scenario needs to be added AFTER attributes are defined
        Scenario(self, "plan", "Plan Scenario", None)

        self.inputFiles: FileList = FileList()
        self.timeSheets: TimeSheets = TimeSheets()

        self.scoreboard: Optional[Scoreboard] = None
        self.scoreboardNoLeaves: Optional[Scoreboard] = None

        self.reportContexts: list[Any] = []
        self.outputDir: str = "./"
        self.warnTsDeltas: bool = False

    def _define_scenario_attributes(self) -> None:
        define_scenario_attributes(self.scenarios)

    def _define_account_attributes(self) -> None:
        define_account_attributes(self.accounts)

    def _define_shift_attributes(self) -> None:
        define_shift_attributes(self.shifts)

    def _define_resource_attributes(self) -> None:
        define_resource_attributes(self.resources)

    def _define_task_attributes(self) -> None:
        define_task_attributes(self.tasks)

    def _define_report_attributes(self) -> None:
        define_report_attributes(self.reports)

    def _propagateContainerEndDates(self, scIdx: int) -> None:
        propagate_container_end_dates(self, scIdx)

    def _updateContainerTaskStatus(self, scIdx: int) -> None:
        update_container_task_status(self, scIdx)

    def _propagateALAPMode(self, scIdx: int) -> None:
        propagate_alap_mode(self, scIdx)

    def scenarioCount(self) -> Any:
        return self.scenarios.items()

    def scenario(self, arg: Union[int, str]) -> Optional[Any]:
        if isinstance(arg, int):
            for sc in self.scenarios:
                if sc.sequenceNo - 1 == arg:
                    return sc
        else:
            return self.scenarios[arg]
        return None

    @staticmethod
    def maxScheduleGranularity() -> int:
        return 60 * 60

    def schedule(self) -> bool:
        """Schedule every active scenario.

        Returns True only if every task in every active scenario was placed.
        When a task cannot be scheduled the reason is recorded as an error on
        the message handler and False is returned; the caller decides whether
        to render a partial result.

        A structurally malformed project (a dependency cycle) raises rather
        than returning False: there is nothing to schedule and no partial
        result worth rendering.
        """
        self.initScoreboards()

        for p in [self.accounts, self.shifts, self.resources, self.tasks]:
            p.index()

        self.scheduleErrors = []

        if self.tasks.empty():
            # Nothing to schedule is a valid, complete result.
            return True

        handler = get_message_handler_instance()
        previous_mode = self.attributeMode
        ok = True
        try:
            for sc in self.scenarios:
                # Skip disabled scenarios if 'active' is false (default true if not set)
                if not sc.get("active") and sc.get("active") is not None:
                    continue

                scIdx: int = sc.sequenceNo - 1

                # Propagate inherited values
                self.attributeMode = AttributeBase.INHERITED
                self.prepareScenario(scIdx)

                # Reject a malformed dependency graph before scheduling it.
                check_no_cycles(self.tasks, scIdx)

                # Schedule. Errors are collected so that one unschedulable task
                # does not hide the others.
                self.attributeMode = AttributeBase.COMPUTED
                with handler.collecting():
                    if not self.scheduleScenario(scIdx):
                        ok = False

                    # Finish
                    self.finishScenario(scIdx)

                    # Constraints that can only be judged once everything is
                    # placed: a maximum gap, a deadline.
                    before = handler.errors
                    run_post_checks(self, scIdx)
                    if handler.errors > before:
                        ok = False
        finally:
            self.attributeMode = previous_mode

        return ok

    def prepareScenario(self, scIdx: int) -> None:
        # Simplified preparation
        # In Ruby: computes criticalness, propagates initial values, checks loops

        # Apply project-level scheduling mode (alap/asap) to all tasks
        # Note: task-level 'scheduling asap/alap' overrides project-level
        # We track which tasks have explicit scheduling via _explicit_scheduling attr
        project_scheduling: Optional[str] = self.attributes.get("scheduling")
        if project_scheduling == "alap":
            for task in self.tasks:
                # Only override if task doesn't have explicit scheduling attribute
                if task.leaf() and not getattr(task, "_explicit_scheduling", False):
                    task[("forward", scIdx)] = False  # ALAP mode

        # Propagate container end dates to leaf children for ALAP mode
        # In ALAP, container end dates act as constraints for children
        self._propagateContainerEndDates(scIdx)

        # We need to ensure tasks are ready
        for task in self.tasks:
            task.prepareScheduling(scIdx)  # type: ignore[attr-defined]

        for resource in self.resources:
            resource.prepareScheduling(scIdx)  # type: ignore[attr-defined]

    def finishScenario(self, scIdx: int) -> None:
        for task in self.tasks:
            if not task.parent:
                task.finishScheduling(scIdx)  # type: ignore[attr-defined]

        for resource in self.resources:
            if not resource.parent:
                resource.finishScheduling(scIdx)  # type: ignore[attr-defined]

    def scheduleScenario(self, scIdx: int) -> bool:
        all_tasks: list[Any] = list(self.tasks)

        # First, handle milestones - they just need end=start (or start=end)
        # A milestone is either:
        # 1. Explicitly marked with milestone attribute, or
        # 2. Has start or end set, but no effort/duration/length (implicit milestone)
        for task in all_tasks:
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

            if is_explicit_milestone or is_implicit_milestone:
                # Only mark as scheduled if we can set both dates
                # Milestones with dependencies but no dates need to go through normal scheduling
                if start and not end:
                    task[("end", scIdx)] = start
                    task[("scheduled", scIdx)] = True
                elif end and not start:
                    task[("start", scIdx)] = end
                    task[("scheduled", scIdx)] = True
                elif start and end:
                    task[("scheduled", scIdx)] = True
                # else: milestone with no dates - let it be scheduled by the main loop

        # Propagate ALAP mode through dependency chains
        # If task B depends on task A, and B is ALAP with fixed end,
        # then A should also be ALAP (scheduled as late as possible)
        self._propagateALAPMode(scIdx)

        # Only care about leaf tasks that aren't scheduled already
        tasks: list[Any] = [t for t in all_tasks if t.leaf() and not t.get("scheduled", scIdx)]

        # Sorting
        # Primary: priority (desc), Secondary: pathcriticalness (desc), Tertiary: seqno (asc)
        # Note: attributes might return None, need safe access for sorting
        def sort_key(t: Any) -> tuple[int, float, int]:
            prio = t.get("priority", scIdx) or 500
            crit = t.get("pathcriticalness", scIdx) or 0.0
            seq = t.get("seqno") or 0
            return (-prio, -crit, seq)

        tasks.sort(key=sort_key)

        failedTasks: list[Any] = []

        while tasks:
            taskToRemove: Optional[Any] = None
            for task in tasks:
                # Task not ready? Ignore it.
                if not task.readyForScheduling(scIdx):
                    continue

                if not task.schedule(scIdx):
                    self._reportUnscheduled(task, scIdx, "ran outside the project window")
                    failedTasks.append(task)

                taskToRemove = task
                break

            if taskToRemove:
                tasks.remove(taskToRemove)
                # After scheduling a leaf, check if any container tasks should be marked scheduled
                self._updateContainerTaskStatus(scIdx)
            elif tasks and self._breakDeadlock(tasks, scIdx):
                # An unanchored backward task was waiting on a forward task
                # that was waiting on it. One of them was turned around, so
                # there is progress to be made; go round again.
                continue
            elif tasks:
                # Nothing is ready and nothing was placed this pass: the
                # remaining tasks are waiting on each other or on a constraint
                # that will never be satisfied.
                stalled = [t for t in tasks if t not in failedTasks]
                for task in stalled:
                    self._reportUnscheduled(task, scIdx, "no ready predecessor or successor")
                failedTasks.extend(stalled)
                break
            else:
                break

        if failedTasks:
            return False

        return True

    def _breakDeadlock(self, tasks: list[Any], scIdx: int) -> bool:
        """Turn one stuck backward task around, if that unblocks the schedule.

        A task scheduled as late as possible waits to learn when its
        successors start. A task scheduled as early as possible waits to learn
        when its predecessors finish. Put one of each in a chain with no fixed
        end and they wait for each other for ever.

        A backward task with no end of its own, and no successor that can give
        it one, has nothing to be late against. It is scheduled forwards
        instead, and the reader is told, which beats reporting a deadlock and
        scheduling nothing.
        """
        for task in tasks:
            if task.get("forward", scIdx) is not False:
                continue
            if task.get("end", scIdx):
                continue
            scenario = task.data[scIdx] if task.data else None
            successors = scenario._getSuccessors() if scenario is not None else []
            if any(successor.get("scheduled", scIdx) for successor in successors):
                continue
            task[("forward", scIdx)] = True
            self.warning(
                "alap_degraded",
                f"Task '{task.fullId}' asks to be scheduled as late as possible, but nothing "
                f"fixes when it must end: it has no end date and no scheduled successor. "
                f"It has been scheduled as early as possible instead. Give it an end date, "
                f"or a successor that has one, to schedule it backwards.",
            )
            return True
        return False

    def _reportUnscheduled(self, task: Any, scIdx: int, reason: str) -> None:
        """Record why one task could not be placed, naming the task."""
        task_id = getattr(task, "fullId", None) or getattr(task, "id", None) or repr(task)
        detail = reason
        if reason == "ran outside the project window":
            detail = (
                f"{reason} ({self.attributes['start']} to {self.attributes['end']}); "
                "it needs more time or more resource availability than the project allows"
            )
        message = f"Task '{task_id}' could not be scheduled: {detail}"
        self.scheduleErrors.append((task_id, detail))
        self.error("unscheduled_task", message, data=task_id)

    def initScoreboards(self) -> None:
        init_scoreboards(self)

    def _isDefaultWorkingTime(self, date: Optional[Any]) -> bool:
        return is_default_working_time(self, date)

    def isWorkingTime(self, sbIdx: int) -> bool:
        return is_working_time(self, sbIdx)

    def scoreboardSize(self) -> int:
        return scoreboard_size(self)

    def dateToIdx(self, date: Any, forceIntoProject: bool = True) -> int:
        return date_to_idx(self, date, forceIntoProject)

    def idxToDate(self, idx: int) -> Optional[Any]:
        return idx_to_date(self, idx)

    def addReport(self, report: Any) -> None:
        """
        Add a report to the project's report list.
        This is called automatically by Report.__init__.

        Args:
            report: The Report object to add
        """
        # Report is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addAccount(self, account: Any) -> None:
        """
        Add an account to the project's account list.
        This is called automatically by Account.__init__.

        Args:
            account: The Account object to add
        """
        # Account is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addShift(self, shift: Any) -> None:
        """
        Add a shift to the project's shift list.
        This is called automatically by Shift.__init__.

        Args:
            shift: The Shift object to add
        """
        # Shift is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addResource(self, resource: Any) -> None:
        """
        Add a resource to the project's resource list.
        This is called automatically by Resource.__init__.

        Args:
            resource: The Resource object to add
        """
        # Resource is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addTask(self, task: Any) -> None:
        """
        Add a task to the project's task list.
        This is called automatically by Task.__init__.

        Args:
            task: The Task object to add
        """
        # Task is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def __getitem__(self, key: str) -> Any:
        """
        Get a project attribute.

        Args:
            key: Attribute name

        Returns:
            Attribute value or None
        """
        return self.attributes.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set a project attribute.

        Args:
            key: Attribute name
            value: Attribute value
        """
        self.attributes[key] = value
        # When timingresolution is set, also update scheduleGranularity
        if key == "timingresolution":
            self.attributes["scheduleGranularity"] = value
