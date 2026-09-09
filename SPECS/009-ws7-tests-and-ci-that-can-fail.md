# WS7 Tests and CI that can fail

**Ticket**: issuedb #9  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 9` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- Every EARS requirement in this epic shall have a probe in audit/evaluations or a test in tests.
- Each probe shall drive ScriptPlan through its own API or CLI and shall print PASS or FAIL with the evidence observed.
- audit/evaluations/run_all.sh shall run the safe probe set and exit non-zero on any failure.
- The test suite shall run without pytest-xdist and from any working directory.
- Where two implementation paths exist, the suite shall run against both.
- No test shall assert a constant it computed itself rather than a value the system produced.

TECHNICAL PROBLEMS:
1. Self-confirming verification (hardcoded expected sums, values harvested from the implementation).
2. Fixture-path and plugin coupling that makes the suite unrunnable in other environments.
3. Certification artefacts that assert only that the process did not crash.

SOLUTION DOMAINS:
- mission-critical-audit probe harness (audit/evaluations, one probe per claim, both directions for guards).
- pytest conftest fixtures for data paths; house CI at ci.rodmena.co.uk.

ALTERNATIVES:
- Goldens: derive expected values by an independent simulation, as TestIssue41 already does [CHOSEN] vs re-record from the implementation [REJECTED: that is the defect] vs compare against real TaskJuggler output [PREFERRED but rejected for now: no TaskJuggler available in this environment; recorded as follow-up].
- judge_*.py scripts: fold their ground truth into tests and delete [CHOSEN: nothing runs them and one of them checks one of its four computed values] vs wire them into CI [REJECTED: duplicate mechanism for the same assertions].
