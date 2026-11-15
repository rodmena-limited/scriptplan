# shared_slot_forward_60min

Three tasks of 40, 13 and 40 minutes on one desk, same priority, 60-minute slots.
Tasks of equal priority are placed larger effort first (path criticalness), and equal efforts in
declaration order, so the order is t0, t2, t1. One person works one task at a time, so they run back to back
from 09:00: t0 09:00 + 40 = 09:40; t2 09:40 + 40 = 10:20; t1 10:20 + 13 = 10:33. Total 93 minutes.
0.10.0 started all three at 09:00 at 60-minute resolution (issuedb #11). Until 0.10.3 equal priorities
were placed in declaration order (issuedb #37).
