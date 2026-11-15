# workinghours: each line replaces the days it names; other days keep inherited hours; 'off'

**Ticket**: issuedb #42  
**Status**: closed (released in 0.11.0)  
**Priority**: high  
**Release**: 0.11.0

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 42` whenever the spec or the chosen
alternative changes.

---

Farshid, 2026-11-15: 'those 3 issues, can you please fix those and do a release as well'. Reading 2 of 3: ScriptPlan treated the workinghours lines of a block as its whole week (unnamed day unworked, same-day lines add up). The reference scheduler keeps inherited hours on unnamed days and lets a later line replace an earlier one for the same day.

Reference runs (hour-level, 2026-11-15): default week is Mon-Fri 09:00-17:00 with no break; project 'workinghours mon 08:00 - 10:00' leaves Tue-Fri 9-17; resource 'workinghours wed 10:00 - 12:00' leaves the other days 9-17; two lines for mon-fri (9-12 then 13-17) give 13-17 only; 'tue, thu off' closes them; a child resource inherits its parent's week; a shift inherits the project's week; a resource on a shift works the shift's whole week.

EARS SPEC:
- R1 (ubiquitous) A project's week shall start as Mon-Fri 09:00-17:00; a shift's week shall start as the project's week; a resource's week shall start as its parent resource's week, or the project's when it has no parent.
- R2 (event) When a workinghours line names days, ScriptPlan shall replace the hours of those days with the line's and leave every other day as it was.
- R3 (event) When a workinghours line names days and says 'off', ScriptPlan shall make those days unworked.
- R4 (event) When a resource takes a shift with 'workinghours <shift id>', its week shall become the shift's week, and a later workinghours line shall replace the days it names.
- R5 (ubiquitous) A resource's hours shall be read in its own timezone, or in the project's timezone when it states none (defect found 2026-11-15: read as UTC, so a London resource on 09:00-17:00 worked 10:00-18:00 in June).
- R6 (quality) Each of the nine reference experiments d1-d9 and z1 shall give the reference's dates through the CLI; no expected value in tests/ or examples/showcase shall change.

TECHNICAL PROBLEMS: 1. a week that is edited by lines over an inherited base; 2. what each kind of block inherits; 3. the zone a resource's hours are meant in.
SOLUTION DOMAINS: calendar inheritance as the format's reference scheduler does it (copy at creation, lines edit the copy); existing WorkingHours class.
ALTERNATIVES: copy the inherited week when the block is created [CHOSEN: matches the reference when a child is declared before a later parent line] vs resolve lazily at scheduling time [REJECTED: differs in that case]. Keep ScriptPlan's whole-week rule [REJECTED by Farshid 2026-11-15].

---

SPEC ADDITIONS made while building (2026-11-15):
- R7 (ubiquitous) A night shift shall belong to the day it starts on: naming the next day in another line, before or after, shall not remove its early hours. (The replace rule taken literally made the result depend on line order, and probe_calendar caught it.)
- R8 (ubiquitous) A resource with a timezone and no hours of its own shall work the project's week in its own zone. (The directive did nothing for such a resource.)
- R9 (quality) The slowest example shall schedule within 110% of its 0.10.3 time.

VERIFICATION (2026-11-15):
- R1-R4, R6: reference experiments d1-d8, d10, d12, d13 and x3 give the reference scheduler's dates through the CLI (tests/test_working_week.py, 12 cases, 11 fail on v0.10.3; the default-week control passes on both). Sub-resource snapshot at declaration (d10) included.
- R5: London project in June: resource with own hours, resource on a shift and resource with none all work 09:00-17:00 local (reference run z1: the same). 0.10.3: 10:00-18:00 for the first two.
- R6: no file in tests/golden and no expected.csv in examples/showcase changed. Two showcase inputs gained `off` lines (eclipse: tue, thu; blackbox: thu, fri and mon - wed); the reference scheduler gives the expected dates with them (eclipse 2025-06-09-13:00) and others without (2025-06-05-13:00).
- R7: probe_calendar "A Sunday night shift carries into Monday even when Monday has day hours" passes; both line orders tested.
- R8: probe_directive_effect "A resource timezone moves a resource that has no hours of its own": Asia/Tokyo ends 08:00 UTC.
- R9: math_torture 105% of 0.10.3, tutorial 100%, airport_stress_test 101%; a London year with 20 resources on own hours 114% after caching the zone conversion per zone (153% before). Python 3.13, three interleaved runs, median.
- 150 random projects: with the 0.10.3 criticalness routine put back, 150 of 150 match the reference scheduler.
