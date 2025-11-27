from rodmena_resource_management.utils.message_handler import MessageHandler

class ScenarioData:
    def __init__(self, property_node, idx, attributes):
        self.property = property_node
        self.project = property_node.project
        self.scenarioIdx = idx
        self.attributes = attributes
        self.messageHandler = MessageHandler() # Should be singleton in real app

        # Register the scenario with the property.
        if self.property.data is None:
             # Initialize if not present, assuming it's a list
             # In PropertyTreeNode we initialized it as list of None
             self.property.data = [None] * (self.project.scenarioCount() if hasattr(self.project, 'scenarioCount') else 1)
        
        # Ensure list is big enough
        while len(self.property.data) <= idx:
            self.property.data.append(None)

        self.property.data[idx] = self

    def deep_clone(self):
        return self

    def a(self, attributeName):
        return self.attributes[attributeName].get()

    def error(self, id, text, sourceFileInfo=None, property_node=None):
        # Delegating to message handler
        # Simplified context passing
        self.messageHandler.error(id, text, sourceFileInfo or self.property.sourceFileInfo)

    def warning(self, id, text, sourceFileInfo=None, property_node=None):
        self.messageHandler.warning(id, text, sourceFileInfo or self.property.sourceFileInfo)
    
    def info(self, id, text, sourceFileInfo=None, property_node=None):
        # Assuming info exists
        print(f"INFO: {text}")
