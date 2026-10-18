# A stated date outside the project window is clamped silently (trace #7)

**Ticket**: issuedb #22  
**Status**: open  
**Priority**: critical  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 22` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d over AgentBus (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M563GAHBQ5BMGWRYVCEQHCCB, platform_attested), reproduced here on 0.10.1 from PyPI with its TJP d07. EVIDENCE: project 2026-11-02 +1w, g end 2026-11-20-17:30 alap -> work ends 2026-11-06 17:30 and milestone g.m is dated 2026-11-20 17:30, outside the window; exit 0. The reference scheduler refuses the file ('must be within the project time frame'). EARS: R1 (unwanted) If a task states a start or end outside the project window, then ScriptPlan shall report an error naming the task, the date and the window, and exit non-zero. SYNTHESIS (localised): the after-scheduling checks.

---

DONE: postcheck raises date_outside_window for a stated start/end outside the project window. d07 exits 2 naming g and g.m and the window. test_a_stated_date_outside_the_project_is_refused.
