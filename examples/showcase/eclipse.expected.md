# eclipse — hand derivation

Source: `src/eclipse.tjp`. Times are UTC (`Etc/UTC`).
Arithmetic check: `out/walk6.py` (stdlib only, no scriptplan).

## Inputs

- Project period: 2025-06-01 00:00 + 1m (30.4167 d) = up to 2025-07-01 ~10:00. 2025-06-01
  is a Sunday. No vacations.
- `r_sun`: `s_odd` = Mon, Wed, Fri 09:00-17:00 only.
- `r_moon`: `s_mid` = every day 12:00-14:00.
- `sys.sync`: effort 14h, `allocate r_sun { mandatory }, r_moon { mandatory }`,
  `start 2025-06-01-00:00`.

## sys.sync (ASAP, effort 14h, both mandatory)

- Earliest start: declared start Sun 1 Jun 00:00.
- Mandatory on both: progress only while both are free = intersection of the calendars =
  Mon/Wed/Fri 12:00-14:00 (120 min per such day). On Sun/Tue/Thu/Sat r_moon works but r_sun
  does not, so nothing is booked.
- Person-time: 2 resources x efficiency 1 = 2 effort-min per elapsed minute.
  840 effort-min / 2 = 420 elapsed min of joint time.
  - Sun 1 Jun: r_sun off, 0
  - Mon 2 Jun 12:00-14:00: 120 min -> 240 effort-min (600 left)
  - Wed 4 Jun 12:00-14:00: 120 -> 240 (360 left)
  - Fri 6 Jun 12:00-14:00: 120 -> 240 (120 left)
  - Mon 9 Jun 12:00-13:00: 60 -> 120 (0 left)
- **start 2025-06-02 12:00 (first joint work), end 2025-06-09 13:00.**
- File comment ("seven hours of both working together is fourteen hours of effort"):
  checked, 120+120+120+60 = 420 min = 7 h joint, x 2 = 14 h. Correct.

## sys (container)

- Only child is sync: 2025-06-02 12:00 -> 2025-06-09 13:00.

## AMBIGUOUS

1. **AMBIGUOUS: reported start.** Declared `start 2025-06-01-00:00` (Sunday, no joint time)
   vs first booked minute 2025-06-02 12:00. Chosen: first booked minute (the reference scheduler
   reports this too). Alternative: 2025-06-01 00:00 for both `sys.sync` and `sys`.
2. **AMBIGUOUS: unlisted weekdays in `workinghours mon, wed, fri ...`.** Chosen (brief:
   workinghours "replace the default"): r_sun has no Tue/Thu hours. Alternative (the reference scheduler behaviour): Tue/Thu keep the 09:00-17:00 default, the joint window becomes Mon-Fri
   12:00-14:00, and sync runs 2025-06-02 12:00 -> 2025-06-05 13:00
   (Mon 120 + Tue 120 + Wed 120 + Thu 60 = 420 min). The project's header comment
   ("discontinuous shift patterns", shift named "Odd") supports the chosen reading.

## the reference scheduler cross-check

the reference scheduler rejects `workinghours s_odd` (shift name). Variants in a translated copy (not kept):

- a translated copy (not kept) (hours inlined on each resource):
  `sys.sync;2025-06-02-12:00;2025-06-05-13:00`
- a translated copy (not kept) (same, plus `workinghours tue, thu, sat, sun off` on r_sun):
  `sys.sync;2025-06-02-12:00;2025-06-09-13:00` — **agrees with the derivation**.

The first variant differs because the reference scheduler's `workinghours` replaces only the listed weekdays;
an hourly booking dump (a translated copy (not kept), `rr.csv`) shows r_sun booked on Tue 3
Jun 12:00-14:00 and Thu 5 Jun 12:00-13:00. Explained by default working hours (AMBIGUOUS
point 2). Both the reference scheduler runs report the start as 06-02 12:00, not the declared 06-01 00:00, and
honour `mandatory` (nothing is booked on Sun 1 Jun although r_moon works then).
