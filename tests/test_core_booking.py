import unittest
from datetime import datetime, timedelta

from scriptplan.core.booking import Booking
from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task
from scriptplan.utils.time import TimeInterval


class TestBooking(unittest.TestCase):
    def test_booking(self):
        project = Project("prj", "Test Project", "1.0")

        res = Resource(project, "r1", "Resource 1", None)
        task = Task(project, "t1", "Task 1", None)

        start = datetime(2023, 1, 1, 9, 0)
        end = start + timedelta(hours=2)
        interval = TimeInterval(start, end)

        booking = Booking(res, task, [interval])

        expected_str = f"r1 {start} + 2.0h"
        self.assertEqual(booking.to_s(), expected_str)

        expected_tjp = f"t1 {start} + 2.0h {{ overtime 2 }}"
        self.assertEqual(booking.to_tjp(True), expected_tjp)

        expected_tjp_res = f"r1 {start} + 2.0h {{ overtime 2 }}"
        self.assertEqual(booking.to_tjp(False), expected_tjp_res)

if __name__ == '__main__':
    unittest.main()
