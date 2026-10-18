# timezone_stress.tjp — derivation

Project `Global_Ops`, timezone Etc/UTC (= UTC), period 2025-05-01 00:00 +1w = up to
2025-05-08 00:00. **2025-05-01 is a Thursday**; the file's comment calls it "Mon May 1".
Both are working days, so nothing changes. Times below are UTC unless marked. All on whole
hours, so slots are 60 min.

## Calendars

Shift `local_9to6` = Mon-Fri 09:00-18:00 (540 min). Each resource works it in its own
`timezone` (brief: "a resource with its own timezone works its hours in that zone, through
DST changes").

- `dev_jp`: Asia/Tokyo, UTC+9, no DST. 09:00-18:00 JST = **00:00-09:00 UTC** on the same
  weekday.
- `qa_ny`: America/New_York. US daylight saving began 2025-03-09, so on 1 May New York is on
  **EDT = UTC-4**, not EST (UTC-5) as the file's comment assumes. 09:00-18:00 EDT =
  **13:00-22:00 UTC** on the same weekday. (No DST change between 1 and 8 May.)

## Tasks

### follow_sun.step1_jp — 2025-05-01-00:00 -> 2025-05-01-09:00
- Declared `start 2025-05-01-00:00` UTC = Thu 09:00 JST, the first minute of Tokyo's
  Thursday shift.
- effort 9h = 540 min at efficiency 1.0: 00:00 + 540 min = **09:00 UTC** (18:00 JST, the end
  of the shift). This agrees with the file's comment.

### follow_sun.step2_ny — 2025-05-01-13:00 -> 2025-05-01-17:00
- `depends !step1_jp`: earliest = Thu 09:00 UTC = 05:00 EDT, before New York's shift.
- First NY working minute after it: Thu 09:00 EDT = **13:00 UTC**. The wait is 4 h, not the
  5 h in the comment.
- effort 4h = 240 min: 13:00 + 240 min = **17:00 UTC** (13:00 EDT).
- The file's comment (start 14:00 UTC, which implies an 18:00 end) assumes EST. It is wrong
  by one hour for May 2025.

### follow_sun (container) — 2025-05-01-00:00 -> 2025-05-01-17:00
- earliest child start (step1 00:00), latest child end (step2 17:00).

## Considered and rejected (not AMBIGUOUS under the brief)

- If the shift's hours were read in project time (UTC) because the shift has no zone of its
  own, step1 would run Thu 09:00-18:00 UTC and step2 Fri 09:00-13:00 UTC. The brief says a
  zoned resource works its hours in its zone, so I rejected this.

## the reference scheduler cross-check

- The original does not parse in the reference scheduler 3.8.4 (`shift local_9to6 {` has no name string; the reference scheduler has
  no resource `timezone`).
- a translated copy (not kept) (zoned shifts) gave step1 09:00-18:00 UTC and step2
  Fri 09:00-13:00. the reference scheduler 3.8.4 does not apply a shift's `timezone` to its working hours (probe
  a translated copy (not kept)), so that run uses unconverted hours and says
  nothing about this file. It is a limit of the the reference scheduler translation, not a scheduling
  disagreement.
- a translated copy (not kept) (hours converted by hand: Tokyo 00:00-09:00 UTC,
  NY 13:00-22:00 UTC) gives follow_sun 05-01 00:00-17:00, step1 00:00-09:00, step2
  13:00-17:00. **Agrees** exactly.
