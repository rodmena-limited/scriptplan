#!/usr/bin/env python3
"""Falsifies: "effort is person-time shared across the allocated resources".

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - with N resources available in a slot the task accrues N slots of effort
  - each resource-slot is charged once, so cost matches the effort actually done
  - a mandatory allocation must be present in every booked slot
  - two tasks sharing a resource never double-book a slot
"""

from __future__ import annotations

from harness import HDR, booked_slots, datetime, main, parse, probe, task, total_booked_hours, window

TWO_RESOURCES = """resource a "A" { workinghours mon-fri 9:00-17:00 }
resource b "B" { workinghours mon-fri 9:00-17:00 }
"""


@probe("16h of effort on two resources finishes in one 8h working day")
def probe_effort_is_person_time() -> tuple[bool, str]:
    project = parse(HDR + TWO_RESOURCES + """
task t "T" { start 2025-01-06 effort 16h allocate a, b }
""")
    start, end = window(project, "t")
    slots_a, slots_b = len(booked_slots(project, "a")), len(booked_slots(project, "b"))
    ok = end == datetime(2025, 1, 6, 17, 0)
    return ok, (
        f"start={start} end={end} (expected end 2025-01-06 17:00); "
        f"slots booked a={slots_a} b={slots_b} (expected 8 each)"
    )


@probe("Cost of a two-resource task charges each resource-hour once")
def probe_effort_cost_not_double_counted() -> tuple[bool, str]:
    project = parse(HDR + """
resource a "A" { workinghours mon-fri 9:00-17:00 rate 100 }
resource b "B" { workinghours mon-fri 9:00-17:00 rate 100 }
task t "T" { start 2025-01-06 effort 16h allocate a, b }
""")
    scenario = task(project, "t").data[0]
    cost, allocated = scenario.getCost(), scenario.getAllocatedTime()
    return abs(cost - 1600.0) < 1e-6, (
        f"cost={cost} allocated={allocated}h (16 resource-hours at rate 100 is 1600)"
    )


@probe("A mandatory allocation is present in every slot the task books")
def probe_mandatory_allocation() -> tuple[bool, str]:
    project = parse(HDR + """
resource a "A" { workinghours mon-fri 9:00-17:00 }
resource b "B" { workinghours mon-fri 9:00-13:00 }
task t "T" { start 2025-01-06 effort 4h allocate a { mandatory }, b { mandatory } }
""")
    start, end = window(project, "t")
    slots_a = {i for i, _ in booked_slots(project, "a")}
    slots_b = {i for i, _ in booked_slots(project, "b")}
    ok = bool(slots_a) and slots_a == slots_b
    return ok, (
        f"start={start} end={end}; a booked {sorted(slots_a)}; b booked {sorted(slots_b)} "
        f"(mandatory pair must book the same slots)"
    )


@probe("Two tasks sharing one resource never double-book a slot")
def probe_no_double_booking() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 3h allocate r }
task b "B" { start 2025-01-06 effort 3h allocate r }
task c "C" { depends !a effort 2h allocate r }
""")
    booked = total_booked_hours(project, "r")
    windows = {name: window(project, name) for name in ("a", "b", "c")}
    return abs(booked - 8.0) < 1e-6, f"total booked = {booked}h (3+3+2 = 8); windows={windows}"


@probe("A resource is charged only for the time it actually worked")
def probe_partial_slot_cost() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 rate 60 }
task a "A" { start 2025-01-06 effort 90min allocate r }
""")
    scenario = task(project, "a").data[0]
    cost = scenario.getCost()
    _, end = window(project, "a")
    return abs(cost - 90.0) < 1e-6, f"cost={cost} for 1.5h at rate 60 (expected 90); end={end}"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
