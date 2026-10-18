# airport_stress_test — hand derivation

Project `acso`, 2025-06-01 00:00 UTC (a Sunday), +2m, so it runs to about 2025-07-31. dailyworkinghours 8 and
yearlyworkingdays 260 give d = 8 h. Nobody declares `workinghours`, so every resource works the ScriptPlan
default, **Mon–Fri 09:00–17:00 UTC** (480 min/day).

Checked by my stdlib walker `out/walk_airport.py` (output in `out/walk_airport.output.txt`), which agrees.

## Resources (with inherited attributes)

| resource | efficiency | limits / leave | effort per minute of its time |
|---|---|---|---|
| d1 (in dev) | 0.8, inherited from dev | leave 2025-06-05 (–06-06) | 0.8 min |
| d2 (in dev) | 0.8, inherited from dev | dailymax 8h | 0.8 min |
| e1 (in elec) | 1.2, its own | – | 1.2 min |
| e2 (in elec) | 0.5, its own | – | 0.5 min |

## Placement order

Priorities: t_crit 1000; t_software, t_install, t_migration, t_audit, deliver 500; t_low 100.
- t_software has a declared start and goes first. t_crit, t_install and t_low all wait for it.
- t_audit is ALAP with a declared end, so it is ready at once. It is alone on e2, so its order does not matter.
- On e1 the order is **t_crit (1000), then t_install (500), then t_low (100)**.
  A time-stepped reading gives the same result: t_crit already holds e1 when t_install becomes ready on Thursday,
  and when e1 frees at 11:40, t_install beats t_low on priority.

## Tasks

