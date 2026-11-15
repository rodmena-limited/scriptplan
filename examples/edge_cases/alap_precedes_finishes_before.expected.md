# alap_precedes_finishes_before

`precedes` on a task scheduled as late as possible: b must finish before a starts. a is bounded only
by g's end: Fri 13:30-17:30. b must end by a's start, Fri 13:30. Friday has 210 minutes left under the
cap (10:00-13:30) and Thursday gives the other 270 (13:00-17:30).

Until 0.11.0 this file said `depends !a { onstart }`, which ScriptPlan read the same way. That is now
refused: `onstart` needs a task scheduled as soon as possible.
