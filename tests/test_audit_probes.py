"""Run the audit probe harness as part of the test suite.

audit/evaluations holds one probe per claim in SPECS/, each driving ScriptPlan
through its own API or CLI. Running them here means a change that breaks a
stated guarantee fails the ordinary test run, rather than waiting for someone
to remember the harness exists.

The probes are also runnable on their own, against an installed wheel or a
release candidate, with audit/evaluations/run_all.sh.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_DIR = REPO_ROOT / "audit" / "evaluations"


def probe_files() -> list[str]:
    """Every probe file except the slow performance one."""
    return sorted(
        path.name
        for path in PROBE_DIR.glob("probe_*.py")
        if path.name != "probe_scale.py"
    )


@pytest.mark.parametrize("probe_file", probe_files())
def test_probe_file_reports_no_failures(probe_file: str) -> None:
    """Every claim the probe file covers still holds."""
    completed = subprocess.run(
        [sys.executable, str(PROBE_DIR / probe_file)],
        capture_output=True,
        text=True,
        cwd=str(PROBE_DIR),
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": f"{REPO_ROOT}{':'}{PROBE_DIR}",
            "HOME": str(Path.home()),
        },
        timeout=600,
    )
    if completed.returncode != 0:
        failures = [
            line
            for line in completed.stdout.splitlines()
            if line.startswith("[FAIL]") or line.startswith("[ERROR]")
        ]
        detail = "\n".join(failures) or completed.stdout[-2000:]
        pytest.fail(
            f"{probe_file} reported failures:\n{detail}\n"
            f"stderr:\n{completed.stderr[-1000:]}"
        )


def test_every_spec_has_a_probe_file() -> None:
    """The harness covers each area the specs describe."""
    expected = {
        "probe_error_propagation.py",
        "probe_parser_strictness.py",
        "probe_units.py",
        "probe_calendar.py",
        "probe_precision.py",
        "probe_limits.py",
        "probe_effort_semantics.py",
        "probe_alap.py",
        "probe_idempotency.py",
        "probe_priority.py",
        "probe_reports.py",
    }
    missing = expected - set(probe_files())
    assert not missing, f"probe files disappeared: {sorted(missing)}"
