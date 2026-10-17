#!/usr/bin/env python3
"""Falsifies: "tasks that share a slot on one resource share its time".

Claims under test (SPECS/011-slot-sharing-never-overbooks.md):
  - the seconds booked in a slot never exceed the slot (R1)
  - the slot's own used-seconds counter agrees with what was booked (R2)
  - the next task starts where the last one stopped, in both directions (R3-R5)
  - several resources finishing a task together stop together (R6)
  - time handed back is handed back to the limits too (R7)
  - a mid-slot start or end constrains that one slot only (R8)
  - every effort task gets exactly its effort, no more and no less (R9)

The capacity checks read slotTaskUsage, the per-task record, and never
slotSecondsUsed: the defect this file exists for corrupted slotSecondsUsed in
the same step that overbooked the slot, so every check that read it stayed
green while three tasks ran at once (issuedb #11). Expected dates come from
packing the efforts by hand, not from the engine.
"""

from __future__ import annotations

import csv
import io
import random
from collections import defaultdict
from typing import Any

from harness import main, parse, probe, run_cli, task, write_tjp

DAY = "2026-10-19"
RESOLUTIONS = (60, 30, 15, 5)


def plan(resolution: int, body: str, resources: str = "") -> str:
    desk = resources or 'resource r0 "Desk" { workinghours mon - fri 9:00 - 17:00 }\n'
    return (
        f'project p "p" {DAY} +2w {{\n  timingresolution {resolution}min\n}}\n'
        + desk
        + body
    )


def report(tjp: str, columns: str = "id, start, end", fmt: str = "%Y-%m-%d %H:%M") -> dict[str, dict[str, str]]:
    """Task rows as the customer sees them: the plan CLI, in a fresh process."""
    text = tjp + f'taskreport out "out" {{ formats csv columns {columns} timeformat "{fmt}" }}\n'
    done = run_cli(["report", "--csv", write_tjp(text)])
    if done.returncode != 0:
        raise RuntimeError(f"plan report failed: {done.stderr or done.stdout}")
    lines = [line for line in done.stdout.splitlines() if "," in line]
    rows = csv.DictReader(io.StringIO("\n".join(lines)))
    return {row["Id"]: row for row in rows}


def hhmm(rows: dict[str, dict[str, str]]) -> dict[str, str]:
    return {tid: f"{row['Start'][-5:]}-{row['End'][-5:]}" for tid, row in rows.items()}


def ledger_problems(project: Any, strict_counter: bool = True) -> list[str]:
    """Slots holding more than they have, and counters that disagree with them."""
    slot = float(project.attributes["scheduleGranularity"])
    problems = []
    for res in project.resources:
        rs = res.data[0] if res.data else None
        if rs is None:
            continue
        for idx, usage in sorted(rs.slotTaskUsage.items()):
            booked = sum(seconds for _, seconds in usage)
            moment = project.idxToDate(idx)
            if booked > slot + 1e-6:
                shares = [(t.id, round(seconds)) for t, seconds in usage]
                problems.append(f"{res.id} {moment:%a %H:%M}: {booked:.0f}s booked in a {slot:.0f}s slot {shares}")
            counted = rs.slotSecondsUsed.get(idx, 0.0)
            if counted < booked - 1e-6 or (strict_counter and abs(counted - booked) > 1e-6):
                problems.append(f"{res.id} {moment:%a %H:%M}: slotSecondsUsed {counted:.0f}s, booked {booked:.0f}s")
            if booked > 0 and not rs.onShift(idx):
                problems.append(f"{res.id} {moment:%a %H:%M}: work booked outside working hours")
    return problems


def worked(project: Any) -> dict[str, float]:
    """Hours of effort each task received, from what was booked for it."""
    out: dict[str, float] = defaultdict(float)
    for res in project.resources:
        rs = res.data[0] if res.data else None
        if rs is None:
            continue
        efficiency = res.get("efficiency", 0) or 1.0
        for usage in rs.slotTaskUsage.values():
            for t, seconds in usage:
                out[t.id] += seconds / 3600.0 * efficiency
    return out


