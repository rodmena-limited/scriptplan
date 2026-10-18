# alap_backward — hand derivation

Source: `src/alap_backward.tjp`. Times are UTC (project `timezone "UTC"`).
Minute walker used as an arithmetic check: `out/walk6.py` (stdlib only, no scriptplan).

## Inputs

- Project period: 2025-12-01 00:00 + 3w = 21 d = 2025-12-01 00:00 -> 2025-12-22 00:00.
  2025-12-01 is a Monday.
- Global `vacation "Holiday" 2025-12-10` (Wednesday): blocks the whole of 10 Dec for every
  resource.
- `team.worker`: `workinghours mon - fri 09:00 - 17:00`, i.e. 480 min a day Mon-Fri.
  Efficiency 1, no limits. (`shift standard` is declared but not used.)
- Slot grid: every time in the file is on the hour, so 1 h slots; nothing here ends mid-slot.

## production.step2 (ALAP, effort 16h, declared end)

- Latest end: the declared `end 2025-12-12-17:00` (Friday). It has no successors; the project
  end (22 Dec) is later, so the declared end decides.
- Needs 16 h x 60 = 960 min of `worker` at efficiency 1.
- Walking back from Fri 12 Dec 17:00:
  - Fri 12 Dec 09:00-17:00: 480 min (480 done, 480 left)
  - Thu 11 Dec 09:00-17:00: 480 min (960 done)
- **start 2025-12-11 09:00, end 2025-12-12 17:00.** `worker` busy Thu 11 and Fri 12 all day.

## production.step1 (ALAP, effort 16h, `precedes !step2`)

- `!step2` resolves to `production.step2`; `precedes` makes step2 a successor of step1.
- step1 has no end of its own; its successor is scheduled first (it has a declared end), so
  step1's latest end = step2's start = Thu 11 Dec 09:00.
- 09:00 is the start of Thursday's working time, so nothing on Thursday is before it.
- Walking back for 960 min of `worker`:
  - Wed 10 Dec: holiday, 0 min
  - Tue 9 Dec 09:00-17:00: 480 min (480 left)
  - Mon 8 Dec 09:00-17:00: 480 min (0 left)
- **start 2025-12-08 09:00, end 2025-12-09 17:00.** `worker` busy Mon 8 and Tue 9 all day;
  no overlap with step2.

## production (container)

- Earliest child start = step1 start = 2025-12-08 09:00; latest child end = step2 end =
  2025-12-12 17:00. No dates are stated on the container.

## AMBIGUOUS

None. (Considered: whether the project-level `vacation` applies to a resource with its own
`workinghours`. The brief says a vacation day is blocked entirely, and nothing scopes the
global vacation, so it applies. If it did not, step1 would be Tue 9 Dec 09:00 -> Wed 10 Dec
17:00.)

## the reference scheduler cross-check

`the reference-scheduler run src/alap_backward.tjp` (file accepted as-is):

```
production;2025-12-08-09:00;2025-12-12-17:00
production.step1;2025-12-08-09:00;2025-12-09-17:00
production.step2;2025-12-11-09:00;2025-12-12-17:00
```

Agrees on every row. No disagreement.
