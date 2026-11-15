# README Python example prints UTC as if it were project time (Siambr)

**Ticket**: issuedb #41  
**Status**: closed on main after 0.10.3. The PyPI page shows it from the next release.  
**Priority**: medium  
**Release**: documentation only, no package change

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 41` whenever the spec or the chosen
alternative changes.

---

Reported by siambr-api (AgentBus delivery 01M7EZ90R7RYAFKCZEQK3YHDR3): `task.get('start')` returns a naive datetime in UTC even with timezone "Europe/London". A task starting 00:00 BST reads 23:00 the day before, and their first version took the wrong date from it. Confirmed on 0.10.3 from PyPI: start 2026-06-02-00:00 reads `datetime(2026, 6, 1, 23, 0)`, tzinfo None. This is the model's documented design (scriptplan/core/timezones.py), but the README's own Python example printed the value with no conversion.

EARS SPEC:
- R1 (ubiquitous) The README's Python API example shall print each task's dates in the project's timezone, using `scriptplan.core.timezones.from_utc`, and shall state that `task.get('start', 0)` and `task.get('end', 0)` are naive UTC.
- R2 (quality) The example, run as written against the installed package on a Europe/London project with a task starting 2026-06-02-00:00, shall print 2026-06-02 00:00:00.

Synthesis (docs only): the concept is the existing `from_utc` helper.

ALTERNATIVES:
- Document and show the conversion [CHOSEN].
- Return timezone-aware datetimes from `task.get` [REJECTED by Farshid, 2026-11-15: "leave it"]. It would change the type every caller of the API receives, and Siambr confirmed the helper covers them.

---

VERIFICATION (2026-11-15): the example was cut out of README.md by script and run unchanged against scriptplan 0.10.3 installed from PyPI (Python 3.13). On a Europe/London project with `start 2026-06-02-00:00` it prints `t: 2026-06-02 00:00:00 -> 2026-06-02 02:00:00`. The example as it stood at v0.10.3 prints `t: 2026-06-01 23:00:00 -> 2026-06-02 01:00:00` on the same file, which is the fault. On a project that sets no timezone the new example prints `2026-06-02 00:00:00` and exits 0.
