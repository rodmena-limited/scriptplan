# 0.10.3 regression: a dependency chain of ~1,000 tasks fails with 'maximum recursion depth exceeded'

**Ticket**: issuedb #46  
**Status**: closed (released in 0.11.0)  
**Priority**: critical  
**Release**: 0.11.0

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 46` whenever the spec or the chosen
alternative changes.

---

Found 2026-11-15 while rewriting path criticalness (#44). 0.10.3's criticalness walk recurses once per task along a dependency chain. A chain of 1,000 one-hour tasks ('task tN { depends tN-1 }') stops with 'Error during scheduling: maximum recursion depth exceeded' on 0.10.3 from PyPI; 0.10.2 schedules it.

EARS SPEC:
- R1 (ubiquitous) Path criticalness shall be computed without recursion that grows with the length of a dependency chain or the depth of the task tree.
- R2 (quality) A chain of 3,000 tasks shall schedule through the CLI with exit code 0.

Synthesis (localised): iterative depth-first walk with an explicit stack, as the cycle check already does.

---

VERIFICATION (2026-11-15):
- R1: scriptplan/core/criticalness.py walks with an explicit stack.
- R2: a chain of 3,000 tasks schedules through the CLI, exit 0, 7.3 s (0.10.3 from PyPI: 'Error during scheduling: maximum recursion depth exceeded'; 0.10.2: schedules). tests/test_contention_and_bookings.py::test_a_chain_of_twelve_hundred_tasks_schedules fails on v0.10.3.
