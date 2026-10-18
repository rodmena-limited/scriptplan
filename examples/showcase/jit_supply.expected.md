# jit_supply.tjp: derivation

Helpers: `oracle_jpq/walk_jpq.py` (stdlib calendar walker, output in
`oracle_jpq/walk_jpq.output.txt`) and the the reference scheduler variants in a translated copy (not kept).

## Setting

- Project 2025-07-01 00:00 UTC, `+1m` = 30.4167 d, so the project ends 2025-07-31 10:00:02.88 UTC.
  That end never binds here.
- `scheduling alap` in the project block makes every task ALAP.
- Machine: Mon-Fri 08:00-16:00 UTC, 480 min a day. July 2025: Mon 14, Tue 15, Wed 16, Thu 17, Fri 18.
- Every date and shift edge is on the hour, so the slots are 1 h and nothing starts or ends mid-slot.
- All efficiencies are 1, so effort minutes equal machine minutes.

## How each bound is reached

| edge in the file | read as |
|---|---|
| `delivery { end 2025-07-18-16:00 }` | Container end as stated. It is passed down to ALAP children that have no end of their own. The README's worked example (this file) says "Anchors packaging to end at 16:00 on July 18", and the the reference scheduler manual says the same of a container `end`. |
| `assemble_b depends !!pack { onstart }` | `!!pack` resolves to `delivery.pack` (A2). `onstart` takes the README Known-limits reading (A1): "the dependent task must finish before the predecessor starts", so **assemble_b.end <= pack.start**. |
| `set_deps depends assemble_a, assemble_b` | set_deps comes after both of them. Backwards, **assemble_x.end <= set_deps.start**. |
| `set_deps precedes pack` | **set_deps.end <= pack.start**. pack is a successor of set_deps. |

The backward pass becomes ready in this order:
1. pack. It has no successor, so its bound is the inherited end.
2. set_deps. Its successor, pack, is scheduled.
3. assemble_b and assemble_a together. Their successor set_deps is scheduled (and pack too, for assemble_b).
4. The containers.

## Tasks

**delivery.pack** (effort 8h = 480 min, machine)
- Latest end = min(inherited 2025-07-18 16:00, project end 07-31 10:00:03) = **Fri 07-18 16:00**. That moment is inside machine time.
- Backward from Fri 16:00: Fri 08:00-16:00 gives 480 min, and 480 - 480 = 0 remain.
- start **2025-07-18 08:00**, end **2025-07-18 16:00**. The machine is busy Fri 18 08:00-16:00.

**connection_setup.set_deps** (milestone: no effort, duration or length; ALAP)
- It sits exactly at the moment it must end: its successor pack starts at **2025-07-18 08:00**. start = end = 07-18 08:00.
- Fri 08:00 is a working moment of the machine. SPECS/014 R4 says an ALAP milestone does not move back over non-working time in any case.

**delivery.assemble_b** (effort 16h = 960 min, machine)
- Latest end = min(inherited 07-18 16:00, set_deps.start 07-18 08:00, pack.start 07-18 08:00) = 07-18 08:00.
- That moment is the start of Friday's working time, so the latest working time before it ends Thu 07-17 16:00.
- Backward: Thu 17 08:00-16:00 gives 480 min, leaving 480. Wed 16 08:00-16:00 gives 480, leaving 0.
- start **2025-07-16 08:00**, end **2025-07-17 16:00**. The end is reported at the last second of work, not at the 08:00 bound.
- Why assemble_b before assemble_a: both become ready at the same moment, both at priority 500. They have the same effort on the same single resource, so the same criticalness. Declaration order then puts assemble_b (line 35) before assemble_a (line 41), so assemble_b is placed first and keeps the latest time.

**delivery.assemble_a** (effort 16h = 960 min, machine)
- Latest end = min(inherited 07-18 16:00, set_deps.start 07-18 08:00) = 07-18 08:00.
- The machine is busy Wed 16 to Fri 18 (assemble_b, then pack).
- Backward: Tue 15 08:00-16:00 gives 480, leaving 480. Mon 14 08:00-16:00 gives 480, leaving 0.
- start **2025-07-14 08:00**, end **2025-07-15 16:00**.

**delivery** (container)
- start = earliest child start = assemble_a, 2025-07-14 08:00.
- end = the stated 2025-07-18 16:00, which is also the latest child end (pack).

**connection_setup** (container)
- start = end = set_deps = 2025-07-18 08:00.

## Checks

