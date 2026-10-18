# alap_milestones_exact

t holds the desk 16:00-17:00, so t2 (end 16:30) must run before it: 15:30-16:00. An alap milestone
sits at the latest moment its successor allows: m at t's start 16:00, m2 at t2's start 15:30. d ends at m,
16:00, and lasts 2 hours: 14:00. 0.10.1 put m at 15:00 and m2 at 15:00 (issuedb #14).
