# tutorial.tjp - independent derivation, scenario `plan`

Source: `src/tutorial.tjp` (the the reference scheduler tutorial). Scenario derived: `plan`, the first one.
`delayed:` attributes (`delayed:start 2002-01-20`, `delayed:effort 40d`) are ignored.
Output: `tutorial.expected.csv`, 15 rows (4 containers, 7 effort leaves, 4 milestones), times in
the project timezone **Europe/Paris**, wall clock.

Tools (stdlib Python, none imports scriptplan), all in `tutorial_work/`:
- `tutorial_sim.py` places the tasks at second precision with exact fractions; `mode=parallel`
  is the primary reading, and the other modes and flags compute the alternatives below. Every run
  asserts that no resource is booked twice at once, every limit is respected, and every task's
  bookings add up to its effort.
- `daily_table.py` prints the per-day bookings in the appendix.
- `tj_custom.py` runs the reference scheduler with a custom report; `probe_*.tjp` are the the reference scheduler probes cited below.

Every number in the walk-through below was first worked by hand. The simulator then reproduced
all of them. It also reproduces the reference scheduler's output exactly (15/15 rows) once the reference scheduler's own
slot rule is switched on (see the the reference scheduler section), so the simulator's calendars, leaves, limits and
placement order are checked against an independent implementation.

## Inputs

**Calendar.** No resource has `workinghours`, so each one works ScriptPlan's default,
Mon-Fri 09:00-17:00 local (480 min a day). Nothing in the file is calendar time (no `duration` or
`gapduration`), so the DST change on Sun 2002-03-31 at 02:00 never touches working time. Every
working day is 09:00-17:00 local before and after it.

**Leaves.**
- Global `leaves holiday "Good Friday" 2002-03-29`: all resources, the whole of Fri 29 March.
- dev3 `leaves annual 2002-02-01 - 2002-02-05`: Fri 1 Feb and Mon 4 Feb (2-3 Feb are a weekend).
  The end date is exclusive, which is the reference scheduler's documented rule. See AMBIGUOUS A3.
- doc `leaves annual 2002-03-11 - 2002-03-16`: Mon 11 to Fri 15 March. The 16th is a Saturday,
  so inclusive and exclusive readings agree. doc is free by then anyway: manual ends 26 Feb.

**Limits.**
- test: `dailymax 6.4h` = 6 h 24 min = **384 min per local day**. It is a resource limit, so it
  counts everything test does that day (alpha and beta share 3 April).
- gui: `dailymax 6h { resources dev2 }` = **360 min per day of dev2's work on gui**, a task limit.
  dev3 has no cap on gui.

**Units.** d = 8 h, w = 5 d = 40 h (see A4).

| task | effort | person-min | allocations | depends | priority |
|---|---|---|---|---|---|
| spec | 20d | 9600 | dev1, dev2, dev3 | deliveries.start | 500 |
| software.database | 20d | 9600 | dev1, dev2 | spec (inherited from `software`) | 1000 (inherited) |
| software.gui | 35d | 16800 | dev2 (360/day cap), dev3 | spec, database, backend | 1000 |
| software.backend | 30d | 14400 | dev1, dev2 | spec, database | 1000 |
| test.alpha | 1w | 2400 | test (384/day), dev2 | software (= its three children) | 500 |
| test.beta | 4w | 9600 | test (384/day), dev1 | alpha | 500 |
| manual | 10w | 24000 | doc, dev3 | deliveries.start | 500 |
| deliveries.start | milestone | - | - | `start ${projectstart}` | |
| deliveries.prev / beta / done | milestones | - | - | backend / alpha / beta + manual | |

`complete 95` on backend, `now`, rates, charges, accounts, journal entries and reports do not
affect dates (see A6 for `complete`). The project window is 2002-01-16 00:00 + 4 m
(4 x 30.4167 d = 121.67 d, to about 2002-05-17 16:00), and every task ends before 18 April.

## Placement order and contention

Tasks are placed whole. Each pass places the first task in the sort order (priority desc, then
criticalness desc, then declaration order) whose predecessors are all placed. That gives:
`deliveries.start`, **spec**, database, backend, gui, manual, alpha, beta, then the milestones.

