"""
Resource - Represents a resource in the project.

This module implements the Resource class which represents any kind of
resource that can be allocated to tasks (people, equipment, etc.).
"""

from typing import TYPE_CHECKING, Any, Callable, Optional

from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.resource_scenario import ResourceScenario

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class Resource(PropertyTreeNode):
    """
    Represents a resource in the project.

    A Resource is a PropertyTreeNode that can be allocated to tasks.
    Resources can be organized hierarchically (e.g., teams containing
    individual team members).

    Attributes:
        data: List of ResourceScenario objects, one per scenario
    """

    def __init__(self, project: "Project", id: str, name: str, parent: Optional["Resource"] = None) -> None:
        """
        Create a new Resource.

        Args:
            project: The Project this resource belongs to
            id: Unique identifier for the resource
            name: Display name of the resource
            parent: Optional parent resource (for hierarchical organization)
        """
        super().__init__(project.resources, id, name, parent)

        # Register with project
        if hasattr(project, "addResource"):
            project.addResource(self)

        # Initialize scenario data
        scenario_count = project.scenarioCount() if hasattr(project, "scenarioCount") else 1
        self.data: list[Optional[ResourceScenario]] = [None] * scenario_count

        for i in range(scenario_count):
            ResourceScenario(self, i, self._scenarioAttributes[i])

    def book(self, scenario_idx: int, sb_idx: int, task: Any) -> bool:
        """
        Book a time slot for a task.

        This is a shortcut to avoid slower calls via __getattr__.

        Args:
            scenario_idx: The scenario index
            sb_idx: The scoreboard index (time slot)
            task: The task to book

        Returns:
            True if booking succeeded, False otherwise
        """
        scenario = self.data[scenario_idx]
        if scenario:
            result = scenario.book(sb_idx, task)
            return bool(result) if result is not None else False
        return False

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """
        Forward unknown method calls to ResourceScenario.

        Many Resource functions are scenario specific. These functions are
        provided by the class ResourceScenario. In case we can't find a
        function called for the Resource class we try to find it in
        ResourceScenario.

        Args:
            name: The method name

        Returns:
            A callable that forwards to ResourceScenario
        """
        # Avoid infinite recursion for special attributes
        if name.startswith("_") or name == "data":
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        def method_forwarder(scenario_idx: int = 0, *args: Any, **kwargs: Any) -> Any:
            if self.data and self.data[scenario_idx]:
                method = getattr(self.data[scenario_idx], name, None)
                if method and callable(method):
                    return method(*args, **kwargs)
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        return method_forwarder

    def prepareScheduling(self, scenario_idx: int) -> None:
        """
        Prepare the resource for scheduling.

        Args:
            scenario_idx: The scenario index
        """
        scenario = self.data[scenario_idx]
        if scenario:
            scenario.prepareScheduling()

    def finishScheduling(self, scenario_idx: int) -> None:
        """
        Finish scheduling for this resource.

        This method does housekeeping work after scheduling is completed.
        It's meant to be called for top-level resources and then recursively
        descends into all child resources.

        Args:
            scenario_idx: The scenario index
        """
        # Recursively descend into all child resources
        for child in self.children:
            if hasattr(child, "finishScheduling"):
                child.finishScheduling(scenario_idx)

        scenario = self.data[scenario_idx]
        if scenario:
            scenario.finishScheduling()

    def bookedEffort(self, scenario_idx: int) -> float:
        """
        Get the booked effort for this resource.

        Args:
            scenario_idx: The scenario index

        Returns:
            The booked effort value
        """
        scenario = self.data[scenario_idx]
        if scenario:
            return scenario.bookedEffort()
        return 0.0

    def query_dashboard(self, query: Any) -> None:
        """
        Handle dashboard query.

        Args:
            query: The query object
        """
        self.dashboard(query)

    def dashboard(self, query: Any) -> None:
        """
        Create a dashboard-like list of all tasks that have a current alert status.

        Args:
            query: The query object
        """
        scenario_idx = self.project.attributes.get("trackingScenarioIdx")
        task_list: list[Any] = []

        if scenario_idx is None:
            r_text = "No 'trackingscenario' defined."
        else:
            journal = self.project.attributes.get("journal")
            for task in self.project.tasks:
                responsible = task.get("responsible", scenario_idx) or []
                if self in responsible and journal:
                    # Check for current entries
                    entries: list[Any] = []  # journal.currentEntries(...)
                    if entries:
                        task_list.append(task)

        if not task_list:
            r_text = f"We have no current status for any task that {self.name} is responsible for."
        else:
            r_text = ""
            for task in task_list:
                # Build rich text output
                r_text += f"=== [{task.fullId}] Task: {task.name} ===\n\n"

        # Set query result
        if hasattr(query, "rti"):
            query.rti = r_text

    def scenario(self, scenario_idx: int) -> Optional[ResourceScenario]:
        """
        Get the ResourceScenario for a given scenario index.

        Args:
            scenario_idx: The scenario index

        Returns:
            The ResourceScenario or None
        """
        if self.data and 0 <= scenario_idx < len(self.data):
            return self.data[scenario_idx]
        return None
