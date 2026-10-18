# union_contract.tjp — derivation

Project `Union_Contract`, timezone Etc/UTC (= UTC), period 2025-10-01 00:00 (Wednesday) +2w
= up to 2025-10-15 00:00. All on whole hours, so slots are 60 min.

## Calendar and limit

- `worker`: Mon-Fri 09:00-17:00 UTC (480 min a day), `limits { weeklymax 20h }` = 1200 min
  per ISO week (Monday to Sunday) in the worker's calendar (UTC).
- ISO week 40 = Mon 29 Sep - Sun 5 Oct. ISO week 41 = Mon 6 Oct - Sun 12 Oct.

## Tasks (a single resource in a finish-to-start chain)

### chain.step1 — 2025-10-01-09:00 -> 2025-10-01-17:00
- Declared `start 2025-10-01-09:00` (Wed), a working minute.
- 8h = 480 min: Wed 09:00-17:00. Week 40 used: 480 / 1200.

### chain.step2 — 2025-10-02-09:00 -> 2025-10-02-17:00
- After step1 (Wed 17:00). The next working minute is Thu 09:00.
- 480 min: Thu 09:00-17:00. Week 40 used: 960 / 1200.

### chain.step3 — 2025-10-03-09:00 -> 2025-10-06-13:00
- After step2 (Thu 17:00). The next working minute is Fri 09:00.
- Week 40 has 1200 - 960 = 240 min left: Fri 09:00-13:00 (240 min). The week is now at
  1200 / 1200, so Fri 13:00-17:00 is blocked by the cap.
- Sat and Sun are not working days. Week 41 starts with nothing used: Mon 6 Oct 09:00 + the
  remaining 480 - 240 = 240 min = **13:00**. Week 41 used: 240.
- The cap is tested both ways: it blocks at 1200 min on Friday, and work resumes Monday.

### chain.step4 — 2025-10-06-13:00 -> 2025-10-06-17:00
- After step3 (Mon 13:00). 4h = 240 min: Mon 13:00-17:00. Week 41 used: 480 / 1200.

### chain (container) — 2025-10-01-09:00 -> 2025-10-06-17:00
- earliest child start (step1), latest child end (step4).

The file's own comment ("must split across week boundary when hitting 20h weekly cap")
matches this result. No AMBIGUOUS points.

## the reference scheduler cross-check

The original file runs in the reference scheduler 3.8.4 as it is: chain 10-01 09:00 -> 10-06 17:00, step1 10-01
09:00-17:00, step2 10-02 09:00-17:00, step3 10-03 09:00 -> 10-06 13:00, step4 10-06
13:00-17:00. **Agrees** exactly. The worker has explicit hours, so the reference scheduler's different default
day does not apply.
