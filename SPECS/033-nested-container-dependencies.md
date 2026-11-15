# A task that depends on a container nested two or more levels deep never schedules (trace N5)

**Ticket**: issuedb #33  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 33` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M57WDGZFYGTYDT1D40R4TCNH, platform_attested); reproduced on 0.10.2 from PyPI and on the 0.10.3 build.

EVIDENCE: p { m { w effort 60min } }, s { depends p; effort 60min } -> 'Task s could not be scheduled: no ready predecessor or successor', exit 2. depends p.m or p.m.w works (s 09:30-10:30). The reference scheduler gives s 09:30-10:30. Cause: project_tree.update_container_task_status makes one pass over the tasks in declaration order, so p is checked before m. When w is placed, m is marked scheduled but p is not, and with no other task to place no further pass runs, so s waits for ever.

EARS SPEC:
- R1 (event) When the last task inside a container is placed, the scheduler shall mark that container and every enclosing container whose children are all placed as scheduled, with their dates, before it looks for the next ready task, however deep the nesting.
- R2 (ubiquitous) A task that depends on a container at any depth shall start when the container ends (trace case: s 09:30-10:30), forward and backward.
- R3 (ubiquitous) Showcase snapshots and example answers shall be unchanged.
- R4 (ubiquitous) A test through the plan CLI shall cover two and three levels of nesting and shall fail on 0.10.2.

SYNTHESIS (localised): domain = bottom-up aggregation over a tree. Alternatives: repeat the pass until nothing changes [CHOSEN: correct for any declaration order and depth, at most depth+1 passes] vs visit containers deepest first [REJECTED: same result, but the order has to be computed and kept in step with the tree] vs mark ancestors from each placed leaf [REJECTED: needs every caller to pass the leaf].

---

DONE: project_tree.update_container_task_status repeats its pass until no container changes (_mark_finished_containers returns whether it marked one). Verified against the reference scheduler: trace's dep_p.tjp s 09:30-10:30; three levels deep; with gapduration 30min s 10:00-11:00; container q after nested p; a sibling branch inside p depending on !!m - every row identical. Backward (by hand): p.m.w 15:30-16:30 before s 16:30-17:30, which also needs #32's container match. Regression since 0.10.0: 0.9.2 schedules dep_p.tjp correctly, 0.10.0-0.10.2 report s unschedulable. tests/test_container_dependencies.py now 14 tests, all 14 fail on v0.10.2.
