"""Finding, validating and preparing the files `plan report` works on.

A project that declares its own reports gets those rendered. One that declares
none gets a default report added to a temporary copy, so that `plan report`
always has something to show without editing the user's file.
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class InputFileError(Exception):
    """The input file is missing, unreadable or empty."""


__all__ = [
    "REPORT_KEYWORDS",
    "InputFileError",
    "create_auto_report_file",
    "declares_report",
    "find_output_files",
    "setup_logging",
    "validate_tjp_file",
]


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
        InputFileError: If the file does not exist or cannot be read
    """
    path = Path(tjp_path)

    if not path.exists():
        raise InputFileError(f"File not found: {tjp_path}")

    if not path.is_file():
        raise InputFileError(f"Not a file: {tjp_path}")

    if path.suffix != ".tjp":
        logger.warning("File does not have .tjp extension: %s", tjp_path)

    if not path.stat().st_size:
        raise InputFileError(f"File is empty: {tjp_path}")

    return path


REPORT_KEYWORDS = ("taskreport", "resourcereport", "textreport", "accountreport")


def declares_report(tjp_path: Path, output_format: str) -> bool:
    """True if the file already defines a report producing ``output_format``.

    The CLI only supplies a report of its own when the project does not define
    one, so that `plan report` shows the user the report they wrote rather than
    a substitute with different columns.
    """
    try:
        with open(tjp_path) as handle:
            text = handle.read()
    except OSError:
        return False

    # Strip comments so a commented-out report is not mistaken for a real one.
    lines = []
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0]
        lines.append(stripped)
    body = "\n".join(lines)

    depth_of_report = None
    depth = 0
    for token_line in body.splitlines():
        opens_report = any(keyword in token_line for keyword in REPORT_KEYWORDS)
        if opens_report and depth_of_report is None:
            depth_of_report = depth
        if depth_of_report is not None and "formats" in token_line:
            formats = token_line.split("formats", 1)[1]
            if output_format in formats:
                return True
        depth += token_line.count("{") - token_line.count("}")
        if depth_of_report is not None and depth <= depth_of_report:
            depth_of_report = None
    return False


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
