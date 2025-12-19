import unittest

from scriptplan.core.project import Project
from scriptplan.core.shift import Shift, ShiftScenario


class TestShift(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")

    def test_shift_init(self):
        shift = Shift(self.project, "s1", "Morning Shift", None)
        self.assertEqual(shift.id, "s1")
        self.assertEqual(shift.name, "Morning Shift")
        self.assertIsNone(shift.parent)
        self.assertEqual(shift.project, self.project)

    def test_shift_in_project(self):
        shift = Shift(self.project, "s1", "Morning Shift", None)
        self.assertIn(shift, self.project.shifts._properties)
        self.assertEqual(self.project.shifts["s1"], shift)

    def test_shift_scenario_data(self):
        shift = Shift(self.project, "s1", "Morning Shift", None)
        self.assertIsNotNone(shift.data)
        self.assertEqual(len(shift.data), self.project.scenarioCount())
        self.assertIsInstance(shift.data[0], ShiftScenario)

    def test_shift_scenario_method(self):
        shift = Shift(self.project, "s1", "Morning Shift", None)
        scenario = shift.scenario(0)
        self.assertIsInstance(scenario, ShiftScenario)
        self.assertEqual(scenario.scenarioIdx, 0)

    def test_shift_hierarchy(self):
        parent_shift = Shift(self.project, "s_parent", "Parent Shift", None)
        child_shift = Shift(self.project, "s_parent.s_child", "Child Shift", parent_shift)
        self.assertEqual(child_shift.parent, parent_shift)
        self.assertIn(child_shift, parent_shift.children)


class TestShiftScenario(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")
        self.shift = Shift(self.project, "s1", "Test Shift", None)
        self.scenario = self.shift.scenario(0)

    def test_scenario_init(self):
        self.assertIsNotNone(self.scenario)
        self.assertEqual(self.scenario.property, self.shift)
        self.assertEqual(self.scenario.scenarioIdx, 0)

    def test_onShift_without_workinghours(self):
        # Without working hours defined, should return False
        from datetime import datetime
        date = datetime(2023, 1, 1, 10, 0, 0)
        self.assertFalse(self.scenario.onShift(date))

    def test_onLeave_without_leaves(self):
        from datetime import datetime
        date = datetime(2023, 1, 1, 10, 0, 0)
        self.assertFalse(self.scenario.onLeave(date))

    def test_replace_default(self):
        # Default replace value should be False
        self.assertFalse(self.scenario.replace())


if __name__ == '__main__':
    unittest.main()
