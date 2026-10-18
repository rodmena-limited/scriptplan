# failover — hand derivation

Source: `src/failover.tjp`. Times are UTC (`Etc/UTC`).
Arithmetic check: `out/walk6.py` (stdlib only, no scriptplan).

## Inputs

- Project period: 2025-08-01 00:00 + 2w = 2025-08-01 -> 2025-08-15 00:00. 2025-08-01 is a
  Friday.
- `primary`: Mon-Fri 09:00-17:00, efficiency 1.0, `vacation 2025-08-01 - 2025-08-05`.
- `backup`: Mon-Fri 09:00-17:00, efficiency 0.5.
- `compute`: effort 8h, `allocate primary { alternative backup }`, no start, no
  dependencies, not `persistent`.

## compute (ASAP, effort 8h, primary with alternative backup)

- Earliest start: project start Fri 1 Aug 00:00; first working minute Fri 09:00.
- Fri 1 Aug: primary on vacation, so the alternative is used. backup at efficiency 0.5:
  480 min of backup = 240 effort-min (240 left).
- Sat 2 / Sun 3 Aug: no hours.
- Mon 4 Aug: primary still on vacation (in either reading of the vacation's end, below), so
  backup again: 09:00-17:00 = 480 min = 240 effort-min (0 left).
- **start 2025-08-01 09:00, end 2025-08-04 17:00.** Resource used: backup only (the report's
  `resources` column should show Cluster B / backup).
- File comment ("use slower backup to finish earlier"): checked. Waiting for primary would
  give Tue 5 Aug 09:00-17:00 (vacation end exclusive) or Wed 6 Aug (inclusive); the backup
  finishes Mon 4 Aug 17:00, earlier in both cases.

## AMBIGUOUS

None that changes a date. Two points the brief does not settle, both checked to give the
same answer:
- Whether `vacation 2025-08-01 - 2025-08-05` includes 5 Aug (the reference scheduler: an end date with
  no time is midnight, so it covers 1-4 Aug only). The task is finished on 4 Aug, which is a
  vacation day in both readings.
- Whether `alternative` is chosen per slot or once for the whole task (by earliest finish).
  primary is unavailable for every minute the task needs, so both give backup for all of it.

## the reference scheduler cross-check

the reference scheduler rejects `workinghours standard` (shift name). Adapted a translated copy (not kept)
(hours inlined):

```
compute;2025-08-01-09:00;2025-08-04-17:00
```

Agrees. No disagreement.
