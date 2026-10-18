# Release 0.10.2 with no known gaps

**Ticket**: issuedb #16  
**Status**: closed (released in 0.10.2)  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 16` whenever the spec or the chosen
alternative changes.

---

Release 0.10.2: close every known gap left by 0.10.1 (Farshid, 2026-10-17: "the next release should fix all known gaps").

EARS SPEC:
- R1 (ubiquitous) 0.10.2 shall resolve #12, #13 (including the 0.10.1 alap duration/length regression), #14 and #15, each verified against its own EARS lines with a probe or test that fails on 0.10.1 and passes on 0.10.2.
- R2 (unwanted) If work on 0.10.2 finds another defect, then it shall be fixed in 0.10.2 or the release shall not go out; the changelog shall have no "not fixed" entries unless Farshid accepts one by name.
- R3 (ubiquitous) The full gate (scripts/ci.sh) shall pass on Python 3.9 and on Python 3.13; the probe harness shall pass against the built wheel in a clean venv; the PyPI-served wheel hash shall equal the tested wheel.
- R4 (ubiquitous) The changelog shall name the 0.10.1 regression as a regression, with the case that shows it.
- R5 (quality) The slowest example fixture shall schedule within 110% of its 0.10.1 time (median of 3, same interpreter, interleaved).

---

RELEASED as scriptplan 0.10.2 (commit b1dbe19, tag v0.10.2, GitHub release v0.10.2). PyPI wheel sha256 afaa45353baf1b779ef5b7ec677482e59cce88c85bdd2554848bec9a4604da69, sdist aeb73459e69f46ea770b3866db9f269cfc92cb0a27c0f153609452603ef73b5c; both downloaded back from PyPI and byte-identical to the tested files.

- R1: #12, #13, #14, #15 closed, each with its verification. Edge cases that fail on 0.10.1 and pass on 0.10.2: 13 of 24. probe_placement: 300/300 plans on 0.10.2, 28 on 0.10.1, 14 on 0.10.0.
- R2: defects found during the work were fixed in 0.10.2 as #17-#29 (including the trace reports #21-#25, the CLI double scheduling #26, the final-slot sharing #27, threads #28, failure messages #29). The changelog has no "not fixed" entry. One item from trace was not changed. Trace defect 2 (onstart on an alap task) keeps ScriptPlan's documented reading (finish before the predecessor starts), because the README's example project jit_supply depends on it: under start-to-start its dependencies form a loop. Farshid saw this listed as "not treated as a defect" before release and answered "do the release". He has not accepted it by name, and it is reported to him again with the release.
- R3: scripts/ci.sh passed every step on Python 3.9.25 and 3.13.7 on the released tree (ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes). The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks and 3 thread tests. The served wheel hash equals the tested wheel's (above). 0.10.2 installed from PyPI on 3.13.7 gives the expected result for all 17 trace TJPs.
- R4: CHANGELOG "Regressions in 0.10.1" names both, with cases (16:20 successor; 14:30 and 09:30 skipped time).
- R5: math_torture.tjp (slowest) 5.533 s on 0.10.2 vs 5.992 s on 0.10.1 (92%); tutorial 87%; three smaller projects 17-29% (mostly #15, grammar built once). Python 3.9.25, interleaved, median of 3, load average 3-4.

After release, two test-only additions (no package change): tests/test_reference_and_duration.py covers #18's ambiguity refusal and #20's duration over a weekend through the CLI; both fail on v0.10.1.

Not exercised: free-threaded (no-GIL) Python builds; Python 3.10-3.12 for the full suite (3.9 and 3.13 only); thread concurrency beyond 15 threads in one process.
