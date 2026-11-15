# precedes drops its gapduration, gaplength and maxgapduration, and onend, silently

**Ticket**: issuedb #34  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 34` whenever the spec or the chosen
alternative changes.

---

Found while probing the container shapes next to trace's N4/N5. Present in 0.10.1, 0.10.2 and the 0.10.3 build.

EVIDENCE: a { effort 60min; precedes b { gapduration 30min } }, b { effort 60min } on one resource -> b 09:30-10:30, starting the moment a ends; the 30 minutes are ignored, exit 0, nothing said. The same with p (container) precedes q { gapduration 30min }. Cause: parser _resolve_precedes appends the source task to the target's depends as a bare task, dropping every option. 'onend' (the source must end before the target ends) is dropped too, and the dependency model has no way to express it. The reference scheduler accepts precedes only on backward tasks, so it cannot be compared here.

EARS SPEC:
- R1 (ubiquitous) 'a precedes b { gapduration X }', '{ gaplength X }' and '{ maxgapduration X }' shall constrain b exactly as 'b depends a' with the same option does, in both scheduling directions.
- R2 (unwanted) If a precedes carries onend, then the parser shall refuse the file naming the task and the option, rather than drop it.
- R3 (ubiquitous) precedes without options, and the showcase projects that use precedes (jit_supply), shall schedule as before; snapshots unchanged.
- R4 (ubiquitous) A test through the plan CLI shall cover gapduration forward and backward, gaplength, and the onend refusal, and shall fail on 0.10.2.

SYNTHESIS (localised): domain = the depends/precedes duality of the .tjp format, implemented here by turning precedes into the target's depends. Alternatives: carry the options into the same dependency dict depends builds [CHOSEN: one representation, so placement, readiness and the post-checks already handle it] vs model precedes separately [REJECTED: every scheduler module would need a second path] vs support onend by a new end-to-end option [REJECTED: no placement code bounds a start by another task's end; refusing is the fail-closed choice until it does].

---

DONE: parser _resolve_precedes carries gapduration, gaplength and maxgapduration into the same dependency dict 'depends' builds, and refuses onend with a SemanticError naming the task. Verified: forward a precedes b { gapduration 30min } -> b 10:00-11:00 (was 09:30); backward with gapduration 30min -> a Mon 17:00-Tue 09:00, b Tue 09:30-10:30, and with gaplength 90min -> a Mon 15:00-16:00, both identical to the reference scheduler (0.10.2 put a at Tue 08:30-09:30 in both); without options unchanged and identical to the reference. Three backward container shapes with precedes (container precedes leaf with gap, leaf precedes container with gaplength, nested chain) identical to the reference. tests/test_container_dependencies.py precedes tests fail on v0.10.2.
