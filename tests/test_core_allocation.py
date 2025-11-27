import unittest
from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.resource import Resource
from rodmena_resource_management.core.allocation import Allocation

class TestAllocation(unittest.TestCase):
    def test_allocation_init(self):
        project = Project("prj", "Test Project", "1.0")
        r1 = Resource(project, "r1", "Resource 1", None)
        r2 = Resource(project, "r2", "Resource 2", None)
        
        alloc = Allocation([r1, r2], selectionMode=Allocation.ORDER)
        self.assertEqual(alloc.candidates(0), [r1, r2])
        
    def test_selection_mode(self):
        project = Project("prj", "Test Project", "1.0")
        r1 = Resource(project, "r1", "Resource 1", None)
        r2 = Resource(project, "r2", "Resource 2", None)
        
        # Mock effort
        # r1 has 10 effort, r2 has 5 effort
        r1.data[0].property[('effort', 0)] = 10
        r2.data[0].property[('effort', 0)] = 5
        
        alloc = Allocation([r1, r2], selectionMode=Allocation.MIN_LOADED)
        candidates = alloc.candidates(0)
        self.assertEqual(candidates, [r2, r1]) # r2 has less load
        
        alloc.setSelectionMode('maxloaded')
        candidates = alloc.candidates(0)
        self.assertEqual(candidates, [r1, r2])

if __name__ == '__main__':
    unittest.main()
