# Tasks that share a slot on one resource are booked into time that does not exist

**Ticket**: issuedb #11  
**Status**: closed  
**Priority**: critical  
**Release**: 0.10.1

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 11` whenever the spec or the chosen
alternative changes.

Reported by trace-thinkpad-83589d over AgentBus (thread
01M55QZ50MPQP6GJ873DPWBEYE, message 01M55QZ50BWS8Z5V8HSYZJR4GQ,
`platform_attested`). Reproduced against scriptplan 0.9.0, 0.9.1, 0.9.2 and
0.10.0 installed from PyPI: `bare60.tjp` (40/13/40 min on one resource, R=60)
scheduled t0 09:00-09:40, t1 09:00-09:13 and t2 09:00-09:40, and slot 09:00 held
5580 s of work in a 3600 s slot while `slotSecondsUsed` reported 2400 s. Present
since commit 6596d09 (2025-11-28).

---

EARS SPEC:
- R1 (unwanted) If several tasks book time in one slot of one resource, then the scheduler shall keep the seconds booked in that slot (sum of `slotTaskUsage`) at or below the slot length, within 1 s.
- R2 (ubiquitous) The scheduler shall keep `slotSecondsUsed` equal to the sum of `slotTaskUsage` for every resource slot, within 1 s, except for time it leaves unbooked to honour a mid-slot start or end (R8, R12), where `slotSecondsUsed` may only be larger.
- R3 (event) When a forward task's first booking lands in a slot that is partly used on that resource, the scheduler shall report its start at the first free second of that slot (bare5: t2 starts 09:53, not 09:50).
- R4 (event) When a task finishes inside a slot, the scheduler shall end it when its remaining effort is done, counted from where its own booking in that slot began, and shall return only the unused part of its own booking (bare60: t0 09:00-09:40, t1 09:40-09:53, t2 09:53-10:33).
- R5 (state) While a task is scheduled backwards (alap), R1-R4 shall hold mirrored: bookings fill a slot from its end, the end is the last second of work and the start the first (40/13/40 alap, all ending 17:00, placed in declaration order: t0 16:20-17:00, t1 16:07-16:20, t2 15:27-16:07).
- R6 (event) When several resources work on a task in its final slot, the scheduler shall end the task at the earliest moment their combined work covers the remaining effort and shall release each resource's unused time (80 min on a, b at R=60: 09:00-09:40, cost 80 at rate 60, not 10:00 and 120).
- R7 (event) When time is released, the scheduler shall return it to the resource's limit counters, the task's limit counters and the resource's booked-effort total (dailymax 60min, 40/13/40: Mon 09:00-09:40, 09:40-09:53, Mon 09:53-Tue 09:33; 0.10.0 gave Mon, Tue, Wed).
- R8 (unwanted) If a task's earliest start falls mid-slot because of a dependency, then the scheduler shall keep the task out of the time before that moment in that one slot only; a later slot shall be bookable from its start (X 10:00-10:30, not 10:50-11:20).
- R9 (ubiquitous) The scheduler shall book, across all resources, person-time equal to each scheduled effort task's effort, within 1 s per task.
- R10 (ubiquitous) An acceptance probe shall check R1, R2 and R9 from `slotTaskUsage`, and the dates from the public `plan` CLI report, for: 40/13/40 at R in {60,30,15,5}; the eight-effort case (61,129,49,73,318,163,579,134 min, R=60, one resource, 09:00-17:00) with no day over 480 min; the alap mirror; the two-resource case; and a seeded fuzz of at least 200 plans with efforts drawn freely from 1-600 min and R in {5,10,15,30,60}. It shall fail against 0.10.0 and pass after the fix.
- R11 (quality) Scheduling cost shall not regress: the slowest example fixture shall schedule within 110% of its 0.10.0 time (same machine, same interpreter, median of 3).
- R12 (unwanted) If a declared `start` falls inside a slot, then the scheduler shall not book work before it; if an alap task's `end` (declared, or derived from a successor) falls inside a slot, then the scheduler shall use that slot up to that moment and no further (`start 09:30` at R=60: 09:30-10:10, not 09:00-09:40; alap `end 16:30`: 15:50-16:30, not 15:20-16:00).
- R13 (event) When a forward milestone follows a task that ends mid-slot, the scheduler shall place the milestone at that task's end, not at the top of the slot.
- R14 (ubiquitous) The scheduler shall keep the slot ledger at full precision and round only reported dates to the second, rounding the end of one task's work and the start of the next from the same value so the two dates meet exactly.

TECHNICAL PROBLEMS (priority order):
1. Sub-slot capacity accounting: which part of a slot each booking occupies, so capacity and position are both exact.
2. Final-slot settlement: how much of each resource's booking in the last slot the task actually needs, and returning the rest to every counter that recorded it (ledger, limits, booked effort).
3. Position reporting: start and end derived from where the work sits, in both scheduling directions.
4. Mid-slot entry: a start, dependency end or alap end that falls inside a slot constrains that one slot only.
5. An oracle independent of the engine's own capacity counter (the counter the bug corrupts is the one every existing check read).

SOLUTION DOMAINS:
- Interval occupancy of a fixed-length bin, filled from both ends: list scheduling places forward work first-fit from the bin start and backward work from the bin end, so free time in a slot is always one gap. Concept: two cursors per bin (front, back), as in a two-ended stack / double-ended arena allocator.
- Settlement of parallel work: monotone piecewise-linear work function W(T) = sum_r e_r * clamp(T - f_r, 0, a_r); the finish time is its first crossing of the remaining effort (breakpoint walk).
- Oracle: physical invariants (capacity per slot, conservation, non-overlap and no gaps for independent tasks on one resource) computed from the public report and the per-task ledger, never from `slotSecondsUsed`.

ALTERNATIVES:
- Slot occupancy: front/back cursors [CHOSEN: O(1) per booking; exact for the only two fill directions the engine has; capacity = slot - front - back] vs per-slot interval set [REJECTED: general but O(k) and more code for gaps the engine never creates; the one gap it does create, before a mid-slot start, is passed over by moving the cursor past it] vs scalar used-seconds with corrected arithmetic [REJECTED: cannot say which end of a slot is free when an asap and an alap task share it, so positions stay wrong] vs rounding off-grid effort up to whole slots, one task per slot (the reference scheduler) [REJECTED: drops the minute-level precision the package exists to provide and moves every off-grid schedule].
- Final-slot settlement: common finish time T over all resources booked in the slot [CHOSEN: earliest finish, physically what parallel work does] vs settle only the last-booked resource (status quo) [REJECTED: other resources keep a full slot; 80 person-min on two people costs 2 h] vs proportional share of each booking [REJECTED: with different offsets resources stop at different times and the finish is later than necessary: a free 0-60, b free 40-60, 30 min needed -> T=30 vs 47.5].
- Where booking positions are recorded: on the task scenario for the current slot only [CHOSEN: settlement happens in the same slot as the booking, so no persistent per-booking state is needed] vs a persistent per-resource interval log [REJECTED: unneeded state; `slotTaskUsage` stays the public (task, seconds) shape Trace already reads].
- Rounding: exact ledger, dates rounded on display [CHOSEN after implementation] vs whole-second ledger [REJECTED: tried first; it moved airport_ultra_math's hand-computed t_float end from 14:57:05 to 14:57:04, because t_interrupt's true finish 806.49 s into its slot was stored as 806 and gave t_float 0.49 s that do not exist, and the error can grow along a chain].
- Mid-slot offset scope: one offset slot recorded with the offset [CHOSEN] vs "until the task first books" (status quo) [REJECTED: a busy first slot carried the offset into the next one and wasted it].
- A release that would hand back time another booking holds: raise [CHOSEN: fail closed; it cannot happen when a task's bookings are released in reverse order, which is the only caller] vs clamp silently [REJECTED: would hide exactly the class of defect this ticket is about].

KNOWN GAPS (not changed by this ticket):
- `TaskScenario.getAllocatedTime()` and timesheet planned work count whole scoreboard slots and credit a shared slot to the last task booked in it (40/13/40 at R=60: 0 h, 0 h, 2 h). Cost reads `slotTaskUsage` and is correct. Tracked as issuedb #12.
- In a quick check, alap milestones with no `end` of their own, before tasks that depend on them, came out at the project start (Mon 00:00) in both 0.10.0 and 0.10.1. Not investigated; unchanged by this ticket.
- Constructing `ProjectFileParser` compiles the grammar each time (0.6-0.9 s); parse() itself is milliseconds.
- `duration` and `length` tasks after a predecessor that ends mid-slot start at the top of that slot, before the predecessor finishes (a 09:00-09:40, then `duration 2h` reported 09:00-11:00), the same in 0.10.0 and 0.10.1. Tracked as issuedb #13.

VERIFICATION:
- `audit/evaluations/probe_slot_sharing.py`: 9 probes. Against 0.10.0 from PyPI 9 FAIL (including the 490-minute day, 115 of 240 mixed fuzz plans broken, 2 of 120 one-desk plans back to back). Against 0.10.1 9 PASS (240/240 and 120/120, 0 plans unschedulable).
- `probe_effort_semantics.py` "never double-book" rewritten off the slot grid: FAIL on 0.10.0, PASS on 0.10.1.
- `tests/test_slot_ledger.py`: 13 unit tests of the finish time, reserve/release, the release guard, withdrawal and limit return.
- Golden fixtures: 22 of 24 unchanged; airport_stress_test (t_install 11:00 -> 11:40, t_low 10:00 -> 10:20, both after e1 is free) and tutorial (test.alpha 12:00 -> 11:36, test.beta and project 13:00 -> 12:48, milestones follow) recorded with reasons.
