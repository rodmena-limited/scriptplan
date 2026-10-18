# thermal.tjp — derivation

Project `Thermal_Shock`, timezone Etc/UTC (= UTC), period 2025-05-10 00:00 (Saturday)
+1w = up to 2025-05-17 00:00 (Saturday). Every time below is UTC. All times in the file
fall on whole hours, so slots are 60 min and nothing starts or ends inside a slot.

## Calendars

- Shift `standard` = Mon-Fri 09:00-17:00 (480 min a day). `heater` and `press` both use it
  (`workinghours standard` points at the shift; it is the same as the default day).
- `press` has `booking "Maintenance" 2025-05-12-09:00 +6h`. `+6h` is calendar time:
  09:00 + 360 min = 15:00, so the press is busy Mon 2025-05-12 09:00-15:00.
- Sat 10 and Sun 11 May are not working days for either resource.

## Tasks

### process.heat — 2025-05-12-09:00 -> 2025-05-12-11:00
- ASAP, no predecessor, no declared start: earliest = project start, Sat 2025-05-10 00:00.
- First working minute of `heater` at or after it: Mon 2025-05-12 09:00.
- effort 2h = 120 min at efficiency 1.0 -> 120 min of heater time: 09:00 + 120 min = 11:00.

### process.forge — 2025-05-12-15:00 -> 2025-05-12-17:00
- `depends !heat { gapduration 0min maxgapduration 60min }`: earliest = heat end 11:00 + 0 min
  = Mon 11:00.
- `press` is busy with the maintenance booking 09:00-15:00, so its first free working minute
  from 11:00 is 15:00.
- effort 2h = 120 min: 15:00 + 120 min = 17:00 (exactly the end of the shift).
- Achieved gap heat.end -> forge.start = 15:00 - 11:00 = 240 min > `maxgapduration` 60 min.
  The README says `maxgapduration` is checked once the schedule is complete and a violation
  is an error (SPECS/005: "report an error naming both tasks and the achieved gap").
  So I expect the dates above **plus an error** `heat -> forge gap 240 min > 60 min`, and a
  non-zero exit.

### process (container) — 2025-05-12-09:00 -> 2025-05-12-17:00
- earliest child start (heat 09:00), latest child end (forge 17:00).

## AMBIGUOUS points

- AMBIGUOUS: what the engine reports for `process.forge` when the `maxgapduration` check
  fails. Chosen: the placement is kept (15:00-17:00) and the violation is reported as an
  error after scheduling, as the README describes. Alternative: the engine refuses the task
  (`UNSCHEDULABLE` for process.forge, and then the container covers heat only, 09:00-11:00),
  or the whole run fails without dates. A third reading, which ScriptPlan's docs do not
  describe, would delay heat so that the gap fits (heat 12:00-14:00 or later, forge
  15:00-17:00). ASAP placement never backtracks, so I did not use it.
- AMBIGUOUS: the meaning of `booking "Maintenance" <interval>` on a resource. The brief does
  not cover resource bookings. Chosen: the press is busy for that interval (09:00-15:00 Mon).
  Alternatives: (a) the booking is ignored, which gives forge 11:00-13:00, gap 0, no error,
  container 09:00-13:00; (b) `"Maintenance"` is read as a task reference that does not
  resolve, which is a parse error (SPECS/002: unresolved references are errors).

## the reference scheduler cross-check

- The original file does not parse in the reference scheduler 3.8.4 (`workinghours standard`: the reference scheduler expects a
  weekday there).
- Translation a translated copy (not kept) (hours spelled out, the booking written as a
  timed leave `leaves annual 2025-05-12-09:00 +6h`) is rejected for a different reason: the reference scheduler
  3.8.4 has no `maxgapduration` ("Expecting one of 'gapduration', 'gaplength', 'onend',
  'onstart'"), and it also refuses `gapduration 0min` ("interval duration may not be 0").
- a translated copy (not kept) (both gap attributes removed) gives
  process 05-12 09:00-17:00, heat 09:00-11:00, forge 15:00-17:00. **Agrees** exactly. the reference scheduler
  cannot check the maxgap constraint.


---

# thermal: adjudication

The independent derivation kept `heat` at 09:00-11:00 and read `maxgapduration` as a
check made after scheduling, which then fails. The engine delays `heat` to 13:00-15:00 so
that `forge`, which cannot start before the press maintenance ends at 15:00, follows it
with no gap.

Verdict: the engine's answer is the one this project specifies. Its header ("Forge must
start within 1h of heat ending, or metal cracks") and the hand-derived test for it
(TestIssue65ThermalShock: "Smart scheduling: Heat 13:00-15:00, Forge 15:00-17:00") both
call for delaying the predecessor. The brief given to the oracle did not describe that
behaviour, and README's line on maxgap describes only the after-scheduling check.

Open point, not changed: heat 12:00-14:00 would also meet the 60-minute limit exactly (the
earliest feasible start). The engine and this project choose the just-in-time alignment
(gap 0). Recorded for Farshid's decision; the golden snapshot is left as it is.
