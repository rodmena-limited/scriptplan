import unittest
from datetime import datetime

from scriptplan.core.project import Project
from scriptplan.parser.tjp_parser import ProjectFileParser


class TestTJPParser(unittest.TestCase):
    def test_parse_simple_project(self):
        text = """
        project prj1 "Test Project" 2023-01-01 +3m {
            timezone "UTC"
            dailyworkinghours 8.0
        }

        resource r1 "Dev 1" {
            email "dev1@example.com"
            efficiency 1.0
        }

        task t1 "Task 1" {
            start 2023-01-01
            end 2023-01-05
        }
        """
        parser = ProjectFileParser()
        project = parser.parse(text)

        self.assertIsInstance(project, Project)
        self.assertEqual(project.id, "prj1")
        self.assertEqual(project.name, "Test Project")

        # Verify resource exists
        res = project.resources["r1"]
        self.assertIsNotNone(res)
        self.assertEqual(res.name, "Dev 1")

        # Verify task exists
        task = project.tasks["t1"]
        self.assertIsNotNone(task)
        self.assertEqual(task.name, "Task 1")
        self.assertEqual(task.get('start', 0), datetime(2023, 1, 1))

    def test_parse_nested_tasks(self):
        text = """
        project prj1 "Test Project" 2023-01-01 +3m {
            timezone "UTC"
        }

        task parent "Parent Task" {
            task child1 "Child 1" {
                effort 5d
            }
            task child2 "Child 2" {
                effort 3d
                depends !child1
            }
        }
        """
        parser = ProjectFileParser()
        project = parser.parse(text)

        self.assertEqual(project.id, "prj1")

        # Verify parent task
        parent = project.tasks["parent"]
        self.assertIsNotNone(parent)

        # Verify children are accessible via full path
        child1 = project.tasks["parent.child1"]
        child2 = project.tasks["parent.child2"]
        self.assertIsNotNone(child1)
        self.assertIsNotNone(child2)

        # Verify dependency resolved
        deps = child2.get('depends', 0)
        self.assertIsNotNone(deps)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].id, "child1")

    def test_parse_nested_resources(self):
        text = """
        project prj1 "Test Project" 2023-01-01 +3m {
            timezone "UTC"
        }

        resource team "Team" {
            resource dev1 "Developer 1" {
                email "dev1@example.com"
            }
            resource dev2 "Developer 2" {
                email "dev2@example.com"
            }
        }
        """
        parser = ProjectFileParser()
        project = parser.parse(text)

        team = project.resources["team"]
        dev1 = project.resources["team.dev1"]
        dev2 = project.resources["team.dev2"]

        self.assertIsNotNone(team)
        self.assertIsNotNone(dev1)
        self.assertIsNotNone(dev2)

        self.assertEqual(dev1.parent, team)
        self.assertEqual(dev2.parent, team)

    def test_parse_tutorial_tjp(self):
        """Test parsing the full tutorial.tjp file from TaskJuggler."""
        import os
        test_file = os.path.join(os.path.dirname(__file__), 'data', 'tutorial.tjp')
        if not os.path.exists(test_file):
            self.skipTest("tutorial.tjp not found")

        with open(test_file) as f:
            content = f.read()

        parser = ProjectFileParser()
        project = parser.parse(content)

        # Verify project parsed correctly
        self.assertEqual(project.id, "acso")
        self.assertEqual(project.name, "Accounting Software")

        # Verify resources were parsed (there are nested resources)
        resource_count = sum(1 for _ in project.resources)
        self.assertGreater(resource_count, 0)

        # Verify tasks were parsed
        task_count = sum(1 for _ in project.tasks)
        self.assertGreater(task_count, 0)

    def test_parse_scenario_specific_attributes(self):
        """Test parsing scenario-specific attributes like delayed:start."""
        text = """
        project prj1 "Test Project" 2023-01-01 +3m {
            scenario plan "Plan" {
                scenario delayed "Delayed"
            }
        }

        task t1 "Task 1" {
            start 2023-01-01
            delayed:start 2023-01-15
            effort 10d
            delayed:effort 15d
        }
        """
        parser = ProjectFileParser()
        project = parser.parse(text)

        # Verify scenarios
        scenario_count = sum(1 for _ in project.scenarios)
        self.assertEqual(scenario_count, 2)

        # Verify task has scenario-specific attributes
        task = project.tasks["t1"]
        self.assertIsNotNone(task)

        # Plan scenario (idx=0)
        from datetime import datetime
        self.assertEqual(task.get('start', 0), datetime(2023, 1, 1))
        self.assertEqual(task.get('effort', 0), 80.0)  # 10d * 8h

        # Delayed scenario (idx=1)
        self.assertEqual(task.get('start', 1), datetime(2023, 1, 15))
        self.assertEqual(task.get('effort', 1), 120.0)  # 15d * 8h

if __name__ == '__main__':
    unittest.main()
