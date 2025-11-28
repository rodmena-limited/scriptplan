"""Shift module implementing work schedule definitions.

A shift is a definition of working hours for each day of the week.
It may also contain a list of intervals that define off-duty periods or leaves.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.scenario_data import ScenarioData

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class ShiftScenario(ScenarioData):
    """Handles the scenario-specific features of a Shift object."""

    def __init__(self, shift: "Shift", scenarioIdx: int, attributes: dict[str, Any]) -> None:
        super().__init__(shift, scenarioIdx, attributes)

    def _get(self, attrName: str) -> Any:
        """Get attribute value using property's attribute access."""
        return self.property.get(attrName, self.scenarioIdx)

    def onShift(self, date: int) -> bool:
        """Returns True if the shift has working time defined for the date."""
        workinghours = self._get("workinghours")
        if workinghours:
            return workinghours.onShift(date)  # type: ignore[no-any-return]
        return False

    def replace(self) -> Any:
        """Returns the replace attribute value."""
        return self._get("replace")

    def onLeave(self, date: datetime) -> bool:
        """Returns True if the shift has a vacation/leave defined for the date."""
        leaves = self._get("leaves")
        if leaves:
            for leave in leaves:
                if hasattr(leave, "interval") and leave.interval.contains(date):
                    return True
        return False


class Shift(PropertyTreeNode):
    """A shift is a definition of working hours for each day of the week.

    It may also contain a list of intervals that define off-duty periods or leaves.
    """

    def __init__(self, project: "Project", id: str, name: str, parent: Optional["Shift"]) -> None:
        super().__init__(project.shifts, id, name, parent)
        project.addShift(self)

        # Initialize scenario data array
        self.data: list[Optional[ShiftScenario]] = [None] * project.scenarioCount()
        for i in range(project.scenarioCount()):
            ShiftScenario(self, i, self._scenarioAttributes[i])

    def scenario(self, scenarioIdx: int) -> Optional[ShiftScenario]:
        """Return a reference to the scenarioIdx-th scenario."""
        return self.data[scenarioIdx]

    def onShift(self, scenarioIdx: int, date: int) -> bool:
        """Check if shift is active on given date for the scenario."""
        scenario = self.data[scenarioIdx]
        return scenario.onShift(date) if scenario else False

    def onLeave(self, scenarioIdx: int, date: datetime) -> bool:
        """Check if there is leave defined for the date in the scenario."""
        scenario = self.data[scenarioIdx]
        return scenario.onLeave(date) if scenario else False

    def replace(self, scenarioIdx: int) -> Any:
        """Get the replace attribute for the scenario."""
        scenario = self.data[scenarioIdx]
        return scenario.replace() if scenario else None
