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
