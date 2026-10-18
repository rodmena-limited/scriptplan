# workflow_engine.tjp — derivation

Project `Cloud_Migration_Workflow`, timezone Etc/UTC (= UTC), period 2025-11-03 00:00
(Monday) +2w = up to 2025-11-17 00:00. All on whole hours, so slots are 60 min.

## Calendars

- `intern`: shift `standard`, Mon-Fri 09:00-17:00 (480 min a day), `efficiency 0.5`.
- `admin`: shift `ops_week`, Tue-Sat 09:00-17:00 (480 min a day; Sun and Mon off),
  `efficiency 1.0`.
- The container `devops` sets no attributes, so there is nothing to inherit.

## Tasks

### migration.prep — 2025-11-03-09:00 -> 2025-11-06-17:00
- Declared `start 2025-11-03-09:00` (Mon), a working minute.
- effort 16h = 960 min. At efficiency 0.5 each intern minute does 0.5 min of effort, so it
  needs 960 / 0.5 = 1920 intern minutes.
- Mon 3 (480, total 480), Tue 4 (480, 960), Wed 5 (480, 1440), Thu 6 (480, 1920) -> ends
  **Thu 2025-11-06 17:00**. This agrees with the file's comment ("Mon(8) + Tue(8) + Wed(8) +
  Thu(8)", "ends Thu 17:00").

### migration.deploy — 2025-11-07-09:00 -> 2025-11-08-17:00
- `depends !prep`: earliest = Thu 17:00. The admin's next working minute is Fri 2025-11-07
  09:00.
- effort 16h = 960 min at efficiency 1.0 -> 960 admin minutes: Fri 7 (480), Sat 8 (480;
  Saturday is in `ops_week`) -> ends **Sat 2025-11-08 17:00**.

### migration (container) — 2025-11-03-09:00 -> 2025-11-08-17:00
- earliest child start (prep), latest child end (deploy).
- The file's report has `leaftasksonly true`, so the engine's own CSV will not show this
  row. I include it because the brief asks for every task.

No AMBIGUOUS points.

## the reference scheduler cross-check

- The original does not parse in the reference scheduler 3.8.4 (`shift standard {` has no name string; resources
  use `workinghours <shift>`).
- Translation a translated copy (not kept) (hours spelled out; the admin also gets
  `workinghours sun, mon off` so the reference scheduler's default Monday is removed) gives migration 11-03 09:00
  -> 11-08 17:00, prep 11-03 09:00 -> 11-06 17:00, deploy 11-07 09:00 -> 11-08 17:00.
  **Agrees** exactly.
