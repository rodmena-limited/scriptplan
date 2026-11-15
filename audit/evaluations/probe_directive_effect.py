#!/usr/bin/env python3
"""Falsifies: "a directive the parser accepts is never silently ignored".

0.10.2 parsed a project's ``workinghours`` and a shift's ``leaves``, stored
them, and never read them (issuedb #35). No test could notice, because no
fixture used either. This probe closes that hole from the other side:

  - every directive the grammar accepts in a project, shift, resource or task
    block, and every dependency, allocation and limit option, is classified
    here, either with a pair of projects that differ only in that directive, or
    with the reason it has no bearing on dates;
  - for each pair the schedules must differ ("moves"), the directive must be
    refused with an error ("refuses"), or it must draw a warning ("warns");
  - a directive that is in the grammar and not classified here fails the probe,
    so a new one cannot be added without saying what it does.

A pair shows that the directive is read. Whether it is read correctly is the
business of the other probes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from harness import _message_handler, main, parse, probe

HEAD = 'project p "P" 2025-01-06 +3m {{\n  timezone "Etc/UTC"\n  now 2025-01-06\n  {project}\n}}\n'
DESK = 'resource r "R" { workinghours mon - fri 9:00 - 17:00 }\n'


def plan(body: str, project: str = "", top: str = "") -> str:
    return HEAD.format(project=project) + top + body


# directive -> (kind, without, with). "moves": both schedule, dates differ.
# "refuses": the first schedules and the second is an error. "warns": both
# schedule and only the second prints a warning.
PAIRS: dict[str, tuple[str, str, str]] = {
    # ---- project block
    "timezone": (
        "moves",
        plan('resource r "R" {}\ntask t "T" { effort 8h allocate r }\n'),
        plan('resource r "R" {}\ntask t "T" { effort 8h allocate r }\n').replace("Etc/UTC", "America/New_York"),
    ),
    "dailyworkinghours": (
        "moves",
        plan(DESK + 'task t "T" { effort 2d allocate r }\n'),
        plan(DESK + 'task t "T" { effort 2d allocate r }\n', "dailyworkinghours 6"),
    ),
    "yearlyworkingdays": (
        "moves",
        plan(DESK + 'task t "T" { effort 1m allocate r }\n'),
        plan(DESK + 'task t "T" { effort 1m allocate r }\n', "yearlyworkingdays 120"),
    ),
    "workinghours": (
        "moves",
        plan('task t "T" { length 6d }\n'),
        plan('task t "T" { length 6d }\n', "workinghours mon - sat 9:00 - 17:00"),
    ),
    "project_scheduling": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r }\n', "scheduling alap"),
    ),
    # ---- global
    "leaves_global": (
        "moves",
        plan('task t "T" { length 3d }\n'),
        plan('task t "T" { length 3d }\n', top='leaves holiday "H" 2025-01-07\n'),
    ),
    "vacation_global": (
        "moves",
        plan('task t "T" { length 3d }\n'),
        plan('task t "T" { length 3d }\n', top='vacation "H" 2025-01-07\n'),
    ),
    # ---- shift block
    "shift_workinghours": (
        "moves",
        plan('shift s "S" { workinghours mon - fri 9:00 - 17:00 }\nresource r "R" { workinghours s }\n'
             'task t "T" { effort 16h allocate r }\n'),
        plan('shift s "S" { workinghours mon - fri 9:00 - 13:00 }\nresource r "R" { workinghours s }\n'
             'task t "T" { effort 16h allocate r }\n'),
    ),
    "shift_leaves": (
        "moves",
        plan('shift s "S" { workinghours mon - fri 9:00 - 17:00 }\nresource r "R" { workinghours s }\n'
             'task t "T" { effort 16h allocate r }\n'),
        plan('shift s "S" { workinghours mon - fri 9:00 - 17:00 leaves holiday 2025-01-07 }\n'
             'resource r "R" { workinghours s }\ntask t "T" { effort 16h allocate r }\n'),
    ),
    # ---- resource block
    "resource_efficiency": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK.replace(" }", " efficiency 2.0 }") + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "resource_limits": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK.replace(" }", " limits { dailymax 4h } }") + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "resource_leaves": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK.replace(" }", " leaves annual 2025-01-07 }") + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "resource_vacation": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK.replace(" }", " vacation 2025-01-07 }") + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "resource_booking": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK.replace(" }", ' booking "Away" 2025-01-06-09:00 +4h }') + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "resource_workinghours": (
        "moves",
        plan('resource r "R" {}\ntask t "T" { effort 16h allocate r }\n'),
        plan('resource r "R" { workinghours mon - fri 9:00 - 13:00 }\ntask t "T" { effort 16h allocate r }\n'),
    ),
    "resource_timezone": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK.replace(" }", ' timezone "Asia/Tokyo" }') + 'task t "T" { effort 8h allocate r }\n'),
    ),
    "resource": (  # a resource inside a resource: allocating the group books its members
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan('resource r "R" {\n  resource a "A" { workinghours mon - fri 9:00 - 17:00 }\n'
             '  resource b "B" { workinghours mon - fri 9:00 - 17:00 }\n}\ntask t "T" { effort 16h allocate r }\n'),
    ),
    # ---- task block
    "task_start": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r start 2025-01-08 }\n'),
    ),
    "task_end": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r scheduling alap }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r scheduling alap end 2025-01-10-17:00 }\n'),
    ),
    "task_effort": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
    ),
    "task_duration": (
        "moves",
        plan('task t "T" { duration 1d }\n'),
        plan('task t "T" { duration 3d }\n'),
    ),
    "task_length": (
        "moves",
        plan('task t "T" { length 1d }\n'),
        plan('task t "T" { length 3d }\n'),
    ),
    "task_milestone": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { depends a duration 1d }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { depends a milestone }\n'),
    ),
    "task_depends": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a }\n'),
    ),
    "task_precedes": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d }\n'),
        plan('task a "A" { duration 2d precedes t }\ntask t "T" { duration 1d }\n'),
    ),
    "task_allocate": (  # a duration task holds the desk it allocates
        "moves",
        plan(DESK + 'task a "A" { effort 8h allocate r }\ntask t "T" { duration 4h start 2025-01-06-09:00 }\n'),
        plan(DESK + 'task a "A" { effort 8h allocate r }\n'
             'task t "T" { duration 4h start 2025-01-06-09:00 allocate r priority 900 }\n'),
    ),
    "task_priority": (
        "moves",
        plan(DESK + 'task a "A" { effort 8h allocate r }\ntask t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task a "A" { effort 8h allocate r }\ntask t "T" { effort 8h allocate r priority 900 }\n'),
    ),
    "task_limits": (
        "moves",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 16h allocate r limits { dailymax 4h } }\n'),
    ),
    "task_scheduling": (
        "moves",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r scheduling alap }\n'),
    ),
    "task_maxend": (
        "refuses",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 16h allocate r maxend 2025-01-06-17:00 }\n'),
    ),
    "task_maxstart": (
        "refuses",
        plan(DESK + 'task t "T" { effort 16h allocate r start 2025-01-08 }\n'),
        plan(DESK + 'task t "T" { effort 16h allocate r start 2025-01-08 maxstart 2025-01-07 }\n'),
    ),
    "task_minend": (
        "refuses",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r minend 2025-01-10 }\n'),
    ),
    "task_minstart": (
        "refuses",
        plan(DESK + 'task t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 8h allocate r minstart 2025-01-08 }\n'),
    ),
    "task": (  # a task inside a task: a container's dependency holds for its children
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d }\n'),
        plan('task a "A" { duration 2d }\ntask g "G" {\n  depends a\n  task t "T" { duration 1d }\n}\n'),
    ),
    # ---- dependency options
    "dep_gapduration": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { gapduration 1d } }\n'),
    ),
    "dep_gaplength": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { gaplength 1d } }\n'),
    ),
    "dep_maxgapduration": (
        "refuses",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a start 2025-01-20 }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { maxgapduration 1d } start 2025-01-20 }\n'),
    ),
    "dep_onstart": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { onstart } }\n'),
    ),
    "dep_onend": (
        "moves",
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { onstart } }\n'),
        plan('task a "A" { duration 2d }\ntask t "T" { duration 1d depends a { onend } }\n'),
    ),
    # ---- allocation options
    "alloc_mandatory": (
        "moves",
        plan(DESK + 'resource s "S" { workinghours mon - fri 13:00 - 17:00 }\ntask t "T" { effort 16h allocate r, s }\n'),
        plan(DESK + 'resource s "S" { workinghours mon - fri 13:00 - 17:00 }\n'
             'task t "T" { effort 16h allocate r, s { mandatory } }\n'),
    ),
    "alloc_alternative": (
        "moves",
        plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
             'task a "A" { effort 8h allocate r priority 900 }\ntask t "T" { effort 8h allocate r }\n'),
        plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
             'task a "A" { effort 8h allocate r priority 900 }\ntask t "T" { effort 8h allocate r { alternative s } }\n'),
    ),
    "alloc_persistent": (
        "moves",
        plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
             'task a "A" { effort 4h allocate r priority 900 start 2025-01-06-13:00 }\n'
             'task t "T" { effort 12h allocate r { alternative s } }\n'),
        plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
             'task a "A" { effort 4h allocate r priority 900 start 2025-01-06-13:00 }\n'
             'task t "T" { effort 12h allocate r { alternative s persistent } }\n'),
    ),
    "alloc_limits": (  # never applied before 0.10.3, and refused since (issuedb #39)
        "refuses",
        plan(DESK + 'task t "T" { effort 16h allocate r }\n'),
        plan(DESK + 'task t "T" { effort 16h allocate r { limits { dailymax 4h } } }\n'),
    ),
}

# One pair per limit: each must change what a 40-hour task on a full week books.
for _limit, _amount in (("dailymax", "4h"), ("weeklymax", "16h"), ("monthlymax", "24h"), ("maximum", "24h")):
    PAIRS[f"limit_{_limit}"] = (
        "moves" if _limit != "maximum" else "refuses",
        plan(DESK + 'task t "T" { effort 40h allocate r }\n'),
        plan(DESK.replace(" }", f" limits {{ {_limit} {_amount} }} }}") + 'task t "T" { effort 40h allocate r }\n'),
    )
for _limit, _amount in (("dailymin", "6h"), ("weeklymin", "30h"), ("monthlymin", "100h"), ("minimum", "100h")):
    PAIRS[f"limit_{_limit}"] = (
        "warns",
        plan(DESK + 'task t "T" { effort 4h allocate r }\n'),
        plan(DESK.replace(" }", f" limits {{ {_limit} {_amount} }} }}") + 'task t "T" { effort 4h allocate r }\n'),
    )
PAIRS["limits_resources"] = (
    "moves",
    plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
         'task t "T" { effort 32h allocate r, s limits { dailymax 4h } }\n'),
    plan(DESK + 'resource s "S" { workinghours mon - fri 9:00 - 17:00 }\n'
         'task t "T" { effort 32h allocate r, s limits { dailymax 4h { resources r } } }\n'),
)

# Accepted, and by design without a bearing on dates. The reason is the claim.
NO_DATE_EFFECT: dict[str, str] = {
    "timeformat": "how reports print dates",
    "numberformat": "how reports print numbers",
    "currencyformat": "how reports print money",
    "currency": "the unit money is reported in",
    "now": "the report date; tasks are scheduled from the project start",
    "scenario_def": "declares a scenario; its dates come from scenario attributes",
    "extend": "declares a custom attribute",
    "weekstartsmonday": "states the default: weekly limits already count Monday to Sunday (checked below)",
    "timingresolution": "slot size; effort is booked to the minute at any size (probe_precision)",
    "copyright": "text",
    "rate": "cost of a resource's time",
    "flags_global": "declares flag names",
    "balance": "names the accounts a balance is reported between",
    "resource_email": "contact detail",
    "resource_rate": "cost of the resource's time",
    "resource_managers": "reporting line",
    "resource_chargeset": "accounts are parsed but not modelled (README, known limits)",
    "resource_flags": "report filters",
    "extended_attr": "custom attribute value",
    "task_responsible": "who answers for the task",
    "task_complete": "progress, shown in reports",
    "task_note": "text",
    "task_chargeset": "accounts are parsed but not modelled (README, known limits)",
    "task_purge_chargeset": "accounts are parsed but not modelled (README, known limits)",
    "task_charge": "accounts are parsed but not modelled (README, known limits)",
    "task_journalentry": "journal text",
    "task_flags": "report filters",
    "scenario_attr": "sets an attribute in one scenario; covered by the attribute's own pair",
    "alloc_select": "which of several free resources is preferred; dates differ only when candidates differ",
}

EFFECT = {"moves": "the schedule changes", "refuses": "the file is refused", "warns": "a warning is printed"}

GRAMMAR_LISTS = ("project_attribute", "global_attribute", "resource_attr", "task_attr", "limit_attr")


def grammar_directives() -> set[str]:
    """Every alternative of the grammar's attribute lists, by rule name."""
    import scriptplan

    text = (Path(scriptplan.__file__).parent / "parser" / "tjp.lark").read_text()
    found: set[str] = set()
    for rule in GRAMMAR_LISTS:
        body = re.search(rf"^{rule}:(.*?)(?=^\S)", text, re.M | re.S)
        if body is None:
            raise AssertionError(f"grammar has no rule {rule!r}")
        for alternative in body.group(1).split("|"):
            found.update(re.findall(r"\b[a-z_]+\b", alternative.split("//")[0]))
    found |= set(re.findall(r"->\s*((?:dep|alloc)_[a-z]+)", text))
    found |= {"shift_workinghours", "shift_leaves", "limits_resources"}
    return found


