"""
Tests for the CLI module.

This module contains tests for the command-line interface.
"""


import pytest

from scriptplan.cli.main import ScriptPlan, create_parser, main, setup_logging


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == 'scriptplan'

    def test_parser_version(self):
        """Test version argument."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['--version'])

    def test_parser_help(self):
        """Test help argument."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])

    def test_parser_files(self):
        """Test file arguments."""
        parser = create_parser()
        args = parser.parse_args(['project.tjp'])
        assert args.files == ['project.tjp']

    def test_parser_multiple_files(self):
        """Test multiple file arguments."""
        parser = create_parser()
        args = parser.parse_args(['project.tjp', 'include1.tji', 'include2.tji'])
        assert args.files == ['project.tjp', 'include1.tji', 'include2.tji']

    def test_parser_check_syntax(self):
        """Test --check-syntax flag."""
        parser = create_parser()
        args = parser.parse_args(['--check-syntax', 'project.tjp'])
        assert args.check_syntax is True

    def test_parser_no_reports(self):
        """Test --no-reports flag."""
        parser = create_parser()
        args = parser.parse_args(['--no-reports', 'project.tjp'])
        assert args.no_reports is True

    def test_parser_force_reports(self):
        """Test --force-reports flag."""
        parser = create_parser()
        args = parser.parse_args(['-f', 'project.tjp'])
        assert args.force_reports is True

    def test_parser_output_dir(self):
        """Test --output-dir option."""
        parser = create_parser()
        args = parser.parse_args(['-o', '/tmp/reports', 'project.tjp'])
        assert args.output_dir == '/tmp/reports'

    def test_parser_report_ids(self):
        """Test --report option (multiple)."""
        parser = create_parser()
        args = parser.parse_args(['--report', 'task_list', '--report', 'resource_list', 'project.tjp'])
        assert args.report_ids == ['task_list', 'resource_list']

    def test_parser_report_patterns(self):
        """Test --reports option (regex)."""
        parser = create_parser()
        args = parser.parse_args(['--reports', 'task.*', 'project.tjp'])
        assert args.report_patterns == ['task.*']

    def test_parser_list_reports(self):
        """Test --list-reports option."""
        parser = create_parser()
        # With pattern argument
        args = parser.parse_args(['--list-reports', 'task.*', 'project.tjp'])
        assert args.list_reports == 'task.*'

        # Without pattern (uses default)
        args = parser.parse_args(['--list-reports', '--', 'project.tjp'])
        assert args.list_reports == '.*'

    def test_parser_debug_level(self):
        """Test --debug-level option."""
        parser = create_parser()
        args = parser.parse_args(['--debug-level', '2', 'project.tjp'])
        assert args.debug_level == 2

    def test_parser_debug_modules(self):
        """Test --debug-modules option."""
        parser = create_parser()
        args = parser.parse_args(['--debug-modules', 'core,scheduler', 'project.tjp'])
        assert args.debug_modules == 'core,scheduler'

    def test_parser_freeze(self):
        """Test --freeze flag."""
        parser = create_parser()
        args = parser.parse_args(['--freeze', 'project.tjp'])
        assert args.freeze is True

    def test_parser_max_cores(self):
        """Test --max-cores option."""
        parser = create_parser()
        args = parser.parse_args(['-c', '4', 'project.tjp'])
        assert args.max_cores == 4


class TestSetupLogging:
    """Tests for logging setup."""

    def test_default_logging(self):
        """Test default logging setup."""
        # Should not raise
        setup_logging()

    def test_debug_logging(self):
        """Test debug logging setup."""
        setup_logging(debug_level=2)

    def test_module_filtering(self):
        """Test logging with module filtering."""
        setup_logging(debug_level=2, debug_modules=['core', 'scheduler'])


class TestScriptPlan:
    """Tests for the ScriptPlan application class."""

    @pytest.fixture
    def simple_project_file(self, tmp_path):
        """Create a simple project file for testing."""
        content = '''project simple "Simple Project" 2024-01-01 +6m {
    timezone "UTC"
}

resource dev1 "Developer 1" {
}

task project "Project" {
    task design "Design Phase" {
        start 2024-01-01
        end 2024-01-31
    }
}
'''
        project_file = tmp_path / "simple.tjp"
        project_file.write_text(content)
        return str(project_file)

    def test_no_files_error(self):
        """Test error when no files provided."""
        parser = create_parser()
        args = parser.parse_args([])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 1

    def test_missing_file_error(self):
        """Test error when file doesn't exist."""
        parser = create_parser()
        args = parser.parse_args(['nonexistent.tjp'])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 1

    def test_invalid_output_dir(self, simple_project_file):
        """Test error when output directory doesn't exist."""
        parser = create_parser()
        args = parser.parse_args(['-o', '/nonexistent/path', simple_project_file])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 1

    def test_check_syntax(self, simple_project_file):
        """Test syntax check only."""
        parser = create_parser()
        args = parser.parse_args(['--check-syntax', simple_project_file])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 0

    def test_parse_and_schedule(self, simple_project_file):
        """Test parsing and scheduling."""
        parser = create_parser()
        args = parser.parse_args(['--no-reports', simple_project_file])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 0
        assert app.project is not None

    def test_with_output_dir(self, simple_project_file, tmp_path):
        """Test with output directory."""
        output_dir = tmp_path / "reports"
        output_dir.mkdir()

        parser = create_parser()
        args = parser.parse_args(['-o', str(output_dir), '--no-reports', simple_project_file])
        app = ScriptPlan(args)
        result = app.run()
        assert result == 0


class TestMainFunction:
    """Tests for the main entry point."""

    @pytest.fixture
    def simple_project_file(self, tmp_path):
        """Create a simple project file for testing."""
        content = '''project simple "Simple Project" 2024-01-01 +6m {
    timezone "UTC"
}

resource dev1 "Developer 1" {
}

task project "Project" {
    task design "Design Phase" {
        start 2024-01-01
        end 2024-01-31
    }
}
'''
        project_file = tmp_path / "simple.tjp"
        project_file.write_text(content)
        return str(project_file)

    def test_main_no_args(self):
        """Test main with no arguments."""
        result = main([])
        assert result == 1

    def test_main_check_syntax(self, simple_project_file):
        """Test main with --check-syntax."""
        result = main(['--check-syntax', simple_project_file])
        assert result == 0

    def test_main_no_reports(self, simple_project_file):
        """Test main with --no-reports."""
        result = main(['--no-reports', simple_project_file])
        assert result == 0


class TestIntegration:
    """Integration tests for the CLI."""

    @pytest.fixture
    def project_with_reports(self, tmp_path):
        """Create a project file with report definitions."""
        content = '''project test "Test Project" 2024-01-01 +1y {
    timezone "UTC"
}

resource dev1 "Developer 1" {
}

task project "Project" {
    task phase1 "Phase 1" {
        start 2024-01-01
        end 2024-03-31
    }
    task phase2 "Phase 2" {
        start 2024-04-01
        end 2024-06-30
    }
}
'''
        project_file = tmp_path / "test.tjp"
        project_file.write_text(content)
        return str(project_file)

    def test_full_workflow(self, project_with_reports, tmp_path):
        """Test full parse -> schedule -> report workflow."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Parse and schedule only (no reports defined in test)
        result = main(['--no-reports', '-o', str(output_dir), project_with_reports])
        assert result == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
