# Release 0.10.2 with no known gaps

**Ticket**: issuedb #16  
**Status**: open  
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
