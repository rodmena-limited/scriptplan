"""One property: a task, a resource, a shift, an account or a report.

Properties form a tree. A node holds its own attribute values, per scenario
where the definition says so, and inherits the rest from its container once,
when the model is built, rather than walking up the tree on every read.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Optional, Union

from scriptplan.core.attributes import (
    AttributeBase,
    AttributeDefinition,
    AttributeOverwrite,
    deep_clone,
)
from scriptplan.core.property_set import PropertySet
from scriptplan.utils.message_handler import MessageHandler

class PropertyTreeNode(MessageHandler):
    def __init__(
        self, property_set: PropertySet, id: Optional[str], name: str, parent: Optional["PropertyTreeNode"]
    ) -> None:
        self.propertySet = property_set
        self.project = property_set.project
        self.parent = parent
        self.data: Optional[Any] = None

        self._attributes: dict[str, AttributeBase] = {}
        self._scenarioAttributes: list[dict[str, AttributeBase]] = []

        scenario_count = self.project.scenarioCount() if hasattr(self.project, "scenarioCount") else 1
        self._scenarioAttributes = [{} for _ in range(scenario_count)]

        if id is None:
            tag = self.__class__.__name__
            id = f"_{tag}_{self.propertySet.items() + 1}"
            if not self.propertySet.flat_namespace and parent:
                id = f"{parent.fullId}.{id}"

        if not self.propertySet.flat_namespace and id and "." in id:
            parent_id = id.rsplit(".", 1)[0]
            if not self.parent:
                self.parent = self.propertySet[parent_id]
            self.subId: str = id.rsplit(".", 1)[1]
        else:
            self.subId = id

        self.id: str = id
        self.name: str = name
        self.sourceFileInfo: Optional[Any] = None
        self.sequenceNo: int = self.propertySet.items() + 1
        self.children: list[PropertyTreeNode] = []
        self.adoptees: list[PropertyTreeNode] = []
        self.stepParents: list[PropertyTreeNode] = []

        self.set("id", self.fullId)
        self.set("name", name)
        self.set("seqno", self.sequenceNo)

        if self.parent:
            self.parent.addChild(self)

        self.propertySet.addProperty(self)

    @property
    def fullId(self) -> str:
        res = self.subId
        if not self.propertySet.flat_namespace:
            t: PropertyTreeNode = self
            while t.parent is not None:
                t = t.parent
                res = f"{t.subId}.{res}"
        return res

    def addChild(self, child: "PropertyTreeNode") -> None:
        self.children.append(child)

    def ptn(self) -> "PropertyTreeNode":
        return self

    def adopt(self, property_node: "PropertyTreeNode") -> None:
        if self == property_node:
            self.error("adopt_self", "A property cannot adopt itself")

        # Check for duplicates logic... simplified

        self.adoptees.append(property_node)
        property_node.getAdopted(self)

    def getAdopted(self, property_node: "PropertyTreeNode") -> None:
        if property_node not in self.stepParents:
            self.stepParents.append(property_node)

    def parents(self) -> list["PropertyTreeNode"]:
        p = [self.parent] if self.parent else []
        return p + self.stepParents

    def backupAttributes(self) -> list[Any]:
        # Shallow copy of attributes dictionaries
        return [self._attributes.copy(), [sa.copy() for sa in self._scenarioAttributes]]

    def restoreAttributes(self, backup: list[Any]) -> None:
        self._attributes, self._scenarioAttributes = backup

    def removeReferences(self, property_node: "PropertyTreeNode") -> None:
        if property_node in self.children:
            self.children.remove(property_node)
        if property_node in self.adoptees:
            self.adoptees.remove(property_node)
        if property_node in self.stepParents:
            self.stepParents.remove(property_node)

    def level(self) -> int:
        lvl = 0
        t: PropertyTreeNode = self
        while t.parent is not None:
            lvl += 1
            t = t.parent
        return lvl

    def getBSIndicies(self) -> list[int]:
        idcs: list[int] = []
        p: Optional[PropertyTreeNode] = self
        while p:
            parent = p.parent
            idx = parent.levelSeqNo(p) if parent else self.propertySet.levelSeqNo(p)
            idcs.insert(0, idx)
            p = parent
        return idcs

    def levelSeqNo(self, node: "PropertyTreeNode") -> int:
        try:
            return self.children.index(node) + 1
        except ValueError as err:
            raise ValueError(f"Node {node.fullId} is not a child of {self.fullId}") from err

    def inheritAttributes(self) -> None:
        # Inherit non-scenario-specific values
        for attrDef in self.propertySet.attributes:
            if attrDef.scenarioSpecific or not attrDef.inheritedFromParent:
                continue

            aId = attrDef.id
            if self.parent:
                # If parent provided or inherited
                parent_attr = self.parent._get_attribute(aId)
                if parent_attr.provided or parent_attr.inherited:
                    my_attr = self._get_attribute(aId)
                    # Only inherit if not already provided explicitly
                    if not my_attr.provided:
                        my_attr.inherit(parent_attr.get())
            elif attrDef.inheritedFromProject:
                # Check project
                if aId in self.project.attributes:
                    val = self.project[aId]
                    if val is not None:
                        my_attr = self._get_attribute(aId)
                        # Only inherit if not already provided explicitly
                        if not my_attr.provided:
                            my_attr.inherit(val)

        # Inherit scenario-specific values
        for attrDef in self.propertySet.attributes:
            if not attrDef.scenarioSpecific or not attrDef.inheritedFromParent:
                continue

            scenario_count = self.project.scenarioCount() if hasattr(self.project, "scenarioCount") else 1
            for scenarioIdx in range(scenario_count):
                if self.parent:
                    parent_attr = self.parent._get_scenario_attribute(attrDef.id, scenarioIdx)
                    if parent_attr.provided or parent_attr.inherited:
                        my_attr = self._get_scenario_attribute(attrDef.id, scenarioIdx)
                        # Only inherit if not already provided explicitly
                        if not my_attr.provided:
                            my_attr.inherit(parent_attr.get())
                else:
                    if attrDef.inheritedFromProject:
                        val = self.project[attrDef.id]
                        # Project attributes usually not scenario specific or stored differently?
                        # Ruby: if @project[attrDef.id] && ...
                        # If project has it, inherit.
                        if val is not None:
                            my_attr = self._get_scenario_attribute(attrDef.id, scenarioIdx)
                            # Only inherit if not already provided explicitly
                            if not my_attr.provided:
                                my_attr.inherit(val)

    def ancestors(self, includeStepParents: bool = False) -> list["PropertyTreeNode"]:
        nodes: list[PropertyTreeNode] = []
        if includeStepParents:
            for p in self.parents():
                nodes.append(p)
                nodes.extend(p.ancestors(True))
        else:
            n: PropertyTreeNode = self
            while n.parent is not None:
                n = n.parent
                nodes.append(n)
        return nodes

    def root(self) -> "PropertyTreeNode":
        n: PropertyTreeNode = self
        while n.parent:
            n = n.parent
        return n

    def provided(self, attributeId: str, scenarioIdx: Optional[int] = None) -> bool:
        if scenarioIdx is not None:
            if attributeId not in self._scenarioAttributes[scenarioIdx]:
                return False
            return bool(self._scenarioAttributes[scenarioIdx][attributeId].provided)
        else:
            if attributeId not in self._attributes:
                return False
            return bool(self._attributes[attributeId].provided)

    def inherited(self, attributeId: str, scenarioIdx: Optional[int] = None) -> bool:
        if scenarioIdx is not None:
            if attributeId not in self._scenarioAttributes[scenarioIdx]:
                return False
            return bool(self._scenarioAttributes[scenarioIdx][attributeId].inherited)
        else:
            if attributeId not in self._attributes:
                return False
            return bool(self._attributes[attributeId].inherited)

    def checkFailsAndWarnings(self) -> None:
        # Placeholder for logic
        pass

    def force(self, attribute_id: str, value: Any) -> None:
        attr = self._get_attribute(attribute_id)
        attr.set(value)

    def set(self, attribute_id: str, value: Any) -> None:
        attr = self._get_attribute(attribute_id)
        if attr.type.scenarioSpecific:
            raise ValueError(f"Attribute {attribute_id} is scenario specific, use []=")
        attr.set(value)

    def _get_attribute(self, attribute_id: str) -> AttributeBase:
        if attribute_id in self._attributes:
            return self._attributes[attribute_id]

        defn = self.attributeDefinition(attribute_id)
        if not defn:
            raise ValueError(f"Unknown attribute {attribute_id}")

        if defn.scenarioSpecific:
            raise ValueError(f"Attribute {attribute_id} is scenario specific")

        attr = defn.objClass(self, defn, self)
        self._attributes[attribute_id] = attr
        return attr

    def _get_scenario_attribute(self, attribute_id: str, scenario_idx: int) -> AttributeBase:
        if attribute_id in self._scenarioAttributes[scenario_idx]:
            return self._scenarioAttributes[scenario_idx][attribute_id]

        defn = self.attributeDefinition(attribute_id)
        if not defn:
            raise ValueError(f"Unknown attribute {attribute_id}")

        if not defn.scenarioSpecific:
            raise ValueError(f"Attribute {attribute_id} is not scenario specific")

        scenario_obj = self.data[scenario_idx] if self.data else None
        attr = defn.objClass(self, defn, scenario_obj if scenario_obj else self)
        self._scenarioAttributes[scenario_idx][attribute_id] = attr
        return attr

    def attributeDefinition(self, attribute_id: str) -> Optional[AttributeDefinition]:
        return self.propertySet.attributeDefinitions.get(attribute_id)

    def get(self, attribute_id: str, scenarioIdx: Optional[int] = None) -> Any:
        """Read an attribute, by scenario when it has one.

        Asking for a scenario of an attribute that has no per-scenario value
        (``id``, ``name``, ``note``) returns the single value it does have,
        rather than raising. Callers that iterate over report columns cannot
        know in advance which attributes are scenario-specific, and a raise
        there is how a column ends up rendering "-".
        """
        if scenarioIdx is not None:
            definition = self.propertySet.attributeDefinitions.get(attribute_id)
            if definition is not None and not definition.scenarioSpecific:
                return self._get_attribute(attribute_id).get()
            attr = self._get_scenario_attribute(attribute_id, scenarioIdx)
        else:
            attr = self._get_attribute(attribute_id)
        return attr.get()

    def __getitem__(self, key: Union[str, tuple[str, int]]) -> Any:
        if isinstance(key, tuple):
            attribute_id, scenario = key
            attr = self._get_scenario_attribute(attribute_id, scenario)
            return attr.get()
        else:
            return self.get(key)

    def __setitem__(self, key: Union[str, tuple[str, int]], value: Any) -> None:
        if isinstance(key, tuple):
            attribute_id, scenario = key
            attr = self._get_scenario_attribute(attribute_id, scenario)
            attr.set(value)
        else:
            self.set(key, value)

    def all(self) -> list["PropertyTreeNode"]:
        res = [self]
        for child in self.kids():
            res.extend(child.all())
        return res

    def kids(self) -> list["PropertyTreeNode"]:
        return self.children + self.adoptees

    def allLeaves(self, without_self: bool = False) -> list["PropertyTreeNode"]:
        res: list[PropertyTreeNode] = []
        if self.leaf():
            if not without_self:
                res.append(self)
        else:
            for c in self.kids():
                res.extend(c.allLeaves())
        return res

    def leaf(self) -> bool:
        return not self.children and not self.adoptees
