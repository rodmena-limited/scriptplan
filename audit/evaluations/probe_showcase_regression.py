#!/usr/bin/env python3
"""Falsifies: "the example projects still schedule as they did before the audit".

The pre-audit SHOWCASE.md recorded the start and end of every task in all 24
example projects. legacy_showcase.json holds those 594 schedules, taken from
commit 1ea3287. This replays each project and compares.

Four projects are expected to differ, each for a reason recorded in the commit
that changed it. They are listed below with what changed and why, and the probe
fails if any *other* project moves, if an expected change stops happening, or
if a project stops scheduling at all. An expected change that no longer appears
is as much a surprise as an unexpected one.
"""

from __future__ import annotations

import contextlib
import io
import json
import os

from harness import main, probe

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "legacy_showcase.json")
FIXTURES = os.path.normpath(os.path.join(HERE, "..", "..", "examples", "showcase"))
TIME_FORMAT = "%Y-%m-%d-%H:%M"

#: project -> why its schedule is expected to differ.
EXPECTED_CHANGES = {
    "airport_stress_test.tjp": (
        "t_install and t_low were reported as starting at the top of a slot the "
        "electrician was still working in: t_install at 11:00 while t_crit ran until "
        "11:40, t_low at 10:00 while t_install ran until 10:20. They now start when e1 "
        "is free. Their ends, and every other task, are unchanged (issuedb #11)."
    ),
    "jit_supply.tjp": (
        "connection_setup.set_deps referenced '!delivery.assemble_a', which resolves "
        "relative to the parent and so pointed at a task that does not exist. The whole "
        "block was inert and its milestone sat at the project end. Corrected to '!!', it "
        "now sits after the two assemblies, where the fixture meant it to. The delivery "
        "tasks themselves are unchanged."
    ),
    "simple.tjp": (
        "'allocate dev1, dev2' shares the effort between two developers, as the .tjp format "
        "defines effort, so the work finishes sooner. It previously took the same elapsed "
        "time as one developer while booking both."
    ),
    "tutorial.tjp": (
        "Same shared-effort correction, across a project that allocates two or three "
        "developers to most of its tasks; it finishes in roughly half the elapsed time. "
        "The fixture's own comment says this is what should happen: 'Because they can "
        "work in parallel, they may finish this task earlier than in 20 working-days.' "
        "Since issuedb #11 the last slot of a shared task also ends when the people on it "
        "have done the remaining work between them, rather than at the top of the next "
        "hour, and the milestones after it sit at that moment."
    ),
}


def _load_baseline() -> dict[str, dict[str, list[str]]]:
    with open(BASELINE) as handle:
        return json.load(handle)["projects"]


def _current(name: str) -> dict[str, tuple[str, str]]:
    """Schedule the project and read every task's window, as a reader sees it.

    Read from the model rather than from a report: a project may declare many
    reports, or none, and which one a CLI would show is a separate question
    from what was scheduled.
    """
    from scriptplan.core.timezones import from_utc
    from scriptplan.parser.tjp_parser import ProjectFileParser

    with open(os.path.join(FIXTURES, name)) as handle:
        text = handle.read()
    noise = io.StringIO()
    with contextlib.redirect_stderr(noise), contextlib.redirect_stdout(noise):
        project = ProjectFileParser().parse(text)

    zone = project["timezone"]
    schedule: dict[str, tuple[str, str]] = {}
    for task in project.tasks:
        start, end = task.get("start", 0), task.get("end", 0)
        if start and end:
            schedule[task.fullId] = (
                from_utc(start, zone).strftime(TIME_FORMAT),
                from_utc(end, zone).strftime(TIME_FORMAT),
            )
    return schedule


def _differences(expected: dict[str, list[str]], actual: dict[str, tuple[str, str]]) -> list[str]:
    found = []
    for task_id, window in sorted(expected.items()):
        now = actual.get(task_id)
        if now is None:
            found.append(f"{task_id} no longer schedules (was {window[0]} -> {window[1]})")
        elif list(now) != window:
            found.append(f"{task_id} was {window[0]} -> {window[1]}, now {now[0]} -> {now[1]}")
    return found


