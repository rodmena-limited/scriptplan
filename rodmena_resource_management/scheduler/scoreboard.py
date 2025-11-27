import math
from rodmena_resource_management.utils.time import TimeInterval

class Scoreboard:
    def __init__(self, start, end, granularity, init_val=None):
        self.startDate = start
        self.endDate = end
        self.resolution = granularity
        
        # Calculate size
        # Ruby: ((endDate - startDate) / resolution).ceil + 1
        diff = (end - start).total_seconds() if hasattr(end - start, 'total_seconds') else (end - start)
        self.size = math.ceil(diff / granularity) + 1
        
        self.clear(init_val)

    def clear(self, init_val=None):
        self.sb = [init_val] * self.size

    def idxToDate(self, idx, forceIntoProject=False):
        if forceIntoProject:
            if idx < 0:
                return self.startDate
            if idx >= self.size:
                return self.endDate
        elif idx < 0 or idx >= self.size:
            raise IndexError(f"Index {idx} is out of scoreboard range ({self.size - 1})")
        
        from datetime import timedelta
        return self.startDate + timedelta(seconds=idx * self.resolution)

    def dateToIdx(self, date, forceIntoProject=True):
        diff = (date - self.startDate).total_seconds() if hasattr(date - self.startDate, 'total_seconds') else (date - self.startDate)
        idx = int(diff / self.resolution)
        
        if forceIntoProject:
            if idx < 0: return 0
            if idx >= self.size: return self.size - 1
        elif idx < 0 or idx >= self.size:
            raise IndexError(f"Date {date} is out of project time range ({self.startDate} - {self.endDate})")
        
        return idx

    def each(self, startIdx=0, endIdx=None):
        if endIdx is None:
            endIdx = self.size
        
        if startIdx != 0 or endIdx != self.size:
            for i in range(startIdx, endIdx):
                yield self.sb[i]
        else:
            for entry in self.sb:
                yield entry

    def each_index(self):
        for i in range(len(self.sb)):
            yield i

    def collect(self, func):
        for i in range(len(self.sb)):
            self.sb[i] = func(self.sb[i])

    def __getitem__(self, idx):
        return self.sb[idx]

    def __setitem__(self, idx, value):
        self.sb[idx] = value

    def get(self, date):
        return self.sb[self.dateToIdx(date)]

    def set(self, date, value):
        self.sb[self.dateToIdx(date)] = value

    def collectIntervals(self, iv, minDuration, predicate):
        startIdx = self.dateToIdx(iv.start)
        endIdx = self.dateToIdx(iv.end)
        sIdx = startIdx
        eIdx = endIdx
        
        minDurationSlots = int(minDuration / self.resolution)
        if minDurationSlots <= 0:
            minDurationSlots = 1
            
        startIdx -= minDurationSlots
        if startIdx < 0: startIdx = 0
        endIdx += minDurationSlots
        if endIdx > self.size - 1: endIdx = self.size - 1
        
        intervals = []
        duration = 0
        start = 0
        
        idx = startIdx
        while idx <= endIdx:
            # yield/predicate check
            val = self.sb[idx] if idx < len(self.sb) else None # Boundary check
            if predicate(val) and idx < endIdx:
                if start == 0:
                    start = idx
                duration += 1
            else:
                if duration > 0:
                    if duration >= minDurationSlots:
                        if start < sIdx: start = sIdx
                        current_idx = idx
                        if current_idx > eIdx: current_idx = eIdx
                        
                        intervals.append(TimeInterval(self.idxToDate(start), self.idxToDate(current_idx)))
                    duration = 0
                    start = 0
            idx += 1
            
        return intervals

    def __iter__(self):
        return iter(self.sb)
    
    def __len__(self):
        return self.size
