# airport_ultra_math — hand derivation

(`airport_ultra_math_report.tjp` schedules identically. It differs only in comments and in having an active
`taskreport`. See `airport_ultra_math_report.md`.)

Project `AirportUltraMath`, 2025-08-01 00:00 UTC, +3m, so it runs to about 2025-10-31. timingresolution 15min.
dailyworkinghours 8 gives d = 8 h. The comment "we will override this per resource" is not acted on: there is
no per-resource `dailyworkinghours`.
2025-08-04 is a Monday.

Checked by my stdlib walker `out/walk_airport.py` (exact Fraction seconds; output in
`out/walk_airport.output.txt`). It agrees to the sub-second.

## Resources

| resource | hours (UTC) | efficiency | other |
|---|---|---|---|
| irregular_shift | (a resource, never allocated) | – | – |
| r_math | Mon/Wed/Fri 08:15–11:45 (210) + 13:15–16:30 (195) = 405 min; Tue/Thu 09:00–10:30 (90) + 14:45–16:00 (75) = 165 min | 0.77 | vacation Tue 2025-08-05 09:30–10:00 |
| r_limit | Mon–Fri 08:00–18:00 (600 min) | 1.25 | dailymax 3.5 h = 210 min of clock time per UTC day |

## Placement order

t_interrupt (priority 1000, declared start) comes first. Then t_finish (500, ALAP, declared end), then t_float
(100, declared start). t_limit (500) waits for t_float. t_finish and t_limit share r_limit, but on different
weeks (Aug 28–29 against Aug 8–13), so their order does not change either one.

## Tasks

### airport_math.t_interrupt — 2025-08-06-14:00:00 → 2025-08-06-14:58:26
- Declared start Wed 08-06 14:00, inside r_math's 13:15–16:30 window.
- Effort 45 min at 0.77 → 45 / 0.77 = **58.441558 min = 3506.4935 s** of r_math.
- 14:00 + 3506.4935 s = 14:58:26.4935 → reported **14:58:26**. Rounding to the nearest second and truncating
  give the same value.
- The file's comment says it "run[s] for 45 mins". That is the effort; the clock time is 58 min 26.5 s.

### airport_math.t_float — 2025-08-04-08:15:00 → 2025-08-08-14:57:05
- Declared start Mon 08-04 08:15, a working moment.
- Effort 17.5 h at 0.77 → 17.5 / 0.77 = **22.727273 h = 1363.636364 min** of r_math. This matches the file's
  "22.7272..." and "1 hour effort = 1.2987... hours".
- Walk:

| day | windows used | min | cumulative |
|---|---|---|---|
| Mon 08-04 | 08:15–11:45, 13:15–16:30 | 405 | 405 |
| Tue 08-05 | 09:00–09:30, (vacation 09:30–10:00), 10:00–10:30, 14:45–16:00 | 30 + 30 + 75 = 135 | 540 |
| Wed 08-06 | 08:15–11:45, 13:15–14:00, (t_interrupt 14:00–14:58:26.49), 14:58:26.49–16:30 | 210 + 45 + 91.558442 = 346.558442 | 886.558442 |
| Thu 08-07 | 09:00–10:30, 14:45–16:00 | 165 | 1051.558442 |
| Fri 08-08 | 08:15–11:45 | 210 | 1261.558442 |
| Fri 08-08 | 13:15 → | 1363.636364 − 1261.558442 = **102.077922** | 1363.636364 |

- 102.077922 min = 1 h 42 min 4.6753 s → 13:15 + that = **14:57:04.6753**, reported **14:57:05**
  (rounded to the nearest second).
- The file's comment numbers check out: Mon 6.75 h ✓; Tue 2.75 h gross, 2.25 h net of the 30-min leave ✓.
- AMBIGUOUS (rounding): chosen nearest → 14:57:05. Truncation → 14:57:04. The brief says "to the second" but
  gives no rounding mode. The same choice applies to t_limit's start and end.
- AMBIGUOUS (vacation scope): the brief says "leaves/vacation on a day block it entirely". This vacation is a
  timed 30-minute interval (09:30–10:00), not a date.
  - Chosen: it blocks only 09:30–10:00. That is what the file's own comment intends, and what the reference scheduler does.
  - Alternative: it blocks all of Tuesday, so Tue contributes 0 instead of 135 min. t_float then ends
    **2025-08-11-08:57:05** (Fri afternoon 195 min, then Mon 08:15 + 42.0779 min), and t_limit runs
    **2025-08-11-08:57:05 → 2025-08-14-09:30:00** (Mon 08:57:05–12:27:05 = 210, Tue 210, Wed 210, Thu 08:00–09:30 = 90).
    t_interrupt, t_finish and the container's start and end are unchanged.

