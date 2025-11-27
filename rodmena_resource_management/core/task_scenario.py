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
            # dep can be a dict with 'task' key (new format with gap),
            # or a Task object directly (old format)
            if isinstance(dep, dict):
                t = dep.get('task')
            elif hasattr(dep, 'task'):
                t = dep.task
            else:
                t = dep  # Assuming it resolved to Task

            if t and not t.get('scheduled', self.scenarioIdx):
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
                        # dep can be a dict with 'task' key (new format with gap),
                        # or a Task object directly (old format)
                        if isinstance(dep, dict):
                            t = dep.get('task')
                            gapduration = dep.get('gapduration')
                            gaplength = dep.get('gaplength')
                        elif hasattr(dep, 'task'):
                            t = dep.task
                            gapduration = getattr(dep, 'gapduration', None)
                            gaplength = getattr(dep, 'gaplength', None)
                        else:
                            t = dep
                            gapduration = None
                            gaplength = None

                        if not t:
                            continue

                        dep_end = t.get('end', self.scenarioIdx)
                        if dep_end:
                            # Add gap if specified
                            if gapduration:
                                # gapduration is calendar time (e.g., "4h" = 4 hours)
                                gap_hours = self._parse_duration(gapduration)
                                from datetime import timedelta
                                dep_end = dep_end + timedelta(hours=gap_hours)
                            elif gaplength:
                                # gaplength is working time - need to find next working slot after gap
                                gap_hours = self._parse_duration(gaplength)
                                gap_slots = int(gap_hours)  # Each slot is 1 hour
                                dep_end_idx = self.project.dateToIdx(dep_end)
                                # Skip gap_slots of working time
                                working_slots = 0
                                while working_slots < gap_slots:
                                    if self.isWorkingTime(dep_end_idx):
                                        working_slots += 1
                                    dep_end_idx += 1
                                dep_end = self.project.idxToDate(dep_end_idx)
                            if dep_end > earliest_start:
                                earliest_start = dep_end

                    self.currentSlotIdx = self.project.dateToIdx(earliest_start)
            else:
                end_date = self.property.get('end', self.scenarioIdx)
                if end_date:
                    # For ALAP, start from the last working slot BEFORE the end date
                    self.currentSlotIdx = self.project.dateToIdx(end_date) - 1
                    # Find the last working slot
                    lowerLimit = self.project.dateToIdx(self.project['start'])
                    while self.currentSlotIdx > lowerLimit and not self.isWorkingTime(self.currentSlotIdx):
                        self.currentSlotIdx -= 1
                else:
                    # ALAP mode, end at project end
                    self.currentSlotIdx = self.project.dateToIdx(self.project['end']) - 1
                    # Find the last working slot
                    lowerLimit = self.project.dateToIdx(self.project['start'])
                    while self.currentSlotIdx > lowerLimit and not self.isWorkingTime(self.currentSlotIdx):
                        self.currentSlotIdx -= 1

        # For effort tasks with allocations, don't set start yet - it will be set
        # when first resource is booked. For non-effort tasks, find first working slot.
        # Exception: milestones happen at the exact dependency end time (no need for working slot)
        milestone = self.property.get('milestone', self.scenarioIdx)
        duration = self.property.get('duration', self.scenarioIdx) or 0
        length = self.property.get('length', self.scenarioIdx) or 0
        is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)
        if forward and not self.property.get('start', self.scenarioIdx) and not is_milestone:
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
            # For backward scheduling: end is at the beginning (first slot scheduled),
            # start is at current position (last slot scheduled)
            # Even if end was constrained, update to actual end time (slot + 1 hour)
            actual_end = self.project.idxToDate(start_slot_idx + 1)
            constrained_end = self.property.get('end', self.scenarioIdx)
            # If constrained end is a "day boundary" (midnight), use actual end instead
            if constrained_end and constrained_end.hour == 0 and constrained_end.minute == 0:
                self.property[('end', self.scenarioIdx)] = actual_end
            elif not constrained_end:
                self.property[('end', self.scenarioIdx)] = actual_end

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

        # A task with no effort/duration/length is a milestone (zero duration task)
        # This includes tasks that only have dependencies but no work
        start_date = self.property.get('start', self.scenarioIdx)
        end_date = self.property.get('end', self.scenarioIdx)
        is_milestone = milestone or (effort == 0 and duration == 0 and length == 0)

        if is_milestone:
            # Milestone: set end = start (zero duration)
            if forward:
                if start_date:
                    self.property[('end', self.scenarioIdx)] = start_date
                else:
                    # No start date - use current slot (set by dependency calculation)
                    date = self.project.idxToDate(self.currentSlotIdx)
                    self.property[('start', self.scenarioIdx)] = date
                    self.property[('end', self.scenarioIdx)] = date
            else:
                if end_date:
                    self.property[('start', self.scenarioIdx)] = end_date
                else:
                    date = self.project.idxToDate(self.currentSlotIdx)
                    self.property[('start', self.scenarioIdx)] = date
                    self.property[('end', self.scenarioIdx)] = date
            return False

        if effort > 0:
            # Store effort before booking to calculate fraction used in final slot
            effort_before = self.doneEffort
            self.bookResources()

            if self.doneEffort >= effort:
                # Finished - calculate precise end time within the final slot
                end_date = self._calculatePreciseEndTime(effort, effort_before, forward)
                self.propagateDate(end_date, forward)
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

    def _calculatePreciseEndTime(self, required_effort, effort_before_slot, forward):
        """
        Calculate the precise end time within the final slot based on fractional effort.

        When a task completes within a slot, we need to determine exactly when
        within that slot the required effort was reached, rather than rounding
        to slot boundaries.

        Args:
            required_effort: Total effort required for the task (hours)
            effort_before_slot: Effort accumulated before the current slot (hours)
            forward: True for forward scheduling, False for backward

        Returns:
            datetime: The precise end time
        """
        from datetime import timedelta

        # Get slot parameters
        slot_duration_seconds = self.project.attributes.get('scheduleGranularity', 3600)
        slot_start = self.project.idxToDate(self.currentSlotIdx)

        # Get the resource efficiency for this slot
        # We need to find what resource was booked for this slot
        allocations = self.property.get('allocate', self.scenarioIdx) or []
        efficiency = 1.0
        for alloc in allocations:
            if isinstance(alloc, str):
                resource = None
                for res in self.project.resources:
                    if res.id == alloc:
                        resource = res
                        break
            else:
                resource = alloc
            if resource:
                eff = resource.get('efficiency', self.scenarioIdx)
                if eff is not None:
                    efficiency = eff
                break

        # Calculate effort gained per second in this slot
        slot_duration_hours = slot_duration_seconds / 3600.0
        effort_per_slot = slot_duration_hours * efficiency
        effort_per_second = effort_per_slot / slot_duration_seconds

        # How much effort was needed in this final slot?
        effort_needed_in_slot = required_effort - effort_before_slot

        # How many seconds into the slot does that take?
        if effort_per_second > 0:
            seconds_into_slot = effort_needed_in_slot / effort_per_second
        else:
            seconds_into_slot = slot_duration_seconds

        # Clamp to slot duration (shouldn't exceed, but safety check)
        seconds_into_slot = min(seconds_into_slot, slot_duration_seconds)

        # Calculate the precise end time
        precise_end = slot_start + timedelta(seconds=seconds_into_slot)

        return precise_end

    def _parse_duration(self, duration_str):
        """
        Parse a duration string like '4h', '2d', '1w' into hours.
        """
        if not duration_str:
            return 0
        import re
        match = re.match(r'(\d+(?:\.\d+)?)\s*([hdwmy])?', str(duration_str).lower())
        if not match:
            return 0
        num = float(match.group(1))
        unit = match.group(2) or 'h'
        multipliers = {'h': 1, 'd': 8, 'w': 40, 'm': 160, 'y': 1920}
        return num * multipliers.get(unit, 1)

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
                # Effort per slot = slot_duration_hours * efficiency
                efficiency = resource.get('efficiency', self.scenarioIdx)
                if efficiency is None:
                    efficiency = 1.0
                slot_duration_seconds = self.project.attributes.get('scheduleGranularity', 3600)
                slot_duration_hours = slot_duration_seconds / 3600.0
                self.doneEffort += slot_duration_hours * efficiency

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

    def finishScheduling(self):
        """
        Finish scheduling for this task.
        For container tasks, compute start/end from children.
        """
        # Recursively process children first
        for child in self.property.children:
            child_scenario = child.data[self.scenarioIdx] if child.data else None
            if child_scenario and hasattr(child_scenario, 'finishScheduling'):
                child_scenario.finishScheduling()

        # For container tasks, set dates from children
        if not self.property.leaf():
            self.scheduleContainer()

    def scheduleContainer(self):
        """
        Compute and set start/end dates for a container task based on its children.
        """
        if self.scheduled or self.property.leaf():
            return

        n_start = None
        n_end = None

        for child in self.property.children:
            child_scenario = child.data[self.scenarioIdx] if child.data else None
            if not child_scenario:
                continue

            # Abort if a child has not been scheduled
            if not child.get('scheduled', self.scenarioIdx):
                return

            child_start = child.get('start', self.scenarioIdx)
            child_end = child.get('end', self.scenarioIdx)

            if child_start is None or child_end is None:
                return

            if n_start is None or child_start < n_start:
                n_start = child_start
            if n_end is None or child_end > n_end:
                n_end = child_end

        # Set the container dates
        current_start = self.property.get('start', self.scenarioIdx)
        current_end = self.property.get('end', self.scenarioIdx)

        if n_start and (current_start is None or current_start > n_start):
            self.property[('start', self.scenarioIdx)] = n_start

        if n_end and (current_end is None or current_end < n_end):
            self.property[('end', self.scenarioIdx)] = n_end

        if n_start and n_end:
            self.scheduled = True
            self.property[('scheduled', self.scenarioIdx)] = True

    def _getResourcesForTask(self):
        """
        Get the actual Resource objects for this task.

        Looks up resources from either 'assignedresources' (if populated)
        or 'allocate' (resource IDs), resolving them to Resource objects.

        Returns:
            List of Resource objects
        """
        resources = []

        # Try assignedresources first
        assigned = self.property.get('assignedresources', self.scenarioIdx) or []
        if assigned:
            return assigned

        # Fall back to allocate (which may contain IDs or resource objects)
        allocate = self.property.get('allocate', self.scenarioIdx) or []
        for res in allocate:
            if isinstance(res, str):
                # Look up resource by ID
                for resource in self.project.resources:
                    if resource.id == res:
                        resources.append(resource)
                        break
            else:
                # Already a resource object
                resources.append(res)

        return resources

    def getCost(self):
        """
        Calculate the cost for this task based on allocated time and resource rates.

        Cost is calculated as: allocated_time × resource_rate
        where allocated_time is the actual duration (not effort).

        For efficiency > 1.0, allocated_time < effort
        For efficiency < 1.0, allocated_time > effort

        Returns:
            The total cost for this task
        """
        total_cost = 0.0

        # Get resources for this task
        resources = self._getResourcesForTask()

        for resource in resources:
            # Get the resource's scenario data
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario is None or res_scenario.scoreboard is None:
                continue

            # Get resource rate
            rate = resource.get('rate', self.scenarioIdx) or 0.0
            if rate == 0.0:
                continue

            # Count slots booked for this task by this resource
            booked_slots = 0
            for i in range(len(res_scenario.scoreboard)):
                if res_scenario.scoreboard[i] == self.property:
                    booked_slots += 1

            # Calculate allocated time in hours
            granularity = self.project.attributes.get('scheduleGranularity', 3600)
            allocated_hours = booked_slots * granularity / 3600.0

            # Cost = allocated_time × rate
            total_cost += allocated_hours * rate

        return total_cost

    def getAllocatedTime(self):
        """
        Calculate the total allocated time (duration) for this task.

        This is the actual calendar time spent on the task, which differs
        from effort when resource efficiency != 1.0.

        Returns:
            The allocated time in hours
        """
        total_allocated = 0.0

        # Get resources for this task
        resources = self._getResourcesForTask()

        for resource in resources:
            # Get the resource's scenario data
            res_scenario = resource.data[self.scenarioIdx] if resource.data else None
            if res_scenario is None or res_scenario.scoreboard is None:
                continue

            # Count slots booked for this task by this resource
            booked_slots = 0
            for i in range(len(res_scenario.scoreboard)):
                if res_scenario.scoreboard[i] == self.property:
                    booked_slots += 1

            # Calculate allocated time in hours
            granularity = self.project.attributes.get('scheduleGranularity', 3600)
            allocated_hours = booked_slots * granularity / 3600.0
            total_allocated += allocated_hours

        return total_allocated