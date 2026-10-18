#!/usr/bin/env python3
"""Falsifies: "every task is placed where its constraints put it, and nowhere else".

Claims under test (SPECS/013, SPECS/014, SPECS/017):
  - a task starts no earlier than each predecessor ends (plus its gapduration)
  - a declared start is never preceded, a declared alap end never passed
  - a duration lasts exactly its calendar time, a length exactly its working time
  - no slot holds more than it has, and no two bookings on one resource overlap
  - a task leaves no free working time unused between the moment it may begin and the
    moment it does (backwards: between its end and the moment it must end)

0.10.1 passed every check in probe_slot_sharing.py and still put an alap duration task
after the task that follows it, and left half-hours free that a task needed. Both
break the claims above, which nothing asserted on generated plans until this file.
Every check reads dates from the public model and booked time from slotTaskUsage, so
it runs unchanged against older releases, which is how it was shown to fail.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from harness import main, probe

DAY = datetime(2026, 10, 19)  # a Monday
WORK = (9, 17)  # the default working day in these plans: Mon-Fri 09:00-17:00


def _parser() -> Any:
    from scriptplan.parser.tjp_parser import ProjectFileParser

    return ProjectFileParser()


def _at(day: int, minute: int) -> datetime:
    return DAY + timedelta(days=day, minutes=minute)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d-%H:%M")


def working_seconds(start: datetime, end: datetime) -> float:
    """Seconds of Mon-Fri 09:00-17:00 in [start, end), counted without the engine."""
    total, day = 0.0, start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < end:
        if day.weekday() < 5:
            lo, hi = max(start, day.replace(hour=WORK[0])), min(end, day.replace(hour=WORK[1]))
            if hi > lo:
                total += (hi - lo).total_seconds()
        day += timedelta(days=1)
    return total


def plan(rng: random.Random) -> tuple[str, list[dict[str, Any]], int]:
    """A random plan mixing effort, duration, length and milestones in both directions."""
    resolution = rng.choice((5, 10, 15, 30, 60))
    people = rng.randint(1, 3)
    tasks: list[dict[str, Any]] = []
    for i in range(rng.randint(3, 9)):
        kind = rng.choice(("effort", "effort", "duration", "length", "milestone"))
        task: dict[str, Any] = {"id": f"t{i}", "kind": kind, "alap": rng.random() < 0.3, "deps": []}
        if kind == "effort":
            task["minutes"] = rng.randint(1, 240)
            task["resource"] = f"r{rng.randrange(people)}"
        elif kind in ("duration", "length"):
            task["minutes"] = rng.randint(5, 300)
        if task["alap"]:
            if rng.random() < 0.6:
                task["end"] = _at(rng.randint(3, 6), rng.randint(9 * 60 + 1, 17 * 60))
        elif i and rng.random() < 0.5:
            task["deps"] = [f"t{j}" for j in rng.sample(range(i), rng.randint(1, min(2, i)))]
        elif rng.random() < 0.4:
            # A stated start, but never together with dependencies: a start that
            # contradicts one is refused, which tests/test_dependency_check.py covers.
            task["start"] = _at(rng.randint(0, 2), rng.randint(9 * 60, 16 * 60))
        tasks.append(task)

    lines = [f'project p "p" {_stamp(DAY)} +3w {{\n  timingresolution {resolution}min\n}}\n']
    lines += [f'resource r{r} "R{r}" {{ workinghours mon - fri 9:00 - 17:00 }}\n' for r in range(people)]
    for t in tasks:
        parts = []
        if t["kind"] == "effort":
            parts.append(f'effort {t["minutes"]}min allocate {t["resource"]}')
        elif t["kind"] in ("duration", "length"):
            parts.append(f'{t["kind"]} {t["minutes"]}min')
        if t["alap"]:
            parts.append("scheduling alap")
        if "end" in t:
            parts.append(f'end {_stamp(t["end"])}')
        if "start" in t:
            parts.append(f'start {_stamp(t["start"])}')
        if t["deps"]:
            parts.append("depends " + ", ".join(t["deps"]))
        lines.append(f'task {t["id"]} "{t["id"].upper()}" {{ {" ".join(parts)} }}\n')
    return "".join(lines), tasks, resolution


def violations(project: Any, tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {t.id: t for t in project.tasks}
    window = {t["id"]: (by_id[t["id"]].get("start", 0), by_id[t["id"]].get("end", 0)) for t in tasks}
    if any(s is None or e is None or not by_id[t["id"]].get("scheduled", 0) for t, (s, e) in zip(tasks, window.values())):
        return []  # reported as unschedulable; the slot checks still apply below
    found = []
    for t in tasks:
        start, end = window[t["id"]]
        for dep in t["deps"]:
            if start < window[dep][1]:
                found.append(f'{t["id"]} starts {start:%a %H:%M:%S} before {dep} ends {window[dep][1]:%a %H:%M:%S}')
        if "start" in t and start < t["start"]:
            found.append(f'{t["id"]} starts {start:%a %H:%M} before its declared {t["start"]:%a %H:%M}')
        if "end" in t and end > t["end"]:
            found.append(f'{t["id"]} ends {end:%a %H:%M} after its declared {t["end"]:%a %H:%M}')
        if t["kind"] == "duration" and abs((end - start).total_seconds() - t["minutes"] * 60) > 1:
            found.append(f'{t["id"]} duration {t["minutes"]}min spans {start:%a %H:%M:%S}-{end:%a %H:%M:%S}')
        if t["kind"] == "length" and abs(working_seconds(start, end) - t["minutes"] * 60) > 1:
            found.append(f'{t["id"]} length {t["minutes"]}min spans {working_seconds(start, end) / 60:.2f} working min')
    found += _idle_before_start(project, tasks, window)
    return found


def _idle_before_start(project: Any, tasks: list[dict[str, Any]], window: dict[str, Any]) -> list[str]:
    """Free working time an effort task left unused next to its window, on its only resource."""
    slot = float(project.attributes["scheduleGranularity"])
    resources = {r.id: r.data[0] for r in project.resources}
    found = []
    for t in tasks:
        if t["kind"] != "effort":
            continue
        rs, (start, end) = resources[t["resource"]], window[t["id"]]
        # The direction the engine used: an alap task with nothing to be late
        # against is scheduled forwards, with a warning (SPECS/005).
        backward = project.tasks[t["id"]].get("forward", 0) is False
        if backward:
            successors = [window[s["id"]][0] for s in tasks if t["id"] in s["deps"]]
            bound = min([t.get("end", project["end"]), *successors])
            lo, hi = end, bound
        else:
            bound = max([t.get("start", project["start"])] + [window[d][1] for d in t["deps"]])
            lo, hi = bound, start
        free = _free_seconds_between(project, rs, lo, hi, slot)
        if free > 1:
            side = "after it ends" if backward else "before it starts"
            found.append(f'{t["id"]} leaves {free / 60:.1f} free min on {t["resource"]} {side} ({lo:%a %H:%M}-{hi:%a %H:%M})')
    return found


def _free_seconds_between(project: Any, rs: Any, lo: datetime, hi: datetime, slot: float) -> float:
    """Free on-shift seconds of ``rs`` in [lo, hi): exact where intervals are known, whole slots otherwise."""
    if hi <= lo:
        return 0.0
    free, idx = 0.0, project.dateToIdx(lo)
    intervals = getattr(rs, "slotIntervals", None)
    while project.idxToDate(idx) < hi:
        s0 = project.idxToDate(idx)
        a, b = max(0.0, (lo - s0).total_seconds()), min(slot, (hi - s0).total_seconds())
        if b > a and rs.onShift(idx):
            if intervals is not None:
                taken = sum(max(0.0, min(e, b) - max(s, a)) for s, e, _ in intervals.get(idx, []))
                free += (b - a) - taken
            elif a == 0 and b == slot:
                free += max(0.0, slot - sum(x for _, x in rs.slotTaskUsage.get(idx, [])))
        idx += 1
    return free


def _slot_problems(project: Any) -> list[str]:
    slot = float(project.attributes["scheduleGranularity"])
    found = []
    for r in project.resources:
        rs = r.data[0]
        for idx, usage in rs.slotTaskUsage.items():
            if sum(s for _, s in usage) > slot + 1e-6:
                found.append(f"{r.id} slot {idx} holds {sum(s for _, s in usage):.0f}s of {slot:.0f}")
        for idx, spans in (getattr(rs, "slotIntervals", None) or {}).items():
            for (_, e1, _), (s2, _, _) in zip(spans, spans[1:]):
                if e1 > s2 + 1e-9:
                    found.append(f"{r.id} slot {idx}: bookings overlap")
    return found


@probe("Seeded fuzz: 300 mixed plans respect every dependency, date, span and resource")
def probe_mixed_plans() -> tuple[bool, str]:
    rng, parser = random.Random(1310), _parser()
    failures, unschedulable = [], 0
    from scriptplan.utils.message_handler import get_message_handler_instance

    for n in range(300):
        text, tasks, _ = plan(rng)
        get_message_handler_instance().clear()
        project = parser.parse(text)
        if not all(t.get("scheduled", 0) for t in project.tasks):
            unschedulable += 1
        problems = violations(project, tasks) + _slot_problems(project)
        if problems:
            failures.append(f"plan {n}: {problems[:3]}\n{text}")
    ok = not failures and unschedulable <= 30
    return ok, f"{300 - len(failures)} of 300 plans clean; {unschedulable} unschedulable" + (
        "\n" + failures[0] if failures else ""
    )


if __name__ == "__main__":
    raise SystemExit(main(globals()))
