# A child of a container that depends on another with a gap or onstart never schedules (trace N4)

**Ticket**: issuedb #32  
**Status**: in progress  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 32` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M57VQS300KK9FJ29B4T2DNCT, platform_attested); reproduced here on 0.10.1, 0.10.2 and the unpublished 0.10.3 build.

EVIDENCE: p { p1 effort 60min }, q { depends p { gapduration 30min }; c effort 60min } -> 'Task q.c could not be scheduled: no ready predecessor or successor', exit 2. Without the gap, q.c runs 09:30-10:30; with q a leaf, q runs 10:00-11:00. The reference scheduler gives q.c 10:00-11:00. Cause: attributes.deep_clone, used when a child inherits an attribute, keeps object identity only for a list whose first item is a task. A dependency with options is stored as a dict holding the task, so inheriting it deep-copied the task object: q.c waited on a copy of p that is never scheduled. The same applies to any option that stores the dependency as a dict (gapduration, gaplength, maxgapduration, onstart, onend).

EARS SPEC:
- R1 (event) When a container's dependency carries options, its children shall inherit a dependency on the same task, and shall be placed after it with the gap the options ask for (trace case: q.c 10:00-11:00).
- R2 (ubiquitous) Copying an attribute value for inheritance shall never copy a task, resource, account or shift; any it contains shall be the same object.
- R3 (ubiquitous) The 24 showcase projects and 24 edge cases shall schedule as their snapshots and answers record.
- R4 (ubiquitous) A test through the plan CLI shall cover gapduration, gaplength and onstart on a container dependency, and shall fail on 0.10.2.

SYNTHESIS (localised): domain = Python's copy protocol (__deepcopy__) for entity objects that are referenced, never valued. Alternatives: PropertyTreeNode.__deepcopy__ returns self [CHOSEN: holds at any depth for every attribute, one place] vs teach deep_clone to recurse into dicts [REJECTED: still copies nodes held in any other structure, such as tuples or objects] vs store the dependency's task by id and resolve late [REJECTED: changes the model every scheduler module reads].

---

DONE: (1) PropertyTreeNode.__deepcopy__ returns self, so inheriting a dependency dict keeps the task it names. (2) task_dependencies.names_this_task(): successors(), bounding_successors() and latest_end_for() match a dependency on this task or any container it belongs to, so a backward task inside p is bounded by q.c when q depends p (found while fixing N4; 0.9.2-0.10.1 placed p.p1 after q.c silently, 0.10.2 refused). (3) postcheck reports a broken dependency once per predecessor and names the declared start when it differs from the actual start. Verified: trace's file q.c 10:00-11:00; gaplength 11:00-12:00, onstart 08:30-09:30, nested and two-children variants identical to the reference scheduler; backward p.p1 15:00-16:00 with the gap and 15:30-16:30 without (by hand). Max gap on a container behaves like on a leaf (checked after scheduling, as documented). tests/test_container_dependencies.py 8/8, all 8 fail on v0.10.2. Same failure on 0.10.0; 0.9.2 left q.c undated silently.
