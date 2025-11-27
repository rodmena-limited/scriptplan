class Scoreboard:
    def __init__(self, start, end, granularity, init_val=None):
        self.start = start
        self.end = end
        self.resolution = granularity
        # Calculate size
        # self.size = ((end - start).total_seconds() / granularity) + 1
        # Simplified for now assuming start/end are timestamps or datetime objects handling arithmetic
        try:
             diff = (end - start).total_seconds()
        except AttributeError:
             diff = end - start # Assuming numeric timestamps
             
        self.size = int(diff / granularity) + 1
        self.data = [init_val] * self.size

    def __getitem__(self, idx):
        if 0 <= idx < self.size:
            return self.data[idx]
        return None # Or raise IndexError

    def __setitem__(self, idx, value):
        if 0 <= idx < self.size:
            self.data[idx] = value

    def idxToDate(self, idx):
        # Implement logic
        return None
    
    def dateToIdx(self, date):
        # Implement logic
        return 0
    
    def __iter__(self):
        return iter(self.data)