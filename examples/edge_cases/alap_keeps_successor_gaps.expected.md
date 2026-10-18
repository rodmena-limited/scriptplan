# alap_keeps_successor_gaps

Backward tasks end as late as their successors allow, less the gap each successor asks for.
b holds the desk Tue 14:00-15:00, so a (alap, precedes b) runs 13:00-14:00. d starts Tue 15:00 and wants
c finished 2 hours (calendar) before it: c ends 13:00 and runs 12:00-13:00. f starts Tue 11:00 and wants
3 working hours after e: Tue 09:00-11:00 is 2 of them and Mon 16:00-17:00 the third, so e ends Mon 16:00
and runs 15:00-16:00. Before 0.10.2 these alap tasks were moved to the project start, and once they were
not, the gap was ignored (issuedb #19).
