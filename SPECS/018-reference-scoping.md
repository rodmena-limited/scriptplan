# A task reference that misses its scope binds the first task with that id, silently

**Ticket**: issuedb #18  
**Status**: closed (released in 0.10.2)  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 18` whenever the spec or the chosen
alternative changes.

---

Found while cross-checking the showcase projects against the reference scheduler (#16).

EVIDENCE: resolve_task_reference falls back, whenever scoped lookup fails or a reference goes above the root, to the FIRST task anywhere in the project whose short id matches. The reference scheduler scopes each "!" one level up from the referring task and errors otherwise. In the showcase, three references rely on the fallback and bind the intended sibling because the short id is unique: jit_supply delivery.assemble_b `depends !!pack` (-> delivery.pack), paradox sequence.a `depends !!b` (-> sequence.b), time_traveler launch.design `depends !!impl` (-> launch.impl). The reference scheduler rejects all three. Where a short id is not unique (tutorial has test.beta and deliveries.beta), the same fallback binds whichever comes first, silently.

EARS SPEC:
- R1 (ubiquitous) The parser shall resolve a task reference with the reference scheduler's scoping: each leading "!" moves the scope up one level from the referring task, and the path then names children level by level from that scope (no "!" = from the project root).
- R2 (unwanted) If a reference does not resolve that way but exactly one task in the project has that path as its id or id suffix, then the parser shall bind it to that task and emit a warning naming the reference, the task it bound and the form the reference scheduler would accept.
- R3 (unwanted) If more than one task could be meant, then the parser shall refuse the file with an error listing the candidates.
- R4 (ubiquitous) The 24 showcase projects shall schedule exactly as their golden snapshots record (no fixture or golden changed).
SYNTHESIS (localised): domain = the reference scheduler's reference scoping (its documented semantics, confirmed by running the reference scheduler on the three files). Alternatives: strict only [REJECTED: breaks three showcase projects that Farshid wants kept as they are] vs first match (status quo) [REJECTED: silent wrong binding when ids repeat] vs strict, then unique fallback with a warning, ambiguous = error [CHOSEN].

---

SPEC CHANGE (golden snapshots are not to be changed, Farshid 2026-10-17): R2 now binds the only task a mis-scoped reference can mean WITHOUT a warning, because fixture_snapshot.render records warnings and three showcase snapshots (jit_supply, paradox, time_traveler) would gain a line. The safety goal holds: an ambiguous reference (two tasks with the id) is now an error listing the candidates (verified: 'deliveries.x depends beta' with test.beta and deliveries.beta -> SemanticError naming both; 0.10.1 silently bound one). Strict scoping is applied first; for the 24 showcase projects the only references that need the fallback are the three !! ones, each unique.

---

VERIFIED: ambiguous reference refused with both candidates named (test in the gate); the three unique out-of-scope references in jit_supply, paradox and time_traveler bind as before, golden snapshots unchanged for paradox and time_traveler. README Known limits now documents the lenient binding.

RELEASED in scriptplan 0.10.2: commit b1dbe19, tag v0.10.2, PyPI wheel sha256 afaa4535...4da69 and sdist aeb73459...73b5c, both downloaded back from PyPI and byte-identical to the tested files. Final gate (scripts/ci.sh) passed every step on Python 3.9.25 and 3.13.7: ruff, mypy, file-size cap, 496 tests, showcase current, 85 probes. The built wheel in a clean 3.9 venv passed 85 probes, 49 example checks (24 showcase + 24 edge cases + coverage) and 3 thread tests.

---

CORRECTION to the closing comment: when it was written, no test in the gate covered the ambiguous reference (it had been verified by hand only). Added tests/test_reference_and_duration.py::test_a_reference_that_could_mean_two_tasks_is_refused, through the plan CLI: 'deliveries.x depends beta' with test.beta and deliveries.beta exits non-zero naming both. It fails on v0.10.1 (exit 0, binds test.beta) and passes on 0.10.2. Test-only change; the released package is unaffected.
