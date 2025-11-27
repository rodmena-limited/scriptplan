"""TJP Parser for TaskJuggler project files."""

from lark import Lark, Transformer, v_args, Token, Tree
from rodmena_resource_management.core.project import Project
from rodmena_resource_management.core.task import Task
from rodmena_resource_management.core.resource import Resource
from rodmena_resource_management.parser.macro_processor import preprocess_tjp
from datetime import datetime
import os


class TJPTransformer(Transformer):
    """Transform the parse tree into a dictionary structure."""

    def start(self, items):
        return items[0] if items else {}

    def statements(self, items):
        result = {
            'project': None,
            'global_attributes': [],
            'property_declarations': [],
            'reports': [],
            'navigators': []
        }
        for item in items:
            if isinstance(item, dict):
                if item.get('type') == 'project':
                    result['project'] = item
                elif item.get('type') in ['resource', 'task', 'account', 'shift']:
                    result['property_declarations'].append(item)
                elif item.get('type') in ['taskreport', 'resourcereport', 'textreport']:
                    result['reports'].append(item)
                elif item.get('type') == 'navigator':
                    result['navigators'].append(item)
            elif isinstance(item, tuple):
                result['global_attributes'].append(item)
        return result

    def statement(self, items):
        return items[0] if items else None

    # Project definition
    def project(self, items):
        p_id = self._get_value(items[0])
        p_name = self._get_value(items[1])
        timeframe = items[2] if len(items) > 2 else {}
        attrs = items[3] if len(items) > 3 else []
        return {
            'type': 'project',
            'id': p_id,
            'name': p_name,
            'timeframe': timeframe,
            'attributes': attrs
        }

    def project_id(self, items):
        return self._get_value(items[0])

    def project_name(self, items):
        return self._get_value(items[0])

    def project_timeframe(self, items):
        result = {'start': items[0]}
        if len(items) > 1 and items[1]:
            result['duration'] = items[1]
        return result

    def duration_spec(self, items):
        return self._get_value(items[0]) if items else None

    def project_attributes(self, items):
        return list(items)

    def project_attribute(self, items):
        return items[0] if items else None

    # Global attributes
    def global_attribute(self, items):
        return items[0] if items else None

    def copyright(self, items):
        return ('copyright', self._get_value(items[0]))

    def rate(self, items):
        return ('rate', float(self._get_value(items[0])))

    def leaves_global(self, items):
        return ('leaves', {
            'type': self._get_value(items[0]),
            'name': self._get_value(items[1]),
            'start': items[2],
            'end': items[3] if len(items) > 3 else None
        })

    def flags_global(self, items):
        return ('flags', [self._get_value(i) for i in items])

    def balance(self, items):
        return ('balance', (self._get_value(items[0]), self._get_value(items[1])))

    # Project attribute handlers
    def timezone(self, items):
        return ('timezone', self._get_value(items[0]))

    def timeformat(self, items):
        return ('timeformat', self._get_value(items[0]))

    def numberformat(self, items):
        return ('numberformat', [self._get_value(i) for i in items])

    def currencyformat(self, items):
        return ('currencyformat', [self._get_value(i) for i in items])

    def currency(self, items):
        return ('currency', self._get_value(items[0]))

    def now(self, items):
        return ('now', items[0])

    def dailyworkinghours(self, items):
        return ('dailyworkinghours', float(self._get_value(items[0])))

    def yearlyworkingdays(self, items):
        return ('yearlyworkingdays', float(self._get_value(items[0])))

    # Scenario
    def scenario_def(self, items):
        s_id = self._get_value(items[0])
        s_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return ('scenario', {'id': s_id, 'name': s_name, 'children': body})

    def scenario_body(self, items):
        return list(items)

    # Extend
    def extend(self, items):
        e_type = self._get_value(items[0])
        attrs = items[1] if len(items) > 1 else []
        return ('extend', {'type': e_type, 'attributes': attrs})

    def extend_body(self, items):
        return list(items)

    def extend_attribute(self, items):
        # Grammar: "text" ID STRING - "text" is literal, so only ID and STRING in items
        return {
            'type': 'text',
            'name': self._get_value(items[0]),
            'label': self._get_value(items[1])
        }

    # Property declarations
    def property_declaration(self, items):
        return items[0] if items else None

    # Resource
    def resource(self, items):
        r_id = self._get_value(items[0])
        r_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return {
            'type': 'resource',
            'id': r_id,
            'name': r_name,
            'attributes': body
        }

    def resource_body(self, items):
        return list(items)

    def resource_attr(self, items):
        return items[0] if items else None

    # Task
    def task(self, items):
        t_id = self._get_value(items[0])
        t_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return {
            'type': 'task',
            'id': t_id,
            'name': t_name,
            'attributes': body
        }

    def task_body(self, items):
        return list(items)

    def task_attr(self, items):
        return items[0] if items else None

    # Named task attribute rules
    def task_start(self, items):
        return ('start', items[0])

    def task_end(self, items):
        return ('end', items[0])

    def task_effort(self, items):
        return items[0]  # effort_value returns a tuple

    def task_duration(self, items):
        return ('duration', items[0])

    def task_length(self, items):
        return ('length', items[0])

    def task_milestone(self, items):
        return ('milestone', True)

    def task_depends(self, items):
        return items[0]  # depends_list returns a tuple

    def task_precedes(self, items):
        return ('precedes', items[0][1] if isinstance(items[0], tuple) else items[0])

    def task_allocate(self, items):
        return items[0]  # allocate_spec returns a tuple

    def task_responsible(self, items):
        return ('responsible', self._get_value(items[0]))

    def task_priority(self, items):
        return ('priority', int(self._get_value(items[0])))

    def task_complete(self, items):
        return ('complete', float(self._get_value(items[0])))

    def task_note(self, items):
        return ('note', self._get_value(items[0]))

    def task_chargeset(self, items):
        return ('chargeset', self._get_value(items[0]))

    def task_purge_chargeset(self, items):
        return ('purge_chargeset', True)

    def task_charge(self, items):
        return ('charge', (float(self._get_value(items[0])), self._get_value(items[1]) if len(items) > 1 else None))

    def task_limits(self, items):
        return ('limits', items[0] if items else [])

    def task_journalentry(self, items):
        # items: date, optional headline (STRING), journal_body
        date = items[0] if items else None
        headline = None
        body = {}

        for item in items[1:]:
            if isinstance(item, str) or (hasattr(item, 'type') and item.type == 'STRING'):
                headline = self._get_value(item)
            elif isinstance(item, dict):
                body = item

        return ('journalentry', {'date': date, 'headline': headline, 'body': body})

    def journal_body(self, items):
        # Collect all journal attributes into a dict
        result = {'author': None, 'alert': 'green', 'summary': None, 'details': None}
        for item in items:
            if isinstance(item, tuple):
                key, value = item
                result[key] = value
        return result

    def journal_attr(self, items):
        # Pass through the inner journal_* rule result
        return items[0] if items else None

    def journal_author(self, items):
        return ('author', self._get_value(items[0]))

    def journal_alert(self, items):
        return ('alert', items[0] if items else 'green')

    def journal_summary(self, items):
        value = items[0] if items else None
        return ('summary', self._extract_text(value))

    def journal_details(self, items):
        value = items[0] if items else None
        return ('details', self._extract_text(value))

    def rich_text(self, items):
        # Rich text is wrapped in -8<- ... ->8-
        # The RICH_TEXT_BLOCK token contains the delimiters and content
        if items:
            text = self._get_value(items[0])
            # Strip the -8<- and ->8- markers
            if text.startswith('-8<-'):
                text = text[4:]
            if text.endswith('->8-'):
                text = text[:-4]
            return text.strip()
        return ''

    def _extract_text(self, value):
        """Extract text from a string or rich_text result."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, 'type') and value.type == 'STRING':
            return self._get_value(value)
        # If it's already processed rich_text
        return str(value) if value else None

    def alert_level(self, items):
        # items[0] is a Token with the alert level value (green/yellow/red)
        return self._get_value(items[0]) if items else 'green'

    def task_flags(self, items):
        return ('flags', [self._get_value(i) for i in items])

    def scenario_attr(self, items):
        """Handle scenario-specific attribute like 'delayed:effort 40d'."""
        scenario_id = self._get_value(items[0])
        attr_data = items[1]  # scenario_specific_attr result
        return ('scenario_attr', (scenario_id, attr_data))

    def scenario_specific_attr(self, items):
        """Handle the attribute part of scenario-specific attribute."""
        # items[0] is the result from scenario_start/end/effort/etc
        return items[0] if items else None

    def scenario_start(self, items):
        """Handle scenario-specific start attribute."""
        return ('start', items[0])  # items[0] is the date

    def scenario_end(self, items):
        """Handle scenario-specific end attribute."""
        return ('end', items[0])

    def scenario_effort(self, items):
        """Handle scenario-specific effort attribute."""
        return items[0]  # effort_value already returns ('effort', value)

    def scenario_duration(self, items):
        """Handle scenario-specific duration attribute."""
        return ('duration', items[0])

    def scenario_length(self, items):
        """Handle scenario-specific length attribute."""
        return ('length', items[0])

    # Task attribute helpers
    def effort_value(self, items):
        num = float(self._get_value(items[0]))
        unit = self._get_value(items[1])
        # Convert to hours (the base unit internally)
        # d=day (8h), w=week (40h), h=hour, m=minute, y=year (2080h)
        multipliers = {
            'd': 8,
            'w': 40,
            'h': 1,
            'm': 1/60,
            'y': 2080,
            'min': 1/60
        }
        hours = num * multipliers.get(unit.lower(), 1)
        return ('effort', hours)

    def duration_value(self, items):
        num = self._get_value(items[0])
        unit = self._get_value(items[1])
        return f"{num}{unit}"

    def depends_list(self, items):
        return ('depends', [self._get_value(i) for i in items])

    def depends_item(self, items):
        return self._get_value(items[0])

    def allocate_spec(self, items):
        resources = []
        for item in items:
            if isinstance(item, Token):
                resources.append(item.value)
        return ('allocate', resources)

    # Account
    def account(self, items):
        a_id = self._get_value(items[0])
        a_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return {
            'type': 'account',
            'id': a_id,
            'name': a_name,
            'attributes': body
        }

    def account_body(self, items):
        return list(items)

    def account_attr(self, items):
        return items[0] if items else None

    # Shift
    def shift(self, items):
        s_id = self._get_value(items[0])
        s_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return {
            'type': 'shift',
            'id': s_id,
            'name': s_name,
            'attributes': body
        }

    def shift_body(self, items):
        return list(items)

    def shift_attr(self, items):
        return items[0] if items else None

    # Reports
    def report_definition(self, items):
        return items[0] if items else None

    def textreport(self, items):
        return self._parse_report('textreport', items)

    def taskreport(self, items):
        return self._parse_report('taskreport', items)

    def resourcereport(self, items):
        return self._parse_report('resourcereport', items)

    def _parse_report(self, report_type, items):
        r_id = None
        r_name = None
        body = []
        for item in items:
            if isinstance(item, Token):
                if item.type == 'ID':
                    r_id = item.value
                elif item.type == 'STRING':
                    r_name = item.value.strip('"')
            elif isinstance(item, list):
                body = item
        return {
            'type': report_type,
            'id': r_id,
            'name': r_name,
            'attributes': body
        }

    def textreport_body(self, items):
        return list(items)

    def textreport_attr(self, items):
        return items[0] if items else None

    def textreport_header(self, items):
        return ('header', self._get_value(items[0]))

    def textreport_footer(self, items):
        return ('footer', self._get_value(items[0]))

    def textreport_center(self, items):
        return ('center', self._get_value(items[0]))

    def textreport_left(self, items):
        return ('left', self._get_value(items[0]))

    def textreport_right(self, items):
        return ('right', self._get_value(items[0]))

    def textreport_formats(self, items):
        # items[0] is the result from format_list which is already ('formats', [...])
        return items[0] if items else ('formats', [])

    def textreport_title(self, items):
        return ('title', self._get_value(items[0]))

    def taskreport_body(self, items):
        return list(items)

    def taskreport_attr(self, items):
        return items[0] if items else None

    def taskreport_header(self, items):
        return ('header', self._get_value(items[0]))

    def taskreport_footer(self, items):
        return ('footer', self._get_value(items[0]))

    def taskreport_headline(self, items):
        return ('headline', self._get_value(items[0]))

    def taskreport_caption(self, items):
        return ('caption', self._get_value(items[0]))

    def taskreport_columns(self, items):
        return items[0] if items else ('columns', [])

    def taskreport_timeformat(self, items):
        return ('timeFormat', self._get_value(items[0]))

    def taskreport_loadunit(self, items):
        return ('loadUnit', self._get_value(items[0]))

    def taskreport_hideresource(self, items):
        return ('hideResource', self._get_value(items[0]))

    def taskreport_hidetask(self, items):
        return ('hideTask', self._get_value(items[0]))

    def taskreport_sorttasks(self, items):
        return items[0] if items else ('sort', [])

    def taskreport_sortresources(self, items):
        return items[0] if items else ('sort', [])

    def taskreport_scenarios(self, items):
        return ('scenarios', [self._get_value(i) for i in items])

    def taskreport_taskroot(self, items):
        return ('taskRoot', self._get_value(items[0]))

    def taskreport_period(self, items):
        return items[0] if items else ('period', None)

    def taskreport_balance(self, items):
        return ('balance', [self._get_value(i) for i in items])

    def taskreport_journalmode(self, items):
        return ('journalMode', self._get_value(items[0]))

    def taskreport_journalattributes(self, items):
        return ('journalAttributes', [self._get_value(i) for i in items])

    def resourcereport_body(self, items):
        return list(items)

    def resourcereport_attr(self, items):
        return items[0] if items else None

    def resourcereport_header(self, items):
        return ('header', self._get_value(items[0]))

    def resourcereport_footer(self, items):
        return ('footer', self._get_value(items[0]))

    def resourcereport_headline(self, items):
        return ('headline', self._get_value(items[0]))

    def resourcereport_columns(self, items):
        return items[0] if items else ('columns', [])

    def resourcereport_loadunit(self, items):
        return ('loadUnit', self._get_value(items[0]))

    def resourcereport_hideresource(self, items):
        return ('hideResource', self._get_value(items[0]))

    def resourcereport_hidetask(self, items):
        return ('hideTask', self._get_value(items[0]))

    def resourcereport_sorttasks(self, items):
        return items[0] if items else ('sort', [])

    def resourcereport_sortresources(self, items):
        return items[0] if items else ('sort', [])

    def resourcereport_scenarios(self, items):
        return ('scenarios', [self._get_value(i) for i in items])

    # Column specifications
    def column_list(self, items):
        """Parse column list into list of column specs."""
        return ('columns', [item for item in items if item])

    def column_spec(self, items):
        """Parse a single column specification."""
        col_id = self._get_value(items[0])
        options = {}
        if len(items) > 1 and items[1]:
            options = items[1]
        return {'id': col_id, 'options': options}

    def column_options(self, items):
        """Parse column options into a dict."""
        result = {}
        for item in items:
            if isinstance(item, tuple):
                result[item[0]] = item[1]
            elif isinstance(item, Token):
                # Macro reference or similar
                result['macro'] = self._get_value(item)
        return result

    def column_option(self, items):
        """Parse a single column option."""
        if not items:
            return None
        first = items[0]
        if isinstance(first, Token):
            if first.type == 'MACRO_REF':
                return ('macro', self._get_value(first))
            # Token is often the keyword like 'title', 'width' etc
            key = self._get_value(first)
            value = self._get_value(items[1]) if len(items) > 1 else None
            return (key, value)
        return items[0] if items else None

    # Sort specifications
    def sort_list(self, items):
        """Parse sort list."""
        return ('sort', [item for item in items if item])

    def sort_item(self, items):
        """Parse a single sort item."""
        return self._get_value(items[0]) if items else None

    # Format list
    def format_list(self, items):
        """Parse formats list."""
        return ('formats', [self._get_value(i) for i in items])

    # Period specification
    def period_spec(self, items):
        """Parse period specification."""
        return ('period', self._get_value(items[0]) if items else None)

    # Navigator
    def navigator(self, items):
        n_id = self._get_value(items[0])
        body = items[1] if len(items) > 1 else []
        return {
            'type': 'navigator',
            'id': n_id,
            'attributes': body
        }

    def navigator_body(self, items):
        return list(items)

    def navigator_attr(self, items):
        return items[0] if items else None

    # Common
    def date(self, items):
        val = self._get_value(items[0])
        try:
            return datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            return datetime.strptime(val, "%Y-%m-%d-%H:%M")

    def _get_value(self, item):
        """Extract value from Token or string."""
        if isinstance(item, Token):
            val = item.value
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            return val
        elif isinstance(item, str):
            if item.startswith('"') and item.endswith('"'):
                return item[1:-1]
            return item
        return item


class ModelBuilder:
    """Build the Project model from the parsed data."""

    def __init__(self):
        self._pending_depends = []  # Store (task, depends_list) for later resolution

    def build(self, data):
        """Build a Project from parsed data."""
        if not data or not data.get('project'):
            raise ValueError("No project definition found")

        proj_data = data['project']
        timeframe = proj_data.get('timeframe', {})
        start_date = timeframe.get('start')
        duration_str = timeframe.get('duration')

        # Create project
        project = Project(
            proj_data['id'],
            proj_data['name'],
            None  # version is not used like this
        )

        # Set project start and end dates
        if start_date:
            project['start'] = start_date
            # Calculate end date from duration if provided
            if duration_str:
                from dateutil.relativedelta import relativedelta
                import re
                match = re.match(r'(\d+)([dwmy])', duration_str)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    if unit == 'd':
                        end_date = start_date + relativedelta(days=amount)
                    elif unit == 'w':
                        end_date = start_date + relativedelta(weeks=amount)
                    elif unit == 'm':
                        end_date = start_date + relativedelta(months=amount)
                    elif unit == 'y':
                        end_date = start_date + relativedelta(years=amount)
                    else:
                        end_date = start_date
                    project['end'] = end_date

        # Apply project attributes
        self._apply_project_attributes(project, proj_data.get('attributes', []))

        # Apply global attributes
        self._apply_global_attributes(project, data.get('global_attributes', []))

        # Apply property declarations (resources, tasks, accounts)
        for prop in data.get('property_declarations', []):
            self._create_property(project, prop)

        # Resolve dependencies after all tasks are created
        self._resolve_dependencies(project)

        # Create reports
        for report_data in data.get('reports', []):
            self._create_report(project, report_data)

        return project

    def _resolve_dependencies(self, project):
        """Resolve task dependency references to actual Task objects."""
        for task, depends_list in self._pending_depends:
            resolved = []
            for dep_ref in depends_list:
                dep_task = self._resolve_task_reference(project, task, dep_ref)
                if dep_task:
                    resolved.append(dep_task)
            if resolved:
                # Set dependencies for all scenarios
                for scIdx in range(project.scenarioCount()):
                    task[('depends', scIdx)] = resolved

    def _resolve_task_reference(self, project, from_task, ref):
        """Resolve a task reference string to a Task object.

        Reference formats:
        - "!taskid" - sibling (same parent)
        - "!!taskid" - uncle (parent's sibling)
        - "taskid" - from project root
        - "parent.child" - path from root
        """
        if not ref:
            return None

        # Count leading exclamation marks to determine scope
        level = 0
        while ref.startswith('!'):
            level += 1
            ref = ref[1:]

        # Find base task to search from
        if level > 0:
            # Go up level times from current task's parent
            base = from_task.parent
            for _ in range(level - 1):
                if base and base.parent:
                    base = base.parent
                else:
                    base = None
                    break
        else:
            base = None  # Search from root

        # Now find the task by ID
        # Handle path references like "parent.child"
        parts = ref.split('.')

        if base:
            # Search in base's children
            current = base
            for part in parts:
                found = None
                for child in current.children:
                    if child.id == part:
                        found = child
                        break
                if found:
                    current = found
                else:
                    return None
            return current
        else:
            # Search from project root
            for task in project.tasks:
                if task.id == parts[0]:
                    if len(parts) == 1:
                        return task
                    # Navigate path
                    current = task
                    for part in parts[1:]:
                        found = None
                        for child in current.children:
                            if child.id == part:
                                found = child
                                break
                        if found:
                            current = found
                        else:
                            return None
                    return current
        return None

    def _apply_project_attributes(self, project, attributes):
        """Apply attributes to the project."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                if key == 'scenario':
                    self._create_scenario(project, value)
                elif key == 'extend':
                    pass  # Handle extensions later
                else:
                    try:
                        project[key] = value
                    except (ValueError, KeyError):
                        pass

    def _apply_global_attributes(self, project, attributes):
        """Apply global attributes to the project."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                try:
                    project[key] = value
                except (ValueError, KeyError):
                    pass

    def _create_scenario(self, project, scenario_data, parent=None):
        """Create a scenario in the project.

        Args:
            project: The project
            scenario_data: Dict with 'id', 'name', 'children'
            parent: Parent scenario for nested scenarios
        """
        from rodmena_resource_management.core.scenario import Scenario

        s_id = scenario_data.get('id')
        s_name = scenario_data.get('name', '').strip('"')
        children = scenario_data.get('children', [])

        # Clear default scenario on first scenario definition
        if parent is None and not hasattr(self, '_scenarios_cleared'):
            # Remove the default 'plan' scenario
            default_plan = project.scenarios['plan']
            if default_plan:
                project.scenarios.removeProperty(default_plan)
            self._scenarios_cleared = True

        # Create the scenario
        scenario = Scenario(project, s_id, s_name, parent)

        # Create nested child scenarios
        for child in children:
            if isinstance(child, tuple) and child[0] == 'scenario':
                self._create_scenario(project, child[1], scenario)

    def _create_property(self, parent, prop_data):
        """Create a property (resource, task, account) in the parent."""
        if not isinstance(prop_data, dict):
            return

        prop_type = prop_data.get('type')
        prop_id = prop_data.get('id')
        prop_name = prop_data.get('name')
        attributes = prop_data.get('attributes', [])

        # Determine project reference
        project = parent if isinstance(parent, Project) else parent.project

        if prop_type == 'task':
            obj = Task(
                project,
                prop_id,
                prop_name,
                parent if isinstance(parent, Task) else None
            )
        elif prop_type == 'resource':
            obj = Resource(
                project,
                prop_id,
                prop_name,
                parent if isinstance(parent, Resource) else None
            )
        elif prop_type == 'account':
            # Skip accounts for now - need Account class
            return
        else:
            return

        # Apply attributes to the created object
        self._apply_property_attributes(obj, attributes, prop_type)

    def _apply_property_attributes(self, obj, attributes, prop_type):
        """Apply attributes to a property object."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, dict):
                # Nested property (e.g., nested resource or task)
                self._create_property(obj, attr)
            elif isinstance(attr, tuple):
                key, value = attr
                if key == 'email':
                    obj['email'] = value
                elif key == 'rate':
                    obj['rate'] = value
                elif key == 'effort':
                    # Set for all scenarios (no prefix means apply to all)
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('effort', scIdx)] = value
                elif key == 'depends':
                    # Store for later resolution (after all tasks created)
                    self._pending_depends.append((obj, value))
                elif key == 'allocate':
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('allocate', scIdx)] = value
                elif key == 'start':
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('start', scIdx)] = value
                elif key == 'end':
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('end', scIdx)] = value
                elif key == 'milestone':
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('milestone', scIdx)] = value
                elif key == 'priority':
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('priority', scIdx)] = value
                elif key == 'scenario_attr':
                    # Handle scenario-specific attributes like ('delayed', ('effort', 320))
                    scenario_id, attr_data = value
                    scenario_idx = self._get_scenario_index(obj.project, scenario_id)
                    if scenario_idx is not None and attr_data:
                        if isinstance(attr_data, tuple):
                            attr_key, attr_value = attr_data
                            obj[(attr_key, scenario_idx)] = attr_value
                elif key == 'journalentry':
                    # Create a journal entry for this task
                    self._create_journal_entry(obj, value)
                elif key == 'charge':
                    # charge is a tuple (amount, mode) where mode is 'onstart', 'onend', or 'perday'
                    amount, mode = value
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('charge', scIdx)] = amount
                        if mode:
                            obj[('chargeMode', scIdx)] = mode
                elif key == 'chargeset':
                    # chargeset specifies which account to charge to
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[('chargeset', scIdx)] = value
                else:
                    try:
                        obj[key] = value
                    except (ValueError, KeyError, AttributeError):
                        pass

    def _get_scenario_index(self, project, scenario_id):
        """Get the index of a scenario by its ID."""
        for i, scenario in enumerate(project.scenarios):
            if scenario.id == scenario_id:
                return i
        return None

    def _create_journal_entry(self, task, entry_data):
        """Create a journal entry for a task.

        Args:
            task: The Task object this entry belongs to
            entry_data: Dict with 'date', 'headline', and 'body' keys
        """
        from rodmena_resource_management.core.journal import JournalEntry, AlertLevel

        journal = task.project.attributes.get('journal')
        if journal is None:
            return

        date = entry_data.get('date')
        headline = entry_data.get('headline', '')
        body = entry_data.get('body', {})

        # Create the journal entry
        entry = journal.create_entry(date, headline, task)

        # Set body attributes
        if body.get('author'):
            # Look up the author resource
            author_id = body['author']
            author = task.project.resources[author_id] if author_id else None
            entry.author = author

        alert_str = body.get('alert', 'green')
        if alert_str == 'red':
            entry.alert_level = AlertLevel.RED
        elif alert_str == 'yellow':
            entry.alert_level = AlertLevel.YELLOW
        else:
            entry.alert_level = AlertLevel.GREEN

        entry.summary = body.get('summary')
        entry.details = body.get('details')

    def _create_report(self, project, report_data, parent=None):
        """Create a Report from parsed data.

        Args:
            project: The Project object
            report_data: Dict with 'type', 'id', 'name', 'attributes'
            parent: Optional parent report for nested reports
        """
        from rodmena_resource_management.report.report import Report, ReportType, ReportFormat

        report_type = report_data.get('type')
        r_id = report_data.get('id') or ''
        r_name = report_data.get('name') or r_id

        # Create the report
        report = Report(project, r_id, r_name, parent)

        # Set report type
        if report_type == 'taskreport':
            report.type_spec = ReportType.TASK_REPORT
        elif report_type == 'resourcereport':
            report.type_spec = ReportType.RESOURCE_REPORT
        elif report_type == 'textreport':
            report.type_spec = ReportType.TEXT_REPORT
        elif report_type == 'accountreport':
            report.type_spec = ReportType.ACCOUNT_REPORT

        # Default to HTML format if not specified
        default_formats = [ReportFormat.HTML]

        # Process attributes
        attributes = report_data.get('attributes', [])
        for attr in attributes:
            self._apply_report_attribute(report, attr, default_formats)

        # If no formats were set, use defaults
        if not report.get('formats'):
            report['formats'] = default_formats

        return report

    def _apply_report_attribute(self, report, attr, default_formats):
        """Apply a single attribute to a report.

        Args:
            report: The Report object
            attr: The attribute (can be tuple, dict, Token, Tree, or string)
            default_formats: List to accumulate format types
        """
        from lark import Token, Tree
        from rodmena_resource_management.report.report import ReportFormat

        if attr is None:
            return

        if isinstance(attr, dict):
            # Nested report definition
            attr_type = attr.get('type')
            if attr_type in ['taskreport', 'resourcereport', 'textreport', 'accountreport']:
                self._create_report(report.project, attr, report)
            return

        if isinstance(attr, tuple):
            key, value = attr
            if key == 'columns':
                # value is list of column specs
                report['columns'] = value
            elif key == 'formats':
                # value is list of format strings
                formats = []
                for fmt_str in value:
                    fmt_str = fmt_str.lower()
                    if fmt_str == 'html':
                        formats.append(ReportFormat.HTML)
                    elif fmt_str == 'csv':
                        formats.append(ReportFormat.CSV)
                    elif fmt_str == 'ical':
                        formats.append(ReportFormat.ICAL)
                    elif fmt_str == 'tjp':
                        formats.append(ReportFormat.TJP)
                    elif fmt_str == 'niku':
                        formats.append(ReportFormat.NIKU)
                report['formats'] = formats
            elif key == 'sort':
                report['sort'] = value
            elif key == 'period':
                report['period'] = value
            else:
                # Generic attribute
                try:
                    report[key] = value
                except (ValueError, KeyError, AttributeError):
                    pass
            return

        if isinstance(attr, Token):
            # Tokens are typically attribute values that need context
            # They represent things like scenarios, hideresource, etc.
            token_type = attr.type
            token_val = attr.value
            if token_val.startswith('"') and token_val.endswith('"'):
                token_val = token_val[1:-1]

            if token_type == 'STRING':
                # This could be timeformat, title, headline, etc.
                # Without knowing the context, we can't assign it properly
                # These are usually preceded by a keyword in the grammar
                pass
            elif token_type == 'ID':
                # Could be scenarios, loadunit, etc.
                # Common IDs in reports
                if token_val in ['plan', 'delayed']:
                    # scenarios attribute
                    existing = report.get('scenarios') or []
                    for i, scenario in enumerate(report.project.scenarios):
                        if scenario.id == token_val:
                            existing.append(i)
                            break
                    report['scenarios'] = existing
                elif token_val in ['days', 'hours', 'weeks', 'months', 'shortauto', 'longauto']:
                    # loadUnit
                    report['loadUnit'] = token_val
            elif token_type == 'FILTER_EXPR':
                # Filter expression for hideResource, hideTask, etc.
                # Store as filter
                if token_val.startswith('@') or token_val.startswith('~'):
                    # Could be hideResource or hideTask - store both
                    if not report.get('hideResource'):
                        report['hideResource'] = token_val
                    elif not report.get('hideTask'):
                        report['hideTask'] = token_val
            elif token_type == 'TASK_PATH':
                # taskRoot
                report['taskRoot'] = token_val
            return

        if isinstance(attr, Tree):
            # Handle Tree objects (shouldn't happen now that we transform them)
            tree_data = attr.data
            if tree_data == 'column_list':
                columns = []
                for child in attr.children:
                    if isinstance(child, Tree) and child.data == 'column_spec':
                        col_id = None
                        col_opts = {}
                        for cc in child.children:
                            if isinstance(cc, Token) and cc.type == 'ID':
                                col_id = cc.value
                            elif isinstance(cc, Tree) and cc.data == 'column_options':
                                # Parse options
                                pass
                        if col_id:
                            columns.append({'id': col_id, 'options': col_opts})
                report['columns'] = columns
            elif tree_data == 'sort_list':
                sorts = []
                for child in attr.children:
                    if isinstance(child, Tree) and child.data == 'sort_item':
                        for cc in child.children:
                            if isinstance(cc, Token):
                                sorts.append(cc.value)
                report['sort'] = sorts
            return

        if isinstance(attr, str):
            # Rich text content (header, footer, headline, etc.)
            # Without context, we try to determine what it is
            if '----' in attr:
                report['footer'] = attr
            elif '====' in attr or '===' in attr:
                # Contains headlines, could be header
                if not report.get('header'):
                    report['header'] = attr
                elif not report.get('headline'):
                    report['headline'] = attr
            else:
                # Generic rich text, could be any of header/footer/headline/caption
                if not report.get('header'):
                    report['header'] = attr


class ProjectFileParser:
    """Parser for TJP project files."""

    def __init__(self):
        grammar_path = os.path.join(os.path.dirname(__file__), 'tjp.lark')
        with open(grammar_path, 'r') as f:
            self.grammar = f.read()
        self.parser = Lark(self.grammar, start='start', parser='lalr')

    def parse(self, text, preprocess_macros=True, schedule=True):
        """Parse TJP text and return a Project object.

        Args:
            text: The TJP file content
            preprocess_macros: If True, expand macros before parsing
            schedule: If True, schedule the project after parsing to compute task dates

        Returns:
            A Project object
        """
        # Preprocess macros
        if preprocess_macros:
            text = preprocess_tjp(text)

        tree = self.parser.parse(text)
        data = TJPTransformer().transform(tree)
        builder = ModelBuilder()
        project = builder.build(data)

        # Schedule the project to compute task dates
        if schedule:
            project.schedule()

        return project
