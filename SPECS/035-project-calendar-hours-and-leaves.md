# Project workinghours is never applied, and global leaves do not close the project calendar (Siambr)

**Ticket**: issuedb #35  
**Status**: in progress  
**Priority**: critical  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 35` whenever the spec or the chosen
alternative changes.

---

Reported by siambr-api on AgentBus thread 01M7ES0QR99SKNWDPKC5QXKNR9 against 0.10.2; reproduced on 0.10.2 and on the unreleased 0.10.3, and checked against the hour-level reference scheduler.

EARS SPEC:
- R1 (ubiquitous) The project calendar shall be the week the project's workinghours lines state; where the project states none it shall be Monday to Friday 09:00-17:00, read in the project's timezone.
- R2 (ubiquitous) length, gaplength and a resource with no working hours of its own shall use the project calendar.
- R3 (ubiquitous) A global leaves entry of any type, and a global vacation, shall close the project calendar for its interval, for length, gaplength and every resource alike.
- R4 (ubiquitous) The workinghours lines of one block (project, shift or resource) shall together state that block's whole week: a day no line names is not worked, and lines naming the same day add up. This is the rule the eclipse golden already asserts for shifts.
- R5 (ubiquitous) The slot size derived from the times a project uses shall include the times in the project's workinghours and the edges of global leaves.
- R6 (quality) Reproductions A1, A4, A5, A6, B1, B2, B3, B4 and D6 shall give the reference's dates exactly: 2026-12-29-17:00, 2026-12-29-17:00, 2026-12-29-13:00 (both tasks), 2026-12-30-17:00, 2026-12-05-17:00, 2026-12-05-17:00, 2026-12-08-09:00, 2026-12-04-09:00, and h at 2026-12-28-17:00.

TECHNICAL PROBLEMS:
1. One calendar answer for 'is this slot project working time', read by length, gaplength and default resources.
2. Parsing the project's workinghours into the same structure resources use.
3. Global leaves and vacations treated as one list.

SOLUTION DOMAINS:
- Weekly working-time calendar -> the existing WorkingHours class (codebase pattern), given to the project.
- Leave intervals -> the existing Leave/TimeInterval lists on the project.

ALTERNATIVES:
- Unnamed days: ScriptPlan's rule, off [CHOSEN: the eclipse golden asserts it and its file states the intent] vs the reference's rule, unnamed days keep inherited hours [REJECTED: changes the eclipse golden from 06-09 to 06-05 and silently changes every existing file that names only some days; put to Farshid as a decision].
- Calendar source: WorkingHours on the project [CHOSEN] vs a second hard-coded table [REJECTED: two implementations of midnight-crossing and timezone reading].

---

Also fixed under this ticket, found while testing it:
- A shift's `leaves` was dropped when parsed (Siambr, delivery 01M7ESTTCZ3GF79SVTVVSSKMX5): the grammar's inline alternative handed the applier the bare leave type. R7 (ubiquitous): a leave on a shift shall hold for every resource that takes the shift's hours. Reproduction S1 ends 2026-12-25-17:00, the reference's date; Siambr expected the 26th, which counts Friday the 25th as a holiday the file does not declare.
- A global vacation in the first week of a UTC project was tiled into every week for a resource on the default hours (T1: 2026-12-23 instead of 2026-12-21). R8 (ubiquitous): the weekly pattern a resource's scoreboard is tiled from shall contain no leave.

VERIFICATION (2026-11-15): A1, A4, A5, A6, B1, B2, B3, B4, D6, S1, T1, T2 all give the reference's dates on the fixed code; tests/test_project_calendar.py holds them (22 tests, 17 fail on v0.10.2 before the stored-once tests are counted).
