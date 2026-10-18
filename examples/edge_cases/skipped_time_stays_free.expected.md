# skipped_time_stays_free

e (alap, end 14:30, priority 900) holds the desk 14:00-14:30. z may start at 14:00 but the desk is busy,
so it starts 14:30 and runs an hour. On Tuesday f holds 09:30-10:00; g may start at 09:00 and the desk is
free until 09:30, so g runs 09:00-09:30. 0.10.1 lost the skipped half hours: z 15:00-16:00, g 10:00-10:30
(issuedb #17).
