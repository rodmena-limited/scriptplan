# inherited_start_waits_for_dependency

g states start Mon 10:00 and its children inherit it as an earliest start. a has nothing to wait for:
Mon 10:00-17:30 is the 450 minutes the daily cap allows and Tue 08:30-09:00 the last 30. b may not start
before 10:00 Monday and must wait for a, so it runs Tue 09:00-10:00. The hour-level reference scheduler gives
the same dates. 0.10.1 started b at Mon 10:00, a day before a finished (trace's defect 13).
