"""TJP Parser for TaskJuggler project files."""

import contextlib
import os
from datetime import datetime
from typing import Any, Optional, Union

from lark import Lark, Token, Transformer, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.exceptions import (
    DuplicateDefinitionError,
    SemanticError,
    UnsupportedFormatError,
)
from scriptplan.core.timezones import to_utc
from scriptplan.core.resolution import derive_resolution
from scriptplan.core.units import Duration, parse_calendar_duration, parse_working_hours
from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task
from scriptplan.parser.attribute_apply import apply_property_attributes
from scriptplan.parser.model_pieces import (
    allocation_ids,
    create_journal_entry,
    create_scenario,
    inherit_all_attributes,
    resolve_task_reference,
    scenario_index,
    validate_allocations,
)
from scriptplan.parser.report_builder import (
    apply_report_attribute,
    create_report,
    resolve_sort_criteria,
)
from scriptplan.parser.transformer_project import ProjectRules
from scriptplan.parser.transformer_report import ReportRules
from scriptplan.parser.transformer_resource import ResourceRules
from scriptplan.parser.transformer_task import TaskRules
from scriptplan.report.logical_expression import parse_expression
from scriptplan.parser.macro_processor import preprocess_tjp




class TJPTransformer(ProjectRules, ResourceRules, TaskRules, ReportRules, Transformer[Any, Any]):
    """Transform the parse tree into a dictionary structure.

    The rules are grouped by what they describe -- the project, its resources,
    its tasks, its reports -- and mixed in here, so that one file does not hold
    every rule in the grammar.
    """


