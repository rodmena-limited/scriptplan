"""
ReportContext - Manages context and state during report generation.

This module provides the ReportContext class which holds settings used during
report generation. Reports can be nested, so multiple ReportContext objects
can exist at a time, but there is always one current context accessible via
Project.reportContexts[-1].
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from scriptplan.core.project import Project


class Query:
    """
    Query object for accessing property attributes during report generation.

    This class provides a unified interface for querying task/resource attributes
    with proper formatting and scenario handling.
    """

    def __init__(self, attrs: Optional[dict[str, Any]] = None):
        self.project = None
        self.property = None
        self.scope_property = None
        self.scenario_idx = None
        self.attributeId = None  # Attribute ID to query
        self.result = None  # Result of the query
        self.load_unit = "days"
        self.number_format = None
        self.time_format = "%Y-%m-%d"
        self.currency_format = None
        self.start = None
        self.end = None
        self.hide_journal_entry = None
        self.journal_mode = None
        self.journal_attributes = None
        self.sort_journal_entries = None
        self.cost_account = None
        self.revenue_account = None

        if attrs:
            for key, value in attrs.items():
                attr_name = self._camel_to_snake(key)
                if hasattr(self, attr_name):
                    setattr(self, attr_name, value)

    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def copy(self) -> "Query":
        """Create a copy of this Query."""
        new_query = Query()
        new_query.project = self.project
        new_query.property = self.property
        new_query.scope_property = self.scope_property
        new_query.scenario_idx = self.scenario_idx
        new_query.attributeId = self.attributeId
        new_query.result = self.result
        new_query.load_unit = self.load_unit
        new_query.number_format = self.number_format
        new_query.time_format = self.time_format
        new_query.currency_format = self.currency_format
        new_query.start = self.start
        new_query.end = self.end
        new_query.hide_journal_entry = self.hide_journal_entry
        new_query.journal_mode = self.journal_mode
        new_query.journal_attributes = self.journal_attributes
        new_query.sort_journal_entries = self.sort_journal_entries
        new_query.cost_account = self.cost_account
        new_query.revenue_account = self.revenue_account
        return new_query

    def process(self) -> Any:
        """
        Process the query and return the result.

        This is the main entry point for executing a query against a property.
        """
        if not self.property:
            self.result = None
            return None

        # If attributeId is set, fetch the value from the property
        if self.attributeId:
            try:
                # Use scenario_idx if available, otherwise just get the attribute
                if self.scenario_idx is not None:
                    # Ensure property supports scenario indexing
                    # We pass scenario_idx as a tuple key if the property supports it
                    # But property.get() usually takes (name, scIdx) or just name
                    # Let's look at how PropertyTreeNode.get is implemented
                    # It usually takes (attribute_name, scenario_idx)

                    # Note: property.py logic sets self.scenarioIdx which maps to self.scenario_idx here
                    # property.py calls self._query.process()

                    val = self.property.get(self.attributeId, self.scenario_idx)
                else:
                    val = self.property.get(self.attributeId)

                self.result = val
            except Exception:
                self.result = None

        return self.result

    def to_sort(self) -> Any:
        """
        Return a sortable representation of the query result.
        """
        return self.result


class ReportContext:
    """
    Context object for report generation.

    The ReportContext holds settings and state used during report generation.
    Reports can be nested, creating a stack of contexts. The current context
    is always accessible via Project.reportContexts[-1].

    Attributes:
        project: Reference to the Project object
        report: Reference to the Report being generated
        query: Query object for attribute access
        tasks: List of tasks in scope for this report
        resources: List of resources in scope for this report
        dynamic_report_id: Unique identifier for nested reports
        child_report_counter: Counter for generating child report IDs
        attribute_backup: Backup of modified attributes for restoration
    """

    def __init__(self, project: "Project", report: Any):
        """
        Initialize a new ReportContext.

        Args:
            project: The Project object
            report: The Report object being generated
        """
        self.project = project
        self.report = report
        self.child_report_counter = 0
        self.attribute_backup = None

        # Build query attributes from report settings
        query_attrs = {
            "project": self.project,
            "loadUnit": self._get_report_attr("loadUnit", "days"),
            "numberFormat": self._get_report_attr("numberFormat"),
            "timeFormat": self._get_report_attr("timeFormat", "%Y-%m-%d"),
            "currencyFormat": self._get_report_attr("currencyFormat"),
            "start": self._get_report_attr("start"),
            "end": self._get_report_attr("end"),
            "hideJournalEntry": self._get_report_attr("hideJournalEntry"),
            "journalMode": self._get_report_attr("journalMode"),
            "journalAttributes": self._get_report_attr("journalAttributes"),
            "sortJournalEntries": self._get_report_attr("sortJournalEntries"),
            "costAccount": self._get_report_attr("costaccount"),
            "revenueAccount": self._get_report_attr("revenueaccount"),
        }
        self.query = Query(query_attrs)

        # Get parent context if exists
        parent = project.reportContexts[-1] if project.reportContexts else None

        if parent:
            # For interactive/nested reports, generate a unique ID based on
            # parent's ID and child counter
            self.dynamic_report_id = f"{parent.dynamic_report_id}.{parent.child_report_counter}"
            parent.child_report_counter += 1

            # Inherit task and resource lists from parent
            self.tasks = list(parent.tasks) if parent.tasks else []
            self.resources = list(parent.resources) if parent.resources else []
        else:
            # Root context - ID is "0", get all tasks/resources from project
            self.dynamic_report_id = "0"
            self.tasks = list(project.tasks) if project.tasks else []
            self.resources = list(project.resources) if project.resources else []

    def _get_report_attr(self, attr_name: str, default: Any = None) -> Any:
        """
        Get an attribute from the report.

        Args:
            attr_name: Name of the attribute
            default: Default value if attribute not found

        Returns:
            The attribute value or default
        """
        try:
            if hasattr(self.report, "get"):
                val = self.report.get(attr_name)
                return val if val is not None else default
        except (ValueError, KeyError, AttributeError):
            pass
        return default

    def push(self) -> "ReportContext":
        """
        Push this context onto the project's context stack.

        Returns:
            self for chaining
        """
        self.project.reportContexts.append(self)
        return self

    def pop(self) -> "ReportContext":
        """
        Pop this context from the project's context stack.

        Returns:
            self for chaining
        """
        if self.project.reportContexts and self.project.reportContexts[-1] is self:
            self.project.reportContexts.pop()
        return self

    def backup_attributes(self, property_node: Any) -> None:
        """
        Backup attributes from a property node for later restoration.

        Args:
            property_node: The property node whose attributes to backup
        """
        if hasattr(property_node, "backupAttributes"):
            self.attribute_backup = property_node.backupAttributes()

    def restore_attributes(self, property_node: Any) -> None:
        """
        Restore previously backed up attributes to a property node.

        Args:
            property_node: The property node to restore attributes to
        """
        if self.attribute_backup and hasattr(property_node, "restoreAttributes"):
            property_node.restoreAttributes(self.attribute_backup)
            self.attribute_backup = None