def outcome(tjp: str) -> tuple[str, Any]:
    """("scheduled", dates) or ("refused", message)."""
    handler = _message_handler()
    handler.clear()
    try:
        project = parse(tjp)
    except Exception as exc:
        return "refused", f"{type(exc).__name__}: {exc}"[:160]
    if handler.errors:
        return "refused", f"{handler.errors} error(s)"
    dates = {t.fullId: (t.get("start", 0), t.get("end", 0)) for t in project.tasks if t.leaf()}
    warnings = sum("Warning" in str(m) for m in handler.messages)
    return "scheduled", (dates, warnings)


@probe("Every directive the grammar accepts is classified: it moves dates, is refused, or is said not to")
def probe_every_directive_is_classified() -> tuple[bool, str]:
    grammar = grammar_directives()
    classified = set(PAIRS) | set(NO_DATE_EFFECT)
    unclassified = sorted(grammar - classified)
    stale = sorted(classified - grammar)
    both = sorted(set(PAIRS) & set(NO_DATE_EFFECT))
    ok = not unclassified and not stale and not both
    return ok, (
        f"{len(grammar)} directives in the grammar; {len(PAIRS)} with a pair, {len(NO_DATE_EFFECT)} without effect on "
        f"dates; unclassified {unclassified}; no longer in the grammar {stale}; classified twice {both}"
    )


