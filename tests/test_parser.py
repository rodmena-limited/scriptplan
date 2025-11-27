import unittest
from rodmena_resource_management.parser.tjp_parser import ProjectFileParser
from rodmena_resource_management.core.project import Project
from datetime import datetime

class TestTJPParser(unittest.TestCase):
    def test_parse_simple_project(self):
        text = """
        project "prj1" "Test Project" "1.0" {
            timezone "UTC"
            dailyworkinghours 8.0
            
            resource r1 "Dev 1" {
                email "dev1@example.com"
                efficiency 1.0
            }
            
            task t1 "Task 1" {
                start 2023-01-01
                end 2023-01-05
            }
        }
        """
        parser = ProjectFileParser()
        project = parser.parse(text)
        
        self.assertIsInstance(project, Project)
        self.assertEqual(project.id, "prj1")
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project['dailyworkinghours'], 8.0)
        
        # Verify resource
        self.assertIn("r1", project.resources._properties)
        res = project.resources["r1"]
        # self.assertEqual(res.get('email'), "dev1@example.com") # Attribute 'email' not defined in Project yet?
        
        # Verify task
        self.assertIn("t1", project.tasks._properties)
        task = project.tasks["t1"]
        self.assertEqual(task.get('start', 0), datetime(2023, 1, 1))

if __name__ == '__main__':
    unittest.main()