### airport_math.t_limit — 2025-08-08-14:57:05 → 2025-08-13-09:57:05
- depends !t_float → earliest Fri 08-08 14:57:04.6753. This is mid-slot (14:45–15:00) and the start is honoured
  there exactly.
- Effort 15 h at 1.25 → 15 / 1.25 = **12 h = 720 min** of r_limit. dailymax caps clock time at 210 min/day.

| day | booked | min | cumulative |
|---|---|---|---|
| Fri 08-08 | 14:57:04.6753–18:00 (day ends before the cap) | 182.922078 | 182.922078 |
| Mon 08-11 | 08:00–11:30 (cap) | 210 | 392.922078 |
| Tue 08-12 | 08:00–11:30 (cap) | 210 | 602.922078 |
| Wed 08-13 | 08:00 → | 720 − 602.922078 = 117.077922 | 720 |

- 117.077922 min = 1 h 57 min 4.6753 s → **Wed 09:57:04.6753**, reported **09:57:05**.
- Checking the file's comment: "3.5h/day for 3 days, Day 4: remaining 1.5h" assumes t_limit starts at the top of a
  day. It does not: t_float hands over at Fri 14:57, so day 1 gets only 3.0487 h. The split is
  3.0487 + 3.5 + 3.5 + 1.9513 = 12 h. The total 12 h, and the cost 12 h × 200 = **2400**, are as the comment says.

### airport_math.t_finish — 2025-08-28-15:06:00 → 2025-08-29-17:00:00
- ALAP with declared end Fri 08-29 17:00, a working moment. No successors.
- Effort 1d = 8 h (project d) at 1.25 → 6.4 h = **384 min** of r_limit, booked backwards, max 210 per day.
- Fri 08-29: 17:00 back 210 min (cap) → 13:30. 174 min remain.
- Thu 08-28: from 18:00 back 174 min → **15:06**. That is mid-slot: 15:00–15:15 is used from 15:06 to its end.
  Thu booked 174 ≤ 210.
- The file's own expectation ("must end on Friday, Aug 29 at 17:00") holds.

### airport_math (container) — 2025-08-04-08:15:00 → 2025-08-29-17:00:00
Earliest child start (t_float 08-04 08:15) and latest child end (t_finish 08-29 17:00).

## Checks

r_math never works two tasks at once: t_float's Wednesday bookings stop at 14:00 and resume at 14:58:26.49,
exactly where t_interrupt ends. r_limit per day: Aug 8 182.92, Aug 11 210, Aug 12 210, Aug 13 117.08, Aug 28 174,
Aug 29 210 — never more than 210.

## the reference scheduler cross-check (`the reference-scheduler run`, file as given)

| id | the reference scheduler | mine | reason |
|---|---|---|---|
| airport_math | 08-04 08:15 → 08-29 17:00 | same | – |
| t_float | 08-04 08:15 → 08-08 **15:00** | → 14:57:05 | slot rounding: the reference scheduler needs 17.5 / (0.25 × 0.77) = 90.9 → 91 whole 15-min slots. Mon 27 + Tue 9 + Wed 23 (the reference scheduler's t_interrupt takes 4) + Thu 11 + Fri morning 14 = 84; 7 more from 13:15 → 15:00 |
| t_interrupt | 08-06 14:00 → **15:00** | → 14:58:26 | slot rounding: 45 / (15 × 0.77) = 3.9 → 4 slots |
| t_limit | 08-08 **15:00** → 08-13 **10:00** | 14:57:05 → 09:57:05 | slot rounding: 48 slots, 14 per day (Fri 12, Mon 14, Tue 14, Wed 8) |
| t_finish | 08-28 **15:00** → 08-29 17:00 | 15:06 → | slot rounding: 6.4 h → 26 slots (6.5 h). Fri 14 slots back to 13:30; Thu 12 slots back from 18:00 → 15:00 |

Every disagreement is the reference scheduler's whole-slot rounding of efficiency-fractional work. the reference scheduler's Tuesday count (9 slots)
confirms the 30-minute reading of the vacation. The whole-day reading would have pushed the reference scheduler's t_float into
Monday 08-11.
