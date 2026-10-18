# time_traveler.tjp — derivation

Project `Time_Traveler`, timezone Etc/UTC (= UTC), period 2025-06-01 00:00 (Sunday) +2w =
up to 2025-06-15 00:00 (Sunday). Project-wide `scheduling alap`. Times below are UTC
unless marked JST/BST. All on whole hours, so slots are 60 min.

## Calendars (resource zones; there is no DST change in June for either zone)

- `dev_tokyo`: Asia/Tokyo (UTC+9, no DST), Mon-Fri 09:00-18:00 JST = **00:00-09:00 UTC**
  on the same weekday (540 min a day).
- `des_london`: Europe/London, in British Summer Time all June (UTC+1), Mon-Fri 09:00-18:00
  BST = **08:00-17:00 UTC** (540 min a day).
- Shift `standard` is defined but nothing uses it.

## Readings used

- `design depends !!impl { onstart }`: the README's "Known limits" says ScriptPlan reads
  `A depends B { onstart }` as "A must finish before B starts". So **design.end <=
  impl.start**, which is what the file's own comment says ("Design must finish before Tokyo
  starts").
- `!!impl` from `launch.design` is taken as the sibling `launch.impl`, the only task called
  `impl`. The README's own example uses `!!pack` for a sibling in the same way. (Under
  the reference scheduler's strict rule `!!` goes one level higher, to a top-level `impl` that does not exist.)
- `launch` states `end 2025-06-13-09:00`. Its children may not end after it. As shown
  below, the bound from the project end gives the same answer, so it does not matter
  whether the container end is inherited.

## Tasks

### launch.impl — 2025-06-13-00:00 -> 2025-06-13-09:00
- ALAP. Latest end = min(container end Fri 2025-06-13 09:00, project end 2025-06-15 00:00)
  = Fri 09:00 UTC = Fri 18:00 JST, which is exactly the end of Tokyo's Friday shift.
- Its only constraint from `design` is the other way round (design must end before impl
  starts), so impl has no successor that bounds its end.
- effort 9h = 540 min at efficiency 1.0. Backwards from Fri 09:00 UTC, Tokyo's Friday shift
  00:00-09:00 UTC has exactly 540 min, so start = 09:00 - 540 min = Fri **00:00 UTC**
  (09:00 JST).
- Check with the project end alone: 2025-06-15 00:00 UTC = Sun 09:00 JST. Sat and Sun JST
  are off, and the latest Tokyo work before it is again Fri 00:00-09:00 UTC. Same result.

### launch.design — 2025-06-12-08:00 -> 2025-06-12-17:00
- ALAP. Latest end = min(impl.start Fri 2025-06-13 00:00, container end Fri 09:00) = Fri
  00:00 UTC = Fri 01:00 BST, before London's Friday shift begins.
- The latest London working time before that is Thu 2025-06-12 08:00-17:00 UTC (09:00-18:00
  BST), 540 min.
- effort 9h = 540 min: end = Thu **17:00 UTC**, start = 17:00 - 540 min = Thu **08:00 UTC**.
- Order: design's bound needs impl's start, so impl is placed first (the brief: a
  successor's start counts once the successor is scheduled).

### launch (container) — 2025-06-12-08:00 -> 2025-06-13-09:00
- start = earliest child start (design, Thu 08:00). end = stated `end 2025-06-13-09:00`,
  which is also the latest child end (impl).

## Notes on readings (decided by the README, not AMBIGUOUS)

- Under the reference scheduler's start-to-start reading of `onstart` (design.start >= impl.start = Fri
  00:00 UTC), design would have to run 540 min of London time between Fri 08:00 and the
  container end at 09:00. Only 60 min exist there, so it would not fit. The README states
  ScriptPlan's reading explicitly, so I used that.

## the reference scheduler cross-check

- The original does not parse in the reference scheduler 3.8.4 (`scheduling` inside the project header; also the reference scheduler
  has no resource `timezone`).
- the reference scheduler's shift `timezone` turned out not to move working hours in 3.8.4 (probe
  a translated copy (not kept): a Tokyo shift still worked 09:00-18:00 UTC).
  So the zoned-shift translations a translated copy (not kept) and
  a translated copy (not kept) give hours that are not converted, and I do not use them.
- a translated copy (not kept) (hours converted to UTC by hand, and
  ScriptPlan's onstart reading written as `design precedes !impl`): launch 06-12 08:00 ->
  06-13 09:00, design 06-12 08:00-17:00, impl 06-13 00:00-09:00. **Agrees** exactly.
- a translated copy (not kept) (the reference scheduler's own `depends !impl { onstart }`):
  impl 06-13 00:00-09:00, design 06-13 08:00-17:00, and the reference scheduler lets launch run on to 17:00,
  past its stated end. The difference is expected: it is the documented onstart divergence
  (README "Known limits"), not rounding.
