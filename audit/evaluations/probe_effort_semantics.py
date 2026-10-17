#!/usr/bin/env python3
"""Falsifies: "effort is person-time shared across the allocated resources".

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - with N resources available in a slot the task accrues N slots of effort
  - each resource-slot is charged once, so cost matches the effort actually done
  - a mandatory allocation must be present in every booked slot
  - two tasks sharing a resource never double-book a slot (off the slot grid;
    probe_slot_sharing.py covers it in depth)
"""

from __future__ import annotations

from harness import (
    HDR,
    booked_seconds,
    booked_slots,
    datetime,
    main,
    parse,
    probe,
    task,
    total_booked_hours,
    window,
)

TWO_RESOURCES = """resource a "A" { workinghours mon-fri 9:00-17:00 }
resource b "B" { workinghours mon-fri 9:00-17:00 }
"""

FOUR_RESOURCES = "".join(
    f'resource {name} "{name.upper()}" {{ workinghours mon-fri 9:00-17:00 rate 100 }}\n'
    for name in "abcd"
)


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
    """Efforts off the slot grid, on purpose.

    The first version used 3h/3h/2h. Whole-hour efforts never share a slot,
    and the total booked stays right even when work overlaps, so it could not
    fail on the defect it was named after: 0.10.0 put 40, 13 and 40 minutes
    on one person all at 09:00 (issuedb #11).
    """
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 100min allocate r }
task b "B" { start 2025-01-06 effort 50min allocate r }
task c "C" { depends !a effort 70min allocate r }
""")
    per_slot = booked_seconds(project, "r")
    over = {f"{project.idxToDate(i):%H:%M}": s for i, s in per_slot.items() if s > 3600 + 1e-6}
    booked = sum(per_slot.values()) / 60.0
    windows = {name: tuple(f"{d:%H:%M}" for d in window(project, name)) for name in ("a", "b", "c")}
    # a, then b where a stopped; c may follow a but the desk is busy with b.
    expected = {"a": ("09:00", "10:40"), "b": ("10:40", "11:30"), "c": ("11:30", "12:40")}
    ok = not over and abs(booked - 220) < 1e-6 and windows == expected
    return ok, f"windows {windows} expected {expected}; booked {booked:.0f} of 220 min; overfull slots {over}"


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


@probe("Work is conserved: resource time consumed equals the effort credited")
def probe_work_is_conserved() -> tuple[bool, str]:
    """Whatever is booked must count towards finishing the task.

    The engine once took the maximum contribution across resources in a slot
    rather than the sum, so a task with four allocations booked four people and
    credited one person's work. Sixty-four hours were consumed and billed,
    sixteen were credited, and the other forty-eight simply vanished.
    """
    crews = ("a", "a, b", "a, b, c, d")
    lines, ok = [], True
    for crew in crews:
        project = parse(HDR + FOUR_RESOURCES + f"""
task t "T" {{ start 2025-01-06 effort 16h allocate {crew} }}
""")
        consumed = sum(total_booked_hours(project, name) for name in "abcd")
        balanced = abs(consumed - 16.0) < 1e-6
        ok = ok and balanced
        lines.append(f"{crew!r}: consumed {consumed:.0f}h for 16h credited{'' if balanced else '  <-- UNBALANCED'}")
    return ok, "; ".join(lines)


@probe("Adding people shortens the work, rather than only multiplying the bill")
def probe_more_resources_finish_sooner() -> tuple[bool, str]:
    """Duration is work over rate, so a bigger crew finishes sooner.

    A model where the completion date does not move when resources are added
    cannot answer the question a resource planner asks of it.
    """
    ends, costs = [], []
    for crew in ("a", "a, b", "a, b, c, d"):
        project = parse(HDR + FOUR_RESOURCES + f"""
task t "T" {{ start 2025-01-06 effort 16h allocate {crew} }}
""")
        ends.append(window(project, "t")[1])
        costs.append(task(project, "t").data[0].getCost())
    shortens = ends[0] > ends[1] > ends[2]
    same_cost = max(costs) - min(costs) < 1e-6
    return shortens and same_cost, (
        f"one/two/four workers finish {ends[0]}, {ends[1]}, {ends[2]}; "
        f"cost {costs[0]:.0f}, {costs[1]:.0f}, {costs[2]:.0f} "
        f"(the same work costs the same however it is staffed)"
    )


@probe("Scheduled backwards, a bigger crew starts later rather than finishing sooner")
def probe_alap_compresses_against_the_deadline() -> tuple[bool, str]:
    """The deadline is fixed, so parallelism buys a later start.

    This is the question a deadline-driven plan actually asks: how late can the
    work begin if more people are put on it. Both the conservation defect and
    the missing parallelism were present in the backward pass too, so it is
    probed in its own right rather than assumed to follow from the forward one.
    """
    starts, ends, consumed = [], [], []
    for crew in ("a", "a, b", "a, b, c, d"):
        project = parse(HDR + FOUR_RESOURCES + f"""
task t "T" {{ scheduling alap end 2025-01-31-17:00 effort 16h allocate {crew} }}
""")
        start, end = window(project, "t")
        starts.append(start)
        ends.append(end)
        consumed.append(sum(total_booked_hours(project, name) for name in "abcd"))

    later = starts[0] < starts[1] < starts[2]
    on_deadline = all(e == datetime(2025, 1, 31, 17, 0) for e in ends)
    balanced = all(abs(c - 16.0) < 1e-6 for c in consumed)
    return later and on_deadline and balanced, (
        f"one/two/four workers start {starts[0]}, {starts[1]}, {starts[2]}; "
        f"all end {ends[0]}; consumed {[f'{c:.0f}h' for c in consumed]} for 16h credited"
    )


if __name__ == "__main__":
    raise SystemExit(main(globals()))
