"""
TableReport - Base class for tabular report content generators.

This module provides the TableReport class which is the base for all types
of tabular reports. All tabular reports are converted to an abstract
(output independent) intermediate form first, before being turned into
the requested output format.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from scriptplan.report.report_base import ReportBase

if TYPE_CHECKING:
    from scriptplan.core.property import PropertyList
    from scriptplan.report.report import Report


class Alignment(Enum):
    """Column alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ReportTableCell:
    """
    Represents a single cell in a report table.

    Attributes:
        text: Cell text content
        alignment: Cell alignment
        colspan: Number of columns to span
        rowspan: Number of rows to span
        indent: Indentation level
        is_header: Whether this is a header cell
        style_class: Optional style class
        tooltip: Optional tooltip text
    """

    def __init__(
        self,
        text: str = "",
        alignment: Alignment = Alignment.LEFT,
        colspan: int = 1,
        rowspan: int = 1,
        indent: int = 0,
        is_header: bool = False,
        style_class: str = "",
        tooltip: str = "",
    ):
        self.text = text
        self.alignment = alignment
        self.colspan = colspan
        self.rowspan = rowspan
        self.indent = indent
        self.is_header = is_header
        self.style_class = style_class
        self.tooltip = tooltip

    def to_json(self) -> dict[str, Any]:
        """Convert cell to JSON-serializable dict."""
        data: dict[str, Any] = {
            "text": self.text,
            "alignment": self.alignment.value,
            "is_header": self.is_header,
        }

        if self.colspan > 1:
            data["colspan"] = self.colspan
        if self.rowspan > 1:
            data["rowspan"] = self.rowspan
        if self.indent > 0:
            data["indent"] = self.indent
        if self.style_class:
            data["style_class"] = self.style_class
        if self.tooltip:
            data["tooltip"] = self.tooltip

        return data


class ReportTableLine:
    """
    Represents a row in a report table.

    Attributes:
        cells: List of cells in this row
        property: The property this row represents
        scenario_idx: The scenario index for this row
        is_hidden: Whether this row should be hidden
        style_class: Optional style class for the row
    """

    def __init__(self, property_node: Any = None, scenario_idx: int = 0):
        self.cells: list[ReportTableCell] = []
        self.property = property_node
        self.scenario_idx = scenario_idx
        self.is_hidden = False
        self.style_class = ""

    def add_cell(self, cell: ReportTableCell) -> None:
        """Add a cell to this row."""
        self.cells.append(cell)

    def to_json(self) -> dict[str, Any]:
        """Convert row to JSON-serializable dict."""
        if self.is_hidden:
            return {"hidden": True}

        data: dict[str, Any] = {
            "cells": [cell.to_json() for cell in self.cells],
        }

        if self.style_class:
            data["style_class"] = self.style_class

        return data


class ReportTableColumn:
    """
    Stores column-specific computed values.

    Attributes:
        start: Start date for column period
        end: End date for column period
    """

    def __init__(self, start: Any = None, end: Any = None):
        self.start = start
        self.end = end


class ReportTable:
    """
    Represents a complete report table.

    Attributes:
        header_lines: Header rows
        body_lines: Body rows
        footer_lines: Footer rows
        self_contained: Whether resources are embedded
        aux_dir: Auxiliary files directory
    """

    def __init__(self) -> None:
        self.header_lines: list[ReportTableLine] = []
        self.body_lines: list[ReportTableLine] = []
        self.footer_lines: list[ReportTableLine] = []
        self.self_contained = True
        self.aux_dir = ""

    def add_header_line(self, line: ReportTableLine) -> None:
        """Add a header row."""
        self.header_lines.append(line)

    def add_body_line(self, line: ReportTableLine) -> None:
        """Add a body row."""
        self.body_lines.append(line)

    def add_footer_line(self, line: ReportTableLine) -> None:
        """Add a footer row."""
        self.footer_lines.append(line)

    def to_json(self) -> dict[str, Any]:
        """Convert table to JSON-serializable dict with clean data structure."""
        # Extract column names from header (lowercase for JSON best practices)
        column_names: list[str] = []
        if self.header_lines:
            for line in self.header_lines:
                if not line.is_hidden:
                    column_names = [cell.text.lower() for cell in line.cells]
                    break  # Use first header line

        # Convert body rows to data records
        records: list[dict[str, str]] = []
        if self.body_lines:
            for line in self.body_lines:
                if not line.is_hidden:
                    record: dict[str, str] = {}
                    for i, cell in enumerate(line.cells):
                        if i < len(column_names):
                            # Use lowercase column name as key, cell text as value
                            record[column_names[i]] = cell.text
                    records.append(record)

        return {"data": records, "columns": column_names}

    def to_csv(self) -> list[list[str]]:
        """Convert table to CSV format."""
        rows = []

        for line in self.header_lines:
            rows.append([cell.text for cell in line.cells])

        for line in self.body_lines:
            rows.append([cell.text for cell in line.cells])

        for line in self.footer_lines:
            rows.append([cell.text for cell in line.cells])

        return rows


