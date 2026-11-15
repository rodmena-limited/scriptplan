# Path criticalness counts a shared follower for every task that leads into it

**Ticket**: issuedb #44  
**Status**: closed (released in 0.11.0)  
**Priority**: high  
**Release**: 0.11.0

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 44` whenever the spec or the chosen
alternative changes.

---

Farshid, 2026-11-15: fix reading 1 of 3. 0.10.3 walked tasks in declaration order and gave a follower reached a second time without its own criticalness, copying what the reference scheduler does. The reference's own comment says the opposite of its code (own criticalness is left out only when the path enters at the task's end), so this is a fault there that 0.10.3 reproduced.

EARS SPEC:
- R1 (ubiquitous) A task's path criticalness shall be its own criticalness plus the largest path criticalness among the tasks that follow it or follow a container it is inside, each follower counted in full.
- R2 (ubiquitous) Path criticalness shall not depend on the order tasks are declared in.
- R3 (quality) No expected value in tests/golden or examples/showcase shall change; the share of the 150 random projects that still match the reference shall be measured and reported, and every mismatch shall involve a follower reached from two tasks.

Synthesis (localised): longest path in a DAG with memoisation. ALTERNATIVES: full count [CHOSEN by Farshid 2026-11-15] vs the reference's order-dependent count [REJECTED: depends on declaration order, contradicts its own stated intent].

---

SPEC ADDITION while building: followers include tasks that wait for a task's start ({ onstart }), not only its end.

VERIFICATION (2026-11-15):
- R1, R2: tests/test_contention_and_bookings.py::test_a_shared_follower_counts_for_both_tasks_that_lead_into_it: a (2 h), b (3 h) and c depending on both give b, a, c in both declaration orders. On v0.10.3 the 'ab' order gives a first.
- R3: no file in tests/golden and no expected.csv in examples/showcase changed. 150 random contended projects: 132 match the reference scheduler; with only the 0.10.3 routine put back, 150 match; all 18 that differ contain a task with two or more predecessors. Recorded in README ("Differences from other schedulers of this format") and CHANGELOG.
- The reference's routine subtracts a task's own criticalness on a repeat visit when the path enters at its start, and its comment says the subtraction is for a path that enters at its end.
