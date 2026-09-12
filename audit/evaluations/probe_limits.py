#!/usr/bin/env python3
"""Falsifies: "every quota blocks when exceeded AND releases when it should".

Claims under test (SPECS/003-ws1-units-and-calendar-arithmetic.md):
  - dailymax / weeklymax / monthlymax block at the cap and resume next period
  - maximum caps the whole interval
  - the grammar accepts every limit kind the engine implements

Each probe tests BOTH directions: a cap that only ever blocks is how a queue
deadlocks forever.
"""

from __future__ import annotations

from collections import defaultdict

from harness import HDR, booked_hours_by_day, main, parse, probe, window

LIMIT_KINDS = [
    "dailymax 4h",
    "dailymin 1h",
    "weeklymax 8h",
    "weeklymin 2h",
    "monthlymax 40h",
    "monthlymin 8h",
    "maximum 40h",
    "minimum 2h",
]


@probe("dailymax blocks at the cap and resumes the next day")
def probe_dailymax_blocks_and_releases() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 limits { dailymax 4h } }
task a "A" { start 2025-01-06 effort 12h allocate r }
""")
    per_day = booked_hours_by_day(project, "r")
    days = sorted(per_day)
    blocks = all(per_day[d] <= 4 + 1e-9 for d in days)
    releases = len(days) == 3 and all(abs(per_day[d] - 4.0) < 1e-9 for d in days)
    return blocks and releases, (
        f"hours per day = {per_day}; blocked at 4h/day = {blocks}; "
        f"resumed over 3 days = {releases}; task {window(project, 'a')}"
    )


@probe("weeklymax blocks at the cap and resumes the next ISO week")
def probe_weeklymax_blocks_and_releases() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 limits { weeklymax 8h } }
task a "A" { start 2025-01-08 effort 24h allocate r }
""")
    per_week: dict[tuple[int, int], float] = defaultdict(float)
    for day, hours in booked_hours_by_day(project, "r").items():
        year, week, _ = day.isocalendar()
        per_week[(year, week)] += hours
    blocks = all(hours <= 8 + 1e-9 for hours in per_week.values())
    releases = len(per_week) == 3
    return blocks and releases, f"hours per ISO week = {dict(per_week)} (8h cap, must span 3 weeks)"


@probe("weeklymax resumes correctly across a year boundary")
def probe_weeklymax_year_boundary() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-12-22 +6w { timezone "Etc/UTC" now 2025-12-22 }
resource r "R" { workinghours mon-fri 9:00-17:00 limits { weeklymax 8h } }
task a "A" { start 2025-12-22 effort 32h allocate r }
""")
    per_week: dict[tuple[int, int], float] = defaultdict(float)
    for day, hours in booked_hours_by_day(project, "r").items():
        year, week, _ = day.isocalendar()
        per_week[(year, week)] += hours
    ok = len(per_week) == 4 and all(abs(hours - 8) < 1e-9 for hours in per_week.values())
    return ok, f"hours per ISO week = {dict(per_week)} (must be 8h in each of 4 weeks across 2025->2026)"


@probe("monthlymax blocks at the cap and resumes the next calendar month")
def probe_monthlymax_blocks_and_releases() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-01-06 +4m { timezone "Etc/UTC" now 2025-01-06 }
resource r "R" { workinghours mon-fri 9:00-17:00 limits { monthlymax 8h } }
task a "A" { start 2025-01-06 effort 24h allocate r }
""")
    per_month: dict[tuple[int, int], float] = defaultdict(float)
    for day, hours in booked_hours_by_day(project, "r").items():
        per_month[(day.year, day.month)] += hours
    blocks = all(hours <= 8 + 1e-9 for hours in per_month.values())
    releases = len(per_month) == 3
    return blocks and releases, f"hours per calendar month = {dict(per_month)} (8h cap, must span 3 months)"


@probe("maximum caps the whole interval")
def probe_maximum_caps_interval() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 limits { maximum 6h } }
task a "A" { start 2025-01-06 effort 24h allocate r }
""", schedule=False)
    result = project.schedule()
    total = sum(booked_hours_by_day(project, "r").values())
    return abs(total - 6.0) < 1e-9, f"total booked = {total}h (cap 6h over the whole interval); schedule()={result}"


@probe("The grammar accepts every limit kind the engine implements")
def probe_all_limit_kinds_parse() -> tuple[bool, str]:
    outcomes = {}
    for kind in LIMIT_KINDS:
        text = (
            HDR
            + f'resource r "R" {{ workinghours mon-fri 9:00-17:00 limits {{ {kind} }} }}\n'
            + 'task a "A" { start 2025-01-06 effort 2h allocate r }\n'
        )
        try:
            parse(text)
            outcomes[kind] = "ok"
        except Exception as exc:
            outcomes[kind] = type(exc).__name__
    ok = all(value == "ok" for value in outcomes.values())
    return ok, f"{outcomes}"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
