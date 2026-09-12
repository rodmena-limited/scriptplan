# WS1 Units and calendar arithmetic

**Ticket**: issuedb #3  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 3` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- ScriptPlan shall convert calendar durations as min=60s, h=3600s, d=86400s, w=7d, m=30.4167d, y=365d.
- ScriptPlan shall convert working durations using dailyworkinghours and yearlyworkingdays (d=dailyworkinghours, w=d*yearlyworkingdays/52.1429, m=d*yearlyworkingdays/12, y=d*yearlyworkingdays).
- The unit 'm' shall mean months and 'min' shall mean minutes in every duration context.
- gapduration shall be calendar time and gaplength working time; a gaplength smaller than one slot shall not be truncated to zero.
- If a limit is written with a duration unit, then ScriptPlan shall convert it with the same table (dailymax 30min shall be 1800 seconds, not 30 months).
- Resource daily/weekly/monthly limits shall count periods in the resource's local calendar.
- The grammar shall accept dailymin, weeklymin, monthlymax, monthlymin, maximum and minimum limits, and maxend/maxstart/minend/minstart dates.
- When a working-hours interval crosses midnight, the part after midnight shall apply to the following weekday only.
- A single-day vacation or leave shall block the whole of that day.

TECHNICAL PROBLEMS:
1. Duration lexing and conversion duplicated in five places with three different tables.
2. Calendar-period bucketing under a resource timezone.
3. Weekday interval rendering across a midnight boundary.

SOLUTION DOMAINS:
- Unit tables -> TaskJuggler rule_calendarDuration (confirmed from TjpSyntaxRules.rb) and rule_workingDuration.
- Period bucketing -> stdlib zoneinfo + isocalendar; calendar months via dateutil.relativedelta (already a dependency).
- Midnight-crossing intervals -> normalise at definition time into (weekday, start, end) pairs with end<=1440, splitting the tail onto weekday+1.

ALTERNATIVES:
- Units: one core/units.py returning typed Duration(kind, seconds) [CHOSEN] vs per-call-site regexes [REJECTED: this is the current defect] vs a third-party duration parser [REJECTED: none implements TaskJuggler working-vs-calendar units].
- Midnight crossing: normalise at set_hours time [CHOSEN: onShift becomes a pure lookup] vs check the previous weekday at query time [REJECTED: this is the current code and it is wrong in both the Python and Cython paths].

---

## Outcome

**Status**: closed.

core/units.py is the single duration table, with calendar and working time distinguished and carried from the grammar to where the project's working-hours settings are known. `duration` and `length` are parsed, stored and scheduled. core/limits.py was rewritten to count seconds in the resource's own calendar and to admit partial slots, so `dailymax 6.4h` is exact; all eight limit kinds reach the grammar, as do maxend/maxstart/minend/minstart. Cross-midnight working hours are split at definition time.

Probes: probe_units 9/9, probe_calendar 8/8, probe_limits 6/6.
