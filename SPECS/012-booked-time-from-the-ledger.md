# Allocated time and timesheet planned work credit a shared slot to its last task

**Ticket**: issuedb #12  
**Status**: in-progress  
**Priority**: medium  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 12` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- When several tasks share a slot on one resource, TaskScenario.getAllocatedTime() shall report each task's own seconds in that slot (sum of slotTaskUsage), not whole slots by scoreboard occupant.
- When a timesheet reports planned work (getEffectiveWork / allocated_slots), it shall count the seconds each task was booked, not whole slots.

EVIDENCE (found while fixing #11, scriptplan 0.10.1 working tree): 40/13/40 min on one resource at R=60 -> getCost() 40, 13, 40 (correct, reads slotTaskUsage) but getAllocatedTime() 0 h, 0 h, 2 h, because resource_reporting.allocated_slots and task_resources.allocated_time count scoreboard slots and the scoreboard holds only the last booker. No report column calls these; TaskScenario.getAllocatedTime() and timesheet planned work do.

SYNTHESIS (localised bugfix): solution domain = the slot ledger from #11; concept = read slotTaskUsage, the per-task record, for any per-task time figure.

---

SPEC UPDATE (scope for 0.10.2; copied to SPECS/012-booked-time-from-the-ledger.md):
- R1 (ubiquitous) TaskScenario.getAllocatedTime() shall return the hours each resource was actually booked for the task, summed from slotTaskUsage (40/13/40 at R=60: 0.667, 0.217, 0.667 h; 0.10.1 gives 0, 0, 2).
- R2 (ubiquitous) A resource's allocated, free and effective work for a period (getAllocatedSlots, getFreeSlots, getEffectiveWork and the timesheet figures built on them) shall count booked seconds, expressed in slots, so a slot shared by several tasks credits each its own share and the shares add up to the slot.
- R3 (ubiquitous) Results on slots booked whole shall be unchanged.
SYNTHESIS (localised): domain = the slot ledger; concept = slotTaskUsage is the per-task record, so every per-task figure is a sum over it. Alternative rejected: keep the scoreboard as the source and add the partial shares on top [REJECTED: two sources of truth for one quantity, which is how #11 hid].

---

DONE in code: allocated_slots/free_slots count booked seconds from slotTaskUsage (fractional slots); allocated_time sums slotTaskUsage. 40/13/40 at R=60: getAllocatedTime 0.6667, 0.2167, 0.6667 h (was 0, 0, 2); getAllocatedSlots matches; free Monday 6.45 slots.
