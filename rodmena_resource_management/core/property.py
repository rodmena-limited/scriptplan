from rodmena_resource_management.utils.message_handler import MessageHandler
from rodmena_resource_management.utils.time import TjTime

class PropertySet:
    def __init__(self, project, flat_namespace=False):
        self.project = project
        self.flat_namespace = flat_namespace
        self.attributes = []
        self.attributeDefinitions = {}
        self._properties = {}

    def addAttributeType(self, attribute_definition):
        self.attributes.append(attribute_definition)
        self.attributeDefinitions[attribute_definition.id] = attribute_definition
    
    def eachAttributeDefinition(self):
        return iter(self.attributes)

    def items(self):
        return len(self._properties)

    def __getitem__(self, key):
        return self._properties.get(key)

    def __setitem__(self, key, value):
        self._properties[key] = value

    def empty(self):
        return len(self._properties) == 0
    
    def addProperty(self, property):
        self._properties[property.fullId] = property
    
    def index(self):
        pass

    def levelSeqNo(self, node):
         try:
            return list(self._properties.values()).index(node) + 1
         except ValueError:
            return 1

class PropertyList(list):
    def __init__(self, property_set):
        super().__init__()
        self.property_set = property_set
    
    def setSorting(self, criteria):
        pass

    def sort(self):
        pass
    
    def delete_if(self, func):
        to_remove = [i for i in self if func(i)]
        for i in to_remove:
            self.remove(i)

class AttributeDefinition:
    def __init__(self, id, name, type_class, inherited, inherited_from_project, scenario_specific, default):
        self.id = id
        self.name = name
        self.objClass = type_class
        self.inheritedFromParent = inherited
        self.inheritedFromProject = inherited_from_project
        self.scenarioSpecific = scenario_specific
        self.default = default
    
    def isList(self):
        return issubclass(self.objClass, ListAttribute)

class AttributeBase:
    _mode = 0

    def __init__(self, property_set, attribute_definition, property_node):
        self.property_set = property_set
        self.definition = attribute_definition
        self.property_node = property_node
        default = attribute_definition.default
        if isinstance(default, list):
             self.value = list(default)
        else:
             self.value = default
        self.provided = False
        self.inherited = False
    
    @classmethod
    def setMode(cls, mode):
        cls._mode = mode

    @classmethod
    def mode(cls):
        return cls._mode

    def set(self, value):
        self.value = value
        self.provided = True

    def inherit(self, value):
        self.value = value
        self.inherited = True
    
    def get(self):
        return self.value
    
    def isList(self):
        return False

# Attribute Types
class StringAttribute(AttributeBase): pass
class IntegerAttribute(AttributeBase): pass
class FloatAttribute(AttributeBase): pass
class DateAttribute(AttributeBase): pass
class BooleanAttribute(AttributeBase): pass
class ReferenceAttribute(AttributeBase): pass

class ListAttribute(AttributeBase):
    def __init__(self, property_set, attribute_definition, property_node):
        super().__init__(property_set, attribute_definition, property_node)
        if self.value is None:
             self.value = []
        elif not isinstance(self.value, list):
             self.value = [self.value]

    def set(self, value):
        if not isinstance(self.value, list):
            self.value = []
        if isinstance(value, list):
            self.value.extend(value)
        else:
            self.value.append(value)
        self.provided = True
    
    def __iter__(self):
        return iter(self.value)

    def isList(self):
        return True

# Data Classes (Value Objects)
class AlertLevelDefinitions: 
    def __init__(self): pass

class Journal:
    def __init__(self): pass

class LeaveList(list): pass

class RealFormat:
    def __init__(self, args=None): pass

class KeywordArray: 
    def __init__(self, args=None): pass

# Specific Attributes
class ResourceListAttribute(ListAttribute): pass
class ShiftAssignmentsAttribute(AttributeBase): pass
class TaskDepListAttribute(ListAttribute): pass
class LogicalExpressionListAttribute(ListAttribute): pass
class PropertyAttribute(AttributeBase): pass
class RichTextAttribute(AttributeBase): pass
class ColumnListAttribute(ListAttribute): pass
class AccountAttribute(AttributeBase): pass
class DefinitionListAttribute(ListAttribute): pass
class FlagListAttribute(ListAttribute): pass
class FormatListAttribute(ListAttribute): pass
class LogicalExpressionAttribute(AttributeBase): pass
class SymbolListAttribute(ListAttribute): pass
class SymbolAttribute(AttributeBase): pass
class NodeListAttribute(ListAttribute): pass
class ScenarioListAttribute(ListAttribute): pass
class SortListAttribute(ListAttribute): pass
class JournalSortListAttribute(ListAttribute): pass
class RealFormatAttribute(AttributeBase): pass
class LeaveListAttribute(ListAttribute): pass

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

    def set(self, attribute_id, value):
        attr = self._get_attribute(attribute_id)
        if attr.definition.scenarioSpecific:
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
        
        attr = defn.objClass(self.propertySet, defn, self)
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
        attr = defn.objClass(self.propertySet, defn, scenario_obj)
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
