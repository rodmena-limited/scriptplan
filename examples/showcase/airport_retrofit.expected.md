# airport_retrofit — hand derivation

Project `Airport_BHS_Upgrade`, 2025-09-01 00:00 UTC, +2m (about 60.8 days, so it runs to
about 2025-10-31; every task below ends by 2025-09-16, so the period never binds).
Timezone `Etc/UTC` == UTC. 2025-09-01 is a Monday.

Checked by my own stdlib walker `out/walk_airport.py` (exact Fraction seconds,
output in `out/walk_airport.output.txt`). It agrees with every number below.

## Calendars

| Calendar | Working time |
|---|---|
| global `vacation "Public Holiday" 2025-09-05` | Fri 2025-09-05 blocked all day, for every resource |
| `standard_shift` | Mon–Fri 09:00–17:00 (480 min/day) |
| `night_shift` `mon - fri 22:00 - 06:00` | crosses midnight: Mon–Fri 22:00–24:00, plus the after-midnight part on the **following** day, Tue–Sat 00:00–06:00. Monday 00:00–06:00 is NOT working (no Sunday interval). |
| arch | standard_shift, efficiency 1.0, vacation 2025-09-11 (–09-12), which no task reaches |
| crew | night_shift, efficiency 1.0 |
| sparky | standard_shift, efficiency 0.8 |

`workinghours standard_shift` (a shift name after `workinghours`) is not the reference scheduler syntax.
I read it as "this resource works the shift's hours", which is clearly what the file means.

## Tasks

### bhs.design — 2025-09-01-09:00:00 → 2025-09-08-17:00:00
- Start: declared `start 2025-09-01-09:00`, a working moment for arch.
- Effort 40h at efficiency 1.0 = 40 h = 2400 min of arch.
- Mon 1, Tue 2, Wed 3, Thu 4: 4 × 480 = 1920 min. Fri 5 is the public holiday. Sat 6 and Sun 7 are off.
  Mon 8, 09:00–17:00: 480 min. Total 2400 min → ends **Mon 2025-09-08 17:00**.
- The arch vacation (Sep 11) comes after design ends, so it does not matter whether its end is inclusive.

### bhs.demo — 2025-09-08-22:00:00 → 2025-09-10-06:00:00
- Earliest start: design end, Mon 09-08 17:00. crew's next working moment is Mon 22:00.
- Effort 16h at efficiency 1.0 = 960 min of crew.
- Mon 22:00–24:00 (120) + Tue 00:00–06:00 (360) = 480; Tue 22:00–24:00 (120) + Wed 00:00–06:00 (360) = 960
  → ends **Wed 2025-09-10 06:00**.
- Under the older ScriptPlan reading of a midnight crossing (00:00–06:00 on the same day), the answer is the
  same: only Monday morning and Saturday morning differ, and demo touches neither.

### bhs.wiring — 2025-09-10-09:00:00 → 2025-09-16-17:00:00
- `depends !demo { gapduration 24h onstart }`. Brief: the dependency is on demo's **start**, plus a calendar gap.
  Earliest = Mon 09-08 22:00 + 24 h = Tue 09-09 22:00. sparky's next working moment is **Wed 09-10 09:00**.
- Effort 32h at efficiency 0.8 → 32 / 0.8 = 40 h = 2400 min of sparky.
- Wed 10, Thu 11, Fri 12 (3 × 480 = 1440), Mon 15 (1920), Tue 16 (2400) → ends **Tue 2025-09-16 17:00**.
- AMBIGUOUS: what `onstart` means.
  - Chosen: start-to-start, as the brief says ("each predecessor's end (or start, for `{ onstart }`)") and as
    the reference scheduler does. Result: 2025-09-10-09:00 → 2025-09-16-17:00.
  - Alternative A (onstart not honoured, so end-to-start + 24h): earliest Thu 09-11 06:00 → 09:00; 2400 min
    → **2025-09-11-09:00 → 2025-09-17-17:00** (bhs then ends 2025-09-17-17:00).
  - Alternative B: README "Known limits" says ScriptPlan reads `onstart` as "the dependent task must finish
    before the predecessor starts". If the engine applies that here, wiring is no longer after demo. One
    plausible result: wiring runs ASAP from the project start, 2025-09-01-09:00 → 2025-09-08-17:00
    (Sep 1–4 plus Mon Sep 8, skipping the holiday). demo is then held to wiring end + 24h = Tue 09-09 17:00 → 22:00,
    giving 2025-09-09-22:00 → 2025-09-11-06:00, and bhs 2025-09-01-09:00 → 2025-09-11-06:00.
    Or the engine reports a conflict, because demo cannot start before Mon 09-08 22:00 and wiring cannot end by
    Sun 09-07 22:00. This reading contradicts the brief, so I did not use it. If the engine disagrees with
    the chosen row, check this first.

### bhs (container) — 2025-09-01-09:00:00 → 2025-09-16-17:00:00
Earliest child start (design) and latest child end (wiring).

## the reference scheduler cross-check

the reference scheduler rejects the file as written:
- `shift standard_shift {` (the reference scheduler wants a name string),
- `workinghours standard_shift` (the reference scheduler uses `shifts standard_shift`),
- `22:00 - 06:00` ("End time of interval must be larger than start time").

So I ran two variants in a translated copy (not kept):
- `v1`: only the names and `shifts` fixed. the reference scheduler still rejects 22:00 - 06:00.
- `v2`: also splits the night shift explicitly: Mon 22–24; Tue–Fri 0–6 and 22–24; Sat 0–6.

the reference scheduler on v2:

| id | the reference scheduler start | the reference scheduler end | mine |
|---|---|---|---|
| bhs | 2025-09-01-09:00 | 2025-09-16-17:00 | same |
| bhs.design | 2025-09-01-09:00 | 2025-09-08-17:00 | same |
| bhs.demo | 2025-09-08-22:00 | 2025-09-10-06:00 | same |
| bhs.wiring | 2025-09-10-09:00 | 2025-09-16-17:00 | same |

There are no disagreements. Every boundary is on the hour and every resource has explicit hours, so neither
slot rounding nor default hours come into it.
