# Changelog

## 0.10.2

0.10.1 shipped two regressions. This release fixes them and the gaps 0.10.1 listed as
not fixed. It also fixes the defects found while checking every example project
against answers worked out without the engine, and the thirteen that Trace reported.
Several plans that 0.10.1 scheduled silently and wrongly are now refused with an error
that names the task and the date it cannot keep.

### Regressions in 0.10.1

- An alap `duration` or `length` task before a successor that starts inside a slot
  ended after that successor started. Before a task starting at 16:20, a 1-hour
  duration ran 16:00-17:00. It now runs 15:20-16:20. 0.10.0 put it at 15:00-16:00.
- Time a task skipped to honour a mid-slot start or end was lost to every other task.
  After an alap task that had to end at 14:30, a task free from 14:00 ran 15:00-16:00
  instead of 14:30-15:30. Before a task declared to start at 09:30, a task free from
  09:00 was pushed to 10:00 instead of using 09:00-09:30.

Each booking now holds its own interval of the slot, so time a task skips stays free
and a task that finishes early frees only what follows it.

### Fixed: wrong schedules

- A `duration` or `length` task after a task ending mid-slot started at the top of
  that slot, before its predecessor finished. It now starts when the predecessor ends
  and lasts its duration or length to the second.
- A `duration` waited for working time. After a task ending Friday 17:00 a 2-hour
  duration ran Monday 09:00-11:00, and it now runs Friday 17:00-19:00. An alap 2-hour
  duration that had to end on a Sunday spanned 48 hours, and it now spans 2.
- A task's finish depended on `timingresolution` when several people shared its last
  slot, because only the first of them worked it. In `tutorial.tjp` the project ended
  at 12:48, 12:00 or 11:44 depending on the slot size alone. All of them now work the
  last slot, and the answer is the same at every resolution.
- An alap milestone sat a slot before the moment it had to be at. Before a task
  starting at 16:00 it was placed at 15:00. It now sits at 16:00, and one with no
  successor sits at the project end.
- An alap task did not keep the gap its successor asked for. With `gapduration 24h`
  it ended where the successor began, and now it ends 24 hours earlier.
- An alap task with an `end` of its own ignored its successors and could end after
  one had started. It now ends by the earlier of the two.
- An alap task whose successor states its start was moved to the project start, as
  though nothing bounded it. It now ends as late as that start allows.
- A `start` inherited from a container overrode the task's dependencies. It is now an
  earliest start, and the task waits for what it depends on.

### Fixed: silent wrong schedules are now errors

Each of these exits non-zero with a message naming the task and both dates:

- a task that would start before a task it depends on ends, including when its own
  `start` says so, with or without a gap, and for milestones;
- a stated `end` that a task scheduled as soon as possible, or its container, cannot
  meet, which 0.10.1 overran by hours;
- a stated `start` that an alap task cannot keep;
- a stated start or end outside the project window. A start after the window used to
  crash with "Error parsing project file: list index out of range", and an end after
  it was clamped while the milestone was dated outside the project.

An alap task that cannot fit before its deadline now names that deadline. A task
whose successor failed is reported as blocked by it. 0.10.1 blamed the project window
for the first, and moved the second to the start of the project, booked after the
deadline.

### Fixed: other

- A reference that could mean two tasks with the same id bound whichever came first.
  It is now an error that lists both.
- `getAllocatedTime()` and timesheet figures credited a shared slot to the last task
  booked in it. 40, 13 and 40 minutes in one hour read as 0, 0 and 2 hours, and now
  read as 0.67, 0.22 and 0.67.
- Each `ProjectFileParser()` compiled the grammar again (about 0.7 s). The grammar is
  now compiled once per process.
- The `plan` CLI scheduled every project twice and reported any exception raised
  while scheduling as a parse error. It now schedules each project once and reports
  a scheduling exception as a scheduling error.
