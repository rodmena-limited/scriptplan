# Task criticalness is never computed, so contention is priority then declaration order (README says otherwise)

**Ticket**: issuedb #37  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 37` whenever the spec or the chosen
alternative changes.

---

Nothing writes a task's criticalness or pathcriticalness; both stay 0.0, so the documented second sort key never decides anything. Reproduction C5: a duration task declared before an effort task on the same resource takes the slots first in ScriptPlan; the reference places the effort task first.

EARS SPEC:
- R1 (ubiquitous) Before placing tasks, ScriptPlan shall compute each resource's criticalness as the effort allocated to it divided by its free slots, and each task's criticalness as its effort times the mean criticalness of the resources it may use.
- R2 (ubiquitous) A task's path criticalness shall be its own criticalness plus the largest path criticalness among the paths through its successors and its ancestors' successors.
- R3 (ubiquitous) Tasks shall be placed by priority, then path criticalness, then declaration order.
- R4 (unwanted) If computing it changes a golden or example result, then the change shall be checked against the reference before the golden is touched.
- R5 (quality) C5 and E1 shall give the reference's dates.

Synthesis and alternatives are recorded in a comment once the impact on the suite is measured.

---

SYNTHESIS (recorded after measuring the suite):
TECHNICAL PROBLEMS: 1. demand per resource; 2. a task's share of it; 3. the heaviest chain behind a task.
SOLUTION DOMAINS: list scheduling with a static priority rule (the format's documented criticalness heuristic); longest-path on the dependency DAG.
ALTERNATIVES:
- Implement the documented order [CHOSEN] vs correct the README to say declaration order [REJECTED: leaves contended plans different from the reference in 5 of 5 hand cases].
- Path sum: plain heaviest-path [REJECTED: 72 of 80 random contended projects matched the reference] vs the reference's walk, in which a follower reached a second time counts without its own criticalness [CHOSEN: 80 of 80 in-process, then 150 of 150 through the CLI]. The order is a tie-break with no single right answer, so the same file giving the same plan decided it. Put to Farshid as overrulable.

VERIFICATION (2026-11-15): C4, C5, E1, K1-K4 give the reference's dates. 150 of 150 random projects (one resource per allocation, scratch generator seeds 1-150) match the reference on every end date and every start except those of length tasks, which the two schedulers report differently by design (README, known limits). No golden changed. Five examples/edge_cases answers and four probes that assumed declaration order were updated after the reference confirmed the new order forwards, backwards and under a daily cap.
