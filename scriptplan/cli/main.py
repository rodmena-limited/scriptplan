#!/usr/bin/env python3
"""
ScriptPlan CLI.

This is the main command-line interface for the ScriptPlan
application (Python implementation of TaskJuggler). It reads project files,
schedules the project, and generates reports.

Usage:
    scriptplan [options] <project_file.tjp> [additional_files...]

Examples:
    scriptplan project.tjp
    scriptplan --output-dir ./reports project.tjp
    scriptplan --check-syntax project.tjp
    scriptplan --report task_list project.tjp
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

from scriptplan import __version__


def setup_logging(debug_level: int = 0, debug_modules: Optional[list[str]] = None) -> None:
    """
    Configure logging based on debug settings.

    Args:
        debug_level: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        debug_modules: List of module names to enable debug for
    """
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    level = levels.get(debug_level, logging.DEBUG)

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=format_str)

    if debug_modules:
        # Set all loggers to WARNING, then enable specific ones
        logging.getLogger().setLevel(logging.WARNING)
        for module in debug_modules:
            logging.getLogger(f"scriptplan.{module}").setLevel(level)


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the CLI.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="scriptplan",
        description="ScriptPlan - A Python implementation of TaskJuggler",
        epilog="For more information, visit: https://github.com/scriptplan/scriptplan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("files", nargs="*", metavar="FILE", help="Project file(s) to process (.tjp and .tji files)")

    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    # Debug options
    debug_group = parser.add_argument_group("Debug Options")
    debug_group.add_argument(
        "--debug-level", type=int, default=0, metavar="N", help="Verbosity of debug output (0-2, default: 0)"
    )
    debug_group.add_argument(
        "--debug-modules", type=str, metavar="x,y,z", help="Restrict debug output to a comma-separated list of modules"
    )

    # Processing options
    proc_group = parser.add_argument_group("Processing Options")
    proc_group.add_argument(
        "--check-syntax", action="store_true", help="Only parse the input files and check syntax, do not schedule"
    )
    proc_group.add_argument(
        "--no-reports", action="store_true", help="Schedule the project but do not generate any reports"
    )
    proc_group.add_argument(
        "-f", "--force-reports", action="store_true", help="Generate reports even if there are scheduling errors"
    )
    proc_group.add_argument("--abort-on-warnings", action="store_true", help="Treat warnings as errors and abort")

    # Report options
    report_group = parser.add_argument_group("Report Options")
    report_group.add_argument(
        "-o", "--output-dir", type=str, metavar="DIR", help="Directory where reports should be written"
    )
    report_group.add_argument(
        "--report",
        type=str,
        action="append",
        metavar="ID",
        dest="report_ids",
        help="Generate only the report with specified ID (can be used multiple times)",
    )
    report_group.add_argument(
        "--reports",
        type=str,
        action="append",
        metavar="REGEX",
        dest="report_patterns",
        help="Generate only reports matching the regex pattern (can be used multiple times)",
    )
    report_group.add_argument(
        "--list-reports",
        type=str,
        nargs="?",
        const=".*",
        metavar="REGEX",
        help="List all reports matching the pattern (default: all)",
    )

    # Freeze options
    freeze_group = parser.add_argument_group("Freeze/Booking Options")
    freeze_group.add_argument(
        "--freeze", action="store_true", help="Generate or update the booking file for the project"
    )
    freeze_group.add_argument(
        "--freeze-date", type=str, metavar="DATE", help="Use a different date as cut-off for the booking file"
    )
    freeze_group.add_argument(
        "--freeze-by-task", action="store_true", help="Group bookings by task instead of by resource"
    )

    # Time/Status sheet options
    sheet_group = parser.add_argument_group("Time/Status Sheet Options")
    sheet_group.add_argument(
        "--check-time-sheet",
        type=str,
        action="append",
        metavar="FILE",
        dest="time_sheets",
        help="Check the given time sheet file",
    )
    sheet_group.add_argument(
        "--check-status-sheet",
        type=str,
        action="append",
        metavar="FILE",
        dest="status_sheets",
        help="Check the given status sheet file",
    )
    sheet_group.add_argument(
        "--warn-ts-deltas", action="store_true", help="Enable warnings for time sheet delta changes"
    )

    # Other options
    parser.add_argument(
        "-c", "--max-cores", type=int, default=1, metavar="N", help="Maximum number of CPU cores to use (default: 1)"
    )
    parser.add_argument("--add-trace", action="store_true", help="Append current data set to all trace reports")

    return parser


class ScriptPlan:
    """
    Main application class for ScriptPlan.

    This class orchestrates the parsing, scheduling, and report generation
    workflow.
    """

    def __init__(self, args: argparse.Namespace):
        """
        Initialize the application with parsed arguments.

        Args:
            args: Parsed command-line arguments
        """
        from scriptplan.core.project import Project

        self.args = args
        self.project: Optional[Project] = None
        self.errors = 0
        self.warnings = 0
        self.logger = logging.getLogger("scriptplan.cli")

    def run(self) -> int:
        """
        Execute the main application workflow.

        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        # Validate inputs
        if not self.args.files:
            print("Error: You must provide at least one .tjp file", file=sys.stderr)
            return 1

        # Validate output directory
        if self.args.output_dir:
            output_path = Path(self.args.output_dir)
            if not output_path.exists():
                print(f"Error: Output directory '{self.args.output_dir}' does not exist", file=sys.stderr)
                return 1
            if not output_path.is_dir():
                print(f"Error: '{self.args.output_dir}' is not a directory", file=sys.stderr)
                return 1

        # Parse project files
        if not self.parse_files(self.args.files):
            return 1

        # Syntax check only?
        if self.args.check_syntax:
            print("Syntax check passed.")
            return 0

        # Schedule the project
        if not self.schedule():
            if not self.args.force_reports:
                return 1
            print("Scheduling failed, but continuing due to --force-reports")

        # Check time sheets if requested
        if self.args.time_sheets:
            for ts_file in self.args.time_sheets:
                if not self.check_time_sheet(ts_file):
                    return 1

        # Check status sheets if requested
        if self.args.status_sheets:
            for ss_file in self.args.status_sheets:
                if not self.check_status_sheet(ss_file):
                    return 1

        # Freeze (generate bookings) if requested
        if self.args.freeze and not self.freeze_project():
            return 1

        # List reports if requested
        if self.args.list_reports:
            self.list_reports(self.args.list_reports)

        # Generate reports
        if not self.args.no_reports and not self.generate_reports():
            return 1

        return 0 if self.errors == 0 else 1

    def parse_files(self, files: list[str]) -> bool:
        """
        Parse the project files.

        Args:
            files: List of file paths to parse

        Returns:
            True if parsing succeeded, False otherwise
        """
        from scriptplan.parser.tjp_parser import ProjectFileParser

        try:
            parser = ProjectFileParser()

            # Parse the main project file
            main_file = files[0]
            self.logger.info("Parsing %s", main_file)

            if not os.path.exists(main_file):
                print(f"Error: File '{main_file}' not found", file=sys.stderr)
                return False

            with open(main_file, encoding="utf-8") as f:
                content = f.read()

            self.project = parser.parse(content)
            if self.project:
                self.logger.info("Project '%s' loaded successfully", self.project.name)

            # Parse additional include files
            for include_file in files[1:]:
                self.logger.info("Parsing include file %s", include_file)
                if not os.path.exists(include_file):
                    print(f"Warning: Include file '{include_file}' not found", file=sys.stderr)
                    self.warnings += 1
                    continue

                # TODO: Parse and merge include files
                # For now, just acknowledge them
                self.logger.debug("Include file %s acknowledged", include_file)

            return True

        except Exception as e:
            print(f"Error parsing project file: {e}", file=sys.stderr)
            self.errors += 1
            return False

    def schedule(self) -> bool:
        """
        Schedule the project.

        Returns:
            True if scheduling succeeded, False otherwise
        """
        if not self.project:
            return False

        try:
            self.logger.info("Scheduling project")
            result = self.project.schedule()

            if result:
                self.logger.info("Scheduling completed successfully")
            else:
                self.logger.warning("Scheduling completed with issues")
                self.warnings += 1

            return result

        except Exception as e:
            print(f"Error during scheduling: {e}", file=sys.stderr)
            self.errors += 1
            return False

    def check_time_sheet(self, filename: str) -> bool:
        """
        Check a time sheet file.

        Args:
            filename: Path to the time sheet file

        Returns:
            True if check passed, False otherwise
        """
        self.logger.info("Checking time sheet: %s", filename)
        # TODO: Implement time sheet checking
        print(f"Time sheet checking not yet implemented: {filename}")
        return True

    def check_status_sheet(self, filename: str) -> bool:
        """
        Check a status sheet file.

        Args:
            filename: Path to the status sheet file

        Returns:
            True if check passed, False otherwise
        """
        self.logger.info("Checking status sheet: %s", filename)
        # TODO: Implement status sheet checking
        print(f"Status sheet checking not yet implemented: {filename}")
        return True

    def freeze_project(self) -> bool:
        """
        Generate a booking file for the project.

        Returns:
            True if freeze succeeded, False otherwise
        """
        self.logger.info("Generating booking file")
        # TODO: Implement freeze/booking generation
        print("Freeze/booking generation not yet implemented")
        return True

    def list_reports(self, pattern: str) -> None:
        """
        List reports matching the given pattern.

        Args:
            pattern: Regular expression pattern to match report IDs
        """
        if not self.project:
            return

        try:
            regex = re.compile(pattern)
        except re.error as e:
            print(f"Invalid regex pattern: {e}", file=sys.stderr)
            return

        print("\nAvailable Reports:")
        print("-" * 60)

        report_count = 0
        for report in self.project.reports:
            if regex.search(report.fullId):
                formats = report.get("formats") or []
                format_str = ", ".join(str(f) for f in formats) if formats else "none"
                print(f"  {report.fullId}: {report.name} [{format_str}]")
                report_count += 1

        if report_count == 0:
            print("  No reports match the specified pattern")
        else:
            print(f"\nTotal: {report_count} report(s)")

    def generate_reports(self) -> bool:
        """
        Generate project reports.

        Returns:
            True if report generation succeeded, False otherwise
        """
        if not self.project:
            return False

        from scriptplan.report import ReportContext

        try:
            output_dir = self.args.output_dir or "./"
            self.project.outputDir = output_dir

            # Determine which reports to generate
            report_ids = self.args.report_ids or []
            report_patterns = self.args.report_patterns or []

            reports_to_generate = []

            if report_ids or report_patterns:
                # Filter to specific reports
                for report in self.project.reports:
                    # Check exact IDs
                    if report.fullId in report_ids:
                        reports_to_generate.append(report)
                        continue

                    # Check patterns
                    for pattern in report_patterns:
                        try:
                            if re.match(pattern, report.fullId):
                                reports_to_generate.append(report)
                                break
                        except re.error:
                            pass
            else:
                # Generate all reports
                reports_to_generate = list(self.project.reports)

            if not reports_to_generate:
                self.logger.info("No reports to generate")
                return True

            self.logger.info("Generating %d report(s)", len(reports_to_generate))

            for report in reports_to_generate:
                self.logger.info("Generating report: %s", report.fullId)

                # Create report context
                context = ReportContext(self.project, report)
                context.push()

                try:
                    result = report.generate()  # type: ignore[attr-defined]
                    if result != 0:
                        self.warnings += 1
                finally:
                    context.pop()

            self.logger.info("Report generation completed")
            return True

        except Exception as e:
            print(f"Error generating reports: {e}", file=sys.stderr)
            self.errors += 1
            return False


