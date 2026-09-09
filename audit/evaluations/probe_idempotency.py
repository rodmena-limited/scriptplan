#!/usr/bin/env python3
"""Falsifies: "scheduling the same project twice gives the same answer".

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - Project.schedule() twice produces identical dates and identical bookings
  - parsing the same text twice in one process produces identical schedules
    (no process-global state leaking between projects)
"""

from __future__ import annotations

from harness import HDR, booked_slots, main, parse, probe, window

PROJECT = HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 2d allocate r }
task b "B" { depends !a effort 1d allocate r }
"""


def _snapshot(project) -> tuple:
    return (
        window(project, "a"),
        window(project, "b"),
        tuple(sorted(i for i, _ in booked_slots(project, "r"))),
    )


@probe("Calling schedule() a second time leaves dates and bookings unchanged")
def probe_schedule_is_idempotent() -> tuple[bool, str]:
    project = parse(PROJECT)
    before = _snapshot(project)
    project.schedule()
    after = _snapshot(project)
    return before == after, (
        f"before: dates={before[0]} {before[1]} slots={len(before[2])}\n"
        f"after:  dates={after[0]} {after[1]} slots={len(after[2])}"
    )


@probe("Scheduling a third time still leaves the result unchanged")
def probe_schedule_is_stable_under_repetition() -> tuple[bool, str]:
    project = parse(PROJECT)
    first = _snapshot(project)
    project.schedule()
    project.schedule()
    third = _snapshot(project)
    return first == third, f"first={first[:2]} slots={len(first[2])}; third={third[:2]} slots={len(third[2])}"


@probe("Parsing another project in between does not change this project's schedule")
def probe_no_cross_project_leakage() -> tuple[bool, str]:
    alone = _snapshot(parse(PROJECT))
    parse("""project other "Other" 2025-01-06 +1m { timezone "Asia/Tokyo" now 2025-01-06 }
resource r "R" { timezone "Asia/Tokyo" workinghours mon-fri 9:00-17:00 }
task a "A" { effort 2d allocate r }
""")
    again = _snapshot(parse(PROJECT))
    return alone == again, f"alone={alone[:2]} slots={len(alone[2])}\n  after another project={again[:2]} slots={len(again[2])}"


@probe("Attribute provenance mode does not leak out of scheduling")
def probe_attribute_mode_restored() -> tuple[bool, str]:
    from scriptplan.core.property import AttributeBase

    parse(PROJECT)
    mode = AttributeBase.mode()
    return mode == 0, f"AttributeBase.mode() after scheduling = {mode} (expected 0, the 'provided' mode)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
