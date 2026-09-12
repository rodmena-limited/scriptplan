"""Attribute definitions and the typed values that fill them.

An AttributeDefinition says what an attribute is called, what type it holds,
whether it is inherited and whether it varies by scenario. An AttributeBase
holds one such value for one property, and remembers whether the value was
provided by the file, inherited, or computed by the scheduler -- which is how
a second scheduling run knows what it may discard.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scriptplan.core.property_tree_node import PropertyTreeNode

class AttributeDefinition:
    """Definition of an attribute type that can be added to a PropertySet.

    The AttributeDefinition describes the meta information of a PropertyTreeNode
    attribute. Based on this information, PropertySet objects generate the
    attribute lists for each PropertyTreeNode upon creation of the node.

    Args:
        id: The ID of the attribute. Must be unique within the PropertySet.
        name: A descriptive text used in report columns and the like.
        objClass: Reference to the class of the attribute (e.g., StringAttribute).
        inheritedFromParent: True if the node can inherit from parent node.
        inheritedFromProject: True if the node can inherit from global scope.
        scenarioSpecific: True if the attribute can have different values per scenario.
        default: The default value set upon creation of the attribute.
        userDefined: True if this is a user-defined (custom) attribute.
    """

    __slots__ = [
        "default",
        "id",
        "inheritedFromParent",
        "inheritedFromProject",
        "name",
        "objClass",
        "scenarioSpecific",
        "userDefined",
    ]

    def __init__(
        self,
        id: str,
        name: str,
        objClass: type[AttributeBase],
        inheritedFromParent: bool,
        inheritedFromProject: bool,
        scenarioSpecific: bool,
        default: Any,
        userDefined: bool = False,
    ) -> None:
        self.id = id
        self.name = name
        self.objClass = objClass
        self.inheritedFromParent = inheritedFromParent
        self.inheritedFromProject = inheritedFromProject
        self.scenarioSpecific = scenarioSpecific
        self.default = default
        self.userDefined = userDefined

    def isList(self) -> bool:
        """Return True if this attribute holds a list of values."""
        return issubclass(self.objClass, ListAttributeBase)

    def __repr__(self) -> str:
        return (
            f"AttributeDefinition(id={self.id!r}, name={self.name!r}, "
            f"objClass={self.objClass.__name__}, scenarioSpecific={self.scenarioSpecific})"
        )


class AttributeOverwrite(ValueError):
    """Exception raised when attempting to overwrite an existing attribute value."""

    pass


def deep_clone(value: Any) -> Any:
    """Create a copy of a value for inheritance.

    For most values, we do a deep copy. However, for lists containing
    PropertyTreeNode objects (like Task references in depends), we do
    a shallow copy to preserve object identity.
    """

    # For lists, check if they contain PropertyTreeNode objects
    if isinstance(value, list):
        if value and hasattr(value[0], "propertySet"):
            # This is a list of PropertyTreeNode objects (like tasks in depends)
            # Do a shallow copy to preserve object identity
            return list(value)
        else:
            # Regular list, deep copy
            return copy.deepcopy(value)

    return copy.deepcopy(value)


class AttributeBase:
    """Base class for all property attribute types.

    Each property can have multiple attributes of different types. Each type
    must be derived from this class. The class tracks whether the attribute
    value was provided by the project file, inherited from another property,
    or computed during scheduling.
    """

    # How a value being set should be recorded: 0 provided by the file,
    # 1 inherited from a container or the project, anything else computed by
    # the scheduler.
    #
    # This lives on the project, because two projects being built or scheduled
    # in the same process must not tag each other's attributes. The class
    # variable below is the fallback for attributes with no project yet, and
    # the setting the module-level setMode()/mode() still reach.
    PROVIDED = 0
    INHERITED = 1
    COMPUTED = 2

    _mode: int = PROVIDED

    def __init__(
        self, property_node: PropertyTreeNode, type_def: AttributeDefinition | Any, container: Any
    ) -> None:
        self._type = type_def
        self._property = property_node
        self._container = container
        self._inherited: bool = False
        self._provided: bool = False
        self._value: Any = None
        self.reset()

    def reset(self) -> None:
        """Reset the attribute value to the default value."""
        self._inherited = False
        self._provided = False

        if isinstance(self._type, AttributeDefinition):
            self._value = deep_clone(self._type.default)
        else:
            self._value = self._type

    def getProperty(self) -> PropertyTreeNode:
        """Return the property node this attribute belongs to."""
        return self._property

    def getType(self) -> AttributeDefinition | Any:
        """Return the attribute type definition."""
        return self._type

    # Alias for Ruby compatibility
    type = property(lambda self: self._type)

    def getProvided(self) -> bool:
        """Return whether the value was provided."""
        return self._provided

    # Alias for Ruby compatibility
    provided = property(lambda self: self._provided)

    def getInherited(self) -> bool:
        """Return whether the value was inherited."""
        return self._inherited

    # Alias for Ruby compatibility
    inherited = property(lambda self: self._inherited)

    def inherit(self, value: Any) -> None:
        """Inherit value from parent property. Values are deep copied."""
        self._inherited = True
        self._value = deep_clone(value)

    @classmethod
    def mode(cls) -> int:
        """The process-wide fallback mode."""
        return cls._mode

    @classmethod
    def setMode(cls, mode: int) -> None:
        """Set the process-wide fallback mode. 0 provided, 1 inherited, 2 computed."""
        cls._mode = mode

    def currentMode(self) -> int:
        """The mode that applies to this attribute.

        The owning project's mode when there is one, so that two projects in
        one process cannot mislabel each other's attributes, and the
        process-wide fallback otherwise.
        """
        project = getattr(self._property, "project", None)
        mode = getattr(project, "attributeMode", None)
        return AttributeBase._mode if mode is None else int(mode)

    def getId(self) -> str:
        """Return the ID of the attribute."""
        return self._type.id

    # Alias for Ruby compatibility
    id = property(lambda self: self._type.id)

    def getName(self) -> str:
        """Return the name of the attribute."""
        return self._type.name

    # Alias for Ruby compatibility
    name = property(lambda self: self._type.name)

    def set(self, value: Any) -> None:
        """Set the value of the attribute. Flags updated based on mode."""
        mode = self.currentMode()
        if mode == AttributeBase.PROVIDED:
            self._provided = True
        elif mode == AttributeBase.INHERITED:
            self._inherited = True
        self._value = value

    def get(self) -> Any:
        """Return the attribute value."""
        return self._value

    # Alias for legacy purposes
    value = property(lambda self: self.get())

    def isNil(self) -> bool:
        """Check whether the value is uninitialized or nil."""
        v = self.get()
        if isinstance(v, list):
            return len(v) == 0
        return v is None

    def isList(self) -> bool:
        return False

    @classmethod
    def isListClass(cls) -> bool:
        return False

    def to_s(self, query: Any | None = None) -> str:
        """Return the value as String."""
        return str(self.get())

    def __str__(self) -> str:
        return self.to_s()

    def to_num(self) -> int | float | None:
        """Return value as number or None."""
        v = self.get()
        if isinstance(v, (int, float)):
            return v
        return None

    def to_sort(self) -> int | float | str | None:
        """Return value suitable for sorting."""
        v = self.get()
        if isinstance(v, (int, float)):
            return v
        elif isinstance(v, list):
            # If the attribute is a list, convert to comma separated string
            return ", ".join(str(x) for x in v)
        elif v is not None:
            return str(v)
        return None

    def to_rti(self, query: Any) -> Any | None:
        """Return RichTextIntermediate value or None."""
        # Placeholder - RichTextIntermediate not implemented
        return None

    def to_tjp(self) -> str:
        """Return the value in TJP file syntax."""
        return f"{self._type.id} {self.get()}"

    def _quotedString(self, s: str) -> str:
        """Format string for TJP output."""
        if "\n" in s:
            return f"-8<-\n{s}\n->8-"
        return f'"{s.replace(chr(34), chr(92) + chr(34))}"'


class ListAttributeBase(AttributeBase):
    """Specialized AttributeBase for list values."""

    def __init__(
        self, property_node: PropertyTreeNode, type_def: AttributeDefinition | Any, container: Any
    ) -> None:
        super().__init__(property_node, type_def, container)
        if self._value is None:
            self._value = []
        elif not isinstance(self._value, list):
            self._value = [self._value]

    def to_s(self, query: Any | None = None) -> str:
        """Return the value as comma-separated String."""
        return ", ".join(str(x) for x in self.get())

    def isList(self) -> bool:
        return True

    @classmethod
    def isListClass(cls) -> bool:
        return True

    def set(self, value: Any) -> None:
        """Set value - for lists, extends the existing list."""
        mode = self.currentMode()
        if mode == AttributeBase.PROVIDED:
            self._provided = True
        elif mode == AttributeBase.INHERITED:
            self._inherited = True

        if not isinstance(self._value, list):
            self._value = []
        if isinstance(value, list):
            self._value.extend(value)
        else:
            self._value.append(value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)


# Backwards compatibility aliases
ListAttribute = ListAttributeBase


# Attribute Types
class StringAttribute(AttributeBase):
    pass


class IntegerAttribute(AttributeBase):
    pass


class FloatAttribute(AttributeBase):
    pass


class DateAttribute(AttributeBase):
    pass


class BooleanAttribute(AttributeBase):
    pass


class ReferenceAttribute(AttributeBase):
    pass


# Data Classes (Value Objects)
class AlertLevelDefinitions:
    def __init__(self) -> None:
        pass


class Journal:
    def __init__(self) -> None:
        pass


class LeaveList(list):  # type: ignore
    pass


class RealFormat:
    def __init__(self, args: Any | None = None) -> None:
        pass


class KeywordArray:
    def __init__(self, args: Any | None = None) -> None:
        pass


# Specific Attributes
class ResourceListAttribute(ListAttributeBase):
    pass


class ShiftAssignmentsAttribute(AttributeBase):
    pass


class TaskDepListAttribute(ListAttributeBase):
    pass


class LogicalExpressionListAttribute(ListAttributeBase):
    pass


class PropertyAttribute(AttributeBase):
    pass


class RichTextAttribute(AttributeBase):
    pass


class ColumnListAttribute(ListAttributeBase):
    pass


class AccountAttribute(AttributeBase):
    pass


class DefinitionListAttribute(ListAttributeBase):
    pass


class FlagListAttribute(ListAttributeBase):
    pass


class FormatListAttribute(ListAttributeBase):
    pass


class LogicalExpressionAttribute(AttributeBase):
    pass


class SymbolListAttribute(ListAttributeBase):
    pass


class SymbolAttribute(AttributeBase):
    pass


class NodeListAttribute(ListAttributeBase):
    pass


class ScenarioListAttribute(ListAttributeBase):
    pass


class SortListAttribute(ListAttributeBase):
    pass


class JournalSortListAttribute(ListAttributeBase):
    pass


class RealFormatAttribute(AttributeBase):
    pass


class LeaveListAttribute(ListAttributeBase):
    pass
