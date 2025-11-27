from rodmena_resource_management.utils.time import TimeInterval

class Booking:
    def __init__(self, resource, task, intervals=None):
        self.resource = resource
        self.task = task
        self.intervals = intervals if intervals else []
        self.sourceFileInfo = None
        self.overtime = 0
        self.sloppy = 0
    
    def to_s(self):
        # Placeholder string representation
        return f"{self.resource.fullId} -> {self.task.fullId}"
