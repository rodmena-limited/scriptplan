from typing import TYPE_CHECKING, Any, Optional

from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.task_scenario import TaskScenario

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class Task(PropertyTreeNode):
    def __init__(self, project: "Project", id: str, name: str, parent: Optional["Task"]) -> None:
        # super init calls project.tasks.addProperty(self)
        super().__init__(project.tasks, id, name, parent)

        # In Ruby: project.addTask(self)
        # But PropertyTreeNode.__init__ already adds to propertySet.
        # project.tasks IS the propertySet for tasks.
        # So it might be redundant or project specific logic.
        # We'll assume super() handles registration with project.tasks

        # Initialize scenarios
        scenario_count = self.project.scenarioCount() if hasattr(self.project, "scenarioCount") else 1
        self.data: list[Optional[TaskScenario]] = [None] * scenario_count

        for i in range(scenario_count):
            # @scenarioAttributes is initialized in PropertyTreeNode
            TaskScenario(self, i, self._scenarioAttributes[i])

    def readyForScheduling(self, scenarioIdx: int) -> bool:
        scenario = self.data[scenarioIdx]
        if scenario:
            return scenario.readyForScheduling()
        return False

    def prepareScheduling(self, scenarioIdx: int) -> None:
        scenario = self.data[scenarioIdx]
        if scenario and hasattr(scenario, "prepareScheduling"):
            # self.data[scenarioIdx] is TaskScenario
            # TaskScenario doesn't implement prepareScheduling?
            # Wait, ScenarioData might? Or TaskScenario should.
            scenario.prepareScheduling()

    def finishScheduling(self, scenarioIdx: int) -> None:
        scenario = self.data[scenarioIdx]
        if scenario and hasattr(scenario, "finishScheduling"):
            scenario.finishScheduling()

    def schedule(self, scenarioIdx: int) -> bool:
        scenario = self.data[scenarioIdx]
        if scenario:
            return scenario.schedule()
        return False

    def journalText(self, query: Any, longVersion: bool, recursive: bool) -> Optional[str]:
        # Implementation of journalText logic
        # Depends on project.journal, RichText, etc.

        r_text = ""

        # Mocking journal retrieval
        journal = self.project.attributes.get("journal")
        if not journal:
            return None

        # Both branches assign empty list, simplified
        entries: list[Any] = []

        # Sorting logic would go here

        for _entry in entries:
            # Build r_text similar to Ruby
            pass

        if not r_text:
            return None

        # Rich Text generation
        # rti = RichText(r_text, ...).generateIntermediateFormat()
        # query.rti = rti
        return None
