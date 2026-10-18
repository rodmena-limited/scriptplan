# A declared end on an ASAP task, or its parent, is exceeded silently (trace #3)

**Ticket**: issuedb #21  
**Status**: closed (released in 0.10.2)  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 21` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d over AgentBus (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M563GAHBQ5BMGWRYVCEQHCCB, platform_attested), reproduced here on 0.10.1 from PyPI with its TJP d03. EVIDENCE: b effort 480min, end 2026-11-03-10:00 -> b ends 13:00, exit 0. The reference scheduler refuses the plan. EARS: R1 (unwanted) If a task scheduled as soon as possible, or a container, ends after the end the file states for it, then ScriptPlan shall report an error naming the task, the stated end and the end it reached, and exit non-zero. R2 (ubiquitous) A run of the same plan twice shall compare against the stated end, not the end a previous run wrote back. SYNTHESIS (localised): the after-scheduling checks (postcheck), with the stated end kept apart from the written one as for the stated start (#14).

---

DONE: core/declared_dates.py keeps stated start/end apart from written values; postcheck _check_stated_dates raises end_violated. d03 (task end) and the parent-end variant now exit 2: "Task 'g.b' must end by 2026-11-03 10:00:00, the end the file states for it, but its work ends at 2026-11-03 13:00:00." Feasible variant (end 17:30) schedules. tests/test_stated_dates.py.

---

VERIFIED on 0.10.2 from PyPI (3.13.7): trace d03 exits 2 'Task g.b must end by 2026-11-03 10:00:00 ... its work ends at 2026-11-03 13:00:00'; feasible variant kept (tests/test_stated_dates.py).

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.
