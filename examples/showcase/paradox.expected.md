# paradox.tjp: derivation

Helpers: `oracle_jpq/walk_jpq.py` (output in `oracle_jpq/walk_jpq.output.txt`) and the
the reference scheduler variants in a translated copy (not kept).

## Setting

- Project 2025-12-25 00:00 UTC, `+2w`, so it ends 2026-01-08 00:00 UTC. Everything is reported in UTC.
- `scheduling alap` for every task.
- Shift `daily` is Mon-Sun 09:00-15:00, 360 min a day. Each resource works it in its own timezone: "a resource with its own timezone works its hours in that zone".
- **k**: Pacific/Kiritimati, UTC+14, no DST.
  - Local day D 09:00-15:00 is UTC (D-1) 19:00 to D 01:00.
  - Efficiency 0.5, so effort 3h = 180 min needs 180 / 0.5 = **360 min** of k.
- **n**: Pacific/Niue, UTC-11, no DST.
  - Local day D 09:00-15:00 is UTC D 20:00 to (D+1) 02:00.
  - Efficiency 2.0, so effort 12h = 720 min needs 720 / 2.0 = **360 min** of n.
- All edges are on whole hours, so the slots are 1 h and nothing falls mid-slot.

## How each bound is reached

| edge in the file | read as |
|---|---|
| `sequence { end 2025-12-31-23:00 }` | Container end as stated. It is passed down to ALAP children without their own end, as in jit_supply, the README example and the the reference scheduler manual. |
| `a depends !!b { gapduration 48h onstart }` | `!!b` resolves to `sequence.b` (P2). The README onstart reading applies, "the dependent task must finish before the predecessor starts": a must finish, then at least 48 h of calendar time pass (gapduration is calendar, 48h = 2880 min), then b starts. So **a.end + 48h <= b.start** (P1). |

Backward order: b has no successor, so its bound is the inherited end and it goes first. a goes once b is scheduled.

## Tasks

**sequence.b** (360 min of k)
- Latest end = min(inherited 2025-12-31 23:00, project end 2026-01-08 00:00) = **2025-12-31 23:00 UTC**. That is 2026-01-01 13:00 Kiritimati time, inside k's 1 January window, so the end is not moved.
- Backward:
  - Window for local 1 Jan, UTC 12-31 19:00 to 01-01 01:00. The part before 23:00 is 19:00-23:00 = 240 min, leaving 120.
  - Window for local 31 Dec, UTC 12-30 19:00 to 12-31 01:00. The last 120 min are 12-30 23:00 to 12-31 01:00 (local 31 Dec 13:00-15:00), leaving 0.
- start **2025-12-30 23:00**, end **2025-12-31 23:00** UTC. In local time that is 31 Dec 13:00 to 1 Jan 13:00 LINT.
- Check: 240 + 120 = 360 min of k, x 0.5 = 180 min = 3h of effort.

**sequence.a** (360 min of n)
- Latest end = min(inherited 12-31 23:00, b.start - 48h).
- b.start - 48h = 2025-12-30 23:00 - 2880 min = 2025-12-28 23:00, so the latest end is **2025-12-28 23:00 UTC**.
- That is 28 Dec 12:00 Niue time, inside n's 28 December window (UTC 12-28 20:00 to 12-29 02:00), so the end is not moved.
- Backward:
  - 12-28 20:00-23:00 = 180 min, leaving 180.
  - Window for local 27 Dec, UTC 12-27 20:00 to 12-28 02:00. The last 180 min are 12-27 23:00 to 12-28 02:00 (local 27 Dec 12:00-15:00), leaving 0.
- start **2025-12-27 23:00**, end **2025-12-28 23:00** UTC. In local time that is 27 Dec 12:00 to 28 Dec 12:00 NUT.
- Check: 360 min of n x 2.0 = 720 min = 12h of effort. Gap b.start - a.end = 12-30 23:00 - 12-28 23:00 = 2880 min = 48 h exactly.
- It starts after the project start (12-25 00:00), so it fits.

**sequence** (container)
- start = earliest child start = a, 2025-12-27 23:00.
- end = the stated 2025-12-31 23:00, which is also b's end.

## AMBIGUOUS

**P1. `onstart` with a gap.**
- Chosen: the README reading, a.end + 48h <= b.start. Result as above.
- Alternative: the brief's ASAP line and the reference scheduler, start-to-start with gap: a.start >= b.start + 48h. Then a is b's successor. Depending on how the engine bounds b, there are three outcomes:
  - **B.** a is placed first from the inherited end: a = 2025-12-30 23:00 to 2025-12-31 23:00.
    - b must then start no later than a.start - 48h = 2025-12-28 23:00.
    - If the engine bounds b's *end* by that moment (the brief's literal "successor's start" minus the gap): b = 2025-12-27 23:00 to 2025-12-28 23:00.
    - If only b's *start* is bounded: b = 2025-12-28 23:00 to 2025-12-29 23:00.
    - sequence starts at b.start.
  - **B'.** What the reference scheduler does: b is ALAP from the inherited end, 2025-12-30 23:00 to 2025-12-31 23:00, and a is pushed to b.start + 48h, giving 2026-01-01 23:00 to 2026-01-02 23:00.
    - That is past sequence's stated end. Under "a task that does not fit is UNSCHEDULABLE", a would be **UNSCHEDULABLE**.

**P2. Reference `!!b`.**
- From `sequence.a`, the reference scheduler resolves `!!` to the root, where there is no top-level `b`.
- Chosen: it resolves to `sequence.b`, the only b. The example renders in ScriptPlan per SPECS/001.
- Alternative: an unresolved-reference parse error.

**Decided, not ambiguous: shift hours are read in each resource's timezone** (brief: "a resource with its own timezone works its hours in that zone").
- If they were read in project UTC instead (alternative C): b = 2025-12-31 09:00-15:00, and a has latest end 12-29 09:00, moved back to 12-28 15:00, giving a = 2025-12-28 09:00-15:00.

## the reference scheduler cross-check

**Original file.** Rejected: `scheduling` is not allowed in the project block, the reference scheduler resources have no `timezone` attribute, and `workinghours daily` (a shift id) is not the reference scheduler syntax.

**a translated copy (not kept).** Per-resource shifts carry the timezone, and the edge is written as `a precedes !b { gapduration 48h }`.
- the reference scheduler: a 2025-12-28 09:00-15:00, b 2025-12-31 09:00-15:00. That is alternative C.
- **Explained:** the reference scheduler 3.8.4 ignores shift timezones. `tzprobe.tjp` shows New York, Kiritimati and plain shifts all working from 09:00 UTC.
- It still confirms the 48 h gap arithmetic: 12-31 09:00 - 48h = 12-29 09:00, moved back to 12-28 15:00.

**a translated copy (not kept).** Each resource's local hours are written out in UTC: k `00:00-01:00, 19:00-24:00`, n `00:00-02:00, 20:00-24:00`. Same `precedes` edge.
- the reference scheduler: a 2025-12-27 23:00 to 2025-12-28 23:00, b 2025-12-30 23:00 to 2025-12-31 23:00, sequence 2025-12-27 23:00 to 2025-12-31 23:00.
- **Exact agreement** with the table above.

**a translated copy (not kept).** The same, with `onstart` kept.
- the reference scheduler: b 2025-12-30 23:00 to 2025-12-31 23:00, a 2026-01-01 23:00 to 2026-01-02 23:00, after the container's end. the reference scheduler does not complain.
- This is reading B' of P1, an expected difference from the README reading.