@probe("A weekly limit counts Monday to Sunday, which is what weekstartsmonday states")
def probe_week_starts_on_monday() -> tuple[bool, str]:
    text = (
        'project p "P" 2025-01-04 +3m {{ timezone "Etc/UTC" now 2025-01-04 {flag} }}\n'
        'resource r "R" {{ workinghours mon - sun 9:00 - 17:00 limits {{ weeklymax 16h }} }}\n'
        'task t "T" {{ effort 32h allocate r }}\n'
    )
    # Saturday and Sunday fill one week's 16 hours; Monday and Tuesday the next.
    ends = [outcome(text.format(flag=flag))[1][0]["t"][1] for flag in ("", "weekstartsmonday")]
    ok = all(f"{end:%Y-%m-%d %H:%M}" == "2025-01-07 17:00" for end in ends)
    return ok, f"ends without and with the directive: {[f'{end:%Y-%m-%d %H:%M}' for end in ends]} (expected 2025-01-07 17:00)"


def _shown(result: tuple[str, Any]) -> str:
    if result[0] != "scheduled":
        return str(result[1])
    dates, warnings = result[1]
    text = str({k: tuple(f"{d:%m-%d %H:%M}" if d else "-" for d in v) for k, v in dates.items()})
    return text + (f" and {warnings} warning(s)" if warnings else "")


def _pair_probe(name: str, kind: str, without: str, with_: str) -> Any:
    @probe(f"{name}: {EFFECT[kind]} when it is added")
    def check() -> tuple[bool, str]:
        before, after = outcome(without), outcome(with_)
        if before[0] != "scheduled":
            return False, f"the project without it did not schedule: {before[1]}"
        if kind == "moves":
            ok = after[0] == "scheduled" and after[1][0] != before[1][0]
        elif kind == "warns":
            ok = after[0] == "scheduled" and before[1][1] == 0 and after[1][1] > 0
        else:
            ok = after[0] == "refused"
        return ok, f"without {_shown(before)}; with {_shown(after)}"

    check.__name__ = f"probe_{name}"
    return check


for _name, (_kind, _without, _with) in PAIRS.items():
    globals()[f"probe_{_name}"] = _pair_probe(_name, _kind, _without, _with)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
