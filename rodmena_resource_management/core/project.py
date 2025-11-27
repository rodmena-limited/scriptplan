import logging
from rodmena_resource_management.utils.message_handler import MessageHandler
from rodmena_resource_management.utils.time import TjTime, TimeInterval
from rodmena_resource_management.utils.data_cache import DataCache, FileList
from rodmena_resource_management.core.property import (
    PropertySet, PropertyList, AttributeDefinition, AttributeBase,
    AlertLevelDefinitions, LeaveList, RealFormat, KeywordArray,
    StringAttribute, IntegerAttribute, DateAttribute, BooleanAttribute,
    ListAttribute, FloatAttribute,
    ResourceListAttribute, ShiftAssignmentsAttribute, TaskDepListAttribute,
    LogicalExpressionListAttribute, PropertyAttribute, RichTextAttribute,
    ColumnListAttribute, AccountAttribute, DefinitionListAttribute,
    FlagListAttribute, FormatListAttribute, LogicalExpressionAttribute,
    SymbolListAttribute, SymbolAttribute, NodeListAttribute, ScenarioListAttribute,
    SortListAttribute, JournalSortListAttribute, RealFormatAttribute,
    LeaveListAttribute
)
from rodmena_resource_management.core.journal import Journal
from rodmena_resource_management.core.scenario import Scenario
from rodmena_resource_management.core.timesheet import TimeSheets
from rodmena_resource_management.core.working_hours import WorkingHours
from rodmena_resource_management.scheduler.scoreboard import Scoreboard