- Projects scheduled in parallel threads shared one message list, one error count
  and one switch that turns error collection on. When one thread finished scheduling,
  another thread's error could raise `TjRuntimeError` out of `schedule()` instead of
  making it return False, and an error in one project could fail another. Each thread
  now has its own messages, error count and switch.
- An `effort` task with no resource allocated was reported as running outside the
  project window because it "needs more time or more resource availability". It is now
  reported as having effort but no resource to do it.
- `plan report` printed every engine error as "Error: Error: …". It now prints one
  "Error:".

### Documentation

- README described `onstart` as one reading for both directions. For a task scheduled
  as soon as possible it is start-to-start. For one scheduled as late as possible it
  means the task must finish before the predecessor starts.
- README now says that `length` and `gaplength` count the project's working time, how
  an alap task's end is bounded, and that unkept stated dates are errors.
- README listed `maxgaplength` among the checked constraints. The syntax has never
  accepted it, and the claim is removed.

### Schedules that move

A plan whose dates all fall on its slot grid, with no alap milestones and no
`duration` across non-working time, schedules as it did in 0.10.1. Of the 24 example
projects, 22 schedule identically:

- `tutorial.tjp`: `spec` ends 14:20 instead of 15:00 on 24 January because three
  developers finish it together, and every task after it moves with it. The project
  ends on 18 April at 11:44 instead of 12:48.
- `jit_supply.tjp`: the alap milestone `connection_setup.set_deps` sits at 2025-07-18
  08:00, when `pack` starts, instead of 2025-07-17 16:00.

### Internal API

`ResourceScenario.reserve()` returns a list of `SlotBooking`, one per free stretch it
books. The slot ledger is `slotIntervals`, and `slotFrontUsed` and `slotBackUsed` from
0.10.1 are gone. Failure handling moved to `scriptplan.scheduler.stalls`, and stated
dates are tracked in `scriptplan.core.declared_dates`. `slotSecondsUsed` is now
exactly the sum of `slotTaskUsage` for every slot.

### Verification

The golden snapshots record what the engine produced last time. They catch a change
but not an error, and 0.10.1 passed all of them. `examples/` now holds an answer for every
task in the 24 showcase projects and in 24 edge cases, each derived by hand from
the file and the documented semantics without running ScriptPlan, and compared with an
hour-level reference scheduler wherever it accepts the file. `tests/test_examples.py`
runs each project through the `plan` CLI and compares every task to the second. Every
project passes on 0.10.2, and 13 of the edge cases fail on 0.10.1.

`audit/evaluations/probe_placement.py` generates 300 plans that mix effort, duration,
length and milestones in both directions. It checks that every dependency, stated date
and span holds, that no slot is overfull, and that no task leaves free time it could
have used. All 300 pass on 0.10.2, against 28 on 0.10.1 and 14
on 0.10.0.

`tests/test_threads.py` schedules five projects three times each in parallel threads
and compares every date and message with the same project scheduled alone. It also
forces one thread to leave error collection while another is still inside it. Its
three tests fail on the 0.10.1 message handler.

The full gate runs on Python 3.9 and 3.13.

## 0.10.1

Tasks that shared a timing slot on one resource could be booked into time that
does not exist. Three tasks of 40, 13 and 40 minutes on one person at
`timingresolution 60min` all started at 09:00, and the 09:00 slot held 5580
seconds of work without any warning. Every release from 0.9.0 to 0.10.0 has
the defect. Trace's scheduling harness found it.

When a task finished part-way through a slot, the engine gave the rest of that
slot back as if the task had booked all of it, even when an earlier task had
already used the front of the slot. It also placed every later task at the top
of the slot. Each booking now records where in the slot it sits. Forward work
fills a slot from its start and backward (`alap`) work from its end, and a task
that finishes early hands back only the part of its own booking it did not use.
The same three tasks now run 09:00-09:40, 09:40-09:53 and 09:53-10:33 at any
resolution.

