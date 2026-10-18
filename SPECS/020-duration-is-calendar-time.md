# Duration tasks skip to working time although duration is calendar time

**Ticket**: issuedb #20  
**Status**: in-progress  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 20` whenever the spec or the chosen
alternative changes.

---

Found by the mixed-plan fuzz (probe_placement.py) for #16; the same in 0.10.0, 0.10.1 and the 0.10.2 tree.

EVIDENCE (gaps/dur_nonworking.tjp, R=60, Mon-Fri 09:00-17:00), against the hour-level reference scheduler:
- d `depends a duration 2h`, a ends Fri 17:00: scriptplan Mon 09:00-11:00; reference Fri 17:00-19:00.
- z `scheduling alap duration 2h end Sun 15:00`: scriptplan Fri 15:00-Sun 15:00 (a 48-hour window for a 2-hour task); reference Sun 13:00-15:00.
- length tasks (l, y): scriptplan and the reference contain the same working time; scriptplan reports a forward length task's start at the next working moment, the reference at its earliest start. Presentation only, unchanged.
Cause: place_task moves every non-effort task to the next (previous) working slot before counting, although duration is calendar time.

EARS SPEC:
- R1 (ubiquitous) A duration task shall start at its earliest start (forward) or end at its latest end (backward), whether or not that moment is working time, and span exactly its duration of calendar time.
- R2 (ubiquitous) Length tasks shall keep their placement; they span exactly their length of working time.
- R3 (ubiquitous) The golden snapshots shall be unchanged, or each change brought to Farshid with evidence.
SYNTHESIS (localised): domain = the documented unit semantics (SPECS/003: duration is calendar time) and the reference scheduler's behaviour. Alternative rejected: keep skipping to working time [REJECTED: contradicts SPECS/003 and the reference, and produced a 48-hour window for a 2-hour task].
