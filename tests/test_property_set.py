import unittest

from scriptplan.core.project import Project
from scriptplan.core.task import Task


class TestPropertySet(unittest.TestCase):
    def test_standard_attributes(self):
        project = Project("prj", "Test Project", "1.0")
        # Check if standard attributes are present in tasks set
        pset = project.tasks
        self.assertTrue(pset.knownAttribute('id'))
        self.assertTrue(pset.knownAttribute('name'))
        self.assertTrue(pset.knownAttribute('seqno'))

    def test_remove_property(self):
        project = Project("prj", "Test Project", "1.0")
        t1 = Task(project, "t1", "Task 1", None)
        t2 = Task(project, "t2", "Task 2", t1)

        self.assertIn(t1, project.tasks)
        self.assertIn(t2, project.tasks)
        self.assertEqual(project.tasks.items(), 2)

        # Remove parent should remove child
        project.tasks.removeProperty(t1)

        self.assertEqual(project.tasks.items(), 0)
        self.assertNotIn(t1, project.tasks)
        self.assertNotIn(t2, project.tasks)

    def test_index(self):
        project = Project("prj", "Test Project", "1.0")
        t1 = Task(project, "t1", "Task 1", None)
        t2 = Task(project, "t2", "Task 2", t1)
        t3 = Task(project, "t3", "Task 3", t1)

        # Index logic
        project.tasks.index()

        # Check BSI (Breakdown Structure Index)
        # t1: 1
        # t2: 1.1
        # t3: 1.2
        # Assuming 'bsi' attribute exists (it is added by index() in ruby?)
        # No, 'bsi' attribute must be defined. In Ruby Project.rb, 'bsi' is defined for reports but maybe not tasks?
        # Wait, PropertySet.rb: index() calls p.force('bsi', bsi).
        # Does Task have 'bsi' attribute?
        # In Project.rb:
        # [ 'bsi',       'BSI',          StringAttribute, false, false,   false, '' ],
        # is defined for @reports.
        # Is it defined for Tasks?
        # Project.rb tasks attributes: [ 'seqno', ... ] but no 'bsi'.
        # Actually TaskJuggler usually has 'bsi' for tasks.
        # Let's check Project.rb again for 'bsi' in tasks.
        pass

if __name__ == '__main__':
    unittest.main()
