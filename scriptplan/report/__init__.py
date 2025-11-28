"""
Reporting System for ScriptPlan.

This package provides a comprehensive reporting system for generating various
types of reports from scheduled project data. Reports can be output in multiple
formats including HTML, CSV, iCal, and others.

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
    report.generate([ReportFormat.HTML, ReportFormat.CSV])
"""

from scriptplan.report.report_context import (
    ReportContext,
    Query,
)
from scriptplan.report.report import (
    Report,
    ReportFormat,
    ReportType,
    ReportScenario,
)
from scriptplan.report.report_base import ReportBase
from scriptplan.report.table_report import (
    TableReport,
    ReportTable,
    ReportTableLine,
    ReportTableCell,
    ReportTableColumn,
    ReportTableLegend,
    Alignment,
)
from scriptplan.report.task_report import TaskReport
from scriptplan.report.resource_report import ResourceReport
from scriptplan.report.text_report import TextReport

__all__ = [
    # Context
    'ReportContext',
    'Query',
    # Report definition
    'Report',
    'ReportFormat',
    'ReportType',
    'ReportScenario',
    # Base classes
    'ReportBase',
    'TableReport',
    # Table components
    'ReportTable',
    'ReportTableLine',
    'ReportTableCell',
    'ReportTableColumn',
    'ReportTableLegend',
    'Alignment',
    # Report types
    'TaskReport',
    'ResourceReport',
    'TextReport',
]
