# synchrony.tjp: derivation

## Setting

- Project 2025-10-09 00:00 UTC, a Thursday. `+1w` means it ends 2025-10-16 00:00. All tasks are ASAP.
- factory: Mon-Fri 08:00-18:00, plus `booking "Outage" 2025-10-09-10:00 +1h`. That booking makes the factory **unavailable Thu 10-09 10:00-11:00** (S1).
- train: Mon-Fri 12:00-13:00 and 16:00-17:00.
- site: Mon-Fri 08:00-18:00.
- All edges are on the hour, so the slots are 1 h. Efficiency is 1.
- `gapduration 0min` means no gap. `maxgapduration 0min` is a check made after scheduling: the actual gap must be 0, or the engine reports an error.

## Tasks

**supply_chain.make** (3h = 180 min, factory)
- Earliest start = project start, 10-09 00:00. The factory's first working moment is 08:00.
- 08:00-10:00 gives 120 min, leaving 60. The outage blocks 10:00-11:00. 11:00-12:00 gives 60 min, leaving 0.
- start **2025-10-09 08:00**, end **2025-10-09 12:00**.

**supply_chain.move** (1h = 60 min, train; depends make, gap 0)
- Earliest start = 12:00 + 0. The train's 12:00-13:00 run is free, and gives 60 min, leaving 0.
- start **2025-10-09 12:00**, end **2025-10-09 13:00**.
- Gap make to move = 0 min, so the maxgapduration of 0 is met.

**supply_chain.install** (3h = 180 min, site; depends move, gap 0)
- Earliest start = 13:00 + 0. The site is free. 13:00-16:00 gives 180 min, leaving 0.
- start **2025-10-09 13:00**, end **2025-10-09 16:00**.
- Gap = 0 min, so the maxgapduration of 0 is met.

**supply_chain** (container)
- **2025-10-09 08:00 to 16:00**.

## AMBIGUOUS

**S1. Resource-level `booking "Outage" 2025-10-09-10:00 +1h`.** The brief does not cover it.
- Chosen: the factory is unavailable 10:00-11:00 on 10-09, as the file's comment says ("The factory is down from 10:00 to 11:00").
- Alternative (a), the booking blocks nothing:
  - make = 2025-10-09 08:00-11:00.
  - move is still 12:00-13:00, the train's first run. The gap is 60 min, more than maxgapduration 0, so the engine must report a maxgapduration error naming make and move.
  - install = 13:00-16:00.
- Alternative (b): a parse error, because the reference scheduler's resource `booking` takes a task id and "Outage" is not a task.

## the reference scheduler cross-check

**Original file.** Rejected:
- `shift factory_shift {` has no name string.
- the reference scheduler refuses `gapduration 0min` ("The interval duration may not be 0").
- the reference scheduler has no `maxgapduration`.

**a translated copy (not kept).** Shift hours inlined, the outage written as `vacation 2025-10-09-10:00 - 2025-10-09-11:00`, and the zero gaps and maxgap dropped (0 is the reference scheduler's default gap).
- the reference scheduler: make 08:00-12:00, move 12:00-13:00, install 13:00-16:00, container 08:00-16:00. **Identical.**

**a translated copy (not kept).** The outage as a 1h duration task allocated to the factory.
- the reference scheduler never gave that task the factory, so make ran 08:00-11:00. That is alternative (a).
- The difference is in how the outage is modelled, not a scheduling disagreement.
