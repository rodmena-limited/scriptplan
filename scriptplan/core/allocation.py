import random
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

if TYPE_CHECKING:
    pass


class Allocation:
    # Selection modes
    ORDER: ClassVar[int] = 0
    MIN_ALLOCATED: ClassVar[int] = 1
    MIN_LOADED: ClassVar[int] = 2
    MAX_LOADED: ClassVar[int] = 3
    RANDOM: ClassVar[int] = 4

    def __init__(
        self,
        candidates: list[Any],
        selectionMode: int = 1,
        persistent: bool = False,
        mandatory: bool = False,
        atomic: bool = False,
    ) -> None:
        self.candidates_list: list[Any] = candidates
        self.selectionMode = selectionMode
        self.atomic = atomic
        self.persistent = persistent
        self.mandatory = mandatory
        self.shifts: Any = None
        self.lockedResource: Any = None
        self.staticCandidates: Optional[list[Any]] = None

    def setSelectionMode(self, mode_str: str) -> None:
        modes = ["order", "minallocated", "minloaded", "maxloaded", "random"]
        try:
            self.selectionMode = modes.index(mode_str)
        except ValueError as err:
            raise ValueError(f"Unknown selection mode {mode_str}") from err

    def addCandidate(self, candidate: Any) -> None:
        self.candidates_list.append(candidate)

    def onShift(self, sbIdx: int) -> bool:
        if self.shifts:
            return bool(self.shifts.onShift(sbIdx))
        return True

    def candidates(self, scenarioIdx: Optional[int] = None) -> list[Any]:
        if self.staticCandidates:
            return self.staticCandidates

        if scenarioIdx is None or self.selectionMode == self.ORDER:
            return self.candidates_list

        if self.selectionMode == self.RANDOM:
            # Random shuffle
            shuffled = list(self.candidates_list)
            random.shuffle(shuffled)
            return shuffled

        def sort_key(res: Any) -> Union[float, tuple[float, float]]:
            if self.selectionMode == self.MIN_ALLOCATED:
                crit = res.get("criticalness", scenarioIdx) or 0.0
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
