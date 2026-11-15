# daily_cap_counts_worked_time

dailymax 60min on the desk, and three tasks of 40, 13 and 40 minutes at the same priority.
Tasks of equal priority are placed larger effort first (path criticalness), and equal efforts in
declaration order, so the order is t0, t2, t1. Monday: t0 works 09:00-09:40, leaving 20 minutes under the
cap, so t2 works 09:40-10:00 on Monday and its other 20 minutes on Tuesday, 09:00-09:20. t1 follows on
Tuesday, 09:20-09:33. The cap blocks at exactly 60 minutes and releases on the next day. 0.10.0 counted
whole booked hours against the cap and spread the tasks over Monday, Tuesday and Wednesday.
