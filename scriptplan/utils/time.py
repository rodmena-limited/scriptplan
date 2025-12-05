import calendar
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional, Union


class TjTime:
    MON_MAX: ClassVar[list[int]] = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    _tz: ClassVar[str] = "UTC"

    def __init__(
        self, t: Optional[Union[datetime, "TjTime", str, list[int], tuple[int, ...], int, float]] = None
    ) -> None:
        if t is None:
            self.time = datetime.now(timezone.utc)
        elif isinstance(t, datetime):
            if t.tzinfo is None:
                # Assume local? Or UTC? TaskJuggler defaults to UTC mostly or system
                # Ruby Time.new creates local time.
                # If we follow strict Ruby behavior, assumes local if no TZ.
                # But here we try to keep things UTC aware internally.
                self.time = t.replace(tzinfo=timezone.utc)  # Simplified assumption: inputs are UTC if naive
            else:
                self.time = t
        elif isinstance(t, TjTime):
            self.time = t.time
        elif isinstance(t, str):
            self.parse(t)
        elif isinstance(t, (list, tuple)):
            # year, month, day, hour, min, sec, usec
            # Ruby Time.mktime interpreted in local time
            # For now assuming UTC for simplicity or explicit timezone handling needed
            dt = datetime(*t[:6])
            self.time = dt.replace(tzinfo=timezone.utc)
        elif isinstance(t, (int, float)):
            self.time = datetime.fromtimestamp(t, tz=timezone.utc)
        else:
            raise ValueError(f"Unknown type for TjTime init: {type(t)}")

    @staticmethod
    def checkTimeZone(zone: str) -> bool:
        if zone == "UTC":
            return True
        # Basic validation not fully implemented against OS db
        return "/" in zone

    @classmethod
    def setTimeZone(cls, zone: str) -> str:
        if not cls.checkTimeZone(zone):
            raise ValueError(f"Illegal time zone {zone}")
        old = cls._tz
        cls._tz = zone
        return old

    @classmethod
    def timeZone(cls) -> str:
        return cls._tz

    def align(self, clock: int) -> "TjTime":
        # clock is seconds
        ts = self.time.timestamp()
        aligned_ts = (int(ts) // clock) * clock
        return TjTime(aligned_ts)

    def utc(self) -> "TjTime":
        return TjTime(self.time.astimezone(timezone.utc))

    def secondsOfDay(self) -> int:
        # Assuming local time relative to set timezone?
        # Simplified: just return UTC seconds of day for now unless we implement full TZ handling
        return self.time.hour * 3600 + self.time.minute * 60 + self.time.second

    def __add__(self, secs: Union[int, float]) -> "TjTime":
        return TjTime(self.time + timedelta(seconds=secs))

    def __sub__(self, arg: Union["TjTime", int, float]) -> Union[float, "TjTime"]:
        if isinstance(arg, TjTime):
            return (self.time - arg.time).total_seconds()
        else:
            return TjTime(self.time - timedelta(seconds=arg))

    def __lt__(self, other: "TjTime") -> bool:
        return self.time < other.time

    def __le__(self, other: "TjTime") -> bool:
        return self.time <= other.time

    def __gt__(self, other: "TjTime") -> bool:
        return self.time > other.time

    def __ge__(self, other: "TjTime") -> bool:
        return self.time >= other.time

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TjTime):
            return NotImplemented
        return self.time == other.time

    def __hash__(self) -> int:
        return hash(self.time)

    def upto(self, endDate: "TjTime", step: int = 1) -> Generator["TjTime", None, None]:
        t = self
        while t < endDate:
            yield t
            t = t + step

    def beginOfHour(self) -> "TjTime":
        return TjTime(self.time.replace(minute=0, second=0, microsecond=0))

    def midnight(self) -> "TjTime":
        return TjTime(self.time.replace(hour=0, minute=0, second=0, microsecond=0))

    def beginOfWeek(self, startMonday: bool) -> "TjTime":
        # startMonday bool
        dt = self.time
        weekday = dt.weekday()  # Mon=0, Sun=6
        # If startMonday=True, we want Monday. weekday is already 0-based from Monday.
        # If startMonday=False (Sunday), we want Sunday.

        days_to_subtract = weekday if startMonday else (weekday + 1) % 7

        start_of_week = dt - timedelta(days=days_to_subtract)
        return TjTime(start_of_week).midnight()

    def beginOfMonth(self) -> "TjTime":
        return TjTime(self.time.replace(day=1, hour=0, minute=0, second=0, microsecond=0))

    def beginOfQuarter(self) -> "TjTime":
        month = self.time.month
        quarter_month = ((month - 1) // 3) * 3 + 1
        return TjTime(self.time.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0))

    def beginOfYear(self) -> "TjTime":
        return TjTime(self.time.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))

    def hoursLater(self, hours: int) -> "TjTime":
        return self + (hours * 3600)

    def sameTimeNextDay(self) -> "TjTime":
        return self + (24 * 3600)  # Simple approx, ignores DST shifts if just adding seconds?
        # Better: add timedelta(days=1) which handles calendar date change
        # return TjTime(self.time + timedelta(days=1))

    def sameTimeNextWeek(self) -> "TjTime":
        return TjTime(self.time + timedelta(weeks=1))

    def sameTimeNextMonth(self) -> "TjTime":
        # Python doesn't have direct month add.
        # Simple logic:
        year = self.time.year
        month = self.time.month + 1
        if month > 12:
            month = 1
            year += 1

        day = self.time.day
        # Clamp day
        _, max_days = calendar.monthrange(year, month)
        day = min(day, max_days)

        return TjTime(self.time.replace(year=year, month=month, day=day))

    def sameTimeNextYear(self) -> "TjTime":
        year = self.time.year + 1
        day = self.time.day
        # Handle leap year feb 29
        if self.time.month == 2 and self.time.day == 29 and not calendar.isleap(year):
            day = 28
        return TjTime(self.time.replace(year=year, day=day))

    def strftime(self, fmt: str) -> str:
        return self.time.strftime(fmt)

    def to_s(self, fmt: Optional[str] = None, tz: Optional[str] = None) -> str:
        if not fmt:
            fmt = "%Y-%m-%d-%H:%M"
        return self.time.strftime(fmt)

    def parse(self, t: str) -> None:
        # format YYYY-MM-DD-HH:MM:SS-ZZZZ?
        # Ruby impl splits by '-'
        parts = t.split("-")
        # Handle various parts length
        # Expected: Year, Month, Day, [Time, [Zone]]
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = 0
        minute = 0
        second = 0

        if len(parts) > 3:
            time_part = parts[3]
            if ":" in time_part:
                time_components = time_part.split(":")
                hour = int(time_components[0])
                minute = int(time_components[1])
                second = int(time_components[2]) if len(time_components) > 2 and time_components[2] else 0

        # Ignore zone for now or handle if present
        self.time = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


class TimeInterval:
    def __init__(self, start: Any, end: Any) -> None:
        self.start = start
        self.end = end
