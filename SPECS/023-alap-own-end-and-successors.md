# An ALAP task with its own end ignores its successors (trace #9)

**Ticket**: issuedb #23  
**Status**: closed (released in 0.10.2)  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 23` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d over AgentBus (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M563GAHBQ5BMGWRYVCEQHCCB, platform_attested), reproduced here on 0.10.1 from PyPI with its TJP d09. EVIDENCE: plan alap, g end Fri 17:30, a end Fri 12:00, b depends a -> a Thu 17:00-Fri 12:00 while b runs Thu 13:00-Fri 17:30 (b starts before a ends); exit 0. The 0.10.2 tree now refuses it (#19), but it is feasible: a can end before b starts. EARS: R1 (ubiquitous) A backward task shall end no later than the earliest of its own stated end and its backward successors' starts (less gaps). R2 (state) While a backward task with a stated end has backward successors not yet scheduled, it shall wait for them. SYNTHESIS: the readiness and bound rules of #14 applied to stated ends too; forward successors still do not bound it (they are placed after it).

---

DONE: backward tasks bound by min(own end or project end, onstart predecessors' starts, bounding successors' starts less gaps); task_dependencies.bounding_successors excludes successors that depend on this task onstart while scheduled backwards (read the other way round, README); readiness waits for backward bounding successors even with an own end. d09 now schedules: a Thu 13:00-17:00, b Thu 17:00-Fri 17:30 (hand-derived; edge case alap_own_end_before_successor, fails on 0.10.1). jit_supply unchanged except set_deps (pending Farshid).

---

VERIFIED on 0.10.2 from PyPI (3.13.7): d09 schedules a Thu 13:00-17:00, b Thu 17:00-Fri 17:30; edge case alap_own_end_before_successor passes (fails on 0.10.1).

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.
