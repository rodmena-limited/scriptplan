# Projects scheduled in parallel threads share one error flag and count

**Ticket**: issuedb #28  
**Status**: open  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 28` whenever the spec or the chosen
alternative changes.

---

Found while closing #16 (no known gaps). Present in 0.10.0, 0.10.1 and the 0.10.2 tree.

EVIDENCE (scratchpad conc/race.py, Python API): one thread repeatedly schedules examples/showcase/simple.tjp while another schedules a 61-task project whose last task misses its stated end. Of 40 runs of the failing project, 1 raised TjRuntimeError out of Project.schedule() instead of returning False with the error recorded. Cause: MessageHandlerInstance is a process-wide singleton. collecting() saves and restores one process-wide flag, so a thread that leaves collecting() switches collection off for a thread still inside it. Project.schedule() also decides that post-checks failed by comparing the process-wide error count before and after, so another thread's error can fail a valid project, and messages from all threads land in one list.

EARS SPEC:
- R1 (state-driven) While several threads schedule projects through the Python API, each Project.schedule() shall return the same result, record the same messages and book the same dates as when that project is scheduled alone.
- R2 (unwanted) If one thread leaves collecting() while another thread is inside it, then the other thread's errors shall still be recorded, not raised.
- R3 (unwanted) If another thread records an error, then handler.errors and handler.messages read in this thread shall not change.
- R4 (ubiquitous) Single-threaded use (the CLI, the tests, the probes) shall behave exactly as before: same messages, same exit codes, golden snapshots unchanged.
- R5 (ubiquitous) The stress check shall run at least 40 overlapping failing schedules and at least 20 valid ones with zero mismatches, and shall fail on the 0.10.1 handler.

SYNTHESIS (localised): domain = per-thread diagnostic context (the pattern of decimal.localcontext / logging's thread-local state). Alternatives: threading.local for collect flag, error count and message list [CHOSEN: isolates threads, keeps the singleton and every same-thread caller unchanged] vs contextvars.ContextVar [REJECTED: on Python 3.14 free-threaded builds new threads inherit a copy of the context that would point at the same mutable state, so isolation depends on the interpreter build] vs a lock around Project.schedule() [REJECTED: serialises all scheduling and still mixes messages for callers that parse in one thread and schedule in another] vs a message list per Project [REJECTED: the parser and model emit messages with no project reference, so it means threading a project through every call site].

---

DONE: utils/message_handler.py keeps collect flag, error count and message list in a threading.local (_RunState); output settings stay shared. tests/test_threads.py: (1) one thread leaves collecting() while another is inside it, events force the order: the second thread's error is recorded, errors == 1, not raised; (2) an error recorded in another thread leaves this thread's errors and messages unchanged, and this thread still raises when not collecting; (3) 5 projects (4 showcase + 1 failing on maxend) x 3 copies in 15 threads match the same projects scheduled alone in result, every task's dates and every message. All three fail on the 0.10.1 handler (raised=True; (1,1) != (0,0); 4 mismatched runs) and pass on the fix. Stress (scratchpad conc/race.py): 80 failing schedules overlapping 89 valid ones, 0 mismatches on 0.10.2; the same run on 0.10.1 from PyPI raised TjRuntimeError once.
