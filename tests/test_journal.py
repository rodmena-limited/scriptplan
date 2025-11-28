import unittest
from datetime import datetime

from scriptplan.core.journal import AlertLevel, Journal, JournalEntry, JournalEntryList


class TestAlertLevel(unittest.TestCase):
    def test_alert_levels_ordered(self):
        self.assertLess(AlertLevel.GREEN, AlertLevel.YELLOW)
        self.assertLess(AlertLevel.YELLOW, AlertLevel.RED)

    def test_alert_level_values(self):
        self.assertEqual(AlertLevel.GREEN, 0)
        self.assertEqual(AlertLevel.YELLOW, 1)
        self.assertEqual(AlertLevel.RED, 2)


class TestJournalEntry(unittest.TestCase):
    def setUp(self):
        self.journal = Journal()
        self.date = datetime(2023, 1, 15)
        self.entry = JournalEntry(self.journal, self.date, "Test headline", None)

    def test_entry_creation(self):
        self.assertEqual(self.entry.date, self.date)
        self.assertEqual(self.entry.headline, "Test headline")
        self.assertIsNone(self.entry.property)
        self.assertEqual(self.entry.alert_level, AlertLevel.GREEN)

    def test_entry_default_values(self):
        self.assertIsNone(self.entry.author)
        self.assertEqual(self.entry.moderators, [])
        self.assertIsNone(self.entry.summary)
        self.assertIsNone(self.entry.details)
        self.assertEqual(self.entry.flags, [])

    def test_entry_to_dict(self):
        d = self.entry.to_dict()
        self.assertEqual(d['headline'], "Test headline")
        self.assertEqual(d['alert_level'], 'GREEN')
        self.assertIsNotNone(d['date'])


class TestJournalEntryList(unittest.TestCase):
    def test_empty_list(self):
        entry_list = JournalEntryList()
        self.assertEqual(len(entry_list), 0)

    def test_list_with_entries(self):
        journal = Journal()
        e1 = JournalEntry(journal, datetime(2023, 1, 10), "Entry 1", None)
        e2 = JournalEntry(journal, datetime(2023, 1, 15), "Entry 2", None)
        entry_list = JournalEntryList([e1, e2])
        self.assertEqual(len(entry_list), 2)

    def test_sort_by_date_ascending(self):
        journal = Journal()
        e1 = JournalEntry(journal, datetime(2023, 1, 15), "Later", None)
        e2 = JournalEntry(journal, datetime(2023, 1, 10), "Earlier", None)
        entry_list = JournalEntryList([e1, e2])
        entry_list.sort_by([('date', True)])
        self.assertEqual(entry_list[0].headline, "Earlier")
        self.assertEqual(entry_list[1].headline, "Later")

    def test_sort_by_date_descending(self):
        journal = Journal()
        e1 = JournalEntry(journal, datetime(2023, 1, 10), "Earlier", None)
        e2 = JournalEntry(journal, datetime(2023, 1, 15), "Later", None)
        entry_list = JournalEntryList([e1, e2])
        entry_list.sort_by([('date', False)])
        self.assertEqual(entry_list[0].headline, "Later")
        self.assertEqual(entry_list[1].headline, "Earlier")

    def test_filter(self):
        journal = Journal()
        e1 = JournalEntry(journal, datetime(2023, 1, 10), "Green", None)
        e1.alert_level = AlertLevel.GREEN
        e2 = JournalEntry(journal, datetime(2023, 1, 15), "Red", None)
        e2.alert_level = AlertLevel.RED
        entry_list = JournalEntryList([e1, e2])

        red_only = entry_list.filter(lambda e: e.alert_level == AlertLevel.RED)
        self.assertEqual(len(red_only), 1)
        self.assertEqual(red_only[0].headline, "Red")


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.journal = Journal()

    def test_empty_journal(self):
        self.assertEqual(len(self.journal), 0)
        self.assertEqual(list(self.journal), [])

    def test_add_entry(self):
        entry = JournalEntry(self.journal, datetime(2023, 1, 15), "Test", None)
        self.journal.add_entry(entry)
        self.assertEqual(len(self.journal), 1)

    def test_create_entry(self):
        entry = self.journal.create_entry(datetime(2023, 1, 15), "Test", None)
        self.assertEqual(len(self.journal), 1)
        self.assertEqual(entry.headline, "Test")

    def test_entries_property(self):
        self.journal.create_entry(datetime(2023, 1, 15), "Entry 1", None)
        self.journal.create_entry(datetime(2023, 1, 16), "Entry 2", None)
        entries = self.journal.entries
        self.assertIsInstance(entries, JournalEntryList)
        self.assertEqual(len(entries), 2)

    def test_entries_by_date(self):
        self.journal.create_entry(datetime(2023, 1, 15, 10, 0), "Morning", None)
        self.journal.create_entry(datetime(2023, 1, 15, 14, 0), "Afternoon", None)
        self.journal.create_entry(datetime(2023, 1, 16, 10, 0), "Next day", None)

        entries = self.journal.entries_by_date(datetime(2023, 1, 15))
        self.assertEqual(len(entries), 2)

    def test_entries_in_range(self):
        self.journal.create_entry(datetime(2023, 1, 10), "Before", None)
        self.journal.create_entry(datetime(2023, 1, 15), "In range", None)
        self.journal.create_entry(datetime(2023, 1, 20), "After", None)

        entries = self.journal.entries_in_range(
            datetime(2023, 1, 12),
            datetime(2023, 1, 18)
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].headline, "In range")

    def test_clear(self):
        self.journal.create_entry(datetime(2023, 1, 15), "Test", None)
        self.assertEqual(len(self.journal), 1)
        self.journal.clear()
        self.assertEqual(len(self.journal), 0)

    def test_to_list(self):
        self.journal.create_entry(datetime(2023, 1, 15), "Test", None)
        result = self.journal.to_list()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['headline'], "Test")


class TestJournalWithMockTask(unittest.TestCase):
    """Test journal with mock task/property objects."""

    class MockProperty:
        def __init__(self, full_id):
            self.fullId = full_id
            self.children = []

    def test_entries_by_task(self):
        journal = Journal()
        task = self.MockProperty("project.task1")

        journal.create_entry(datetime(2023, 1, 15), "Task entry", task)
        journal.create_entry(datetime(2023, 1, 16), "Another entry", task)
        journal.create_entry(datetime(2023, 1, 17), "Other task", self.MockProperty("project.task2"))

        entries = journal.entries_by_task(task)
        self.assertEqual(len(entries), 2)

    def test_entries_by_task_with_date_filter(self):
        journal = Journal()
        task = self.MockProperty("project.task1")

        journal.create_entry(datetime(2023, 1, 10), "Early", task)
        journal.create_entry(datetime(2023, 1, 20), "Late", task)

        entries = journal.entries_by_task(
            task,
            start=datetime(2023, 1, 15),
            end=datetime(2023, 1, 25)
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].headline, "Late")

    def test_entries_by_task_recursive(self):
        journal = Journal()
        parent = self.MockProperty("project.parent")
        child = self.MockProperty("project.parent.child")
        parent.children = [child]

        journal.create_entry(datetime(2023, 1, 15), "Parent entry", parent)
        journal.create_entry(datetime(2023, 1, 16), "Child entry", child)

        entries = journal.entries_by_task_recursive(parent)
        self.assertEqual(len(entries), 2)


if __name__ == '__main__':
    unittest.main()
