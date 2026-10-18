"""Turning parsed blocks into the model's smaller pieces.

Scenarios, journal entries, attribute inheritance, and resolving the references
one task makes to another. Each is a step in building the project that is
separable from the task and resource construction around it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scriptplan.core.task import Task

from scriptplan.core.exceptions import SemanticError
from scriptplan.core.project import Project

__all__ = [
    "allocation_ids",
    "create_journal_entry",
    "create_scenario",
    "inherit_all_attributes",
    "resolve_task_reference",
    "scenario_index",
    "validate_allocations",
]


def create_journal_entry(builder: Any, task: Task, entry_data: dict[str, Any]) -> None:
    """Create a journal entry for a task.

    Args:
        task: The Task object this entry belongs to
        entry_data: Dict with 'date', 'headline', and 'body' keys
    """
    from scriptplan.core.journal import AlertLevel

    journal = task.project.attributes.get("journal")
    if journal is None:
        return

    date = entry_data.get("date")
    headline = entry_data.get("headline", "")
    body = entry_data.get("body", {})

    # Create the journal entry
    entry = journal.create_entry(date, headline, task)

    # Set body attributes
    if body.get("author"):
        # Look up the author resource
        author_id = body["author"]
        author = task.project.resources[author_id] if author_id else None
        entry.author = author

    alert_str = body.get("alert", "green")
    if alert_str == "red":
        entry.alert_level = AlertLevel.RED
    elif alert_str == "yellow":
        entry.alert_level = AlertLevel.YELLOW
    else:
        entry.alert_level = AlertLevel.GREEN

    entry.summary = body.get("summary")
    entry.details = body.get("details")


def create_scenario(builder: Any, project: Project, scenario_data: dict[str, Any], parent: Any | None = None) -> None:
    """Create a scenario in the project.

    Args:
        project: The project
        scenario_data: Dict with 'id', 'name', 'children'
        parent: Parent scenario for nested scenarios
    """
    from scriptplan.core.scenario import Scenario

    s_id = str(scenario_data.get("id", ""))
    s_name = str(scenario_data.get("name", "")).strip('"')
    children = scenario_data.get("children", [])

    # Clear default scenario on first scenario definition
    if parent is None and not hasattr(builder, "_scenarios_cleared"):
        # Remove the default 'plan' scenario
        default_plan = project.scenarios["plan"]
        if default_plan:
            project.scenarios.removeProperty(default_plan)
        builder._scenarios_cleared = True

    # Create the scenario
    scenario = Scenario(project, s_id, s_name, parent)

    # Create nested child scenarios
    for child in children:
        if isinstance(child, tuple) and child[0] == "scenario":
            create_scenario(builder, project, child[1], scenario)


def scenario_index(builder: Any, project: Project, scenario_id: str) -> int | None:
    """Get the index of a scenario by its ID."""
    for i, scenario in enumerate(project.scenarios):
        if scenario.id == scenario_id:
            return i
    return None


def inherit_all_attributes(builder: Any, project: Project) -> None:
    """Inherit attributes from parent nodes for all tasks and resources."""

    # Process tasks in tree order (parents before children)
    def inherit_recursive(node: Any) -> None:
        node.inheritAttributes()
        for child in node.children:
            inherit_recursive(child)

    # Get top-level items (no parent)
    for task in project.tasks:
        if not task.parent:
            inherit_recursive(task)

    for resource in project.resources:
        if not resource.parent:
            inherit_recursive(resource)


def validate_allocations(builder: Any, project: Project) -> None:
    """Reject an allocation naming a resource that does not exist.

    Resource lookup is otherwise lazy and forgiving: an unknown id resolves
    to None at scheduling time and the task quietly books nothing.
    """
    known = {resource.id for resource in project.resources}
    known.update(resource.fullId for resource in project.resources)

    for task in project.tasks:
        for scIdx in range(project.scenarioCount()):
            for name in allocation_ids(task.get("allocate", scIdx)):
                if name not in known:
                    raise SemanticError(
                        f"task '{task.fullId}' allocates '{name}', which is not a resource "
                        f"in this project. The task would silently book nothing."
                    )
            break  # allocate is set identically for every scenario here


def allocation_ids(allocations: Any) -> list[str]:
    """Resource ids named by an allocate attribute, primary and alternative."""
    from scriptplan.core.allocation_plan import AllocationPlan

    names: list[str] = []
    for entry in AllocationPlan._entries(allocations):
        resource = entry.get("resource")
        if isinstance(resource, str):
            names.append(resource)
        names.extend(name for name in entry.get("alternative", []) if isinstance(name, str))
    return names


def resolve_task_reference(builder: Any, project: Project, from_task: Task, ref: str) -> Task | None:
    """Resolve a task reference string to a Task object, scoped as the .tjp format scopes it.

    Each leading "!" moves the scope up one level from the referring task, so
    "!x" is a sibling and "!!x" a child of the grandparent; with no "!" the
    path starts at the project root. A path then names children level by
    level ("parent.child").

    A reference that does not resolve that way but can mean only one task in
    the project, such as "!!pack" written for the sibling "!pack", is bound to
    that task, as it always was. One that could mean several is an error: the
    parser used to bind the first task with that id anywhere in the project,
    silently, which puts a dependency on the wrong task when ids repeat
    (issuedb #18).
    """
    if not ref:
        return None

    level = len(ref) - len(ref.lstrip("!"))
    path = ref[level:]
    # No "!": from the project root. Otherwise up one level per "!".
    scope: Any = from_task if level else None
    for _ in range(level):
        if scope is None:
            break
        scope = scope.parent
    else:
        found = _walk_path(project, scope, path.split("."))
        if found is not None:
            return found

    candidates = [t for t in project.tasks if t.fullId == path or t.fullId.endswith("." + path)]
    if len(candidates) > 1:
        names = ", ".join(sorted(t.fullId for t in candidates))
        raise SemanticError(
            f"task '{from_task.fullId}' refers to '{ref}', which does not name a task from where it "
            f"is written and could mean any of: {names}. Write the reference with its full path."
        )
    if not candidates:
        return None
    # The only task the reference can mean: bound as before, with no message,
    # so the showcase projects that rely on it read exactly as they did.
    resolved = candidates[0]
    return resolved  # type: ignore[return-value]


def _walk_path(project: Project, scope: Any, parts: list[str]) -> Task | None:
    """The task at ``parts`` below ``scope``, or below the project root when ``scope`` is None."""
    children = scope.children if scope is not None else [t for t in project.tasks if t.parent is None]
    current: Any = None
    for part in parts:
        current = next((child for child in children if child.id == part), None)
        if current is None:
            return None
        children = current.children
    found: Task | None = current
    return found
