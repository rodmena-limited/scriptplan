# airport_ultra_math_report — hand derivation

`diff airport_ultra_math.tjp airport_ultra_math_report.tjp` shows only three changes:
1. a comment on line 50 (drops "(30 mins)"),
2. a comment on line 144,
3. an active `taskreport "math_dump"` (csv; columns id, name, start, end, duration, effort, cost;
   `hidetask ~isleaf()`; `loadunit hours`) instead of the commented-out one.

None of these touches the project header, resources, calendars, vacation, limits or tasks, so the schedule is
identical. The full derivation is in `airport_ultra_math.md`, and its ambiguities (rounding mode; timed vacation
blocking 30 minutes or the whole Tuesday) apply here unchanged.

| id | start | end | key arithmetic |
|---|---|---|---|
| airport_math | 2025-08-04-08:15:00 | 2025-08-29-17:00:00 | earliest child start / latest child end |
| airport_math.t_float | 2025-08-04-08:15:00 | 2025-08-08-14:57:05 | 17.5 h / 0.77 = 1363.636 min of r_math. Mon 405 + Tue 135 (leave 09:30–10:00) + Wed 346.558 (around t_interrupt) + Thu 165 + Fri 210 + 102.078 from 13:15 → 14:57:04.675 |
| airport_math.t_interrupt | 2025-08-06-14:00:00 | 2025-08-06-14:58:26 | 45 min / 0.77 = 58.4416 min, priority 1000, placed first |
| airport_math.t_limit | 2025-08-08-14:57:05 | 2025-08-13-09:57:05 | 15 h / 1.25 = 720 min, dailymax 210: Fri 182.922 + Mon 210 + Tue 210 + Wed 117.078 |
| airport_math.t_finish | 2025-08-28-15:06:00 | 2025-08-29-17:00:00 | ALAP, 8 h / 1.25 = 384 min back from Fri 17:00: Fri 210 (to 13:30), Thu 174 back from 18:00 |

The report's `hidetask ~isleaf()` would hide the container `airport_math` from the engine's own CSV. The row is
in `expected.csv` because the brief asks for every task.

The report's `cost` column, as a side check: t_limit 12 h × 200 = 2400; t_finish 6.4 h × 200 = 1280;
t_float 22.7273 h × 150 = 3409.09; t_interrupt 0.97403 h × 150 = 146.10. The README says accounts and chargesets
are not yet modelled, but these figures come from the resource rate.

the reference scheduler gives exactly the same output for this file as for `airport_ultra_math.tjp`:
t_float → 08-08 15:00, t_interrupt → 15:00, t_limit 08-08 15:00 → 08-13 10:00, t_finish 08-28 15:00 → 08-29 17:00.
All differences are whole 15-minute-slot rounding, as itemised in `airport_ultra_math.md`.
