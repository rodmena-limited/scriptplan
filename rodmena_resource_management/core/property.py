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
