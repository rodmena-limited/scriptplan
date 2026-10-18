# A stated start is ignored under ALAP (trace #10)

**Ticket**: issuedb #24  
**Status**: open  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 24` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d over AgentBus (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M563GAHBQ5BMGWRYVCEQHCCB, platform_attested), reproduced here on 0.10.1 from PyPI with its TJP d10. EVIDENCE: plan alap, g end Fri 17:30, a start Fri 08:30 -> a Thu 13:00-17:00, before its stated start; exit 0. The reference scheduler honours the start. EARS: R1 (unwanted) If a backward task's latest placement starts before the start the file states for it, then ScriptPlan shall report an error naming the task, the stated start and where the work would have to start, and exit non-zero. SYNTHESIS (localised): the after-scheduling checks; backward placement is already as late as possible, so an earlier start means the stated start cannot be met.

---

DONE: postcheck raises start_violated when a task starts before its stated start. d10 exits 2: "Task 'g.a' may not start before 2026-11-06 08:30:00 ... would have to start at 2026-11-05 13:00:00". Feasible variant (start Wed 08:30) schedules a Thu 13:00-17:00.
