# WS8 Packaging, docs and file-size cap

**Ticket**: issuedb #10  
**Status**: open  
**Priority**: medium

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 10` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- No source file shall exceed 500 lines.
- The README shall carry no capability claim that has no probe or test.
- The package version shall have a single source of truth.
- The test suite shall not require optional plugins to start.

TECHNICAL PROBLEMS:
1. Nine source files over the 550-line hard cap.
2. Marketing claims used as certification evidence.

SOLUTION DOMAINS:
- Module decomposition along existing class boundaries with re-export shims to preserve import paths.
- House rules in the global CLAUDE.md (500 soft / 550 hard, no GitHub Actions).

ALTERNATIVES:
- Splitting: extract by class with a re-export shim [CHOSEN: import paths and the 383 tests keep working] vs move classes and update every import [REJECTED: needless churn in tests that are themselves being rewritten].
- Claims: rewrite README as verified behaviours listing only harness-backed items [CHOSEN] vs regenerate SHOWCASE from a fixed CLI [DEFERRED to after WS6: the document is only meaningful once reports honour their definitions].
