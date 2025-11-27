from rodmena_resource_management.utils.message_handler import MessageHandler
from rodmena_resource_management.utils.time import TjTime

class PropertySet:
    def __init__(self, project, flat_namespace=False):
        self.project = project
        self.flat_namespace = flat_namespace
        self.attributes = []
        self.attributeDefinitions = {}
        self._properties = [] # List for order
        self._propertyMap = {} # Dict fullId -> PropertyTreeNode
        
        # Add standard attributes
        # In Ruby: id, name, seqno
        # I will move this logic here from Project.py if I update Project.py later, 
        # but for now I can duplicate or rely on Project.py calling _add_standard_attributes.
        # However, cleaner to have it here.
        self.addAttributeType(AttributeDefinition('id', 'ID', StringAttribute, False, False, False, ''))
        self.addAttributeType(AttributeDefinition('name', 'Name', StringAttribute, False, False, False, ''))
        self.addAttributeType(AttributeDefinition('seqno', 'Seq. No', IntegerAttribute, False, False, False, 0))

    def addAttributeType(self, attribute_definition):
        if self._properties:
             raise RuntimeError("Fatal Error: Attribute types must be defined before properties are added.")
        
        self.attributes.append(attribute_definition)
        self.attributeDefinitions[attribute_definition.id] = attribute_definition
    
    def eachAttributeDefinition(self):
        return iter(self.attributes)

    def items(self):
        return len(self._properties)

    def length(self):
        return len(self._properties)

    def __len__(self):
        return len(self._properties)

    def __getitem__(self, key):
        return self._propertyMap.get(key)

    def __setitem__(self, key, value):
        # Should typically use addProperty
        pass

    def __iter__(self):
        return iter(self._properties)
    
    def __contains__(self, item):
        if isinstance(item, str):
            return item in self._propertyMap
        return item in self._properties

    def empty(self):
        return len(self._properties) == 0
    
    def addProperty(self, property):
        self._propertyMap[property.fullId] = property
        self._properties.append(property)
    
    def removeProperty(self, prop):
        if isinstance(prop, str):
            property_node = self._propertyMap.get(prop)
        else:
            property_node = prop
        
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
            
        if property_node.parent:
            if property_node in property_node.parent.children:
                property_node.parent.children.remove(property_node)
        
        return property_node

    def clearProperties(self):
        self._properties.clear()
        self._propertyMap.clear()

    def index(self):
        for p in self._properties:
            bsIdcs = p.getBSIndicies()
            bsi = ".".join(map(str, bsIdcs))
            p.force('bsi', bsi)

    def levelSeqNo(self, property_node):
        seqNo = 1
        for p in self._properties:
            if not p.parent:
                if p == property_node:
                    return seqNo
                seqNo += 1
        raise ValueError(f"Unknown property {property_node.fullId}")

    def maxDepth(self):
        md = 0
        for p in self._properties:
            if p.level() > md:
                md = p.level()
        return md + 1

    def topLevelItems(self):
        items = 0
        for p in self._properties:
            if not p.parent:
                items += 1
        return items

    def to_ary(self):
        return list(self._properties)

    def to_s(self):
        # PropertyList.new(self).to_s
        return str(self._properties)

    def knownAttribute(self, attrId):
        return attrId in self.attributeDefinitions

    def hasQuery(self, attrId, scenarioIdx=None):
        if not self._properties:
            return False
        
        property_node = self._properties[0]
        method_name = f"query_{attrId}"
        
        if hasattr(property_node, method_name):
            return True
        elif scenarioIdx is not None:
            # Check scenario object
            if property_node.data and property_node.data[scenarioIdx]:
                return hasattr(property_node.data[scenarioIdx], method_name)
        return False

    def scenarioSpecific(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        if defn:
            return defn.scenarioSpecific
        
        # Check for query method
        if self._properties:
            prop = self._properties[0]
            if prop.data and prop.data[0] and hasattr(prop.data[0], f"query_{attrId}"):
                return True
        return False

    def inheritedFromProject(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.inheritedFromProject if defn else False

    def inheritedFromParent(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.inheritedFromParent if defn else False

    def userDefined(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        # userDefined attribute on AttributeDefinition not implemented yet, defaulting to False
        return getattr(defn, 'userDefined', False) if defn else False

    def listAttribute(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.isList() if defn else False

    def defaultValue(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.default if defn else None

    def attributeName(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.name if defn else None

    def attributeType(self, attrId):
        defn = self.attributeDefinitions.get(attrId)
        return defn.objClass if defn else None

class PTNProxy:
    """Proxy for PropertyTreeNode that represents adopted nodes in their new parental context."""

    def __init__(self, ptn, parent):
        self._ptn = ptn
        if not parent:
            raise ValueError("Adopted properties must have a parent")
        self._parent = parent
        self._index = None
        self._tree = None
        self._level = -1

    @property
    def parent(self):
        return self._parent

    @property
    def ptn(self):
        return self._ptn

    @property
    def logicalId(self):
        if self._ptn.propertySet.flat_namespace:
            return self._ptn.id
        else:
            dot_pos = self._ptn.id.rfind('.')
            if dot_pos >= 0:
                id = self._ptn.id[dot_pos + 1:]
            else:
                id = self._ptn.id
            return f"{self._parent.logicalId}.{id}"

    def set(self, attribute, val):
        if attribute == 'index':
            self._index = val
        elif attribute == 'tree':
            self._tree = val
        else:
            self._ptn.set(attribute, val)

    def get(self, attribute):
        if attribute == 'index':
            return self._index
        elif attribute == 'tree':
            return self._tree
        else:
            return self._ptn.get(attribute)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            attribute, scenarioIdx = key
        else:
            attribute = key
            scenarioIdx = None

        if attribute == 'index':
            return self._index
        elif attribute == 'tree':
            return self._tree
        else:
            if scenarioIdx is not None:
                return self._ptn[(attribute, scenarioIdx)]
            return self._ptn[attribute]

    def level(self):
        if self._level >= 0:
            return self._level

        t = self
        self._level = 0
        while t.parent is not None:
            t = t.parent
            self._level += 1
        return self._level

    def isChildOf(self, ancestor):
        parent = self
        while parent.parent is not None:
            parent = parent.parent
            if parent == ancestor:
                return True
        return False

    def getIndicies(self):
        idcs = []
        p = self
        while p is not None:
            parent = p.parent
            idcs.insert(0, p.get('index'))
            p = parent
        return idcs

    def force(self, attribute, val):
        if attribute == 'index':
            self._index = val
        elif attribute == 'tree':
            self._tree = val
        else:
            self._ptn.force(attribute, val)

    @property
    def fullId(self):
        return self._ptn.fullId

    @property
    def kids(self):
        return self._ptn.kids()

    @property
    def adoptees(self):
        return self._ptn.adoptees

    @property
    def propertySet(self):
        return self._ptn.propertySet

    def __getattr__(self, name):
        return getattr(self._ptn, name)

    def __eq__(self, other):
        if isinstance(other, PTNProxy):
            return self._ptn == other._ptn
        return self._ptn == other


class PropertyList:
    """List of PropertyTreeNodes with multi-level sorting support.

    All nodes in the list must belong to the same PropertySet.
    Sorting can use multiple criteria with ascending/descending direction.
    """

    def __init__(self, arg, copyItems=True):
        if isinstance(arg, PropertySet):
            self._items = list(arg._properties) if copyItems else []
            self._propertySet = arg
            self._query = None
            self.resetSorting()
            self.addSortingCriteria('seqno', True, -1)
            self.sort()
        elif isinstance(arg, PropertyList):
            self._items = list(arg._items) if copyItems else []
            self._propertySet = arg._propertySet
            self._query = arg._query.copy() if arg._query else None
            self._sortingLevels = arg._sortingLevels
            self._sortingCriteria = list(arg._sortingCriteria)
            self._sortingUp = list(arg._sortingUp)
            self._scenarioIdx = list(arg._scenarioIdx)
        else:
            # Assume it's a list/iterable
            self._items = list(arg) if copyItems else []
            self._propertySet = arg[0].propertySet if arg else None
            self._query = None
            self.resetSorting()

    @property
    def propertySet(self):
        return self._propertySet

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @property
    def sortingLevels(self):
        return self._sortingLevels

    @property
    def sortingCriteria(self):
        return self._sortingCriteria

    @property
    def sortingUp(self):
        return self._sortingUp

    @property
    def scenarioIdx(self):
        return self._scenarioIdx

    def includeAdopted(self):
        adopted = []
        for p in self._items:
            for ap in p.adoptees:
                adopted.extend(self._includeAdoptedR(ap, p))
        self.append(adopted)

    def _includeAdoptedR(self, property, parent):
        parentProxy = PTNProxy(property, parent)
        adopted = [parentProxy]

        for p in property.kids():
            adopted.extend(self._includeAdoptedR(p, parentProxy))

        return adopted

    def checkForDuplicates(self, sourceFileInfo=None):
        ptns = {}
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

    def __contains__(self, node):
        target_ptn = node.ptn if isinstance(node, PTNProxy) else node
        for p in self._items:
            p_ptn = p.ptn if isinstance(p, PTNProxy) else p
            if p_ptn == target_ptn:
                return True
        return False

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._items[key]
        # Node lookup
        target_ptn = key.ptn if isinstance(key, PTNProxy) else key
        for n in self._items:
            n_ptn = n.ptn if isinstance(n, PTNProxy) else n
            if n_ptn == target_ptn:
                return n
        return None

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def to_ary(self):
        return list(self._items)

    def setSorting(self, modes):
        self.resetSorting()
        for mode in modes:
            self.addSortingCriteria(*mode)

    def resetSorting(self):
        self._sortingLevels = 0
        self._sortingCriteria = []
        self._sortingUp = []
        self._scenarioIdx = []

    def append(self, items):
        if isinstance(items, (list, PropertyList)):
            for node in items:
                if node.propertySet != self._propertySet:
                    raise ValueError("All nodes must belong to the same PropertySet.")
            self._items.extend(items)
            if len(self._items) != len(set(id(x) for x in self._items)):
                raise ValueError("Duplicate items")
        else:
            self._items.append(items)
        self.sort()

    def treeMode(self):
        return self._sortingLevels > 0 and self._sortingCriteria[0] == 'tree'

    def sort(self):
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

    def itemIndex(self, item):
        try:
            return self._items.index(item)
        except ValueError:
            return None

    def index(self):
        i = 0
        for p in self._items:
            i += 1
            p.force('index', i)

    def __str__(self):
        res = "Sorting: "
        for i in range(self._sortingLevels):
            direction = 'up' if self._sortingUp[i] else 'down'
            res += f"{self._sortingCriteria[i]}/{direction}/{self._scenarioIdx[i]}, "
        res += f"\n{len(self._items)} properties:"
        for item in self._items:
            res += f"{item.get('id')}: {item.get('name')}\n"
        return res

    def addSortingCriteria(self, criteria, up, scIdx):
        if not self._propertySet.knownAttribute(criteria) and \
           not self._propertySet.hasQuery(criteria, scIdx):
            raise ValueError(f"Unknown attribute '{criteria}' used for sorting criterium")

        if self._propertySet.scenarioSpecific(criteria):
            if scIdx < 0 or (hasattr(self._propertySet.project, 'scenario') and
                           self._propertySet.project.scenario(scIdx) is None):
                # Allow if scIdx is valid or we can't verify
                pass
        else:
            scIdx = -1

        self._sortingCriteria.append(criteria)
        self._sortingUp.append(up)
        self._scenarioIdx.append(scIdx)
        self._sortingLevels += 1

    def _indexTree(self):
        for property in self._items:
            if isinstance(property, PTNProxy):
                treeIdcs = property.getIndicies()
            else:
                treeIdcs = self._getIndicies(property)

            tree = ''
            for idx in treeIdcs:
                tree += str(idx).rjust(6, '0')
            property.force('tree', tree)

    def _getIndicies(self, property):
        idcs = []
        p = property
        while p is not None:
            parent = p.parent
            idx = p.get('index')
            idcs.insert(0, idx)
            p = parent
        return idcs

    def _sortInternal(self):
        def compare_key(item):
            key_parts = []
            for i in range(self._sortingLevels):
                criteria = self._sortingCriteria[i]
                scIdx = self._scenarioIdx[i]
                up = self._sortingUp[i]

                if self._query and criteria != 'tree':
                    # Query-based sorting
                    self._query.scenarioIdx = None if scIdx < 0 else scIdx
                    self._query.attributeId = criteria
                    self._query.property = item
                    self._query.process()
                    val = self._query.to_sort()
                else:
                    # Static attribute sorting
                    if scIdx < 0:
                        if criteria == 'id':
                            val = item.fullId
                        else:
                            val = item.get(criteria)
                    else:
                        val = item[(criteria, scIdx)]

                # Handle None values
                if val is None:
                    val = ''

                # Invert for descending order
                if not up:
                    if isinstance(val, (int, float)):
                        val = -val
                    elif isinstance(val, str):
                        # For strings, we need a different approach
                        # Use a tuple with a flag
                        val = (1, val)  # descending strings will be sorted differently
                    else:
                        val = (1, val)
                else:
                    if isinstance(val, str):
                        val = (0, val)
                    elif not isinstance(val, (int, float)):
                        val = (0, val)

                key_parts.append(val)
            return tuple(key_parts)

        self._items.sort(key=compare_key)

    def delete_if(self, func):
        to_remove = [i for i in self._items if func(i)]
        for i in to_remove:
            self._items.remove(i)

    def each(self, func):
        for item in self._items:
            func(item)

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

    __slots__ = ['id', 'name', 'objClass', 'inheritedFromParent',
                 'inheritedFromProject', 'scenarioSpecific', 'default', 'userDefined']

    def __init__(self, id, name, objClass, inheritedFromParent, inheritedFromProject,
                 scenarioSpecific, default, userDefined=False):
        self.id = id
        self.name = name
        self.objClass = objClass
        self.inheritedFromParent = inheritedFromParent
        self.inheritedFromProject = inheritedFromProject
        self.scenarioSpecific = scenarioSpecific
        self.default = default
        self.userDefined = userDefined

    def isList(self):
        """Return True if this attribute holds a list of values."""
        return issubclass(self.objClass, ListAttributeBase)

    def __repr__(self):
        return (f"AttributeDefinition(id={self.id!r}, name={self.name!r}, "
                f"objClass={self.objClass.__name__}, scenarioSpecific={self.scenarioSpecific})")


class AttributeOverwrite(ValueError):
    """Exception raised when attempting to overwrite an existing attribute value."""
    pass


def deep_clone(value):
    """Create a deep copy of a value."""
    import copy
    return copy.deepcopy(value)


class AttributeBase:
    """Base class for all property attribute types.

    Each property can have multiple attributes of different types. Each type
    must be derived from this class. The class tracks whether the attribute
    value was provided by the project file, inherited from another property,
    or computed during scheduling.
    """

    _mode = 0  # 0=provided, 1=inherited, other=calculated

    def __init__(self, property_node, type_def, container):
        self._type = type_def
        self._property = property_node
        self._container = container
        self.reset()

    def reset(self):
        """Reset the attribute value to the default value."""
        self._inherited = False
        self._provided = False

        if isinstance(self._type, AttributeDefinition):
            self._value = deep_clone(self._type.default)
        else:
            self._value = self._type

    def getProperty(self):
        """Return the property node this attribute belongs to."""
        return self._property

    def getType(self):
        """Return the attribute type definition."""
        return self._type

    # Alias for Ruby compatibility
    type = property(lambda self: self._type)

    def getProvided(self):
        """Return whether the value was provided."""
        return self._provided

    # Alias for Ruby compatibility
    provided = property(lambda self: self._provided)

    def getInherited(self):
        """Return whether the value was inherited."""
        return self._inherited

    # Alias for Ruby compatibility
    inherited = property(lambda self: self._inherited)

    def inherit(self, value):
        """Inherit value from parent property. Values are deep copied."""
        self._inherited = True
        self._value = deep_clone(value)

    @classmethod
    def mode(cls):
        """Return the current attribute setting mode."""
        return cls._mode

    @classmethod
    def setMode(cls, mode):
        """Change the mode. 0=provided, 1=inherited, other=calculated."""
        cls._mode = mode

    def getId(self):
        """Return the ID of the attribute."""
        return self._type.id

    # Alias for Ruby compatibility
    id = property(lambda self: self._type.id)

    def getName(self):
        """Return the name of the attribute."""
        return self._type.name

    # Alias for Ruby compatibility
    name = property(lambda self: self._type.name)

    def set(self, value):
        """Set the value of the attribute. Flags updated based on mode."""
        if AttributeBase._mode == 0:
            self._provided = True
        elif AttributeBase._mode == 1:
            self._inherited = True
        self._value = value

    def get(self):
        """Return the attribute value."""
        return self._value

    # Alias for legacy purposes
    value = property(lambda self: self.get())

    def isNil(self):
        """Check whether the value is uninitialized or nil."""
        v = self.get()
        if isinstance(v, list):
            return len(v) == 0
        return v is None

    def isList(self):
        return False

    @classmethod
    def isListClass(cls):
        return False

    def to_s(self, query=None):
        """Return the value as String."""
        return str(self.get())

    def __str__(self):
        return self.to_s()

    def to_num(self):
        """Return value as number or None."""
        v = self.get()
        if isinstance(v, (int, float)):
            return v
        return None

    def to_sort(self):
        """Return value suitable for sorting."""
        v = self.get()
        if isinstance(v, (int, float)):
            return v
        elif isinstance(v, list):
            # If the attribute is a list, convert to comma separated string
            return ', '.join(str(x) for x in v)
        elif v is not None:
            return str(v)
        return None

    def to_rti(self, query):
        """Return RichTextIntermediate value or None."""
        # Placeholder - RichTextIntermediate not implemented
        return None

    def to_tjp(self):
        """Return the value in TJP file syntax."""
        return f"{self._type.id} {self.get()}"

    def _quotedString(self, s):
        """Format string for TJP output."""
        if '\n' in s:
            return f"-8<-\n{s}\n->8-"
        return f'"{s.replace(chr(34), chr(92) + chr(34))}"'


class ListAttributeBase(AttributeBase):
    """Specialized AttributeBase for list values."""

    def __init__(self, property_node, type_def, container):
        super().__init__(property_node, type_def, container)
        if self._value is None:
            self._value = []
        elif not isinstance(self._value, list):
            self._value = [self._value]

    def to_s(self, query=None):
        """Return the value as comma-separated String."""
        return ', '.join(str(x) for x in self.get())

    def isList(self):
        return True

    @classmethod
    def isListClass(cls):
        return True

    def set(self, value):
        """Set value - for lists, extends the existing list."""
        if AttributeBase._mode == 0:
            self._provided = True
        elif AttributeBase._mode == 1:
            self._inherited = True

        if not isinstance(self._value, list):
            self._value = []
        if isinstance(value, list):
            self._value.extend(value)
        else:
            self._value.append(value)

    def __iter__(self):
        return iter(self._value)

    def __len__(self):
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
    def __init__(self):
        pass


class Journal:
    def __init__(self):
        pass


class LeaveList(list):
    pass


class RealFormat:
    def __init__(self, args=None):
        pass


class KeywordArray:
    def __init__(self, args=None):
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

class PropertyTreeNode(MessageHandler):
    def __init__(self, property_set, id, name, parent):
        self.propertySet = property_set
        self.project = property_set.project
        self.parent = parent
        self.data = None 
        
        self._attributes = {} 
        self._scenarioAttributes = [] 

        scenario_count = self.project.scenarioCount() if hasattr(self.project, 'scenarioCount') else 1
        self._scenarioAttributes = [{} for _ in range(scenario_count)]

        if id is None:
            tag = self.__class__.__name__
            id = f"_{tag}_{self.propertySet.items() + 1}"
            if not self.propertySet.flat_namespace and parent:
                id = f"{parent.fullId}.{id}"
        
        if not self.propertySet.flat_namespace and id and '.' in id:
            parent_id = id.rsplit('.', 1)[0]
            if not self.parent:
                self.parent = self.propertySet[parent_id]
            self.subId = id.rsplit('.', 1)[1]
        else:
            self.subId = id
        
        self.id = id 
        self.name = name
        self.sourceFileInfo = None
        self.sequenceNo = self.propertySet.items() + 1
        self.children = []
        self.adoptees = []
        self.stepParents = []
        
        self.set('id', self.fullId)
        self.set('name', name)
        self.set('seqno', self.sequenceNo)

        if self.parent:
            self.parent.addChild(self)
        
        self.propertySet.addProperty(self)

    @property
    def fullId(self):
        res = self.subId
        if not self.propertySet.flat_namespace:
            t = self
            while t.parent:
                t = t.parent
                res = f"{t.subId}.{res}"
        return res

    def addChild(self, child):
        self.children.append(child)

    def ptn(self):
        return self

    def adopt(self, property_node):
        if self == property_node:
            self.error('adopt_self', 'A property cannot adopt itself')
        
        # Check for duplicates logic... simplified
        
        self.adoptees.append(property_node)
        property_node.getAdopted(self)

    def getAdopted(self, property_node):
        if property_node not in self.stepParents:
            self.stepParents.append(property_node)

    def parents(self):
        p = [self.parent] if self.parent else []
        return p + self.stepParents

    def backupAttributes(self):
        # Shallow copy of attributes dictionaries
        return [self._attributes.copy(), [sa.copy() for sa in self._scenarioAttributes]]

    def restoreAttributes(self, backup):
        self._attributes, self._scenarioAttributes = backup

    def removeReferences(self, property_node):
        if property_node in self.children: self.children.remove(property_node)
        if property_node in self.adoptees: self.adoptees.remove(property_node)
        if property_node in self.stepParents: self.stepParents.remove(property_node)

    def level(self):
        lvl = 0
        t = self
        while t.parent:
            lvl += 1
            t = t.parent
        return lvl

    def getBSIndicies(self):
        idcs = []
        p = self
        while p:
            parent = p.parent
            idx = parent.levelSeqNo(p) if parent else self.propertySet.levelSeqNo(p)
            idcs.insert(0, idx)
            p = parent
        return idcs

    def levelSeqNo(self, node):
        try:
            return self.children.index(node) + 1
        except ValueError:
            raise ValueError(f"Node {node.fullId} is not a child of {self.fullId}")

    def inheritAttributes(self):
        # Inherit non-scenario-specific values
        for attrDef in self.propertySet.attributes:
            if attrDef.scenarioSpecific or not attrDef.inheritedFromParent:
                continue
            
            aId = attrDef.id
            if self.parent:
                # If parent provided or inherited
                # Simplified: check if parent has value different from default or just take it?
                # Ruby: if parent.provided(aId) || parent.inherited(aId)
                # In our implementation, 'provided' flag handles this.
                # We need to check parent's attribute object status.
                
                parent_attr = self.parent._get_attribute(aId)
                if parent_attr.provided or parent_attr.inherited:
                    my_attr = self._get_attribute(aId)
                    my_attr.inherit(parent_attr.get())
            else:
                if attrDef.inheritedFromProject:
                    # Check project
                    if aId in self.project.attributes:
                         # Project attributes are raw values or Attribute objects?
                         # In Project.py they are in self.attributes dict as values/objects.
                         # If standard attribute (int/string), it's value.
                         # If AttributeBase, it's object?
                         # My Project implementation uses a mix.
                         # But we should use standard access.
                         val = self.project[aId]
                         if val is not None:
                             my_attr = self._get_attribute(aId)
                             my_attr.inherit(val)

        # Inherit scenario-specific values
        for attrDef in self.propertySet.attributes:
            if not attrDef.scenarioSpecific or not attrDef.inheritedFromParent:
                continue
            
            scenario_count = self.project.scenarioCount() if hasattr(self.project, 'scenarioCount') else 1
            for scenarioIdx in range(scenario_count):
                if self.parent:
                    parent_attr = self.parent._get_scenario_attribute(attrDef.id, scenarioIdx)
                    if parent_attr.provided or parent_attr.inherited:
                        my_attr = self._get_scenario_attribute(attrDef.id, scenarioIdx)
                        my_attr.inherit(parent_attr.get())
                else:
                    if attrDef.inheritedFromProject:
                         val = self.project[attrDef.id]
                         # Project attributes usually not scenario specific or stored differently?
                         # Ruby: if @project[attrDef.id] && ...
                         # If project has it, inherit.
                         if val is not None:
                             my_attr = self._get_scenario_attribute(attrDef.id, scenarioIdx)
                             my_attr.inherit(val)

    def ancestors(self, includeStepParents=False):
        nodes = []
        if includeStepParents:
            for p in self.parents():
                nodes.append(p)
                nodes.extend(p.ancestors(True))
        else:
            n = self
            while n.parent:
                n = n.parent
                nodes.append(n)
        return nodes

    def root(self):
        n = self
        while n.parent:
            n = n.parent
        return n

    def provided(self, attributeId, scenarioIdx=None):
        if scenarioIdx is not None:
            if attributeId not in self._scenarioAttributes[scenarioIdx]:
                return False
            return self._scenarioAttributes[scenarioIdx][attributeId].provided
        else:
            if attributeId not in self._attributes:
                return False
            return self._attributes[attributeId].provided

    def inherited(self, attributeId, scenarioIdx=None):
        if scenarioIdx is not None:
            if attributeId not in self._scenarioAttributes[scenarioIdx]:
                return False
            return self._scenarioAttributes[scenarioIdx][attributeId].inherited
        else:
            if attributeId not in self._attributes:
                return False
            return self._attributes[attributeId].inherited

    def checkFailsAndWarnings(self):
        # Placeholder for logic
        pass

    def force(self, attribute_id, value):
        attr = self._get_attribute(attribute_id)
        attr.set(value)

    def set(self, attribute_id, value):
        attr = self._get_attribute(attribute_id)
        if attr.type.scenarioSpecific:
            raise ValueError(f"Attribute {attribute_id} is scenario specific, use []=")
        attr.set(value)

    def _get_attribute(self, attribute_id):
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

    def _get_scenario_attribute(self, attribute_id, scenario_idx):
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

    def attributeDefinition(self, attribute_id):
        return self.propertySet.attributeDefinitions.get(attribute_id)
    
    def get(self, attribute_id, scenarioIdx=None):
        if scenarioIdx is not None:
             attr = self._get_scenario_attribute(attribute_id, scenarioIdx)
        else:
             attr = self._get_attribute(attribute_id)
        return attr.get()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            attribute_id, scenario = key
            attr = self._get_scenario_attribute(attribute_id, scenario)
            return attr.get()
        else:
            return self.get(key)

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            attribute_id, scenario = key
            attr = self._get_scenario_attribute(attribute_id, scenario)
            attr.set(value)
        else:
            self.set(key, value)

    def all(self):
        res = [self]
        for child in self.kids():
            res.extend(child.all())
        return res

    def kids(self):
        return self.children + self.adoptees
    
    def allLeaves(self, without_self=False):
        res = []
        if self.leaf():
            if not without_self:
                res.append(self)
        else:
            for c in self.kids():
                res.extend(c.allLeaves())
        return res
    
    def leaf(self):
        return not self.children and not self.adoptees
