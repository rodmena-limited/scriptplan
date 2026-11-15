# onstart on a task scheduled as late as possible is refused

**Ticket**: issuedb #43  
**Status**: closed (released in 0.11.0)  
**Priority**: high  
**Release**: 0.11.0

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 43` whenever the spec or the chosen
alternative changes.

---

Farshid, 2026-11-15: fix reading 3 of 3. ScriptPlan read 'depends X { onstart }' on a backward task as 'finish before X starts'. The reference scheduler refuses it: 'Tasks with on-start dependencies must be ASAP scheduled', also when the dependency is inherited from a container (reference runs t1, t2, e7).

EARS SPEC:
- R1 (unwanted) If a task scheduled as late as possible has a dependency with onstart, its own or inherited from a container, then ScriptPlan shall refuse the file, name the task and the predecessor, and say that 'precedes' states finish-before-start.
- R2 (ubiquitous) onstart on a task scheduled as soon as possible shall keep meaning start-to-start (reference run e5).
- R3 (quality) No expected value in tests/ or examples/showcase shall change; a fixture that used onstart under ALAP shall say the same thing with precedes.

Synthesis (localised): concept is validation before scheduling (preflight). ALTERNATIVES: refuse [CHOSEN: the reference's behaviour] vs start-to-start for backward tasks [REJECTED: no scheduler of this format defines it] vs keep finish-before-start [REJECTED by Farshid 2026-11-15].

---

SYNTHESIS CHANGE while building: propagation of backward scheduling through a dependency chain no longer turns a task with an onstart dependency backward (it stays forward, as the reference scheduler leaves it), and a successor that depends on a backward task { onstart } no longer bounds where that task ends.

VERIFICATION (2026-11-15):
- R1: tests/test_onstart_direction.py: own dependency, inherited from a container, and project-level `scheduling alap` are each refused with exit code 2 and one message naming the task and the predecessor (reference runs v1, e7: 'Tasks with on-start dependencies must be ASAP scheduled'). All three fail on v0.10.3.
- R2: forward onstart is start-to-start (reference run e5); a backward task with forward onstart successors, one with a gap and one inside a container, gives the reference's dates (run q1).
- R3: jit_supply, paradox and time_traveler say `precedes`; every expected date unchanged; the reference scheduler gives those dates for the precedes form of each (recorded in each expected.md). examples/edge_cases/alap_onstart_reading renamed alap_precedes_finishes_before.
