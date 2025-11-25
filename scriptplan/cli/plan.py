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


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Configure logging for the CLI.

    Args:
        verbose: Enable verbose/debug logging
        quiet: Suppress all non-error output
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", stream=sys.stderr)


def validate_tjp_file(tjp_path: str) -> Path:
    """
    Validate that the .tjp file exists and is readable.

    Args:
        tjp_path: Path to the .tjp file

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: If file doesn't exist or isn't readable
    """
    path = Path(tjp_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {tjp_path}")

    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {tjp_path}")

    if path.suffix != ".tjp":
        logger.warning("File does not have .tjp extension: %s", tjp_path)

    if not path.stat().st_size:
        raise FileNotFoundError(f"File is empty: {tjp_path}")

    return path


def create_auto_report_file(tjp_path: Path, output_format: str) -> tuple[Path, str]:
    """
    Create a temporary .tjp file with auto-generated report.

    If the original file doesn't have a report matching the requested format,
    this creates a temporary file that includes the original and adds a default report.

    Args:
        tjp_path: Path to the original .tjp file
        output_format: Desired output format ('json' or 'csv')

    Returns:
        Tuple of (Path to temp .tjp file, report_id)
    """
    # Create a unique report ID using secure random string (safe for concurrent execution)
    random_suffix = secrets.token_hex(8)
    report_id = f"plan_auto_{random_suffix}"

    # Default report definition
    auto_report = f"""
# Auto-generated report by plan CLI
taskreport {report_id} "{report_id}" {{
    formats {output_format}
    columns id, start, end
    timeformat "%Y-%m-%d-%H:%M"
}}
"""

    # Create temporary file with random suffix (safe for concurrent execution)
    temp_fd, temp_path = tempfile.mkstemp(suffix=".tjp", prefix="plan_auto_")
    temp_file = Path(temp_path)

    # Read original file
    with open(tjp_path) as f:
        original_content = f.read()

    # Write combined content and close file descriptor
    with os.fdopen(temp_fd, "w") as f:
        # Include original file
        f.write(f"# Original file: {tjp_path}\n")
        f.write("# Auto-report added by plan CLI\n\n")
        f.write(original_content)
        f.write("\n\n")
        f.write(auto_report)

    return temp_file, report_id


def find_output_files(tjp_path: Path, output_format: str, report_id: str = "") -> list[Path]:
    """
    Find generated output files for a .tjp file.

    Args:
        tjp_path: Path to the .tjp file
        output_format: Expected output format ('json' or 'csv')
        report_id: Specific report ID to look for

    Returns:
        List of generated output files
    """
    cwd = Path.cwd()

    if report_id:
        # Look for specific report ID
        if output_format == "json":
            return list(cwd.glob(f"{report_id}.json"))
        else:
            return list(cwd.glob(f"*{report_id}*.csv"))
    else:
        # Look for any files matching the base name
        base_name = tjp_path.stem
        if output_format == "json":
            return list(cwd.glob(f"*{base_name}*.json"))
        else:
            return list(cwd.glob(f"*{base_name}*.csv"))


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

        # Calculate SHA256 hash of the input file for report_id
        with open(tjp_path, "rb") as f:  # type: ignore[assignment]
            file_hash = hashlib.sha256(f.read()).hexdigest()  # type: ignore[arg-type]

        if verbose:
            logger.debug("Input file SHA256: %s", file_hash)

        # Determine output format
        output_format = "csv" if output_csv else "json"

        # Create temp directory for report output
        temp_output_dir = Path(tempfile.mkdtemp(prefix="plan_output_"))

        if verbose:
            logger.debug("Created temp output directory: %s", temp_output_dir)

        # Create auto-report file (always, to ensure output in requested format)
        if verbose:
            logger.debug("Creating auto-report for %s format", output_format)

        temp_file, auto_report_id = create_auto_report_file(tjp_path, output_format)

        if verbose:
            logger.debug("Temporary file: %s", temp_file)
            logger.debug("Auto-report ID: %s", auto_report_id)

        # Run scriptplan to generate reports in temp directory
        if verbose:
            logger.debug("Running ScriptPlan report generator")

        success, error_msg = run_scriptplan(str(temp_file), str(temp_output_dir))

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

        # Get the primary output file (first one)
        primary_output = output_files[0]

        if verbose:
            logger.debug("Reading report from: %s", primary_output)

        # Read the file content
        with open(primary_output) as f:
            report_content = f.read()

        # Replace report_id with SHA256 hash for JSON output
        if output_format == "json":
            try:
                report_data = json.loads(report_content)
                # Replace report_id with file hash
                report_data["report_id"] = file_hash
                report_content = json.dumps(report_data, indent=2)
                if verbose:
                    logger.debug("Replaced report_id with SHA256 hash: %s", file_hash)
            except json.JSONDecodeError:
                # If JSON parsing fails, keep original content
                logger.warning("Failed to parse JSON for report_id replacement")

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

    except FileNotFoundError as e:
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


@cli.command()
def help() -> None:
    """
    Show detailed help and usage information.

    Displays comprehensive help including all available commands,
    common usage patterns, and examples.
    """
    help_text = (
        """
ScriptPlan - Enterprise Project Planning Tool

DESCRIPTION:
    ScriptPlan is a modern, Python-based implementation of TaskJuggler's
    project planning capabilities. It provides powerful scheduling, resource
    management, and reporting features for managing complex projects.

USAGE:
    plan [OPTIONS] COMMAND [ARGS]...

COMMANDS:
    report      Generate reports from .tjp project files
    help        Show this detailed help message

GLOBAL OPTIONS:
    -v, --version       Show version information
    --verbose           Enable verbose/debug output
    --quiet             Suppress non-error messages
    -h, --help          Show command help

REPORT COMMAND:
    plan report [OPTIONS] <tjp-file>

    Generate scheduling reports in JSON or CSV format from TaskJuggler
    project files (.tjp).

    Options:
        --csv               Generate CSV output (default: JSON)
        -o, --output PATH   Specify output file path
        --force             Overwrite existing output files
        -h, --help          Show report command help

EXAMPLES:
    # Generate JSON report from project file
    $ plan report project.tjp

    # Generate CSV report
    $ plan report --csv project.tjp

    # Save report to specific file
    $ plan report --output report.json project.tjp

    # Enable verbose output for debugging
    $ plan --verbose report project.tjp

    # Quiet mode (only show errors)
    $ plan --quiet report project.tjp

OUTPUT FORMATS:
    JSON:
        Clean, structured data with no HTML metadata.
        Format: {"data": [...], "columns": [...], "report_id": "..."}

    CSV:
        Comma-separated values suitable for spreadsheet applications.
        First row contains column headers.

EXIT CODES:
    0   Success
    1   File not found or invalid input
    2   Report generation failed
    3   Output file exists (use --force)

ENVIRONMENT:
    PLAN_VERBOSE        Set to '1' to enable verbose output
    PLAN_OUTPUT_DIR     Default directory for output files

TJP FILE REQUIREMENTS:
    Your .tjp file must contain at least one report definition:

    taskreport my_report "My Report" {
        formats json      # or csv
        columns id, start, end
    }

MORE INFORMATION:
    Documentation: https://github.com/rodmena-limited/scriptplan
    Issues: https://github.com/rodmena-limited/scriptplan/issues

VERSION:
    ScriptPlan """
        + __version__
        + """
"""
    )
    click.echo(help_text)


@cli.command(name="shell-completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def shell_completion(shell: str) -> None:
    """
    Generate shell completion script.

    Outputs shell completion configuration for the specified shell.
    Add the output to your shell's configuration file to enable
    tab completion for the 'plan' command.

    \b
    Supported shells: bash, zsh, fish

    \b
    Examples:
        # Bash
        plan shell-completion bash >> ~/.bashrc

        # Zsh
        plan shell-completion zsh >> ~/.zshrc

        # Fish
        plan shell-completion fish > ~/.config/fish/completions/plan.fish
    """
    if shell == "bash":
        completion = """
# plan bash completion
_plan_completion() {
    local IFS=$'\\n'
    COMPREPLY=( $(env COMP_WORDS="${COMP_WORDS[*]}" \\
                     COMP_CWORD=$COMP_CWORD \\
                     _PLAN_COMPLETE=complete $1) )
    return 0
}

complete -F _plan_completion -o default plan
"""
    elif shell == "zsh":
        completion = """
# plan zsh completion
#compdef plan

_plan() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    response=("${(@f)$( env COMP_WORDS="${words[*]}" \\
                        COMP_CWORD=$((CURRENT-1)) \\
                        _PLAN_COMPLETE="complete_zsh" \\
                        plan )}")

    for key descr in ${(kv)response}; do
      if [[ "$descr" == "_" ]]; then
          completions+=("$key")
      else
          completions_with_descriptions+=("$key":"$descr")
      fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
    compstate[insert]="automenu"
}

compdef _plan plan
"""
    else:  # fish
        completion = """
# plan fish completion
complete -c plan -f -a "(env _PLAN_COMPLETE=complete_fish COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) plan)"
"""

    click.echo(completion)


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
