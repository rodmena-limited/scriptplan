# Failure messages: doubled 'Error:' prefix, and no-resource effort blamed on the window

**Ticket**: issuedb #29  
**Status**: open  
**Priority**: medium  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 29` whenever the spec or the chosen
alternative changes.

---

Found while re-running trace's TJPs for #16. Both present in 0.10.1.

EVIDENCE: (1) plan report --csv on trace d03 prints 'Error: Error: Task g.b must end by ...'. plan.py prefixes 'Error: ' to the captured engine output, which already carries a coloured 'Error:' tag. (2) 'task a { effort 2h }' with no allocate exits 2 with 'Task a could not be scheduled: ran outside the project window (...); it needs more time or more resource availability than the project allows'. No resource is allocated, so the window is not the cause.

EARS SPEC:
- R1 (unwanted) If the engine's output already names its severity (Error, Warning, Fatal), then plan report shall print it without adding another 'Error:' prefix.
- R2 (unwanted) If a task with effort has no resource allocated, directly or inherited, then the error shall say it has effort but no resource to do it, and shall not mention the project window.
- R3 (ubiquitous) A task with an allocated resource that does not fit shall still be reported as running outside the project window.

SYNTHESIS (localised): domain = the CLI's error presentation (cli/plan.py) and the stall messages (scheduler/stalls.py). Alternatives for R1: strip ANSI and check for a severity word before prefixing [CHOSEN] vs stop prefixing entirely [REJECTED: plan's own errors (file not found, output exists) carry no tag and need one]. For R2: name the cause in stalls._runaway_detail [CHOSEN: it only changes the text of a failure already reported] vs refuse effort without allocation before scheduling [REJECTED: a booking-only task or one allocated through a container must still be judged by the scheduler].

---

DONE: cli/plan.py _as_error() strips ANSI codes and adds 'Error: ' only when no severity word is present; stalls._runaway_detail names a missing resource first. tests/test_failure_messages.py: test_effort_with_no_resource_says_so fails with both fixes reverted (doubled prefix and window message) and passes with them; test_effort_that_does_not_fit_names_the_window (allocation inherited from the parent) passes in both, so the new message is not over-broad.
