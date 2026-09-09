#!/usr/bin/env python3
"""Falsifies: "ScriptPlan's calendar knows about midnight, leave and timezones".

Claims under test (SPECS/003-ws1-units-and-calendar-arithmetic.md):
  - a working-hours interval that crosses midnight applies to the following
    weekday, not the same one
  - a single-day vacation or leave blocks the whole day
  - resource limits count periods in the resource's local calendar
  - a resource's shift follows its own timezone across DST in both directions
"""

from __future__ import annotations

from harness import (
    HDR,
    booked_hours_by_day,
    booked_hours_by_local_day,
    booked_slots,
    datetime,
    main,
    parse,
    probe,
    window,
)

EARLY_HDR = """project p "P" 2025-01-05 +1m {
  timezone "Etc/UTC"
  now 2025-01-05
}
"""


@probe("A Friday night shift 22:00-06:00 works Saturday morning, not Friday morning")
def probe_cross_midnight_next_day() -> tuple[bool, str]:
    project = parse(EARLY_HDR + """
resource r "R" { workinghours fri 22:00-06:00 }
task a "A" { start 2025-01-10 effort 6h allocate r }
""")
    start, end = window(project, "a")
    slots = [d.strftime("%a %H:%M") for _, d in booked_slots(project, "r")]
    ok = start == datetime(2025, 1, 10, 22, 0) and end == datetime(2025, 1, 11, 4, 0)
    return ok, f"start={start} end={end} slots={slots} (expected Fri 22:00 -> Sat 04:00)"


@probe("A Sunday night shift carries into Monday even when Monday has day hours")
def probe_cross_midnight_into_busy_weekday() -> tuple[bool, str]:
    project = parse(EARLY_HDR + """
resource r "R" { workinghours sun 22:00-06:00 workinghours mon 09:00-17:00 }
task a "A" { start 2025-01-05-22:00 effort 6h allocate r }
""")
    start, end = window(project, "a")
    slots = [d.strftime("%a %H:%M") for _, d in booked_slots(project, "r")]
    ok = end == datetime(2025, 1, 6, 4, 0)
    return ok, f"start={start} end={end} slots={slots} (expected Sun 22:00 -> Mon 04:00)"


@probe("A single-day resource vacation blocks that whole day")
def probe_single_day_vacation() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 vacation 2025-01-07 }
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    per_day = booked_hours_by_day(project, "r")
    blocked = datetime(2025, 1, 7).date() not in per_day
    return blocked, f"hours booked per day = {per_day} (2025-01-07 must be absent)"


@probe("A single-day resource leave blocks that whole day")
def probe_single_day_leave() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 leaves annual 2025-01-07 }
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    per_day = booked_hours_by_day(project, "r")
    blocked = datetime(2025, 1, 7).date() not in per_day
    return blocked, f"hours booked per day = {per_day} (2025-01-07 must be absent)"


@probe("A global vacation blocks resources with and without their own hours")
def probe_global_vacation() -> tuple[bool, str]:
    project = parse(HDR + """
vacation "closure" 2025-01-07
resource r "R" { workinghours mon-fri 9:00-17:00 }
resource q "Q" { }
task a "A" { start 2025-01-06 effort 16h allocate r }
task b "B" { start 2025-01-06 effort 16h allocate q }
""")
    day = datetime(2025, 1, 7).date()
    r_days, q_days = booked_hours_by_day(project, "r"), booked_hours_by_day(project, "q")
    return day not in r_days and day not in q_days, f"r={r_days}\n  q={q_days} (2025-01-07 must be absent from both)"


@probe("dailymax counts the resource's local calendar day, not UTC")
def probe_limit_uses_local_day() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { timezone "America/Los_Angeles" workinghours mon-fri 9:00-17:00 limits { dailymax 4h } }
task a "A" { start 2025-01-06 effort 16h allocate r }
""")
    per_day = booked_hours_by_local_day(project, "r", "America/Los_Angeles")
    ok = bool(per_day) and all(hours <= 4 + 1e-9 for hours in per_day.values())
    return ok, f"hours per Los Angeles day = {per_day} (cap is 4h per local day)"


@probe("A London resource keeps 09:00 local across the spring DST change")
def probe_dst_spring_forward() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-03-24 +1m { timezone "Etc/UTC" now 2025-03-24 }
resource r "R" { timezone "Europe/London" workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-03-28 effort 10h allocate r }
""")
    monday = [d for _, d in booked_slots(project, "r") if d.date() == datetime(2025, 3, 31).date()]
    ok = bool(monday) and monday[0] == datetime(2025, 3, 31, 8, 0)
    return ok, f"first Monday slot (UTC) = {monday[0] if monday else None} (09:00 BST is 08:00 UTC)"


@probe("A London resource keeps 09:00 local across the autumn DST change")
def probe_dst_fall_back() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-10-20 +1m { timezone "Etc/UTC" now 2025-10-20 }
resource r "R" { timezone "Europe/London" workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-10-24 effort 10h allocate r }
""")
    slots = booked_slots(project, "r")
    friday = [d for _, d in slots if d.date() == datetime(2025, 10, 24).date()]
    monday = [d for _, d in slots if d.date() == datetime(2025, 10, 27).date()]
    ok = (
        bool(friday)
        and friday[0] == datetime(2025, 10, 24, 8, 0)
        and bool(monday)
        and monday[0] == datetime(2025, 10, 27, 9, 0)
    )
    return ok, (
        f"Friday first slot={friday[0] if friday else None} (09:00 BST = 08:00 UTC); "
        f"Monday first slot={monday[0] if monday else None} (09:00 GMT = 09:00 UTC)"
    )


if __name__ == "__main__":
    raise SystemExit(main(globals()))
