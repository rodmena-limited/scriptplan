# WS0 Honesty and safety: fail closed

**Ticket**: issuedb #2  
**Status**: open  
**Priority**: high

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 2` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- If any task cannot be scheduled, then Project.schedule() shall return False and record an error naming the task and reason.
- If the .tjp defines a dependency cycle, then ScriptPlan shall raise CircularDependencyError naming the cycle before scheduling starts.
- ScriptPlan shall never call sys.exit() or print() from library code.
- When a scheduling failure occurs, then 'plan report' and 'scriptplan' shall exit non-zero and print the reasons on stderr.
- Where the input file defines its own reports, 'plan report' shall render those reports rather than substituting its own.
- report_id shall be the SHA-256 of the canonical JSON of the rendered result, identical across two runs of the same input and different when the schedule differs.
- If a task/resource attribute in the grammar is not applied to the model, then the parser shall raise an error naming the attribute (no silent discard).
- If a depends/precedes/allocate/shift reference does not resolve, then the parser shall raise an error naming the reference.
- If two properties share an id in the same scope, then the parser shall raise a duplicate-definition error.
- Setting a list attribute shall replace its value; accumulation shall use an explicit append.

TECHNICAL PROBLEMS:
1. Result propagation through four layers that each discard it (project.py:338, cli/main.py:510, cli/plan.py:335).
2. Structural validation of untrusted input at the edge (parser generic sink tjp_parser.py:1583).
3. Library-vs-application separation of process control (message_handler.py:418-424 sys.exit).

SOLUTION DOMAINS:
- Collect-then-fail error model -> core/exceptions.py (classes already exist unused: CircularDependencyError, ResourceNotFoundError, DuplicateDefinitionError).
- Cycle detection -> DFS colouring over the dependency graph (standard).
- Canonical JSON hashing -> json.dumps(sort_keys=True, separators) + hashlib (stdlib).

ALTERNATIVES:
- Errors: collect-then-fail with a per-project collector [CHOSEN: TaskJuggler reports all errors in one run] vs raise on first error [REJECTED: one typo hides the rest].
- Parser strictness: raise on unhandled attribute [CHOSEN] vs warn and continue [REJECTED: this is exactly the silent-drop defect, and a warning nobody reads is the same bug].
- report_id: hash of canonical result JSON [CHOSEN] vs hash of input file [REJECTED: identical id for a correct and a broken schedule, and README calls it content-based].