def conservation_problems(project: Any, efforts: dict[str, float]) -> list[str]:
    """Scheduled tasks that got more or less work than their effort."""
    got = worked(project)
    scheduled = {t.id for t in project.tasks if t.get("scheduled", 0)}
    return [
        f"{tid}: effort {hours * 60:.2f} min, booked {got.get(tid, 0.0) * 60:.2f} min"
        for tid, hours in efforts.items()
        if tid in scheduled and abs(got.get(tid, 0.0) - hours) * 3600 > 1.0
    ]


def sequential(efforts: list[int], start: str = "09:00") -> list[str]:
    """Back-to-back windows on one desk within one 09:00-17:00 day."""
    h, m = map(int, start.split(":"))
    at, out = h * 60 + m, []
    for minutes in efforts:
        out.append(f"{at // 60:02d}:{at % 60:02d}-{(at + minutes) // 60:02d}:{(at + minutes) % 60:02d}")
        at += minutes
    return out


THREE = (
    'task t0 "T0" { effort 40min allocate r0 }\n'
    'task t1 "T1" { effort 13min allocate r0 }\n'
    'task t2 "T2" { effort 40min allocate r0 }\n'
)


@probe("40/13/40 minutes on one desk run back to back at every resolution (CLI)")
def probe_three_tasks_forward() -> tuple[bool, str]:
    expected = dict(zip(("t0", "t1", "t2"), sequential([40, 13, 40])))
    lines, ok = [], True
    for resolution in RESOLUTIONS:
        got = hhmm(report(plan(resolution, THREE)))
        project = parse(plan(resolution, THREE))
        problems = ledger_problems(project)
        good = got == expected and not problems
        ok &= good
        lines.append(f"R={resolution}: {got} {'ok' if good else f'expected {expected}'} {problems}")
    return ok, "\n".join(lines)


@probe("The same three tasks scheduled alap end back to back at 17:00 (CLI)")
def probe_three_tasks_backward() -> tuple[bool, str]:
    body = THREE.replace("allocate r0 }", f"allocate r0 scheduling alap end {DAY}-17:00 }}")
    # Placed in declaration order from the end: t0 last, then t1, then t2.
    expected = {"t0": "16:20-17:00", "t1": "16:07-16:20", "t2": "15:27-16:07"}
    lines, ok = [], True
    for resolution in RESOLUTIONS:
        got = hhmm(report(plan(resolution, body)))
        problems = ledger_problems(parse(plan(resolution, body)))
        good = got == expected and not problems
        ok &= good
        lines.append(f"R={resolution}: {got} {'ok' if good else f'expected {expected}'} {problems}")
    return ok, "\n".join(lines)


@probe("Eight off-grid efforts never fill a day past its 480 minutes")
def probe_eight_efforts_whole_days() -> tuple[bool, str]:
    efforts = [61, 129, 49, 73, 318, 163, 579, 134]
    body = "".join(f'task t{i} "T{i}" {{ effort {m}min allocate r0 }}\n' for i, m in enumerate(efforts))
    project = parse(plan(60, body))
    per_day: dict[Any, float] = defaultdict(float)
    desk = next(r for r in project.resources if r.id == "r0")
    for idx, usage in desk.data[0].slotTaskUsage.items():
        per_day[project.idxToDate(idx).date()] += sum(s for _, s in usage) / 60.0
    full = {str(day): round(minutes, 2) for day, minutes in sorted(per_day.items())}
    over = {day: minutes for day, minutes in full.items() if minutes > 480 + 1e-6}
    lost = conservation_problems(project, {f"t{i}": m / 60.0 for i, m in enumerate(efforts)})
    total = sum(full.values())
    ok = not over and not lost and abs(total - sum(efforts)) < 1e-6 and not ledger_problems(project)
    return ok, f"minutes per day {full}; total {total} of {sum(efforts)}; over {over}; {lost}"


