# dependency_offset_one_slot

a takes the desk 09:00-10:00 and y the other resource 09:00-09:50 (both priority 900). x needs y done
(09:50) and the desk (free from 10:00), so it runs 10:00-10:30. 0.10.0 started x at 10:50: the 50-minute
offset of y's end leaked into the next slot.
