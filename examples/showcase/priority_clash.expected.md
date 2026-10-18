# priority_clash.tjp: derivation

## Setting

- Project 2025-08-01 00:00 UTC, which is a Friday. `+1w` means it ends 2025-08-08 00:00 UTC. All tasks are ASAP.
- consultant: Mon-Fri 09:00-13:00 UTC, 240 min a day.
- Every edge is on the hour, so the slots are 1 h. Efficiency is 1.
- Both tasks: effort 4h = 240 min, `allocate consultant`, `start 2025-08-01-09:00`. That declared start is inside working time.
- Both are ready at the same moment. Priority decides: high_prio (1000) is placed before low_prio (100), and keeps its time.

## Tasks

**conflict.high_prio**
- Start = latest of project start (08-01 00:00) and declared start (08-01 09:00) = **Fri 08-01 09:00**.
- The consultant is free. Fri 09:00-13:00 gives 240 min, leaving 0.
- end **2025-08-01 13:00**. The consultant is busy Fri 09:00-13:00.

**conflict.low_prio**
- Earliest start is Fri 08-01 09:00.
- The consultant is busy until 13:00, and Friday has no working time after 13:00. Sat 08-02 and Sun 08-03 are not working days.
- First free working time: Mon 08-04 09:00. 09:00-13:00 gives 240 min, leaving 0.
- start **2025-08-04 09:00**, end **2025-08-04 13:00**. This is inside the project, which ends 08-08.

**conflict** (container)
- start = earliest child start = 2025-08-01 09:00.
- end = latest child end = 2025-08-04 13:00.

## AMBIGUOUS

**Q1. low_prio's reported start.**
- Chosen: the first moment of work, 2025-08-04 09:00. SPECS/011 R3 and the 0.10.1 changelog (airport_stress_test `t_install` starts "when the electrician finishes") report the start where the work begins. the reference scheduler does the same.
- Alternative: the stated `start 2025-08-01-09:00` kept as the task's start, with the work on 08-04. The end and the container are the same either way.

## the reference scheduler cross-check

Original file, unchanged: conflict 08-01 09:00 to 08-04 13:00, high_prio 08-01 09:00 to 13:00, low_prio 08-04 09:00 to 13:00. **Identical.** The file sets its own working hours, so the reference scheduler's default day does not apply.
