"""
Tests for the reporting system.

This module contains comprehensive tests for:
- ReportContext
- Report
- TableReport
- TaskReport
- ResourceReport
- TextReport
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task
from scriptplan.report import (
    Alignment,
    Query,
    Report,
    ReportContext,
    ReportTable,
    ReportTableCell,
    ReportTableLegend,
    ReportTableLine,
    ReportType,
    ResourceReport,
    TableReport,
    TaskReport,
    TextReport,
)


class TestQuery:
    """Tests for Query class."""

    def test_query_init_empty(self):
        """Test Query initialization without attributes."""
        query = Query()
        assert query.project is None
        assert query.property is None
        assert query.load_unit == 'days'
        assert query.time_format == '%Y-%m-%d'

    def test_query_init_with_attrs(self):
        """Test Query initialization with attributes."""
        attrs = {
            'loadUnit': 'hours',
            'timeFormat': '%d/%m/%Y',
            'start': datetime(2024, 1, 1),
            'end': datetime(2024, 12, 31),
        }
        query = Query(attrs)
        assert query.load_unit == 'hours'
        assert query.time_format == '%d/%m/%Y'
        assert query.start == datetime(2024, 1, 1)
        assert query.end == datetime(2024, 12, 31)

    def test_query_copy(self):
        """Test Query copy method."""
        query = Query({'loadUnit': 'hours'})
        query.project = 'test_project'
        query.property = 'test_property'

        copy = query.copy()
        assert copy.load_unit == 'hours'
        assert copy.project == 'test_project'
        assert copy.property == 'test_property'

        # Ensure it's a copy, not same object
        copy.load_unit = 'days'
        assert query.load_unit == 'hours'


class TestReportContext:
    """Tests for ReportContext class."""

    def test_report_context_init(self):
        """Test ReportContext initialization."""
        project = Mock()
        project.reportContexts = []
        project.tasks = []
        project.resources = []

        report = Mock()
        report.get = Mock(return_value=None)

        context = ReportContext(project, report)

        assert context.project == project
        assert context.report == report
        assert context.dynamic_report_id == "0"
        assert context.child_report_counter == 0
        assert context.tasks == []
        assert context.resources == []

    def test_report_context_nested(self):
        """Test nested ReportContext with parent."""
        project = Mock()
        project.tasks = ['task1', 'task2']
        project.resources = ['res1']

        parent_report = Mock()
        parent_report.get = Mock(return_value=None)

        # Create parent context
        project.reportContexts = []
        parent_context = ReportContext(project, parent_report)
        project.reportContexts.append(parent_context)

        # Create child context
        child_report = Mock()
        child_report.get = Mock(return_value=None)
        child_context = ReportContext(project, child_report)

        assert child_context.dynamic_report_id == "0.0"
        assert parent_context.child_report_counter == 1

    def test_report_context_push_pop(self):
        """Test context push/pop operations."""
        project = Mock()
        project.reportContexts = []
        project.tasks = []
        project.resources = []

        report = Mock()
        report.get = Mock(return_value=None)

        context = ReportContext(project, report)
        context.push()

        assert len(project.reportContexts) == 1
        assert project.reportContexts[-1] is context

        context.pop()
        assert len(project.reportContexts) == 0


class TestReportTableCell:
    """Tests for ReportTableCell class."""

    def test_cell_default(self):
        """Test default cell creation."""
        cell = ReportTableCell()
        assert cell.text == ''
        assert cell.alignment == Alignment.LEFT
        assert cell.colspan == 1
        assert cell.rowspan == 1
        assert cell.indent == 0
        assert not cell.is_header

    def test_cell_with_values(self):
        """Test cell with custom values."""
        cell = ReportTableCell(
            text='Test Value',
            alignment=Alignment.RIGHT,
            colspan=2,
            indent=1,
            is_header=True,
            style_class='custom-class'
        )
        assert cell.text == 'Test Value'
        assert cell.alignment == Alignment.RIGHT
        assert cell.colspan == 2
        assert cell.indent == 1
        assert cell.is_header
        assert cell.style_class == 'custom-class'

    def test_cell_to_json_basic(self):
        """Test basic cell JSON generation."""
        cell = ReportTableCell(text='Hello')
        data = cell.to_json()
        assert isinstance(data, dict)
        assert data['text'] == 'Hello'
        assert data['is_header'] is False

    def test_cell_to_json_header(self):
        """Test header cell JSON generation."""
        cell = ReportTableCell(text='Header', is_header=True)
        data = cell.to_json()
        assert isinstance(data, dict)
        assert data['text'] == 'Header'
        assert data['is_header'] is True

    def test_cell_to_json_with_attributes(self):
        """Test cell JSON with attributes."""
        cell = ReportTableCell(
            text='Value',
            colspan=2,
            alignment=Alignment.CENTER,
            style_class='special'
        )
        data = cell.to_json()
        assert isinstance(data, dict)
        assert data['text'] == 'Value'
        assert data['colspan'] == 2
        assert data['alignment'] == 'center'
        assert data['style_class'] == 'special'


class TestReportTableLine:
    """Tests for ReportTableLine class."""

    def test_line_default(self):
        """Test default line creation."""
        line = ReportTableLine()
        assert line.cells == []
        assert line.property is None
        assert line.scenario_idx == 0
        assert not line.is_hidden

    def test_line_add_cell(self):
        """Test adding cells to a line."""
        line = ReportTableLine()
        cell1 = ReportTableCell(text='A')
        cell2 = ReportTableCell(text='B')

        line.add_cell(cell1)
        line.add_cell(cell2)

        assert len(line.cells) == 2
        assert line.cells[0].text == 'A'
        assert line.cells[1].text == 'B'

    def test_line_to_json(self):
        """Test line JSON generation."""
        line = ReportTableLine()
        line.add_cell(ReportTableCell(text='Col1'))
        line.add_cell(ReportTableCell(text='Col2'))

        data = line.to_json()
        assert isinstance(data, dict)
        assert 'cells' in data
        assert len(data['cells']) == 2
        assert data['cells'][0]['text'] == 'Col1'
        assert data['cells'][1]['text'] == 'Col2'

    def test_line_to_json_hidden(self):
        """Test hidden line returns hidden flag."""
        line = ReportTableLine()
        line.is_hidden = True
        data = line.to_json()
        assert isinstance(data, dict)
        assert data['hidden'] is True


class TestReportTable:
    """Tests for ReportTable class."""

    def test_table_default(self):
        """Test default table creation."""
        table = ReportTable()
        assert table.header_lines == []
        assert table.body_lines == []
        assert table.footer_lines == []
        assert table.self_contained

    def test_table_add_lines(self):
        """Test adding lines to table."""
        table = ReportTable()

        header = ReportTableLine()
        header.add_cell(ReportTableCell(text='Header', is_header=True))
        table.add_header_line(header)

        body = ReportTableLine()
        body.add_cell(ReportTableCell(text='Data'))
        table.add_body_line(body)

        footer = ReportTableLine()
        footer.add_cell(ReportTableCell(text='Footer'))
        table.add_footer_line(footer)

        assert len(table.header_lines) == 1
        assert len(table.body_lines) == 1
        assert len(table.footer_lines) == 1

    def test_table_to_json(self):
        """Test table JSON generation."""
        table = ReportTable()

        header = ReportTableLine()
        header.add_cell(ReportTableCell(text='Name', is_header=True))
        table.add_header_line(header)

        body = ReportTableLine()
        body.add_cell(ReportTableCell(text='Task 1'))
        table.add_body_line(body)

        data = table.to_json()
        assert isinstance(data, dict)
        assert 'columns' in data
        assert 'data' in data
        assert data['columns'] == ['name']
        assert len(data['data']) == 1
        assert data['data'][0] == {'name': 'Task 1'}

    def test_table_to_csv(self):
        """Test table CSV generation."""
        table = ReportTable()

        header = ReportTableLine()
        header.add_cell(ReportTableCell(text='Col1'))
        header.add_cell(ReportTableCell(text='Col2'))
        table.add_header_line(header)

        body = ReportTableLine()
        body.add_cell(ReportTableCell(text='A'))
        body.add_cell(ReportTableCell(text='B'))
        table.add_body_line(body)

        csv = table.to_csv()
        assert csv == [['Col1', 'Col2'], ['A', 'B']]


class TestReportTableLegend:
    """Tests for ReportTableLegend class."""

    def test_legend_empty(self):
        """Test empty legend."""
        legend = ReportTableLegend()
        assert legend.items == []
        data = legend.to_json()
        assert data == []

    def test_legend_add_items(self):
        """Test adding legend items."""
        legend = ReportTableLegend()
        legend.add_item('*', 'Important')
        legend.add_item('#', 'Milestone')

        assert len(legend.items) == 2
        assert legend.items[0] == ('*', 'Important')

    def test_legend_to_json(self):
        """Test legend JSON generation."""
        legend = ReportTableLegend()
        legend.add_item('*', 'Important')

        data = legend.to_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['symbol'] == '*'
        assert data[0]['description'] == 'Important'


class TestTableReport:
    """Tests for TableReport class."""

    def test_default_column_title(self):
        """Test default column title lookup."""
        assert TableReport.default_column_title('name') == 'Name'
        assert TableReport.default_column_title('id') == 'Id'
        assert TableReport.default_column_title('effort') == 'Effort'
        assert TableReport.default_column_title('chart') == ''
        assert TableReport.default_column_title('unknown') is None

    def test_column_indent(self):
        """Test column indent determination."""
        assert TableReport.indent('name') is True
        assert TableReport.indent('id') is False
        assert TableReport.indent('effort') is True

    def test_column_alignment(self):
        """Test column alignment."""
        assert TableReport.alignment('name') == Alignment.LEFT
        assert TableReport.alignment('effort') == Alignment.RIGHT
        assert TableReport.alignment('unknown') == Alignment.CENTER

    def test_is_calculated(self):
        """Test calculated column check."""
        assert TableReport.is_calculated('effort') is True
        assert TableReport.is_calculated('unknown') is False

    def test_is_scenario_specific(self):
        """Test scenario specific check."""
        assert TableReport.is_scenario_specific('effort') is True
        assert TableReport.is_scenario_specific('id') is False


class TestTaskReport:
    """Tests for TaskReport class."""

    def test_task_report_init(self):
        """Test TaskReport initialization."""
        project = Mock()
        project.scenarioCount = Mock(return_value=1)
        project.reportContexts = []
        project.reports = Mock()
        project.reports.addProperty = Mock()
        project.reports.items = Mock(return_value=0)
        project.reports.flat_namespace = False
        project.reports.attributeDefinitions = {}
        project.reports.attributes = []

        report = Mock()
        report.project = project
        report.get = Mock(return_value=None)
        report.content = None

        task_report = TaskReport(report)

        assert task_report.table is not None
        assert isinstance(task_report.table, ReportTable)


class TestResourceReport:
    """Tests for ResourceReport class."""

    def test_resource_report_init(self):
        """Test ResourceReport initialization."""
        project = Mock()
        project.scenarioCount = Mock(return_value=1)
        project.reportContexts = []
        project.reports = Mock()
        project.reports.addProperty = Mock()
        project.reports.items = Mock(return_value=0)
        project.reports.flat_namespace = False
        project.reports.attributeDefinitions = {}
        project.reports.attributes = []

        report = Mock()
        report.project = project
        report.get = Mock(return_value=None)
        report.content = None

        resource_report = ResourceReport(report)

        assert resource_report.table is not None
        assert isinstance(resource_report.table, ReportTable)


class TestTextReport:
    """Tests for TextReport class."""

    def test_text_report_init(self):
        """Test TextReport initialization."""
        report = Mock()
        report.project = Mock()
        report.project.reportContexts = []
        report.get = Mock(return_value=None)

        text_report = TextReport(report)

        assert text_report.content_data == {}

    def test_text_report_generate(self):
        """Test TextReport intermediate format generation."""
        report = Mock()
        report.project = Mock()
        report.project.reportContexts = []
        report.get = Mock(side_effect=lambda x: {
            'headline': 'Test Headline',
            'caption': 'Test Caption',
        }.get(x))

        text_report = TextReport(report)
        text_report.generate_intermediate_format()

        assert isinstance(text_report.content_data, dict)
        assert text_report.content_data['headline'] == 'Test Headline'
        assert text_report.content_data['caption'] == 'Test Caption'

    def test_text_report_to_csv_returns_none(self):
        """Test TextReport to_csv returns None."""
        report = Mock()
        report.project = Mock()
        report.project.reportContexts = []
        report.get = Mock(return_value=None)

        text_report = TextReport(report)
        assert text_report.to_csv() is None


class TestReportIntegration:
    """Integration tests for the reporting system."""

    @pytest.fixture
    def project(self):
        """Create a test project with tasks and resources."""
        project = Project('test', 'Test Project', '1.0')
        project.attributes['start'] = datetime(2024, 1, 1)
        project.attributes['end'] = datetime(2024, 12, 31)
        return project

    def test_create_task_report(self, project):
        """Test creating a task report."""
        # Add a task
        task = Task(project, 'task1', 'Test Task', None)

        # Create report
        report = Report(project, 'task_list', 'Task List', None)
        report.type_spec = ReportType.TASK_REPORT

        assert report.type_spec == ReportType.TASK_REPORT
        assert report.project == project

    def test_create_resource_report(self, project):
        """Test creating a resource report."""
        # Add a resource
        resource = Resource(project, 'res1', 'Test Resource', None)

        # Create report
        report = Report(project, 'resource_list', 'Resource List', None)
        report.type_spec = ReportType.RESOURCE_REPORT

        assert report.type_spec == ReportType.RESOURCE_REPORT

    def test_report_context_flow(self, project):
        """Test report context push/pop flow."""
        report = Report(project, 'test', 'Test Report', None)
        report.type_spec = ReportType.TASK_REPORT

        # Create and push context
        context = ReportContext(project, report)
        context.push()

        assert len(project.reportContexts) == 1
        assert project.reportContexts[-1] is context

        # Pop context
        context.pop()
        assert len(project.reportContexts) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
