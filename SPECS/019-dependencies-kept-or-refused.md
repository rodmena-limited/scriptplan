# A declared start that conflicts with a dependency is scheduled anyway, silently

**Ticket**: issuedb #19  
**Status**: in-progress  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 19` whenever the spec or the chosen
alternative changes.

---

Found while writing the mixed-plan fuzz for #16. Present in 0.10.0, 0.10.1 and the 0.10.2 tree.

EVIDENCE (gaps/start_and_dep.tjp, R=60): a effort 3h on r0 -> 09:00-12:00; b `start 2026-10-19-10:00 depends a effort 1h allocate r1` -> b 10:00-11:00, two hours before a ends. No warning, exit 0. The hour-level reference scheduler refuses the file: "Task b must start after end of task a. This condition could not be met."

EARS SPEC:
- R1 (unwanted) If a finished schedule has a task starting before a predecessor ends (plus its gapduration or gaplength), then ScriptPlan shall report an error naming both tasks, both dates and the gap required, and the CLI shall exit non-zero.
- R2 (unwanted) If a task's declared start conflicts with a dependency, then that error shall say so.
- R3 (ubiquitous) Schedules that keep every dependency (all 24 showcase projects and all edge cases) shall be unaffected.
SYNTHESIS (localised): domain = the after-scheduling checks (scheduler/postcheck.py), the same place maxgap and min/max dates are verified. Alternatives: verify every dependency after scheduling [CHOSEN: fails closed on this conflict and on any placement defect that breaks a dependency, which is the class of bug 0.10.1 shipped] vs move a declared start later to satisfy the dependency [REJECTED: silently overrides a date the file states] vs only check tasks that declare a start [REJECTED: narrower than the defect class].

---

SCOPE ADDED: the new dependency check exposed that a backward task bounded by a successor ignored the gap that successor's dependency asks for (c alap duration 1h; d start Tue 15:00 depends c { gapduration 2h } -> c ended 15:00). Fixed with task_dependencies.latest_end_for (start minus gapduration, or retreat_working_time for gaplength). Verified: c 12:00-13:00; gaplength 3h before Tue 11:00 -> e ends Mon 16:00. Edge case examples/edge_cases/alap_keeps_successor_gaps fails on 0.10.0 and 0.10.1, passes now. Conflict case: plan exits 2 naming both tasks and both dates; the same plan with start 12:00 is accepted. No example project trips the check (41 checked).

---

EXTENDED (trace defect 13, message 01M567JDJQ4N4RR0GN1ZW07VSN): an OWN start that contradicts a dependency is refused (main, gapduration and milestone variants all exit 2, as the hour-level reference scheduler does: 'must start after end ... could not be met'). A start INHERITED from a container is an earliest start: task_placement.own_start() returns only a start provided on the task; an inherited one enters the earliest-start computation as a lower bound with the dependencies. Verified against the reference scheduler: parent-start variant g Mon 10:00-Tue 10:00, a Mon 10:00-Tue 09:00, b Tue 09:00-10:00, identical. Edge case inherited_start_waits_for_dependency (fails on 0.10.1); tests for the milestone and gap variants.