@probe("Two people finishing a task together stop together and are charged once (CLI)")
def probe_two_resources_final_slot() -> tuple[bool, str]:
    people = "".join(
        f'resource {r} "{r.upper()}" {{ workinghours mon - fri 9:00 - 17:00 rate 60 }}\n' for r in "ab"
    )
    body = 'task t "T" { effort 80min allocate a, b }\n'
    row = report(plan(60, body, people), columns="id, start, end, cost", fmt="%H:%M")["t"]
    project = parse(plan(60, body, people))
    got = (row["Start"], row["End"], float(row["Cost"]))
    lost = conservation_problems(project, {"t": 80 / 60.0})
    ok = got == ("09:00", "09:40", 80.0) and not lost and not ledger_problems(project)
    return ok, f"start/end/cost {got} (80 person-minutes on two people: 09:00-09:40 at cost 80) {lost}"


@probe("Asap and alap tasks sharing one slot take opposite ends of it (CLI)")
def probe_mixed_directions() -> tuple[bool, str]:
    body = (
        f'task late "Late" {{ end {DAY}-10:00 effort 40min allocate r0 scheduling alap }}\n'
        'task e1 "E1" { effort 13min allocate r0 }\n'
        'task e2 "E2" { effort 10min allocate r0 }\n'
    )
    got = hhmm(report(plan(60, body)))
    # late holds 09:20-10:00; e1 takes 09:00-09:13; e2 has 7 minutes before
    # late and finishes its last 3 after it.
    expected = {"late": "09:20-10:00", "e1": "09:00-09:13", "e2": "09:13-10:03"}
    problems = ledger_problems(parse(plan(60, body)))
    return got == expected and not problems, f"{got} expected {expected} {problems}"


@probe("A mid-slot start or end is honoured exactly, and only in its own slot (CLI)")
def probe_mid_slot_constraints() -> tuple[bool, str]:
    other = (
        'resource r0 "Desk" { workinghours mon - fri 9:00 - 17:00 }\n'
        'resource b "Other" { workinghours mon - fri 9:00 - 17:00 }\n'
    )
    body = (
        'task a "A" { effort 60min allocate r0 priority 900 }\n'
        'task y "Y" { effort 50min allocate b priority 900 }\n'
        'task x "X" { depends y effort 30min allocate r0 priority 100 }\n'
        f'task f "F" {{ start {DAY}-11:30 effort 40min allocate b }}\n'
        f'task k "K" {{ end {DAY}-16:30 effort 40min allocate b scheduling alap }}\n'
    )
    got = hhmm(report(plan(60, body, other)))
    # X may start at 09:50 but the desk is busy until 10:00: 10:00, not 10:50.
    expected = {"a": "09:00-10:00", "y": "09:00-09:50", "x": "10:00-10:30", "f": "11:30-12:10", "k": "15:50-16:30"}
    problems = ledger_problems(parse(plan(60, body, other)), strict_counter=False)
    return got == expected and not problems, f"{got} expected {expected} {problems}"


@probe("A daily cap counts the time worked: it blocks at the cap and frees what was not used")
def probe_cap_counts_released_time() -> tuple[bool, str]:
    capped = 'resource r0 "Desk" { workinghours mon - fri 9:00 - 17:00 limits { dailymax 60min } }\n'
    rows = report(plan(60, THREE, capped), fmt="%a %H:%M")
    got = {tid: f"{row['Start']}-{row['End']}" for tid, row in rows.items()}
    # 60 minutes on Monday: 40 + 13 + 7 of t2; the other 33 on Tuesday.
    expected = {"t0": "Mon 09:00-Mon 09:40", "t1": "Mon 09:40-Mon 09:53", "t2": "Mon 09:53-Tue 09:33"}
    return got == expected, f"{got} expected {expected}"


def _fuzz_parser() -> Any:
    """One parser for the fuzz loops.

    Building one compiles the grammar (most of a second); parse() itself makes
    a fresh transformer and model every call, so plans share nothing else.
    """
    from scriptplan.parser.tjp_parser import ProjectFileParser

    return ProjectFileParser()