### airport.t_software — 2025-06-02-09:00:00 → 2025-06-04-13:00:00
- Declared `start 2025-06-02` (Mon 00:00). d1's first working moment is Mon 09:00.
- Effort 2d = 16 h; at 0.8 that is 16 / 0.8 = 20 h = 1200 min of d1.
- Mon 2 (480), Tue 3 (960), Wed 4 09:00–13:00 (240 → 1200) → ends **Wed 06-04 13:00**.
- The leave (Thu 06-05, and possibly Fri 06-06) comes after this, so whether its end is inclusive makes no difference.
- AMBIGUOUS (minor): the reported start. Chosen: 09:00, the first booked moment ("then takes the earliest free
  working time"). Alternative: the declared 2025-06-02-00:00. the reference scheduler reports 09:00. The container `airport` start
  follows this row.

### airport.t_crit — 2025-06-04-13:00:00 → 2025-06-05-11:40:00
- depends !t_software → earliest Wed 13:00. Priority 1000, so it is first on e1.
- Effort 1d = 8 h; at 1.2 that is 8 / 1.2 = 6.6667 h = **400 min** of e1.
- Wed 13:00–17:00 = 240 min; 160 min remain → Thu 09:00 + 2 h 40 = **Thu 06-05 11:40**.

### airport.t_install — 2025-06-05-11:40:00 → 2025-06-06-10:20:00
- depends !t_software { gapduration 4h } → Wed 13:00 + 4 h (calendar) = Wed 17:00. Next working moment: Thu 09:00.
- e1 is busy with t_crit until Thu 11:40, so it starts at **Thu 11:40**.
- 8 h / 1.2 = 400 min: Thu 11:40–17:00 = 320; 80 remain → Fri 09:00 + 80 = **Fri 06-06 10:20**.
- (The CHANGELOG's 0.10.1 note also gives 11:40. I derived it independently; it matches.)

### airport.t_low — 2025-06-06-10:20:00 → 2025-06-06-13:40:00
- depends !t_software → earliest Wed 13:00, but e1 is held without a gap by t_crit (Wed 13:00–Thu 11:40) and
  then t_install (Thu 11:40–Fri 10:20). The first free e1 moment is **Fri 10:20**. That is mid-slot, and the slot is
  shared with t_install's last 20 minutes.
- Effort 4h / 1.2 = 3.3333 h = **200 min** → Fri 10:20 + 3 h 20 = **Fri 06-06 13:40**. The default day has no lunch break.

### airport.t_migration — 2025-06-05-11:40:00 → 2025-06-06-11:10:00
- depends !t_crit → earliest Thu 11:40. d2 is free.
- Effort 6h / 0.8 = 7.5 h = **450 min** of d2.
- Thu 11:40–17:00 = 320 min (within dailymax 480); 130 remain → Fri 09:00 + 2 h 10 = **Fri 06-06 11:10**
  (Fri booked 130 ≤ 480). dailymax 8h never binds, because the default day is 8 h.

### airport.t_audit — 2025-06-19-09:00:00 → 2025-06-24-17:00:00
- ALAP, declared `end 2025-06-25` (Wed 00:00). Its only successor, `deliver`, is ASAP and depends on it, so it
  is not scheduled first and does not constrain the end. The end is the declared end.
- The latest working time before Wed 00:00 is Tue 06-24 17:00.
- Effort 2d = 16 h; at 0.5 that is 16 / 0.5 = 32 h = 1920 min of e2, booked backwards: Tue 24 (480), Mon 23 (960),
  Fri 20 (1440), Thu 19 (1920) → starts **Thu 06-19 09:00**. Jun 21 and 22 are the weekend.
- AMBIGUOUS (minor): the reported end. Chosen: 2025-06-24-17:00, the last booked moment (the mirror of
  "takes the latest free working time before that"). Alternative: the declared 2025-06-25-00:00. the reference scheduler reports 17:00.
  `deliver` and the container `airport` end follow this row.

### airport.deliver (milestone) — 2025-06-24-17:00:00 → 2025-06-24-17:00:00
- depends !t_migration (Fri 06-06 11:10), !t_audit (Tue 06-24 17:00), !t_low (Fri 06-06 13:40).
- A forward milestone sits at the moment it may begin, the latest predecessor end = **Tue 06-24 17:00**. It does
  not move forward over non-working time.
- Under the alternative t_audit end, it is 2025-06-25-00:00.

### airport (container) — 2025-06-02-09:00:00 → 2025-06-24-17:00:00
Earliest child start (t_software) and latest child end (t_audit / deliver).

## Checks

Effort booked: t_software 1200 min × 0.8 = 960 min = 16 h ✓; t_crit 400 × 1.2 = 480 = 8 h ✓;
t_install 400 × 1.2 = 8 h ✓; t_low 200 × 1.2 = 4 h ✓; t_migration 450 × 0.8 = 6 h ✓; t_audit 1920 × 0.5 = 16 h ✓.
e1 has no overlap: 13:00 Wed–11:40 Thu, 11:40 Thu–10:20 Fri, 10:20–13:40 Fri.

## the reference scheduler cross-check (`the reference-scheduler run`, file as given)

| id | the reference scheduler start | the reference scheduler end | mine | reason |
|---|---|---|---|---|
| airport | 06-02 09:00 | 06-24 17:00 | same | – |
| t_software | 06-02 09:00 | 06-04 13:00 | same | 16 h / 0.8 = 20 whole 1-h slots exactly |
| t_crit | 06-04 13:00 | 06-05 **12:00** | 11:40 | slot rounding: 8 / 1.2 = 6.67 → 7 whole slots |
| t_install | 06-05 **12:00** | 06-06 **11:00** | 11:40 / 10:20 | slot rounding: starts after the reference scheduler's t_crit; 7 slots (Thu 12–17, Fri 9–11) |
| t_migration | 06-05 **12:00** | 06-06 **12:00** | 11:40 / 11:10 | slot rounding: 6 / 0.8 = 7.5 → 8 slots |
| t_low | 06-06 **11:00** | 06-06 **15:00** | 10:20 / 13:40 | slot rounding: 4 / 1.2 = 3.33 → 4 slots after the reference scheduler's t_install |
| t_audit | 06-19 09:00 | 06-24 17:00 | same | 32 whole slots |
| deliver | 06-24 17:00 | 06-24 17:00 | same | – |

Every disagreement comes from the reference scheduler booking whole 1-hour slots where an efficiency makes the work fractional.
the reference scheduler also confirms both minor ambiguities in favour of the chosen reading: start at first booking (09:00) and
ALAP end at last booking (17:00).

Note on the reference scheduler's default hours: in this the reference scheduler 3.8.4 install the default day behaved as **09:00–17:00 with no lunch
break**, not 09:00–12:00 + 13:00–18:00 as the brief says. Probes in a translated copy (not kept):
two 4 h tasks ran 09–13 and 13–17, a 9 h task ended Tue 10:00, and `length 1h` from 12:00 ended 13:00.
That is why the reference scheduler agrees with the ScriptPlan default here.