def run_scriptplan(tjp_file: str, output_dir: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Run ScriptPlan report generation on a .tjp file.

    This is a simplified interface for programmatic use.

    Args:
        tjp_file: Path to the .tjp file
        output_dir: Optional output directory for reports (default: current directory)

    Returns:
        Tuple of (success, error_message)
    """
    import contextlib
    import io

    # Capture stderr to get error messages
    stderr_capture = io.StringIO()

    try:
        with contextlib.redirect_stderr(stderr_capture):
            # Create minimal args
            parser = create_parser()
            args_list = [tjp_file]
            if output_dir:
                args_list.extend(["--output-dir", output_dir])
            args = parser.parse_args(args_list)

            # Suppress logging for programmatic use
            logging.getLogger().setLevel(logging.ERROR)

            # Run the application
            app = ScriptPlan(args)
            exit_code = app.run()

            if exit_code == 0:
                return (True, None)
            else:
                error_output = stderr_capture.getvalue()
                return (False, error_output or "Report generation failed")

    except Exception as e:
        error_output = stderr_capture.getvalue()
        return (False, error_output or str(e))


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    debug_modules = args.debug_modules.split(",") if args.debug_modules else None
    setup_logging(args.debug_level, debug_modules)

    # Run the application
    app = ScriptPlan(args)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
