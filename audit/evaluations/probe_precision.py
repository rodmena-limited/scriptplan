#!/usr/bin/env python3
"""Falsifies: "ScriptPlan schedules to the minute".

Claims under test (SPECS/004-ws2-time-model-and-minute-precision.md):
  - an explicit minute-level start is honoured exactly
  - non-standard shift boundaries yield their true capacity at the default
    resolution, not only when the user sets timingresolution 1min
  - a project timezone is applied to the times the user reads back
"""

from __future__ import annotations

from harness import HDR, booked_hours_by_day, datetime, main, parse, probe, window

ODD_SHIFT = 'resource r "R" { workinghours mon-fri 08:13-11:59, 13:07-17:47 }\n'
ODD_SHIFT_HOURS = (11 * 60 + 59 - 8 * 60 - 13 + 17 * 60 + 47 - 13 * 60 - 7) / 60.0  # 8h26m


@probe("A task starting 09:30 with 2h of effort ends at 11:30")
def probe_minute_start_is_honoured() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06-09:30 effort 2h allocate r }
task b "B" { depends !a effort 1h allocate r }
""")
    a_start, a_end = window(project, "a")
    b_start, _ = window(project, "b")
    ok = (
        a_start == datetime(2025, 1, 6, 9, 30)
        and a_end == datetime(2025, 1, 6, 11, 30)
        and b_start == datetime(2025, 1, 6, 11, 30)
    )
    return ok, f"a={a_start} -> {a_end} (expected 09:30 -> 11:30); successor starts {b_start}"


@probe("A 08:13-11:59 / 13:07-17:47 shift starts at 08:13 at the default resolution")
def probe_odd_shift_start_default_resolution() -> tuple[bool, str]:
    project = parse(HDR + ODD_SHIFT + """
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    start, end = window(project, "a")
    granularity = project.attributes["scheduleGranularity"]
    return start == datetime(2025, 1, 6, 8, 13), (
        f"start={start} end={end} scheduleGranularity={granularity}s (expected start 08:13)"
    )


@probe("A 08:13-11:59 / 13:07-17:47 shift yields 8h26m per day at the default resolution")
def probe_odd_shift_capacity_default_resolution() -> tuple[bool, str]:
    project = parse(HDR + ODD_SHIFT + """
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    per_day = booked_hours_by_day(project, "r")
    first = per_day.get(datetime(2025, 1, 6).date(), 0.0)
    return abs(first - ODD_SHIFT_HOURS) < 1e-6, (
        f"hours on the first day = {first:.4f} (expected {ODD_SHIFT_HOURS:.4f}); per day = {per_day}"
    )


@probe("The same odd shift behaves identically with timingresolution 1min")
def probe_odd_shift_explicit_minute_resolution() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-01-06 +3m {
  timezone "Etc/UTC"
  now 2025-01-06
  timingresolution 1min
}
""" + ODD_SHIFT + """
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    start, _ = window(project, "a")
    per_day = booked_hours_by_day(project, "r")
    first = per_day.get(datetime(2025, 1, 6).date(), 0.0)
    ok = start == datetime(2025, 1, 6, 8, 13) and abs(first - ODD_SHIFT_HOURS) < 1e-6
    return ok, f"start={start} first-day hours={first:.4f} (expected 08:13 and {ODD_SHIFT_HOURS:.4f})"


@probe("A project timezone is applied to the times the user reads back")
def probe_project_timezone_applied() -> tuple[bool, str]:
    """The file is written in the project's timezone, so a report is too.

    Scheduling happens in UTC so that resources in different zones share one
    axis; that is an internal representation, and what the reader sees must be
    the zone they wrote their file in.
    """
    project = parse("""project p "P" 2025-01-06 +1m { timezone "America/New_York" now 2025-01-06 }
resource r "R" { timezone "America/New_York" workinghours mon-fri 9:00-17:00 }
task a "A" { effort 2h allocate r }
taskreport t "t" { formats csv columns id, start, end timeformat "%Y-%m-%d-%H:%M" }
""")
    stored_start, stored_end = window(project, "a")
    report = next(iter(project.reports))
    report.generate_intermediate_format()
    rows = report.content.table.to_json().get("data", []) if report.content else []
    shown = rows[0] if rows else {}
    ok = shown.get("start", "").endswith("09:00") and shown.get("end", "").endswith("11:00")
    return ok, (
        f"report shows start={shown.get('start')!r} end={shown.get('end')!r} "
        f"(expected 09:00 and 11:00 New York time); "
        f"stored internally as {stored_start} / {stored_end} UTC"
    )


@probe("A project timezone does not disturb a project written in UTC")
def probe_utc_project_unchanged() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-01-06 +1m { timezone "Etc/UTC" now 2025-01-06 }
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06-09:00 effort 2h allocate r }
""")
    start, end = window(project, "a")
    ok = start == datetime(2025, 1, 6, 9, 0) and end == datetime(2025, 1, 6, 11, 0)
    return ok, f"start={start} end={end} (a UTC project is stored exactly as written)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
