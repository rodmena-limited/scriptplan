import unittest
from datetime import datetime
from pathlib import Path

from scriptplan.core.project import Project
from scriptplan.core.task import Task
from scriptplan.parser.tjp_parser import ProjectFileParser


class TestSchedulingBasic(unittest.TestCase):
    """Basic scheduling tests with manually created projects."""

    def test_scheduling_simple_duration(self):
        """Test scheduling a task with duration."""
        project = Project("prj", "Test Project", "1.0")
        project['start'] = datetime(2023, 1, 1)
        project['end'] = datetime(2023, 1, 10)
        project['scheduleGranularity'] = 86400  # 1 day

        task = Task(project, "t1", "Task 1", None)
        task[('start', 0)] = datetime(2023, 1, 1)
        task[('duration', 0)] = 2  # 2 days

        result = project.schedule()
        self.assertTrue(result)
        self.assertTrue(task.get('scheduled', 0))

    def test_scheduling_empty_project(self):
        """Test scheduling a project with no tasks."""
        project = Project("prj", "Test Project", "1.0")
        project['start'] = datetime(2023, 1, 1)
        project['end'] = datetime(2023, 1, 10)

        # Should not error
        result = project.schedule()
        self.assertTrue(result)


class TestSchedulingFromTJP(unittest.TestCase):
    """Test scheduling from parsed TJP files."""

    def test_scheduling_simple_effort(self):
        """Basic scheduling of a simple project with effort."""
        text = '''
project test "Test" 2024-01-01 +1m {
    scenario plan "Plan"
}

resource dev "Developer" {}

task t "Task" {
    effort 5d
    allocate dev
}
'''
        parser = ProjectFileParser()
        project = parser.parse(text)
        # Scheduling should have been called by parse()
        task = list(project.tasks)[0]
        start = task.get('start', 0)
        self.assertIsNotNone(start)

    def test_scheduling_with_dependencies(self):
        """Test that dependencies are respected in scheduling."""
        text = '''
project test "Test" 2024-01-01 +2m {
    scenario plan "Plan"
}

resource dev "Developer" {}

task phase1 "Phase 1" {
    effort 5d
    allocate dev
}

task phase2 "Phase 2" {
    effort 5d
    allocate dev
    depends phase1
}
'''
        parser = ProjectFileParser()
        project = parser.parse(text)

        tasks = {t.id: t for t in project.tasks}
        phase1 = tasks['phase1']
        phase2 = tasks['phase2']

        # Phase 1 should have dates
        phase1_start = phase1.get('start', 0)
        phase1_end = phase1.get('end', 0)
        self.assertIsNotNone(phase1_start)
        self.assertIsNotNone(phase1_end)

        # Phase 2 should start after Phase 1 ends
        phase2_start = phase2.get('start', 0)
        self.assertIsNotNone(phase2_start)
        self.assertGreaterEqual(phase2_start, phase1_end)

    def test_scheduling_tutorial(self):
        """Test scheduling the tutorial project."""
        test_data_dir = Path(__file__).parent / 'data'
        tutorial_path = test_data_dir / 'tutorial.tjp'

        parser = ProjectFileParser()
        with open(tutorial_path) as f:
            text = f.read()

        project = parser.parse(text)

        # Check that tasks have dates
        tasks_with_dates = 0
        for task in project.tasks:
            start = task.get('start', 0)
            if start:
                tasks_with_dates += 1

        # At least some tasks should have dates (leaf tasks)
        self.assertGreater(tasks_with_dates, 5)

    def test_scheduling_milestones(self):
        """Test that milestones are scheduled correctly."""
        text = '''
project test "Test" 2024-01-01 +1m {
    scenario plan "Plan"
}

task start_milestone "Project Start" {
    start 2024-01-01
    milestone
}
'''
        parser = ProjectFileParser()
        project = parser.parse(text)

        task = list(project.tasks)[0]

        # Milestone should have start = end
        start = task.get('start', 0)
        end = task.get('end', 0)
        self.assertEqual(start, end)

    def test_parse_without_scheduling(self):
        """Test that we can parse without scheduling."""
        text = '''
project test "Test" 2024-01-01 +1m {
    scenario plan "Plan"
}

task t "Task" {
    effort 5d
}
'''
        parser = ProjectFileParser()
        project = parser.parse(text, schedule=False)

        # Task should not have dates yet
        task = list(project.tasks)[0]
        start = task.get('start', 0)
        self.assertIsNone(start)

    def test_scheduling_nested_tasks(self):
        """Test that nested tasks (containers) get dates from children."""
        text = '''
project test "Test" 2024-01-01 +2m {
    scenario plan "Plan"
}

resource dev "Developer" {}

task parent "Parent Task" {
    task child1 "Child 1" {
        effort 3d
        allocate dev
    }
    task child2 "Child 2" {
        effort 2d
        allocate dev
        depends !child1
    }
}
'''
        parser = ProjectFileParser()
        project = parser.parse(text)

        tasks = {t.id: t for t in project.tasks}

        # Children should have dates
        child1 = tasks['child1']
        child2 = tasks['child2']

        self.assertIsNotNone(child1.get('start', 0))
        self.assertIsNotNone(child2.get('start', 0))

        # Child2 should start after child1
        self.assertGreaterEqual(child2.get('start', 0), child1.get('end', 0))


if __name__ == '__main__':
    unittest.main()
