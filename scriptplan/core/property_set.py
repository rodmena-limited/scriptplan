"""The set of properties of one kind in a project, and a proxy onto one.

A PropertySet owns the attribute definitions its members may carry and the
map from id to member. A property with a name must be unique in it: two
definitions sharing an id means references resolve to one of them while the
other still occupies the schedule.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from scriptplan.core.attributes import (
    AttributeDefinition,
    IntegerAttribute,
    StringAttribute,
)

if TYPE_CHECKING:
    from scriptplan.core.attributes import AttributeBase
    from scriptplan.core.property_tree_node import PropertyTreeNode

class PropertySet:
    def __init__(self, project: Any, flat_namespace: bool = False) -> None:
        self.project = project
        self.flat_namespace = flat_namespace
        self.attributes: list[AttributeDefinition] = []
        self.attributeDefinitions: dict[str, AttributeDefinition] = {}
        self._properties: list[PropertyTreeNode] = []  # List for order
        self._propertyMap: dict[str, PropertyTreeNode] = {}  # Dict fullId -> PropertyTreeNode

        # Add standard attributes
        # In Ruby: id, name, seqno
        # I will move this logic here from Project.py if I update Project.py later,
        # but for now I can duplicate or rely on Project.py calling _add_standard_attributes.
        # However, cleaner to have it here.
        self.addAttributeType(AttributeDefinition("id", "ID", StringAttribute, False, False, False, ""))
        self.addAttributeType(AttributeDefinition("name", "Name", StringAttribute, False, False, False, ""))
        self.addAttributeType(AttributeDefinition("seqno", "Seq. No", IntegerAttribute, False, False, False, 0))

    def addAttributeType(self, attribute_definition: AttributeDefinition) -> None:
        if self._properties:
            raise RuntimeError("Fatal Error: Attribute types must be defined before properties are added.")

        self.attributes.append(attribute_definition)
        self.attributeDefinitions[attribute_definition.id] = attribute_definition

    def eachAttributeDefinition(self) -> Iterator[AttributeDefinition]:
        return iter(self.attributes)

    def items(self) -> int:
        return len(self._properties)

    def length(self) -> int:
        return len(self._properties)

    def __len__(self) -> int:
        return len(self._properties)

    def __getitem__(self, key: str) -> PropertyTreeNode | None:
        return self._propertyMap.get(key)

    def __setitem__(self, key: str, value: PropertyTreeNode) -> None:
        # Should typically use addProperty
        pass

    def __iter__(self) -> Iterator[PropertyTreeNode]:
        return iter(self._properties)

    def __contains__(self, item: str | PropertyTreeNode) -> bool:
        if isinstance(item, str):
            return item in self._propertyMap
        return item in self._properties

    def empty(self) -> bool:
        return len(self._properties) == 0

    def addProperty(self, property: PropertyTreeNode) -> None:
        # An anonymous property (a nested report with no id) cannot be referred
        # to, so two of them colliding is harmless; only named ones must be unique.
        existing = self._propertyMap.get(property.fullId) if property.id else None
        if existing is not None and existing is not property:
            from scriptplan.core.exceptions import DuplicateDefinitionError

            raise DuplicateDefinitionError(
                f"'{property.fullId}' is defined twice. References to it would resolve to "
                f"one definition while the other still occupies the schedule."
            )
        self._propertyMap[property.fullId] = property
        self._properties.append(property)

    def removeProperty(self, prop: str | PropertyTreeNode) -> PropertyTreeNode | None:
        property_node = self._propertyMap.get(prop) if isinstance(prop, str) else prop

        if not property_node:
            return None

        # Eliminate references
        for p in self._properties:
            p.removeReferences(property_node)

        # Recursively remove children
        # Copy children list to avoid modification during iteration issue
        children = list(property_node.children)
        for child in children:
            self.removeProperty(child)

        if property_node in self._properties:
            self._properties.remove(property_node)
        if property_node.fullId in self._propertyMap:
            del self._propertyMap[property_node.fullId]

        if property_node.parent and property_node in property_node.parent.children:
            property_node.parent.children.remove(property_node)

        return property_node

    def clearProperties(self) -> None:
        self._properties.clear()
        self._propertyMap.clear()

    def index(self) -> None:
        for p in self._properties:
            bsIdcs = p.getBSIndicies()
            bsi = ".".join(map(str, bsIdcs))
            p.force("bsi", bsi)

    def levelSeqNo(self, property_node: PropertyTreeNode) -> int:
        seqNo = 1
        for p in self._properties:
            if not p.parent:
                if p == property_node:
                    return seqNo
                seqNo += 1
        raise ValueError(f"Unknown property {property_node.fullId}")

    def maxDepth(self) -> int:
        md = 0
        for p in self._properties:
            if p.level() > md:
                md = p.level()
        return md + 1

    def topLevelItems(self) -> int:
        items = 0
        for p in self._properties:
            if not p.parent:
                items += 1
        return items

    def to_ary(self) -> list[PropertyTreeNode]:
        return list(self._properties)

    def to_s(self) -> str:
        # PropertyList.new(self).to_s
        return str(self._properties)

    def knownAttribute(self, attrId: str) -> bool:
        return attrId in self.attributeDefinitions

    def hasQuery(self, attrId: str, scenarioIdx: int | None = None) -> bool:
        if not self._properties:
            return False

        property_node = self._properties[0]
        method_name = f"query_{attrId}"

        if hasattr(property_node, method_name):
            return True
        if scenarioIdx is not None and property_node.data and property_node.data[scenarioIdx]:
            # Check scenario object
            return hasattr(property_node.data[scenarioIdx], method_name)
        return False

    def scenarioSpecific(self, attrId: str) -> bool:
        defn = self.attributeDefinitions.get(attrId)
        if defn:
            return defn.scenarioSpecific

        # Check for query method
        if self._properties:
            prop = self._properties[0]
            if prop.data and prop.data[0] and hasattr(prop.data[0], f"query_{attrId}"):
                return True
        return False

    def inheritedFromProject(self, attrId: str) -> bool:
        defn = self.attributeDefinitions.get(attrId)
        return defn.inheritedFromProject if defn else False

    def inheritedFromParent(self, attrId: str) -> bool:
        defn = self.attributeDefinitions.get(attrId)
        return defn.inheritedFromParent if defn else False

    def userDefined(self, attrId: str) -> bool:
        defn = self.attributeDefinitions.get(attrId)
        # userDefined attribute on AttributeDefinition not implemented yet, defaulting to False
        return getattr(defn, "userDefined", False) if defn else False

    def listAttribute(self, attrId: str) -> bool:
        defn = self.attributeDefinitions.get(attrId)
        return defn.isList() if defn else False

    def defaultValue(self, attrId: str) -> Any:
        defn = self.attributeDefinitions.get(attrId)
        return defn.default if defn else None

    def attributeName(self, attrId: str) -> str | None:
        defn = self.attributeDefinitions.get(attrId)
        return defn.name if defn else None

    def attributeType(self, attrId: str) -> type[AttributeBase] | None:
        defn = self.attributeDefinitions.get(attrId)
        return defn.objClass if defn else None


class PTNProxy:
    """Proxy for PropertyTreeNode that represents adopted nodes in their new parental context."""

    def __init__(self, ptn: PropertyTreeNode, parent: PropertyTreeNode | PTNProxy) -> None:
        self._ptn = ptn
        if not parent:
            raise ValueError("Adopted properties must have a parent")
        self._parent = parent
        self._index: int | None = None
        self._tree: str | None = None
        self._level = -1

    @property
    def parent(self) -> PropertyTreeNode | PTNProxy:
        return self._parent

    @property
    def ptn(self) -> PropertyTreeNode:
        return self._ptn

    @property
    def logicalId(self) -> str:
        if self._ptn.propertySet.flat_namespace:
            return self._ptn.id
        else:
            dot_pos = self._ptn.id.rfind(".")
            id = self._ptn.id[dot_pos + 1 :] if dot_pos >= 0 else self._ptn.id
            parent_logical_id = self._parent.logicalId if isinstance(self._parent, PTNProxy) else self._parent.fullId
            return f"{parent_logical_id}.{id}"

    def set(self, attribute: str, val: Any) -> None:
        if attribute == "index":
            self._index = val
        elif attribute == "tree":
            self._tree = val
        else:
            self._ptn.set(attribute, val)

    def get(self, attribute: str) -> Any:
        if attribute == "index":
            return self._index
        elif attribute == "tree":
            return self._tree
        else:
            return self._ptn.get(attribute)

    def __getitem__(self, key: str | tuple[str, int]) -> Any:
        if isinstance(key, tuple):
            attribute, scenarioIdx = key
        else:
            attribute = key
            scenarioIdx = None

        if attribute == "index":
            return self._index
        elif attribute == "tree":
            return self._tree
        else:
            if scenarioIdx is not None:
                return self._ptn[(attribute, scenarioIdx)]
            return self._ptn[attribute]

    def level(self) -> int:
        if self._level >= 0:
            return self._level

        t: PropertyTreeNode | PTNProxy = self
        self._level = 0
        while t.parent is not None:
            t = t.parent
            self._level += 1
        return self._level

    def isChildOf(self, ancestor: PropertyTreeNode | PTNProxy) -> bool:
        parent: PropertyTreeNode | PTNProxy = self
        while parent.parent is not None:
            parent = parent.parent
            if parent == ancestor:
                return True
        return False

    def getIndicies(self) -> list[int]:
        idcs: list[int] = []
        p: PropertyTreeNode | PTNProxy | None = self
        while p is not None:
            parent = p.parent
            idcs.insert(0, p.get("index"))
            p = parent
        return idcs

    def force(self, attribute: str, val: Any) -> None:
        if attribute == "index":
            self._index = val
        elif attribute == "tree":
            self._tree = val
        else:
            self._ptn.force(attribute, val)

    @property
    def fullId(self) -> str:
        return self._ptn.fullId

    @property
    def kids(self) -> list[PropertyTreeNode]:
        return self._ptn.kids()

    @property
    def adoptees(self) -> list[PropertyTreeNode]:
        return self._ptn.adoptees

    @property
    def propertySet(self) -> PropertySet:
        return self._ptn.propertySet

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ptn, name)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PTNProxy):
            return bool(self._ptn == other._ptn)
        return bool(self._ptn == other)
