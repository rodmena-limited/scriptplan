# quota.tjp: derivation

## Setting

- Project 2025-07-01 00:00 UTC, a Tuesday. `+1w` means it ends 2025-07-08 00:00. All tasks are ASAP.
- Every resource works Mon-Sun 09:00-17:00 UTC, 480 min a day. The slots are 1 h. Efficiency is 1.
- api_gateway has `limits { dailymax 6h }`, which is 360 min per UTC day.
- slot_1, slot_2 and slot_3 set no limits of their own. Following the brief ("Resources in a container inherit its attributes (efficiency, rate, limits) unless they set their own"), **each child gets its own dailymax of 360 min**, counted over its own bookings.

## Tasks

Each task is 180 min of effort on its own child resource. No child resource is used by more than one task, so nothing competes.

**batch.job_a** (slot_1)
- start = declared 2025-07-01 09:00, a working moment.
- 09:00-12:00 gives 180 min. slot_1's total for 07-01 is 180, which is at most 360.
- end **2025-07-01 12:00**.

**batch.job_b** (slot_2)
- The same: **2025-07-01 09:00 to 12:00**. slot_2's total for 07-01 is 180.

**batch.job_c** (slot_3)
- No declared start, so the earliest start is the project start, 07-01 00:00. The first working moment after that is 09:00.
- 09:00-12:00 gives 180 min. slot_3's total for 07-01 is 180.
- **2025-07-01 09:00 to 12:00**.

**batch** (container)
- **2025-07-01 09:00 to 12:00**.

## AMBIGUOUS

**Q1. job_c (and the batch end).**
- The file's own comment says the parent's dailymax is a quota *shared* by the three children ("3 tasks using 3 child resources, but parent has dailymax 6h").
- Shared-pool reading, with tasks placed whole in priority-then-declaration order:
  - job_a 180 + job_b 180 = 360 = the cap for 07-01, so job_c cannot work on 07-01.
  - job_c = **2025-07-02 09:00 to 12:00**, and batch ends 2025-07-02 12:00. job_a and job_b are unchanged.
- Shared pool, with the three tasks advanced slot by slot together:
  - Each gets 120 min on 07-01 (09:00-11:00, 3 x 120 = 360), then 60 min on 07-02 at 09:00-10:00.
  - All three run 2025-07-01 09:00 to 2025-07-02 10:00.
- Chosen: per-child copies, because that is the brief's stated semantics, and the reference scheduler agrees. The comment's intent is the alternative.

## the reference scheduler cross-check

**Original file.** Rejected: `workinghours standard` (a shift id) is not the reference scheduler syntax.

**a translated copy (not kept).** The shift is expanded into `workinghours mon - sun 09:00 - 17:00` on every resource.
- the reference scheduler: batch, job_a, job_b and job_c all run 2025-07-01 09:00 to 12:00. **Identical** to the chosen reading.
- the reference scheduler does not pool a parent's `limits` over its children.


---

# quota: adjudication

The independent derivation gave each child resource its own copy of the parent's dailymax
6h, so job_c ran Jul 1 09:00-12:00 alongside job_a and job_b. The engine treats the parent's
cap as one pool for the three connections and moves job_c to Jul 2 09:00-12:00.

Verdict: the engine's answer is the one this project specifies. Its header says "parent
dailymax applies to child resources" and its hand-derived test (TestIssue62SharedQuotaProtocol)
says "job_c MUST wait for Jul 2 (quota exceeded)". The brief given to the oracle wrongly said
children inherit their own copy of a parent's limit. The oracle listed this answer as its
alternative ("tasks placed one at a time: job_c 07-02 09:00-12:00, batch ends 07-02 12:00").
