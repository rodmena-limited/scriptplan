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

    def prepareScheduling(self):
        """
        Reset all scheduling related data prior to scheduling.
        Called once per scenario before scheduling begins.
        """
        self.isRunAway = False
        self.currentSlotIdx = None
        self.doneDuration = 0
        self.doneLength = 0
        self.doneEffort = 0.0
        self.scheduled = False

        # Reset the counters of all limits of this task (not parent tasks).
        # This is critical - limits track usage per period and must be reset
        # before each scheduling run to avoid carrying over counts from
        # previous scenario scheduling.
        limits = self.property.get('limits', self.scenarioIdx)
        if limits:
            limits.reset()
    
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
        effort = self.property.get('effort', self.scenarioIdx) or 0
        allocations = self.property.get('allocate', self.scenarioIdx)

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
            else:
                end_date = self.property.get('end', self.scenarioIdx)
                if end_date:
                    self.currentSlotIdx = self.project.dateToIdx(end_date) - 1
                else:
                    # ALAP mode, end at project end
                    self.currentSlotIdx = self.project.dateToIdx(self.project['end']) - 1

        # For effort tasks with allocations, don't set start yet - it will be set
        # when first resource is booked. For non-effort tasks, find first working slot.
        if forward and not self.property.get('start', self.scenarioIdx):
            if effort == 0 or not allocations:
                # Non-effort task: find first working slot and set start
                upperLimit = self.project.dateToIdx(self.project['end'])
                while self.currentSlotIdx < upperLimit and not self.isWorkingTime(self.currentSlotIdx):
                    self.currentSlotIdx += 1
                self.property[('start', self.scenarioIdx)] = self.project.idxToDate(self.currentSlotIdx)
            # For effort tasks, start will be set in bookResources() on first booking

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

        This method attempts to book allocated resources for the current time slot.
        Only resources that are available (not booked, not on leave, within working hours)
        will be booked. Effort is accumulated based on resource efficiency.
        """
        # Get allocations
        allocations = self.property.get('allocate', self.scenarioIdx)
        if not allocations:
            return

        # Track if we booked any resource this slot
        booked_any = False
        effort = self.property.get('effort', self.scenarioIdx) or 0

        for alloc in allocations:
            # alloc might be a Resource object or a string ID
            if isinstance(alloc, str):
                resource = self.project.resources[alloc]
                # If not found by full ID, search all resources by short ID
                if resource is None:
                    for res in self.project.resources:
                        if res.id == alloc:
                            resource = res
                            break
            else:
                resource = alloc

            if resource is None:
                continue

            # Try to book this resource
            if self.bookResource(resource):
                booked_any = True

                # For effort-based tasks, set start date on first booking
                if effort > 0 and self.doneEffort == 0:
                    forward = self.property.get('forward', self.scenarioIdx)
                    if forward:
                        # First booking - set start date
                        start_date = self.project.idxToDate(self.currentSlotIdx)
                        self.property[('start', self.scenarioIdx)] = start_date

                # Accumulate effort based on resource efficiency
                efficiency = resource.get('efficiency', self.scenarioIdx)
                if efficiency is None:
                    efficiency = 1.0
                self.doneEffort += efficiency

    def getAllLimits(self):
        """
        Collect limits from this task and all parent tasks.
        Returns a list of Limits objects.
        """
        all_limits = []
        task = self.property
        while task is not None:
            limits = task.get('limits', self.scenarioIdx)
            if limits:
                all_limits.append(limits)
            task = task.parent
        return all_limits

    def limitsOk(self, sbIdx, resource=None):
        """
        Check if all task limits (including parent limits) are satisfied.

        Args:
            sbIdx: Scoreboard index to check
            resource: Resource to check (for resource-specific limits)

        Returns:
            True if all limits are satisfied
        """
        for limits in self.getAllLimits():
            if not limits.ok(sbIdx, upper=True, resource=resource.id if resource else None):
                return False
        return True

    def incLimits(self, sbIdx, resource=None):
        """
        Increment all task limit counters (including parent limits).

        Args:
            sbIdx: Scoreboard index
            resource: Resource being booked (for resource-specific limits)
        """
        for limits in self.getAllLimits():
            limits.inc(sbIdx, resource=resource.id if resource else None)

    def bookResource(self, resource):
        """
        Try to book a single resource for the current slot.

        Args:
            resource: The resource to book

        Returns:
            True if booking succeeded, False otherwise
        """
        # Get the resource's scenario data
        res_scenario = resource.data[self.scenarioIdx] if resource.data else None
        if res_scenario is None:
            return False

        # Initialize resource scoreboard if needed
        if res_scenario.scoreboard is None:
            res_scenario.prepareScheduling()

        # Check if resource is available
        if not res_scenario.available(self.currentSlotIdx):
            return False

        # Check task limits for this resource (including parent limits)
        if not self.limitsOk(self.currentSlotIdx, resource):
            return False

        # Book the resource - ResourceScenario.book will call back to incLimits
        return res_scenario.book(self.currentSlotIdx, self.property)

    def propagateDate(self, date, atEnd):
        attr = 'end' if atEnd else 'start'
        self.property[(attr, self.scenarioIdx)] = date
        # Propagate to dependencies?