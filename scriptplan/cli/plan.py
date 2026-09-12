"""
Enterprise-grade CLI for ScriptPlan project planning and reporting.

This module provides the 'plan' command-line interface for generating
reports from TaskJuggler (.tjp) project files.
"""

import hashlib
import json
import logging
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from scriptplan import __version__
from scriptplan.cli.main import run_scriptplan
from scriptplan.cli.plan_files import (
    InputFileError,
    create_auto_report_file,
    declares_report,
    setup_logging,
    validate_tjp_file,
)
from scriptplan.cli.plan_help import register as register_help_commands

# Configure logging
logger = logging.getLogger(__name__)


class PlanError(Exception):
    """Base exception for plan CLI errors."""

    pass


class FileNotFoundError(PlanError):
    """Raised when input file is not found."""

    pass


class ReportGenerationError(PlanError):
    """Raised when report generation fails."""

    pass


@click.group(invoke_without_command=True)
@click.option("-v", "--version", is_flag=True, help="Show version and exit.")
@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
@click.pass_context
def cli(ctx: click.Context, version: bool, verbose: bool, quiet: bool) -> None:
    """
    ScriptPlan - Enterprise project planning and scheduling tool.

    ScriptPlan is a modern implementation of TaskJuggler's project planning
    capabilities, providing powerful scheduling, resource management, and
    reporting features for complex projects.

    \b
    Examples:
        # Generate JSON report
        plan report project.tjp

        # Generate CSV report
        plan report --csv project.tjp

        # Verbose output
        plan --verbose report project.tjp

    For more information, use 'plan COMMAND --help' for detailed command help.
    """
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    setup_logging(verbose=verbose, quiet=quiet)

    if version:
        click.echo(f"ScriptPlan version {__version__}")
        ctx.exit(0)

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@cli.command()
@click.argument("tjp_file", type=click.Path(exists=False), metavar="<tjp-file>", required=False)
@click.option("--csv", "output_csv", is_flag=True, help="Generate CSV output instead of JSON.")
@click.option("-o", "--output", type=click.Path(), help="Output file path (default: stdout).")
@click.option("--force", is_flag=True, help="Overwrite existing output files.")
@click.pass_context
def report(ctx: click.Context, tjp_file: Optional[str], output_csv: bool, output: Optional[str], force: bool) -> None:
    """
    Generate reports from TaskJuggler project files.

    Processes a .tjp project file and generates scheduling reports in
    JSON or CSV format. Output goes to stdout by default (Unix style),
    messages go to stderr.

    \b
    The TJP_FILE argument specifies the path to your TaskJuggler project file,
    or '-' to read from stdin. If omitted, reads from stdin.

    \b
    Output Formats:
        JSON (default): Structured data with columns and records
        CSV: Comma-separated values for spreadsheet applications

    \b
    Examples:
        # Output to stdout, save to file
        plan report project.tjp > output.json

        # Generate CSV report
        plan report --csv project.tjp > output.csv

        # Read from stdin
        cat project.tjp | plan report > output.json
        plan report - < project.tjp > output.json

        # Pipe to other tools
        plan report project.tjp | jq '.data[0]'
        plan report --csv project.tjp | csvkit

        # Save to specific file (alternative)
        plan report --output results.json project.tjp

    Exit Codes:
        0: Success
        1: File not found or invalid
        2: Report generation failed
        3: Output file exists (use --force to overwrite)
    """
    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)

    temp_file: Optional[Path] = None
    auto_report_id = ""
    stdin_temp_file: Optional[Path] = None
    temp_output_dir: Optional[Path] = None

    try:
        # Check if reading from stdin
        if not tjp_file or tjp_file == "-":
            # Read from stdin
            if verbose:
                logger.debug("Reading .tjp content from stdin")

            stdin_content = sys.stdin.read()

            if not stdin_content.strip():
                raise FileNotFoundError("No input provided on stdin")

            # Create temporary file from stdin content (safe for concurrent execution)
            temp_fd, temp_path = tempfile.mkstemp(suffix=".tjp", prefix="plan_stdin_")
            stdin_temp_file = Path(temp_path)

            # Write content and close file descriptor
            with os.fdopen(temp_fd, "w") as f:
                f.write(stdin_content)

            tjp_path = stdin_temp_file

            if verbose:
                logger.debug("Created temporary file from stdin: %s", stdin_temp_file)

        else:
            # Validate input file
            if verbose:
                logger.debug("Validating input file: %s", tjp_file)

            tjp_path = validate_tjp_file(tjp_file)

        if not quiet:
            click.echo(f"Processing: {tjp_path.name}", err=True)

        if verbose:
            with open(tjp_path, "rb") as handle:
                logger.debug("Input file SHA256: %s", hashlib.sha256(handle.read()).hexdigest())

        # Determine output format
        output_format = "csv" if output_csv else "json"

        # Create temp directory for report output
        temp_output_dir = Path(tempfile.mkdtemp(prefix="plan_output_"))

        if verbose:
            logger.debug("Created temp output directory: %s", temp_output_dir)

        # Only supply a report when the project does not define one, so the user
        # sees the report they wrote, with the columns they asked for.
        if declares_report(tjp_path, output_format):
            if verbose:
                logger.debug("Using the %s report(s) declared in the project", output_format)
            temp_file, auto_report_id = None, ""
            source_for_run = tjp_path
        else:
            if verbose:
                logger.debug("Project declares no %s report; adding a default one", output_format)
            temp_file, auto_report_id = create_auto_report_file(tjp_path, output_format)
            source_for_run = temp_file

        if verbose:
            logger.debug("Temporary file: %s", temp_file)
            logger.debug("Auto-report ID: %s", auto_report_id)

        # Run scriptplan to generate reports in temp directory
        if verbose:
            logger.debug("Running ScriptPlan report generator")

        success, error_msg = run_scriptplan(str(source_for_run), str(temp_output_dir))

        if not success:
            raise ReportGenerationError(error_msg or "Report generation failed")

        # Find ALL generated files in temp directory
        if output_format == "json":
            output_files = list(temp_output_dir.glob("*.json"))
        else:
            output_files = list(temp_output_dir.glob("*.csv"))

        if verbose:
            logger.debug("Found %d output files: %s", len(output_files), [f.name for f in output_files])

        if not output_files:
            raise ReportGenerationError(
                "Report generation completed but no output files found. "
                "This may indicate a scheduling issue with your project."
            )

        # Pick deterministically: glob order is filesystem order, so sort by
        # name to make repeated runs of the same input byte-identical.
        output_files.sort(key=lambda path: path.name)
        primary_output = output_files[0]
        if len(output_files) > 1 and not quiet:
            click.echo(
                f"Note: the project defines {len(output_files)} {output_format} reports; "
                f"showing '{primary_output.stem}'. Use --output to write them individually.",
                err=True,
            )

        if verbose:
            logger.debug("Reading report from: %s", primary_output)

        # Read the file content
        with open(primary_output) as f:
            report_content = f.read()

        # Stamp report_id with a SHA256 over the rendered result, so that the
        # id identifies the schedule the user is looking at. Hashing the input
        # file instead would give a correct and a broken schedule the same id.
        if output_format == "json":
            try:
                report_data = json.loads(report_content)
                report_data.pop("report_id", None)
                canonical = json.dumps(report_data, sort_keys=True, separators=(",", ":"))
                report_data["report_id"] = hashlib.sha256(canonical.encode()).hexdigest()
                report_content = json.dumps(report_data, indent=2)
                if verbose:
                    logger.debug("report_id (SHA256 of result): %s", report_data["report_id"])
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON for report_id computation")

        # Handle output
        if output:
            # User specified output path
            output_path = Path(output)

            if output_path.exists() and not force:
                raise ReportGenerationError(f"Output file already exists: {output_path}\nUse --force to overwrite.")

            # Write to specified file
            with open(output_path, "w") as f:
                f.write(report_content)

            if not quiet:
                click.echo(f"Generated: {output_path}", err=True)

            if verbose:
                logger.debug("Wrote report to: %s", output_path)
        else:
            # Output to stdout (Unix way)
            click.echo(report_content)

        # Clean up temp output directory (contains all generated files)
        if temp_output_dir and temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)
            if verbose:
                logger.debug("Cleaned up temp output directory: %s", temp_output_dir)

        # Success message to stderr
        if not quiet:
            click.secho("✓ Report generation completed successfully", fg="green", err=True)

        # Cleanup temp files
        if temp_file and temp_file.exists():
            temp_file.unlink()
            if verbose:
                logger.debug("Cleaned up temporary file: %s", temp_file)

        if stdin_temp_file and stdin_temp_file.exists():
            stdin_temp_file.unlink()
            if verbose:
                logger.debug("Cleaned up stdin temporary file: %s", stdin_temp_file)

        sys.exit(0)

    except (FileNotFoundError, InputFileError) as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        if verbose:
            logger.exception("File validation failed")

        # Cleanup temp files and directories
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if stdin_temp_file and stdin_temp_file.exists():
            stdin_temp_file.unlink()
        if temp_output_dir and temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)

        sys.exit(1)

    except ReportGenerationError as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        if verbose:
            logger.exception("Report generation failed")

        # Cleanup temp files and directories
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if stdin_temp_file and stdin_temp_file.exists():
            stdin_temp_file.unlink()
        if temp_output_dir and temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)

        sys.exit(2)

    except Exception as e:
        click.secho(f"Unexpected error: {e}", fg="red", err=True)
        if verbose:
            logger.exception("Unexpected error occurred")

        # Cleanup temp files and directories
        if temp_file and temp_file.exists():
            temp_file.unlink()
        if stdin_temp_file and stdin_temp_file.exists():
            stdin_temp_file.unlink()
        if temp_output_dir and temp_output_dir.exists():
            shutil.rmtree(temp_output_dir)

        sys.exit(2)


register_help_commands(cli)


def main() -> None:
    """Entry point for the plan CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.secho("\nInterrupted by user", fg="yellow", err=True)
        sys.exit(130)
    except Exception as e:
        click.secho(f"Fatal error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
