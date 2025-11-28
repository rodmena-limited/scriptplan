from scriptplan.core.property import PropertyTreeNode

class Scenario(PropertyTreeNode):
    def __init__(self, project, id, name, parent):
        super().__init__(project.scenarios, id, name, parent)
