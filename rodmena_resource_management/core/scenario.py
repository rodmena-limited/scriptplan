from rodmena_resource_management.core.property import PropertyTreeNode

class Scenario(PropertyTreeNode):
    def __init__(self, project, id, name, parent):
        super().__init__(project.scenarios, id, name, parent)
        # project.addScenario(self) # PropertyTreeNode handles adding to set
    
    def get(self, attribute_name):
        # Stub for now, use PropertyTreeNode.get
        try:
            return super().get(attribute_name)
        except ValueError:
            return None

class ScenarioList(list):
    # This might be deprecated if we use PropertySet for scenarios
    pass