def _fuzz_plan(rng: random.Random) -> tuple[str, dict[str, float], bool]:
    resolution = rng.choice((5, 10, 15, 30, 60))
    people = rng.randint(1, 3)
    resources = ""
    for r in range(people):
        extra = f" efficiency {rng.choice(('0.5', '1.0', '1.5'))}" if rng.random() < 0.3 else ""
        if rng.random() < 0.3:
            extra += f" limits {{ dailymax {rng.choice((240, 400))}min }}"
        resources += f'resource r{r} "R{r}" {{ workinghours mon - fri 9:00 - 17:00{extra} }}\n'
    body, efforts, plain = "", {}, True
    for i in range(rng.randint(3, 10)):
        minutes = rng.randint(1, 600)
        crew = ", ".join(f"r{r}" for r in sorted(rng.sample(range(people), rng.randint(1, min(2, people)))))
        extra = ""
        roll = rng.random()
        if roll < 0.2:
            day, hour, minute = rng.randint(10, 18), rng.randint(9, 16), rng.choice(("00", "17", "45"))
            extra = f" scheduling alap end 2026-12-{day}-{hour:02d}:{minute}"
            plain = False
        elif roll < 0.4 and i > 0:
            extra = f" depends t{rng.randrange(i)}"
            plain = False
        body += f'task t{i} "T{i}" {{ effort {minutes}min allocate {crew}{extra} }}\n'
        efforts[f"t{i}"] = minutes / 60.0
    tjp = f'project p "p" {DAY} +3m {{\n  timingresolution {resolution}min\n}}\n' + resources + body
    return tjp, efforts, plain


@probe("Seeded fuzz: 240 plans with free efforts never overbook, lose or invent work")
def probe_fuzz() -> tuple[bool, str]:
    rng, parser = random.Random(20261017), _fuzz_parser()
    failures, infeasible = [], 0
    for n in range(240):
        tjp, efforts, plain = _fuzz_plan(rng)
        project = parser.parse(tjp)
        if not all(t.get("scheduled", 0) for t in project.tasks):
            # Reported as an error, which is right; the slots must still hold.
            infeasible += 1
        problems = ledger_problems(project, strict_counter=plain)
        problems += conservation_problems(project, efforts)
        first = {t.id: (t.get("start", 0), t.get("end", 0)) for t in project.tasks}
        project.schedule()
        again = {t.id: (t.get("start", 0), t.get("end", 0)) for t in project.tasks}
        if first != again:
            problems.append(f"scheduling twice moved {[k for k in first if first[k] != again[k]]}")
        if problems:
            failures.append(f"plan {n}: {problems[:3]}\n{tjp}")
    # A fuzz that mostly generates plans nobody can schedule proves little.
    ok = not failures and infeasible <= 24
    summary = f"{240 - len(failures)} of 240 plans clean; {infeasible} reported as unschedulable"
    return ok, summary + ("\n" + failures[0] if failures else "")


@probe("Seeded fuzz: independent tasks on one desk never overlap and leave no gaps")
def probe_fuzz_one_desk() -> tuple[bool, str]:
    rng, parser = random.Random(83589), _fuzz_parser()
    failures = []
    for _ in range(120):
        resolution = rng.choice((5, 10, 15, 30, 60))
        efforts = [rng.randint(1, 90) for _ in range(rng.randint(2, 5))]
        body = "".join(f'task t{i} "T{i}" {{ effort {m}min allocate r0 }}\n' for i, m in enumerate(efforts))
        project = parser.parse(plan(resolution, body))
        windows = sorted((task(project, f"t{i}").get("start", 0), task(project, f"t{i}").get("end", 0), m)
                         for i, m in enumerate(efforts))
        # Under 8 hours in total, so it all fits Monday: each window lasts its
        # effort and starts where the previous one ended.
        expect_start = windows[0][0].replace(hour=9, minute=0)
        for start, end, minutes in windows:
            if start != expect_start or (end - start).total_seconds() != minutes * 60:
                failures.append(f"R={resolution} efforts={efforts}: {[(s.time(), e.time()) for s, e, _ in windows]}")
                break
            expect_start = end
    return not failures, f"{120 - len(failures)} of 120 plans back to back" + ("\n" + failures[0] if failures else "")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
