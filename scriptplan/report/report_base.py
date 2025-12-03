"""
ReportBase - Abstract base class for report content generators.

This module provides the ReportBase class which is the abstract base for all
kinds of report content generators. Derived classes must implement the
generate_intermediate_format function as well as to_json, to_csv, etc.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from scriptplan.core.property import PropertyList
    from scriptplan.report.report import Report


class ReportBase(ABC):
    """
    Abstract base class for all report content generators.

    This class provides common functionality for filtering property lists
    and generating the intermediate format that can be converted to
    various output formats (JSON, CSV, etc.).

    Attributes:
        report: Reference to the parent Report object
        project: Reference to the Project object
    """

    def __init__(self, report: "Report"):
        """
        Initialize the ReportBase.

        Args:
            report: The parent Report object
        """
        self.report = report
        self.project = report.project

    def a(self, attribute: str) -> Any:
        """
        Convenience function to access a report attribute.

        Args:
            attribute: Name of the attribute to access

        Returns:
            The attribute value
        """
        return self.report.get(attribute)

    def get_scenario_indices(self) -> list[int]:
        """
        Get scenario indices from the report's scenarios attribute.

        The 'scenarios' attribute can contain either scenario names (strings)
        or scenario indices (integers). This method resolves all names to
        their corresponding indices.

        Returns:
            List of scenario indices (integers). Defaults to [0] if not set.
        """
        scenarios = self.a("scenarios") or []
        if not scenarios:
            return [0]

        result = []
        for scen in scenarios:
            if isinstance(scen, int):
                result.append(scen)
            elif isinstance(scen, str):
                # Resolve scenario name to index
                for idx, proj_scen in enumerate(self.project.scenarios):
                    if proj_scen.id == scen:
                        result.append(idx)
                        break
                else:
                    # Scenario name not found, try to parse as int
                    from contextlib import suppress

                    with suppress(ValueError):
                        result.append(int(scen))

        return result if result else [0]

    @abstractmethod
    def generate_intermediate_format(self) -> None:
        """
        Generate the intermediate format representation.

        This method must be implemented by derived classes to generate
        an output-format-agnostic representation of the report data.
        """
        # Process RichText elements like header, footer, etc.
        query = None
        if self.project.reportContexts:
            query = self.project.reportContexts[-1].query

        for name in ["header", "left", "center", "right", "footer", "prolog", "headline", "caption", "epilog"]:
            text = self.a(name)
            if text and query and hasattr(text, "setQuery"):
                text.setQuery(query)

    @abstractmethod
    def to_json(self) -> Optional[dict[str, Any]]:
        """
        Convert the intermediate format to JSON.

        Returns:
            Dictionary suitable for JSON serialization or None
        """
        pass

    def to_csv(self) -> Optional[list[list[str]]]:
        """
        Convert the intermediate format to CSV.

        Returns:
            List of rows (each row is a list of column values)
        """
        return None

    def filter_account_list(
        self,
        account_list: "PropertyList",
        hide_expr: Any = None,
        rollup_expr: Any = None,
        open_nodes: Optional[list[Any]] = None,
    ) -> "PropertyList":
        """
        Filter an account list based on hide/rollup expressions.

        Takes the complete account list and removes all accounts that are
        matching the hide expression, the rollup expression or are not a
        descendant of accountroot.

        Args:
            account_list: List of accounts to filter
            hide_expr: Expression to determine which accounts to hide
            rollup_expr: Expression to determine which accounts to roll up
            open_nodes: List of nodes to keep expanded

        Returns:
            Filtered PropertyList
        """
        from scriptplan.core.property import PropertyList

        result: PropertyList = PropertyList(account_list)

        account_root = self.a("accountRoot")
        if account_root:
            # Remove accounts not descended from accountRoot
            result.delete_if(lambda acc: not self._is_child_of(acc, account_root))

        return self._standard_filter_ops(result, hide_expr, rollup_expr, open_nodes, None, account_root)

    def filter_task_list(
        self,
        task_list: "PropertyList",
        resource: Any = None,
        hide_expr: Any = None,
        rollup_expr: Any = None,
        open_nodes: Optional[list[Any]] = None,
    ) -> "PropertyList":
        """
        Filter a task list based on hide/rollup expressions.

        Takes the complete task list and removes all tasks that are matching
        the hide expression, the rollup expression or are not a descendant
        of taskroot. If resource is not None, a task is only included if
        the resource is allocated to it.

        Args:
            task_list: List of tasks to filter
            resource: Optional resource filter
            hide_expr: Expression to determine which tasks to hide
            rollup_expr: Expression to determine which tasks to roll up
            open_nodes: List of nodes to keep expanded

        Returns:
            Filtered PropertyList
        """
        from scriptplan.core.property import PropertyList

        result: PropertyList = PropertyList(task_list)

        task_root = self.a("taskRoot")
        if task_root:
            result.delete_if(lambda task: not self._is_child_of(task, task_root))

        if resource:
            # Filter to tasks that have the resource allocated
            scenario_indices = self.get_scenario_indices()
            start = self.a("start")
            end = self.a("end")

            def has_resource(task: Any) -> bool:
                for scenario_idx in scenario_indices:
                    if hasattr(task, "hasResourceAllocated") and task.hasResourceAllocated(
                        scenario_idx, (start, end), resource
                    ):
                        return True
                return False

            result.delete_if(lambda task: not has_resource(task))

        return self._standard_filter_ops(result, hide_expr, rollup_expr, open_nodes, resource, task_root)

    def filter_resource_list(
        self,
        resource_list: "PropertyList",
        task: Any = None,
        hide_expr: Any = None,
        rollup_expr: Any = None,
        open_nodes: Optional[list[Any]] = None,
    ) -> "PropertyList":
        """
        Filter a resource list based on hide/rollup expressions.

        Takes the complete resource list and removes all resources that are
        matching the hide expression, the rollup expression or are not a
        descendant of resourceroot. If task is not None, a resource is only
        included if it is assigned to the task.

        Args:
            resource_list: List of resources to filter
            task: Optional task filter
            hide_expr: Expression to determine which resources to hide
            rollup_expr: Expression to determine which resources to roll up
            open_nodes: List of nodes to keep expanded

        Returns:
            Filtered PropertyList
        """
        from scriptplan.core.property import PropertyList

        result: PropertyList = PropertyList(resource_list)

        resource_root = self.a("resourceRoot")
        if resource_root:
            result.delete_if(lambda res: not self._is_child_of(res, resource_root))

        if task:
            # Filter to resources assigned to the task
            scenario_indices = self.get_scenario_indices()
            start = self.a("start")
            end = self.a("end")

            def is_assigned(resource: Any) -> bool:
                for scenario_idx in scenario_indices:
                    if hasattr(task, "hasResourceAllocated") and task.hasResourceAllocated(
                        scenario_idx, (start, end), resource
                    ):
                        return True
                return False

            result.delete_if(lambda res: not is_assigned(res))

        return self._standard_filter_ops(result, hide_expr, rollup_expr, open_nodes, task, resource_root)

    def _standard_filter_ops(
        self,
        items: "PropertyList",
        hide_expr: Any,
        rollup_expr: Any,
        open_nodes: Optional[list[Any]],
        scope_property: Any,
        root: Any,
    ) -> "PropertyList":
        """
        Apply standard filtering operations to a property list.

        Args:
            items: The property list to filter
            hide_expr: Expression determining what to hide
            rollup_expr: Expression determining what to roll up
            open_nodes: List of explicitly open nodes
            scope_property: The scope property for queries
            root: The root property

        Returns:
            Filtered PropertyList
        """
        # Get query copy for evaluating expressions
        query = None
        if self.project.reportContexts:
            query = self.project.reportContexts[-1].query.copy()
            query.scope_property = scope_property

        # Remove hidden properties
        if hide_expr and query:

            def should_hide(prop: Any) -> bool:
                query.property = prop
                return bool(self._eval_expression(hide_expr, query))

            items.delete_if(should_hide)

        # Remove children of rolled-up properties
        if rollup_expr or open_nodes:

            def should_remove_child(prop: Any) -> bool:
                parent = prop.parent
                while parent:
                    if query:
                        query.property = parent

                    if open_nodes and [parent, scope_property] not in open_nodes:
                        # If open_nodes specified, only listed nodes are unrolled
                        return True
                    elif rollup_expr and bool(self._eval_expression(rollup_expr, query)):
                        # Roll up based on expression
                        return True

                    parent = parent.parent
                return False

            items.delete_if(should_remove_child)

        # Re-add parents in tree mode (if applicable)
        if hasattr(items, "tree_mode") and items.tree_mode():
            parents: list[Any] = []
            for prop in items:
                parent = prop.parent
                while parent:
                    if parent not in items and parent not in parents:
                        parents.append(parent)
                    if parent == root:
                        break
                    parent = parent.parent
            # Manually add parents since extend() is not typed
            for parent in parents:
                items.append(parent)

        return items

    def _is_child_of(self, node: Any, parent: Any) -> bool:
        """
        Check if node is a descendant of parent.

        Args:
            node: The potential child node
            parent: The potential parent node

        Returns:
            True if node is a descendant of parent
        """
        if hasattr(node, "isChildOf"):
            result: Any = node.isChildOf(parent)
            return bool(result)

        # Manual check
        current = node
        while current:
            if current == parent:
                return True
            current = current.parent if hasattr(current, "parent") else None
        return False

    def _eval_expression(self, expr: Any, query: Any) -> bool:
        """
        Evaluate a logical expression.

        Args:
            expr: The expression to evaluate
            query: The query context

        Returns:
            Boolean result of expression evaluation
        """
        if hasattr(expr, "eval"):
            result: Any = expr.eval(query)
            return bool(result)
        if callable(expr):
            result = expr(query)
            return bool(result)
        return bool(expr)
