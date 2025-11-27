from rodmena_resource_management.core.property import PropertyTreeNode
from rodmena_resource_management.core.resource_scenario import ResourceScenario

class Resource(PropertyTreeNode):
    def __init__(self, project, id, name, parent):
        super().__init__(project.resources, id, name, parent)
        # project.addResource(self) # PropertyTreeNode adds to set
        
        scenario_count = self.project.scenarioCount() if hasattr(self.project, 'scenarioCount') else 1
        self.data = [None] * scenario_count
        
        for i in range(scenario_count):
            ResourceScenario(self, i, self._scenarioAttributes[i])

    def book(self, scenarioIdx, sbIdx, task):
        return self.data[scenarioIdx].book(sbIdx, task)

    def query_dashboard(self, query):
        self.dashboard(query)

    def dashboard(self, query):
        # Logic for dashboard report
        pass