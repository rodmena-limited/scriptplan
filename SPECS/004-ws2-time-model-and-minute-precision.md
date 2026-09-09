# WS2 Time model and minute precision

**Ticket**: issuedb #4  
**Status**: open  
**Priority**: medium

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 4` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- ScriptPlan shall interpret naive file dates in the project timezone and store scheduling times as UTC internally.
- Reports shall render times in the report timezone, else the project timezone.
- While timingresolution is R, ScriptPlan shall honour explicit start/end minutes exactly (start 09:30 with 2h effort shall end 11:30).
- ScriptPlan shall compute shift boundaries at minute precision regardless of R (08:13-11:59 plus 13:07-17:47 shall yield 8h26m of capacity per day).
- ScriptPlan shall derive the effective resolution from the file when timingresolution is absent, and shall validate that 60 <= R <= 3600 and 86400 mod R == 0.

TECHNICAL PROBLEMS:
1. Mapping wall-clock instants to slots without losing sub-slot offsets.
2. Partial-slot capacity accounting when a shift starts mid-slot.
3. Timezone ingest at the parser boundary without breaking UTC fixtures.

SOLUTION DOMAINS:
- Slot algebra -> TimeAxis object (index<->UTC datetime, local period keys).
- Partial capacity -> the existing partial-slot machinery in resource_scenario.py:361-471, generalised to shift overlap.
- Timezone -> stdlib zoneinfo.

ALTERNATIVES:
- Precision: derive the effective resolution as gcd of the file's time offsets [CHOSEN: hour-aligned files keep 3600 and today's performance; 08:13 files get 60 automatically] vs always 60s [REJECTED: 525k slots per resource-year for every project] vs require the user to set timingresolution [REJECTED: README claims minute accuracy out of the box].
- Timezone: convert on ingest, store UTC [CHOSEN] vs carry aware datetimes everywhere [REJECTED: every comparison and every report format becomes tz-sensitive; larger blast radius].
