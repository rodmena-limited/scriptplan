from lark import Lark, Transformer
from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.task import Task
from rodmena_resource_management.core.resource import Resource
from datetime import datetime
import os

class TJPTransformerDict(Transformer):
    def start(self, items): return items[0]

    def project(self, items):
        # items: [id, name, version, attributes]
        
        p_id = str(items[0]).strip('"')
        p_name = str(items[1]).strip('"')
        p_version = str(items[2]).strip('"')
        
        attrs = items[3]
        return {'type': 'project', 'id': p_id, 'name': p_name, 'version': p_version, 'attributes': attrs}

    def project_id(self, items): return items[0].value
    def project_name(self, items): return items[0].value
    def version(self, items): return items[0].value

    def project_attributes(self, items): return items
    def project_attribute(self, items): return items[0]
    
    def property_declaration(self, items): return items[0]
    
    def timezone(self, items): return ('timezone', items[0].value.strip('"'))
    def dailyworkinghours(self, items): return ('dailyworkinghours', float(items[0].value))
    def yearlyworkingdays(self, items): return ('yearlyworkingdays', float(items[0].value))
    
    def task(self, items):
        t_id = items[0].value
        t_name = items[1].value.strip('"')
        attrs = items[2]
        return ('task', (t_id, t_name, attrs))
    
    def task_id(self, items): return items[0]
    def task_name(self, items): return items[0]

    def resource(self, items):
        r_id = items[0].value
        r_name = items[1].value.strip('"')
        attrs = items[2]
        return ('resource', (r_id, r_name, attrs))
    
    def resource_id(self, items): return items[0]
    def resource_name(self, items): return items[0]

    def resource_attributes(self, items): return items
    def task_attributes(self, items): return items
    def resource_attribute(self, items): return items[0]
    def task_attribute(self, items): return items[0]
    
    def start_attr(self, items): return ('start', items[-1]) 
    
    def end(self, items): return ('end', items[-1])
    # def duration(self, items): return ('duration', items[0].value)
    
    def date(self, items):
        val = items[0].value
        try:
            return datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            return datetime.strptime(val, "%Y-%m-%d-%H:%M")

class ModelBuilder:
    def build(self, data):
        project = Project(data['id'], data['name'], data['version'])
        self._apply_attributes(project, data['attributes'])
        return project

    def _apply_attributes(self, context, attributes):
        for attr in attributes:
            if isinstance(attr, tuple):
                key, value = attr
                if key in ['task', 'resource']:
                    self._create_property(context, key, value)
                else:
                    # Check if scenario specific
                    if hasattr(context, 'attributeDefinition'):
                        defn = context.attributeDefinition(key)
                        if defn and defn.scenarioSpecific:
                             context[(key, 0)] = value
                             continue
                    
                    # Handle standard attributes
                    try:
                        context[key] = value
                    except ValueError:
                        pass
    
    def _create_property(self, parent, type_name, data):
        p_id, p_name, attrs = data
        
        # Determine project reference
        project = parent if isinstance(parent, Project) else parent.project
        
        if type_name == 'task':
            obj = Task(project, p_id, p_name, parent if isinstance(parent, Task) else None)
        elif type_name == 'resource':
            obj = Resource(project, p_id, p_name, parent if isinstance(parent, Resource) else None)
        
        self._apply_attributes(obj, attrs)

class ProjectFileParser:
    def __init__(self):
        grammar_path = os.path.join(os.path.dirname(__file__), 'tjp.lark')
        with open(grammar_path, 'r') as f:
            self.grammar = f.read()
        self.parser = Lark(self.grammar, start='start', parser='lalr')

    def parse(self, text):
        tree = self.parser.parse(text)
        data = TJPTransformerDict().transform(tree)
        builder = ModelBuilder()
        return builder.build(data)