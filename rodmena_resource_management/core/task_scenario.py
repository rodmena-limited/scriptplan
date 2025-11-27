from rodmena_resource_management.core.scenario_data import ScenarioData
from rodmena_resource_management.core.property import AttributeBase

class TaskScenario(ScenarioData):
    def __init__(self, task, scenarioIdx, attributes):
        super().__init__(task, scenarioIdx, attributes)
        self.isRunAway = False
        self.hasDurationSpec = False
        self.scheduled = False
        self.currentSlotIdx = None
        
        # Ensure required attributes exist
        required_attrs = [
             'allocate', 'assignedresources', 'booking', 'charge', 'chargeset', 'complete',
             'competitors', 'criticalness', 'depends', 'duration',
             'effort', 'effortdone', 'effortleft', 'end', 'forward', 'gauge', 'length',
             'maxend', 'maxstart', 'minend', 'minstart', 'milestone', 'pathcriticalness',
             'precedes', 'priority', 'projectionmode', 'responsible',
             'scheduled', 'shifts', 'start', 'status'
        ]
        
        for attr in required_attrs:
            try:
                _ = self.property[(attr, self.scenarioIdx)]
            except ValueError:
                pass

        if not self.property.parent:
            mode = AttributeBase.mode()
            AttributeBase.setMode(1)
            
            proj_projection = self.project.scenario(self.scenarioIdx).get('projection') if hasattr(self.project, 'scenario') else None
            if proj_projection:
                 self.property[( 'projectionmode', self.scenarioIdx )] = proj_projection
            
            AttributeBase.setMode(mode)
    
    def readyForScheduling(self):
        # Basic check: Start date known (if ASAP) or dependencies met?
        # Ruby: @data[scenarioIdx].readyForScheduling?
        # Logic: Dependencies scheduled?
        
        depends = self.property.get('depends', self.scenarioIdx)
        for dep in depends:
            # dep is a TaskDependency? Or Task?
            # depends attribute is TaskDepListAttribute -> returns list of TaskDependency objects?
            # For now, assuming list of tasks for simplicity if not fully implemented
            if hasattr(dep, 'task'):
                t = dep.task
            else:
                t = dep # Assuming it resolved to Task
            
            if not t.get('scheduled', self.scenarioIdx):
                return False
        
        return True

    def schedule(self):
        if self.scheduled:
            return True
        
        # Determine start slot
        forward = self.property.get('forward', self.scenarioIdx)
        
        if self.currentSlotIdx is None:
            if forward:
                start_date = self.property.get('start', self.scenarioIdx)
                if start_date:
                    self.currentSlotIdx = self.project.dateToIdx(start_date)
                else:
                    # ASAP mode, start at project start or dependencies?
                    # For now default to project start if no start date
                    self.currentSlotIdx = self.project.dateToIdx(self.project['start'])
            else:
                end_date = self.property.get('end', self.scenarioIdx)
                if end_date:
                    self.currentSlotIdx = self.project.dateToIdx(end_date) - 1
                else:
                    # ALAP mode, end at project end
                    self.currentSlotIdx = self.project.dateToIdx(self.project['end']) - 1
        
        delta = 1 if forward else -1
        lowerLimit = self.project.dateToIdx(self.project['start'])
        upperLimit = self.project.dateToIdx(self.project['end'])
        
        while self.scheduleSlot():
            self.currentSlotIdx += delta
            if self.currentSlotIdx < lowerLimit or self.currentSlotIdx > upperLimit:
                self.isRunAway = True
                return False
        
        self.scheduled = True
        self.property[('scheduled', self.scenarioIdx)] = True
        return True

    def scheduleSlot(self):
        # Determine duration type
        # :effortTask, :lengthTask, :durationTask, :startEndTask
        
        # Simplified logic:
        # If effort > 0 -> effortTask
        # If length > 0 -> lengthTask
        # If duration > 0 -> durationTask
        # Else -> startEndTask
        
        effort = self.property.get('effort', self.scenarioIdx) or 0
        length = self.property.get('length', self.scenarioIdx) or 0
        duration = self.property.get('duration', self.scenarioIdx) or 0
        
        # We need state tracking for done effort/duration
        if not hasattr(self, 'doneEffort'): self.doneEffort = 0
        if not hasattr(self, 'doneDuration'): self.doneDuration = 0
        if not hasattr(self, 'doneLength'): self.doneLength = 0
        
        forward = self.property.get('forward', self.scenarioIdx)

        if effort > 0:
            self.bookResources()
            if self.doneEffort >= effort:
                # Finished
                date = self.project.idxToDate(self.currentSlotIdx + (1 if forward else 0))
                self.propagateDate(date, forward) # Set end if forward
                return False
        elif duration > 0:
            self.bookResources() # Even if just duration, might use resources?
            self.doneDuration += 1
            if self.doneDuration >= duration:
                date = self.project.idxToDate(self.currentSlotIdx + (1 if forward else 0))
                self.propagateDate(date, forward)
                return False
        else:
            # startEndTask
            self.bookResources()
            # Check if reached end/start
            target_date = self.property.get('end', self.scenarioIdx) if forward else self.property.get('start', self.scenarioIdx)
            if target_date:
                target_idx = self.project.dateToIdx(target_date)
                if (forward and self.currentSlotIdx >= target_idx) or (not forward and self.currentSlotIdx <= target_idx):
                    return False
            
        return True

    def bookResources(self):
        # Simplified booking
        # Check mandatory allocations
        allocations = self.property.get('allocate', self.scenarioIdx)
        if not allocations:
            return
            
        # For now, just consume effort if resource available
        # Assuming 'efficiency' of 1.0 for simplicity
        
        # Real logic needs to iterate allocations, check availability on resource scenarios
        
        # self.doneEffort += 1 * efficiency
        pass

    def propagateDate(self, date, atEnd):
        attr = 'end' if atEnd else 'start'
        self.property[(attr, self.scenarioIdx)] = date
        # Propagate to dependencies?