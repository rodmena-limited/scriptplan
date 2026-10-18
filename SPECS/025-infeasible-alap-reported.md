# Infeasible ALAP is reported as running outside the window, and a task is booked after its successor (trace #6)

**Ticket**: issuedb #25  
**Status**: closed (released in 0.10.2)  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 25` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d over AgentBus (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M563GAHBQ5BMGWRYVCEQHCCB, platform_attested), reproduced here on 0.10.1 from PyPI with its TJP d06. EVIDENCE: plan alap, g end Mon 12:00, a 240min, b 480min after a -> exit 2 with 'Task g.b ... ran outside the project window', and g.a is degraded to ASAP with alap_degraded and booked 12:00-16:00, after the deadline its successor failed to meet. EARS: R1 (event) When a backward task cannot fit before the moment it must end, ScriptPlan shall say which moment that is and that there is not enough working time before it. R2 (unwanted) If a backward task's successor could not be scheduled, then ScriptPlan shall report the task as unschedulable because of that successor, and shall not degrade it to ASAP. SYNTHESIS: move stall handling out of project.py (519 lines, over the 500 soft cap) into scheduler/stalls.py and fix it there.

---

DONE: scheduler/stalls.py (moved out of project.py, now 481 lines). A backward runaway names its deadline; a backward task whose successor failed is reported ('its successor g.b could not be scheduled') and not degraded or booked. d06 exits 2 with both messages and no alap_degraded warning. test_an_alap_deadline_too_early_names_the_deadline_not_the_window.

---

VERIFIED on 0.10.2 from PyPI (3.13.7): d06 exits 2 naming the deadline 2026-11-02 12:00:00 for g.b and 'its successor g.b could not be scheduled' for g.a; no alap_degraded warning and nothing booked after the deadline.

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.
