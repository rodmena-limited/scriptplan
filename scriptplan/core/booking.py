from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from scriptplan.core.resource import Resource
    from scriptplan.core.task import Task


class Booking:
    def __init__(self, resource: "Resource", task: "Task", intervals: Optional[list[Any]] = None) -> None:
        self.resource = resource
        self.task = task
        self.intervals: list[Any] = intervals if intervals else []
        self.sourceFileInfo: Any = None
        self.overtime: int = 0
        self.sloppy: int = 0

    def to_s(self) -> str:
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

    def to_tjp(self, taskMode: bool) -> str:
        out = f"{self.task.fullId} " if taskMode else f"{self.resource.fullId} "
        first = True
        for iv in self.intervals:
            if first:
                first = False
            else:
                out += ",\n"

            duration_hours = (iv.end - iv.start).total_seconds() / 3600
            out += f"{iv.start} + {duration_hours}h"

        out += " { overtime 2 }"
        return out
