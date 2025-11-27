from rodmena_resource_management.core.scenario_data import ScenarioData
from rodmena_resource_management.core.property import AttributeBase

class TaskScenario(ScenarioData):
    def __init__(self, task, scenarioIdx, attributes):
        super().__init__(task, scenarioIdx, attributes)
        self.isRunAway = False
        self.hasDurationSpec = False
        
        # Ensure required attributes exist
        required_attrs = [
             'allocate', 'assignedresources', 'booking', 'charge', 'chargeset', 'complete',
             'competitors', 'criticalness', 'depends', 'duration',
             'effort', 'effortdone', 'effortleft', 'end', 'forward', 'gauge', 'length',
             'maxend', 'maxstart', 'minend', 'minstart', 'milestone', 'pathcriticalness',
             'precedes', 'priority', 'projectionmode', 'responsible',
             'scheduled', 'shifts', 'start', 'status'
        ]
        
        for attr in required_attrs:
            # Access to create them
            # self.property.get(attr, self.scenarioIdx) would trigger creation
            # But we need to be careful about accessing via [] with scenario
            try:
                _ = self.property[(attr, self.scenarioIdx)]
            except ValueError:
                # Attribute might not be defined yet in Project attribute list
                pass

        if not self.property.parent:
            # Handle projection mode inheritance logic
            # Simplified pythonic way
            # In Ruby it switched mode to 1 (Inherited) to set value from project
            mode = AttributeBase.mode()
            AttributeBase.setMode(1)
            
            proj_projection = self.project.scenario(self.scenarioIdx).get('projection') if hasattr(self.project, 'scenario') else None
            if proj_projection:
                 self.property[( 'projectionmode', self.scenarioIdx )] = proj_projection
            
            AttributeBase.setMode(mode)
    
    def readyForScheduling(self):
        # Stub implementation
        return True
