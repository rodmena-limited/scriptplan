class Scenario:
    def __init__(self, project, id, name, parent):
        self.project = project
        self.id = id
        self.name = name
        self.parent = parent
        self.sequenceNo = 1
    
    def get(self, attribute_name):
        return None

class ScenarioList(list):
    def addProperty(self, scenario):
        self.append(scenario)
    
    @property
    def items(self):
        return len(self)
