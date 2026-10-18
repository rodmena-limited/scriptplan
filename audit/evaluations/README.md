# ScriptPlan audit harness

One probe per claim, each named after the behaviour it would falsify. Every
probe drives ScriptPlan through its own API or its `plan` CLI, and prints
`PASS`/`FAIL` with the evidence it observed rather than a bare exit code.

```bash
./run_all.sh                                   # safe set
SCRIPTPLAN_PROBE_SLOW=1 ./run_all.sh           # plus the performance probes
SCRIPTPLAN_PROBE_PYTHON=/path/to/python ./run_all.sh
```

The package under test is whatever `import scriptplan` resolves to, so the
same files run unchanged against a source checkout, an installed wheel, or a
release candidate in a fresh virtualenv. Each run prints the resolved package
path and which accelerated modules are active.

| File | Claim area | SPEC |
|---|---|---|
| `probe_error_propagation.py` | failures are reported as failures; report_id covers the result | `SPECS/002` |
| `probe_parser_strictness.py` | what the file says reaches the scheduler | `SPECS/002` |
| `probe_units.py` | duration/effort/gap unit conversion | `SPECS/003` |
| `probe_calendar.py` | midnight crossing, leave, local days, DST | `SPECS/003` |
| `probe_precision.py` | minute-level starts and shift boundaries | `SPECS/004` |
| `probe_limits.py` | every quota blocks **and** releases | `SPECS/003` |
| `probe_effort_semantics.py` | effort is person-time; cost charged once | `SPECS/005` |
| `probe_slot_sharing.py` | tasks sharing a slot share its time; nothing overbooked, lost or invented | `SPECS/011` |
| `probe_placement.py` | every dependency, stated date and span holds; no task leaves usable time idle | `SPECS/013`, `SPECS/014`, `SPECS/017` |
| `probe_alap.py` | backward scheduling; declared project end | `SPECS/005` |
| `probe_idempotency.py` | scheduling twice gives the same answer | `SPECS/005` |
| `probe_priority.py` | regression guard: priority contention already works | `SPECS/005` |
| `probe_reports.py` | reports honour their own definitions | `SPECS/008` |
| `probe_showcase_regression.py` | the 24 example projects still schedule as they did before the audit | `SPECS/001` |
| `probe_scale.py` | performance budgets (opt-in, slow) | `SPECS/005` |

## Rules this harness follows

- **Both directions for every guard.** A cap is probed for blocking *and* for
  releasing; a cap tested only for blocking is how a queue deadlocks forever.
- **No self-confirming checks.** Expected values are computed from the stated
  semantics, never read back from the implementation. Booked time is summed
  from `slotTaskUsage`, never read from `slotSecondsUsed`: that counter is what
  the slot-sharing defect corrupted (`SPECS/011`), so it cannot be the witness.
- **Safe by default.** No probe writes to the repository or to a shared
  service; there is no destructive probe, so `run_all.sh` needs no opt-in.
- **A probe that goes red must first have been able to go green.** When a probe
  is added for a defect, it is also run against the fixed behaviour before the
  finding is closed.
- **A deliberate change is recorded, not absorbed.**
  `probe_showcase_regression.py` compares every example project against the
  schedule it produced before the audit, and names the three that differ and
  why. It fails if any other project moves *and* if one of those three stops
  differing: a change that quietly reverts is as much a surprise as one that
  quietly appears.

When a claim changes, update its probe in the same change. A probe asserting a
stale contract is itself a self-confirming check.
