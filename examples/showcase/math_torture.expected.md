# math_torture.tjp - independent derivation

Source: `src/math_torture.tjp`. Project timezone `Etc/UTC` (no DST), `timingresolution 1min`.
Output: `math_torture.expected.csv` (1 container + 500 leaves = 501 rows).

## The file, checked mechanically

A script (not by eye) confirmed: exactly 500 leaf tasks `t_001`..`t_500` inside container `chain`;
every one has `effort 73min` and `allocate cruncher`; `t_001` alone has `start 2024-02-28-08:13`;
every `t_N` (N >= 2) has exactly `depends !t_(N-1) { gapduration 29min }`. No priority, limit,
efficiency, scheduling-mode, duration or length attribute appears anywhere. One resource, so there
is no contention: the chain is a pure calendar walk.

- Shift `prime_shift`: `mon - sun 08:13 - 11:59, 13:07 - 17:47`, every day of the week.
  Morning 08:13-11:59 = 226 min, afternoon 13:07-17:47 = 280 min, **506 min (8h26m) a day**.
- `cruncher` works only that shift, efficiency 1.0.
- Project window: 2024-02-28-00:00 + 4m; m = 30.4167 d (calendar) -> 121.6668 d -> ends
  2024-06-28-16:00:11 (reading `+4m` as four calendar months instead gives 2024-06-28-00:00; both
  are far after the last end, so the choice changes nothing).

## The walker's rules (`math_torture_work/walker.py`, stdlib only)

- **W1** The resource works only inside the shift intervals, each half-open `[start, end)`, wall
  clock in the project timezone (UTC, no DST).
- **W2** Earliest start = declared `start` for `t_001`; for every other task, predecessor end +
  29 min of *calendar* time (`gapduration`), so the gap runs through lunch and through the night.
- **W3** An effort task starts at the first working instant at or after its earliest start.
- **W4** 73 minutes of working time are consumed from the start; reaching the end of an interval,
  the remainder continues at the start of the next one. The end is the instant the 73rd minute
  finishes; an end exactly on an interval end is reported as that instant (never happens here).
- **W5** `chain` spans its children (first child start, last child end).
- **W6** Any end beyond the project window would be UNSCHEDULABLE (none is).

Resolution is 1 min and every quantity (73, 29, shift edges) is a whole number of minutes, so no
task starts or ends inside a slot and no second-level arithmetic arises.

## Hand checks

**t_001** - declared start 2024-02-28-08:13 (Wed), which is the first working minute of the shift.
Work 08:13 + 73 min = **09:26** (inside the 08:13-11:59 block, 153 min left in it).
-> `2024-02-28-08:13:00 ; 2024-02-28-09:26:00`

**t_002** - earliest 09:26 + 29 min = 09:55, inside the morning block -> starts 09:55.
09:55 + 73 min = **11:08** (51 min before the block ends).
-> `2024-02-28-09:55:00 ; 2024-02-28-11:08:00`

**t_003** - earliest 11:08 + 29 = 11:37, inside the morning block -> starts 11:37.
Morning remaining 11:37-11:59 = 22 min; 73 - 22 = 51 min left; the afternoon block opens
13:07; 13:07 + 51 = **13:58**. (The 68 min lunch break 11:59-13:07 is not worked.)
-> `2024-02-28-11:37:00 ; 2024-02-28-13:58:00`

The day then closes as follows (same arithmetic):
- t_004: 13:58 + 29 = 14:27 -> 14:27 + 73 = 15:40.
- t_005: 15:40 + 29 = 16:09 -> 16:09 + 73 = 17:22 (25 min before the 17:47 close).
- t_006: 17:22 + 29 = 17:51, which is after 17:47 -> next working instant is the next day's
  08:13 -> 08:13-09:26 on 2024-02-29, i.e. exactly t_001's times one day later.

So **every day repeats the same five tasks** at 08:13-09:26, 09:55-11:08, 11:37-13:58,
14:27-15:40, 16:09-17:22 (5 x 73 = 365 min booked of the 506 available, the rest is the four
29-min gaps that fall in working time = 116 min, plus 25 min unused before 17:47:
365 + 116 + 25 = 506). Task k sits in position (k-1) mod 5 on day (k-1) div 5.

**t_500 (the last)** - k = 500: day index 499 div 5 = 99 (the 100th day), position 499 mod 5 = 4
(the fifth slot). Day 100 = 2024-02-28 + 99 days: 2024 is a leap year, so Feb 29 is +1,
Mar 31 is +32, Apr 30 is +62, May 31 is +93, **Jun 6 is +99** (a Thursday). Earliest start =
t_499's end 15:40 + 29 = 16:09 -> 16:09 + 73 = **17:22**.
-> `2024-06-06-16:09:00 ; 2024-06-06-17:22:00`. This agrees with the file's own header comment
("run to 2024-06-06").

