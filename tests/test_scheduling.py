import unittest
from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.task import Task
from datetime import datetime

class TestScheduling(unittest.TestCase):
    def test_scheduling_simple(self):
        project = Project("prj", "Test Project", "1.0")
        project['start'] = datetime(2023, 1, 1)
        project['end'] = datetime(2023, 1, 10)
        project['scheduleGranularity'] = 86400 # 1 day
        
        task = Task(project, "t1", "Task 1", None)
        task[('start', 0)] = datetime(2023, 1, 1)
        task[('duration', 0)] = 2 # 2 days
        
        result = project.schedule()
        self.assertTrue(result)
        self.assertTrue(task.get('scheduled', 0))
        self.assertEqual(task.get('end', 0), datetime(2023, 1, 3)) # 1+2

if __name__ == '__main__':
    unittest.main()
