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
        out = f"{self.resource.fullId} "
        first = True
        for iv in self.intervals:
            if first:
                first = False
            else:
                out += ", "
            
            # Assuming iv.start and iv.end are datetime objects
            duration_hours = (iv.end - iv.start).total_seconds() / 3600
            out += f"{iv.start} + {duration_hours}h"
        return out

    def to_tjp(self, taskMode):
        out = f"{self.task.fullId} " if taskMode else f"{self.resource.fullId} "
        first = True
        for iv in self.intervals:
            if first:
                first = False
            else:
                out += ",\n"
            
            duration_hours = (iv.end - iv.start).total_seconds() / 3600
            out += f"{iv.start} + {duration_hours}h"
        
        out += ' { overtime 2 }'
        return out