**chain** = t_001 start .. t_500 end = `2024-02-28-08:13:00 ; 2024-06-06-17:22:00`.
Fits the window (ends 22 days before 2024-06-28). No task is UNSCHEDULABLE.

## Every task

Each of the 100 days below holds five consecutive tasks at the five fixed times above
(the first of each day starts at 08:13 because the previous day's last task ends at 17:22 and
17:22 + 29 = 17:51 is after the shift closes).

| day | date | tasks (positions 1..5 = 08:13-09:26, 09:55-11:08, 11:37-13:58, 14:27-15:40, 16:09-17:22) |
|---|---|---|
| 1 | 2024-02-28 Wed | t_001 - t_005 |
| 2 | 2024-02-29 Thu | t_006 - t_010 |
| 3 | 2024-03-01 Fri | t_011 - t_015 |
| 4 | 2024-03-02 Sat | t_016 - t_020 |
| 5 | 2024-03-03 Sun | t_021 - t_025 |
| 6 | 2024-03-04 Mon | t_026 - t_030 |
| 7 | 2024-03-05 Tue | t_031 - t_035 |
| 8 | 2024-03-06 Wed | t_036 - t_040 |
| 9 | 2024-03-07 Thu | t_041 - t_045 |
| 10 | 2024-03-08 Fri | t_046 - t_050 |
| 11 | 2024-03-09 Sat | t_051 - t_055 |
| 12 | 2024-03-10 Sun | t_056 - t_060 |
| 13 | 2024-03-11 Mon | t_061 - t_065 |
| 14 | 2024-03-12 Tue | t_066 - t_070 |
| 15 | 2024-03-13 Wed | t_071 - t_075 |
| 16 | 2024-03-14 Thu | t_076 - t_080 |
| 17 | 2024-03-15 Fri | t_081 - t_085 |
| 18 | 2024-03-16 Sat | t_086 - t_090 |
| 19 | 2024-03-17 Sun | t_091 - t_095 |
| 20 | 2024-03-18 Mon | t_096 - t_100 |
| 21 | 2024-03-19 Tue | t_101 - t_105 |
| 22 | 2024-03-20 Wed | t_106 - t_110 |
| 23 | 2024-03-21 Thu | t_111 - t_115 |
| 24 | 2024-03-22 Fri | t_116 - t_120 |
| 25 | 2024-03-23 Sat | t_121 - t_125 |
| 26 | 2024-03-24 Sun | t_126 - t_130 |
| 27 | 2024-03-25 Mon | t_131 - t_135 |
| 28 | 2024-03-26 Tue | t_136 - t_140 |
| 29 | 2024-03-27 Wed | t_141 - t_145 |
| 30 | 2024-03-28 Thu | t_146 - t_150 |
| 31 | 2024-03-29 Fri | t_151 - t_155 |
| 32 | 2024-03-30 Sat | t_156 - t_160 |
| 33 | 2024-03-31 Sun | t_161 - t_165 |
| 34 | 2024-04-01 Mon | t_166 - t_170 |
| 35 | 2024-04-02 Tue | t_171 - t_175 |
| 36 | 2024-04-03 Wed | t_176 - t_180 |
| 37 | 2024-04-04 Thu | t_181 - t_185 |
| 38 | 2024-04-05 Fri | t_186 - t_190 |
| 39 | 2024-04-06 Sat | t_191 - t_195 |
| 40 | 2024-04-07 Sun | t_196 - t_200 |
| 41 | 2024-04-08 Mon | t_201 - t_205 |
| 42 | 2024-04-09 Tue | t_206 - t_210 |
| 43 | 2024-04-10 Wed | t_211 - t_215 |
| 44 | 2024-04-11 Thu | t_216 - t_220 |
| 45 | 2024-04-12 Fri | t_221 - t_225 |
| 46 | 2024-04-13 Sat | t_226 - t_230 |
| 47 | 2024-04-14 Sun | t_231 - t_235 |
| 48 | 2024-04-15 Mon | t_236 - t_240 |
| 49 | 2024-04-16 Tue | t_241 - t_245 |
| 50 | 2024-04-17 Wed | t_246 - t_250 |
| 51 | 2024-04-18 Thu | t_251 - t_255 |
| 52 | 2024-04-19 Fri | t_256 - t_260 |
| 53 | 2024-04-20 Sat | t_261 - t_265 |
| 54 | 2024-04-21 Sun | t_266 - t_270 |
| 55 | 2024-04-22 Mon | t_271 - t_275 |
| 56 | 2024-04-23 Tue | t_276 - t_280 |
| 57 | 2024-04-24 Wed | t_281 - t_285 |
| 58 | 2024-04-25 Thu | t_286 - t_290 |
| 59 | 2024-04-26 Fri | t_291 - t_295 |
| 60 | 2024-04-27 Sat | t_296 - t_300 |
| 61 | 2024-04-28 Sun | t_301 - t_305 |
| 62 | 2024-04-29 Mon | t_306 - t_310 |
| 63 | 2024-04-30 Tue | t_311 - t_315 |
| 64 | 2024-05-01 Wed | t_316 - t_320 |
| 65 | 2024-05-02 Thu | t_321 - t_325 |
| 66 | 2024-05-03 Fri | t_326 - t_330 |
| 67 | 2024-05-04 Sat | t_331 - t_335 |
| 68 | 2024-05-05 Sun | t_336 - t_340 |
| 69 | 2024-05-06 Mon | t_341 - t_345 |
| 70 | 2024-05-07 Tue | t_346 - t_350 |
| 71 | 2024-05-08 Wed | t_351 - t_355 |
| 72 | 2024-05-09 Thu | t_356 - t_360 |
| 73 | 2024-05-10 Fri | t_361 - t_365 |
| 74 | 2024-05-11 Sat | t_366 - t_370 |
| 75 | 2024-05-12 Sun | t_371 - t_375 |
| 76 | 2024-05-13 Mon | t_376 - t_380 |
| 77 | 2024-05-14 Tue | t_381 - t_385 |
| 78 | 2024-05-15 Wed | t_386 - t_390 |
| 79 | 2024-05-16 Thu | t_391 - t_395 |
| 80 | 2024-05-17 Fri | t_396 - t_400 |
| 81 | 2024-05-18 Sat | t_401 - t_405 |
| 82 | 2024-05-19 Sun | t_406 - t_410 |
| 83 | 2024-05-20 Mon | t_411 - t_415 |
| 84 | 2024-05-21 Tue | t_416 - t_420 |
| 85 | 2024-05-22 Wed | t_421 - t_425 |
| 86 | 2024-05-23 Thu | t_426 - t_430 |
| 87 | 2024-05-24 Fri | t_431 - t_435 |
| 88 | 2024-05-25 Sat | t_436 - t_440 |
| 89 | 2024-05-26 Sun | t_441 - t_445 |
| 90 | 2024-05-27 Mon | t_446 - t_450 |
| 91 | 2024-05-28 Tue | t_451 - t_455 |
| 92 | 2024-05-29 Wed | t_456 - t_460 |
| 93 | 2024-05-30 Thu | t_461 - t_465 |
| 94 | 2024-05-31 Fri | t_466 - t_470 |
| 95 | 2024-06-01 Sat | t_471 - t_475 |
| 96 | 2024-06-02 Sun | t_476 - t_480 |
| 97 | 2024-06-03 Mon | t_481 - t_485 |
| 98 | 2024-06-04 Tue | t_486 - t_490 |
| 99 | 2024-06-05 Wed | t_491 - t_495 |
| 100 | 2024-06-06 Thu | t_496 - t_500 |

