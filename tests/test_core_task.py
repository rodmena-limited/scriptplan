import unittest

from scriptplan.core.project import Project
from scriptplan.core.property import PropertyTreeNode
from scriptplan.core.task import Task


class TestTask(unittest.TestCase):
    def test_task_initialization(self):
        project = Project("prj", "Test Project", "1.0")
        task = Task(project, "t1", "Task 1", None)

        self.assertEqual(task.id, "t1")
        self.assertEqual(task.name, "Task 1")
        self.assertIsInstance(task, PropertyTreeNode)
        self.assertEqual(task.project, project)

        # Check registration - task is in the PropertySet
        self.assertIn(task, project.tasks._properties)
        self.assertEqual(project.tasks["t1"], task)

        # Check scenario data
        self.assertTrue(len(task.data) >= 1)
        self.assertIsNotNone(task.data[0])

        # Check child
        child = Task(project, "t2", "Task 2", task)
        self.assertEqual(child.parent, task)
        self.assertIn(child, task.children)
        self.assertEqual(child.fullId, "t1.t2")

if __name__ == '__main__':
    unittest.main()
