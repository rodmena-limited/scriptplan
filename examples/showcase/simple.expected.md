# simple.tjp: derivation

## Setting

- Project 2024-01-01 00:00 America/New_York, a Monday. `+3m` = 3 x 30.4167 d = 91.25 d, so it ends around 2024-04-01; it never binds.
- Timezone America/New_York. EST (UTC-5) throughout, because the DST change on 2024-03-10 is never reached. Everything is reported in New York time.
- No resource has `workinghours`, so dev1 and dev2 work the ScriptPlan default: Mon-Fri 09:00-17:00 New York time, 480 min a day.
- No holidays or leaves are declared, so 1 January is an ordinary Monday.
- `d` = dailyworkinghours, default 8h = 480 min.
- `rate`, `email`, `flags`, accounts and `now 2024-02-01` do not affect dates: there are no bookings or completion data.
- Scenario `delayed` overrides nothing, so it schedules the same as `plan`. The rows are the plan scenario.
- All edges are on the hour, so the slots are 1 h.

## Tasks

**project.spec** (effort 10d = 4800 person-min, dev1 and dev2)
- Earliest start = project start, Mon 01-01 00:00. The first working moment is 09:00.
- Both resources are free and have identical calendars, so each contributes 480 min a working day. Together that is 960 person-min a day.
- 4800 / 960 = 5 working days: Mon 01-01 to Fri 01-05, each resource 09:00-17:00.
- start **2024-01-01 09:00**, end **2024-01-05 17:00**. dev1 and dev2 are both busy Mon 1 to Fri 5, 09:00-17:00.

**project.impl** (effort 20d = 9600 min, dev1; depends spec)
- Earliest start = spec end, Fri 01-05 17:00. The first working moment after that is Mon 01-08 09:00.
- 9600 / 480 = 20 working days: the weeks of 8, 15, 22 and 29 January, the last ending Fri 2 Feb.
- start **2024-01-08 09:00**, end **2024-02-02 17:00**. dev1 is busy on all 20 of those days.

**project.test** (effort 5d = 2400 min, dev2; depends impl)
- Earliest start = impl end, Fri 02-02 17:00. The first working moment is Mon 02-05 09:00.
- dev2 has been free since 01-05.
- 2400 / 480 = 5 days, Mon 5 Feb to Fri 9 Feb.
- start **2024-02-05 09:00**, end **2024-02-09 17:00**.

**project** (container)
- start **2024-01-01 09:00**, end **2024-02-09 17:00**.

These are the dates that follow from effort being person-time. SPECS/005 notes that simple.tjp "finish[es] sooner because effort is now shared".

## AMBIGUOUS

None.

## the reference scheduler cross-check

Original file, unchanged:
- project 01-01 09:00 to 02-09 17:00
- spec 01-01 09:00 to 01-05 17:00
- impl 01-08 09:00 to 02-02 17:00
- test 02-05 09:00 to 02-09 17:00

**Identical.**

The brief expects the reference scheduler's default day to be 09:00-12:00 plus 13:00-18:00. This the reference scheduler 3.8.4 install actually uses 09:00-17:00 by default. In a translated copy (not kept), a 4h effort runs 09:00-13:00 and the next 8h runs 13:00 to 13:00 the next day, under both UTC and New York. So the expected default-hours difference does not occur. Even with the brief's the reference scheduler day, 8h a day gives the same days, and only the end times would read 18:00.
