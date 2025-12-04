"""
TaskReport - Task list report content generator.

This module provides the TaskReport class (equivalent to TaskListRE in Ruby)
which generates a list of tasks that can optionally have the allocated
resources nested underneath each task line.
"""

from typing import TYPE_CHECKING, Any

from scriptplan.core.property import PropertyList
from scriptplan.report.table_report import Alignment, ReportTable, ReportTableCell, ReportTableLine, TableReport

if TYPE_CHECKING:
    from scriptplan.report.report import Report


class TaskReport(TableReport):
    """
    Task list report generator.

    This specialization of TableReport implements a task listing. It generates
    a list of tasks that can optionally have the allocated resources nested
    underneath each task line.

    Attributes:
        table: The intermediate table representation
    """

    def __init__(self, report: "Report"):
        """
        Initialize TaskReport.

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

        This method prepares the task list, optionally filters it, generates
        the header row, and then generates a row for each task (and optionally
        nested resources).
        """
        super().generate_intermediate_format()

        # Prepare the task list
        task_list = self._prepare_task_list()

        # Prepare the resource list (for nested resources under tasks)
        resource_list = self._prepare_resource_list()

        # Generate table header
        columns = self.a("columns") or []
        self._generate_header(columns)

        # Generate task list with optional nested resources
        self._generate_task_list(task_list, resource_list, columns)

    def _prepare_task_list(self) -> PropertyList:
        """
        Prepare and filter the task list.

        Returns:
            Filtered and sorted PropertyList of tasks
        """
        task_list: PropertyList = PropertyList(self.project.tasks)

        # Include adopted tasks
        if hasattr(task_list, "includeAdopted"):
            task_list.includeAdopted()

        # Apply sorting
        sort_tasks = self.a("sortTasks")
        if sort_tasks:
            task_list.setSorting(sort_tasks)

        # Set query for sorting
        if self.project.reportContexts:
            task_list.query = self.project.reportContexts[-1].query

        # Filter the list
        task_list = self.filter_task_list(
            task_list,
            resource=None,
            hide_expr=self.a("hideTask"),
            rollup_expr=self.a("rollupTask"),
            open_nodes=self.a("openNodes"),
        )

        # Sort after filtering
        self._sort_task_list(task_list)

        # Filter to only leaf tasks if leafTasksOnly is set
        if self.a("leafTasksOnly"):
            leaf_tasks: PropertyList = PropertyList(task_list, copyItems=False)
            for task in task_list:
                if hasattr(task, "leaf") and task.leaf():
                    leaf_tasks.append(task)
            return leaf_tasks

        return task_list

    def _prepare_resource_list(self) -> PropertyList:
        """
        Prepare the resource list for nested display.

        Returns:
            Sorted PropertyList of resources
        """
        resource_list: PropertyList = PropertyList(self.project.resources)

        for resource in self.project.resources:
            resource_list.append(resource)

        sort_resources = self.a("sortResources")
        if sort_resources:
            resource_list.setSorting(sort_resources)

        if self.project.reportContexts:
            resource_list.query = self.project.reportContexts[-1].query

        self._sort_resource_list(resource_list)

        return resource_list

    def _sort_task_list(self, task_list: PropertyList) -> None:
        """
        Sort the task list according to report settings.

        Args:
            task_list: The list to sort
        """
        # Use PropertyList's built-in sorting which sorts by seqno by default
        task_list.sort()

    def _sort_resource_list(self, resource_list: PropertyList) -> None:
        """
        Sort the resource list according to report settings.

        Args:
            resource_list: The list to sort
        """
        # Use PropertyList's built-in sorting which sorts by seqno by default
        resource_list.sort()

    def _generate_header(self, columns: list[Any]) -> None:
        """
        Generate the table header row.

        Args:
            columns: List of column definitions
        """
        header_line = ReportTableLine()

        for column_def in columns:
            # Adjust column period if needed
            self.a("scenarios") or []
            # self.adjust_column_period(column_def, task_list, scenarios)

            cell = self.generate_header_cell(column_def)
            header_line.add_cell(cell)

        self.table.add_header_line(header_line)

    def _generate_task_list(self, task_list: PropertyList, resource_list: PropertyList, columns: list[Any]) -> None:
        """
        Generate rows for each task in the list.

        Args:
            task_list: List of tasks to display
            resource_list: List of resources (for nested display)
            columns: Column definitions
        """
        scenario_indices = self.get_scenario_indices()
        scenario_idx = scenario_indices[0] if scenario_indices else 0

        for task in task_list:
            # Generate task row
            task_line = self._generate_task_line(task, columns, scenario_idx)
            self.table.add_body_line(task_line)

            # Optionally generate nested resource rows
            if self._should_show_resources():
                nested_resources = self._get_resources_for_task(task, resource_list, scenario_idx)
                for resource in nested_resources:
                    resource_line = self._generate_resource_line(resource, task, columns, scenario_idx)
                    resource_line.style_class = "nested_resource"
                    self.table.add_body_line(resource_line)

    def _generate_task_line(self, task: Any, columns: list[Any], scenario_idx: int) -> ReportTableLine:
        """
        Generate a table row for a task.

        Args:
            task: The task property
            columns: Column definitions
            scenario_idx: Scenario index

        Returns:
            ReportTableLine for the task
        """
        line = ReportTableLine(task, scenario_idx)
        line.style_class = "task_row"

        for column_def in columns:
            cell = self._generate_task_cell(task, column_def, scenario_idx)
            line.add_cell(cell)

        return line

    def _generate_task_cell(self, task: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a cell for a task column.

        Args:
            task: The task property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell for the task column
        """
        column_id = column_def.id if hasattr(column_def, "id") else str(column_def)

        # Handle special columns
        if column_id == "chart":
            return self._generate_gantt_cell(task, column_def, scenario_idx)
        elif column_id in ("hourly", "daily", "weekly", "monthly", "quarterly", "yearly"):
            return self._generate_calendar_cell(task, column_def, scenario_idx)

        # Standard cell generation
        return self.generate_cell(task, column_def, scenario_idx)

    def _generate_gantt_cell(self, task: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a Gantt chart cell for a task.

        Args:
            task: The task property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell with Gantt representation
        """
        # Simplified Gantt - just show start/end dates for now
        start = task.get("start", scenario_idx) if hasattr(task, "get") else None
        end = task.get("end", scenario_idx) if hasattr(task, "get") else None

        text = ""
        if start and end:
            text = f"{start} - {end}"

        return ReportTableCell(text=text, alignment=Alignment.LEFT)

    def _generate_calendar_cell(self, task: Any, column_def: Any, scenario_idx: int) -> ReportTableCell:
        """
        Generate a calendar column cell for a task.

        Args:
            task: The task property
            column_def: Column definition
            scenario_idx: Scenario index

        Returns:
            ReportTableCell with calendar data
        """
        # Placeholder - would show effort/work per time period
        return ReportTableCell(text="", alignment=Alignment.RIGHT)

    def _should_show_resources(self) -> bool:
        """
        Check if resources should be shown nested under tasks.

        Returns:
            True if resources should be nested
        """
        # Check for 'resources' column or specific report setting
        columns = self.a("columns") or []
        for col in columns:
            col_id = col.id if hasattr(col, "id") else str(col)
            if col_id == "resources":
                return False  # Resources shown in column, not nested

        return self.a("showResources") or False

    def _get_resources_for_task(self, task: Any, resource_list: PropertyList, scenario_idx: int) -> list[Any]:
        """
        Get resources allocated to a task.

        Args:
            task: The task
            resource_list: All resources
            scenario_idx: Scenario index

        Returns:
            List of resources allocated to the task
        """
        result = []
        start = self.a("start")
        end = self.a("end")

        for resource in resource_list:
            if hasattr(task, "hasResourceAllocated") and task.hasResourceAllocated(
                scenario_idx, (start, end), resource
            ):
                result.append(resource)

        return result

    def _generate_resource_line(
        self, resource: Any, task: Any, columns: list[Any], scenario_idx: int
    ) -> ReportTableLine:
        """
        Generate a nested resource row under a task.

        Args:
            resource: The resource
            task: The parent task
            columns: Column definitions
            scenario_idx: Scenario index

        Returns:
            ReportTableLine for the nested resource
        """
        line = ReportTableLine(resource, scenario_idx)

        for column_def in columns:
            col_id = column_def.id if hasattr(column_def, "id") else str(column_def)

            if col_id == "name":
                # Indent the resource name
                name = resource.get("name") if hasattr(resource, "get") else str(resource)
                cell = ReportTableCell(
                    text=name,
                    alignment=Alignment.LEFT,
                    indent=1,  # Extra indent for nested
                )
            else:
                cell = self.generate_cell(resource, column_def, scenario_idx)

            line.add_cell(cell)

        return line
