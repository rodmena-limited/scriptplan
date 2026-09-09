# WS4 Drop the compiled path

**Ticket**: issuedb #6  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 6` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- ScriptPlan shall ship a single implementation path; the published wheel and the source checkout shall produce identical schedules for every fixture and probe.
- Where an optional acceleration exists, ScriptPlan shall expose which path is active and shall provide an environment switch to force the pure path.

TECHNICAL PROBLEMS:
1. Build-artefact divergence: the wheel computes different schedules from the same input than the source.
2. Untested second implementation (no test references the compiled path).

SOLUTION DOMAINS:
- Cython compiler directives (cdivision, boundscheck) and their C semantics.
- Wheel/sdist packaging (setuptools ext_modules, Root-Is-Purelib).

ALTERNATIVES:
- Drop Cython [CHOSEN: the three .pyx modules accelerate exactly the flat-slot representation WS3 retires; deleting removes the divergence permanently and makes the wheel pure-Python] vs fix and keep behind a parity gate [REJECTED: permanent parity cost for a ~25% gain on code being deleted] vs keep as-is [REJECTED: confirmed wrong schedules in every published wheel: (0-1)%7 == -1 under cdivision loses Monday 00:00-06:00 after a Sunday night shift].
- Interim: fix working_hours_cy.pyx modulo and add a source-vs-wheel parity probe [CHOSEN if WS0-WS2 ship before WS3 as 0.9.3].
