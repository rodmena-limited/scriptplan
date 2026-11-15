# Each leaves line stores every earlier leave again: 2^N entries, scheduling time doubles per line (Siambr)

**Ticket**: issuedb #40  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 40` whenever the spec or the chosen
alternative changes.

---

Reported by siambr-api (AgentBus delivery 01M7EVDS8HH2PN1V3RTF6QEVVW): one resource, one alap task of 30d effort, N consecutive weekday 'leaves holiday' lines: N=15 1.9 s, N=20 58 s. Reproduced: N=10 0.68 s, N=12 1.46 s, N=14 4.18 s; stored entries 1, 3, 7, 31, 1023 for N = 1, 2, 3, 5, 10.

EARS SPEC:
- R1 (ubiquitous) A resource or shift with N leaves, vacation or booking lines shall hold exactly N leave entries.
- R2 (quality) The reproduction with N=20 shall schedule in under 5 s on the development machine (0.10.2: 58 s as reported), and N=40 within 150% of the N=0 time.
- R3 (ubiquitous) The dates for N=5, 10 and 14 shall equal those of 0.10.2.

Synthesis (localised bugfix): 'leaves' is a list attribute whose assignment extends; the applier handed back the existing entries plus the new one. Concept: append once.

---

VERIFICATION (2026-11-15): entries for N = 20 lines: 20 (0.10.2: 1,048,575). Times on the development machine, plan report: N=0 0.46 s, N=10 0.45 s, N=14 0.45 s, N=20 0.47 s, N=40 0.47 s (0.10.2: N=14 2.88 s here; N=20 58 s as Siambr measured). Dates for N=5, 10, 14 equal 0.10.2's; N=20 equals the reference's (2026-12-07 to 2027-02-12). tests/test_project_calendar.py::test_each_leave_line_is_stored_once fails on v0.10.2 with 1048575 == 20.
