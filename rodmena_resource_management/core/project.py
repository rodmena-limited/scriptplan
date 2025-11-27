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
        self._add_standard_attributes(self.accounts)
        
        self.shifts = PropertySet(self, False)
        self._add_standard_attributes(self.shifts)
        
        self.resources = PropertySet(self, False)
        self._add_standard_attributes(self.resources)
        self._define_resource_attributes()
        
        self.tasks = PropertySet(self, False)
        self._add_standard_attributes(self.tasks)
        self._define_task_attributes()
        
        self.reports = PropertySet(self, False)
        self._add_standard_attributes(self.reports)
        self._define_report_attributes()
        
        self.scenarios = PropertySet(self, False)
        self._add_standard_attributes(self.scenarios)
        
        Scenario(self, 'plan', 'Plan Scenario', None)
        
        self.inputFiles = FileList()
        self.timeSheets = TimeSheets()
        
        self.scoreboard = None
        self.scoreboardNoLeaves = None
        
        self.reportContexts = []
        self.outputDir = './'
        self.warnTsDeltas = False

    def _add_standard_attributes(self, property_set):
        property_set.addAttributeType(AttributeDefinition('id', 'ID', StringAttribute, False, False, False, None))
        property_set.addAttributeType(AttributeDefinition('name', 'Name', StringAttribute, False, False, False, None))
        property_set.addAttributeType(AttributeDefinition('seqno', 'No', IntegerAttribute, False, False, False, None))

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
             for sc in self.scenarios._properties.values():
                 if sc.sequenceNo - 1 == arg:
                     return sc
        else:
            return self.scenarios[arg]
        return None
    
    def resource(self, id):
        return self.resources[id]

    def __getitem__(self, name):
        if name not in self.attributes:
            raise ValueError(f"Unknown project attribute {name}")
        return self.attributes[name]

    def __setitem__(self, name, value):
        if name not in self.attributes:
            raise ValueError(f"Unknown project attribute {name}")
        self.attributes[name] = value
        
        if name in ['start', 'end', 'scheduleGranularity', 'timezone', 'timingresolution']:
            if self.attributes.get('start') and self.attributes.get('end'):
                 self.attributes['workinghours'] = WorkingHours(
                     self.attributes['scheduleGranularity'],
                     self.attributes['start'],
                     self.attributes['end'],
                     self.attributes['timezone']
                 )

    @staticmethod
    def maxScheduleGranularity():
        return 60 * 60

    def schedule(self):
        self.initScoreboards()
        
        for p in [self.accounts, self.shifts, self.resources, self.tasks]:
            p.index()
            
        if self.tasks.empty():
            self.error('no_tasks', "No tasks defined")
        pass
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
        return None
