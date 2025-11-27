"""Shift module implementing work schedule definitions.

A shift is a definition of working hours for each day of the week.
It may also contain a list of intervals that define off-duty periods or leaves.
"""

from rodmena_resource_management.core.property import PropertyTreeNode
from rodmena_resource_management.core.scenario_data import ScenarioData


class ShiftScenario(ScenarioData):
    """Handles the scenario-specific features of a Shift object."""

    def __init__(self, shift, scenarioIdx, attributes):
        super().__init__(shift, scenarioIdx, attributes)

    def _get(self, attrName):
        """Get attribute value using property's attribute access."""
        return self.property.get(attrName, self.scenarioIdx)

    def onShift(self, date):
        """Returns True if the shift has working time defined for the date."""
        workinghours = self._get('workinghours')
        if workinghours:
            return workinghours.onShift(date)
        return False

    def replace(self):
        """Returns the replace attribute value."""
        return self._get('replace')

    def onLeave(self, date):
        """Returns True if the shift has a vacation/leave defined for the date."""
        leaves = self._get('leaves')
        if leaves:
            for leave in leaves:
                if hasattr(leave, 'interval') and leave.interval.contains(date):
                    return True
        return False


class Shift(PropertyTreeNode):
    """A shift is a definition of working hours for each day of the week.

    It may also contain a list of intervals that define off-duty periods or leaves.
    """

    def __init__(self, project, id, name, parent):
        super().__init__(project.shifts, id, name, parent)
        project.addShift(self)

        # Initialize scenario data array
        self.data = [None] * project.scenarioCount()
        for i in range(project.scenarioCount()):
            ShiftScenario(self, i, self._scenarioAttributes[i])

    def scenario(self, scenarioIdx):
        """Return a reference to the scenarioIdx-th scenario."""
        return self.data[scenarioIdx]

    def onShift(self, scenarioIdx, date):
        """Check if shift is active on given date for the scenario."""
        return self.data[scenarioIdx].onShift(date)

    def onLeave(self, scenarioIdx, date):
        """Check if there is leave defined for the date in the scenario."""
        return self.data[scenarioIdx].onLeave(date)

    def replace(self, scenarioIdx):
        """Get the replace attribute for the scenario."""
        return self.data[scenarioIdx].replace()
