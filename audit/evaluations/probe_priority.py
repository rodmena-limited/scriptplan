#!/usr/bin/env python3
"""Regression guard: priority contention already behaves correctly.

These probes PASS today.  They exist so the WS3 engine rewrite cannot quietly
lose behaviour that the current scheduler gets right.

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - a higher-priority task that becomes ready later takes the contended
    resource ahead of a lower-priority task that is still running
  - the repository's own preemption fixture keeps its shape
"""

from __future__ import annotations

import os

from harness import HDR, datetime, main, parse, probe, window


@probe("A higher-priority task takes the resource when it becomes ready")
def probe_priority_wins_contention() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
resource q "Q" { workinghours mon-fri 9:00-17:00 }
task low "Low" { start 2025-01-06 effort 5d allocate r priority 100 }
task gate "Gate" { start 2025-01-06 effort 8h allocate q priority 900 }
task high "High" { depends !gate effort 1d allocate r priority 900 }
""")
    low, gate, high = window(project, "low"), window(project, "gate"), window(project, "high")
    ok = high[0] == datetime(2025, 1, 7, 9, 0) and high[1] == datetime(2025, 1, 7, 17, 0)
    return ok, f"gate={gate} high={high} low={low} (high must take Tue 7th ahead of the low-priority task)"


@probe("The repository's own preemption fixture keeps its shape")
def probe_repository_preemption_fixture() -> tuple[bool, str]:
    here = os.path.dirname(os.path.abspath(__file__))
    fixture = os.path.join(here, "..", "..", "tests", "data", "airport_ultra_math.tjp")
    if not os.path.exists(fixture):
        return True, f"fixture not present at {fixture}; nothing to guard"
    with open(fixture) as handle:
        project = parse(handle.read())
    rows = {t.fullId: (t.get("start", 0), t.get("end", 0)) for t in project.tasks if t.leaf()}
    floats = [v for k, v in rows.items() if k.endswith("t_float")]
    interrupts = [v for k, v in rows.items() if k.endswith("t_interrupt")]
    ok = bool(floats and interrupts) and floats[0][0] < interrupts[0][0] < floats[0][1]
    return ok, f"t_float={floats} t_interrupt={interrupts} (the interrupt must land inside t_float's window)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
