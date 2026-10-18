#!/usr/bin/env python3
"""Falsifies: "ScriptPlan converts durations the way the .tjp format defines them".

Claims under test (SPECS/003-ws1-units-and-calendar-arithmetic.md):
  - calendar durations: min=60s, h=3600s, d=86400s, w=7d, m=30.4167d, y=365d
  - working durations use dailyworkinghours / yearlyworkingdays
  - 'm' means months, 'min' means minutes, everywhere
  - gapduration is calendar time; gaplength is working time and is not
    truncated to zero when it is smaller than one slot
  - a limit written with a duration unit uses the same table
"""

from __future__ import annotations

from harness import HDR, datetime, main, parse, probe, task, timedelta, window

ONE_RESOURCE = 'resource r "R" { workinghours mon-fri 9:00-17:00 }\n'


@probe("gapduration is calendar time (2d after a Monday finish lands on Wednesday)")
def probe_gapduration_is_calendar_time() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 8h allocate r }
task b "B" { depends !a { gapduration 2d } effort 1h allocate r }
""")
    _, a_end = window(project, "a")
    b_start, _ = window(project, "b")
    gap = b_start - a_end
    return gap >= timedelta(hours=48), f"a.end={a_end} b.start={b_start} gap={gap} (expected >= 48h of calendar time)"


@probe("gaplength 30min is honoured rather than truncated to zero")
def probe_gaplength_sub_slot() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 2h allocate r }
task b "B" { depends !a { gaplength 30min } effort 1h allocate r }
""")
    _, a_end = window(project, "a")
    b_start, _ = window(project, "b")
    gap = b_start - a_end
    return gap >= timedelta(minutes=30), f"a.end={a_end} b.start={b_start} gap={gap} (expected >= 30min of working time)"


@probe("gaplength 1d is one working day, not one calendar day")
def probe_gaplength_working_day() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 2h allocate r }
task b "B" { depends !a { gaplength 1d } effort 1h allocate r }
""")
    b_start, _ = window(project, "b")
    return b_start == datetime(2025, 1, 7, 11, 0), (
        f"b.start={b_start} (a ends Mon 11:00; one working day of gap is 8 working hours -> Tue 11:00)"
    )


@probe("effort 3m means three months of effort, not three minutes")
def probe_effort_month_unit() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 3m allocate r }
""")
    effort = task(project, "a").get("effort", 0)
    return effort >= 400, f"stored effort for '3m' = {effort} (a month of effort is ~173h, so >= 400h for three)"


@probe("effort 30min and 2.5h are stored and scheduled exactly")
def probe_effort_small_units() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 30min allocate r }
task b "B" { start 2025-01-07 effort 2.5h allocate r }
""")
    _, a_end = window(project, "a")
    _, b_end = window(project, "b")
    ok = a_end == datetime(2025, 1, 6, 9, 30) and b_end == datetime(2025, 1, 7, 11, 30)
    return ok, f"30min task ends {a_end} (expected 09:30); 2.5h task ends {b_end} (expected 11:30)"


@probe("limits { dailymax 30min } is a thirty-minute cap")
def probe_limit_minute_unit() -> tuple[bool, str]:
    from harness import booked_hours_by_day

    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 limits { dailymax 30min } }
task a "A" { start 2025-01-06 effort 4h allocate r }
""")
    per_day = booked_hours_by_day(project, "r")
    ok = bool(per_day) and all(hours <= 0.5 + 1e-9 for hours in per_day.values())
    return ok, f"hours booked per day = {per_day} (cap is 30 minutes)"


@probe("duration is calendar time and is actually scheduled")
def probe_duration_is_scheduled() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 duration 2d }
""")
    stored = task(project, "a").get("duration", 0)
    start, end = window(project, "a")
    ok = bool(stored) and end == datetime(2025, 1, 8, 0, 0)
    return ok, f"stored duration={stored!r}; start={start} end={end} (2 calendar days from 2025-01-06 00:00)"


@probe("length is working time and is actually scheduled")
def probe_length_is_scheduled() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 length 2d allocate r }
""")
    stored = task(project, "a").get("length", 0)
    start, end = window(project, "a")
    ok = bool(stored) and end == datetime(2025, 1, 7, 17, 0)
    return ok, f"stored length={stored!r}; start={start} end={end} (2 working days ends Tue 17:00)"


@probe("dailyworkinghours changes what one day of effort means")
def probe_dailyworkinghours_is_used() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-01-06 +3m {
  timezone "Etc/UTC"
  now 2025-01-06
  dailyworkinghours 4
}
resource r "R" { workinghours mon-fri 9:00-13:00 }
task a "A" { start 2025-01-06 effort 1d allocate r }
""")
    effort = task(project, "a").get("effort", 0)
    _, end = window(project, "a")
    ok = abs(float(effort) - 4.0) < 1e-6 and end == datetime(2025, 1, 6, 13, 0)
    return ok, f"effort for '1d' with dailyworkinghours 4 = {effort} (expected 4); end={end} (expected 13:00)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
