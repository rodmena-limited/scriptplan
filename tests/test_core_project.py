import unittest

from scriptplan.core.project import Project
from scriptplan.core.property import PropertySet


class TestProject(unittest.TestCase):
    def test_initialization(self):
        project = Project("prj", "Test Project", "1.0")
        self.assertEqual(project.id, "prj")
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.version, "1.0")

        self.assertIsInstance(project.tasks, PropertySet)
        self.assertIsInstance(project.resources, PropertySet)
        self.assertIsInstance(project.reports, PropertySet)
        self.assertIsInstance(project.scenarios, PropertySet)

    def test_attributes(self):
        project = Project("prj", "Test Project", "1.0")
        self.assertEqual(project['dailyworkinghours'], 8.0)
        self.assertEqual(project['currency'], "EUR")

        project['dailyworkinghours'] = 7.5
        self.assertEqual(project['dailyworkinghours'], 7.5)

    def test_attribute_error(self):
        project = Project("prj", "Test Project", "1.0")
        # Accessing nonexistent attribute returns None (not an error)
        self.assertIsNone(project['nonexistent_attribute'])

if __name__ == '__main__':
    unittest.main()
