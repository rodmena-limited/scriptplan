# blackbox — hand derivation

Source: `src/blackbox.tjp`. Report times are UTC (project `Etc/UTC`).
Arithmetic check: `out/walk6.py` (stdlib only, zoneinfo for the zones; no scriptplan).

## Inputs

- Project period: 2025-01-01 00:00 + 1m (30.4167 d) = up to 2025-01-31 ~10:00. 2025-01-01 is
  a Wednesday. No global vacations.
- `agent_a`: timezone Europe/Athens (EET, UTC+2 all of January, no DST change), hours
  `alpha_shift` = Mon-Wed 10:00-14:00 Athens = **Mon-Wed 08:00-12:00 UTC**, 240 min a day.
  Efficiency 0.5.
- `agent_b`: timezone America/Los_Angeles (PST, UTC-8 all of January), hours `beta_shift` =
  Thu-Sun 18:00-22:00 LA = **Fri-Mon 02:00-06:00 UTC** (each LA evening crosses midnight
  UTC: LA Thu 18:00 = UTC Fri 02:00). 240 min a day. Efficiency 2.0.
- Efficiency rule (brief): resource time = effort / efficiency.

## operations.phase_1 (ASAP, effort 4h, agent_a, start 2025-01-01-00:00)

- Earliest start: max(project start, declared start) = Wed 1 Jan 00:00 UTC.
- Resource time needed: 240 min / 0.5 = 480 min of agent_a.
- Walk (UTC):
  - Wed 1 Jan 08:00-12:00: 240 min of agent_a = 120 min effort (120 done, 120 left)
  - Thu 2 - Sun 5 Jan: agent_a does not work (only Mon-Wed)
  - Mon 6 Jan 08:00-12:00: 240 min = 120 min effort (240 done)
- **start 2025-01-01 08:00 (first work), end 2025-01-06 12:00** (= 14:00 Athens).
- agent_a busy Wed 1 Jan 08-12 and Mon 6 Jan 08-12 UTC.

## operations.phase_2 (ASAP, effort 4h, agent_b, depends !phase_1)

- Earliest start: phase_1 end = Mon 6 Jan 12:00 UTC = Mon 6 Jan 04:00 LA.
- Resource time needed: 240 min / 2.0 = 120 min of agent_b.
- agent_b's previous window, LA Sun 5 Jan 18:00-22:00 = UTC Mon 6 Jan 02:00-06:00, is
  before 12:00 UTC and so not usable. LA Mon/Tue/Wed have no hours. Next window: LA Thu
  9 Jan 18:00-22:00 = UTC Fri 10 Jan 02:00-06:00.
- 120 min from 02:00: **start 2025-01-10 02:00, end 2025-01-10 04:00 UTC** (= Thu 9 Jan
  18:00-20:00 LA).

## operations (container)

- min child start = 2025-01-01 08:00; max child end = 2025-01-10 04:00.

## AMBIGUOUS

1. **AMBIGUOUS: reported start of phase_1.** The file declares `start 2025-01-01-00:00`,
   but agent_a's first working minute is 08:00 UTC. The brief says the task starts at the
   latest of its bounds and "then takes the earliest free working time of its resources from
   there", but does not say which of the two an effort task *reports*. Chosen: the first
   booked minute, 2025-01-01 08:00 (the reference scheduler reports this too, see below).
   Alternative: the declared start, 2025-01-01 00:00 (and then `operations` would also
   start 00:00).
2. **AMBIGUOUS: what `workinghours <days> <hours>` does to the days it does not list.**
   The brief says workinghours on a resource or shift "replace the default for it". Chosen:
   the whole week is replaced, so alpha has no Thu-Sun hours and beta no Mon-Wed hours
   (this is also what the file's "disjoint calendars" comment intends). Alternative
   (the reference scheduler's behaviour, measured below): only the listed weekdays are replaced and
   the unlisted Mon-Fri keep the 09:00-17:00 default. Under that reading:
   phase_1 2025-01-01 08:00 -> 2025-01-02 11:00 (default read in Athens) or -> 13:00
   (default read in UTC); phase_2 2025-01-03 02:00 -> 04:00; operations ends 2025-01-03
   04:00.

## the reference scheduler cross-check

the reference scheduler rejects the file as written (a `shift` without a name string; `workinghours <shift>`;
no `timezone` on a resource). Variants in a translated copy (not kept):

| variant | phase_1 | phase_2 |
|---|---|---|
| `blackbox_utc` (hours converted to UTC by hand, inline) | 01-01 08:00 -> 01-02 13:00 | 01-02 13:00 -> 15:00 |
| `blackbox_utc_off` (same, unlisted weekdays set `off`) | **01-01 08:00 -> 01-06 12:00** | **01-10 02:00 -> 04:00** |
| `blackbox_shift` (the reference scheduler shifts carrying `timezone`, via `shifts`) | 01-01 10:00 -> 01-02 13:00 | 01-02 18:00 -> 20:00 |
| `blackbox_shift_off` (same, unlisted weekdays `off`) | 01-01 10:00 -> 01-06 14:00 | 01-09 18:00 -> 20:00 |

- `blackbox_utc_off` agrees with the derivation on every row, including the 08:00 reported
  start despite the declared 00:00 start.
- `blackbox_utc` differs only because the reference scheduler's `workinghours mon - wed ...` leaves Thu/Fri at
  its default (a probe, a translated copy (not kept), shows unlisted weekdays get
  09:00-17:00 in the reference scheduler 3.8.4), so agent_a also works Thu 2 Jan. Explained by default working
  hours (the AMBIGUOUS point 2 above). Note: the brief says the reference scheduler's default day is 09:00-12:00 +
  13:00-18:00, but a translated copy (not kept) (hourly booking dump) shows the reference scheduler 3.8.4 here
  booking a resource with no `workinghours` 09:00-17:00 straight through, the same as
  ScriptPlan's default.
- The `blackbox_shift*` variants show the reference scheduler 3.8.4 reading the shift's hours as UTC (10:00-14:00
  UTC, 18:00-22:00 UTC) despite the shift's `timezone`; that is the reference scheduler not applying the zone in
  this construction, not a different reading of the file. The hand-converted UTC variant is
  the meaningful cross-check, and it agrees exactly.
