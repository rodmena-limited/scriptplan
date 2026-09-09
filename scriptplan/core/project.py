from datetime import timedelta
from typing import Any, Optional, Union

from scriptplan.core.journal import Journal

# Try to import Cython-optimized functions
try:
    from scriptplan._cython.time_utils_cy import (
        project_date_to_idx,
        project_idx_to_date,
    )

    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False
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
from scriptplan.core.scenario import Scenario
from scriptplan.core.timesheet import TimeSheets
from scriptplan.scheduler.scoreboard import Scoreboard
from scriptplan.utils.data_cache import FileList
from scriptplan.scheduler.preflight import check_no_cycles
from scriptplan.utils.message_handler import MessageHandler, get_message_handler_instance
from scriptplan.utils.time import TjTime


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

        if hasattr(AttributeBase, "setMode"):
            AttributeBase.setMode(0)

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
        attrs: list[list[Any]] = [
            ["active", "Enabled", BooleanAttribute, True, False, False, True],
            ["ownbookings", "Own Bookings", BooleanAttribute, False, False, False, True],
            ["projection", "Projection Mode", BooleanAttribute, True, False, False, False],
        ]
        for a in attrs:
            self.scenarios.addAttributeType(AttributeDefinition(*a))

    def _define_account_attributes(self) -> None:
        attrs: list[list[Any]] = [
            # ID           Name            Type                     Inh   InhPrj Scen  Default
            ["aggregate", "Aggregate", SymbolAttribute, True, False, False, "tasks"],
            ["bsi", "BSI", StringAttribute, False, False, False, ""],
            ["credits", "Credits", ListAttribute, False, False, True, []],
            ["index", "Index", IntegerAttribute, False, False, False, -1],
            ["flags", "Flags", FlagListAttribute, True, False, True, []],
            ["tree", "Tree Index", StringAttribute, False, False, False, ""],
        ]
        for a in attrs:
            self.accounts.addAttributeType(AttributeDefinition(*a))

    def _define_shift_attributes(self) -> None:
        attrs: list[list[Any]] = [
            # ID           Name            Type                     Inh   InhPrj Scen  Default
            ["bsi", "BSI", StringAttribute, False, False, False, ""],
            ["index", "Index", IntegerAttribute, False, False, False, -1],
            ["leaves", "Leaves", LeaveListAttribute, True, True, True, []],
            ["replace", "Replace", BooleanAttribute, True, False, True, False],
            ["timezone", "Time Zone", StringAttribute, True, True, True, TjTime.timeZone()],
            ["tree", "Tree Index", StringAttribute, False, False, False, ""],
            ["workinghours", "Working Hours", ShiftAssignmentsAttribute, True, True, True, None],
        ]
        for a in attrs:
            self.shifts.addAttributeType(AttributeDefinition(*a))

    def _define_resource_attributes(self) -> None:
        # Add attributes required by ResourceScenario
        attrs: list[list[Any]] = [
            ["alloctdeffort", "Allocated Effort", IntegerAttribute, True, False, True, 0],
            ["booking", "Booking", ResourceListAttribute, True, False, True, []],
            ["bsi", "BSI", StringAttribute, False, False, False, ""],
            ["email", "Email", StringAttribute, False, False, False, ""],
            ["index", "Index", IntegerAttribute, False, False, False, -1],
            ["chargeset", "Charge Set", StringAttribute, True, False, True, []],
            ["criticalness", "Criticalness", FloatAttribute, False, False, True, 0.0],
            ["directreports", "Direct Reports", ResourceListAttribute, True, False, True, []],
            ["duties", "Duties", TaskDepListAttribute, True, False, True, []],
            ["efficiency", "Efficiency", FloatAttribute, True, False, True, 1.0],
            ["effort", "Effort", IntegerAttribute, True, False, True, 0],
            ["flags", "Flags", FlagListAttribute, True, False, True, []],
            ["leaves", "Leaves", LeaveListAttribute, True, False, True, []],  # Changed to LeaveListAttribute
            ["leaveallowances", "Leave Allowances", AttributeBase, True, False, True, None],  # Placeholder
            ["limits", "Limits", AttributeBase, True, False, True, None],  # Placeholder
            ["managers", "Managers", ResourceListAttribute, True, False, True, []],
            ["note", "Note", StringAttribute, False, False, False, None],
            ["rate", "Rate", FloatAttribute, True, False, True, 0.0],
            ["reports", "Reports", ResourceListAttribute, True, False, True, []],
            ["shifts", "Shifts", ShiftAssignmentsAttribute, True, False, True, None],
            ["timezone", "Time Zone", StringAttribute, True, False, True, None],
            ["workinghours", "Working Hours", AttributeBase, True, False, True, None],
        ]
        for a in attrs:
            self.resources.addAttributeType(AttributeDefinition(*a))

    def _define_task_attributes(self) -> None:
        attrs: list[list[Any]] = [
            ["allocate", "Allocate", ListAttribute, True, False, True, []],
            ["assignedresources", "Assigned Resources", ListAttribute, False, False, True, []],
            ["booking", "Booking", ResourceListAttribute, True, False, True, []],
            ["bsi", "BSI", StringAttribute, False, False, False, ""],
            ["charge", "Charge", FloatAttribute, True, False, True, 0.0],
            ["chargeset", "Charge Set", StringAttribute, True, False, True, []],
            ["complete", "Complete", FloatAttribute, True, False, True, 0.0],
            ["competitors", "Competitors", ListAttribute, True, False, True, []],
            ["criticalness", "Criticalness", FloatAttribute, False, False, True, 0.0],
            ["depends", "Dependencies", TaskDepListAttribute, True, False, True, []],
            ["duration", "Duration", IntegerAttribute, True, False, True, 0],
            ["effort", "Effort", IntegerAttribute, True, False, True, 0],
            ["effortdone", "Effort Done", IntegerAttribute, True, False, True, 0],
            ["effortleft", "Effort Left", IntegerAttribute, True, False, True, 0],
            ["end", "End", DateAttribute, False, False, True, None],
            ["flags", "Flags", FlagListAttribute, True, False, True, []],
            ["forward", "Forward", BooleanAttribute, True, False, True, True],
            ["gauge", "Gauge", StringAttribute, True, False, True, None],
            ["index", "Index", IntegerAttribute, False, False, False, -1],
            ["length", "Length", IntegerAttribute, True, False, True, 0],
            ["limits", "Limits", PropertyAttribute, True, False, True, None],
            ["maxend", "Max End", DateAttribute, True, False, True, None],
            ["maxstart", "Max Start", DateAttribute, True, False, True, None],
            ["minend", "Min End", DateAttribute, True, False, True, None],
            ["minstart", "Min Start", DateAttribute, True, False, True, None],
            ["milestone", "Milestone", BooleanAttribute, True, False, True, False],
            ["note", "Note", StringAttribute, False, False, False, None],
            ["pathcriticalness", "Path Criticalness", FloatAttribute, False, False, True, 0.0],
            ["precedes", "Precedes", TaskDepListAttribute, True, False, True, []],
            ["priority", "Priority", IntegerAttribute, True, False, True, 500],
            ["projectionmode", "Projection Mode", BooleanAttribute, True, False, True, False],
            ["responsible", "Responsible", ListAttribute, True, False, True, []],
            ["scheduled", "Scheduled", BooleanAttribute, True, False, True, False],
            ["shifts", "Shifts", ShiftAssignmentsAttribute, True, False, True, None],
            ["start", "Start", DateAttribute, True, False, True, None],
            ["status", "Status", StringAttribute, True, False, True, ""],
        ]
        for a in attrs:
            self.tasks.addAttributeType(AttributeDefinition(*a))

    def _define_report_attributes(self) -> None:
        attrs: list[list[Any]] = [
            # ID               Name                Type                     Inh    InhPrj  Scen   Default
            ["accountRoot", "Account Root", StringAttribute, True, False, False, None],
            ["auxDir", "Aux Directory", StringAttribute, True, True, False, ""],
            ["balance", "Balance", ListAttribute, True, False, False, []],
            ["caption", "Caption", RichTextAttribute, True, False, False, None],
            ["center", "Center", RichTextAttribute, True, False, False, None],
            ["columns", "Columns", ColumnListAttribute, True, False, False, []],
            ["currencyFormat", "Currency Format", StringAttribute, True, True, False, None],
            ["end", "End Date", DateAttribute, True, True, False, None],
            ["epilog", "Epilog", RichTextAttribute, True, False, False, None],
            ["flags", "Flags", FlagListAttribute, True, False, False, []],
            ["footer", "Footer", RichTextAttribute, True, False, False, None],
            ["formats", "Formats", FormatListAttribute, True, False, False, []],
            ["header", "Header", RichTextAttribute, True, False, False, None],
            ["headline", "Headline", RichTextAttribute, True, False, False, None],
            ["hideAccount", "Hide Account", LogicalExpressionAttribute, True, False, False, None],
            ["hideResource", "Hide Resource", LogicalExpressionAttribute, True, False, False, None],
            ["hideTask", "Hide Task", LogicalExpressionAttribute, True, False, False, None],
            ["interactive", "Interactive", BooleanAttribute, True, False, False, False],
            ["journalAttributes", "Journal Attributes", SymbolListAttribute, True, False, False, []],
            ["journalMode", "Journal Mode", SymbolAttribute, True, False, False, None],
            ["leafTasksOnly", "Leaf Tasks Only", BooleanAttribute, True, False, False, False],
            ["left", "Left", RichTextAttribute, True, False, False, None],
            ["loadUnit", "Load Unit", SymbolAttribute, True, True, False, "days"],
            ["numberFormat", "Number Format", StringAttribute, True, True, False, None],
            ["openNodes", "Open Nodes", ListAttribute, True, False, False, []],
            ["period", "Period", StringAttribute, True, True, False, None],
            ["prolog", "Prolog", RichTextAttribute, True, False, False, None],
            ["resourceRoot", "Resource Root", StringAttribute, True, False, False, None],
            ["right", "Right", RichTextAttribute, True, False, False, None],
            ["rollupAccount", "Rollup Account", LogicalExpressionAttribute, True, False, False, None],
            ["rollupResource", "Rollup Resource", LogicalExpressionAttribute, True, False, False, None],
            ["rollupTask", "Rollup Task", LogicalExpressionAttribute, True, False, False, None],
            ["scenarios", "Scenarios", ScenarioListAttribute, True, True, False, []],
            ["selfContained", "Self Contained", BooleanAttribute, True, False, False, False],
            ["showResources", "Show Resources", BooleanAttribute, True, False, False, False],
            ["showTasks", "Show Tasks", BooleanAttribute, True, False, False, False],
            ["sort", "Sort", SortListAttribute, True, False, False, []],
            ["sortAccounts", "Sort Accounts", SortListAttribute, True, False, False, []],
            ["sortResources", "Sort Resources", SortListAttribute, True, False, False, []],
            ["sortTasks", "Sort Tasks", SortListAttribute, True, False, False, []],
            ["start", "Start Date", DateAttribute, True, True, False, None],
            ["taskRoot", "Task Root", StringAttribute, True, False, False, None],
            ["timeFormat", "Time Format", StringAttribute, True, True, False, "%Y-%m-%d"],
            ["timeZone", "Time Zone", StringAttribute, True, True, False, None],
            ["title", "Title", StringAttribute, True, False, False, None],
            ["width", "Width", IntegerAttribute, True, False, False, None],
        ]
        for a in attrs:
            self.reports.addAttributeType(AttributeDefinition(*a))

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
        previous_mode = AttributeBase.mode()
        ok = True
        try:
            for sc in self.scenarios:
                # Skip disabled scenarios if 'active' is false (default true if not set)
                if not sc.get("active") and sc.get("active") is not None:
                    continue

                scIdx: int = sc.sequenceNo - 1

                # Propagate inherited values
                AttributeBase.setMode(1)
                self.prepareScenario(scIdx)

                # Reject a malformed dependency graph before scheduling it.
                check_no_cycles(self.tasks, scIdx)

                # Schedule. Errors are collected so that one unschedulable task
                # does not hide the others.
                AttributeBase.setMode(2)
                with handler.collecting():
                    if not self.scheduleScenario(scIdx):
                        ok = False

                # Finish
                self.finishScenario(scIdx)
        finally:
            AttributeBase.setMode(previous_mode)

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

    def _propagateContainerEndDates(self, scIdx: int) -> None:
        """
        Propagate container task end dates to their leaf children as constraints.

        In ALAP mode, if a container has an end date, only the "terminal" tasks
        (those with no successors within the container) should get the end constraint.
        Other tasks will get their end constraints from their successors.

        Special handling for `onstart` dependencies in ALAP mode:
        - `A depends B { onstart }` means A.start >= B.start
        - In ALAP, this translates to: A must END before B can START
        - So B is the anchor (terminal), not A
        - A derives its end from B's start
        """
        # First, identify which tasks have successors via normal (finish-to-start) dependencies
        # For onstart dependencies in ALAP, the dependent task (A) derives its END from
        # predecessor's START, so the predecessor (B) is the terminal task
        has_fs_successor: set[Any] = set()  # Tasks that are predecessors in finish-to-start deps
        has_onstart_dep: set[Any] = set()  # Tasks that have onstart dependencies (not terminal)

        for task in self.tasks:
            if not task.leaf():
                continue
            deps = task.get("depends", scIdx) or []
            for dep in deps:
                if isinstance(dep, dict):
                    pred = dep.get("task")
                    onstart = dep.get("onstart", False)
                elif hasattr(dep, "task"):
                    pred = dep.task
                    onstart = getattr(dep, "onstart", False)
                else:
                    pred = dep
                    onstart = False

                if pred and hasattr(pred, "fullId"):
                    if onstart:
                        # For onstart deps in ALAP: the dependent task (this task)
                        # derives END from predecessor's START, so this task is NOT terminal
                        has_onstart_dep.add(task.fullId if hasattr(task, "fullId") else None)
                    else:
                        # Normal finish-to-start: predecessor has a successor
                        has_fs_successor.add(pred.fullId)

        def propagate_end_to_children(task: Any, container_end: Optional[Any]) -> None:
            """Recursively propagate end constraint down the task tree."""
            task_end = task.get("end", scIdx)
            # Use the most restrictive (earliest) end date
            effective_end = task_end if task_end else container_end

            if task.leaf():
                # Leaf task - apply the constraint if ALAP, no explicit end,
                # AND the task is terminal
                forward = task.get("forward", scIdx)
                task_id = task.fullId if hasattr(task, "fullId") else None

                # A task is terminal if:
                # 1. No finish-to-start successors (nothing depends on its END), AND
                # 2. No onstart dependencies (doesn't derive END from another task's START)
                is_terminal = (task_id not in has_fs_successor) and (task_id not in has_onstart_dep)

                if forward is False and not task_end and container_end and is_terminal:
                    task[("end", scIdx)] = container_end
            else:
                # Container - propagate to children
                for child in task.children:
                    propagate_end_to_children(child, effective_end)

        # Start from root tasks (no parent)
        for task in self.tasks:
            if task.parent is None:
                task_end = task.get("end", scIdx)
                if task_end:
                    propagate_end_to_children(task, task_end)

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

    def _updateContainerTaskStatus(self, scIdx: int) -> None:
        """Mark container tasks as scheduled when all their children are scheduled.

        Also compute start/end dates for container tasks based on children.
        """
        for task in self.tasks:
            if task.leaf():
                continue  # Skip leaf tasks

            if task.get("scheduled", scIdx):
                continue  # Already scheduled

            # Check if all children are scheduled
            children = task.children
            if not children:
                continue

            all_scheduled = all(child.get("scheduled", scIdx) for child in children)
            if not all_scheduled:
                continue

            # All children scheduled - mark container as scheduled
            # Compute start/end from children
            min_start: Optional[Any] = None
            max_end: Optional[Any] = None
            for child in children:
                child_start = child.get("start", scIdx)
                child_end = child.get("end", scIdx)
                if child_start and (min_start is None or child_start < min_start):
                    min_start = child_start
                if child_end and (max_end is None or child_end > max_end):
                    max_end = child_end

            if min_start:
                task[("start", scIdx)] = min_start
            if max_end:
                task[("end", scIdx)] = max_end
            task[("scheduled", scIdx)] = True

    def _propagateALAPMode(self, scIdx: int) -> None:
        """
        Propagate ALAP scheduling mode backward through dependency chains.

        When task B depends on task A, and B is ALAP with a fixed end date,
        task A should also be scheduled ALAP (as late as possible) to allow
        B to meet its deadline.

        This implements "backward propagation" of ALAP constraints:
        1. Find all ALAP tasks with fixed end dates (anchor tasks)
        2. For each anchor, traverse its dependencies backward
        3. Mark predecessor tasks as ALAP and set their end constraint
           to the dependent task's calculated start
        """
        # Build reverse dependency map: task -> list of tasks that depend on it
        reverse_deps: dict[Any, list[Any]] = {}  # predecessor_id -> [successor tasks]
        for task in self.tasks:
            if not task.leaf():
                continue
            deps = task.get("depends", scIdx) or []
            for dep in deps:
                # Extract the predecessor task from dependency
                if isinstance(dep, dict):
                    pred = dep.get("task")
                elif hasattr(dep, "task"):
                    pred = dep.task
                else:
                    pred = dep

                if pred:
                    pred_id = pred.fullId if hasattr(pred, "fullId") else id(pred)
                    if pred_id not in reverse_deps:
                        reverse_deps[pred_id] = []
                    reverse_deps[pred_id].append(task)

        # Find ALAP anchor tasks (ALAP with fixed end)
        alap_anchors: list[Any] = []
        for task in self.tasks:
            if not task.leaf():
                continue
            forward = task.get("forward", scIdx)
            end = task.get("end", scIdx)
            if forward is False and end:  # ALAP with fixed end
                alap_anchors.append(task)

        # Propagate ALAP backward from each anchor
        # Use BFS to traverse dependency chains
        processed: set[Any] = set()
        for anchor in alap_anchors:
            anchor_id = anchor.fullId if hasattr(anchor, "fullId") else id(anchor)
            processed.add(anchor_id)

            # Get dependencies of the anchor (tasks that must finish before anchor starts)
            deps = anchor.get("depends", scIdx) or []
            for dep in deps:
                if isinstance(dep, dict):
                    pred = dep.get("task")
                elif hasattr(dep, "task"):
                    pred = dep.task
                else:
                    pred = dep

                if not pred:
                    continue

                pred_id = pred.fullId if hasattr(pred, "fullId") else id(pred)
                if pred_id in processed:
                    continue

                # Mark predecessor as ALAP
                # It should finish as late as possible while still allowing the anchor to start
                self._markTaskALAP(pred, scIdx, processed, reverse_deps)

    def _markTaskALAP(self, task: Any, scIdx: int, processed: set[Any], reverse_deps: dict[Any, list[Any]]) -> None:
        """
        Mark a task as ALAP and propagate to its predecessors.

        Args:
            task: The task to mark as ALAP
            scIdx: Scenario index
            processed: Set of already processed task IDs
            reverse_deps: Map of task ID -> list of successor tasks
        """
        task_id = task.fullId if hasattr(task, "fullId") else id(task)
        if task_id in processed:
            return
        processed.add(task_id)

        # Only process leaf tasks
        if not task.leaf():
            return

        # Check if task is already explicitly ASAP with a fixed start
        # In that case, don't override
        forward = task.get("forward", scIdx)
        start = task.get("start", scIdx)
        if forward is True and start:
            # Explicitly ASAP with start date - don't change
            return

        # Mark as ALAP (forward=False)
        task[("forward", scIdx)] = False

        # Now propagate to predecessors of this task
        deps = task.get("depends", scIdx) or []
        for dep in deps:
            if isinstance(dep, dict):
                pred = dep.get("task")
            elif hasattr(dep, "task"):
                pred = dep.task
            else:
                pred = dep

            if pred:
                self._markTaskALAP(pred, scIdx, processed, reverse_deps)

    def initScoreboards(self) -> None:
        if not self.attributes["start"] or not self.attributes["end"]:
            return

        self.scoreboard = Scoreboard(
            self.attributes["start"], self.attributes["end"], self.attributes["scheduleGranularity"], 2
        )
        self.scoreboardNoLeaves = Scoreboard(
            self.attributes["start"], self.attributes["end"], self.attributes["scheduleGranularity"], 2
        )

        # Initialize working time slots - mark working hours as None
        # Default working hours: Mon-Fri, 9am-5pm
        size: int = self.scoreboardSize()
        self.attributes["scheduleGranularity"]

        for i in range(size):
            date = self.idxToDate(i)
            if self._isDefaultWorkingTime(date):
                self.scoreboard[i] = None
                self.scoreboardNoLeaves[i] = None

    def _isDefaultWorkingTime(self, date: Optional[Any]) -> bool:
        """Check if a date/time falls within default working hours."""
        if date is None:
            return False
        # Check global vacations
        vacations = self.attributes.get("vacations", [])
        for vac in vacations:
            if hasattr(vac, "interval") and vac.interval:
                if vac.interval.start <= date < vac.interval.end:
                    return False
            elif hasattr(vac, "contains") and vac.contains(date):
                return False
        weekday: int = date.weekday()
        if weekday >= 5:  # Saturday or Sunday
            return False
        hour: int = date.hour
        result: bool = 9 <= hour < 17  # Within 9am-5pm
        return result

    def isWorkingTime(self, sbIdx: int) -> bool:
        """Check if a scoreboard slot is working time."""
        if self.scoreboard is None:
            return self._isDefaultWorkingTime(self.idxToDate(sbIdx))
        result: Any = self.scoreboard[sbIdx]
        return result is None

    def scoreboardSize(self) -> int:
        if self.scoreboard:
            return self.scoreboard.size
        if self.attributes["start"] and self.attributes["end"]:
            try:
                diff_seconds: float = (self.attributes["end"] - self.attributes["start"]).total_seconds()
            except AttributeError:
                diff_seconds = float(self.attributes["end"] - self.attributes["start"])
            return int(diff_seconds / self.attributes["scheduleGranularity"]) + 1
        return 0

    def dateToIdx(self, date: Any, forceIntoProject: bool = True) -> int:
        if not self.attributes["start"]:
            return 0

        if _USE_CYTHON:
            return int(project_date_to_idx(date, self.attributes["start"], self.attributes["scheduleGranularity"]))

        try:
            diff_seconds: float = (date - self.attributes["start"]).total_seconds()
        except AttributeError:
            diff_seconds = float(date - self.attributes["start"])

        idx: int = int(diff_seconds / self.attributes["scheduleGranularity"])
        return idx

    def idxToDate(self, idx: int) -> Optional[Any]:
        if not self.attributes["start"]:
            return None

        if _USE_CYTHON:
            return project_idx_to_date(idx, self.attributes["start"], self.attributes["scheduleGranularity"])

        # Assuming idx is integer steps of scheduleGranularity from start
        seconds: int = idx * self.attributes["scheduleGranularity"]
        return self.attributes["start"] + timedelta(seconds=seconds)

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
