#!/usr/bin/env python3
"""Falsifies: "ScriptPlan's calendar knows about midnight, leave and timezones".

Claims under test (SPECS/003-ws1-units-and-calendar-arithmetic.md):
  - a working-hours interval that crosses midnight applies to the following
    weekday, not the same one
  - a single-day vacation or leave blocks the whole day
  - resource limits count periods in the resource's local calendar
  - a resource's shift follows its own timezone across DST in both directions
  - a shift starts from the project's week and a sub-resource from its
    parent's, with each line replacing the days it names (issuedb #42)
  - a resource with no timezone of its own works its hours in the project's
  - with a stated timingresolution, a slot that starts in working time counts
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


WEEK_HDR = 'project p "P" 2025-06-02 +2m {{ timezone "Etc/UTC" now 2025-06-02 {project} }}\n'


@probe("A shift starts from the project's week and a sub-resource from its parent's")
def probe_weeks_are_inherited() -> tuple[bool, str]:
    # Expected ends are the reference scheduler's, to the hour.
    on_shift = parse(WEEK_HDR.format(project="workinghours mon - fri 07:00 - 11:00") + """
shift s "S" { workinghours wed 10:00 - 12:00 }
resource r "R" { workinghours s }
task a "A" { effort 20h allocate r }
""")
    sub = parse(WEEK_HDR.format(project="") + """
resource g "G" { workinghours mon - fri 06:00 - 10:00
  resource r "R" { workinghours wed 10:00 - 12:00 } }
task a "A" { effort 20h allocate r }
""")
    ends = window(on_shift, "a")[1], window(sub, "a")[1]
    ok = ends == (datetime(2025, 6, 9, 9, 0), datetime(2025, 6, 9, 8, 0))
    return ok, f"on the shift ends {ends[0]} (expected 2025-06-09 09:00); sub-resource ends {ends[1]} (expected 2025-06-09 08:00)"


@probe("A resource with no timezone of its own works its hours in the project's")
def probe_hours_in_project_zone() -> tuple[bool, str]:
    project = parse("""project p "P" 2025-06-02 +2m { timezone "Europe/London" now 2025-06-02 }
resource r "R" { workinghours mon - fri 09:00 - 17:00 }
task a "A" { effort 8h allocate r }
""")
    start, end = window(project, "a")
    # 09:00 in London in June is 08:00 UTC, which is how the model holds it.
    ok = start == datetime(2025, 6, 2, 8, 0) and end == datetime(2025, 6, 2, 16, 0)
    return ok, f"start={start} end={end} UTC (expected 08:00 -> 16:00 UTC, which is 09:00 -> 17:00 in London)"


@probe("With a stated timingresolution, a slot that starts in working time counts as worked")
def probe_stated_resolution_rounds_to_the_slot() -> tuple[bool, str]:
    text = """project p "P" 2025-06-02 +2m {{ timezone "Etc/UTC" now 2025-06-02 {resolution} }}
resource r "R" {{ workinghours mon - fri 09:00 - 23:59 }}
task a "A" {{ effort 15h allocate r }}
"""
    stated = window(parse(text.format(resolution="timingresolution 30min")), "a")[1]
    derived = window(parse(text.format(resolution="")), "a")[1]
    # Half-hour slots: 23:30 starts in working time, so Monday gives 15 h (the
    # reference scheduler's answer). Derived slots are a minute: Monday gives 14h59.
    ok = stated == datetime(2025, 6, 3, 0, 0) and derived == datetime(2025, 6, 3, 9, 1)
    return ok, f"stated 30min ends {stated} (expected 2025-06-03 00:00); derived ends {derived} (expected 2025-06-03 09:01)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