class Project(MessageHandler):
    """
    This class implements objects that hold all project properties. Project
    generally consist of resources, tasks and a number of other optional
    properties.
    """
    
    def __init__(self, id, name, version):
        self.id = id
        self.name = name
        self.version = version
        
        if hasattr(AttributeBase, 'setMode'):
             AttributeBase.setMode(0)
        
        self.attributes = {
            'alertLevels': AlertLevelDefinitions(),
            'auxdir': '',
            'copyright': None,
            'costaccount': None,
            'currency': "EUR",
            'currencyFormat': RealFormat(['-', '', '', ',', 2]),
            'dailyworkinghours': 8.0,
            'end': None,
            'markdate': None,
            'flags': [],
            'journal': Journal(self),
            'limits': None,
            'leaves': LeaveList(),
            'loadUnit': 'days',
            'name': name,
            'navigators': {},
            'now': TjTime().align(3600),
            'numberFormat': RealFormat(['-', '', '', '.', 1]),
            'priority': 500,
            'projectid': id or "prj",
            'projectids': [id] if id else ["prj"],
            'rate': 0.0,
            'revenueaccount': None,
            'scheduleGranularity': self.maxScheduleGranularity(),
            'shortTimeFormat': "%H:%M",
            'start': None,
            'timeFormat': "%Y-%m-%d",
            'timeOffId': None,
            'timeOffName': None,
            'timingresolution': 60 * 60,
            'timezone': TjTime.timeZone(),
            'trackingscenario': None,
            'version': version,
            'weekStartsMonday': False,
            'workinghours': None,
            'yearlyworkingdays': 260.714,
            'yresolution': 1
        }
        
        self.accounts = PropertySet(self, True)
        self._define_account_attributes()

        self.shifts = PropertySet(self, True)
        self._define_shift_attributes()

        self.resources = PropertySet(self, False)
        self._define_resource_attributes()
        
        self.tasks = PropertySet(self, False)
        self._define_task_attributes()
        
        self.reports = PropertySet(self, False)
        self._define_report_attributes()
        
        self.scenarios = PropertySet(self, True)
        self._define_scenario_attributes()
        
        # Scenario needs to be added AFTER attributes are defined
        Scenario(self, 'plan', 'Plan Scenario', None)
        
        self.inputFiles = FileList()
        self.timeSheets = TimeSheets()
        
        self.scoreboard = None
        self.scoreboardNoLeaves = None
        
        self.reportContexts = []
        self.outputDir = './'
        self.warnTsDeltas = False

    def _define_scenario_attributes(self):
        attrs = [
            ['active', 'Enabled', BooleanAttribute, True, False, False, True],
            ['ownbookings', 'Own Bookings', BooleanAttribute, False, False, False, True],
            ['projection', 'Projection Mode', BooleanAttribute, True, False, False, False],
        ]
        for a in attrs:
            self.scenarios.addAttributeType(AttributeDefinition(*a))

    def _define_account_attributes(self):
        attrs = [
            # ID           Name            Type                     Inh   InhPrj Scen  Default
            ['aggregate', 'Aggregate', SymbolAttribute, True, False, False, 'tasks'],
            ['bsi', 'BSI', StringAttribute, False, False, False, ''],
            ['credits', 'Credits', ListAttribute, False, False, True, []],
            ['index', 'Index', IntegerAttribute, False, False, False, -1],
            ['flags', 'Flags', FlagListAttribute, True, False, True, []],
            ['tree', 'Tree Index', StringAttribute, False, False, False, ''],
        ]
        for a in attrs:
            self.accounts.addAttributeType(AttributeDefinition(*a))

    def _define_shift_attributes(self):
        attrs = [
            # ID           Name            Type                     Inh   InhPrj Scen  Default
            ['bsi', 'BSI', StringAttribute, False, False, False, ''],
            ['index', 'Index', IntegerAttribute, False, False, False, -1],
            ['leaves', 'Leaves', LeaveListAttribute, True, True, True, []],
            ['replace', 'Replace', BooleanAttribute, True, False, True, False],
            ['timezone', 'Time Zone', StringAttribute, True, True, True, TjTime.timeZone()],
            ['tree', 'Tree Index', StringAttribute, False, False, False, ''],
            ['workinghours', 'Working Hours', ShiftAssignmentsAttribute, True, True, True, None],
        ]
        for a in attrs:
            self.shifts.addAttributeType(AttributeDefinition(*a))

    def _define_resource_attributes(self):
        # Add attributes required by ResourceScenario
        attrs = [
            ['alloctdeffort', 'Allocated Effort', IntegerAttribute, True, False, True, 0],
            ['booking', 'Booking', ResourceListAttribute, True, False, True, []],
            ['bsi', 'BSI', StringAttribute, False, False, False, ""],
            ['email', 'Email', StringAttribute, False, False, False, ""],
            ['index', 'Index', IntegerAttribute, False, False, False, -1],
            ['chargeset', 'Charge Set', StringAttribute, True, False, True, []],
            ['criticalness', 'Criticalness', FloatAttribute, False, False, True, 0.0],
            ['directreports', 'Direct Reports', ResourceListAttribute, True, False, True, []],
            ['duties', 'Duties', TaskDepListAttribute, True, False, True, []],
            ['efficiency', 'Efficiency', FloatAttribute, True, False, True, 1.0],
            ['effort', 'Effort', IntegerAttribute, True, False, True, 0],
            ['leaves', 'Leaves', LeaveListAttribute, True, False, True, []], # Changed to LeaveListAttribute
            ['leaveallowances', 'Leave Allowances', AttributeBase, True, False, True, None], # Placeholder
            ['limits', 'Limits', AttributeBase, True, False, True, None], # Placeholder
            ['managers', 'Managers', ResourceListAttribute, True, False, True, []],
            ['rate', 'Rate', FloatAttribute, True, False, True, 0.0],
            ['reports', 'Reports', ResourceListAttribute, True, False, True, []],
            ['shifts', 'Shifts', ShiftAssignmentsAttribute, True, False, True, None],
            ['workinghours', 'Working Hours', AttributeBase, True, False, True, None]
        ]
        for a in attrs:
            self.resources.addAttributeType(AttributeDefinition(*a))

    def _define_task_attributes(self):
        attrs = [
            ['allocate', 'Allocate', ListAttribute, True, False, True, []],
            ['assignedresources', 'Assigned Resources', ListAttribute, False, False, True, []],
            ['booking', 'Booking', ResourceListAttribute, True, False, True, []],
            ['bsi', 'BSI', StringAttribute, False, False, False, ""],
            ['charge', 'Charge', FloatAttribute, True, False, True, 0.0],
            ['chargeset', 'Charge Set', StringAttribute, True, False, True, []],
            ['complete', 'Complete', FloatAttribute, True, False, True, 0.0],
            ['competitors', 'Competitors', ListAttribute, True, False, True, []],
            ['criticalness', 'Criticalness', FloatAttribute, False, False, True, 0.0],
            ['depends', 'Dependencies', TaskDepListAttribute, True, False, True, []],
            ['duration', 'Duration', IntegerAttribute, True, False, True, 0],
            ['effort', 'Effort', IntegerAttribute, True, False, True, 0],
            ['effortdone', 'Effort Done', IntegerAttribute, True, False, True, 0],
            ['effortleft', 'Effort Left', IntegerAttribute, True, False, True, 0],
            ['end', 'End', DateAttribute, True, False, True, None],
            ['forward', 'Forward', BooleanAttribute, True, False, True, True],
            ['gauge', 'Gauge', StringAttribute, True, False, True, None],
            ['index', 'Index', IntegerAttribute, False, False, False, -1],
            ['length', 'Length', IntegerAttribute, True, False, True, 0],
            ['limits', 'Limits', PropertyAttribute, True, False, True, None],
            ['maxend', 'Max End', DateAttribute, True, False, True, None],
            ['maxstart', 'Max Start', DateAttribute, True, False, True, None],
            ['minend', 'Min End', DateAttribute, True, False, True, None],
            ['minstart', 'Min Start', DateAttribute, True, False, True, None],
            ['milestone', 'Milestone', BooleanAttribute, True, False, True, False],
            ['pathcriticalness', 'Path Criticalness', FloatAttribute, False, False, True, 0.0],
            ['precedes', 'Precedes', TaskDepListAttribute, True, False, True, []],
            ['priority', 'Priority', IntegerAttribute, True, False, True, 500],
            ['projectionmode', 'Projection Mode', BooleanAttribute, True, False, True, False],
            ['responsible', 'Responsible', ListAttribute, True, False, True, []],
            ['scheduled', 'Scheduled', BooleanAttribute, True, False, True, False],
            ['shifts', 'Shifts', ShiftAssignmentsAttribute, True, False, True, None],
            ['start', 'Start', DateAttribute, True, False, True, None],
            ['status', 'Status', StringAttribute, True, False, True, ""],
        ]
        for a in attrs:
            self.tasks.addAttributeType(AttributeDefinition(*a))

    def _define_report_attributes(self):
        attrs = [
            # ID               Name                Type                     Inh    InhPrj  Scen   Default
            ['accountRoot', 'Account Root', StringAttribute, True, False, False, None],
            ['auxDir', 'Aux Directory', StringAttribute, True, True, False, ''],
            ['balance', 'Balance', ListAttribute, True, False, False, []],
            ['caption', 'Caption', RichTextAttribute, True, False, False, None],
            ['center', 'Center', RichTextAttribute, True, False, False, None],
            ['columns', 'Columns', ColumnListAttribute, True, False, False, []],
            ['currencyFormat', 'Currency Format', StringAttribute, True, True, False, None],
            ['end', 'End Date', DateAttribute, True, True, False, None],
            ['epilog', 'Epilog', RichTextAttribute, True, False, False, None],
            ['flags', 'Flags', FlagListAttribute, True, False, False, []],
            ['footer', 'Footer', RichTextAttribute, True, False, False, None],
            ['formats', 'Formats', FormatListAttribute, True, False, False, []],
            ['header', 'Header', RichTextAttribute, True, False, False, None],
            ['headline', 'Headline', RichTextAttribute, True, False, False, None],
            ['hideAccount', 'Hide Account', LogicalExpressionAttribute, True, False, False, None],
            ['hideResource', 'Hide Resource', LogicalExpressionAttribute, True, False, False, None],
            ['hideTask', 'Hide Task', LogicalExpressionAttribute, True, False, False, None],
            ['interactive', 'Interactive', BooleanAttribute, True, False, False, False],
            ['journalAttributes', 'Journal Attributes', SymbolListAttribute, True, False, False, []],
            ['journalMode', 'Journal Mode', SymbolAttribute, True, False, False, None],
            ['left', 'Left', RichTextAttribute, True, False, False, None],
            ['loadUnit', 'Load Unit', SymbolAttribute, True, True, False, 'days'],
            ['numberFormat', 'Number Format', StringAttribute, True, True, False, None],
            ['openNodes', 'Open Nodes', ListAttribute, True, False, False, []],
            ['period', 'Period', StringAttribute, True, True, False, None],
            ['prolog', 'Prolog', RichTextAttribute, True, False, False, None],
            ['rawHtmlHead', 'Raw HTML Head', RichTextAttribute, True, False, False, None],
            ['resourceRoot', 'Resource Root', StringAttribute, True, False, False, None],
            ['right', 'Right', RichTextAttribute, True, False, False, None],
            ['rollupAccount', 'Rollup Account', LogicalExpressionAttribute, True, False, False, None],
            ['rollupResource', 'Rollup Resource', LogicalExpressionAttribute, True, False, False, None],
            ['rollupTask', 'Rollup Task', LogicalExpressionAttribute, True, False, False, None],
            ['scenarios', 'Scenarios', ScenarioListAttribute, True, True, False, []],
            ['selfContained', 'Self Contained', BooleanAttribute, True, False, False, False],
            ['showResources', 'Show Resources', BooleanAttribute, True, False, False, False],
            ['showTasks', 'Show Tasks', BooleanAttribute, True, False, False, False],
            ['sort', 'Sort', SortListAttribute, True, False, False, []],
            ['sortAccounts', 'Sort Accounts', SortListAttribute, True, False, False, []],
            ['sortResources', 'Sort Resources', SortListAttribute, True, False, False, []],
            ['sortTasks', 'Sort Tasks', SortListAttribute, True, False, False, []],
            ['start', 'Start Date', DateAttribute, True, True, False, None],
            ['taskRoot', 'Task Root', StringAttribute, True, False, False, None],
            ['timeFormat', 'Time Format', StringAttribute, True, True, False, '%Y-%m-%d'],
            ['timeZone', 'Time Zone', StringAttribute, True, True, False, None],
            ['title', 'Title', StringAttribute, True, False, False, None],
            ['width', 'Width', IntegerAttribute, True, False, False, None],
        ]
        for a in attrs:
            self.reports.addAttributeType(AttributeDefinition(*a))
    
    def scenarioCount(self):
        return self.scenarios.items()

    def scenario(self, arg):
        if isinstance(arg, int):
             for sc in self.scenarios:
                 if sc.sequenceNo - 1 == arg:
                     return sc
        else:
            return self.scenarios[arg]
        return None

