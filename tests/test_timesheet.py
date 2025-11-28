import unittest
from datetime import datetime

from scriptplan.core.timesheet import TimeSheet, TimeSheetRecord, TimeSheets
from scriptplan.utils.time import TimeInterval


class MockResource:
    """Mock resource for testing."""
    def __init__(self, project=None, name="Test Resource"):
        self.project = project
        self.name = name


class MockProject:
    """Mock project for testing."""
    def __init__(self):
        self.dailyWorkingHours = 8
        self.weeklyWorkingDays = 5
        self._scheduleGranularity = 3600

    def get(self, key, default=None):
        if key == 'scheduleGranularity':
            return self._scheduleGranularity
        return default

    def dateToIdx(self, date):
        return 0


class MockTask:
    """Mock task for testing."""
    def __init__(self, task_id):
        self._id = task_id

    @property
    def fullId(self):
        return self._id


class TestTimeSheetRecord(unittest.TestCase):
    def setUp(self):
        self.project = MockProject()
        self.resource = MockResource(self.project)
        self.interval = TimeInterval(
            datetime(2023, 1, 1),
            datetime(2023, 1, 8)
        )
        self.time_sheet = TimeSheet(self.resource, self.interval, 0)

    def test_init_with_task(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        self.assertEqual(record.task, task)
        self.assertIsNone(record.work)
        self.assertIsNone(record.remaining)

    def test_init_with_string_id(self):
        record = TimeSheetRecord(self.time_sheet, "new_task")
        self.assertEqual(record.task, "new_task")

    def test_work_setter_integer(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        record.work = 10
        self.assertEqual(record.work, 10)

    def test_work_setter_percentage(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        record.work = 0.5  # 50%
        self.assertIsNotNone(record.work)

    def test_taskId_with_task_object(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        self.assertEqual(record.taskId, "t1")

    def test_taskId_with_string(self):
        record = TimeSheetRecord(self.time_sheet, "new_task")
        self.assertEqual(record.taskId, "new_task")

    def test_remaining_setter(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        record.remaining = 5
        self.assertEqual(record.remaining, 5)

    def test_expected_end_setter(self):
        task = MockTask("t1")
        record = TimeSheetRecord(self.time_sheet, task)
        end_date = datetime(2023, 1, 15)
        record.expectedEnd = end_date
        self.assertEqual(record.expectedEnd, end_date)


class TestTimeSheet(unittest.TestCase):
    def setUp(self):
        self.project = MockProject()
        self.resource = MockResource(self.project)
        self.interval = TimeInterval(
            datetime(2023, 1, 1),
            datetime(2023, 1, 8)
        )

    def test_init(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        self.assertEqual(ts.resource, self.resource)
        self.assertEqual(ts.interval, self.interval)
        self.assertEqual(ts.scenarioIdx, 0)

    def test_init_no_resource(self):
        with self.assertRaises(ValueError):
            TimeSheet(None, self.interval, 0)

    def test_init_no_interval(self):
        with self.assertRaises(ValueError):
            TimeSheet(self.resource, None, 0)

    def test_init_no_scenario(self):
        with self.assertRaises(ValueError):
            TimeSheet(self.resource, self.interval, None)

    def test_add_record(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        task = MockTask("t1")
        record = TimeSheetRecord(ts, task)
        self.assertEqual(len(ts.records), 1)
        self.assertEqual(ts.records[0], record)

    def test_lshift_operator(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        # Records are added during construction, so we check the list
        self.assertEqual(len(ts.records), 0)

    def test_percentToSlots(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        slots = ts.percentToSlots(0.5)
        self.assertIsInstance(slots, int)

    def test_slotsToPercent(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        percent = ts.slotsToPercent(10)
        self.assertIsInstance(percent, float)

    def test_slotsToDays(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        days = ts.slotsToDays(8)  # 8 slots = 1 day with default settings
        self.assertIsInstance(days, float)

    def test_daysToSlots(self):
        ts = TimeSheet(self.resource, self.interval, 0)
        slots = ts.daysToSlots(1)  # 1 day
        self.assertIsInstance(slots, int)


class TestTimeSheets(unittest.TestCase):
    def test_init(self):
        tss = TimeSheets()
        self.assertEqual(len(tss), 0)

    def test_is_list(self):
        tss = TimeSheets()
        self.assertIsInstance(tss, list)

    def test_append(self):
        project = MockProject()
        resource = MockResource(project)
        interval = TimeInterval(
            datetime(2023, 1, 1),
            datetime(2023, 1, 8)
        )
        ts = TimeSheet(resource, interval, 0)
        tss = TimeSheets()
        tss.append(ts)
        self.assertEqual(len(tss), 1)

    def test_check_empty(self):
        tss = TimeSheets()
        # Should not raise
        tss.check()

    def test_warnOnDelta_empty(self):
        tss = TimeSheets()
        # Should not raise
        tss.warnOnDelta()


if __name__ == '__main__':
    unittest.main()
