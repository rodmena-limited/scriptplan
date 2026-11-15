# Directives accepted and ignored: group allocation fails, allocate limits and lower limits do nothing

**Ticket**: issuedb #39  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 39` whenever the spec or the chosen
alternative changes.

---

Found by audit/evaluations/probe_directive_effect.py (issuedb #38), each checked against the reference.

EARS SPEC:
- R1 (ubiquitous) Allocating a resource that has members shall allocate every member: each that is on shift and free books the slot. (G1: 16 h on a group of two ends 2025-01-06-17:00; 0.10.2 reports the task as unschedulable.)
- R2 (unwanted) If an allocate option block contains limits, then ScriptPlan shall refuse the file, naming the task, because the option was parsed and never applied. (The reference refuses it too.)
- R3 (event-driven) When scheduling completes and a period in which a resource or task was booked fell short of its dailymin, weeklymin, monthlymin or minimum, ScriptPlan shall print one warning per limit naming the holder, the first such period, the time booked and the minimum. The exit code is unchanged.
- R4 (ubiquitous) weekstartsmonday states the default; weeks used by weeklymax start on Monday (G4: 32 h from Saturday 2025-01-04 under weeklymax 16h ends 2025-01-07-17:00).

Synthesis (localised): R1 reuses AllocationPlan, expanding a group into one allocation per leaf member; R2 is a SemanticError in the transformer; R3 reads Limits.lowerLimitShortfalls, which already counts and which nothing called.
ALTERNATIVES for R2: refuse [CHOSEN: matches the reference, nothing to mis-apply] vs implement per-allocation limits [REJECTED: no specification of what it would mean; the task's own limits block with { resources } already says it].

---

Also under this ticket: `plan report` discarded engine warnings on success (run_scriptplan captured stderr and dropped it). R5 (ubiquitous): a warning raised while scheduling shall reach stderr from `plan report` as it does from `scriptplan`. And the attribute applier skipped any item that was not a (name, value) pair; it now raises, except for the value of a custom attribute declared with `extend`, which is listed as not kept.

VERIFICATION (2026-11-15): G1 ends 2025-01-06-17:00 (reference: same). G2 exits 2 with the refusal. G3 prints four warnings and exits 0. G4/G5 end 2025-01-07-17:00 with and without weekstartsmonday (reference: same). tests/test_contention_and_bookings.py.
