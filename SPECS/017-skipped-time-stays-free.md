# Time skipped at a mid-slot bound is lost to every other task (0.10.1 regression)

**Ticket**: issuedb #17  
**Status**: closed (released in 0.10.2)  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 17` whenever the spec or the chosen
alternative changes.

---

REGRESSION SHIPPED IN 0.10.1, found while working on #14. The 0.10.1 slot ledger (#11) kept two cursors per slot. To keep a task out of the part of a slot on the wrong side of a mid-slot bound, it moved the cursor past that part, so the time was booked to nobody and usable by nobody.

EVIDENCE (passover.tjp, R=60, one desk):
- e alap effort 30min end Mon 14:30 (priority 900); z start Mon 14:00 effort 60min (priority 100). 0.10.1: e 14:00-14:30, z 15:00-16:00, although the desk is free 14:30-15:00. Expected z 14:30-15:30.
- f start Tue 09:30 effort 30min (priority 900); g start Tue 09:00 effort 30min (priority 100). 0.10.1: f 09:30-10:00, g 10:00-10:30, although the desk is free 09:00-09:30. Expected g 09:00-09:30. (0.10.0: f and g both 09:00-09:30 on the same desk.)

EARS SPEC:
- R1 (ubiquitous) The scheduler shall keep time it skips to honour a mid-slot start or end available to every other task.
- R2 (ubiquitous) For every resource slot, slotSecondsUsed shall equal the sum of slotTaskUsage exactly (within 1e-6 s); the R2 exception in SPECS/011 is withdrawn.
- R3 (ubiquitous) No two bookings on one resource shall overlap in time, checked from the booked intervals themselves.

SYNTHESIS CHANGE (supersedes the slot-occupancy choice in SPECS/011): per-slot set of occupied intervals [CHOSEN: the gaps the engine creates at mid-slot bounds are real free time; a slot rarely holds more than three intervals, so a scan costs little] vs two cursors (0.10.1) [REJECTED now: it can represent free time only between the cursors, which is what lost z's and g's half hours; the earlier rejection of the interval set assumed those gaps were worthless, and passover.tjp shows they are not].

---

DONE in code: slot_ledger.py rewritten around per-slot occupied intervals (rs.slotIntervals: sorted [start, end, task]); reserve() returns one SlotBooking per free stretch taken; release() shrinks only the booking's own interval (the RuntimeError guard of 0.10.1 is gone because no release can touch another booking). slotSecondsUsed is the sum of booked intervals, so R2 holds exactly. Verified: passover.tjp z 14:30-15:30, g Tue 09:00-09:30; edge case skipped_time_stays_free fails on 0.10.1, passes now; unit tests for two-sided free time.

---

VERIFIED: edge case skipped_time_stays_free passes (fails on 0.10.1); tests/test_slot_ledger.py 15 tests; probe_slot_sharing 9/9; probe_placement idle-time check 300/300.

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.
