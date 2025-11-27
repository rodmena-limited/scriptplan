from datetime import datetime, timezone

class TjTime:
    def __init__(self, time=None):
        self.time = time or datetime.now(timezone.utc)
    
    def align(self, seconds):
        return self

    @staticmethod
    def timeZone():
        return "UTC"

class TimeInterval:
    def __init__(self, start, end):
        self.start = start
        self.end = end
