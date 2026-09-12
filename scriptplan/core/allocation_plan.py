"""What a task is allowed to book, and under what conditions.

`allocate` carries more than a list of names. Each entry may be mandatory (the
task makes no progress without it), persistent (once a resource is chosen it is
kept for the rest of the task), or carry alternatives to fall back on. Those
options belong to the resource they follow, so

    allocate a { mandatory }, b

makes `a` mandatory and leaves `b` optional.

This module turns the parsed form into that structure once, so the scheduler
does not re-derive it from a list-or-dict-or-string at every call site.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

__all__ = ["Allocation", "AllocationPlan"]


class Allocation:
    """One resource a task may book, with the options attached to it."""

    __slots__ = ("alternatives", "locked", "mandatory", "persistent", "resource", "resource_id", "select")

    def __init__(
        self,
        resource_id: str,
        resource: Any | None = None,
        mandatory: bool = False,
        persistent: bool = False,
        alternatives: list[Any] | None = None,
        select: str | None = None,
    ) -> None:
        self.resource_id = resource_id
        self.resource = resource
        self.mandatory = mandatory
        self.persistent = persistent
        self.alternatives = alternatives or []
        self.select = select
        self.locked: Any | None = None

    def candidates(self) -> list[Any]:
        """The resources that could satisfy this allocation, best first."""
        if self.locked is not None:
            return [self.locked]
        found = [self.resource] if self.resource is not None else []
        found.extend(r for r in self.alternatives if r is not None)
        return found

    def __repr__(self) -> str:
        marks = "".join(
            mark for mark, on in (("!", self.mandatory), ("=", self.persistent)) if on
        )
        return f"Allocation({self.resource_id}{marks})"


class AllocationPlan:
    """Every allocation on one task, in declaration order."""

    __slots__ = ("allocations",)

    def __init__(self, allocations: list[Allocation] | None = None) -> None:
        self.allocations: list[Allocation] = allocations or []

    def __bool__(self) -> bool:
        return bool(self.allocations)

    def __iter__(self) -> Any:
        return iter(self.allocations)

    def __len__(self) -> int:
        return len(self.allocations)

    @property
    def mandatory(self) -> list[Allocation]:
        return [a for a in self.allocations if a.mandatory]

    def resources(self) -> list[Any]:
        """Every resource that could be booked, without duplicates."""
        found: list[Any] = []
        for allocation in self.allocations:
            for candidate in allocation.candidates():
                if candidate is not None and candidate not in found:
                    found.append(candidate)
        return found

    def reset(self) -> None:
        for allocation in self.allocations:
            allocation.locked = None

    # -- construction ------------------------------------------------------

    @classmethod
    def read(cls, value: Any, resolve: Any) -> AllocationPlan:
        """Build a plan from the parsed `allocate` attribute.

        ``resolve`` maps a resource id to a Resource. Older shapes -- a bare
        list of names, or a dict of resources plus shared options -- are still
        understood, so a caller that builds a project in Python rather than
        from a file keeps working.
        """
        allocations: list[Allocation] = []
        for entry in cls._entries(value):
            resource_id = entry.get("resource")
            if resource_id is None:
                continue
            allocations.append(
                Allocation(
                    resource_id=str(resource_id),
                    resource=resolve(resource_id),
                    mandatory=bool(entry.get("mandatory")),
                    persistent=bool(entry.get("persistent")),
                    alternatives=[resolve(name) for name in entry.get("alternative", [])],
                    select=entry.get("select"),
                )
            )
        return cls(allocations)

    @staticmethod
    def _entries(value: Any) -> Iterable[dict[str, Any]]:
        """Normalise every shape `allocate` has ever been stored in."""
        if not value:
            return []
        data = value
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            data = data[0]

        if isinstance(data, dict):
            if "allocations" in data:
                return [e for e in data["allocations"] if isinstance(e, dict)]
            # Legacy: {"resources": [...], "options": {...}} with options shared
            # across every resource in the statement.
            options = data.get("options", {}) or {}
            shared = {
                key: options[key]
                for key in ("mandatory", "persistent", "alternative", "select")
                if key in options
            }
            return [{"resource": name, **shared} for name in data.get("resources", [])]

        if isinstance(data, list):
            entries: list[dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    # Repeated `allocate` statements accumulate, so the
                    # attribute holds one wrapper per statement.
                    if "allocations" in item:
                        entries.extend(e for e in item["allocations"] if isinstance(e, dict))
                    elif "resources" in item:
                        options = item.get("options", {}) or {}
                        shared = {
                            key: options[key]
                            for key in ("mandatory", "persistent", "alternative", "select")
                            if key in options
                        }
                        entries.extend({"resource": name, **shared} for name in item["resources"])
                    else:
                        entries.append(item)
                elif isinstance(item, str):
                    entries.append({"resource": item})
                elif item is not None:
                    entries.append({"resource": getattr(item, "id", item)})
            return entries

        if isinstance(data, str):
            return [{"resource": data}]
        return [{"resource": getattr(data, "id", data)}]
