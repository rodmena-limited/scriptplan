# A shared task's finish depends on the slot size (the last slot used one person)

**Ticket**: issuedb #27  
**Status**: open  
**Priority**: high  
**Release**: 0.10.2

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 27` whenever the spec or the chosen
alternative changes.

---

Found while deriving tutorial.tjp independently for #16. book_resources stopped adding resources in a slot once the first one's full-slot gain covered the remaining effort, so the last slot was worked by one person where several were free. tutorial: spec ended 15:00 at timingresolution 60min, 14:30 at 30 and 15, 14:20 at 5 and 1; the project end moved 12:48 / 12:00 / 11:45 / 11:44 with the slot size alone. Same in every release since 0.10.0 (effort sharing). EARS: R1 (ubiquitous) A plan's dates shall not depend on timingresolution where every date in it is a whole multiple of every resolution tried. R2 (event) When several allocated resources are free in a task's final slot, they shall all work it and the task shall end when their combined work covers the remainder; a resource not needed shall get its time back and a persistent allocation shall not stay locked to it. FIX: book every chosen resource; finish_offset settles; restore_unused_locks undoes a persistent lock on a resource released entirely. Farshid approved fixing it (2026-10-18, 'if there is a need for fix, do it'), which changes the tutorial golden.
