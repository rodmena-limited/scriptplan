# alap_bounded_by_declared_starts

x and y are declared to start at 14:00 and 14:30; x holds the desk until 15:00, so y runs 15:00-16:00.
The alap milestones m and n precede them and are bounded by the starts the file states: m at 14:00, n at
14:30. Scheduling twice gives the same answer because the bound is the stated start, not a start a
previous run wrote back.
