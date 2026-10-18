# atomic — hand derivation

Source: `src/atomic.tjp`. Times are UTC (`Etc/UTC`).
Arithmetic check: `out/walk6.py` (stdlib only, no scriptplan).

## Inputs

- Project period: 2025-11-01 00:00 + 1w = 2025-11-01 00:00 -> 2025-11-08 00:00.
  2025-11-01 is a Saturday.
- `kiln`: `workinghours broken_day` = Mon-Fri 08:00-12:00 (240 min) and 13:00-18:00
  (300 min). Efficiency 1. No leaves.
- `production`: effort 4.5h, `flags contiguous`, allocate `kiln`, no declared start, no
  dependencies.

## production (ASAP, effort 4.5h, contiguous)

- Earliest start: project start, Sat 1 Nov 00:00. Sat and Sun have no kiln hours.
- Needs 4.5 h x 60 = 270 min of kiln time (efficiency 1), in one unbroken stretch.
- First working moment: Mon 3 Nov 08:00. The morning block runs 08:00-12:00 = 240 min,
  less than 270, so no start in the morning block fits (any start t in 08:00-12:00 has
  only 12:00 - t <= 240 min before the lunch break).
- Afternoon block Mon 3 Nov 13:00-18:00 = 300 min >= 270. Start 13:00, end 13:00 + 270 min
  = 17:30.
- **start 2025-11-03 13:00, end 2025-11-03 17:30.** Kiln busy Mon 13:00-17:30; idle Mon
  morning.
- 17:30 is mid-slot on the 1 h grid; the brief places work to the minute, so the end is
  reported as 17:30, not rounded.

## AMBIGUOUS

None that the brief leaves open. For reference only: if `contiguous` were ignored the task
would run Mon 08:00-12:00 (240 min) + 13:00-13:30 (30 min), i.e. 08:00 -> 13:30.

## the reference scheduler cross-check

the reference scheduler rejects the file as written (`workinghours broken_day`: the reference scheduler does not take a shift name
there; and an undeclared flag). Adapted copy a translated copy (not kept): hours inlined
on the resource and `flags contiguous` declared. Result:

```
production;2025-11-03-08:00;2025-11-03-14:00
```

Disagreement, expected:
1. the reference scheduler gives `flags` no scheduling meaning (a flag is just a tag), so it splits the task
   over the lunch break and starts at 08:00.
2. the reference scheduler rounds to whole 1 h slots: 270 min becomes 5 slots (08-12, 13-14), so it ends 14:00
   rather than 13:30.
Neither is a defect in the derivation.
