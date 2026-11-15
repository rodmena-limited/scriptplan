# Release 0.11.0: three readings changed, resource hours in project time

**Ticket**: issuedb #45  
**Status**: closed (released as 0.11.0)  
**Priority**: high  
**Release**: 0.11.0

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 45` whenever the spec or the chosen
alternative changes.

---

Farshid, 2026-11-15: "those 3 issues, can you please fix those and do a release as well? you don't need further authorisation from me". While the work was running he added: "also please fix the AI-SLOP language style in the readme. it's very machine generated language, not human voice."

EARS SPEC:
- R1 (ubiquitous) The release shall contain the fixes of the three reading tickets and of every defect found while making them.
- R2 (ubiquitous) scripts/ci.sh shall pass on Python 3.9 and 3.13; the probe harness shall pass against the built wheel in clean venvs; the PyPI-served files shall be byte-identical to the tested ones.
- R3 (ubiquitous) The changelog shall name each change that can move an existing schedule, with what to write to keep the old meaning.
- R4 (ubiquitous) The repo, wheel and sdist shall not name the reference scheduler.
- R5 (ubiquitous) The README shall be rewritten to the house writing standard with no fact dropped, weakened or strengthened without a check, and its examples shall run as written.

---

RELEASED as scriptplan 0.11.0 (commit 42f5702, tag v0.11.0, GitHub release v0.11.0). PyPI wheel sha256 c287803ec025c7146a0029f9cd6a196b228d55cc23704f7a74605ce62d86faff, sdist e7d24b8c0f11df42bbb95d7dac0dd1524fa3afc3542c218c5186ac7cf4c20c0d; both downloaded back from PyPI and byte-identical to the tested files.

- R1: #42 (working week, and resource hours read as UTC), #43 (onstart), #44 (shared followers), #46 (0.10.3 regression: recursion on a long chain) closed, each with its verification. Also fixed: the README example project, which had not parsed since 0.10.3.
- R2: scripts/ci.sh passed every step on Python 3.9.25 and 3.13.7 (ruff, mypy, file-size cap, 581 tests, showcase current, 145 probes). The built wheel in clean 3.9 and 3.13 venvs passed 145 probes each. 0.11.0 installed from PyPI on 3.13.7: 11 of 11 working-hours cases give the reference scheduler's dates (0.10.3: 1 of 11), both onstart refusals exit 2, the 3,000-task chain exits 0, probe_directive_effect 57 of 57 and probe_calendar 11 of 11.
- R3: CHANGELOG 0.11.0, "Changes that can move an existing schedule", nine items, each with the line to write.
- R4: 0 hits for the name in the repo (tracked and untracked), the wheel (88 files) and the sdist (284 files); the scanner finds a planted positive.
- R5: voice checker self-test passed and it flags a planted machine-written paragraph. README hits per 1,000 words: before, absolute 8.7, comma tail 6.3, trailing modifier 3.9, colon reveal 3.9, semicolon 3.1, contrast framing 1.6; after, absolute 6.5 (each literally true), and two stubs that are a heading and Farshid's sign-off. Facts dropped on purpose: "No HTML metadata", the csvkit pipe example, the numbered list under the example. tests/test_readme_examples.py runs the example project, the Python example and the command lines as written; two of its three tests fail on the v0.10.3 README.

Not exercised: free-threaded (no-GIL) Python builds; Python 3.10-3.12 for the full suite; a second independent reader for the README.
