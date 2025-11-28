"""
Report - Base class for all report types.

This module implements the Report class which holds the fundamental description
and functionality to turn a scheduled project into user-readable form.
A report may contain other reports (nested reports).
"""

import os
from typing import TYPE_CHECKING, Optional, List, Any, Dict
from enum import Enum
from pathlib import Path

from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.scenario_data import ScenarioData
from scriptplan.utils.message_handler import MessageHandler
from scriptplan.report.report_context import ReportContext
from scriptplan.report.html_generator import (
    build_html_document, get_default_css
)

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class ReportFormat(Enum):
    """Supported report output formats."""
    HTML = 'html'
    CSV = 'csv'
    ICAL = 'ical'
    TJP = 'tjp'
    CTAGS = 'ctags'
    NIKU = 'niku'
    MSPXML = 'mspxml'


class ReportType(Enum):
    """Supported report types."""
    TASK_REPORT = 'taskreport'
    RESOURCE_REPORT = 'resourcereport'
    ACCOUNT_REPORT = 'accountreport'
    TEXT_REPORT = 'textreport'
    TRACE_REPORT = 'tracereport'
    STATUS_SHEET = 'statusSheet'
    TIME_SHEET = 'timeSheet'
    ICAL = 'iCal'
    NIKU = 'niku'
    EXPORT = 'export'
    TAG_FILE = 'tagfile'


class ReportScenario(ScenarioData):
    """
    Dummy class to make the 'flags' attribute work for reports.
    Reports don't have scenario-specific attributes but need this
    for consistent flag handling.
    """
    pass