class ReportTableLegend:
    """
    Legend for the report table.

    Shows explanations for icons, colors, and symbols used in the report.
    """

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []  # (symbol, description)

    def add_item(self, symbol: str, description: str) -> None:
        """Add a legend item."""
        self.items.append((symbol, description))

    def to_json(self) -> list[dict[str, str]]:
        """Convert legend to JSON-serializable list."""
        return [{"symbol": symbol, "description": description} for symbol, description in self.items]


class TableReport(ReportBase):
    """
    Base class for all tabular reports.

    All tabular reports are converted to an abstract (output independent)
    intermediate form first, before being turned into the requested output
    format (JSON, CSV, etc.).

    Attributes:
        table: The intermediate table representation
        columns: Column-specific computed values
        legend: Report legend
    """

    # Column properties: ID -> (Header, Indent, Alignment, ScenarioSpecific)
    PROPERTIES_BY_ID: ClassVar[dict[str, tuple[str, bool, Alignment, bool]]] = {
        "activetasks": ("Active Tasks", True, Alignment.RIGHT, True),
        "alert": ("Alert", True, Alignment.LEFT, False),
        "alertmessages": ("Alert Messages", False, Alignment.LEFT, False),
        "alertsummaries": ("Alert Summaries", False, Alignment.LEFT, False),
        "alerttrend": ("Alert Trend", False, Alignment.LEFT, False),
        "bsi": ("BSI", False, Alignment.LEFT, False),
        "children": ("Children", False, Alignment.LEFT, False),
        "closedtasks": ("Closed Tasks", True, Alignment.RIGHT, True),
        "complete": ("Completion", False, Alignment.RIGHT, True),
        "cost": ("Cost", True, Alignment.RIGHT, True),
        "duration": ("Duration", True, Alignment.RIGHT, True),
        "effort": ("Effort", True, Alignment.RIGHT, True),
        "effortdone": ("Effort Done", True, Alignment.RIGHT, True),
        "effortleft": ("Effort Left", True, Alignment.RIGHT, True),
        "end": ("End", True, Alignment.RIGHT, True),
        "followers": ("Followers", False, Alignment.LEFT, True),
        "freetime": ("Free Time", True, Alignment.RIGHT, True),
        "freework": ("Free Work", True, Alignment.RIGHT, True),
        "fte": ("FTE", True, Alignment.RIGHT, True),
        "headcount": ("Headcount", True, Alignment.RIGHT, True),
        "id": ("Id", False, Alignment.LEFT, False),
        "inputs": ("Inputs", False, Alignment.LEFT, True),
        "journal": ("Journal", False, Alignment.LEFT, False),
        "line": ("Line No.", False, Alignment.RIGHT, False),
        "name": ("Name", True, Alignment.LEFT, False),
        "no": ("No.", False, Alignment.RIGHT, False),
        "opentasks": ("Open Tasks", True, Alignment.RIGHT, True),
        "precursors": ("Precursors", False, Alignment.LEFT, True),
        "priority": ("Priority", True, Alignment.RIGHT, True),
        "rate": ("Rate", True, Alignment.RIGHT, True),
        "resources": ("Resources", False, Alignment.LEFT, True),
        "responsible": ("Responsible", False, Alignment.LEFT, True),
        "revenue": ("Revenue", True, Alignment.RIGHT, True),
        "scenario": ("Scenario", False, Alignment.LEFT, True),
        "scheduling": ("Scheduling Mode", True, Alignment.LEFT, True),
        "start": ("Start", True, Alignment.RIGHT, True),
        "status": ("Status", False, Alignment.LEFT, True),
        "targets": ("Targets", False, Alignment.LEFT, True),
    }

    def __init__(self, report: "Report"):
        """
        Initialize TableReport.

        Args:
            report: The parent Report object
        """
        super().__init__(report)
        self.report.content = self
        self.table: Optional[ReportTable] = None
        self.columns: dict[Any, ReportTableColumn] = {}
        self.legend = ReportTableLegend()

    def generate_intermediate_format(self) -> None:
        """Generate the intermediate table format."""
        super().generate_intermediate_format()

    def to_json(self) -> Optional[dict[str, Any]]:
        """
        Convert the table report to JSON-serializable dict.

        Returns:
            JSON-serializable dict or None
        """
        if not self.table:
            return None

        # Get the clean data structure from table
        data: dict[str, Any] = self.table.to_json()

        # Add report metadata only if present and useful
        if self.project.reportContexts:
            dynamic_id = self.project.reportContexts[-1].dynamic_report_id
            if dynamic_id:
                data["report_id"] = str(dynamic_id)

        # Add header text if present
        header = self.a("header")
        if header:
            data["header"] = str(header)

        # Add caption if present
        caption = self.a("caption")
        if caption:
            data["caption"] = str(caption)

        # Add footer text if present
        footer = self.a("footer")
        if footer:
            data["footer"] = str(footer)

        return data

    def to_csv(self) -> Optional[list[list[str]]]:
        """
        Convert the table report to CSV.

        Returns:
            List of rows or None
        """
        if not self.table:
            return None
        return self.table.to_csv()

    @classmethod
    def default_column_title(cls, column_id: str) -> Optional[str]:
        """
        Get the default column title for a column ID.

        Args:
            column_id: The column identifier

        Returns:
            Default title or None
        """
        # Special columns without fixed titles
        if column_id in ("chart", "hourly", "daily", "weekly", "monthly", "quarterly", "yearly"):
            return ""

        if column_id in cls.PROPERTIES_BY_ID:
            return cls.PROPERTIES_BY_ID[column_id][0]
        return None

    @classmethod
    def indent(cls, column_id: str, property_type: Any = None) -> bool:
        """
        Determine if column values should be indented.

        Args:
            column_id: The column identifier
            property_type: The property type class

        Returns:
            True if values should be indented
        """
        if column_id in cls.PROPERTIES_BY_ID:
            return cls.PROPERTIES_BY_ID[column_id][1]
        return False

    @classmethod
    def alignment(cls, column_id: str, attribute_type: Any = None) -> Alignment:
        """
        Get the alignment for a column.

        Args:
            column_id: The column identifier
            attribute_type: The attribute type class

        Returns:
            Alignment enum value
        """
        if column_id in cls.PROPERTIES_BY_ID:
            return cls.PROPERTIES_BY_ID[column_id][2]
        return Alignment.CENTER

    @classmethod
    def is_calculated(cls, column_id: str) -> bool:
        """
        Check if column values need to be calculated.

        Args:
            column_id: The column identifier

        Returns:
            True if values are calculated
        """
        return column_id in cls.PROPERTIES_BY_ID

    @classmethod
    def is_scenario_specific(cls, column_id: str) -> bool:
        """
        Check if column values are scenario specific.

        Args:
            column_id: The column identifier

        Returns:
            True if scenario specific
        """
        if column_id in cls.PROPERTIES_BY_ID:
            return cls.PROPERTIES_BY_ID[column_id][3]
        return False

    def generate_header_cell(self, column_def: Any) -> ReportTableCell:
        """
        Generate a header cell for a column.

        Args:
            column_def: Column definition (can be dict, object with id attr, or string)

        Returns:
            ReportTableCell for the header
        """
        # Handle different column_def formats
        if isinstance(column_def, dict):
            column_id = column_def.get("id", str(column_def))
            options = column_def.get("options", {})
            title = options.get("title") if options else None
        elif hasattr(column_def, "id"):
            column_id = column_def.id
            title = getattr(column_def, "title", None)
        else:
            column_id = str(column_def)
            title = None

        if not title:
            title = self.default_column_title(column_id) or column_id

        return ReportTableCell(text=title, alignment=self.alignment(column_id), is_header=True)

    def generate_cell(self, property_node: Any, column_def: Any, scenario_idx: int = 0) -> ReportTableCell:
        """
        Generate a data cell for a property and column.

        Args:
            property_node: The property (task/resource)
            column_def: Column definition (can be dict, object with id attr, or string)
            scenario_idx: Scenario index

        Returns:
            ReportTableCell for the data
        """
        # Handle different column_def formats
        if isinstance(column_def, dict):
            column_id = column_def.get("id", str(column_def))
        elif hasattr(column_def, "id"):
            column_id = column_def.id
        else:
            column_id = str(column_def)

        alignment = self.alignment(column_id)
        should_indent = self.indent(column_id)
        indent_level = property_node.level() if should_indent and hasattr(property_node, "level") else 0

        # Get the value
        value = self._get_cell_value(property_node, column_id, scenario_idx)
        text = self._format_value(value, column_id)

        return ReportTableCell(text=text, alignment=alignment, indent=indent_level)

    def _get_cell_value(self, property_node: Any, column_id: str, scenario_idx: int) -> Any:
        """
        Get the value for a cell.

        Args:
            property_node: The property
            column_id: Column identifier
            scenario_idx: Scenario index

        Returns:
            The cell value
        """
        try:
            # Handle special computed columns
            if column_id == "revenue":
                return self._get_revenue_value(property_node, scenario_idx)
            elif column_id == "cost":
                return self._get_cost_value(property_node, scenario_idx)

            if self.is_scenario_specific(column_id):
                return property_node.get(column_id, scenario_idx) if hasattr(property_node, "get") else None
            else:
                return property_node.get(column_id) if hasattr(property_node, "get") else None
        except (ValueError, KeyError, AttributeError):
            # Unknown attribute - return placeholder
            return "-"

    def _get_revenue_value(self, property_node: Any, scenario_idx: int) -> Any:
        """
        Get the revenue value for a task.

        Revenue is the sum of charges that go to revenue accounts.
        """
        if not hasattr(property_node, "get"):
            return None

        charge = property_node.get("charge", scenario_idx)
        if not charge or charge == 0:
            return None

        # Check if the chargeset is a revenue account
        chargeset_id = property_node.get("chargeset", scenario_idx)
        if not chargeset_id:
            return None

        # Look up the account and check if it's a revenue account
        # For now, use a simple heuristic: if the chargeset is 'rev' or similar
        # A more complete implementation would check the account's properties
        if isinstance(chargeset_id, str) and ("rev" in chargeset_id.lower() or chargeset_id == "rev"):
            # Simple check: 'rev' accounts are revenue accounts
            return charge

        return None

    def _get_cost_value(self, property_node: Any, scenario_idx: int) -> Any:
        """
        Get the cost value for a task.

        Cost is calculated as: allocated_time * resource_rate
        Uses the task's getCost() method if available.
        """
        if not hasattr(property_node, "data"):
            return None

        # Get the task scenario data
        if not property_node.data or scenario_idx >= len(property_node.data):
            return None

        task_scenario = property_node.data[scenario_idx]
        if task_scenario is None:
            return None

        # Use getCost() method if available
        if hasattr(task_scenario, "getCost"):
            cost = task_scenario.getCost()
            if cost and cost > 0:
                return cost

        return None

    def _format_value(self, value: Any, column_id: str) -> str:
        """
        Format a value for display.

        Args:
            value: The value to format
            column_id: Column identifier for context

        Returns:
            Formatted string
        """
        from datetime import datetime

        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, datetime):
            # Use report's timeFormat, falling back to project's timeformat
            timeformat = self.a("timeFormat")
            # Check if it's the default - if so, try project's timeformat
            if timeformat == "%Y-%m-%d":
                project_timeformat = self.project.attributes.get("timeformat")
                if project_timeformat:
                    timeformat = project_timeformat
            if timeformat:
                return value.strftime(timeformat)
            return str(value)
        if isinstance(value, float):
            return f"{value:.2f}"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    def adjust_column_period(
        self, column_def: Any, tasks: Optional["PropertyList"] = None, scenarios: Optional[list[int]] = None
    ) -> None:
        """
        Adjust the column period based on task dates.

        If the user has not specified the report period, try to fit all
        tasks and add extra time at both ends for certain column types.

        Args:
            column_def: Column definition
            tasks: List of tasks
            scenarios: List of scenario indices
        """
        # Determine start date
        do_not_adjust_start = False
        do_not_adjust_end = False

        if hasattr(column_def, "start") and column_def.start:
            r_start = column_def.start
            do_not_adjust_start = True
        else:
            r_start = self.a("start")
            if r_start != self.project.attributes.get("start"):
                do_not_adjust_start = True

        if hasattr(column_def, "end") and column_def.end:
            r_end = column_def.end
            do_not_adjust_end = True
        else:
            r_end = self.a("end")
            if r_end != self.project.attributes.get("end"):
                do_not_adjust_end = True

        # Store the column info
        self.columns[column_def] = ReportTableColumn(r_start, r_end)

        # Early exit if no adjustment needed
        if not tasks or not scenarios or (do_not_adjust_start and do_not_adjust_end):
            return

        # Find task date range
        task_start = None
        task_end = None

        for scenario_idx in scenarios:
            for task in tasks:
                # Use __getitem__ with tuple for scenario-specific access
                start = task["start", scenario_idx] if hasattr(task, "__getitem__") else None
                end = task["end", scenario_idx] if hasattr(task, "__getitem__") else None

                if start and (task_start is None or start < task_start):
                    task_start = start
                if end and (task_end is None or end > task_end):
                    task_end = end

        # Update column range if found
        if task_start and not do_not_adjust_start:
            self.columns[column_def].start = task_start
        if task_end and not do_not_adjust_end:
            self.columns[column_def].end = task_end
