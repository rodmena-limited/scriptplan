# Probe: every scheduling directive the grammar accepts changes a schedule or is refused

**Ticket**: issuedb #38  
**Status**: in progress  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 38` whenever the spec or the chosen
alternative changes.

---

Farshid, 2026-11-15: 'how our extensive tests missed this?' No fixture set a project workinghours, so a parsed-and-ignored line could not fail anything.

EARS SPEC:
- R1 (ubiquitous) The audit harness shall hold, for each directive the grammar accepts that bears on scheduling, a pair of projects that differ only in that directive and shall assert that their schedules differ.
- R2 (unwanted) If a directive is accepted and no pair can show an effect, then it shall be listed in the README as recorded-only, or refused when parsed.
- R3 (quality) The probe shall fail on 0.10.2 for project workinghours and for global leaves.

---

VERIFICATION (2026-11-15): audit/evaluations/probe_directive_effect.py classifies 81 grammar directives: 52 with a pair, 29 listed as having no bearing on dates with the reason. 54 probes pass on the fixed code. Against scriptplan 0.10.2 from PyPI it fails 9: workinghours, leaves_global, shift_leaves, resource (group allocation), alloc_limits, and the four lower limits.
