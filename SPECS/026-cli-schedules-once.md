# The CLI schedules every project twice and labels scheduling exceptions as parse errors

**Ticket**: issuedb #26  
**Status**: closed (released in 0.10.2)  
**Priority**: medium  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 26` whenever the spec or the chosen
alternative changes.

---

Found via trace defect 12. scriptplan/cli/main.py parse_files() called ProjectFileParser().parse(content), which schedules by default, then schedule() called project.schedule() again: every 'plan' run scheduled twice (doubling CLI time and making idempotency defects visible only through the CLI), and any exception raised while scheduling was printed as 'Error parsing project file: ...'. EARS: R1 (ubiquitous) The CLI shall schedule a project once per run. R2 (unwanted) If scheduling raises, then the CLI shall report it as a scheduling error. FIX: parse(content, schedule=False); schedule() schedules once and already labels its exceptions 'Error during scheduling'. Verified: 102 CLI-based tests (test_cli, test_plan_cli, test_examples, test_stated_dates, test_dependency_check) pass; main.py kept at 544 lines.

---

VERIFIED: the CLI schedules once (102 CLI-based tests in the gate); trace d12 on 0.10.2 from PyPI prints one error, no 'Error parsing project file'.

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.