### Fixed

- A task whose first slot was partly used reported its start at the top of that
  slot. At 5-minute resolution the third task above started at 09:50 while the
  second ran until 09:53. It now starts at 09:53.
- `alap` tasks sharing a slot overbooked it the same way. They now fill it
  backwards from the end without overlapping.
- When several resources finished a task in the same slot, only one of them
  handed back its unused time. 80 minutes of effort on two people ended at
  10:00 and cost two hours. It now ends at 09:40 and costs 80 minutes.
- Time handed back was not returned to `limits`. Under `dailymax 60min` the
  three tasks above took Monday, Tuesday and Wednesday, and the person worked
  40 minutes on Monday. They now use exactly 60 minutes on Monday and finish on
  Tuesday at 09:33.
- A task that could start mid-slot because its predecessor ended there was kept
  out of the first part of every slot until it booked something. When the
  resource was busy in that slot, the task lost the same minutes in the next
  one, and a task free to start at 10:00 started at 10:50.
- A `start` inside a slot was rounded down. `start 2026-10-19-09:30` at 60-minute
  resolution started at 09:00, half an hour before the date in the file. A
  mid-slot `end` on an `alap` task was also rounded down to the start of its
  slot. Both are now honoured to the minute.
- A milestone after a task that ended mid-slot sat at the top of that slot,
  before its predecessor had finished. It now sits at the moment the
  predecessor ends.

### Schedules that move

A plan in which no work starts or ends inside a slot schedules as it did in
0.10.0. Results change where efforts are off the slot grid, where an efficiency
other than 1 makes work end mid-slot, where several resources share a task, and
where a date falls inside a slot. Of the 24 example projects, 22 schedule
identically to 0.10.0:

- `airport_stress_test.tjp`: `t_install` starts at 11:40 instead of 11:00,
  which is when the electrician finishes `t_crit`. `t_low` starts at 10:20
  instead of 10:00 for the same reason. Both keep the end times they had.
- `tutorial.tjp`: `test.alpha` ends at 11:36 instead of 12:00 on 3 April because
  both people on it stop together. `test.beta` and the project finish at 12:48
  instead of 13:00, and the `beta` and `done` milestones follow.

### Not fixed in this release

A `duration` or `length` task that depends on a task ending mid-slot still
starts at the top of that slot, before its predecessor has finished. After a
task ending at 09:40, `duration 2h` is reported as 09:00-11:00. 0.10.0 does the
same. `TaskScenario.getAllocatedTime()` still credits a shared slot to the last
task booked in it, although cost is correct.

### Internal API

`ResourceScenario.book()` takes a `forward` argument. `reserve()` and
`release()` are new and return or take a `SlotBooking` from
`scriptplan.core.slot_ledger`. `markSlotPartiallyUsed()` and
`releasePartialSlot()` had no callers and are removed. `slotSecondsUsed` also
counts the time a task skips to honour a mid-slot start or end. To measure the work
booked in a slot, sum `slotTaskUsage`.

### Verification

The probe named "Two tasks sharing one resource never double-book a slot" used
efforts of whole hours, which never share a slot, and it checked the total
booked, which stays correct when work overlaps. Every capacity check in the
harness read `slotSecondsUsed`, and the defect lowered that counter in the same
step that overbooked the slot. None of them could fail on this defect.

`audit/evaluations/probe_slot_sharing.py` checks each slot against what was
booked into it, compares the CLI's report with dates worked out by hand, and
runs 360 seeded random plans, 240 of them with efforts anywhere from 1 to 600
minutes. Against 0.10.0 all nine of its probes fail, including the 490-minute
day Trace reported, and 115 of those 240 plans break at least one of its
checks. Against 0.10.1 all nine pass. The harness now sums `slotTaskUsage`
wherever it measures booked time.

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
contributes its own time towards it, as the .tjp format defines it. The same task
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