class Report(PropertyTreeNode, MessageHandler):
    """
    Base class for all reports.

    The Report class holds the fundamental description and functionality to
    turn the scheduled project into a user readable form. A report may contain
    other reports (nested reports).

    Attributes:
        type_spec: The type of report (task, resource, text, etc.)
        content: The generated content object (TaskListRE, ResourceListRE, etc.)
    """

    def __init__(self, project: 'Project', id: str, name: str, parent: Optional['Report'] = None):
        """
        Create a new Report object.

        Args:
            project: The Project object
            id: Unique identifier for this report
            name: Display name (also used as filename)
            parent: Optional parent report for nested reports
        """
        super().__init__(project.reports, id, name, parent)

        self._check_filename(name)
        project.addReport(self)

        # The type specifier must be set for every report
        self.type_spec: Optional[ReportType] = None

        # The generated content object
        self.content: Optional[Any] = None

        # Reports need scenario data for flag handling
        scenario_count = project.scenarioCount()
        self.data = [None] * scenario_count
        for i in range(scenario_count):
            self.data[i] = ReportScenario(self, i, self._scenarioAttributes[i])

    def _check_filename(self, name: str) -> None:
        """
        Validate the filename for the report.

        Args:
            name: The filename to validate
        """
        if not name:
            return

        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in name:
                self.error('invalid_filename',
                          f"Report filename '{name}' contains invalid character '{char}'")

    def generate(self, requested_formats: Optional[List[ReportFormat]] = None) -> int:
        """
        Generate the report in the requested formats.

        This is where the main action happens. The report defined by all class
        attributes and report elements is generated according to the requested
        output format(s).

        Args:
            requested_formats: List of formats to generate. If None, uses
                              formats specified in report definition.

        Returns:
            0 on success, non-zero on error
        """
        # Store current timezone and set report timezone
        # old_timezone = TjTime.setTimeZone(self.get('timezone'))

        # Generate intermediate format first
        self.generate_intermediate_format()

        # Determine which formats to generate
        formats = requested_formats or self.get('formats') or []

        for fmt in formats:
            if not self.name:
                self.error('empty_report_file_name',
                          f"Report {self.id} has output formats requested, "
                          "but the file name is empty.")
                continue

            if fmt == ReportFormat.ICAL:
                self._generate_ical()
            elif fmt == ReportFormat.HTML:
                self._generate_html()
                self._copy_auxiliary_files()
            elif fmt == ReportFormat.CSV:
                self._generate_csv()
            elif fmt == ReportFormat.CTAGS:
                self._generate_ctags()
            elif fmt == ReportFormat.NIKU:
                self._generate_niku()
            elif fmt == ReportFormat.TJP:
                self._generate_tjp()
            elif fmt == ReportFormat.MSPXML:
                self._generate_msp_xml()
            else:
                raise ValueError(f"Unknown report output format {fmt}")

        # Restore timezone
        # TjTime.setTimeZone(old_timezone)

        return 0

    def generate_intermediate_format(self) -> None:
        """
        Generate an output format agnostic version.

        This intermediate format can later be turned into the respective
        output formats (HTML, CSV, etc.).
        """
        # scenarios = self.get('scenarios') or []
        # if not scenarios:
        #     self.warning('all_scenarios_disabled',
        #                 f"The report {self.fullId} has only disabled scenarios. "
        #                 "The report will possibly be empty.")

        self.content = None

        # Import report type classes here to avoid circular imports
        if self.type_spec == ReportType.TASK_REPORT:
            from scriptplan.report.task_report import TaskReport
            self.content = TaskReport(self)
        elif self.type_spec == ReportType.RESOURCE_REPORT:
            from scriptplan.report.resource_report import ResourceReport
            self.content = ResourceReport(self)
        elif self.type_spec == ReportType.TEXT_REPORT:
            from scriptplan.report.text_report import TextReport
            self.content = TextReport(self)
        elif self.type_spec == ReportType.ACCOUNT_REPORT:
            # from scriptplan.report.account_report import AccountReport
            # self.content = AccountReport(self)
            pass
        elif self.type_spec == ReportType.TRACE_REPORT:
            # from scriptplan.report.trace_report import TraceReport
            # self.content = TraceReport(self)
            pass
        elif self.type_spec == ReportType.STATUS_SHEET:
            # from scriptplan.report.status_sheet_report import StatusSheetReport
            # self.content = StatusSheetReport(self)
            pass
        elif self.type_spec == ReportType.TIME_SHEET:
            # from scriptplan.report.time_sheet_report import TimeSheetReport
            # self.content = TimeSheetReport(self)
            pass
        elif self.type_spec == ReportType.ICAL:
            # from scriptplan.report.ical_report import ICalReport
            # self.content = ICalReport(self)
            pass
        elif self.type_spec == ReportType.NIKU:
            # from scriptplan.report.niku_report import NikuReport
            # self.content = NikuReport(self)
            pass
        elif self.type_spec == ReportType.EXPORT:
            # from scriptplan.report.export_report import ExportReport
            # self.content = ExportReport(self)
            pass
        elif self.type_spec == ReportType.TAG_FILE:
            # from scriptplan.report.tag_file import TagFile
            # self.content = TagFile(self)
            pass
        else:
            if self.type_spec:
                raise ValueError(f"Unknown report type: {self.type_spec}")

        # Generate intermediate format for the content
        if self.content:
            self.content.generate_intermediate_format()

    def to_html(self) -> Optional[str]:
        """
        Render the content of the report as HTML.

        Returns:
            HTML string or None if no content
        """
        return self.content.to_html() if self.content else None

    def to_csv(self) -> Optional[List[List[str]]]:
        """
        Convert the report to CSV format.

        Returns:
            List of rows, each row being a list of column values
        """
        return self.content.to_csv() if self.content else None

    def interactive(self) -> bool:
        """
        Check if report should be rendered in interactive version.

        The top-level report defines the output format and the interactive setting.

        Returns:
            True if interactive mode, False otherwise
        """
        if self.project.reportContexts:
            top_report = self.project.reportContexts[0].report
            return top_report.get('interactive') or False
        return False

    def _get_output_path(self, extension: str) -> Path:
        """
        Get the output file path for a given extension.

        Args:
            extension: File extension (e.g., 'html', 'csv')

        Returns:
            Full path to output file
        """
        output_dir = self.project.outputDir or './'
        base_name = self.name or self.id
        return Path(output_dir) / f"{base_name}.{extension}"

    def _generate_html(self) -> None:
        """Generate HTML output."""
        if not self.content:
            return

        if not hasattr(self.content, 'to_html'):
            self.warning('html_not_supported',
                        f"HTML format is not supported for report {self.id} "
                        f"of type {self.type_spec}")
            return

        html_content = self._build_html_document()
        output_path = self._get_output_path('html')

        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _build_html_document(self) -> str:
        """
        Build complete HTML document.

        Returns:
            Complete HTML document as string
        """
        title = f"{self.project.name} - {self.get('title') or self.name}"
        body_content = self.content.to_html() if self.content else ""
        if body_content is None:
            body_content = ""

        # Build navigation for sibling reports
        navigation = self._build_navigation()

        # Build subtitle from report period
        subtitle = self._build_subtitle()

        return build_html_document(
            title=title,
            content=body_content,
            project_name=self.project.name,
            subtitle=subtitle,
            navigation=navigation,
            include_css=True,
            footer=True
        )

    def _build_navigation(self) -> Optional[List[Dict[str, str]]]:
        """
        Build navigation links for sibling reports.

        Returns:
            List of navigation items or None
        """
        # Get all reports in the project
        reports = list(self.project.reports)
        if not reports or len(reports) <= 1:
            return None

        navigation = []
        for report in reports:
            # Skip reports without names (they won't have HTML output)
            if not report.name:
                continue

            nav_item = {
                'title': report.get('title') or report.name,
                'url': f'{report.name}.html',
                'active': report == self
            }
            navigation.append(nav_item)

        return navigation if len(navigation) > 1 else None

    def _build_subtitle(self) -> str:
        """
        Build subtitle showing report period or other context.

        Returns:
            Subtitle string
        """
        parts = []

        # Add report period if defined
        start = self.get('start')
        end = self.get('end')
        if start and end:
            from scriptplan.report.html_generator import format_date
            parts.append(f"{format_date(start)} - {format_date(end)}")

        # Add scenario info if multiple scenarios
        scenarios = self.get('scenarios') or []
        if len(scenarios) > 1:
            scenario_names = []
            for scen in scenarios:
                # Handle both scenario names and indices
                if isinstance(scen, int):
                    if scen < len(self.project.scenarios):
                        scenario_names.append(self.project.scenarios[scen].name)
                elif isinstance(scen, str):
                    # Resolve scenario name to get display name
                    for proj_scen in self.project.scenarios:
                        if proj_scen.id == scen:
                            scenario_names.append(proj_scen.name or scen)
                            break
                    else:
                        scenario_names.append(scen)  # Use raw name if not found
            if scenario_names:
                parts.append(f"Scenarios: {', '.join(scenario_names)}")

        return ' | '.join(parts) if parts else ''

    def _generate_csv(self) -> None:
        """Generate CSV output."""
        if not self.content:
            return

        if not hasattr(self.content, 'to_csv'):
            self.warning('csv_not_supported',
                        f"CSV format is not supported for report {self.id} "
                        f"of type {self.type_spec}")
            return

        csv_data = self.content.to_csv()
        if not csv_data:
            return

        output_path = self._get_output_path('csv')
        os.makedirs(output_path.parent, exist_ok=True)

        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)

    def _generate_ical(self) -> None:
        """Generate iCal output."""
        # To be implemented
        pass

    def _generate_ctags(self) -> None:
        """Generate ctags output."""
        # To be implemented
        pass

    def _generate_niku(self) -> None:
        """Generate Niku output."""
        # To be implemented
        pass

    def _generate_tjp(self) -> None:
        """Generate TJP export output."""
        # To be implemented
        pass

    def _generate_msp_xml(self) -> None:
        """Generate MS Project XML output."""
        # To be implemented
        pass

    def _copy_auxiliary_files(self) -> None:
        """Copy CSS and other auxiliary files to output directory."""
        # To be implemented - copy CSS files, icons, etc.
        pass

    def addReport(self, report: 'Report') -> None:
        """
        Add this report to the project.
        This is called from __init__ to register with project.

        Note: This method is on Project, not Report. It's here for documentation.
        """
        pass


def add_report_to_project(project: 'Project', report: Report) -> None:
    """
    Helper function to add a report to a project.

    Args:
        project: The project to add the report to
        report: The report to add
    """
    # The report is already added via PropertySet in __init__
    pass