class ModelBuilder:
    """Build the Project model from the parsed data."""

    def __init__(self) -> None:
        self._pending_depends: list[tuple[Task, list[Any]]] = []  # Store (task, depends_list) for later resolution
        self._pending_precedes: list[tuple[Task, list[Any]]] = []  # Store (task, precedes_list) for later resolution

    def build(self, data: dict[str, Any]) -> Project:
        """Build a Project from parsed data."""
        if not data or not data.get("project"):
            raise ValueError("No project definition found")

        proj_data = data["project"]
        timeframe = proj_data.get("timeframe", {})
        start_date = timeframe.get("start")
        duration_str = timeframe.get("duration")

        # Create project
        project = Project(
            proj_data["id"],
            proj_data["name"],
            "",  # version is not used like this
        )

        # Set project start and end dates
        if start_date:
            project["start"] = start_date
            # Calculate end date from duration if provided
            if duration_str:
                import re

                from dateutil.relativedelta import relativedelta

                match = re.match(r"(\d+)([dwmy])", duration_str)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    if unit == "d":
                        end_date = start_date + relativedelta(days=amount)
                    elif unit == "w":
                        end_date = start_date + relativedelta(weeks=amount)
                    elif unit == "m":
                        end_date = start_date + relativedelta(months=amount)
                    elif unit == "y":
                        end_date = start_date + relativedelta(years=amount)
                    else:
                        end_date = start_date
                    project["end"] = end_date

        # Apply project attributes
        self._apply_project_attributes(project, proj_data.get("attributes", []))

        # The file is written in the project's timezone; scheduling happens in
        # UTC so that resources in different zones share one axis.
        self._timezone = project["timezone"]
        for key in ("start", "end", "markdate"):
            if isinstance(project[key], datetime):
                project[key] = to_utc(project[key], self._timezone)

        # With no explicit timingresolution, the slot size is derived from the
        # times the file actually uses, so a project written to the half hour
        # is scheduled to the half hour without the user having to say so, and
        # one written to the hour keeps hour-sized slots.
        self._explicit_resolution = any(
            isinstance(attr, tuple) and attr[0] == "timingresolution"
            for attr in proj_data.get("attributes", [])
        )

        # Apply global attributes
        self._apply_global_attributes(project, data.get("global_attributes", []))

        # Apply property declarations (resources, tasks, accounts)
        for prop in data.get("property_declarations", []):
            self._create_property(project, prop)

        # Resolve dependencies after all tasks are created
        self._resolve_dependencies(project)

        # Resolve precedes relationships (convert to dependencies on target tasks)
        self._resolve_precedes(project)

        # Every allocation must name a resource that exists.
        self._validate_allocations(project)

        # Inherit attributes from parents for all tasks
        self._inherit_all_attributes(project)

        # Now that every task, shift and resource is known, the slot size can
        # be chosen to fit the times they use.
        if not getattr(self, "_explicit_resolution", False):
            project["timingresolution"] = derive_resolution(project)

        # Create reports
        for report_data in data.get("reports", []):
            self._create_report(project, report_data)

        return project

    def _resolve_dependencies(self, project: Project) -> None:
        """Resolve task dependency references to actual Task objects."""
        for task, depends_list in self._pending_depends:
            resolved: list[Any] = []
            for dep_item in depends_list:
                # dep_item can be a dict with 'ref' key or a string (for backwards compat)
                if isinstance(dep_item, dict):
                    dep_ref = dep_item.get("ref", "")
                    gapduration = dep_item.get("gapduration")
                    gaplength = dep_item.get("gaplength")
                    maxgapduration = dep_item.get("maxgapduration")
                    onstart = dep_item.get("onstart", False)
                    onend = dep_item.get("onend", False)
                else:
                    dep_ref = dep_item
                    gapduration = None
                    gaplength = None
                    maxgapduration = None
                    onstart = False
                    onend = False

                dep_task = self._resolve_task_reference(project, task, dep_ref)
                if dep_task is None:
                    raise SemanticError(
                        f"task '{task.fullId}' depends on '{dep_ref}', which is not a task in "
                        f"this project. A dependency that does not resolve would silently "
                        f"disappear from the schedule."
                    )
                if dep_task:
                    # Store as dict if we have gap info or onstart/onend, else just the task
                    if gapduration or gaplength or maxgapduration or onstart or onend:
                        resolved.append(
                            {
                                "task": dep_task,
                                "gapduration": gapduration,
                                "gaplength": gaplength,
                                "maxgapduration": maxgapduration,
                                "onstart": onstart,
                                "onend": onend,
                            }
                        )
                    else:
                        resolved.append(dep_task)
            if resolved:
                # Set dependencies for all scenarios
                for scIdx in range(project.scenarioCount()):
                    task[("depends", scIdx)] = resolved

    def _resolve_precedes(self, project: Project) -> None:
        """Resolve precedes relationships by adding dependencies to target tasks.

        If task A precedes task B, then B depends on A.
        This is the inverse of the 'depends' relationship.
        """
        for source_task, precedes_list in self._pending_precedes:
            for prec_item in precedes_list:
                # prec_item can be a dict with 'ref' key or a string
                prec_ref = prec_item.get("ref", "") if isinstance(prec_item, dict) else prec_item

                target_task = self._resolve_task_reference(project, source_task, prec_ref)
                if target_task is None:
                    raise SemanticError(
                        f"task '{source_task.fullId}' precedes '{prec_ref}', which is not a task "
                        f"in this project."
                    )
                if target_task:
                    # Add source_task as a dependency of target_task
                    for scIdx in range(project.scenarioCount()):
                        existing_deps = target_task.get("depends", scIdx) or []
                        if not isinstance(existing_deps, list):
                            existing_deps = [existing_deps] if existing_deps else []
                        # Check if source_task is already in dependencies
                        already_exists = False
                        for dep in existing_deps:
                            dep_task = dep.get("task") if isinstance(dep, dict) else dep
                            if dep_task is source_task:
                                already_exists = True
                                break
                        if not already_exists:
                            existing_deps.append(source_task)
                            target_task[("depends", scIdx)] = existing_deps

    def _apply_project_attributes(self, project: Project, attributes: list[Any]) -> None:
        """Apply attributes to the project."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                if key == "scenario":
                    self._create_scenario(project, value)
                elif key == "extend":
                    pass  # Handle extensions later
                else:
                    with contextlib.suppress(ValueError, KeyError):
                        project[key] = value

    def _apply_global_attributes(self, project: Project, attributes: list[Any]) -> None:
        """Apply global attributes to the project."""
        from scriptplan.core.leave import Leave
        from scriptplan.utils.time import TimeInterval

        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                if key == "leaves":
                    # Global leaves - convert dict to Leave object
                    leave_type = value.get("type", "holiday")
                    start_date = value.get("start")
                    # For single-day holidays, end_date might be None
                    end_date = value.get("end")
                    if end_date is None:
                        # Single day - end is start + 1 day
                        from datetime import timedelta

                        end_date = start_date + timedelta(days=1)

                    if start_date:
                        interval = TimeInterval(
                            to_utc(start_date, project["timezone"]),
                            to_utc(end_date, project["timezone"]),
                        )
                        type_idx = Leave.Types.get(leave_type, 1)  # Default to 'holiday' (1)
                        leave = Leave(interval, type_idx)

                        # Add to project's leaves list
                        existing = project.attributes.get("leaves", [])
                        if not isinstance(existing, list):
                            existing = [existing] if existing else []
                        existing.append(leave)
                        project.attributes["leaves"] = existing
                elif key == "vacation":
                    # Global vacation - similar to leaves but always 'holiday' type
                    start_date = value.get("start")
                    end_date = value.get("end")
                    # If end_date equals start_date (single day vacation), extend to next day
                    from datetime import timedelta

                    if end_date is None or end_date == start_date:
                        end_date = start_date + timedelta(days=1)

                    if start_date:
                        interval = TimeInterval(
                            to_utc(start_date, project["timezone"]),
                            to_utc(end_date, project["timezone"]),
                        )
                        type_idx = Leave.Types.get("holiday", 1)
                        leave = Leave(interval, type_idx)

                        # Add to project's vacations/leaves list
                        existing = project.attributes.get("vacations", [])
                        if not isinstance(existing, list):
                            existing = [existing] if existing else []
                        existing.append(leave)
                        project.attributes["vacations"] = existing
                else:
                    with contextlib.suppress(ValueError, KeyError):
                        project[key] = value

    def _create_property(self, parent: Union[Project, Task, Resource], prop_data: Any) -> None:
        """Create a property (resource, task, account) in the parent."""
        if not isinstance(prop_data, dict):
            return

        prop_type = prop_data.get("type")
        prop_id = prop_data.get("id", "")
        prop_name = prop_data.get("name", "")
        attributes = prop_data.get("attributes", [])

        # Determine project reference
        project = parent if isinstance(parent, Project) else parent.project

        obj: Union[Task, Resource, Any]
        if prop_type == "task":
            obj = Task(project, str(prop_id), str(prop_name), parent if isinstance(parent, Task) else None)
        elif prop_type == "resource":
            obj = Resource(project, str(prop_id), str(prop_name), parent if isinstance(parent, Resource) else None)
        elif prop_type == "account":
            # Skip accounts for now - need Account class
            return
        elif prop_type == "shift":
            from scriptplan.core.shift import Shift

            obj = Shift(project, str(prop_id), str(prop_name), parent if isinstance(parent, Shift) else None)
        else:
            return

        # Apply attributes to the created object
        self._apply_property_attributes(obj, attributes, prop_type)

    def _apply_property_attributes(
        self, obj: Union[Task, Resource, Any], attributes: list[Any], prop_type: str
    ) -> None:
        """Apply attributes to a property object.

        Delegates to parser.attribute_apply, which has no silent fallback: an
        attribute it cannot place raises rather than being dropped.
        """
        apply_property_attributes(self, obj, attributes, prop_type)

    def _create_report(self, project: Project, report_data: dict[str, Any], parent: Optional[Any] = None) -> Any:
        return create_report(self, project, report_data, parent)

    def _apply_report_attribute(self, report: Any, attr: Any, default_formats: list[Any]) -> None:
        apply_report_attribute(self, report, attr, default_formats)

    def _resolve_sort_criteria(self, project: Project, criteria: Any) -> list[Any]:
        return resolve_sort_criteria(self, project, criteria)


    def _create_journal_entry(self, task: Any, entry_data: dict[str, Any]) -> None:
        create_journal_entry(self, task, entry_data)

    def _create_scenario(self, project: Project, scenario_data: dict[str, Any], parent: Optional[Any] = None) -> None:
        create_scenario(self, project, scenario_data, parent)

    def _get_scenario_index(self, project: Project, scenario_id: str) -> Optional[int]:
        return scenario_index(self, project, scenario_id)

    def _inherit_all_attributes(self, project: Project) -> None:
        inherit_all_attributes(self, project)

    def _validate_allocations(self, project: Project) -> None:
        validate_allocations(self, project)

    @staticmethod
    def _allocation_ids(allocations: Any) -> list[str]:
        return allocation_ids(allocations)

    def _resolve_task_reference(self, project: Project, from_task: Any, ref: str) -> Optional[Any]:
        return resolve_task_reference(self, project, from_task, ref)


class ProjectFileParser:
    """Parser for TJP project files."""

    def __init__(self) -> None:
        grammar_path: str = os.path.join(os.path.dirname(__file__), "tjp.lark")
        with open(grammar_path) as f:
            self.grammar: str = f.read()
        self.parser: Lark = Lark(self.grammar, start="start", parser="lalr")

    def parse(self, text: str, preprocess_macros: bool = True, schedule: bool = True) -> Project:
        """Parse TJP text and return a Project object.

        Args:
            text: The TJP file content
            preprocess_macros: If True, expand macros before parsing
            schedule: If True, schedule the project after parsing to compute task dates

        Returns:
            A Project object
        """
        # Preprocess macros
        if preprocess_macros:
            text = preprocess_tjp(text)

        tree = self.parser.parse(text)
        data = TJPTransformer().transform(tree)
        builder = ModelBuilder()
        project = builder.build(data)

        # Schedule the project to compute task dates
        if schedule:
            project.schedule()

        return project