- assemble_a.end (07-15 16:00) <= set_deps (07-18 08:00).
- assemble_b.end (07-17 16:00) <= set_deps.
- assemble_b.end <= pack.start.
- set_deps = pack.start.
- The machine is never booked twice: Mon-Tue a, Wed-Thu b, Fri pack.
- Everything falls inside 07-01 .. 07-31.

The README states pack 07-18 08:00-16:00, assemble_a 07-14 08:00 to 07-15 16:00, and assemble_b 07-16 08:00 to 07-17 16:00. I derived these independently above, and they are the same.

## AMBIGUOUS

**A1. `onstart`.**
- Chosen: the README reading, assemble_b.end <= pack.start.
- Alternative: the brief's ASAP line ("or start, for { onstart }"), which is the reference scheduler's start-to-start, assemble_b.start >= pack.start.
- Together with set_deps, the alternative is a cycle: pack.start <= assemble_b.start < assemble_b.end <= set_deps <= pack.start. That cannot hold with 960 min of effort.
- Under the alternative, delivery.pack, delivery.assemble_b and connection_setup.set_deps (and through them assemble_a and the containers) are **UNSCHEDULABLE**, or the file is rejected as a loop. SPECS/001 notes that the loop check follows finish-to-start edges only, so it may not name this cycle.
- the reference scheduler shows the cycle: on the onstart variant it crashes with `stack level too deep` in `calcPathCriticalness`.
- Under the chosen reading the onstart edge is redundant, because set_deps already forces assemble_b before pack. Any reading that does not create the loop, including ignoring the edge, gives the same dates.

**A2. Reference `!!pack`.**
- From `delivery.assemble_b`, the reference scheduler resolves `!!` to the root, where there is no `pack`. the reference scheduler rejects it: "Task delivery.assemble_b has unknown depends pack".
- Chosen: it resolves to `delivery.pack`. That is the only pack. The README's own worked example writes it this way, and SPECS/001 records that every example project renders with exit 0.
- Alternative: an unresolved-reference parse error, with nothing scheduled.

**A3 (weak). Placement order of assemble_a and assemble_b.**
- The brief does not define criticalness. I chose declaration order.
- If the engine placed assemble_a first, the two rows swap: assemble_a 07-16 08:00 to 07-17 16:00, assemble_b 07-14 08:00 to 07-15 16:00.
- No plausible criticalness ranks assemble_a above assemble_b: equal effort, same resource, and assemble_b has the extra edge to pack.

**Decided, not ambiguous: end inheritance.**
- Without inheritance, pack's bound would be the project end. pack would run 07-30 10:00:03 to 07-31 10:00:03 (Wed 10:00-16:00 is 360 min, plus Thu 08:00-10:00 is 120 min), and delivery's stated end would be broken.
- The README example decides this.

## the reference scheduler cross-check

**Original file.** Rejected: `scheduling` is not allowed in the project block, and `workinghours factory_hours` is not the reference scheduler syntax.

**a translated copy (not kept).** `scheduling alap` is set on each task, the hours are expanded, `!!pack` becomes `!pack`, and `onstart` is kept.
- the reference scheduler crashes (stack level too deep, path criticalness). This is the A1 loop. Expected.

**a translated copy (not kept).** onstart is rewritten as `assemble_b precedes !pack`, and set_deps keeps its `depends`.
- the reference scheduler: "Task delivery.assemble_a has not been marked as scheduled". It does place set_deps at 2025-07-18-08:00.
- Reason: the reference scheduler does not derive an ALAP task's end from a successor that names it in `depends`. ALAP chains in the reference scheduler must be written with `precedes`. This is a the reference scheduler limitation, not a disagreement about dates.

**a translated copy (not kept).** Every edge is written as `precedes`.
- the reference scheduler gives exactly the table above for all six rows, including both containers.


---

# jit_supply: set_deps

The golden snapshot (0.10.0 and 0.10.1) places the alap milestone connection_setup.set_deps at
2025-07-17 16:00. Two independent sources place it at 2025-07-18 08:00:

- the hand derivation: set_deps is an alap milestone that precedes delivery.pack, which starts
  2025-07-18 08:00, so as late as possible is exactly 08:00 on the 18th;
- the hour-level reference scheduler, run on the same dependency graph written with
  `precedes` (the form it accepts), gives connection_setup and set_deps 2025-07-18-08:00. All
  times in this project are whole hours, so its answer is exact here.

The 16:00 in the snapshot came from 0.10.1's placement of alap milestones one slot before the
moment they must end and then back to the start of the last working slot (issuedb #14): the
same mechanism puts a milestone before a task starting at 16:00 at 15:00.
