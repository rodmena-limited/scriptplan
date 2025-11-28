import unittest

from scriptplan.core.project import Project
from scriptplan.core.scenario import Scenario


class TestScenario(unittest.TestCase):
    def test_scenario_initialization(self):
        project = Project("prj", "Test Project", "1.0")

        # Default plan scenario created in Project init
        self.assertEqual(project.scenarios.items(), 1)
        plan = project.scenario(0)
        self.assertIsInstance(plan, Scenario)
        self.assertEqual(plan.id, "plan")
        self.assertTrue(plan.get('active'))

        # Create new scenario
        sc2 = Scenario(project, "sc2", "Scenario 2", plan)
        self.assertEqual(project.scenarios.items(), 2)
        self.assertEqual(sc2.parent, plan)
        self.assertEqual(sc2.fullId, "sc2") # Scenarios have flat namespace=True
        # Wait, Project.py says PropertySet(self, True) -> flat_namespace=True
        # Ruby says PropertySet.new(self, true).
        # If flat, fullId should just be id.
        # But if it has parent, and flat namespace...
        # In flat namespace, IDs must be unique globally in the set. Hierarchy is logical but not in ID?
        # Let's check PropertyTreeNode fullId logic.

        # If flatNamespace is True:
        # def fullId(self): res = self.subId; ... return res

        # So it should be just "sc2".
        self.assertEqual(sc2.fullId, "sc2")

if __name__ == '__main__':
    unittest.main()
