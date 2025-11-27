class PropertySet:
    def __init__(self, project, flat_namespace=False):
        self.project = project
        self.flat_namespace = flat_namespace
        self.attributes = []

    def addAttributeType(self, attribute_definition):
        self.attributes.append(attribute_definition)
    
    def index(self):
        pass

    def __getitem__(self, key):
        return None

    def empty(self):
        return True

class PropertyList:
    def __init__(self, property_set):
        self.property_set = property_set
        self.items = []
    
    def __iter__(self):
        return iter(self.items)

    def setSorting(self, criteria):
        pass

    def sort(self):
        pass
    
    def delete_if(self, func):
        self.items = [i for i in self.items if not func(i)]

class AttributeDefinition:
    def __init__(self, id, name, type_class, inherited, inherited_from_project, scenario_specific, default):
        self.id = id
        self.name = name
        self.type_class = type_class
        self.inherited = inherited
        self.inherited_from_project = inherited_from_project
        self.scenario_specific = scenario_specific
        self.default = default

# Stub Attribute Classes
class AttributeBase: 
    @staticmethod
    def setMode(mode):
        pass

class StringAttribute(AttributeBase): pass
class IntegerAttribute(AttributeBase): pass
class FloatAttribute(AttributeBase): pass
class DateAttribute(AttributeBase): pass
class BooleanAttribute(AttributeBase): pass
class ReferenceAttribute(AttributeBase): pass
class ListAttribute(AttributeBase): pass

class AlertLevelDefinitions: pass
class Journal:
    def __init__(self): pass
class LeaveList(list): pass
class RealFormat:
    def __init__(self, args): pass
class KeywordArray: 
    def __init__(self, args): pass

# Specific Attributes from Project.rb
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