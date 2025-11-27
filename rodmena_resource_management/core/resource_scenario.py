from rodmena_resource_management.core.scenario_data import ScenarioData
from rodmena_resource_management.scheduler.scoreboard import Scoreboard
from rodmena_resource_management.utils.data_cache import DataCache
from rodmena_resource_management.core.leave import Leave
from rodmena_resource_management.core.booking import Booking
from rodmena_resource_management.utils.time import TimeInterval
from rodmena_resource_management.core.task import Task
# from rodmena_resource_management.utils.rich_text import RichText # Future

class ResourceScenario(ScenarioData):
    def __init__(self, resource, scenarioIdx, attributes):
        super().__init__(resource, scenarioIdx, attributes)
        
        self.scoreboard = None
        self.firstBookedSlot = None
        self.firstBookedSlots = {}
        self.lastBookedSlot = None
        self.lastBookedSlots = {}
        
        self.minslot = None
        self.maxslot = None
        
        self.dCache = DataCache.instance()
        
        required_attrs = [
            'alloctdeffort', 'chargeset', 'criticalness', 'directreports', 'duties', 'efficiency',
            'effort', 'limits', 'managers', 'rate', 'reports', 'shifts',
            'leaves', 'leaveallowances', 'workinghours'
        ]
        for attr in required_attrs:
             try:
                _ = self.property[(attr, self.scenarioIdx)]
             except ValueError:
                pass

    # ... (Previous methods: prepareScheduling, calcCriticalness, setDirectReports, setReports, finishScheduling)
    def prepareScheduling(self):
        self.property[( 'effort', self.scenarioIdx )] = 0
        if self.property.leaf():
            self.initScoreboard()

    def calcCriticalness(self):
        if self.scoreboard is None:
            self.property[( 'criticalness', self.scenarioIdx )] = 0.0
        else:
            freeSlots = 0
            for slot in self.scoreboard:
                if slot is None:
                    freeSlots += 1
            
            allocated_effort = self.property[( 'alloctdeffort', self.scenarioIdx )]
            if freeSlots == 0:
                 self.property[( 'criticalness', self.scenarioIdx )] = 1.0
            else:
                 self.property[( 'criticalness', self.scenarioIdx )] = allocated_effort / freeSlots

    def setDirectReports(self):
        managers = self.property[( 'managers', self.scenarioIdx )]
        new_managers = []
        for managerId in managers:
            manager = self.project.resource(managerId)
            if manager is None:
                self.error('resource_id_expected', f"{managerId} is not a defined resource.")
                continue
            if not manager.leaf():
                self.error('manager_is_group', f"Resource {self.property.fullId} has group {manager.fullId} assigned as manager.")
            if manager == self.property:
                self.error('manager_is_self', f"Resource {self.property.fullId} cannot manage itself.")
            if self.property.leaf():
                 direct_reports = manager.get('directreports', self.scenarioIdx)
                 if self.property not in direct_reports:
                     direct_reports.append(self.property)
            new_managers.append(manager)
        managers.clear()
        seen = set()
        for m in new_managers:
            if m not in seen:
                managers.append(m)
                seen.add(m)

    def setReports(self):
        direct_reports = self.property[( 'directreports', self.scenarioIdx )]
        if not direct_reports:
            return
        managers = self.property[( 'managers', self.scenarioIdx )]
        for r in managers:
            r.setReports_i(self.scenarioIdx, [self.property])

    def finishScheduling(self):
        for resource in self.property.children:
            resource.finishScheduling(self.scenarioIdx)
        duties = self.property[( 'duties', self.scenarioIdx )]
        current_duties = list(duties)
        for task in current_duties:
            for pTask in task.ancestors(True):
                if pTask not in duties:
                    duties.append(pTask)
        for pResource in self.property.parents:
            p_duties = pResource[( 'duties', self.scenarioIdx )]
            for task in duties:
                if task not in p_duties:
                    p_duties.append(task)

    def available(self, sbIdx):
        if self.scoreboard is None: return False
        if self.scoreboard[sbIdx] is not None: return False
        limits = self.property[( 'limits', self.scenarioIdx )]
        if limits and not limits.ok(sbIdx): return False
        return True

    def booked(self, sbIdx):
        if self.scoreboard is None: return False
        return isinstance(self.scoreboard[sbIdx], Task)

    def book(self, sbIdx, task, force=False):
        if not force and not self.available(sbIdx): return False
        duties = self.property[( 'duties', self.scenarioIdx )]
        if task not in duties: duties.append(task)
        if self.scoreboard is None: self.initScoreboard()
        self.scoreboard[sbIdx] = task
        efficiency = self.property[( 'efficiency', self.scenarioIdx )] or 1.0
        current_effort = self.property[( 'effort', self.scenarioIdx )] or 0.0
        self.property[( 'effort', self.scenarioIdx )] = current_effort + efficiency
        limits = self.property[( 'limits', self.scenarioIdx )]
        if limits: limits.inc(sbIdx)
        if self.firstBookedSlot is None or self.firstBookedSlot > sbIdx:
            self.firstBookedSlot = sbIdx
            self.firstBookedSlots[task] = sbIdx
        elif task not in self.firstBookedSlots or self.firstBookedSlots[task] > sbIdx:
            self.firstBookedSlots[task] = sbIdx
        if self.lastBookedSlot is None or self.lastBookedSlot < sbIdx:
            self.lastBookedSlot = sbIdx
            self.lastBookedSlots[task] = sbIdx
        elif task not in self.lastBookedSlots or self.lastBookedSlots[task] < sbIdx:
             self.lastBookedSlots[task] = sbIdx
        return True

    def initScoreboard(self):
        start = self.project['start']
        end = self.project['end']
        granularity = self.project['scheduleGranularity']
        self.scoreboard = Scoreboard(start, end, granularity, 2)
        size = self.project.scoreboardSize() 
        for i in range(size):
            if self.onShift(i): self.scoreboard[i] = None
        leaves = self.project['leaves']
        for leave in leaves:
            startIdx = self.project.dateToIdx(leave.interval.start)
            endIdx = self.project.dateToIdx(leave.interval.end)
            for i in range(startIdx, endIdx):
                 sb = self.scoreboard[i]
                 val = 0 if sb is None else 2
                 self.scoreboard[i] = val | (leave.type_idx << 2)
        res_leaves = self.property[( 'leaves', self.scenarioIdx )]
        if res_leaves:
            for leave in res_leaves:
                startIdx = self.project.dateToIdx(leave.interval.start)
                endIdx = self.project.dateToIdx(leave.interval.end)
                for i in range(startIdx, endIdx):
                    sb = self.scoreboard[i]
                    if sb is not None:
                         leaveIdx = (sb & 0x3C) >> 2
                         if leave.type_idx > leaveIdx:
                             self.scoreboard[i] = (sb & 0x2) | (leave.type_idx << 2)
                    else:
                         self.scoreboard[i] = leave.type_idx << 2

    def onShift(self, sbIdx):
        shifts = self.property[( 'shifts', self.scenarioIdx )]
        if shifts and hasattr(shifts, 'assigned') and shifts.assigned(sbIdx):
             return shifts.onShift(sbIdx)
        else:
             workinghours = self.property[( 'workinghours', self.scenarioIdx )]
             if workinghours: return workinghours.onShift(sbIdx)
        return False

    def setReports_i(self, reports):
         if self.property in reports:
             self.error('manager_loop', f"Management loop detected. {self.property.fullId} has self in list of reports")
         current_reports = self.property[( 'reports', self.scenarioIdx )]
         for r in reports:
             if r not in current_reports:
                 current_reports.append(r)
         managers = self.property[( 'managers', self.scenarioIdx )]
         for r in managers:
             r.setReports_i(self.scenarioIdx, current_reports)

    # Implementation of treeSum and getEffectiveWork
    
    def treeSum(self, startIdx, endIdx, *args, block):
        # In Python we pass the block as a callable 'block' argument
        cacheTag = "treeSum" # Simplified tag
        return self.treeSumR(cacheTag, startIdx, endIdx, *args, block=block)

    def treeSumR(self, cacheTag, startIdx, endIdx, *args, block):
        # Check cache (mocked)
        # return self.dCache.cached(self, cacheTag, startIdx, endIdx, *args) or ...
        
        if self.property.container():
            sum_val = 0.0
            for resource in self.property.kids():
                # Access scenario object for child
                res_scenario = resource.data[self.scenarioIdx]
                sum_val += res_scenario.treeSumR(cacheTag, startIdx, endIdx, *args, block=block)
            return sum_val
        else:
            return block(self) # Block executes in context of self (ResourceScenario)

    def getEffectiveWork(self, startIdx, endIdx, task=None):
        if task:
             # Ensure task is Task object
             pass
        
        if startIdx >= endIdx or (task and task not in self.property[( 'duties', self.scenarioIdx )]):
            return 0.0
        
        def calculate(res_scen):
            if res_scen.scoreboard is None: return 0.0
            allocated = res_scen.getAllocatedSlots(startIdx, endIdx, task)
            return self.project.convertToDailyLoad(allocated * self.project['scheduleGranularity']) * (res_scen.property[( 'efficiency', self.scenarioIdx )] or 1.0)

        return self.treeSum(startIdx, endIdx, task, block=calculate)

    def getAllocatedSlots(self, startIdx, endIdx, task=None):
        if not self.scoreboard: return 0
        # fitIndicies logic ... simplified
        if startIdx >= endIdx: return 0
        
        bookedSlots = 0
        taskList = task.all() if task else []
        
        # Limit loop
        actualEnd = min(endIdx, self.scoreboard.size)
        
        for i in range(startIdx, actualEnd):
            slot = self.scoreboard[i]
            if isinstance(slot, Task):
                if task is None or slot in taskList:
                    bookedSlots += 1
        return bookedSlots