import unittest
from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.task import Task
from rodmena_resource_management.core.property import PropertyTreeNode

class TestPropertyTreeNode(unittest.TestCase):
    def test_adopt(self):
        project = Project("prj", "Test Project", "1.0")

        parent_task = Task(project, "parent", "Parent Task", None)
        child_task = Task(project, "child", "Child Task", None)  # Top level initially

        self.assertIn(child_task, project.tasks._properties)

        parent_task.adopt(child_task)

        self.assertIn(child_task, parent_task.adoptees)
        self.assertIn(parent_task, child_task.stepParents)
        self.assertIn(child_task, parent_task.kids())
        self.assertIn(parent_task, child_task.parents())

    def test_inherit_attributes(self):
        project = Project("prj", "Test Project", "1.0")
        # 'priority' is scenario specific (True) in Project.py
        
        parent_task = Task(project, "parent", "Parent Task", None)
        parent_task[('priority', 0)] = 800
        
        child_task = Task(project, "child", "Child Task", parent_task)
        
        # Before inheritance
        self.assertEqual(child_task.get('priority', 0), 500) # Default
        
        child_task.inheritAttributes()
        
        # After inheritance
        self.assertEqual(child_task.get('priority', 0), 800)

if __name__ == '__main__':
    unittest.main()
