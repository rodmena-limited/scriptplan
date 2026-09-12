# WS6 Reports honour their definitions

**Ticket**: issuedb #8  
**Status**: open  
**Priority**: medium

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 8` whenever the spec or the chosen
alternative changes.

---

EARS SPEC:
- Where a report declares sorttasks or sortresources, ScriptPlan shall order rows accordingly.
- Where a report declares hidetask or hideresource, ScriptPlan shall evaluate the expression and hide only matching rows.
- Where a report declares column options (title, width), ScriptPlan shall apply them.
- A duration column shall report elapsed scheduled time and a chart column shall render, or the parser shall reject them.
- Where a report declares several scenarios, ScriptPlan shall render each.
- If a report declares an unimplemented format, then the parser shall reject it naming the format.

TECHNICAL PROBLEMS:
1. Attribute key mismatch between parser and reader (sort vs sortTasks).
2. Logical expression evaluation for row filters (currently bool(non-empty string) == hide everything).
3. Column specification type dispatch (dict vs object vs string).

SOLUTION DOMAINS:
- Filter expressions -> TaskJuggler logical expression syntax over flags and predicates; small recursive-descent evaluator.
- Column model -> one normalised ColumnSpec dataclass produced by the parser.

ALTERNATIVES:
- Filters: implement flags/isleaf/~/&/| evaluator [CHOSEN] vs reject hidetask at parse time [REJECTED: fixtures and the tutorial use it] vs keep ignoring it [REJECTED: currently hides every row, which is worse than ignoring].
- Unimplemented formats: reject at parse time [CHOSEN: today they silently write nothing and the CLI blames scheduling] vs implement ical/tjp/niku [REJECTED: out of scope for readiness].

---

## Outcome

**Status**: closed.

Sort criteria are plumbed to the keys the reports read and applied; PropertyList sorting is one stable pass per criterion, so descending works and a missing value does not raise. report/logical_expression.py evaluates hidetask/hideresource/rolluptask/rollupresource, including predicates with arguments and comparisons against scenario-qualified attributes. The duration column reports elapsed time. Unimplemented formats are rejected at parse time.

Probes: probe_reports 5/5.
