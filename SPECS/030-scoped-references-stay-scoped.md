# A !reference whose scope is a task binds a task elsewhere when it names no child (0.10.2 regression, trace N2)

**Ticket**: issuedb #30  
**Status**: in progress  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 30` whenever the spec or the chosen
alternative changes.

---

Reported by trace-thinkpad-83589d (thread 01M563GAHKNN9CHN418PR07YYQ, message 01M57TCBXTCAE58E7HQAF75R5C, platform_attested); reproduced here on 0.10.1 and on 0.10.2 from PyPI. Introduced in 0.10.2 by #18.

EVIDENCE: g.b 'depends !a' with no sibling a and one task h.a elsewhere. 0.10.1: SemanticError 'depends on !a, which is not a task in this project'. 0.10.2: binds h.a silently and schedules. The same for 'depends !x' with a root task x. The reference scheduler refuses both: 'Task g.b has unknown depends g.a'. Cause: #18's unique-id fallback runs whenever scoped lookup fails. 0.10.1 fell back to a project-wide id search only when there was no '!' or when the '!'s climbed to the top level of the project; a scope that is a task named its children exactly.

EARS SPEC:
- R1 (unwanted) If a reference's '!'s stop at a task and that task has no child with the referenced path, then the parser shall refuse the file naming the reference, as 0.10.1 did.
- R2 (ubiquitous) A reference with no '!', or whose '!'s reach the top level of the project, shall resolve as in 0.10.2: the path from the top level, else the only task with that id, else an error listing every candidate when there are several.
- R3 (ubiquitous) The 24 showcase projects shall schedule exactly as their golden snapshots record, including the three '!!' references in jit_supply, paradox and time_traveler.
- R4 (ubiquitous) A test through the plan CLI shall refuse both trace cases and shall fail on 0.10.2.

SYNTHESIS (localised): domain = the reference scoping that 0.10.1 implemented and the reference scheduler enforces. Alternatives: fall back only where 0.10.1 did [CHOSEN: refuses everything 0.10.1 refused, keeps the showcase references, keeps #18's ambiguity refusal] vs strict scoping everywhere [REJECTED: breaks three showcase projects whose snapshots are not to change] vs keep the fallback and warn [REJECTED: still binds a typo to an unrelated task, and warnings change golden snapshots].

---

DONE: parser/model_pieces.resolve_task_reference returns the scoped result, or None, whenever the '!'s stop at a task; the project-wide unique-id fallback runs only with no '!' or when the '!'s reach the top level, which is where 0.10.1 fell back. The unresolved depends/precedes error now says the reference 'names no task from where it is written' (0.10.1 and 0.10.2 said 'not a task in this project', which is false when the id exists elsewhere). Verified: both trace cases refused through the CLI; the !!pack top-level case still binds; ambiguous 'beta' still refused naming both; SHOWCASE.md regenerated with no schedule change. tests/test_scope_and_inherited_start.py: the two refusal tests fail on v0.10.2 and pass now.
