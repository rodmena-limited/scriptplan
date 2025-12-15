import unittest

from scriptplan.core.account import Account, AccountScenario
from scriptplan.core.project import Project


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")

    def test_account_init(self):
        account = Account(self.project, "a1", "Revenue Account", None)
        self.assertEqual(account.id, "a1")
        self.assertEqual(account.name, "Revenue Account")
        self.assertIsNone(account.parent)
        self.assertEqual(account.project, self.project)

    def test_account_in_project(self):
        account = Account(self.project, "a1", "Revenue Account", None)
        self.assertIn(account, self.project.accounts._properties)
        self.assertEqual(self.project.accounts["a1"], account)

    def test_account_scenario_data(self):
        account = Account(self.project, "a1", "Revenue Account", None)
        self.assertIsNotNone(account.data)
        self.assertEqual(len(account.data), self.project.scenarioCount())
        self.assertIsInstance(account.data[0], AccountScenario)

    def test_account_scenario_method(self):
        account = Account(self.project, "a1", "Revenue Account", None)
        scenario = account.scenario(0)
        self.assertIsInstance(scenario, AccountScenario)
        self.assertEqual(scenario.scenarioIdx, 0)

    def test_account_hierarchy(self):
        parent_account = Account(self.project, "a_parent", "Parent Account", None)
        child_account = Account(self.project, "a_parent.a_child", "Child Account", parent_account)
        self.assertEqual(child_account.parent, parent_account)
        self.assertIn(child_account, parent_account.children)

    def test_account_container(self):
        parent = Account(self.project, "parent", "Parent", None)
        child = Account(self.project, "parent.child", "Child", parent)
        self.assertTrue(parent.container())
        self.assertFalse(child.container())


class TestAccountScenario(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")
        self.account = Account(self.project, "a1", "Test Account", None)
        self.scenario = self.account.scenario(0)

    def test_scenario_init(self):
        self.assertIsNotNone(self.scenario)
        self.assertEqual(self.scenario.property, self.account)
        self.assertEqual(self.scenario.scenarioIdx, 0)

    def test_turnover_empty(self):
        # Turnover with no credits should be 0
        turnover = self.scenario.turnover(0, 100)
        self.assertEqual(turnover, 0.0)


if __name__ == '__main__':
    unittest.main()
