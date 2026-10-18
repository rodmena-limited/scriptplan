# A milestone treats a start inherited from its container as fixed (trace N3)

**Ticket**: issuedb #31  
**Status**: in progress  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 31` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M57TCBXTCAE58E7HQAF75R5C, platform_attested); reproduced here.

EVIDENCE: g { start Mon 09:00; a effort 8h; m milestone depends !a }. 0.10.1: m dated Mon 09:00, before a ends at 17:00, silently. 0.10.2: refused with dependency_violated. The reference scheduler places m at Mon 17:00. Cause: Project.scheduleScenario's milestone pre-pass fixes any milestone that has a start, including one inherited from a container, so it never reaches the placement that treats an inherited start as an earliest start (#19 did this for tasks with work only).

EARS SPEC:
- R1 (event) When a milestone has a start only by inheritance from a container, the scheduler shall place it at the later of that start and the end of its predecessors (plus their gaps), as it does for tasks with work.
- R2 (ubiquitous) A start or end stated on the milestone itself shall stay fixed, and a dependency that contradicts it shall stay an error.
- R3 (ubiquitous) The 24 showcase projects shall schedule exactly as their golden snapshots record.
- R4 (ubiquitous) A test through the plan CLI shall check trace's case and its own-start counterpart, and shall fail on 0.10.2.

SYNTHESIS (localised): domain = the own-versus-inherited start rule of #19 (task_placement.own_start). Alternatives: pre-fix only milestones whose start or end is their own [CHOSEN: one rule for every task, reuses own_start's 'provided' test] vs move a fixed milestone later when a dependency requires [REJECTED: overrides a date the file states on the milestone itself].

---

DONE: Project.scheduleScenario's milestone pre-pass leaves a forward milestone whose start is inherited (task_placement.own_start is None) to the main placement loop, which treats an inherited start as an earliest start. Backward milestones keep their handling. Verified through the CLI: trace's case gives g.m 2026-11-02 17:00, the same four rows as the reference scheduler; an inherited start later than the predecessor's end (Tue 12:00) holds the milestone there; a start stated on the milestone itself still refuses a contradicting dependency. The holds-until-predecessor test fails on v0.10.2 and passes now. project.py 487 lines.
