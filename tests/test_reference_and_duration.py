"""Two 0.10.2 fixes that only the hand-run reproductions covered.

A reference that could mean two tasks is refused (issuedb #18), and a
`duration` counts calendar time across nights and weekends (issuedb #20).
0.10.1 bound the first matching task silently, and moved a duration to the
next working hour.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

AMBIGUOUS = """project p "p" 2026-10-19 +1w { }
task test "Test" {
  task beta "B" { duration 1d }
}
task deliveries "D" {
  task beta "B2" { duration 1d }
  task x "X" { depends beta duration 1d }
}
"""

# 2026-10-23 is a Friday and 2026-10-25 a Sunday.
ACROSS_THE_WEEKEND = """project p "p" 2026-10-19 +3w {
  timingresolution 60min
}
resource r0 "R0" { workinghours mon - fri 9:00 - 17:00 }
task a "A" { effort 8h allocate r0 start 2026-10-23-09:00 }
task d "D" { depends a duration 2h }
task z "Z" { scheduling alap duration 2h end 2026-10-25-15:00 }
taskreport out "out" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }
"""


def plan(tmp_path: Path, text: str) -> tuple[int, str]:
    path = tmp_path / "plan.tjp"
    path.write_text(text)
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    done = subprocess.run(
        [sys.executable, "-m", "scriptplan.cli.plan", "report", "--csv", str(path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
        timeout=300,
    )
    return done.returncode, done.stdout + done.stderr


def test_a_reference_that_could_mean_two_tasks_is_refused(tmp_path: Path) -> None:
    code, output = plan(tmp_path, AMBIGUOUS)
    assert code != 0, output
    assert "task 'deliveries.x' refers to 'beta'" in output
    assert "deliveries.beta, test.beta" in output


def test_a_duration_runs_through_non_working_time(tmp_path: Path) -> None:
    code, output = plan(tmp_path, ACROSS_THE_WEEKEND)
    assert code == 0, output
    assert "a,2026-10-23-09:00,2026-10-23-17:00" in output
    # Friday 17:00 to 19:00, not Monday 09:00 to 11:00.
    assert "d,2026-10-23-17:00,2026-10-23-19:00" in output
    # Two hours ending on Sunday, not 48 hours back to Friday's working time.
    assert "z,2026-10-25-13:00,2026-10-25-15:00" in output