@probe("Every example project still schedules every task it used to")
def probe_no_project_stopped_scheduling() -> tuple[bool, str]:
    baseline = _load_baseline()
    missing: list[str] = []
    for name, expected in sorted(baseline.items()):
        actual = _current(name)
        gone = [task_id for task_id in expected if task_id not in actual]
        if gone:
            missing.append(f"{name}: {gone[:5]}")
    return not missing, (
        f"{len(baseline)} projects checked; "
        + ("every task still schedules" if not missing else f"tasks lost: {missing}")
    )


@probe("Only the projects with a recorded reason schedule differently")
def probe_only_expected_projects_changed() -> tuple[bool, str]:
    baseline = _load_baseline()
    unchanged, changed = [], {}
    for name, expected in sorted(baseline.items()):
        diffs = _differences(expected, _current(name))
        if diffs:
            changed[name] = diffs
        else:
            unchanged.append(name)

    unexpected = sorted(set(changed) - set(EXPECTED_CHANGES))
    vanished = sorted(set(EXPECTED_CHANGES) - set(changed))

    lines = [f"{len(unchanged)} of {len(baseline)} projects schedule exactly as before."]
    for name in sorted(changed):
        reason = EXPECTED_CHANGES.get(name, "NO RECORDED REASON")
        lines.append(f"  {name}: {len(changed[name])} task(s) differ -- {reason[:90]}...")
    if unexpected:
        lines.append(f"  UNEXPECTED: {unexpected}")
        for name in unexpected:
            lines.extend(f"      {d}" for d in changed[name][:6])
    if vanished:
        lines.append(f"  expected to differ but no longer does: {vanished}")

    return not unexpected and not vanished, "\n".join(lines)


@probe("airport_stress_test moves only the two starts that preceded a free electrician")
def probe_airport_starts_follow_the_electrician() -> tuple[bool, str]:
    """Each moved start is the moment e1 finished the task before it, nothing else."""
    baseline = _load_baseline()["airport_stress_test.tjp"]
    actual = _current("airport_stress_test.tjp")
    diffs = _differences(baseline, actual)
    moved = {d.split(" ")[0] for d in diffs}
    follows = (
        actual["airport.t_install"][0] == actual["airport.t_crit"][1]
        and actual["airport.t_low"][0] == actual["airport.t_install"][1]
    )
    ends_kept = all(actual[t][1] == baseline[t][1] for t in ("airport.t_install", "airport.t_low"))
    ok = moved == {"airport.t_install", "airport.t_low"} and follows and ends_kept
    return ok, f"moved {sorted(moved)}; t_crit {actual['airport.t_crit']}, t_install {actual['airport.t_install']}, t_low {actual['airport.t_low']}"


@probe("The delivery tasks in jit_supply are untouched by its reference fix")
def probe_jit_supply_delivery_unchanged() -> tuple[bool, str]:
    """The corrected reference must move only the milestone it gates."""
    baseline = _load_baseline()["jit_supply.tjp"]
    actual = _current("jit_supply.tjp")
    delivery = {k: v for k, v in baseline.items() if k.startswith("delivery")}
    diffs = _differences(delivery, actual)
    return not diffs, (
        f"{len(delivery)} delivery tasks compared; "
        + ("all unchanged" if not diffs else f"changed: {diffs}")
    )


@probe("The projects that now finish sooner do so because effort is shared")
def probe_shared_effort_finishes_sooner() -> tuple[bool, str]:
    """A schedule that moved must have moved earlier, not later."""
    from datetime import datetime

    baseline = _load_baseline()
    report = []
    ok = True
    for name in ("simple.tjp", "tutorial.tjp"):
        expected, actual = baseline[name], _current(name)
        was = max(datetime.strptime(w[1], TIME_FORMAT) for w in expected.values())
        now = max(
            datetime.strptime(w[1], TIME_FORMAT)
            for task_id, w in actual.items()
            if task_id in expected
        )
        earlier = now < was
        ok = ok and earlier
        report.append(f"{name}: finished {was}, now {now} ({'earlier' if earlier else 'NOT earlier'})")
    return ok, "; ".join(report)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
