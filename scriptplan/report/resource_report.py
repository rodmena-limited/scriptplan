"""
ResourceReport - Resource list report content generator.

This module provides the ResourceReport class (equivalent to ResourceListRE
in Ruby) which generates a list of resources that can optionally have the
assigned tasks nested underneath each resource line.
"""

from typing import TYPE_CHECKING, Any

from scriptplan.core.property import PropertyList
from scriptplan.report.table_report import Alignment, ReportTable, ReportTableCell, ReportTableLine, TableReport

if TYPE_CHECKING:
    from scriptplan.report.report import Report


class ResourceReport(TableReport):
    """
    Resource list report generator.

    This specialization of TableReport implements a resource listing. It
    generates a list of resources that can optionally have the assigned
    tasks nested underneath each resource line.

    Attributes:
        table: The intermediate table representation
    """

    def __init__(self, report: "Report"):
        """
        Initialize ResourceReport.

        Args:
            report: The parent Report object
        """
        super().__init__(report)
        self.table: ReportTable = ReportTable()
        self_contained = report.get("selfContained")
        self.table.self_contained = self_contained if self_contained is not None else True
        aux_dir = report.get("auxDir")
        self.table.aux_dir = aux_dir or ""

    def generate_intermediate_format(self) -> None:
        """
        Generate the table in the intermediate format.

        This method prepares the resource list, optionally filters it,
        generates the header row, and then generates a row for each resource
        (and optionally nested tasks).
        """
        super().generate_intermediate_format()

        # Prepare the resource list
        resource_list = self._prepare_resource_list()

        # Prepare the task list (for nested tasks under resources)
        task_list = self._prepare_task_list()

        # Generate table header
        columns = self.a("columns") or []
        self._generate_header(columns)

        # Generate resource list with optional nested tasks
        self._generate_resource_list(resource_list, task_list, columns)

    def _prepare_resource_list(self) -> PropertyList:
        """
        Prepare and filter the resource list.

        Returns:
            Filtered and sorted PropertyList of resources
        """
        resource_list: PropertyList = PropertyList(self.project.resources)

        # Include adopted resources
        if hasattr(resource_list, "includeAdopted"):
            resource_list.includeAdopted()

        # Apply sorting
        sort_resources = self.a("sortResources")
        if sort_resources:
            resource_list.setSorting(sort_resources)

        # Set query for sorting
        if self.project.reportContexts:
            resource_list.query = self.project.reportContexts[-1].query

        # Filter the list
        resource_list = self.filter_resource_list(
            resource_list,
            task=None,
            hide_expr=self.a("hideResource"),
            rollup_expr=self.a("rollupResource"),
            open_nodes=self.a("openNodes"),
        )

        # Sort after filtering
        self._sort_resource_list(resource_list)

        return resource_list

    def _prepare_task_list(self) -> PropertyList:
        """
        Prepare the task list for nested display.

        Returns:
            Sorted PropertyList of tasks
        """
        task_list: PropertyList = PropertyList(self.project.tasks)

        for task in self.project.tasks:
            task_list.append(task)

        sort_tasks = self.a("sortTasks")
        if sort_tasks:
            task_list.setSorting(sort_tasks)

        if self.project.reportContexts:
            task_list.query = self.project.reportContexts[-1].query

        self._sort_task_list(task_list)

        return task_list

    def _sort_resource_list(self, resource_list: PropertyList) -> None:
        """
        Sort the resource list according to report settings.

        Args:
            resource_list: The list to sort
        """
        # Use PropertyList's built-in sorting which sorts by seqno by default
        resource_list.sort()

    def _sort_task_list(self, task_list: PropertyList) -> None:
        """
        Sort the task list according to report settings.

        Args:
            task_list: The list to sort
        """
        # Use PropertyList's built-in sorting which sorts by seqno by default
        task_list.sort()

    def _generate_header(self, columns: list[Any]) -> None:
        """
        Generate the table header row.

        Args:
            columns: List of column definitions
        """
        header_line = ReportTableLine()

        for column_def in columns:
            cell = self.generate_header_cell(column_def)
            header_line.add_cell(cell)

        self.table.add_header_line(header_line)

    def _generate_resource_list(self, resource_list: PropertyList, task_list: PropertyList, columns: list[Any]) -> None:
        """
        Generate rows for each resource in the list.

        Args:
            resource_list: List of resources to display
            task_list: List of tasks (for nested display)
            columns: Column definitions
        """
        scenario_indices = self.get_scenario_indices()
        scenario_idx = scenario_indices[0] if scenario_indices else 0

        for resource in resource_list:
            # Generate resource row
            resource_line = self._generate_resource_line(resource, columns, scenario_idx)
            self.table.add_body_line(resource_line)

            # Optionally generate nested task rows
            if self._should_show_tasks():
                nested_tasks = self._get_tasks_for_resource(resource, task_list, scenario_idx)
                for task in nested_tasks:
                    task_line = self._generate_task_line(task, resource, columns, scenario_idx)
                    task_line.style_class = "nested_task"
                    self.table.add_body_line(task_line)

    def _generate_resource_line(self, resource: Any, columns: list[Any], scenario_idx: int) -> ReportTableLine:
        """
        Generate a table row for a resource.

        Args:
            resource: The resource property
            columns: Column definitions
            scenario_idx: Scenario index

        Returns:
            ReportTableLine for the resource
        """
        line = ReportTableLine(resource, scenario_idx)
        line.style_class = "resource_row"

        for column_def in columns:
            cell = self._generate_resource_cell(resource, column_def, scenario_idx)
            line.add_cell(cell)

        return line

    def _generate_resource_cell(self, resource: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a cell for a resource column.

        Args:
            resource: The resource property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell for the resource column
        """
        column_id = column_def.id if hasattr(column_def, "id") else str(column_def)

        # Handle special columns
        if column_id == "chart":
            return self._generate_load_chart_cell(resource, column_def, scenario_idx)
        elif column_id in ("hourly", "daily", "weekly", "monthly", "quarterly", "yearly"):
            return self._generate_calendar_cell(resource, column_def, scenario_idx)

        # Standard cell generation
        return self.generate_cell(resource, column_def, scenario_idx)

    def _generate_load_chart_cell(self, resource: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a load chart cell for a resource.

        Args:
            resource: The resource property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell with load chart representation
        """
        # Simplified - show efficiency or FTE for now
        efficiency = resource.get("efficiency", scenario_idx) if hasattr(resource, "get") else 1.0
        text = f"{efficiency:.0%}" if efficiency else ""

        return ReportTableCell(text=text, alignment=Alignment.RIGHT)

    def _generate_calendar_cell(self, resource: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a calendar column cell for a resource.

        Args:
            resource: The resource property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell with calendar data
        """
        # Placeholder - would show availability per time period
        return ReportTableCell(text="", alignment=Alignment.RIGHT)

    def _should_show_tasks(self) -> bool:
        """
        Check if tasks should be shown nested under resources.

        Returns:
            True if tasks should be nested
        """
        return self.a("showTasks") or False

    def _get_tasks_for_resource(self, resource: Any, task_list: PropertyList, scenario_idx: int) -> list[Any]:
        """
        Get tasks assigned to a resource.

        Args:
            resource: The resource
            task_list: All tasks
            scenario_idx: Scenario index

        Returns:
            List of tasks assigned to the resource
        """
        result = []
        start = self.a("start")
        end = self.a("end")

        for task in task_list:
            if hasattr(task, "hasResourceAllocated") and task.hasResourceAllocated(
                scenario_idx, (start, end), resource
            ):
                result.append(task)

        return result

    def _generate_task_line(self, task: Any, resource: Any, columns: list[Any], scenario_idx: int) -> ReportTableLine:
        """
        Generate a nested task row under a resource.

        Args:
            task: The task
            resource: The parent resource
            columns: Column definitions
            scenario_idx: Scenario index

        Returns:
            ReportTableLine for the nested task
        """
        line = ReportTableLine(task, scenario_idx)

        for column_def in columns:
            col_id = column_def.id if hasattr(column_def, "id") else str(column_def)

            if col_id == "name":
                # Indent the task name
                name = task.get("name") if hasattr(task, "get") else str(task)
                cell = ReportTableCell(
                    text=name,
                    alignment=Alignment.LEFT,
                    indent=1,  # Extra indent for nested
                )
            else:
                cell = self.generate_cell(task, column_def, scenario_idx)

            line.add_cell(cell)

        return line
