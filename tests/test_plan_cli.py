"""The `plan` CLI, exercised the way a user runs it.

This CLI produced every result in SHOWCASE.md and had no test file at all;
tests/test_cli.py covers the other entry point, `scriptplan`. Each test here
runs a real sub-process, because that is what a user does, and because an
import-time or command-registration mistake is invisible to an in-process call.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SIMPLE_PROJECT = """project p "P" 2025-01-06 +3m {
  timezone "Etc/UTC"
  now 2025-01-06
}
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "Alpha" { start 2025-01-06 effort 8h allocate r }
"""


def run_plan(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", *args],
        capture_output=True,
        text=True,
        input=stdin,
        cwd=str(REPO_ROOT),
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO_ROOT), "HOME": str(Path.home())},
        timeout=300,
    )


@pytest.fixture
def project_file(tmp_path: Path) -> Path:
    path = tmp_path / "project.tjp"
    path.write_text(SIMPLE_PROJECT)
    return path


@pytest.mark.parametrize("args", [("--version",), ("help",), ("--help",), ("report", "--help")])
def test_informational_commands_succeed(args: tuple[str, ...]) -> None:
    """Every command a user reaches for before running anything must work."""
    done = run_plan(*args)
    assert done.returncode == 0, f"plan {' '.join(args)} failed:\n{done.stderr}"
    assert done.stdout.strip(), f"plan {' '.join(args)} printed nothing"


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_shell_completion_is_offered_for_each_shell(shell: str) -> None:
    done = run_plan("shell-completion", shell)
    assert done.returncode == 0, done.stderr
    assert shell in done.stdout


def test_report_writes_json_to_stdout(project_file: Path) -> None:
    done = run_plan("report", str(project_file))
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["columns"], "the report named no columns"
    assert payload["data"], "the report produced no rows"
    assert payload["report_id"], "the report carried no id"


def test_report_writes_csv_when_asked(project_file: Path) -> None:
    done = run_plan("report", "--csv", str(project_file))
    assert done.returncode == 0, done.stderr
    first_line = done.stdout.splitlines()[0]
    assert "," in first_line, f"expected CSV, got {first_line!r}"


def test_report_reads_a_project_from_stdin(project_file: Path) -> None:
    done = run_plan("report", "-", stdin=SIMPLE_PROJECT)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]


def test_the_same_project_yields_the_same_report_id(project_file: Path) -> None:
    """The id identifies the schedule, so it must not move between runs."""
    first = json.loads(run_plan("report", str(project_file)).stdout)["report_id"]
    second = json.loads(run_plan("report", str(project_file)).stdout)["report_id"]
    assert first == second


def test_a_different_schedule_yields_a_different_report_id(tmp_path: Path) -> None:
    """Hashing the input file gave a correct and a broken schedule one id."""
    first_file = tmp_path / "one.tjp"
    first_file.write_text(SIMPLE_PROJECT)
    second_file = tmp_path / "two.tjp"
    second_file.write_text(SIMPLE_PROJECT.replace("effort 8h", "effort 16h"))

    first = json.loads(run_plan("report", str(first_file)).stdout)["report_id"]
    second = json.loads(run_plan("report", str(second_file)).stdout)["report_id"]
    assert first != second


def test_a_missing_file_exits_non_zero(tmp_path: Path) -> None:
    done = run_plan("report", str(tmp_path / "nothing.tjp"))
    assert done.returncode != 0
    assert "not found" in done.stderr.lower()


def test_an_unschedulable_project_exits_non_zero(tmp_path: Path) -> None:
    path = tmp_path / "cycle.tjp"
    path.write_text(SIMPLE_PROJECT + """
task b "Bravo" { depends !c effort 1h allocate r }
task c "Charlie" { depends !b effort 1h allocate r }
""")
    done = run_plan("report", str(path))
    assert done.returncode != 0, "a circular dependency must not report success"
    assert "circular" in done.stderr.lower() or "cycle" in done.stderr.lower()


def test_output_goes_to_a_file_when_asked(project_file: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    done = run_plan("report", "--output", str(target), str(project_file))
    assert done.returncode == 0, done.stderr
    assert json.loads(target.read_text())["data"]


def test_an_existing_output_file_is_not_overwritten_without_force(
    project_file: Path, tmp_path: Path
) -> None:
    target = tmp_path / "out.json"
    target.write_text("keep me")
    done = run_plan("report", "--output", str(target), str(project_file))
    assert done.returncode != 0
    assert target.read_text() == "keep me"

    forced = run_plan("report", "--force", "--output", str(target), str(project_file))
    assert forced.returncode == 0, forced.stderr
    assert target.read_text() != "keep me"
