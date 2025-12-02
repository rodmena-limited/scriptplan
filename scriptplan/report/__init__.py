"""
Reporting System for ScriptPlan.

This package provides a comprehensive reporting system for generating various
types of reports from scheduled project data. Reports can be output in multiple
formats including JSON, CSV, iCal, and others.

Main Classes:
    - Report: Base class for all report definitions
    - ReportContext: Context management during report generation
    - ReportBase: Abstract base for report content generators
    - TableReport: Base for tabular reports
    - TaskReport: Task listing reports
    - ResourceReport: Resource listing reports
    - TextReport: Simple text-based reports

Usage:
    from scriptplan.report import Report, ReportType, ReportFormat

    # Create a report
    report = Report(project, 'task_list', 'Task List', None)
    report.type_spec = ReportType.TASK_REPORT

    # Generate output
    report.generate([ReportFormat.JSON, ReportFormat.CSV])
"""

from scriptplan.report.report import (
    Report,
    ReportFormat,
    ReportScenario,
    ReportType,
)
from scriptplan.report.report_base import ReportBase
from scriptplan.report.report_context import (
    Query,
    ReportContext,
)
from scriptplan.report.resource_report import ResourceReport
from scriptplan.report.table_report import (
    Alignment,
    ReportTable,
    ReportTableCell,
    ReportTableColumn,
    ReportTableLegend,
    ReportTableLine,
    TableReport,
)
from scriptplan.report.task_report import TaskReport
from scriptplan.report.text_report import TextReport

__all__ = [
    "Alignment",
    "Query",
    # Report definition
    "Report",
    # Base classes
    "ReportBase",
    # Context
    "ReportContext",
    "ReportFormat",
    "ReportScenario",
    # Table components
    "ReportTable",
    "ReportTableCell",
    "ReportTableColumn",
    "ReportTableLegend",
    "ReportTableLine",
    "ReportType",
    "ResourceReport",
    "TableReport",
    # Report types
    "TaskReport",
    "TextReport",
]