- **dev3 is contested by spec and manual**, which are both ready at the project start with
  priority 500. spec goes first: its path criticalness (the reference scheduler-style, 531 vs 177 in the
  simulator's units) is higher, and it is also declared first. See AMBIGUOUS A2 for the reading
  that puts manual first.
- dev3 is also on gui (priority 1000, so placed before manual), but gui starts on 28 Feb, after
  manual has finished on 26 Feb. The order between those two changes nothing.
- dev1 and dev2 move spec -> database -> backend -> gui/alpha/beta strictly in dependency order,
  so they never overlap. test moves alpha -> beta, and the two share 3 April under the 384-min cap.
- Priority inheritance (1000 for software's children) changes nothing here. Inheriting `depends
  !spec` from the `software` container is essential: without it, database would start at the
  project start.

## Derivation, task by task (minutes are person-minutes unless stated)

**AcSo.deliveries.start** (milestone): `start ${projectstart}` = the project start,
**2002-01-16-00:00** Paris (dates are read in the project timezone). start = end. See A5.

**AcSo.spec**: the earliest start is the milestone, Wed 16 Jan 00:00, and the first working
minute is 09:00. dev1, dev2 and dev3 are all free: 3 x 480 = 1440 a day.
16, 17, 18, 21, 22, 23 Jan = 6 days = 8640. That leaves 960 for Thu 24 Jan: 960 / 3 = 320 min
each, 09:00 + 5:20 = **14:20**.
-> 2002-01-16-09:00 .. **2002-01-24-14:20**. (dev3 is busy here, so manual cannot have it yet.)

**AcSo.software.database**: earliest = spec end, 24 Jan 14:20. dev1 and dev2 stop spec at
14:20 and are free. Two people make 960 a day, and 9600 / 960 = 10 working days exactly.
24 Jan 14:20-17:00: 160 x 2 = 320. The 9 full days 25, 28, 29, 30, 31 Jan and 1, 4, 5, 6 Feb
add 8640, total 8960. Thu 7 Feb: 640 / 2 = 320 each -> **14:20**.
-> **2002-01-24-14:20 .. 2002-02-07-14:20**.

**AcSo.software.backend**: earliest = database end, 7 Feb 14:20. 14400 / 960 = 15 days exactly.
7 Feb: 320. The 14 full days 8, 11-15, 18-22, 25-27 Feb add 13440, total 13760.
Thu 28 Feb: 640 / 2 = 320 each -> **14:20**.
-> **2002-02-07-14:20 .. 2002-02-28-14:20**.

**AcSo.deliveries.prev** (milestone after backend) -> **2002-02-28-14:20**.

**AcSo.software.gui**: earliest = max(spec, database, backend ends) = 28 Feb 14:20. dev2 (at most
360 a day on gui) and dev3 (480) make 840 a day.
28 Feb 14:20-17:00: dev2 160 (under its cap) + dev3 160 = 320.
The 19 full days 1 Mar, 4-8, 11-15, 18-22 and 25-27 Mar add 19 x 840 = 15960, total 16280.
Each of those days dev2 works 09:00-15:00 and dev3 09:00-17:00.
Thu 28 Mar: 520 left, both from 09:00, 260 each -> **13:20** (dev2's 260 < 360).
Good Friday is not reached.
Check: dev2 160 + 19 x 360 + 260 = 7260 min = 121 h; dev3 160 + 19 x 480 + 260 = 9540 min = 159 h;
121 + 159 = 280 h.
-> **2002-02-28-14:20 .. 2002-03-28-13:20**.

**AcSo.software** (container) = database start .. gui end = **2002-01-24-14:20 .. 2002-03-28-13:20**.

**AcSo.test.alpha**: `depends !!software` -> earliest = software end, 28 Mar 13:20. test is idle
and dev2 is free from 13:20.
Thu 28 Mar 13:20-17:00: 220 + 220 = 440.
Fri 29 Mar is Good Friday, then a weekend (with DST on Sunday).
Mon 1 Apr: test 384 (09:00-15:24, cap) + dev2 480 = 864, total 1304.
Tue 2 Apr: 864, total 2168.
Wed 3 Apr: 232 left, 116 each from 09:00 -> **10:56**.
-> **2002-03-28-13:20 .. 2002-04-03-10:56**.

**AcSo.deliveries.beta** (milestone after alpha) -> **2002-04-03-10:56**.

**AcSo.test.beta**: earliest = alpha end, 3 Apr 10:56.
Wed 3 Apr: test has already worked 116 min on alpha today, so its cap leaves 384 - 116 = 268
(10:56-15:24). dev1 works 10:56-17:00 = 364. That makes 632.
The 10 full days 4, 5, 8-12 and 15-17 Apr add 10 x (384 + 480) = 8640, total 9272.
Thu 18 Apr: 328 left, 164 each from 09:00 -> **11:44** (test's 164 < 384).
-> **2002-04-03-10:56 .. 2002-04-18-11:44**.

**AcSo.test** (container) = **2002-03-28-13:20 .. 2002-04-18-11:44**.

**AcSo.manual**: earliest = the start milestone. doc works from 16 Jan 09:00. dev3 is on spec until
24 Jan 14:20 and on leave 1 and 4 Feb. gui's claim on dev3 starts after manual ends.
- 16-23 Jan, doc only: 6 x 480 = 2880.
- 24 Jan: doc 480 + dev3 160 (14:20-17:00) = 640, total 3520.
- 25 and 28-31 Jan: 5 x 960 = 4800, total 8320.
- 1 Feb and 4 Feb, doc only: 960, total 9280.
- 5-8 Feb: 3840, total 13120.
- 11-15 Feb and 18-22 Feb: 9600, total 22720.
- 25 Feb: 960, total 23680.
- Tue 26 Feb: 320 left, 160 each -> **11:40**.

-> **2002-01-16-09:00 .. 2002-02-26-11:40**. (doc 234 h 40 min + dev3 165 h 20 min = 400 h.)

**AcSo.deliveries.done** (milestone): max(beta end 18 Apr 11:44, manual end 26 Feb 11:40) ->
**2002-04-18-11:44**.

**AcSo.deliveries** (container) = start milestone .. done = **2002-01-16-00:00 .. 2002-04-18-11:44**.

**AcSo** (root container) = **2002-01-16-00:00 .. 2002-04-18-11:44**.

No task is UNSCHEDULABLE.

## AMBIGUOUS points

**AMBIGUOUS A1 (the important one): several resources in a task's last slot.** The project uses
only whole hours, so the derived slot is 1 h. At 24 Jan 14:00, spec has 60 person-min left and
dev1, dev2 and dev3 are all free.
- *Chosen:* all three keep working together and finish at **14:20**. This follows the brief
  ("each allocated resource available contributes its own time", "two resources available
  together halve the elapsed time", "work is placed to the minute") and SPECS/011 R6 ("end the
  task at the earliest moment their combined work covers the remaining effort"). It also does
  not depend on the slot size.
- *Alternative:* inside a slot the resources are booked one after another in allocation order,
  and no further one is booked once the remainder is covered. dev1's hour alone covers the 60
  min, so spec ends at **15:00**, dev2 idles 14:00-15:00 and dev3 goes to manual at 14:00. This
  is the reference scheduler's rule. The same rule decides the last slot of alpha (two people, 72 min left at
  11:00: shared, 11:36) and of beta (48 min left at 12:00: test alone, 12:48).
- The two readings differ on **14 of 15 rows** (every row except deliveries.start), shown in the
  table below.
- **Evidence the engine may follow the alternative:** CHANGELOG 0.10.1 reports "test.alpha ends
  at 11:36 ... on 3 April" and "test.beta and the project finish at 12:48". `mode=seqslot` at
  R = 1 h reproduces both numbers exactly. The primary reading gives 10:56 and 11:44.
- The alternative's answer moves with the slot size (`mode=seqslot R=...`):

  | R | spec end | alpha end | beta end | manual end |
  |---|---|---|---|---|
  | 60 min | 15:00 | 11:36 | 12:48 | 12:00 |
  | 30 min | 14:30 | 11:12 | 12:00 | 11:30 |
  | 15 min | 14:30 | 11:12 | 12:00 | 11:45 |
  | 5 min | 14:20 | 10:57 | 11:45 | 11:40 |
  | 1 min | 14:20 | 10:56 | 11:44 | 11:40 (at 1 min all 15 rows equal the primary reading) |

  A minute-precise result that depends on `timingresolution` contradicts the brief's statement
  that a task may start or end inside a slot. That is why the parallel reading is the primary one.

**AMBIGUOUS A2: spec vs manual for dev3.** The brief says "then criticalness" without defining
it.
- *Chosen:* path criticalness (a task plus its longest chain of successors, the reference scheduler's sort
  key), which puts spec first. Declaration order agrees, and the reference scheduler places spec first.
- *Alternative:* the task's own criticalness (effort x resource criticalness) is 176.7 for manual
  vs 88.1 for spec, so manual goes first. dev3 then works manual from 16 Jan, spec gets only
  dev1 and dev2 and ends 29 Jan 17:00. Everything downstream ends about 3 working days later
  (done 2002-04-23-15:24), while manual ends earlier (2002-02-20-17:00). See the table.

**AMBIGUOUS A3: the end date of `leaves annual 2002-02-01 - 2002-02-05` (dev3).**
- *Chosen:* the end is exclusive (midnight starting 5 Feb), which is the reference scheduler's documented
  interval rule ("the day of the end date is not included").
- *Alternative:* inclusive (5 Feb is also off). Only **manual** moves: its end becomes
  **2002-02-26-15:40**.
- The the reference scheduler run tells the two apart: the reference scheduler-rule simulation with an inclusive leave gives manual
  2002-02-26-16:00, while the reference scheduler itself gives 12:00.

**AMBIGUOUS A4: the length of a week.**
- *Chosen:* w = 5 d = 40 h, which is the brief's stated result, the reference scheduler's value, and the value
  under which the CHANGELOG's 11:36 is reproduced.
- *Alternative:* the brief's own formula taken literally, d x 260 / 52.1429 = 4.98630 d = 39 h
  53 min 25.4 s. That moves alpha's end to 2002-04-03-10:52:43 (and deliveries.beta and beta's
  start with it), beta's end to 2002-04-18-11:27:33 (and done, test, deliveries and AcSo with it),
  and manual's end to 2002-02-26-11:07:07.

**AMBIGUOUS A5: the project start instant.**
- *Chosen:* 2002-01-16-00:00 Paris, because dates are read in the project timezone.
- *Alternative:* 01:00 Paris, the reference scheduler's reading. the reference scheduler parses the header date before it has seen
  `timezone`, so it reads it as UTC. Probe `probe_tz.tjp` proves this: the reference scheduler rejects a task
  `start 2002-01-16` with "must be within the project time frame 2002-01-16-01:00-+0100".
- Only the starts of AcSo, AcSo.deliveries and deliveries.start change.

**AMBIGUOUS A6 (minor): `complete 95` on backend.** The brief does not cover it.
- *Chosen:* it is reporting-only, as in the reference scheduler, so backend still books its full 240 h.
- *Alternative:* reading it as 95 % already done would shrink backend to 12 h. That reading was
  not computed, since no documented semantics supports it.

| id | primary start | primary end | A1 alternative start | end | A2 alternative start | end |
|---|---|---|---|---|---|---|
| AcSo | 2002-01-16-00:00:00 | 2002-04-18-11:44:00 | = | 2002-04-18-12:48:00 | = | 2002-04-23-15:24:00 |
| AcSo.spec | 2002-01-16-09:00:00 | 2002-01-24-14:20:00 | = | 2002-01-24-15:00:00 | = | 2002-01-29-17:00:00 |
| AcSo.software | 2002-01-24-14:20:00 | 2002-03-28-13:20:00 | 2002-01-24-15:00:00 | 2002-03-28-14:00:00 | 2002-01-30-09:00:00 | 2002-04-03-17:00:00 |
| AcSo.software.database | 2002-01-24-14:20:00 | 2002-02-07-14:20:00 | 2002-01-24-15:00:00 | 2002-02-07-15:00:00 | 2002-01-30-09:00:00 | 2002-02-12-17:00:00 |
| AcSo.software.gui | 2002-02-28-14:20:00 | 2002-03-28-13:20:00 | 2002-02-28-15:00:00 | 2002-03-28-14:00:00 | 2002-03-06-09:00:00 | 2002-04-03-17:00:00 |
| AcSo.software.backend | 2002-02-07-14:20:00 | 2002-02-28-14:20:00 | 2002-02-07-15:00:00 | 2002-02-28-15:00:00 | 2002-02-13-09:00:00 | 2002-03-05-17:00:00 |
| AcSo.test | 2002-03-28-13:20:00 | 2002-04-18-11:44:00 | 2002-03-28-14:00:00 | 2002-04-18-12:48:00 | 2002-04-04-09:00:00 | 2002-04-23-15:24:00 |
| AcSo.test.alpha | 2002-03-28-13:20:00 | 2002-04-03-10:56:00 | 2002-03-28-14:00:00 | 2002-04-03-11:36:00 | 2002-04-04-09:00:00 | 2002-04-08-14:36:00 |
| AcSo.test.beta | 2002-04-03-10:56:00 | 2002-04-18-11:44:00 | 2002-04-03-11:36:00 | 2002-04-18-12:48:00 | 2002-04-08-14:36:00 | 2002-04-23-15:24:00 |
| AcSo.manual | 2002-01-16-09:00:00 | 2002-02-26-11:40:00 | = | 2002-02-26-12:00:00 | = | 2002-02-20-17:00:00 |
| AcSo.deliveries | 2002-01-16-00:00:00 | 2002-04-18-11:44:00 | = | 2002-04-18-12:48:00 | = | 2002-04-23-15:24:00 |
| AcSo.deliveries.start | 2002-01-16-00:00:00 | 2002-01-16-00:00:00 | = | = | = | = |
| AcSo.deliveries.prev | 2002-02-28-14:20:00 | 2002-02-28-14:20:00 | 2002-02-28-15:00:00 | 2002-02-28-15:00:00 | 2002-03-05-17:00:00 | 2002-03-05-17:00:00 |
| AcSo.deliveries.beta | 2002-04-03-10:56:00 | 2002-04-03-10:56:00 | 2002-04-03-11:36:00 | 2002-04-03-11:36:00 | 2002-04-08-14:36:00 | 2002-04-08-14:36:00 |
| AcSo.deliveries.done | 2002-04-18-11:44:00 | 2002-04-18-11:44:00 | 2002-04-18-12:48:00 | 2002-04-18-12:48:00 | 2002-04-23-15:24:00 | 2002-04-23-15:24:00 |

("=" means the same as the primary reading. A1 alternative = `mode=seqslot R=3600`. A2
alternative = `order=own`.)

## the reference scheduler cross-check

Run with a translated copy (not kept) (output saved as `tutorial_work/tj_tutorial_full.txt`).
the reference scheduler disagrees with the primary reading on all 15 rows, in at least one column each. Every disagreement has a cause
that was demonstrated by a run, not assumed:

1. **Default working hours are not a cause, and the brief's premise does not hold for this the reference scheduler.**
   `probe_hours.tjp` (Paris) and `probe_hours_utc.tjp` (UTC) put a 16 h task on one default
   resource. The hourly report shows the reference scheduler booking 09:00-17:00 Mon-Fri on both days,
   *including 12:00-13:00*, so its default here is the same 09:00-17:00 as ScriptPlan's. The
   tutorial also shows it: on 24 Jan the reference scheduler books spec in the 12:00 slot.
2. **"A5": the 01:00 start of AcSo, deliveries and deliveries.start.** the reference scheduler reads the
   project header date as UTC, because the date comes before `timezone` in the file. Proof: in
   `probe_tz.tjp`, the reference scheduler itself rejects `start 2002-01-16` with "Date 2002-01-16-00:00-+0100 must be
   within the project time frame 2002-01-16-01:00-+0100". ScriptPlan reads file dates in the
   project timezone, so its start is 00:00. **This is neither slot rounding nor default hours.**
   It is a third, the reference scheduler-specific cause.
3. **"slot rule": every other difference.** the reference scheduler books whole 1-hour slots. Inside a slot
   it books the resources one after another and stops as soon as the remainder is covered. A
   task ends at the end of its last slot. A limit admits a slot only if the whole slot fits under
   it, so test works 6 h a day, not 6 h 24 min.
   - `tutorial_sim.py mode=tjslot pstart=utc` runs exactly this rule on the same model and
     reproduces **all 15 the reference scheduler rows exactly, 0 mismatches**.
   - The comparison can fail, and does when a reading changes: an inclusive dev3 leave
     mismatches 1 row (manual 16:00), manual-first ordering 14 rows, the formula week 1 row, and
     a 00:00 start 3 rows. So the reference scheduler independently confirms the chosen readings of A2 and A3, and the
     model's calendars, leaves, both limits and the placement order.
   - The chain: in the 14:00 slot on 24 Jan, spec needs 1 person-hour, and dev1's slot alone
     covers it. So spec ends 15:00 instead of 14:20, and dev3 goes to manual from 14:00.
   - The 40 minutes carry through database, backend and gui unchanged: each is a whole number of
     two-person days. So prev and software move to 15:00 / 14:00.
   - manual's last hour is a single slot ending 12:00. alpha starts 14:00, runs under 6-hour test
     days and ends in a whole slot at 12:00. beta then ends 15:00.

| id | primary (ScriptPlan semantics) | the reference scheduler | the reference scheduler-rule simulation | cause |
|---|---|---|---|---|
| AcSo | 2002-01-16-00:00 .. 2002-04-18-11:44 | 2002-01-16-01:00 .. 2002-04-18-15:00 | identical to the reference scheduler | start: A5; end: slot rule |
| AcSo.spec | 2002-01-16-09:00 .. 2002-01-24-14:20 | 2002-01-16-09:00 .. 2002-01-24-15:00 | identical to the reference scheduler | end: slot rule |
| AcSo.software | 2002-01-24-14:20 .. 2002-03-28-13:20 | 2002-01-24-15:00 .. 2002-03-28-14:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.software.database | 2002-01-24-14:20 .. 2002-02-07-14:20 | 2002-01-24-15:00 .. 2002-02-07-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.software.gui | 2002-02-28-14:20 .. 2002-03-28-13:20 | 2002-02-28-15:00 .. 2002-03-28-14:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.software.backend | 2002-02-07-14:20 .. 2002-02-28-14:20 | 2002-02-07-15:00 .. 2002-02-28-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.test | 2002-03-28-13:20 .. 2002-04-18-11:44 | 2002-03-28-14:00 .. 2002-04-18-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.test.alpha | 2002-03-28-13:20 .. 2002-04-03-10:56 | 2002-03-28-14:00 .. 2002-04-03-12:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.test.beta | 2002-04-03-10:56 .. 2002-04-18-11:44 | 2002-04-03-12:00 .. 2002-04-18-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.manual | 2002-01-16-09:00 .. 2002-02-26-11:40 | 2002-01-16-09:00 .. 2002-02-26-12:00 | identical to the reference scheduler | end: slot rule |
| AcSo.deliveries | 2002-01-16-00:00 .. 2002-04-18-11:44 | 2002-01-16-01:00 .. 2002-04-18-15:00 | identical to the reference scheduler | start: A5; end: slot rule |
| AcSo.deliveries.start | 2002-01-16-00:00 .. 2002-01-16-00:00 | 2002-01-16-01:00 .. 2002-01-16-01:00 | identical to the reference scheduler | start: A5; end: A5 |
| AcSo.deliveries.prev | 2002-02-28-14:20 .. 2002-02-28-14:20 | 2002-02-28-15:00 .. 2002-02-28-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.deliveries.beta | 2002-04-03-10:56 .. 2002-04-03-10:56 | 2002-04-03-12:00 .. 2002-04-03-12:00 | identical to the reference scheduler | start: slot rule; end: slot rule |
| AcSo.deliveries.done | 2002-04-18-11:44 .. 2002-04-18-11:44 | 2002-04-18-15:00 .. 2002-04-18-15:00 | identical to the reference scheduler | start: slot rule; end: slot rule |

## Appendix: per-day bookings in the primary reading (from `daily_table.py`)

Times are local Paris wall clock, and h:mm are booked hours of that resource on that task.
The cumulative column reaching the effort is where each end above comes from.

### AcSo.spec  (effort 160 h)
| date | dev1 | dev2 | dev3 | day total | cumulative |
|---|---|---|---|---|---|
| 2002-01-16 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 24:00 |
| 2002-01-17 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 48:00 |
| 2002-01-18 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 72:00 |
| 2002-01-21 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 96:00 |
| 2002-01-22 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 120:00 |
| 2002-01-23 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 24:00 | 144:00 |
| 2002-01-24 Thu | 5:20 (09:00-14:20) | 5:20 (09:00-14:20) | 5:20 (09:00-14:20) | 16:00 | 160:00 |

### AcSo.software.database  (effort 160 h)
| date | dev1 | dev2 | day total | cumulative |
|---|---|---|---|---|
| 2002-01-24 Thu | 2:40 (14:20-17:00) | 2:40 (14:20-17:00) | 5:20 | 5:20 |
| 2002-01-25 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 21:20 |
| 2002-01-28 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 37:20 |
| 2002-01-29 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 53:20 |
| 2002-01-30 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 69:20 |
| 2002-01-31 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 85:20 |
| 2002-02-01 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 101:20 |
| 2002-02-04 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 117:20 |
| 2002-02-05 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 133:20 |
| 2002-02-06 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 149:20 |
| 2002-02-07 Thu | 5:20 (09:00-14:20) | 5:20 (09:00-14:20) | 10:40 | 160:00 |

### AcSo.software.gui  (effort 280 h)
| date | dev2 | dev3 | day total | cumulative |
|---|---|---|---|---|
| 2002-02-28 Thu | 2:40 (14:20-17:00) | 2:40 (14:20-17:00) | 5:20 | 5:20 |
| 2002-03-01 Fri | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 19:20 |
| 2002-03-04 Mon | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 33:20 |
| 2002-03-05 Tue | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 47:20 |
| 2002-03-06 Wed | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 61:20 |
| 2002-03-07 Thu | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 75:20 |
| 2002-03-08 Fri | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 89:20 |
| 2002-03-11 Mon | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 103:20 |
| 2002-03-12 Tue | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 117:20 |
| 2002-03-13 Wed | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 131:20 |
| 2002-03-14 Thu | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 145:20 |
| 2002-03-15 Fri | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 159:20 |
| 2002-03-18 Mon | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 173:20 |
| 2002-03-19 Tue | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 187:20 |
| 2002-03-20 Wed | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 201:20 |
| 2002-03-21 Thu | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 215:20 |
| 2002-03-22 Fri | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 229:20 |
| 2002-03-25 Mon | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 243:20 |
| 2002-03-26 Tue | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 257:20 |
| 2002-03-27 Wed | 6:00 (09:00-15:00) | 8:00 (09:00-17:00) | 14:00 | 271:20 |
| 2002-03-28 Thu | 4:20 (09:00-13:20) | 4:20 (09:00-13:20) | 8:40 | 280:00 |

### AcSo.software.backend  (effort 240 h)
| date | dev1 | dev2 | day total | cumulative |
|---|---|---|---|---|
| 2002-02-07 Thu | 2:40 (14:20-17:00) | 2:40 (14:20-17:00) | 5:20 | 5:20 |
| 2002-02-08 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 21:20 |
| 2002-02-11 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 37:20 |
| 2002-02-12 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 53:20 |
| 2002-02-13 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 69:20 |
| 2002-02-14 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 85:20 |
| 2002-02-15 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 101:20 |
| 2002-02-18 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 117:20 |
| 2002-02-19 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 133:20 |
| 2002-02-20 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 149:20 |
| 2002-02-21 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 165:20 |
| 2002-02-22 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 181:20 |
| 2002-02-25 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 197:20 |
| 2002-02-26 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 213:20 |
| 2002-02-27 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 229:20 |
| 2002-02-28 Thu | 5:20 (09:00-14:20) | 5:20 (09:00-14:20) | 10:40 | 240:00 |

### AcSo.test.alpha  (effort 40 h)
| date | test | dev2 | day total | cumulative |
|---|---|---|---|---|
| 2002-03-28 Thu | 3:40 (13:20-17:00) | 3:40 (13:20-17:00) | 7:20 | 7:20 |
| 2002-04-01 Mon | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 21:44 |
| 2002-04-02 Tue | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 36:08 |
| 2002-04-03 Wed | 1:56 (09:00-10:56) | 1:56 (09:00-10:56) | 3:52 | 40:00 |

### AcSo.test.beta  (effort 160 h)
| date | test | dev1 | day total | cumulative |
|---|---|---|---|---|
| 2002-04-03 Wed | 4:28 (10:56-15:24) | 6:04 (10:56-17:00) | 10:32 | 10:32 |
| 2002-04-04 Thu | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 24:56 |
| 2002-04-05 Fri | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 39:20 |
| 2002-04-08 Mon | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 53:44 |
| 2002-04-09 Tue | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 68:08 |
| 2002-04-10 Wed | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 82:32 |
| 2002-04-11 Thu | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 96:56 |
| 2002-04-12 Fri | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 111:20 |
| 2002-04-15 Mon | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 125:44 |
| 2002-04-16 Tue | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 140:08 |
| 2002-04-17 Wed | 6:24 (09:00-15:24) | 8:00 (09:00-17:00) | 14:24 | 154:32 |
| 2002-04-18 Thu | 2:44 (09:00-11:44) | 2:44 (09:00-11:44) | 5:28 | 160:00 |

### AcSo.manual  (effort 400 h)
| date | doc | dev3 | day total | cumulative |
|---|---|---|---|---|
| 2002-01-16 Wed | 8:00 (09:00-17:00) | 0:00  | 8:00 | 8:00 |
| 2002-01-17 Thu | 8:00 (09:00-17:00) | 0:00  | 8:00 | 16:00 |
| 2002-01-18 Fri | 8:00 (09:00-17:00) | 0:00  | 8:00 | 24:00 |
| 2002-01-21 Mon | 8:00 (09:00-17:00) | 0:00  | 8:00 | 32:00 |
| 2002-01-22 Tue | 8:00 (09:00-17:00) | 0:00  | 8:00 | 40:00 |
| 2002-01-23 Wed | 8:00 (09:00-17:00) | 0:00  | 8:00 | 48:00 |
| 2002-01-24 Thu | 8:00 (09:00-17:00) | 2:40 (14:20-17:00) | 10:40 | 58:40 |
| 2002-01-25 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 74:40 |
| 2002-01-28 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 90:40 |
| 2002-01-29 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 106:40 |
| 2002-01-30 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 122:40 |
| 2002-01-31 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 138:40 |
| 2002-02-01 Fri | 8:00 (09:00-17:00) | 0:00  | 8:00 | 146:40 |
| 2002-02-04 Mon | 8:00 (09:00-17:00) | 0:00  | 8:00 | 154:40 |
| 2002-02-05 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 170:40 |
| 2002-02-06 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 186:40 |
| 2002-02-07 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 202:40 |
| 2002-02-08 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 218:40 |
| 2002-02-11 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 234:40 |
| 2002-02-12 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 250:40 |
| 2002-02-13 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 266:40 |
| 2002-02-14 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 282:40 |
| 2002-02-15 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 298:40 |
| 2002-02-18 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 314:40 |
| 2002-02-19 Tue | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 330:40 |
| 2002-02-20 Wed | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 346:40 |
| 2002-02-21 Thu | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 362:40 |
| 2002-02-22 Fri | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 378:40 |
| 2002-02-25 Mon | 8:00 (09:00-17:00) | 8:00 (09:00-17:00) | 16:00 | 394:40 |
| 2002-02-26 Tue | 2:40 (09:00-11:40) | 2:40 (09:00-11:40) | 5:20 | 400:00 |



---

# tutorial: adjudication

The independent derivation lets every developer free in a task's last slot work it, so
`spec`, with 60 person-minutes left at 14:00 on 24 January and three developers free, ends
at 14:20. The engine let the first developer's full hour cover it and ended at 15:00, and
its answer moved with `timingresolution`: 15:00 at 60 minutes, 14:30 at 30 and 15, 14:20
at 5 and 1.

Verdict: the derivation is right. A plan's dates must not depend on the slot size, and at
1-minute slots the engine itself gave 14:20. Fixed in 0.10.2 (issuedb #27) with Farshid's
approval; the engine now gives these dates at every resolution, and the tutorial golden
snapshot was updated for the 14 rows this moves.
