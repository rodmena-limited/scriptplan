import logging
from rodmena_resource_management.utils.message_handler import MessageHandler
from rodmena_resource_management.utils.time import TjTime, TimeInterval
from rodmena_resource_management.utils.data_cache import DataCache, FileList
from rodmena_resource_management.core.property import (
    PropertySet, PropertyList, AttributeDefinition, AttributeBase,
    AlertLevelDefinitions, Journal, LeaveList, RealFormat, KeywordArray,
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
            'journal': Journal(),
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
        
        self.accounts = PropertySet(self, False)
        
        self.shifts = PropertySet(self, False)
        
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

    def _define_resource_attributes(self):
        # Add attributes required by ResourceScenario
        attrs = [
            ['alloctdeffort', 'Allocated Effort', IntegerAttribute, True, False, True, 0],
            ['booking', 'Booking', ResourceListAttribute, True, False, True, []],
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
             ['formats', 'Formats', FormatListAttribute, True, False, False, []],
             ['columns', 'Columns', ColumnListAttribute, True, False, False, []],
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
            self.error('no_tasks', "No tasks defined")
            
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
        tasks = list(self.tasks)
        
        # Only care about leaf tasks that are not milestones and aren't
        # scheduled already (marked with the 'scheduled' attribute).
        tasks = [t for t in tasks if t.leaf() and not t.get('milestone', scIdx) and not t.get('scheduled', scIdx)]

        
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
