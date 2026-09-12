# ScriptPlan readiness: audit findings S1-S10 (epic)

**Ticket**: issuedb #1  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 1` whenever the spec or the chosen
alternative changes.

---

EARS SPEC (summary; full spec in SPECS/000-readiness-epic.md):
- If any task cannot be scheduled, then ScriptPlan shall return False from Project.schedule(), record an error naming the task and reason, and the CLIs shall exit non-zero.
- If a .tjp file contains an attribute or reference ScriptPlan does not implement or resolve, then ScriptPlan shall raise a parse error naming the line and attribute.
- ScriptPlan shall never call sys.exit or print from library code.
- ScriptPlan shall interpret file dates in the project timezone and honour explicit minute-level start/end and shift boundaries.
- effort shall be person-hours split across allocated resources; duration calendar time; length working time; gapduration calendar; gaplength working; m shall mean months.
- ScriptPlan shall never change the declared project end.
- Calling Project.schedule() twice shall produce identical dates and bookings.
- While a daily/weekly/monthly limit is reached, ScriptPlan shall book no further slots in that period, and shall resume in the next period.
- The pure-Python and compiled paths shall produce identical output for every fixture and probe.
- No source file shall exceed 500 lines.

TECHNICAL PROBLEMS:
1. Fail-closed error propagation across parser -> model -> scheduler -> CLI.
2. Unit and calendar arithmetic in one authoritative module.
3. Time representation: project-timezone ingest; minute-precision working hours independent of slot size.
4. Resource allocation under contention: person-hour effort, mandatory/alternative/persistent.
5. Backward (ALAP) scheduling without a fabricated project end; mixed-direction chains.
6. Idempotent scheduling state.
7. Single implementation path (drop Cython).
8. Verification infrastructure: probe harness, dual-path CI, non-vacuous tests.
9. Reports consuming a stable schedule result.

SOLUTION DOMAINS:
- Scheduling loop / effort semantics / ALAP -> TaskJuggler 3 documented semantics (clean-room; README asserts no TJ source was copied).
- Minute precision with coarse slots -> interval arithmetic + per-day bitmaps (standard calendar-library technique).
- Time model -> stdlib zoneinfo, aware UTC internally; dateutil relativedelta for months (already a dependency).
- Error model -> collect-then-fail with a per-project message collector; exceptions already exist unused in core/exceptions.py.
- Verification -> mission-critical-audit audit/evaluations harness; house CI at ci.rodmena.co.uk (no GitHub Actions).

ALTERNATIVES:
- Scheduling core: new scheduler/engine package keeping the data model [CHOSEN] vs in-place rewrite of task_scenario/project [REJECTED: same work, no old-vs-new diffing while goldens are re-derived] vs incremental patching [REJECTED: cannot deliver minute precision or date-based readiness without rewriting the loop anyway].
- Scoreboard: per-day bitmaps [CHOSEN: ~73KB/resource-year at 1min] vs flat slot list [REJECTED: 525k refs, 37-59s] vs run-length intervals [REJECTED: fragmentation under interleaved booking].
- Compiled path: drop Cython [CHOSEN: the .pyx files accelerate the representation being retired and cause wheel-vs-source divergence] vs keep with parity gate [REJECTED: permanent parity cost].
- Error propagation: collect-then-fail [CHOSEN] vs raise at first error [REJECTED: TaskJuggler collects all errors].

EVIDENCE: 56 live probes, 32 failing on source checkout and 33 on the published cp313 wheel, while all 383 tests pass on both paths.

---

## Closing statement

### What was exercised

Every guarantee in the EARS specs was driven through ScriptPlan's own interface
and asserted: 69 probes across 12 files in `audit/evaluations`, run against the
source checkout on Python 3.9 and against the built wheel installed into a
clean virtualenv, from a directory outside the checkout, so what is verified is
what is shipped. The probes cover error propagation and exit codes, parser
strictness, duration units, the calendar (midnight crossing, leave, local-day
limits, daylight saving in both directions), minute-level precision, every
limit kind in both directions, person-time effort with mandatory and persistent
allocations, backward scheduling and mixed-direction chains, idempotency,
priority contention and report definitions.

Alongside them, 411 tests pass from any working directory without optional
plugins, including a golden snapshot of what all 24 example projects schedule
to, and 16 sub-process tests of the `plan` CLI. `scripts/ci.sh` runs lint,
types, the file-size cap, the tests, the showcase check and the probes: all six
steps pass. Every fixture renders through `plan report` with exit code 0.

Scale exercised: 500 chained tasks at one-minute resolution (3.3s), 500 chained
tasks at one-hour resolution (1.5s against a 3s budget), and 100 tasks over 10
resources for a year at one-minute resolution (about 13s, 92MB peak).

One quantified criterion is not met: that last case was specified at 10s and
takes about 13. It was 58.7s before the audit and 80.5s part-way through it.
The remainder is the per-slot list scoreboard, and the denser representation
that would fix it was not built. This is recorded in SPECS/005 and gated by
probe_scale.py rather than left as a rounded-up "meets budget".

### What was not tested

Concurrency. Nothing runs two schedules in one process on two threads, and the
message handler remains a process-wide singleton that accumulates; the
project-scoped attribute mode was fixed and covered, but thread safety was not
established and should not be assumed.

Python 3.10 through 3.14. Everything here ran on 3.9. The wheel is
`py3-none-any` so there is no per-version build to diverge, but no version
other than 3.9 was exercised.

Long-running service behaviour. Memory over thousands of sequential parses,
and whether anything besides the message handler accumulates, was not measured.

`include`, `supplement`, `leaveallowance`, `statussheet`, accounts end to end,
`timesheet` and `journal` as scheduler inputs. `include` is accepted on the
command line and discarded, which is now the only remaining silent drop I know
of and is recorded in the README's known limits.

Multi-year projects at minute resolution, and sustained load of any kind.

### What I remain unsure about

**`onstart`.** ScriptPlan reads `A depends B { onstart }` as "A must finish
before B starts". TaskJuggler reads it as start-to-start. I left ScriptPlan's
reading in place and documented it, because changing it would move the README's
own worked example and `jit_supply.tjp` depends on it, but it means files
written for TaskJuggler will schedule differently here. This is the one
semantic decision I deferred rather than settled.

**Whether the remaining fixture expectations are TaskJuggler-correct.** Several
were written from this implementation's output rather than derived
independently. I re-derived the ones I changed, and `TestIssue41` and
`TestIssue42` compute theirs by independent simulation, but I could not compare
against real TaskJuggler: it is not available in this environment. Until
someone does, "TaskJuggler-compatible" rests on reading the manual rather than
on running both.

**The loop check.** It follows finish-to-start edges only. A project mixing
`onstart` and ordinary dependencies could in principle describe an unsatisfiable
schedule that it does not catch; a complete check works over (task, start|end)
pairs and was not written.

**Report coverage.** `hidetask` and sorting are now exercised, but the report
layer still has code I did not probe: nested reports, `rollupresource`, period
columns, `loadUnit`, and the text report's rich-text handling. They are not
known to be broken; they are unverified.

Two defects were introduced during the refactoring and caught by the probes
rather than by the tests: a rename that shadowed the task scenario with the
resource's, which silently stopped every booking, and a tiled shift pattern
that repeated one week's holiday across the year. Both are fixed. That the
probes caught them and 411 tests did not is the most useful thing I learned
about this codebase's test coverage.
