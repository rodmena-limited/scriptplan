"""Building Report objects from the parsed report blocks.

A report block names its type, its columns, how the rows are sorted and
filtered, and which formats to write. Turning that into a Report is separate
from turning the rest of the file into a Project, and long enough to live on
its own.
"""

from __future__ import annotations

import contextlib
from typing import Any

from lark import Token, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.exceptions import SemanticError, UnsupportedFormatError
from scriptplan.core.project import Project
from scriptplan.report.logical_expression import parse_expression

__all__ = [
    "apply_report_attribute",
    "create_report",
    "resolve_sort_criteria",
]


def create_report(builder: Any, project: Project, report_data: dict[str, Any], parent: Any | None = None) -> Any:
    """Create a Report from parsed data.

    Args:
        project: The Project object
        report_data: Dict with 'type', 'id', 'name', 'attributes'
        parent: Optional parent report for nested reports
    """
    from scriptplan.report.report import Report, ReportFormat, ReportType

    report_type = report_data.get("type")
    r_id = report_data.get("id") or ""
    r_name = report_data.get("name") or r_id

    # Create the report
    report = Report(project, r_id, r_name, parent)

    # Set report type
    if report_type == "taskreport":
        report.type_spec = ReportType.TASK_REPORT
    elif report_type == "resourcereport":
        report.type_spec = ReportType.RESOURCE_REPORT
    elif report_type == "textreport":
        report.type_spec = ReportType.TEXT_REPORT
    elif report_type == "accountreport":
        report.type_spec = ReportType.ACCOUNT_REPORT

    # Default to JSON format if not specified
    default_formats = [ReportFormat.JSON]

    # Process attributes
    attributes = report_data.get("attributes", [])
    for attr in attributes:
        apply_report_attribute(builder, report, attr, default_formats)

    # If no formats were set, use defaults
    if not report.get("formats"):
        report["formats"] = default_formats

    return report


def apply_report_attribute(builder: Any, report: Any, attr: Any, default_formats: list[Any]) -> None:
    """Apply a single attribute to a report.

    Args:
        report: The Report object
        attr: The attribute (can be tuple, dict, Token, Tree, or string)
        default_formats: List to accumulate format types
    """

    from scriptplan.report.report import ReportFormat

    if attr is None:
        return

    if isinstance(attr, dict):
        # Nested report definition
        attr_type = attr.get("type")
        if attr_type in ["taskreport", "resourcereport", "textreport", "accountreport"]:
            create_report(builder, report.project, attr, report)
        return

    if isinstance(attr, tuple):
        key, value = attr
        if key == "columns":
            # value is list of column specs
            report["columns"] = value
        elif key == "formats":
            # Only the formats ScriptPlan can actually write are accepted.
            # The others used to parse, write no file, and leave the CLI
            # reporting a scheduling problem that did not exist.
            supported = {"json": ReportFormat.JSON, "csv": ReportFormat.CSV}
            formats = []
            for raw in value:
                name = str(raw).lower()
                if name not in supported:
                    raise UnsupportedFormatError(
                        f"report '{report.id}' asks for '{name}' output, which ScriptPlan "
                        f"does not produce. Supported formats: "
                        f"{', '.join(sorted(supported))}."
                    )
                formats.append(supported[name])
            report["formats"] = formats
        elif key in ("sortTasks", "sortResources", "sort"):
            report[key] = resolve_sort_criteria(builder, report.project, value)
        elif key == "period":
            report["period"] = value
        else:
            # Generic attribute
            with contextlib.suppress(ValueError, KeyError, AttributeError):
                report[key] = value
        return

    if isinstance(attr, Token):
        # Tokens are typically attribute values that need context
        # They represent things like scenarios, hideresource, etc.
        token_type = attr.type
        token_val = attr.value
        if token_val.startswith('"') and token_val.endswith('"'):
            token_val = token_val[1:-1]

        if token_type == "STRING":
            # This could be timeformat, title, headline, etc.
            # Without knowing the context, we can't assign it properly
            # These are usually preceded by a keyword in the grammar
            pass
        elif token_type == "ID":
            # Could be scenarios, loadunit, etc.
            # Common IDs in reports
            if token_val in ["plan", "delayed"]:
                # scenarios attribute
                existing = report.get("scenarios") or []
                for i, scenario in enumerate(report.project.scenarios):
                    if scenario.id == token_val:
                        existing.append(i)
                        break
                report["scenarios"] = existing
            elif token_val in ["days", "hours", "weeks", "months", "shortauto", "longauto"]:
                # loadUnit
                report["loadUnit"] = token_val
        elif token_type == "FILTER_EXPR":
            # A bare filter expression with no keyword in front of it. It
            # is parsed here so a malformed one is rejected at parse time
            # rather than silently hiding every row.
            expression = parse_expression(token_val.lstrip("@"))
            if not report.get("hideTask"):
                report["hideTask"] = expression
            elif not report.get("hideResource"):
                report["hideResource"] = expression
        elif token_type == "TASK_PATH":
            # taskRoot
            report["taskRoot"] = token_val
        return

    if isinstance(attr, Tree):
        # Handle Tree objects (shouldn't happen now that we transform them)
        tree_data = attr.data
        if tree_data == "column_list":
            columns = []
            for child in attr.children:
                if isinstance(child, Tree) and child.data == "column_spec":
                    col_id = None
                    col_opts: dict[str, Any] = {}
                    for cc in child.children:
                        if isinstance(cc, Token) and cc.type == "ID":
                            col_id = cc.value
                        elif isinstance(cc, Tree) and cc.data == "column_options":
                            # Parse options
                            pass
                    if col_id:
                        columns.append({"id": col_id, "options": col_opts})
            report["columns"] = columns
        elif tree_data == "sort_list":
            sorts = []
            for child in attr.children:
                if isinstance(child, Tree) and child.data == "sort_item":
                    for cc in child.children:
                        if isinstance(cc, Token):
                            sorts.append(cc.value)
            report["sort"] = sorts
        return

    if isinstance(attr, str):
        # Rich text content (header, footer, headline, etc.)
        # Without context, we try to determine what it is
        if "----" in attr:
            report["footer"] = attr
        elif "====" in attr or "===" in attr:
            # Contains headlines, could be header
            if not report.get("header"):
                report["header"] = attr
            elif not report.get("headline"):
                report["headline"] = attr
        else:
            # Generic rich text, could be any of header/footer/headline/caption
            if not report.get("header"):
                report["header"] = attr


def resolve_sort_criteria(builder: Any, project: Project, criteria: Any) -> list[Any]:
    """Turn parsed sort criteria into (attribute, ascending, scenarioIdx)."""
    resolved: list[tuple[str, bool, int]] = []
    for item in criteria or []:
        if not isinstance(item, tuple) or len(item) != 3:
            continue
        attribute, ascending, scenario = item
        scenario_idx = -1
        if scenario:
            index = builder._get_scenario_index(project, str(scenario))
            if index is None:
                raise SemanticError(
                    f"sort criterion '{scenario}.{attribute}' names a scenario that is not defined"
                )
            scenario_idx = index
        resolved.append((str(attribute), bool(ascending), scenario_idx))
    return resolved
