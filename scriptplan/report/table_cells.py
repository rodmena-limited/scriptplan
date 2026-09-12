"""What goes in one cell of a report, and how it is written.

A column is either an attribute of the property, or something the report works
out: what a task cost, what it earned, how long it actually took. Times are
rendered in the report's timezone, else the project's -- scheduling happens in
UTC, but a reader wrote their file in their own zone and is shown it back.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "cell_value",
    "cost_value",
    "duration_value",
    "format_value",
    "revenue_value",
]


def cell_value(report: Any, property_node: Any, column_id: str, scenario_idx: int) -> Any:
    """
    Get the value for a cell.

    Args:
        property_node: The property
        column_id: Column identifier
        scenario_idx: Scenario index

    Returns:
        The cell value
    """
    try:
        # Handle special computed columns
        if column_id == "revenue":
            return revenue_value(report, property_node, scenario_idx)
        elif column_id == "cost":
            return cost_value(report, property_node, scenario_idx)
        elif column_id == "duration":
            return duration_value(report, property_node, scenario_idx)

        if report.is_scenario_specific(column_id):
            return property_node.get(column_id, scenario_idx) if hasattr(property_node, "get") else None
        else:
            return property_node.get(column_id) if hasattr(property_node, "get") else None
    except (ValueError, KeyError, AttributeError):
        # Unknown attribute - return placeholder
        return "-"


def duration_value(report: Any, property_node: Any, scenario_idx: int) -> Any:
    """Elapsed scheduled time, as a number of days.

    The `duration` attribute is what the file asked for, and is zero for
    every task that did not ask for one. What a report means by "duration"
    is how long the task actually took, so it is measured from the dates
    the scheduler worked out.
    """
    try:
        start = property_node.get("start", scenario_idx)
        end = property_node.get("end", scenario_idx)
    except (ValueError, KeyError, AttributeError):
        return None
    if not start or not end:
        return None
    return (end - start).total_seconds() / 86400.0


def revenue_value(report: Any, property_node: Any, scenario_idx: int) -> Any:
    """
    Get the revenue value for a task.

    Revenue is the sum of charges that go to revenue accounts.
    """
    if not hasattr(property_node, "get"):
        return None

    charge = property_node.get("charge", scenario_idx)
    if not charge or charge == 0:
        return None

    # Check if the chargeset is a revenue account
    chargeset_id = property_node.get("chargeset", scenario_idx)
    if not chargeset_id:
        return None

    # Look up the account and check if it's a revenue account
    # For now, use a simple heuristic: if the chargeset is 'rev' or similar
    # A more complete implementation would check the account's properties
    if isinstance(chargeset_id, str) and ("rev" in chargeset_id.lower() or chargeset_id == "rev"):
        # Simple check: 'rev' accounts are revenue accounts
        return charge

    return None


def cost_value(report: Any, property_node: Any, scenario_idx: int) -> Any:
    """
    Get the cost value for a task.

    Cost is calculated as: allocated_time * resource_rate
    Uses the task's getCost() method if available.
    """
    if not hasattr(property_node, "data"):
        return None

    # Get the task scenario data
    if not property_node.data or scenario_idx >= len(property_node.data):
        return None

    task_scenario = property_node.data[scenario_idx]
    if task_scenario is None:
        return None

    # Use getCost() method if available
    if hasattr(task_scenario, "getCost"):
        cost = task_scenario.getCost()
        if cost and cost > 0:
            return cost

    return None


def format_value(report: Any, value: Any, column_id: str) -> str:
    """
    Format a value for display.

    Args:
        value: The value to format
        column_id: Column identifier for context

    Returns:
        Formatted string
    """
    from datetime import datetime

    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        # Scheduling happens in UTC. A reader wrote their file in the
        # project's timezone, so that is what they are shown, unless the
        # report asks for another.
        from scriptplan.core.timezones import from_utc

        zone = report.a("timeZone") or report.project.attributes.get("timezone")
        local = from_utc(value, zone) or value

        # Use report's timeFormat, falling back to project's timeformat
        timeformat = report.a("timeFormat")
        # Check if it's the default - if so, try project's timeformat
        if timeformat == "%Y-%m-%d":
            project_timeformat = report.project.attributes.get("timeformat")
            if project_timeformat:
                timeformat = project_timeformat
        if timeformat:
            return local.strftime(timeformat)
        return str(local)
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)
