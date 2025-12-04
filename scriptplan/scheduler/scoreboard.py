import math
from collections.abc import Generator, Iterator
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Union, cast

from scriptplan.utils.time import TimeInterval

# Try to import Cython-optimized functions
try:
    from scriptplan._cython.scoreboard_cy import (
        collect_intervals_fast,
        date_to_idx_fast,
        idx_to_date_fast,
    )

    _USE_CYTHON = True
except ImportError:
    _USE_CYTHON = False


class Scoreboard:
    def __init__(self, start: datetime, end: datetime, granularity: int, init_val: Optional[Any] = None) -> None:
        self.startDate = start
        self.endDate = end
        self.resolution = granularity

        # Calculate size
        # Ruby: ((endDate - startDate) / resolution).ceil + 1
        diff_result = end - start
        diff: float = diff_result.total_seconds()
        self.size = math.ceil(diff / granularity) + 1

        self.sb: list[Any] = []
        self.clear(init_val)

    def clear(self, init_val: Optional[Any] = None) -> None:
        self.sb = [init_val] * self.size

    def idxToDate(self, idx: int, forceIntoProject: bool = False) -> datetime:
        if _USE_CYTHON:
            # Cython handles clamping but not error raising
            if not forceIntoProject and (idx < 0 or idx >= self.size):
                raise IndexError(f"Index {idx} is out of scoreboard range ({self.size - 1})")
            result = idx_to_date_fast(idx, self.startDate, self.resolution, self.size, forceIntoProject, self.endDate)
            if result is not None:
                return cast(datetime, result)

        if forceIntoProject:
            if idx < 0:
                return self.startDate
            if idx >= self.size:
                return self.endDate
        elif idx < 0 or idx >= self.size:
            raise IndexError(f"Index {idx} is out of scoreboard range ({self.size - 1})")

        return self.startDate + timedelta(seconds=idx * self.resolution)

    def dateToIdx(self, date: datetime, forceIntoProject: bool = True) -> int:
        if _USE_CYTHON:
            idx = date_to_idx_fast(date, self.startDate, self.resolution, self.size, forceIntoProject)
            # Cython version handles clamping, but not error raising
            if not forceIntoProject and (idx < 0 or idx >= self.size):
                raise IndexError(f"Date {date} is out of project time range ({self.startDate} - {self.endDate})")
            return int(idx)

        diff_result = date - self.startDate
        diff: float = diff_result.total_seconds()
        idx = int(diff / self.resolution)

        if forceIntoProject:
            if idx < 0:
                return 0
            if idx >= self.size:
                return self.size - 1
        elif idx < 0 or idx >= self.size:
            raise IndexError(f"Date {date} is out of project time range ({self.startDate} - {self.endDate})")

        return idx

    def each(self, startIdx: int = 0, endIdx: Optional[int] = None) -> Generator[Any, None, None]:
        if endIdx is None:
            endIdx = self.size

        if startIdx != 0 or endIdx != self.size:
            for i in range(startIdx, endIdx):
                yield self.sb[i]
        else:
            yield from self.sb

    def each_index(self) -> Generator[int, None, None]:
        yield from range(len(self.sb))

    def collect(self, func: Callable[[Any], Any]) -> None:
        for i in range(len(self.sb)):
            self.sb[i] = func(self.sb[i])

    def __getitem__(self, idx: int) -> Any:
        return self.sb[idx]

    def __setitem__(self, idx: int, value: Any) -> None:
        self.sb[idx] = value

    def get(self, date: datetime) -> Any:
        return self.sb[self.dateToIdx(date)]

    def set(self, date: datetime, value: Any) -> None:
        self.sb[self.dateToIdx(date)] = value

    def collectIntervals(
        self, iv: TimeInterval, minDuration: Union[int, float], predicate: Callable[[Any], bool]
    ) -> list[TimeInterval]:
        startIdx = self.dateToIdx(iv.start)
        endIdx = self.dateToIdx(iv.end)
        sIdx = startIdx
        eIdx = endIdx

        minDurationSlots = int(minDuration / self.resolution)
        if minDurationSlots <= 0:
            minDurationSlots = 1

        startIdx -= minDurationSlots
        if startIdx < 0:
            startIdx = 0
        endIdx += minDurationSlots
        if endIdx > self.size - 1:
            endIdx = self.size - 1

        # Use Cython-optimized version if available
        if _USE_CYTHON:
            return cast(
                list[TimeInterval],
                collect_intervals_fast(
                    self.sb,
                    startIdx,
                    endIdx,
                    sIdx,
                    eIdx,
                    minDurationSlots,
                    self.size,
                    self.startDate,
                    self.resolution,
                    predicate,
                    TimeInterval,
                ),
            )

        intervals: list[TimeInterval] = []
        duration = 0
        start = 0

        idx = startIdx
        while idx <= endIdx:
            # yield/predicate check
            val = self.sb[idx] if idx < len(self.sb) else None  # Boundary check
            if predicate(val) and idx < endIdx:
                if start == 0:
                    start = idx
                duration += 1
            else:
                if duration > 0:
                    if duration >= minDurationSlots:
                        if start < sIdx:
                            start = sIdx
                        current_idx = idx
                        if current_idx > eIdx:
                            current_idx = eIdx

                        intervals.append(TimeInterval(self.idxToDate(start), self.idxToDate(current_idx)))
                    duration = 0
                    start = 0
            idx += 1

        return intervals

    def __iter__(self) -> Iterator[Any]:
        return iter(self.sb)

    def __len__(self) -> int:
        return self.size
