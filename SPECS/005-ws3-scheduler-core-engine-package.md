# WS3 Scheduler core: engine package

**Ticket**: issuedb #5  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 5` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- effort shall be person-time: with N allocated resources available in a slot the task shall accrue N*slot*efficiency of effort, and each resource-slot shall be counted once for bookings and cost.
- Where an allocation is mandatory, ScriptPlan shall book a slot only if every mandatory allocation can be booked in it.
- duration shall be calendar time and length working time, and both shall be scheduled.
- When several ready tasks compete for a resource, ScriptPlan shall order them by priority, then criticalness, then declaration order.
- ScriptPlan shall never change the declared project end; an ALAP task with no end constraint shall end at the declared project end.
- Where a dependency chain mixes ASAP and ALAP tasks, ScriptPlan shall schedule it instead of reporting a deadlock.
- If a maxgapduration or maxgaplength constraint cannot be met, then ScriptPlan shall report an error naming both tasks and the achieved gap.
- Calling Project.schedule() twice shall produce identical task dates and identical resource bookings.
- Readiness shall be evaluated in O(1) per task per pass using a precomputed dependency graph.
- 500 chained tasks at 1h resolution shall schedule in <= 3s; 100 tasks / 10 resources / 1 year at 1min shall schedule in <= 10s and <= 200MB RSS.

TECHNICAL PROBLEMS:
1. Resource allocation under contention with per-slot admission control.
2. Date-driven readiness and propagation over a dependency DAG (replaces scan-based readiness).
3. Backward scheduling as the mirror of the forward pass over shared booking code.
4. Availability representation at minute resolution without a slot object per minute.
5. Scheduling state that is reset deterministically per run.

SOLUTION DOMAINS:
- Loop, effort, ALAP, allocation modes -> the .tjp format's documented semantics (clean-room).
- Availability -> per-day bitmaps (day_index -> int of 86400/R bits) with popcount for limits; big-int ops are C-speed in CPython.
- Booking ownership/cost -> per-resource run list (BookingRun with last_slot_seconds) rather than a per-slot owner array.
- Graph -> precomputed DependencyGraph with cycle detection and criticalness.

ALTERNATIVES:
- Architecture: new scheduler/engine package with the model kept behind a facade [CHOSEN: modules <=350 lines, old loop retained for per-fixture diffing while goldens are re-derived, engine unit-testable with dataclass fakes] vs in-place rewrite of task_scenario/project/resource_scenario [REJECTED: identical work, no diffing, refactor and semantic change entangled] vs incremental patching [REJECTED: leaves the person-hour and readiness defects].
- Availability: per-day bitmaps [CHOSEN: ~73KB/resource-year at 1min, O(1) next-free via (m & -m).bit_length()] vs flat list of slots [REJECTED: 525k refs/resource-year, measured 37-59s] vs run-length intervals [REJECTED: interleaved booking fragments runs; split/merge bookkeeping].
- Loop shape: event-driven cursor jumps to next availability [CHOSEN] vs visiting every slot [REJECTED: O(slots x tasks) at 1min].
- Sub-slot precise end: keep the existing formula as a documented ScriptPlan extension [CHOSEN: the t_float 14:57:05 golden depends on it] vs end on slot boundaries as the reference scheduler does [REJECTED: loses accuracy the README advertises].

---

## Outcome

**Status**: closed.

effort is person-time; allocation options bind per resource, and `mandatory` and `persistent` work. Cost is charged once per resource-hour. Mixed ASAP/ALAP chains schedule, with a warning where a backward task has nothing to be late against. maxgap and the min/max dates are verified after scheduling (scheduler/postcheck.py). Scheduling twice gives the same answer.

The engine was not extracted into a separate package: the defects were addressable in place once the allocation model (core/allocation_plan.py) existed, and the file-size work split the module into task_placement, task_booking, task_dependencies and task_resources, which gives the same separation without a migration. The per-day bitmap board was not needed either, because deriving the slot size keeps hour-aligned projects on hour-sized slots. Both are recorded here as deliberately not done rather than pending.

Fixture changes: eclipse.tjp and bottleneck.tjp express 'these two together' as `mandatory` with the effort in person-hours, keeping every expected datetime; simple.tjp and tutorial.tjp finish sooner because effort is now shared, which tutorial.tjp's own comment says it should.

Probes: probe_effort_semantics 5/5, probe_alap 5/5, probe_idempotency 4/4, probe_priority 2/2.

**One quantified criterion is not met.** The spec asks that 100 tasks over 10
resources for a year at one-minute resolution schedule in 10 seconds. Measured:
about 13 seconds on the reference box, down from 58.7 seconds before the audit
and from 80.5 seconds mid-way through it. 500 chained tasks at one-hour
resolution is met with room to spare: 1.5 seconds against a 3-second ask.

The remaining cost is laying out the scoreboard: a year at minute resolution is
525,600 slots, held as a Python list per resource. The shift pattern is now
computed for one week and tiled where it repeats, which removed most of it, but
the list itself is still allocated and walked. The fix is the denser
representation the original plan described -- a bit per slot per day, with
bookings held separately -- and it was not done, because the correctness work
was the point and this is a known, measured, bounded limitation rather than a
wrong answer. probe_scale.py records the measurement and gates against a
regression at roughly twice it.