## How the walk was checked (so the check can fail)

- `math_torture_work/minute_array_check.py` re-derives the chain with a structurally different
  method (one byte per minute of the window, minutes counted one by one) and compares with the
  walker: **0 mismatches in 500 tasks**; the five-a-day pattern holds for **all 500**; every one
  of the 100 days books exactly 365 minutes of its 506-minute capacity.
- The walker's *rules* were checked against the reference scheduler (an independent implementation) on
  three 5-minute-grid analogues of this chain (the reference scheduler cannot take this file, see below):
  shift 08:15-12:00, 13:05-17:45 with effort/gap 75/30, 95/35 and 140/55 min, 500 chained tasks
  each. The last two are deliberately not periodic (tasks split across lunch and across the
  night at varying points). **0 mismatches in 1500 rows** (`math_torture_work/tj_crosscheck.py`).
  This is a known-positive test of the same rules W1-W5; it does not test the real numbers.

## the reference scheduler cross-check on the real file

the reference scheduler refuses the file:
`Error: Timing resolution must be one of 5, 10, 15, 20, 30, 60 min.` With the resolution set to
5 min it refuses the 08:13 start (`The date must be aligned to the timing resolution`), and the
file's `workinghours prime_shift` (a shift referenced from `workinghours`) is ScriptPlan syntax
(the reference scheduler uses `shifts`). There is therefore no the reference scheduler result for the real file, and no disagreement to
record. The analogue runs above are the only the reference scheduler evidence.

## AMBIGUOUS points

None that change a date. The only reading choice, `+4m` as 4 x 30.4167 d versus four calendar
months, moves the project end between 2024-06-28-00:00 and 2024-06-28-16:00:11, both far after
the last end (2024-06-06-17:22).
