# WS5 Library hygiene and global state

**Ticket**: issuedb #7  
**Status**: open  
**Priority**: medium

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 7` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- ScriptPlan shall hold no scheduling or messaging state in module- or class-level variables shared between projects.
- Where an attribute-provenance mode is needed, ScriptPlan shall scope it to the project and restore it on exception.
- Sorting a property list by a string key descending shall reverse the order, and a list containing missing values shall sort without raising.
- ScriptPlan shall contain no unreachable modules.

TECHNICAL PROBLEMS:
1. Process-global mutable state in a library used by a long-running service (AttributeBase._mode, MessageHandlerInstance, TjTime._tz).
2. Dead and racy code (batch_processor, data_cache, logger) presenting as supported surface.

SOLUTION DOMAINS:
- Scoped state -> context manager on the project object.
- Sorting -> decorate-sort-undecorate with a type-uniform key.

ALTERNATIVES:
- Mode: per-project attribute with a context manager [CHOSEN] vs thread-local [REJECTED: two projects on one thread still collide] vs pass explicitly through every setter [REJECTED: touches every call site for the same guarantee].
- Dead code: delete batch_processor/data_cache/logger [CHOSEN: unreachable, racy, and data_cache never caches] vs fix in place [REJECTED: nothing calls them; fixing unreachable code is unverifiable].
