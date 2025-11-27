import logging
from rodmena_resource_management.utils.message_handler import MessageHandler
from rodmena_resource_management.utils.time import TjTime, TimeInterval
from rodmena_resource_management.utils.data_cache import DataCache, FileList
from rodmena_resource_management.core.property import (
    PropertySet, PropertyList, AttributeDefinition, AttributeBase,
    AlertLevelDefinitions, Journal, LeaveList, RealFormat, KeywordArray,
    StringAttribute, IntegerAttribute, DateAttribute, BooleanAttribute,
    ResourceListAttribute, ShiftAssignmentsAttribute, TaskDepListAttribute,
    LogicalExpressionListAttribute, PropertyAttribute, RichTextAttribute,
    ColumnListAttribute, AccountAttribute, DefinitionListAttribute,
    FlagListAttribute, FormatListAttribute, LogicalExpressionAttribute,
    SymbolListAttribute, SymbolAttribute, NodeListAttribute, ScenarioListAttribute,
    SortListAttribute, JournalSortListAttribute, RealFormatAttribute
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
        
        self.scenarios = PropertySet(self, False)
        Scenario(self, 'plan', 'Plan Scenario', None)
        
        self.inputFiles = FileList()
        self.timeSheets = TimeSheets()
        
        self.scoreboard = None
        self.scoreboardNoLeaves = None
        
        self.reportContexts = []
        self.outputDir = './'
        self.warnTsDeltas = False

    def _define_resource_attributes(self):
        # Partial list based on Project.rb structure/types commonly found
        # Ideally would parse the ruby file to get exact list
        attrs = [
            ['booking', 'Booking', ResourceListAttribute, True, False, True, []],
            ['chargeset', 'Charge Set', StringAttribute, True, False, True, []], # Placeholder type
             # ... Add more as discovered
        ]
        for a in attrs:
            self.resources.addAttributeType(AttributeDefinition(*a))

    def _define_task_attributes(self):
        attrs = [
            ['booking', 'Booking', ResourceListAttribute, True, False, True, []],
            ['duration', 'Duration', IntegerAttribute, True, False, True, 0],
            ['start', 'Start', DateAttribute, True, False, True, None],
            ['end', 'End', DateAttribute, True, False, True, None],
            ['priority', 'Priority', IntegerAttribute, True, False, True, 500],
            ['depends', 'Dependencies', TaskDepListAttribute, True, False, True, []],
             # ... Add more as discovered
        ]
        for a in attrs:
            self.tasks.addAttributeType(AttributeDefinition(*a))

    def _define_report_attributes(self):
        attrs = [
             ['formats', 'Formats', FormatListAttribute, True, False, False, []],
             ['columns', 'Columns', ColumnListAttribute, True, False, False, []],
             # ... Add more as discovered
        ]
        for a in attrs:
            self.reports.addAttributeType(AttributeDefinition(*a))

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
            
        # In python we might iterate differently if PropertySet isn't iterable directly
        # Assuming PropertySet holds properties in self.scenarios.attributes or similar?
        # No, PropertySet holds PropertyTreeNodes.
        # We need a way to iterate scenarios.
        # For now stub loop
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

    def dateToIdx(self, date, forceIntoProject=True):
         if not self.attributes['start']:
             return 0
         # Simplified logic
         return 0

    def idxToDate(self, idx):
        return None