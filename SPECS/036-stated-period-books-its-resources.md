# A task with a stated start and end books none of the resources it allocates

**Ticket**: issuedb #36  
**Status**: closed (released in 0.10.3)  
**Priority**: high  
**Release**: 0.10.3

This file is the in-repo copy of the ticket's EARS spec and synthesis record.
Keep it in sync with `issuedb-cli context 36` whenever the spec or the chosen
alternative changes.

---

Found while answering Siambr's question about overlapping fixed tasks (thread 01M7ES0QR99SKNWDPKC5QXKNR9). Reproduction C6: task a priority 600, start 18:00, end 20:00, allocate r; task w effort 1h allocate r start 18:00. The reference books r to a for 18:00-20:00 and places w at 20:00-21:00. ScriptPlan 0.10.2 books nothing for a and places w at 18:00-19:00. A task stated as duration 2h does book (C7 agrees with the reference).

EARS SPEC:
- R1 (ubiquitous) A task whose period comes from a stated start and end shall book each allocated resource for every slot of that period in which the resource is on shift and free, exactly as a duration task does.
- R2 (unwanted) If two such tasks overlap on one resource, then the one placed first shall hold the shared slots and the other shall keep its stated dates and book the remaining slots; neither is an error.
- R3 (quality) C, C6 and C7 shall give the reference's dates, and the bookings for C shall be a 2 h, b 1 h, c 0 h.

Synthesis (localised bugfix): solution domain is the existing duration-task booking path; the concept is reused, not a new one.

---

VERIFICATION (2026-11-15): C6 and C7 give the reference's dates (w at 20:00-21:00). Bookings for C are a 2.0 h, b 1.0 h, c 0.0 h, the reference's 0.3/0.1/0.0 days at its one-decimal rounding. tests/test_contention_and_bookings.py.
