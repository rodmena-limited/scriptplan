import random

class Allocation:
    # Selection modes
    ORDER = 0
    MIN_ALLOCATED = 1
    MIN_LOADED = 2
    MAX_LOADED = 3
    RANDOM = 4

    def __init__(self, candidates, selectionMode=1, persistent=False, mandatory=False, atomic=False):
        self.candidates_list = candidates
        self.selectionMode = selectionMode
        self.atomic = atomic
        self.persistent = persistent
        self.mandatory = mandatory
        self.shifts = None
        self.lockedResource = None
        self.staticCandidates = None

    def setSelectionMode(self, mode_str):
        modes = ['order', 'minallocated', 'minloaded', 'maxloaded', 'random']
        try:
            self.selectionMode = modes.index(mode_str)
        except ValueError:
            raise ValueError(f"Unknown selection mode {mode_str}")

    def addCandidate(self, candidate):
        self.candidates_list.append(candidate)

    def onShift(self, sbIdx):
        if self.shifts:
            return self.shifts.onShift(sbIdx)
        return True

    def candidates(self, scenarioIdx=None):
        if self.staticCandidates:
            return self.staticCandidates
        
        if scenarioIdx is None or self.selectionMode == self.ORDER:
            return self.candidates_list
        
        if self.selectionMode == self.RANDOM:
            # Random shuffle
            shuffled = list(self.candidates_list)
            random.shuffle(shuffled)
            return shuffled
        
        def sort_key(res):
            if self.selectionMode == self.MIN_ALLOCATED:
                crit = res.get('criticalness', scenarioIdx) or 0.0
                if self.persistent:
                    effort = res.bookedEffort(scenarioIdx) or 0
                    return (effort, crit)
                else:
                    return crit
            elif self.selectionMode == self.MIN_LOADED:
                return res.bookedEffort(scenarioIdx) or 0
            elif self.selectionMode == self.MAX_LOADED:
                return -(res.bookedEffort(scenarioIdx) or 0)
            else:
                raise ValueError(f"Unknown selection mode {self.selectionMode}")

        sorted_list = sorted(self.candidates_list, key=sort_key)
        
        if self.selectionMode == self.MIN_ALLOCATED and not self.persistent:
            self.staticCandidates = sorted_list
            
        return sorted_list
