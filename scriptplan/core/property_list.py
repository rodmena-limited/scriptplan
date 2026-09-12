"""An ordered list of properties, and the criteria a report sorts it by.

Sorting is one stable pass per criterion, least significant first, so a
descending pass is a plain reverse. Building one composite key instead means
inverting values to reverse them, which does nothing to a string, and standing
in for a missing value with something comparable to the others, which raises
as soon as one row lacks it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Callable

from scriptplan.core.property_set import PropertySet, PTNProxy

if TYPE_CHECKING:
    from scriptplan.core.property_tree_node import PropertyTreeNode

def _sort_by_id(item: Any, _scenario: int) -> Any:
    return getattr(item, "fullId", None)


def _sort_by_tree(item: Any, _scenario: int) -> Any:
    return getattr(item, "fullId", None)


def _sort_by_alert(item: Any, _scenario: int) -> int:
    """The highest journal alert level recorded against this property.

    `alert` is a report column rather than a property attribute, so it is
    computed here instead of being looked up and rejected as unknown.
    """
    project = getattr(item, "project", None)
    journal = getattr(project, "attributes", {}).get("journal") if project is not None else None
    if journal is None:
        return 0
    try:
        entries = list(journal.entries())
    except Exception:
        return 0
    highest = 0
    for entry in entries:
        node = getattr(entry, "property", None) or getattr(entry, "task", None)
        while node is not None:
            if node is item:
                highest = max(highest, int(getattr(entry, "alert_level", 0)))
                break
            node = getattr(node, "parent", None)
    return highest


#: Sort criteria a report computes rather than reading from the property.
COMPUTED_SORT_CRITERIA: dict[str, Callable[[Any, int], Any]] = {
    "id": _sort_by_id,
    "tree": _sort_by_tree,
    "alert": _sort_by_alert,
}


class PropertyList:
    """List of PropertyTreeNodes with multi-level sorting support.

    All nodes in the list must belong to the same PropertySet.
    Sorting can use multiple criteria with ascending/descending direction.
    """

    def __init__(
        self, arg: PropertySet | PropertyList | list[PropertyTreeNode | PTNProxy], copyItems: bool = True
    ) -> None:
        if isinstance(arg, PropertySet):
            self._items: list[PropertyTreeNode | PTNProxy] = list(arg._properties) if copyItems else []
            self._propertySet: PropertySet | None = arg
            self._query: Any | None = None
            self.resetSorting()
            self.addSortingCriteria("seqno", True, -1)
            self.sort()
        elif isinstance(arg, PropertyList):
            self._items = list(arg._items) if copyItems else []
            self._propertySet = arg._propertySet
            self._query = arg._query.copy() if arg._query else None
            self._sortingLevels: int = arg._sortingLevels
            self._sortingCriteria: list[str] = list(arg._sortingCriteria)
            self._sortingUp: list[bool] = list(arg._sortingUp)
            self._scenarioIdx: list[int] = list(arg._scenarioIdx)
        else:
            # Assume it's a list/iterable
            self._items = list(arg) if copyItems else []
            self._propertySet = arg[0].propertySet if arg else None
            self._query = None
            self.resetSorting()

    @property
    def propertySet(self) -> PropertySet | None:
        return self._propertySet

    @property
    def query(self) -> Any | None:
        return self._query

    @query.setter
    def query(self, value: Any | None) -> None:
        self._query = value

    @property
    def sortingLevels(self) -> int:
        return self._sortingLevels

    @property
    def sortingCriteria(self) -> list[str]:
        return self._sortingCriteria

    @property
    def sortingUp(self) -> list[bool]:
        return self._sortingUp

    @property
    def scenarioIdx(self) -> list[int]:
        return self._scenarioIdx

    def includeAdopted(self) -> None:
        adopted: list[PropertyTreeNode | PTNProxy] = []
        for p in self._items:
            for ap in p.adoptees:
                adopted.extend(self._includeAdoptedR(ap, p))
        self.append(adopted)

    def _includeAdoptedR(
        self, property: PropertyTreeNode, parent: PropertyTreeNode | PTNProxy
    ) -> list[PTNProxy]:
        parentProxy = PTNProxy(property, parent)
        adopted: list[PTNProxy] = [parentProxy]

        for p in property.kids():
            adopted.extend(self._includeAdoptedR(p, parentProxy))

        return adopted

    def checkForDuplicates(self, sourceFileInfo: Any | None = None) -> None:
        ptns: dict[PropertyTreeNode, PropertyTreeNode | PTNProxy] = {}
        for i in self._items:
            ptn = i.ptn if isinstance(i, PTNProxy) else i
            if ptn in ptns:
                other = ptns[ptn]
                raise ValueError(
                    f"An adopted property is included as {i.logicalId if hasattr(i, 'logicalId') else i.fullId} and "
                    f"as {other.logicalId if hasattr(other, 'logicalId') else other.fullId}. "
                    "Please use stronger filtering to avoid including the property more than once!"
                )
            ptns[ptn] = i

    def __contains__(self, node: PropertyTreeNode | PTNProxy) -> bool:
        target_ptn = node.ptn if isinstance(node, PTNProxy) else node
        for p in self._items:
            p_ptn = p.ptn if isinstance(p, PTNProxy) else p
            if p_ptn == target_ptn:
                return True
        return False

    def __getitem__(
        self, key: int | PropertyTreeNode | PTNProxy
    ) -> PropertyTreeNode | PTNProxy | None:
        if isinstance(key, int):
            return self._items[key]
        # Node lookup
        target_ptn = key.ptn if isinstance(key, PTNProxy) else key
        for n in self._items:
            n_ptn = n.ptn if isinstance(n, PTNProxy) else n
            if n_ptn == target_ptn:
                return n
        return None

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[PropertyTreeNode | PTNProxy]:
        return iter(self._items)

    def to_ary(self) -> list[PropertyTreeNode | PTNProxy]:
        return list(self._items)

    def setSorting(self, modes: list[tuple[str, bool, int]]) -> None:
        self.resetSorting()
        for mode in modes:
            self.addSortingCriteria(*mode)

    def resetSorting(self) -> None:
        self._sortingLevels = 0
        self._sortingCriteria = []
        self._sortingUp = []
        self._scenarioIdx = []

    def append(
        self,
        items: list[PropertyTreeNode | PTNProxy] | PropertyList | PropertyTreeNode | PTNProxy,
    ) -> None:
        if isinstance(items, (list, PropertyList)):
            for node in items:
                if node.propertySet != self._propertySet:
                    raise ValueError("All nodes must belong to the same PropertySet.")
            self._items.extend(items)
            if len(self._items) != len({id(x) for x in self._items}):
                raise ValueError("Duplicate items")
        else:
            self._items.append(items)
        self.sort()

    def treeMode(self) -> bool:
        return self._sortingLevels > 0 and self._sortingCriteria[0] == "tree"

    def sort(self) -> None:
        if self.treeMode():
            sc = self._sortingCriteria.pop(0)
            su = self._sortingUp.pop(0)
            si = self._scenarioIdx.pop(0)
            self._sortingLevels -= 1

            self._sortInternal()
            self.index()
            self._indexTree()

            self._sortingCriteria.insert(0, sc)
            self._sortingUp.insert(0, su)
            self._scenarioIdx.insert(0, si)
            self._sortingLevels += 1

            self._sortInternal()
        else:
            self._sortInternal()
        self.index()

    def itemIndex(self, item: PropertyTreeNode | PTNProxy) -> int | None:
        try:
            return self._items.index(item)
        except ValueError:
            return None

    def index(self) -> None:
        for i, p in enumerate(self._items, 1):
            p.force("index", i)

    def __str__(self) -> str:
        res = "Sorting: "
        for i in range(self._sortingLevels):
            direction = "up" if self._sortingUp[i] else "down"
            res += f"{self._sortingCriteria[i]}/{direction}/{self._scenarioIdx[i]}, "
        res += f"\n{len(self._items)} properties:"
        for item in self._items:
            res += f"{item.get('id')}: {item.get('name')}\n"
        return res

    def addSortingCriteria(self, criteria: str, up: bool, scIdx: int) -> None:
        if self._propertySet is None:
            raise ValueError("PropertySet cannot be None")

        if (
            criteria not in COMPUTED_SORT_CRITERIA
            and not self._propertySet.knownAttribute(criteria)
            and not self._propertySet.hasQuery(criteria, scIdx)
        ):
            raise ValueError(
                f"Unknown attribute '{criteria}' used for sorting criterium. Sort by a "
                f"property attribute, or by one of: {', '.join(sorted(COMPUTED_SORT_CRITERIA))}."
            )

        if self._propertySet.scenarioSpecific(criteria):
            if scIdx < 0 or (
                hasattr(self._propertySet.project, "scenario") and self._propertySet.project.scenario(scIdx) is None
            ):
                # Allow if scIdx is valid or we can't verify
                pass
        else:
            scIdx = -1

        self._sortingCriteria.append(criteria)
        self._sortingUp.append(up)
        self._scenarioIdx.append(scIdx)
        self._sortingLevels += 1

    def _indexTree(self) -> None:
        for property in self._items:
            treeIdcs = property.getIndicies() if isinstance(property, PTNProxy) else self._getIndicies(property)

            tree = ""
            for idx in treeIdcs:
                tree += str(idx).rjust(6, "0")
            property.force("tree", tree)

    def _getIndicies(self, property: PropertyTreeNode) -> list[int]:
        idcs: list[int] = []
        p: PropertyTreeNode | None = property
        while p is not None:
            parent = p.parent
            idx = p.get("index")
            idcs.insert(0, idx)
            p = parent
        return idcs

    def _sortInternal(self) -> None:
        """Order the list by each criterion in turn.

        Sorting happens one criterion at a time, least significant first, so a
        descending pass is a plain reverse of a stable sort. Building a single
        composite key instead means negating values to invert them, which does
        nothing to a string, and mixing numbers with the empty string stands in
        for a missing value, which raises as soon as one row lacks it.
        """
        for i in reversed(range(self._sortingLevels)):
            criteria = self._sortingCriteria[i]
            scIdx = self._scenarioIdx[i]
            ascending = self._sortingUp[i]
            def key_for(item: Any, c: str = criteria, s: int = scIdx) -> tuple[int, Any]:
                return self._sortKey(item, c, s)

            self._items.sort(key=key_for, reverse=not ascending)

    def _sortKey(self, item: PropertyTreeNode | PTNProxy, criteria: str, scIdx: int) -> tuple[int, Any]:
        """A comparable key for one criterion.

        The leading number separates rows that have no value from rows that do,
        so a missing value sorts to one end instead of being compared against a
        value of another type.
        """
        value = self._sortValue(item, criteria, scIdx)
        if value is None:
            return (1, "")
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, (int, float)):
            return (0, value)
        if isinstance(value, str):
            return (0, value)
        return (0, str(value))

    def _sortValue(self, item: PropertyTreeNode | PTNProxy, criteria: str, scIdx: int) -> Any:
        if self._query and criteria != "tree":
            self._query.scenarioIdx = None if scIdx < 0 else scIdx
            self._query.attributeId = criteria
            self._query.property = item
            self._query.process()
            return self._query.to_sort()
        if criteria in COMPUTED_SORT_CRITERIA:
            return COMPUTED_SORT_CRITERIA[criteria](item, scIdx)
        try:
            if scIdx < 0:
                return item.get(criteria)
            return item.get(criteria, scIdx)  # type: ignore[call-arg]
        except (ValueError, KeyError, AttributeError):
            return None

    def delete_if(self, func: Callable[[PropertyTreeNode | PTNProxy], bool]) -> None:
        to_remove = [i for i in self._items if func(i)]
        for i in to_remove:
            self._items.remove(i)

    def each(self, func: Callable[[PropertyTreeNode | PTNProxy], None]) -> None:
        for item in self._items:
            func(item)
