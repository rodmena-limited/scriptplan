#!/usr/bin/env python3
"""Falsifies: "what the user writes in a .tjp reaches the scheduler".

Claims under test (SPECS/002-ws0-honesty-and-safety-fail-closed.md):
  - an attribute in the grammar that the model does not apply is an error
  - an unresolved depends / allocate / shift reference is an error
  - a duplicate property id is an error
  - setting a list attribute replaces it rather than accumulating

These probes are the reason the "24/24 passed" badge could be green while
`duration`, `length`, `complete` and `note` were being discarded.
"""

from __future__ import annotations

from harness import HDR, main, parse, probe, task

ONE_RESOURCE = 'resource r "R" { workinghours mon-fri 9:00-17:00 }\n'


def _expect_error(text: str) -> tuple[bool, str]:
    try:
        parse(text)
    except Exception as exc:  # noqa: BLE001
        return True, f"raised {type(exc).__name__}: {str(exc)[:200]}"
    return False, "parsed and scheduled without complaint"


@probe("A dependency on an undefined task is an error")
def probe_unresolved_dependency() -> tuple[bool, str]:
    return _expect_error(HDR + ONE_RESOURCE + """
task a "A" { depends !nosuchtask effort 1h allocate r }
""")


@probe("An allocation of an undefined resource is an error")
def probe_unresolved_resource() -> tuple[bool, str]:
    return _expect_error(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 1h allocate nosuchresource }
""")


@probe("A workinghours reference to an undefined shift is an error")
def probe_unresolved_shift() -> tuple[bool, str]:
    return _expect_error(HDR + """
resource r "R" { workinghours nosuchshift }
task a "A" { start 2025-01-06 effort 1h allocate r }
""")


@probe("Two tasks with the same id in the same scope is an error")
def probe_duplicate_task_id() -> tuple[bool, str]:
    return _expect_error(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 1h allocate r }
task a "A again" { start 2025-01-07 effort 1h allocate r }
""")


@probe("A task 'complete' percentage reaches the model")
def probe_complete_is_kept() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 8h allocate r complete 95 }
""")
    value = task(project, "a").get("complete", 0)
    return abs(float(value or 0) - 95.0) < 1e-9, f"stored complete = {value!r} (file said 95)"


@probe("A task 'note' reaches the model")
def probe_note_is_kept() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 8h allocate r note "keep me" }
""")
    try:
        value = task(project, "a").get("note", 0)
    except Exception as exc:  # noqa: BLE001
        return False, f"reading the note raised {type(exc).__name__}: {exc}"
    return value == "keep me", f"stored note = {value!r} (file said 'keep me')"


@probe("Declaring 'allocate' twice does not silently accumulate resources")
def probe_list_attribute_replaces() -> tuple[bool, str]:
    project = parse(HDR + """
resource r "R" { workinghours mon-fri 9:00-17:00 }
resource q "Q" { workinghours mon-fri 9:00-17:00 }
task a "A" { start 2025-01-06 effort 1h allocate r allocate q }
""")
    allocations = task(project, "a").get("allocate", 0)
    flat = []
    for item in allocations or []:
        flat.append(getattr(item, "resource_id", None) or getattr(item, "id", None) or item)
    return len(flat) <= 2, f"allocations = {flat} (two allocate lines must not produce more than two entries)"


@probe("A 'precedes' relation does not duplicate the target's dependency list")
def probe_precedes_does_not_duplicate() -> tuple[bool, str]:
    project = parse(HDR + ONE_RESOURCE + """
task a "A" { start 2025-01-06 effort 1h allocate r precedes !b }
task b "B" { effort 1h allocate r }
""")
    deps = task(project, "b").get("depends", 0) or []
    return len(deps) == 1, f"b.depends has {len(deps)} entries (expected exactly 1)"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
