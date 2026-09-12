#!/usr/bin/env python3
"""Falsifies: "a report does what its definition says".

Claims under test (SPECS/008-ws6-reports-honour-their-definitions.md):
  - sorttasks orders the rows
  - hidetask hides only the matching rows
  - a duration column reports elapsed scheduled time
  - an unimplemented format is rejected rather than silently producing nothing
"""

from __future__ import annotations

from harness import HDR, main, parse, probe

BASE = HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
"""


def _rows(project) -> list[dict]:
    report = next(iter(project.reports))
    report.generate_intermediate_format()
    if not report.content or not hasattr(report.content, "table"):
        return []
    return report.content.table.to_json().get("data", [])


@probe("sorttasks name.down orders rows by name descending")
def probe_sorttasks_descending() -> tuple[bool, str]:
    project = parse(BASE + """
task a "Alpha" { start 2025-01-06 effort 1h allocate r }
task b "Bravo" { start 2025-01-06 effort 1h allocate r }
taskreport t "t" { formats csv columns id, name sorttasks name.down }
""")
    ids = [row.get("id") for row in _rows(project)]
    return ids == ["b", "a"], f"row ids = {ids} (expected ['b', 'a'] for name descending)"


@probe("sorttasks name.up orders rows by name ascending")
def probe_sorttasks_ascending() -> tuple[bool, str]:
    project = parse(BASE + """
task b "Bravo" { start 2025-01-06 effort 1h allocate r }
task a "Alpha" { start 2025-01-06 effort 1h allocate r }
taskreport t "t" { formats csv columns id, name sorttasks name.up }
""")
    ids = [row.get("id") for row in _rows(project)]
    return ids == ["a", "b"], f"row ids = {ids} (expected ['a', 'b'] for name ascending)"


@probe("hidetask hides only the rows the expression matches")
def probe_hidetask_filters() -> tuple[bool, str]:
    project = parse(BASE + """
task a "Alpha" { start 2025-01-06 effort 1h allocate r }
task b "Bravo" { start 2025-01-06 effort 1h allocate r flags done }
taskreport t "t" { formats csv columns id, name hidetask done }
""")
    ids = [row.get("id") for row in _rows(project)]
    return ids == ["a"], f"row ids = {ids} (expected ['a'] - only the task flagged 'done' is hidden)"


@probe("A duration column reports the elapsed scheduled time")
def probe_duration_column() -> tuple[bool, str]:
    project = parse(BASE + """
task a "Alpha" { start 2025-01-06 effort 8h allocate r }
taskreport t "t" { formats csv columns id, start, end, duration }
""")
    rows = _rows(project)
    values = [row.get("duration") for row in rows]
    non_zero = [v for v in values if v not in (None, "", 0, "0", "-")]
    return bool(non_zero), f"duration column values = {values} (an 8h task must not report 0)"


@probe("A report format ScriptPlan cannot produce is rejected, not silently empty")
def probe_unimplemented_format_rejected() -> tuple[bool, str]:
    try:
        parse(BASE + """
task a "Alpha" { start 2025-01-06 effort 1h allocate r }
taskreport t "t" { formats ical columns id, start, end }
""")
    except Exception as exc:
        return True, f"raised {type(exc).__name__}: {str(exc)[:160]}"
    return False, "an 'ical' report was accepted; it writes no file and the CLI then blames scheduling"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
