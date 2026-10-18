# asap_and_alap_share_a_slot

late (alap, end 10:00) holds 09:20-10:00. e1 takes 09:00-09:13. e2 needs 10 minutes: 7 are free
before late (09:13-09:20); the other 3 come after it, 10:00-10:03. So e2's window is 09:13-10:03 and the
desk never works two tasks at once. 0.10.0 put e2 at 09:00-09:10, on top of e1.