# ...

    @staticmethod
    def maxScheduleGranularity():
        return 60 * 60

    def schedule(self):
        self.initScoreboards()
        
        for p in [self.accounts, self.shifts, self.resources, self.tasks]:
            p.index()
            
        if self.tasks.empty():
            # No tasks to schedule - just return
            return True
            
        for sc in self.scenarios:
            # Skip disabled scenarios if 'active' is false (default true if not set)
            if not sc.get('active') and sc.get('active') is not None:
                continue

            scIdx = sc.sequenceNo - 1
            
            # Propagate inherited values
            AttributeBase.setMode(1)
            self.prepareScenario(scIdx)
            
            # Schedule
            AttributeBase.setMode(2)
            self.scheduleScenario(scIdx)
            
            # Finish
            self.finishScenario(scIdx)
             
        return True

    def prepareScenario(self, scIdx):
        # Simplified preparation
        # In Ruby: computes criticalness, propagates initial values, checks loops
        
        # We need to ensure tasks are ready
        for task in self.tasks:
            task.prepareScheduling(scIdx)
            
        for resource in self.resources:
            resource.prepareScheduling(scIdx)

    def finishScenario(self, scIdx):
        for task in self.tasks:
            if not task.parent:
                task.finishScheduling(scIdx)
        
        for resource in self.resources:
            if not resource.parent:
                resource.finishScheduling(scIdx)

    def scheduleScenario(self, scIdx):
        all_tasks = list(self.tasks)

        # First, handle milestones - they just need end=start (or start=end)
        # A milestone is either:
        # 1. Explicitly marked with milestone attribute, or
        # 2. Has start or end set, but no effort/duration/length (implicit milestone)
        for task in all_tasks:
            if not task.leaf():
                continue

            is_explicit_milestone = task.get('milestone', scIdx)
            effort = task.get('effort', scIdx) or 0
            duration = task.get('duration', scIdx) or 0
            length = task.get('length', scIdx) or 0
            start = task.get('start', scIdx)
            end = task.get('end', scIdx)

            # Implicit milestone: has start/end but no duration metrics
            is_implicit_milestone = (start or end) and effort == 0 and duration == 0 and length == 0

            if is_explicit_milestone or is_implicit_milestone:
                if start and not end:
                    task[('end', scIdx)] = start
                elif end and not start:
                    task[('start', scIdx)] = end
                task[('scheduled', scIdx)] = True

        # Only care about leaf tasks that aren't scheduled already
        tasks = [t for t in all_tasks if t.leaf() and not t.get('scheduled', scIdx)]

        # Sorting
        # Primary: priority (desc), Secondary: pathcriticalness (desc), Tertiary: seqno (asc)
        # Note: attributes might return None, need safe access for sorting
        def sort_key(t):
            prio = t.get('priority', scIdx) or 500
            crit = t.get('pathcriticalness', scIdx) or 0.0
            seq = t.get('seqno') or 0
            return (-prio, -crit, seq)

        tasks.sort(key=sort_key)

        failedTasks = []

        while tasks:
            taskToRemove = None
            for task in tasks:
                # Task not ready? Ignore it.
                if not task.readyForScheduling(scIdx):
                    continue

                if not task.schedule(scIdx):
                    failedTasks.append(task)

                taskToRemove = task
                break

            if taskToRemove:
                tasks.remove(taskToRemove)
                # After scheduling a leaf, check if any container tasks should be marked scheduled
                self._updateContainerTaskStatus(scIdx)
            elif tasks and not failedTasks:
                # If we have tasks but none are ready and no failures yet, it's a deadlock
                # (Unless readyForScheduling logic waits for something else?)
                self.warning('deadlock', 'Deadlock detected in scheduling')
                failedTasks.extend(tasks)
                break
            else:
                # If tasks is not empty but we didn't remove any, we break to avoid infinite loop
                # likely deadlock or all failed
                break

        if failedTasks:
            self.warning('unscheduled_tasks', f"{len(failedTasks)} tasks could not be scheduled")
            return False

        return True

    def _updateContainerTaskStatus(self, scIdx):
        """Mark container tasks as scheduled when all their children are scheduled.

        Also compute start/end dates for container tasks based on children.
        """
        for task in self.tasks:
            if task.leaf():
                continue  # Skip leaf tasks

            if task.get('scheduled', scIdx):
                continue  # Already scheduled

            # Check if all children are scheduled
            children = task.children
            if not children:
                continue

            all_scheduled = all(child.get('scheduled', scIdx) for child in children)
            if not all_scheduled:
                continue

            # All children scheduled - mark container as scheduled
            # Compute start/end from children
            min_start = None
            max_end = None
            for child in children:
                child_start = child.get('start', scIdx)
                child_end = child.get('end', scIdx)
                if child_start and (min_start is None or child_start < min_start):
                    min_start = child_start
                if child_end and (max_end is None or child_end > max_end):
                    max_end = child_end

            if min_start:
                task[('start', scIdx)] = min_start
            if max_end:
                task[('end', scIdx)] = max_end
            task[('scheduled', scIdx)] = True

    def initScoreboards(self):
        if not self.attributes['start'] or not self.attributes['end']:
            return

        self.scoreboard = Scoreboard(
            self.attributes['start'],
            self.attributes['end'],
            self.attributes['scheduleGranularity'],
            2
        )
        self.scoreboardNoLeaves = Scoreboard(
            self.attributes['start'],
            self.attributes['end'],
            self.attributes['scheduleGranularity'],
            2
        )

        # Initialize working time slots - mark working hours as None
        # Default working hours: Mon-Fri, 9am-5pm
        from datetime import timedelta
        size = self.scoreboardSize()
        granularity = self.attributes['scheduleGranularity']

        for i in range(size):
            date = self.idxToDate(i)
            if self._isDefaultWorkingTime(date):
                self.scoreboard[i] = None
                self.scoreboardNoLeaves[i] = None

    def _isDefaultWorkingTime(self, date):
        """Check if a date/time falls within default working hours."""
        if date is None:
            return False
        weekday = date.weekday()
        if weekday >= 5:  # Saturday or Sunday
            return False
        hour = date.hour
        if hour < 9 or hour >= 17:  # Outside 9am-5pm
            return False
        return True

    def isWorkingTime(self, sbIdx):
        """Check if a scoreboard slot is working time."""
        if self.scoreboard is None:
            return self._isDefaultWorkingTime(self.idxToDate(sbIdx))
        return self.scoreboard[sbIdx] is None
    
    def scoreboardSize(self):
        if self.scoreboard:
            return self.scoreboard.size
        if self.attributes['start'] and self.attributes['end']:
             try:
                diff = (self.attributes['end'] - self.attributes['start']).total_seconds()
             except AttributeError:
                diff = self.attributes['end'] - self.attributes['start']
             return int(diff / self.attributes['scheduleGranularity']) + 1
        return 0

    def dateToIdx(self, date, forceIntoProject=True):
         if not self.attributes['start']:
             return 0
         try:
            diff = (date - self.attributes['start']).total_seconds()
         except AttributeError:
            diff = date - self.attributes['start']
         
         idx = int(diff / self.attributes['scheduleGranularity'])
         return idx

    def idxToDate(self, idx):
        if not self.attributes['start']:
            return None

        from datetime import timedelta
        # Assuming idx is integer steps of scheduleGranularity from start
        seconds = idx * self.attributes['scheduleGranularity']
        return self.attributes['start'] + timedelta(seconds=seconds)

    def addReport(self, report):
        """
        Add a report to the project's report list.
        This is called automatically by Report.__init__.

        Args:
            report: The Report object to add
        """
        # Report is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addAccount(self, account):
        """
        Add an account to the project's account list.
        This is called automatically by Account.__init__.

        Args:
            account: The Account object to add
        """
        # Account is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addShift(self, shift):
        """
        Add a shift to the project's shift list.
        This is called automatically by Shift.__init__.

        Args:
            shift: The Shift object to add
        """
        # Shift is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addResource(self, resource):
        """
        Add a resource to the project's resource list.
        This is called automatically by Resource.__init__.

        Args:
            resource: The Resource object to add
        """
        # Resource is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def addTask(self, task):
        """
        Add a task to the project's task list.
        This is called automatically by Task.__init__.

        Args:
            task: The Task object to add
        """
        # Task is already added via PropertySet in PropertyTreeNode.__init__
        # This method exists for compatibility with TaskJuggler's API
        pass

    def __getitem__(self, key):
        """
        Get a project attribute.

        Args:
            key: Attribute name

        Returns:
            Attribute value or None
        """
        return self.attributes.get(key)

    def __setitem__(self, key, value):
        """
        Set a project attribute.

        Args:
            key: Attribute name
            value: Attribute value
        """
        self.attributes[key] = value
