# Changelog

## 0.10.0

A readiness audit of 0.9.2 turned every documented claim into a probe that
drives ScriptPlan through its own API or CLI. 32 of those probes failed. This
release is what it took to make them pass, and it changes scheduling results.

### Breaking: `effort` is person-time

`effort 16h allocate a, b` used to occupy both resources for sixteen hours and
credit sixteen hours of work. Two resources booked thirty-two hours, four booked
sixty-four, and the completion date never moved however many were assigned. The
engine took the largest contribution in each slot rather than the sum, so the
labour of every resource but one was booked, billed and discarded.

Effort is now the amount of work to be done, and each allocated resource
contributes its own time towards it, as TaskJuggler defines it. The same task
with two resources finishes in half the time and costs what one resource's worth
of work costs.

**Upgrading.** A task whose allocations were meant to work side by side is
written with `mandatory` and its effort in person-hours:

```
# before 0.10.0: four hours of a pair working together
task deploy "Deploy" { effort 4h  allocate dev, qa }

# 0.10.0 and after
task deploy "Deploy" { effort 8h  allocate dev { mandatory }, qa { mandatory } }
```

Tasks with a single allocation are unaffected. Of the 24 example projects, 21
schedule identically to 0.9.2; the three that differ are those that allocate
more than one resource to a task.

### Breaking: failures are reported as failures

`Project.schedule()` always returned `True`, and the CLI exited 0 with empty
start and end cells. A circular dependency, an effort task with no allocation,
or a task that did not fit the project window produced a warning nobody saw.

Scheduling now returns the real result and names each failing task and why; the
CLIs exit non-zero. A dependency cycle is rejected before scheduling, naming the
cycle. An attribute or reference the parser cannot place is an error rather than
a silent drop, which is how `duration`, `length`, `complete` and `note` reached
the model for the first time.

### Breaking: the declared project period is honoured

The project end was grown by a heuristic before scheduling. It is now taken as
written, and a task that does not fit is reported. Projects that relied on the
extension need their period stated honestly.

### Breaking: unimplemented report formats are rejected

`ical`, `tjp`, `niku`, `ctags` and MS Project XML were accepted, wrote no file,
and left the CLI blaming a scheduling problem that did not exist. They now raise
at parse time. Use `json` or `csv`.

### Fixed

- Durations follow one table: `m` is months and `min` is minutes everywhere;
  `duration` and `gapduration` are calendar time, `effort`, `length` and
  `gaplength` working time derived from `dailyworkinghours` and
  `yearlyworkingdays`. `gapduration 2d` was 16 hours; `gaplength 30min` was no
  gap at all; `limits { dailymax 30min }` was a 4800-hour cap.
- Limits count seconds in the resource's own calendar and admit part of a slot,
  so `dailymax 6.4h` is exact. A resource in Los Angeles capped at four hours a
  day was working five in one of its own days. `dailymin`, `weeklymin`,
  `monthlymax`, `monthlymin`, `maximum` and `minimum` reach the grammar, as do
  `maxend`, `maxstart`, `minend` and `minstart`, and violations are reported.
- Dates are read in the project's timezone and scheduled in UTC; reports convert
  back. The default working day was compared against the hour of a UTC slot,
  putting a New York project five hours out.
- Slot size is derived from the times a project uses, so `start 09:30` and a
  shift of `08:13 - 11:59` are exact without setting `timingresolution`. That
  shift was credited with seven hours a day instead of eight and a half.
- A working-hours interval crossing midnight applies to the following day.
  `fri 22:00 - 06:00` marked Friday morning instead of Saturday.
- Chains mixing ASAP and ALAP schedule instead of deadlocking.
- Scheduling twice gives the same dates and the same bookings. The second run
  kept the dates and discarded every booking.
- Reports honour their own `sorttasks`, `hidetask`, column options and formats,
  and `plan report` renders the reports a project declares rather than
  substituting a three-column one. Descending sort was a no-op, and any filter
  hid every row.
- `report_id` is a SHA-256 of the rendered result. It hashed the input file, so
  a correct and a broken schedule of the same input shared an id.
- `mandatory`, `persistent` and per-resource allocation options work; they
  parsed to nothing.

### Removed

- The Cython extensions. Under `cdivision` the compiled path computed
  `(0 - 1) % 7` as `-1`, so a resource with a Sunday night shift lost its Monday
  morning in every published wheel and kept it in every source checkout: the
  same file, two schedules, and no test covering the compiled one. The wheel is
  now pure Python and cannot diverge from its source.
- `scheduler.batch_processor`, `utils.data_cache.DataCache` and `utils.Log`,
  none of which were reachable.

### Performance

500 chained tasks at minute resolution schedule in 3.3s, from 14.4s. A year at
minute resolution with ten resources takes about 13s, from 58.7s.

### Verification

`audit/evaluations/` holds 74 probes across 12 files, each named after the
behaviour it would falsify and each driving ScriptPlan through its own
interface. `scripts/ci.sh` runs lint, types, a file-size cap, 411 tests, a
showcase currency check and the probes. The probes also pass against the built
wheel installed in a clean virtualenv, so what is verified is what ships.

## 0.9.2 and earlier

See the git history.
