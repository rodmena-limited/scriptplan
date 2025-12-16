import unittest
from datetime import datetime

from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task


class TestResource(unittest.TestCase):
    def test_resource_initialization(self):
        project = Project("prj", "Test Project", "1.0")
        # Setup minimal project data
        project['start'] = datetime(2023, 1, 1)
        project['end'] = datetime(2023, 1, 31)

        res = Resource(project, "res1", "Resource 1", None)
        self.assertEqual(res.id, "res1")
        self.assertEqual(res.name, "Resource 1")
        self.assertIsNotNone(res.data[0])

        # Test booking (stub behavior)
        task = Task(project, "t1", "Task 1", None)
        # booking requires initScoreboard which needs project start/end and attributes

        # We need to verify ResourceScenario attributes are created
        self.assertEqual(res.get('efficiency', 0), 1.0)

if __name__ == '__main__':
    unittest.main()
