from rodmena_resource_management.core.scenario_data import ScenarioData
from rodmena_resource_management.core.property import AttributeBase

# Default working hours: 9am-5pm (0-indexed: hours 9-16 are working)
DEFAULT_WORK_START_HOUR = 9
DEFAULT_WORK_END_HOUR = 17  # 5pm, so hours 9,10,11,12,13,14,15,16 are working (8 hours)


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
    
    def getAllDependencies(self):
        """
        Get all dependencies including inherited ones from parent containers.

        In TaskJuggler, child tasks inherit dependencies from their parent
        containers. For example, if a container 'software' depends on 'spec',
        all children of 'software' (database, gui, backend) also depend on 'spec'.
        """
        all_deps = []

        # Get own dependencies
        own_deps = self.property.get('depends', self.scenarioIdx) or []
        all_deps.extend(own_deps)

        # Get parent dependencies (recursively up the tree)
        parent = self.property.parent
        while parent:
            parent_deps = parent.get('depends', self.scenarioIdx) or []
            all_deps.extend(parent_deps)
            parent = parent.parent

        return all_deps

    def readyForScheduling(self):
        """
        Check if all dependencies (including inherited) are scheduled.
        """
        for dep in self.getAllDependencies():
            # dep is a TaskDependency? Or Task?
            if hasattr(dep, 'task'):
                t = dep.task
            else:
                t = dep  # Assuming it resolved to Task

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
                    # ASAP mode, start at project start or after dependencies
                    # Check ALL dependencies (including inherited) to find the earliest start
                    earliest_start = self.project['start']
                    for dep in self.getAllDependencies():
                        if hasattr(dep, 'task'):
                            t = dep.task
                        else:
                            t = dep
                        dep_end = t.get('end', self.scenarioIdx)
                        if dep_end and dep_end > earliest_start:
                            earliest_start = dep_end

                    self.currentSlotIdx = self.project.dateToIdx(earliest_start)
                    # Set the start date now
                    self.property[('start', self.scenarioIdx)] = earliest_start
            else:
                end_date = self.property.get('end', self.scenarioIdx)
                if end_date:
                    self.currentSlotIdx = self.project.dateToIdx(end_date) - 1
                else:
                    # ALAP mode, end at project end
                    self.currentSlotIdx = self.project.dateToIdx(self.project['end']) - 1

        # Record starting position for forward scheduling
        start_slot_idx = self.currentSlotIdx

        delta = 1 if forward else -1
        lowerLimit = self.project.dateToIdx(self.project['start'])
        upperLimit = self.project.dateToIdx(self.project['end'])

        while self.scheduleSlot():
            self.currentSlotIdx += delta
            if self.currentSlotIdx < lowerLimit or self.currentSlotIdx > upperLimit:
                self.isRunAway = True
                return False

        # Set start/end dates based on scheduling direction
        if forward:
            # For forward scheduling: start is at the beginning, end is at current position
            if not self.property.get('start', self.scenarioIdx):
                self.property[('start', self.scenarioIdx)] = self.project.idxToDate(start_slot_idx)
        else:
            # For backward scheduling: end is at the beginning, start is at current position
            if not self.property.get('end', self.scenarioIdx):
                self.property[('end', self.scenarioIdx)] = self.project.idxToDate(start_slot_idx + 1)

        self.scheduled = True
        self.property[('scheduled', self.scenarioIdx)] = True
        return True

    def scheduleSlot(self):
        # Determine duration type
        # :effortTask, :lengthTask, :durationTask, :startEndTask, or milestone

        effort = self.property.get('effort', self.scenarioIdx) or 0
        length = self.property.get('length', self.scenarioIdx) or 0
        duration = self.property.get('duration', self.scenarioIdx) or 0
        milestone = self.property.get('milestone', self.scenarioIdx)

        # We need state tracking for done effort/duration
        if not hasattr(self, 'doneEffort'): self.doneEffort = 0
        if not hasattr(self, 'doneDuration'): self.doneDuration = 0
        if not hasattr(self, 'doneLength'): self.doneLength = 0

        forward = self.property.get('forward', self.scenarioIdx)

        # A task with no effort/duration/length and only start or end is a milestone
        # (zero duration task - instant in time)
        start_date = self.property.get('start', self.scenarioIdx)
        end_date = self.property.get('end', self.scenarioIdx)
        is_milestone = milestone or (effort == 0 and duration == 0 and length == 0 and
                                      ((start_date and not end_date) or (end_date and not start_date)))

        if is_milestone:
            # Milestone: set end = start (zero duration)
            if forward and start_date:
                self.property[('end', self.scenarioIdx)] = start_date
            elif not forward and end_date:
                self.property[('start', self.scenarioIdx)] = end_date
            return False

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
            # startEndTask - has both start and end dates explicitly set
            self.bookResources()
            # Check if reached end/start
            target_date = end_date if forward else start_date
            if target_date:
                target_idx = self.project.dateToIdx(target_date)
                if (forward and self.currentSlotIdx >= target_idx) or (not forward and self.currentSlotIdx <= target_idx):
                    return False

        return True

    def isWorkingTime(self, slotIdx):
        """
        Check if a slot index falls within working hours.

        Working hours are Mon-Fri, 9am-5pm by default.
        Returns True if the slot is during working time.
        """
        date = self.project.idxToDate(slotIdx)

        # Check weekday (0=Monday, 6=Sunday)
        weekday = date.weekday()
        if weekday >= 5:  # Saturday or Sunday
            return False

        # Check hour
        hour = date.hour
        if hour < DEFAULT_WORK_START_HOUR or hour >= DEFAULT_WORK_END_HOUR:
            return False

        return True

    def bookResources(self):
        """
        Book resources for the current slot and accumulate effort.

        Only counts effort during working hours.
        """
        # Skip non-working time slots
        if not self.isWorkingTime(self.currentSlotIdx):
            return

        # Check mandatory allocations
        allocations = self.property.get('allocate', self.scenarioIdx)

        # Get schedule granularity (seconds per slot, default 1 hour = 3600)
        granularity = self.project['scheduleGranularity'] or 3600
        hours_per_slot = granularity / 3600.0  # Convert seconds to hours

        if allocations:
            # Each allocated resource contributes hours_per_slot of effort per slot
            num_resources = len(allocations)
            self.doneEffort += hours_per_slot * num_resources
        else:
            # No allocations but still an effort task - assume 1 resource implicitly
            self.doneEffort += hours_per_slot

        # Note: doneDuration and doneLength are tracked separately in scheduleSlot
        # since duration/length tasks have their own increment logic

    def propagateDate(self, date, atEnd):
        attr = 'end' if atEnd else 'start'
        self.property[(attr, self.scenarioIdx)] = date
        # Propagate to dependencies?