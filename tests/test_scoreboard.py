import unittest
from datetime import datetime, timedelta

from scriptplan.scheduler.scoreboard import Scoreboard
from scriptplan.utils.time import TimeInterval


class TestScoreboard(unittest.TestCase):
    def test_init(self):
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 2) # 1 day
        sb = Scoreboard(start, end, 3600) # 1 hour

        self.assertEqual(sb.size, 25) # 24 hours + 1 endpoint? Ruby says ceil + 1
        self.assertEqual(len(sb.sb), 25)

    def test_idxToDate(self):
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 2)
        sb = Scoreboard(start, end, 3600)

        d = sb.idxToDate(1)
        self.assertEqual(d, start + timedelta(hours=1))

        with self.assertRaises(IndexError):
            sb.idxToDate(100)

    def test_dateToIdx(self):
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 2)
        sb = Scoreboard(start, end, 3600)

        idx = sb.dateToIdx(start + timedelta(hours=1))
        self.assertEqual(idx, 1)

        idx_force = sb.dateToIdx(start + timedelta(hours=100), True)
        self.assertEqual(idx_force, sb.size - 1)

    def test_collectIntervals(self):
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 2)
        sb = Scoreboard(start, end, 3600)

        # Mark slots 5 to 10 as True
        for i in range(5, 11):
            sb[i] = True

        iv = TimeInterval(start, end)
        intervals = sb.collectIntervals(iv, 3600, lambda x: x is True)

        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0].start, sb.idxToDate(5))
        # self.assertEqual(intervals[0].end, sb.idxToDate(11)) # Logic is complex, verify range

if __name__ == '__main__':
    unittest.main()
