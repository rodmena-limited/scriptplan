#!/usr/bin/env python3
"""Falsifies: "backward scheduling respects the project the user declared".

Claims under test (SPECS/005-ws3-scheduler-core-engine-package.md):
  - the declared project end is never rewritten
  - an ALAP task with no end constraint ends at the declared project end
  - a chain that mixes ASAP and ALAP tasks schedules instead of deadlocking
  - an ALAP chain packs against its anchor
  - a maxgapduration that cannot be met is reported
"""

from __future__ import annotations

from harness import datetime, main, parse, probe, timedelta, window

SHORT_PROJECT = """project p "P" 2025-01-06 +2w {
  timezone "Etc/UTC"
  now 2025-01-06
}
resource r "R" { workinghours mon-fri 9:00-17:00 }
"""

HDR3M = """project p "P" 2025-01-06 +3m {
  timezone "Etc/UTC"
  now 2025-01-06
}
resource r "R" { workinghours mon-fri 9:00-17:00 }
"""


@probe("The declared project end is not rewritten by scheduling")
def probe_project_end_is_not_moved() -> tuple[bool, str]:
    project = parse(SHORT_PROJECT + """
task a "A" { start 2025-01-06 effort 5d allocate r }
task z "Z" { scheduling alap effort 1d allocate r }
""", schedule=False)
    declared = project["end"]
    project.schedule()
    return project["end"] == declared, f"declared end={declared} end after scheduling={project['end']}"


@probe("An ALAP task with no successor ends at the declared project end")
def probe_alap_uses_declared_end() -> tuple[bool, str]:
    project = parse(SHORT_PROJECT + """
task a "A" { start 2025-01-06 effort 1d allocate r }
task z "Z" { scheduling alap effort 1d allocate r }
""")
    start, end = window(project, "z")
    declared = project["end"]
    ok = end is not None and (declared - end) < timedelta(days=3)
    return ok, f"ALAP task z={start} -> {end}; declared project end={declared}"


@probe("An ALAP chain packs backwards against its anchor")
def probe_alap_chain_packs() -> tuple[bool, str]:
    project = parse(HDR3M + """
task a "A" { effort 8h allocate r }
task b "B" { depends !a scheduling alap end 2025-01-31-17:00 effort 8h allocate r }
""")
    a_win, b_win = window(project, "a"), window(project, "b")
    ok = (
        b_win == (datetime(2025, 1, 31, 9, 0), datetime(2025, 1, 31, 17, 0))
        and a_win == (datetime(2025, 1, 30, 9, 0), datetime(2025, 1, 30, 17, 0))
    )
    return ok, f"a={a_win} b={b_win} (b anchored Fri 31st; a must sit on Thu 30th)"


@probe("A chain mixing an ALAP predecessor with an ASAP successor schedules")
def probe_mixed_direction_chain() -> tuple[bool, str]:
    project = parse(HDR3M + """
task a "A" { scheduling alap effort 8h allocate r }
task b "B" { depends !a effort 8h allocate r }
""", schedule=False)
    result = project.schedule()
    a_win, b_win = window(project, "a"), window(project, "b")
    ok = result is not False and None not in a_win and None not in b_win and b_win[0] >= a_win[1]
    return ok, f"schedule()={result}; a={a_win} b={b_win} (both must be placed, b after a)"


@probe("A maxgapduration that cannot be met is reported")
def probe_maxgap_violation_reported() -> tuple[bool, str]:
    from scriptplan.utils.message_handler import get_message_handler_instance

    handler = get_message_handler_instance()
    handler.clear()
    project = parse(HDR3M + """
resource q "Q" { workinghours mon-fri 9:00-17:00 }
task busy "Busy" { start 2025-01-06 effort 5d allocate q priority 900 }
task a "A" { start 2025-01-06 effort 2h allocate r }
task b "B" { depends !a { maxgapduration 1h } effort 2h allocate q }
""")
    _, a_end = window(project, "a")
    b_start, _ = window(project, "b")
    gap = b_start - a_end if (b_start and a_end) else None
    texts = [str(m) for m in handler.messages]
    honoured = gap is not None and gap <= timedelta(hours=1)
    reported = any("gap" in t.lower() for t in texts)
    return honoured or reported, f"gap achieved={gap} (limit 1h); messages={texts}"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
