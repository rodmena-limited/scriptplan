# ALAP milestones land a slot early, and ALAP tasks before a declared start are degraded

**Ticket**: issuedb #14  
**Status**: in-progress  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 14` whenever the spec or the chosen
alternative changes.

---

Found while closing the known gaps of 0.10.1. All cases identical in 0.10.0 and 0.10.1 unless stated.

EVIDENCE:
- m alap precedes t (t alap effort 60min end 17:00 -> 16:00-17:00): m at 15:00, a slot early. m2 precedes t2 starting 15:30: m2 at 15:00 (0.10.0: 14:00).
- m alap with no successor and no end, project 2026-10-19 +1w: m at Fri 16:00; SPECS/005 says an alap task with no end ends at the declared project end.
- x start 14:00 (declared) depends m, m alap, no end: m degraded to asap with alap_degraded and placed at Mon 00:00, although x's declared start is a fixed moment m could be late against. Same for alap duration/length/effort tasks before such an x.

EARS SPEC:
- R1 (event) When an alap milestone's latest moment is fixed by a successor's start, its declared end or the project end, the scheduler shall place it at that moment exactly (m -> 16:00; m2 -> 15:30; m with nothing -> project end 2026-10-26 00:00).
- R2 (unwanted) If an alap task has no end of its own and a successor has a declared start, then the scheduler shall schedule it backwards from the earliest such start instead of degrading it (m before x start 14:00 -> 14:00, no alap_degraded warning).
- R3 (unwanted) If an alap task has no end, no declared-start successor and no scheduled successor (a genuine asap/alap cycle), then the scheduler shall keep the documented SPECS/005 behaviour: schedule it forwards and warn alap_degraded.
- R4 (ubiquitous) An alap milestone shall not move back over non-working time, mirroring forward milestones, which do not move forward over it.

TECHNICAL PROBLEMS: 1. the latest moment for a zero-length task; 2. readiness of an alap task whose successor's start is declared rather than computed.
SOLUTION DOMAINS: the 0.10.1 entry offset (enter_at) gives the exact latest moment; readiness is the SPECS/005 date-driven readiness, extended to treat a provided start as a known date.
ALTERNATIVES: milestone at the entry moment computed by enter_at [CHOSEN: exact, symmetric with forward milestones] vs keep slot-start placement [REJECTED: the defect]. Readiness: a successor's provided start counts as known [CHOSEN: it is a fixed date the file states; the successor cannot start earlier] vs wait for the successor to be scheduled (status quo) [REJECTED: deadlocks and degrades a task that has a perfectly good bound].

---

DONE in code: alap milestones placed at entry_moment (exact latest moment), not moved back over non-working time (R4 confirmed by the reference scheduler on jit_supply: set_deps 2025-07-18 08:00); readiness counts a successor's STATED start (TaskScenario.successorStart / declaredStart, kept apart from the start a run writes back, so scheduling twice agrees: alap_ms three runs identical). Edge cases alap_milestones_exact, alap_project_end_and_declared_end, alap_before_declared_start, alap_bounded_by_declared_starts pass now, fail on 0.10.1. Pending: Farshid's yes/no on updating the jit_supply golden (16:00 -> 08:00).
