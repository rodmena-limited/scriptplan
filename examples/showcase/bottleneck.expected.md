# bottleneck — hand derivation

Source: `src/bottleneck.tjp`. Times are UTC.
Arithmetic check: `out/walk6.py` (stdlib only, no scriptplan).

## Inputs

- Project period: 2025-06-02 00:00 + 3w = 2025-06-02 -> 2025-06-23 00:00. 2025-06-02 is a
  Monday.
- Global `vacation "Company Founder Day" 2025-06-04` (Wednesday): whole day blocked for all.
- `team.dev`: Mon-Fri 09:00-17:00 (480 min/day). No limits.
- `team.qa`: Mon-Fri 09:00-17:00, `limits { dailymax 4h }` = 240 booked min per calendar
  day (UTC), fresh each day.
- 1 h slots; every booking below starts and ends on the hour.

## release.coding (ASAP, effort 16h, dev, start 2025-06-02-09:00)

- Earliest start: declared start Mon 2 Jun 09:00 (inside working time).
- 960 min of dev:
  - Mon 2 Jun 09:00-17:00: 480 (480 left)
  - Tue 3 Jun 09:00-17:00: 480 (0 left)
- **start 2025-06-02 09:00, end 2025-06-03 17:00.**

## release.review (ASAP, effort 12h, qa, depends !coding)

- Earliest start: coding end, Tue 3 Jun 17:00 (end of Tuesday's hours).
- 720 min of qa, at most 240 a day:
  - Wed 4 Jun: holiday, 0
  - Thu 5 Jun 09:00-13:00: 240 (cap reached; 480 left)
  - Fri 6 Jun 09:00-13:00: 240 (240 left)
  - Sat/Sun: no hours
  - Mon 9 Jun 09:00-13:00: 240 (0 left)
- **start 2025-06-05 09:00, end 2025-06-09 13:00.** qa's Monday cap is now used up.

## release.deploy (ASAP, effort 8h, dev {mandatory}, qa {mandatory}, depends !review)

- Earliest start: review end, Mon 9 Jun 13:00.
- Both allocations mandatory: progress only in minutes where dev AND qa are both free.
  Mon 9 Jun 13:00-17:00: dev free, but qa has booked 240 min today (dailymax), so no
  progress on Monday.
- Tue 10 Jun 09:00: both free. Person-time: 2 resources x 1 min per minute = 2 effort-min
  per minute. 480 effort-min / 2 = 240 elapsed min -> 09:00-13:00. qa books exactly 240 min
  on Tuesday, which is precisely its cap, so the cap does not cut the run.
- **start 2025-06-10 09:00, end 2025-06-10 13:00.** dev and qa both busy Tue 09-13.
- File comment ("four hours of the pair ... is eight hours of effort"): checked, 4 h x 2
  people = 8 h. Correct.

## release (container)

- min child start = 2025-06-02 09:00; max child end = 2025-06-10 13:00.

## AMBIGUOUS

None.

## the reference scheduler cross-check

`the reference-scheduler run src/bottleneck.tjp` (accepted as-is):

```
release;2025-06-02-09:00;2025-06-10-13:00
release.coding;2025-06-02-09:00;2025-06-03-17:00
release.review;2025-06-05-09:00;2025-06-09-13:00
release.deploy;2025-06-10-09:00;2025-06-10-13:00
```

Agrees on every row. No disagreement.
