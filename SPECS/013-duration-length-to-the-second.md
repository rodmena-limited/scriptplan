# Duration and length tasks after a mid-slot end start before their predecessor finishes

**Ticket**: issuedb #13  
**Status**: in-progress  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 13` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- If a duration or length task's earliest start falls inside a slot because a predecessor ends there, then the scheduler shall start it at that moment and end it the stated duration (calendar) or length (working time) later, to the second.

EVIDENCE (found while fixing #11; identical in 0.10.0 from PyPI and the 0.10.1 tree): a: effort 40min on r0 at R=60 -> 09:00-09:40; d: depends a, duration 2h -> reported 09:00-11:00; l: depends a, length 2h -> reported 09:00-11:00. Both start 40 minutes before a ends. place_task sets a non-effort task's start to idxToDate(currentSlotIdx), and place_slot counts doneDuration/doneLength in whole slots, so the end is slot-aligned too.

SYNTHESIS (localised bugfix): solution domain = the mid-slot entry offset from #11 (enter_at / slotStartOffset); concept = start at slot start + offset and count the first slot as (slot - offset) seconds, ending mid-slot where the remainder runs out.

---

SPEC UPDATE (scope widened for 0.10.2; copied to SPECS/013-duration-length-to-the-second.md):

REGRESSION SHIPPED IN 0.10.1: an alap duration or length task before a successor that starts mid-slot now ends after the successor starts. t4 alap effort 40min end 17:00 -> 16:20-17:00; d4 alap duration 1h precedes t4 -> 0.10.1: 16:00-17:00 (overlaps t4); 0.10.0: 15:00-16:00. Cause: 0.10.1's enter_at() places backward work in the slot containing a mid-slot end, and only effort tasks got the matching end handling (workEnd).

EARS SPEC:
- R1 (unwanted) If a duration or length task's earliest start falls inside a slot (a predecessor ends there or its declared start is there), then the scheduler shall start it at that moment (a 09:00-09:40, d depends a: d starts 09:40, not 09:00).
- R2 (ubiquitous) The scheduler shall end a duration task exactly its duration of calendar time, and a length task exactly its length of working time, after its start, to the second, including inside a slot (duration 2h from 09:40 -> 11:40; duration 90min at R=60 from 09:00 -> 10:30).
- R3 (state) While a duration or length task is scheduled backwards, the scheduler shall end it at its latest permitted moment (declared end, successor start or project end) to the second, start it its duration or length earlier, and shall never end it after a successor starts (d4 -> 15:20-16:20; alap duration 2h end 11:30 -> 09:30-11:30, 0.10.0 gave 09:00-11:30, 0.10.1 10:00-11:30).
- R4 (ubiquitous) A duration or length task's window shall come from calendar or working time only, not from when its resources happened to be booked (alap duration 3h with r0 busy in its last hour still spans 3 h).
- R5 (event) When a duration or length task with allocations ends or starts inside a slot, the scheduler shall book its resources only inside its window and release the rest of the slot.
- R6 (ubiquitous) Plans in which no duration or length task starts or ends inside a slot shall schedule as in 0.10.1.

TECHNICAL PROBLEMS: 1. counting calendar/working time from a mid-slot entry; 2. the precise moment the count is reached; 3. backward mirror and the window end; 4. trimming resource bookings to the window.
SOLUTION DOMAINS: interval arithmetic on the slot grid, reusing the 0.10.1 entry offset (enter_at, slotStartOffset) and the slot ledger's release(); the same two-ended slot model.
ALTERNATIVES: count the entry slot as (slot - offset) and finish at slot edge minus overshoot [CHOSEN: O(1) per slot, symmetric in both directions, reuses the 0.10.1 entry offset] vs compute the end directly as start + duration via calendar arithmetic [REJECTED for length: working time needs the per-slot calendar walk anyway, and two code paths for duration and length would drift] vs keep slot-aligned windows [REJECTED: that is the defect].

---

DONE in code: task_spans.py (entry_moment, slot_share, finish_span) counts duration/length from the entry moment and finishes inside the slot, trimming resource bookings to the window; backward non-effort window ends at the entry moment. 0.10.1 regression fixed: d4/l4 15:20-16:20. Edge cases duration_length_after_mid_slot_end and alap_spans_before_mid_slot_successor fail on 0.10.0/0.10.1, pass now.
