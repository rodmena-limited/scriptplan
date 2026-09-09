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
- Loop, effort, ALAP, allocation modes -> TaskJuggler 3 documented semantics (clean-room).
- Availability -> per-day bitmaps (day_index -> int of 86400/R bits) with popcount for limits; big-int ops are C-speed in CPython.
- Booking ownership/cost -> per-resource run list (BookingRun with last_slot_seconds) rather than a per-slot owner array.
- Graph -> precomputed DependencyGraph with cycle detection and criticalness.

ALTERNATIVES:
- Architecture: new scheduler/engine package with the model kept behind a facade [CHOSEN: modules <=350 lines, old loop retained for per-fixture diffing while goldens are re-derived, engine unit-testable with dataclass fakes] vs in-place rewrite of task_scenario/project/resource_scenario [REJECTED: identical work, no diffing, refactor and semantic change entangled] vs incremental patching [REJECTED: leaves the person-hour and readiness defects].
- Availability: per-day bitmaps [CHOSEN: ~73KB/resource-year at 1min, O(1) next-free via (m & -m).bit_length()] vs flat list of slots [REJECTED: 525k refs/resource-year, measured 37-59s] vs run-length intervals [REJECTED: interleaved booking fragments runs; split/merge bookkeeping].
- Loop shape: event-driven cursor jumps to next availability [CHOSEN] vs visiting every slot [REJECTED: O(slots x tasks) at 1min].
- Sub-slot precise end: keep the existing formula as a documented ScriptPlan extension [CHOSEN: the t_float 14:57:05 golden depends on it] vs end on slot boundaries as TaskJuggler does [REJECTED: loses accuracy the README advertises].
