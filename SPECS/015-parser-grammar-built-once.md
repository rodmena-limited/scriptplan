# Every ProjectFileParser compiles the grammar again (about 0.7 s)

**Ticket**: issuedb #15  
**Status**: in-progress  
**Priority**: medium  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 15` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- R1 (ubiquitous) Constructing a ProjectFileParser after the first in a process shall take under 10 ms (median of 20), by reusing the compiled grammar; the first may still take the grammar build (about 0.7 s).
- R2 (unwanted) If parsers share the compiled grammar, then parsing shall still share no state: projects parsed by one parser or by several are independent, including after a parse that fails (tests/test_project_isolation.py and a new failing-then-good parse test).
- R3 (state) While 8 threads parse different files on the shared grammar, every result shall equal the sequential result.
SYNTHESIS (localised): domain = memoisation of an immutable compiled artefact. Concept = one process-wide compiled LALR parser built once under a lock. ALTERNATIVES: in-process memo [CHOSEN] vs lark cache=True [REJECTED: it unpickles a file from the shared temp directory, so a local user who plants one gets code execution in every scriptplan process] vs a generated standalone parser module [REJECTED: a large generated artefact to regenerate on every grammar change, for a cost the memo already removes].

---

DONE: _compiled_grammar() builds the LALR parser once per process under a lock. Measured: first ProjectFileParser() 353 ms, later median 0.001 ms (max 0.003) over 20; parse after a failing parse unaffected; 8 threads x 15 files identical to sequential.
