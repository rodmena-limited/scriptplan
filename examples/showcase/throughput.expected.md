# throughput.tjp — derivation

Project `Data_Tsunami`, timezone Etc/UTC (= UTC), period 2025-09-01 00:00 (Monday) +1m.
Calendar `m` = 30.4167 d = 2,628,002.88 s, so the project ends 2025-10-01 ~10:00:03 UTC.
(Read as one calendar month instead, it would end 2025-10-01 00:00. The task fits either way.)
All times are whole hours, so slots are 60 min.

## Calendar of `server_cluster` (shift `variable_throughput`, UTC)

| day | hours | minutes |
|-----|-------|---------|
| Mon | 09:00-11:00 | 120 |
| Tue | 09:00-13:00 | 240 |
| Wed | 09:00-17:00 | 480 |
| Thu | 06:00-22:00 | 960 |
| Fri | 09:00-17:00 | 480 |
| Sat | 09:00-13:00 | 240 |
| Sun | 09:00-11:00 | 120 |
| week | | 2640 = 44 h |

The file's comment "2h, 4h, 8h, 16h, 8h, 4h, 2h = 44h/week" checks out.

## processing — 2025-09-01-09:00 -> 2025-09-17-15:00

- Declared `start 2025-09-01-09:00` (Mon), which is the first working minute (Mon 09:00-11:00).
- effort 100h = 6000 min at efficiency 1.0 -> 6000 min of cluster time.
- Week of 1-7 Sep: 120+240+480+960+480+240+120 = 2640 min (running total 2640).
- Week of 8-14 Sep: 2640 min (total 5280).
- Remaining 6000 - 5280 = 720 min:
  - Mon 15 Sep 09:00-11:00: 120 (total 5400, 600 left)
  - Tue 16 Sep 09:00-13:00: 240 (total 5640, 360 left)
  - Wed 17 Sep 09:00 + 360 min = **15:00** (total 6000).
- End Wed 2025-09-17 15:00, well inside the project period.

No AMBIGUOUS points.

## the reference scheduler cross-check

- The original does not parse in the reference scheduler 3.8.4 (`workinghours variable_throughput`: the reference scheduler expects a
  weekday).
- Translation a translated copy (not kept) (the seven `workinghours` lines on the
  resource) gives processing 2025-09-01-09:00 -> 2025-09-17-15:00. **Agrees**.
