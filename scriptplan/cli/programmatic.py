"""Running the report generator from Python, as `plan report` does."""

from __future__ import annotations

import logging
import sys

__all__ = ["run_scriptplan"]


def run_scriptplan(tjp_file: str, output_dir: str | None = None) -> tuple[bool, str | None]:
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
            from scriptplan.cli.main import ScriptPlan, create_parser

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

            if exit_code != 0:
                error_output = stderr_capture.getvalue()
                return (False, error_output or "Report generation failed")

    except Exception as e:
        error_output = stderr_capture.getvalue()
        return (False, error_output or str(e))

    # A schedule that succeeded with warnings still has to show them: a
    # warning nobody sees is a silent change to what the file asked for.
    said = stderr_capture.getvalue()
    if said:
        sys.stderr.write(said if said.endswith("\n") else said + "\n")
    return (True, None)
