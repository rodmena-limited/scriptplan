import unittest

from scriptplan.core.project import Project
from scriptplan.core.property import PropertyList, PTNProxy
from scriptplan.core.task import Task


class TestPropertyList(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")
        self.t1 = Task(self.project, "t1", "Task 1", None)
        self.t2 = Task(self.project, "t2", "Task 2", None)
        self.t3 = Task(self.project, "t3", "Task 3", None)

    def test_init_from_property_set(self):
        pl = PropertyList(self.project.tasks)
        self.assertEqual(len(pl), 3)
        self.assertEqual(pl.propertySet, self.project.tasks)
        self.assertEqual(pl.sortingLevels, 1)
        self.assertEqual(pl.sortingCriteria, ['seqno'])

    def test_init_from_property_list(self):
        pl1 = PropertyList(self.project.tasks)
        pl2 = PropertyList(pl1)
        self.assertEqual(len(pl2), 3)
        self.assertEqual(pl2.propertySet, self.project.tasks)

    def test_contains(self):
        pl = PropertyList(self.project.tasks)
        self.assertIn(self.t1, pl)
        self.assertIn(self.t2, pl)

    def test_getitem_by_index(self):
        pl = PropertyList(self.project.tasks)
        self.assertEqual(pl[0], self.t1)
        self.assertEqual(pl[1], self.t2)
        self.assertEqual(pl[2], self.t3)

    def test_len(self):
        pl = PropertyList(self.project.tasks)
        self.assertEqual(len(pl), 3)

    def test_iter(self):
        pl = PropertyList(self.project.tasks)
        items = list(pl)
        self.assertEqual(len(items), 3)

    def test_sorting_by_seqno(self):
        pl = PropertyList(self.project.tasks)
        # Default sorting by seqno ascending
        self.assertEqual(pl[0], self.t1)
        self.assertEqual(pl[1], self.t2)
        self.assertEqual(pl[2], self.t3)

    def test_sorting_by_name(self):
        pl = PropertyList(self.project.tasks)
        pl.setSorting([('name', True, -1)])
        pl.sort()
        names = [item.name for item in pl]
        self.assertEqual(names, sorted(names))

    def test_sorting_descending(self):
        pl = PropertyList(self.project.tasks)
        pl.setSorting([('seqno', False, -1)])
        pl.sort()
        # Should be in reverse order
        self.assertEqual(pl[0], self.t3)
        self.assertEqual(pl[1], self.t2)
        self.assertEqual(pl[2], self.t1)

    def test_reset_sorting(self):
        pl = PropertyList(self.project.tasks)
        pl.resetSorting()
        self.assertEqual(pl.sortingLevels, 0)
        self.assertEqual(pl.sortingCriteria, [])

    def test_to_ary(self):
        pl = PropertyList(self.project.tasks)
        arr = pl.to_ary()
        self.assertIsInstance(arr, list)
        self.assertEqual(len(arr), 3)

    def test_delete_if(self):
        pl = PropertyList(self.project.tasks)
        pl.delete_if(lambda x: x.name == "Task 2")
        self.assertEqual(len(pl), 2)
        self.assertNotIn(self.t2, pl)

    def test_each(self):
        pl = PropertyList(self.project.tasks)
        results = []
        pl.each(lambda x: results.append(x.name))
        self.assertEqual(len(results), 3)

    def test_index_attribute(self):
        pl = PropertyList(self.project.tasks)
        # After sorting and indexing, items should have 'index' attribute
        self.assertEqual(pl[0].get('index'), 1)
        self.assertEqual(pl[1].get('index'), 2)
        self.assertEqual(pl[2].get('index'), 3)

    def test_str(self):
        pl = PropertyList(self.project.tasks)
        s = str(pl)
        self.assertIn('Sorting:', s)
        self.assertIn('3 properties:', s)


class TestPTNProxy(unittest.TestCase):
    def setUp(self):
        self.project = Project("prj", "Test Project", "1.0")
        self.parent = Task(self.project, "parent", "Parent Task", None)
        self.child = Task(self.project, "child", "Child Task", None)
        self.parent.adopt(self.child)

    def test_proxy_init(self):
        proxy = PTNProxy(self.child, self.parent)
        self.assertEqual(proxy.parent, self.parent)
        self.assertEqual(proxy.ptn, self.child)

    def test_proxy_requires_parent(self):
        with self.assertRaises(ValueError):
            PTNProxy(self.child, None)

    def test_proxy_get_set(self):
        proxy = PTNProxy(self.child, self.parent)
        proxy.set('index', 5)
        self.assertEqual(proxy.get('index'), 5)

        proxy.set('tree', '000001')
        self.assertEqual(proxy.get('tree'), '000001')

    def test_proxy_getitem(self):
        proxy = PTNProxy(self.child, self.parent)
        proxy.set('index', 5)
        self.assertEqual(proxy['index'], 5)

    def test_proxy_fullId(self):
        proxy = PTNProxy(self.child, self.parent)
        self.assertEqual(proxy.fullId, self.child.fullId)

    def test_proxy_level(self):
        proxy = PTNProxy(self.child, self.parent)
        level = proxy.level()
        self.assertEqual(level, 1)  # parent is at level 0

    def test_proxy_equality(self):
        proxy1 = PTNProxy(self.child, self.parent)
        proxy2 = PTNProxy(self.child, self.parent)
        self.assertEqual(proxy1, proxy2)
        self.assertEqual(proxy1, self.child)


if __name__ == '__main__':
    unittest.main()
