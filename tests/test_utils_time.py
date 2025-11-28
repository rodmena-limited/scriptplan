import unittest
from datetime import datetime, timezone

from scriptplan.utils.time import TjTime


class TestTjTime(unittest.TestCase):
    def test_init(self):
        t = TjTime()
        self.assertTrue(isinstance(t.time, datetime))

        t2 = TjTime(t)
        self.assertEqual(t2.time, t.time)

        t3 = TjTime(1672531200) # 2023-01-01 00:00:00 UTC
        self.assertEqual(t3.time.year, 2023)

    def test_operations(self):
        t = TjTime(datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
        t_later = t + 3600
        self.assertEqual(t_later.time.hour, 13)

        diff = t_later - t
        self.assertEqual(diff, 3600)

        self.assertTrue(t < t_later)

    def test_align(self):
        # 12:00:00 aligned to 1 hour (3600) -> 12:00:00
        t = TjTime(datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
        aligned = t.align(3600)
        self.assertEqual(aligned.time, t.time)

        # 12:30:00 aligned to 1 hour -> 12:00:00
        t = TjTime(datetime(2023, 1, 1, 12, 30, 0, tzinfo=timezone.utc))
        aligned = t.align(3600)
        self.assertEqual(aligned.time.minute, 0)

    def test_calendar_logic(self):
        t = TjTime(datetime(2023, 1, 31, 12, 0, 0, tzinfo=timezone.utc))
        next_month = t.sameTimeNextMonth()
        self.assertEqual(next_month.time.month, 2)
        self.assertEqual(next_month.time.day, 28) # 2023 not leap

if __name__ == '__main__':
    unittest.main()
