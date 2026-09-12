"""Column headings.

A column's heading is the title the report gave it, else the name the
attribute goes by.
"""

from __future__ import annotations

from typing import Any, Optional


__all__ = [
    "header_cell",
    "default_column_title",
]


def header_cell(report: Any, column_def: Any) -> ReportTableCell:
    """
    Generate a header cell for a column.

    Args:
        column_def: Column definition (can be dict, object with id attr, or string)

    Returns:
        ReportTableCell for the header
    """
    # Handle different column_def formats
    if isinstance(column_def, dict):
        column_id = column_def.get("id", str(column_def))
        options = column_def.get("options", {})
        title = options.get("title") if options else None
    elif hasattr(column_def, "id"):
        column_id = column_def.id
        title = getattr(column_def, "title", None)
    else:
        column_id = str(column_def)
        title = None

    if not title:
        title = report.default_column_title(column_id) or column_id

    from scriptplan.report.table_report import ReportTableCell

    return ReportTableCell(text=title, alignment=report.alignment(column_id), is_header=True)


def default_column_title(column_id: str) -> Optional[str]:
    """
    Get the default column title for a column ID.

    Args:
        column_id: The column identifier

    Returns:
        Default title or None
    """
    # Special columns without fixed titles
    if column_id in ("chart", "hourly", "daily", "weekly", "monthly", "quarterly", "yearly"):
        return ""

    from scriptplan.report.table_report import TableReport

    if column_id in TableReport.PROPERTIES_BY_ID:
        return TableReport.PROPERTIES_BY_ID[column_id][0]
    return None
