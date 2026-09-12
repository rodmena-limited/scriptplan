"""Reports: their columns, sorting, filters, formats and navigators."""

from __future__ import annotations

from typing import Any, Optional, Union

from lark import Token, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.units import Duration, parse_calendar_duration, parse_working_hours

from datetime import datetime

from scriptplan.report.logical_expression import parse_expression


class ReportRules:
    """Transformer methods for reports: their columns, sorting, filters, formats and navigators."""

    # Reports
    def report_definition(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def textreport(self, items: list[Any]) -> dict[str, Any]:
        return self._parse_report("textreport", items)

    def taskreport(self, items: list[Any]) -> dict[str, Any]:
        return self._parse_report("taskreport", items)

    def resourcereport(self, items: list[Any]) -> dict[str, Any]:
        return self._parse_report("resourcereport", items)

    def _parse_report(self, report_type: str, items: list[Any]) -> dict[str, Any]:
        r_id = None
        r_name = None
        body = []
        for item in items:
            if isinstance(item, Token):
                if item.type == "ID":
                    r_id = item.value
                elif item.type == "STRING":
                    r_name = item.value.strip('"')
            elif isinstance(item, list):
                body = item
        return {"type": report_type, "id": r_id, "name": r_name, "attributes": body}

    def textreport_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def textreport_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def textreport_header(self, items: list[Any]) -> tuple[str, str]:
        return ("header", self._get_value(items[0]))

    def textreport_footer(self, items: list[Any]) -> tuple[str, str]:
        return ("footer", self._get_value(items[0]))

    def textreport_center(self, items: list[Any]) -> tuple[str, str]:
        return ("center", self._get_value(items[0]))

    def textreport_left(self, items: list[Any]) -> tuple[str, str]:
        return ("left", self._get_value(items[0]))

    def textreport_right(self, items: list[Any]) -> tuple[str, str]:
        return ("right", self._get_value(items[0]))

    def textreport_formats(self, items: list[Any]) -> Any:
        # items[0] is the result from format_list which is already ('formats', [...])
        return items[0] if items else ("formats", [])

    def textreport_title(self, items: list[Any]) -> tuple[str, str]:
        return ("title", self._get_value(items[0]))

    def taskreport_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def taskreport_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def taskreport_header(self, items: list[Any]) -> tuple[str, str]:
        return ("header", self._get_value(items[0]))

    def taskreport_footer(self, items: list[Any]) -> tuple[str, str]:
        return ("footer", self._get_value(items[0]))

    def taskreport_headline(self, items: list[Any]) -> tuple[str, str]:
        return ("headline", self._get_value(items[0]))

    def taskreport_caption(self, items: list[Any]) -> tuple[str, str]:
        return ("caption", self._get_value(items[0]))

    def taskreport_columns(self, items: list[Any]) -> Any:
        return items[0] if items else ("columns", [])

    def taskreport_timeformat(self, items: list[Any]) -> tuple[str, str]:
        return ("timeFormat", self._get_value(items[0]))

    def taskreport_loadunit(self, items: list[Any]) -> tuple[str, str]:
        return ("loadUnit", self._get_value(items[0]))

    def taskreport_hideresource(self, items: list[Any]) -> tuple[str, Any]:
        """A filter expression, parsed now so a bad one is rejected now."""
        return ("hideResource", parse_expression(str(self._get_value(items[0])).lstrip("@")))

    def taskreport_hidetask(self, items: list[Any]) -> tuple[str, Any]:
        """A filter expression, parsed now so a bad one is rejected now."""
        return ("hideTask", parse_expression(str(self._get_value(items[0])).lstrip("@")))

    def taskreport_sorttasks(self, items: list[Any]) -> Any:
        return ("sortTasks", items[0][1] if items else [])

    def taskreport_sortresources(self, items: list[Any]) -> Any:
        return ("sortResources", items[0][1] if items else [])

    def taskreport_scenarios(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("scenarios", [self._get_value(i) for i in items])

    def taskreport_taskroot(self, items: list[Any]) -> tuple[str, str]:
        return ("taskRoot", self._get_value(items[0]))

    def taskreport_period(self, items: list[Any]) -> Any:
        return items[0] if items else ("period", None)

    def taskreport_balance(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("balance", [self._get_value(i) for i in items])

    def taskreport_journalmode(self, items: list[Any]) -> tuple[str, str]:
        return ("journalMode", self._get_value(items[0]))

    def taskreport_journalattributes(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("journalAttributes", [self._get_value(i) for i in items])

    def taskreport_formats(self, items: list[Any]) -> Any:
        # items[0] is the result from format_list: ('formats', [...])
        if items and isinstance(items[0], tuple) and items[0][0] == "formats":
            return items[0]  # Already a properly formatted tuple
        return ("formats", [self._get_value(i) for i in items])

    def taskreport_leaftasksonly(self, items: list[Any]) -> tuple[str, bool]:
        val = self._get_value(items[0])
        # Convert string to boolean
        if isinstance(val, str):
            val = val.lower() in ("true", "yes", "1")
        return ("leafTasksOnly", val)

    def resourcereport_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def resourcereport_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def resourcereport_header(self, items: list[Any]) -> tuple[str, str]:
        return ("header", self._get_value(items[0]))

    def resourcereport_footer(self, items: list[Any]) -> tuple[str, str]:
        return ("footer", self._get_value(items[0]))

    def resourcereport_headline(self, items: list[Any]) -> tuple[str, str]:
        return ("headline", self._get_value(items[0]))

    def resourcereport_columns(self, items: list[Any]) -> Any:
        return items[0] if items else ("columns", [])

    def resourcereport_loadunit(self, items: list[Any]) -> tuple[str, str]:
        return ("loadUnit", self._get_value(items[0]))

    def resourcereport_hideresource(self, items: list[Any]) -> tuple[str, Any]:
        """A filter expression, parsed now so a bad one is rejected now."""
        return ("hideResource", parse_expression(str(self._get_value(items[0])).lstrip("@")))

    def resourcereport_hidetask(self, items: list[Any]) -> tuple[str, Any]:
        """A filter expression, parsed now so a bad one is rejected now."""
        return ("hideTask", parse_expression(str(self._get_value(items[0])).lstrip("@")))

    def resourcereport_sorttasks(self, items: list[Any]) -> Any:
        return ("sortTasks", items[0][1] if items else [])

    def resourcereport_sortresources(self, items: list[Any]) -> Any:
        return ("sortResources", items[0][1] if items else [])

    def resourcereport_scenarios(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("scenarios", [self._get_value(i) for i in items])

    # Column specifications
    def column_list(self, items: list[Any]) -> tuple[str, list[Any]]:
        """Parse column list into list of column specs."""
        return ("columns", [item for item in items if item])

    def column_spec(self, items: list[Any]) -> dict[str, Any]:
        """Parse a single column specification."""
        col_id = self._get_value(items[0])
        options = {}
        if len(items) > 1 and items[1]:
            options = items[1]
        return {"id": col_id, "options": options}

    def column_options(self, items: list[Any]) -> dict[str, Any]:
        """Parse column options into a dict."""
        result = {}
        for item in items:
            if isinstance(item, tuple):
                result[item[0]] = item[1]
            elif isinstance(item, Token):
                # Macro reference or similar
                result["macro"] = self._get_value(item)
        return result

    def column_option(self, items: list[Any]) -> Optional[tuple[str, Any]]:
        """Parse a single column option."""
        if not items:
            return None
        first = items[0]
        if isinstance(first, Token):
            if first.type == "MACRO_REF":
                return ("macro", self._get_value(first))
            # Token is often the keyword like 'title', 'width' etc
            key = self._get_value(first)
            value = self._get_value(items[1]) if len(items) > 1 else None
            return (key, value)
        return items[0] if items else None

    # Sort specifications
    def sort_list(self, items: list[Any]) -> tuple[str, list[Any]]:
        """Parse a sort list into (attribute, ascending, scenario) triples."""
        return ("sort", [item for item in items if item])

    def sort_item(self, items: list[Any]) -> Optional[tuple[str, bool, int]]:
        """Parse one sort criterion.

        Written as `attribute.up` / `attribute.down`, optionally scenario
        qualified as `plan.start.up`.
        """
        if not items:
            return None
        text = str(self._get_value(items[0]))
        parts = text.split(".")
        ascending = True
        if parts and parts[-1].lower() in ("up", "down"):
            ascending = parts.pop().lower() == "up"
        if not parts:
            return None
        # A leading scenario id is resolved later, when the project exists.
        attribute = parts[-1]
        scenario = ".".join(parts[:-1]) if len(parts) > 1 else ""
        return (attribute, ascending, scenario)  # type: ignore[return-value]

    # Format list
    def format_list(self, items: list[Any]) -> tuple[str, list[str]]:
        """Parse formats list."""
        return ("formats", [self._get_value(i) for i in items])

    # Period specification
    def period_spec(self, items: list[Any]) -> tuple[str, Optional[str]]:
        """Parse period specification."""
        return ("period", self._get_value(items[0]) if items else None)

    # Navigator
    def navigator(self, items: list[Any]) -> dict[str, Any]:
        n_id = self._get_value(items[0])
        body = items[1] if len(items) > 1 else []
        return {"type": "navigator", "id": n_id, "attributes": body}

    def navigator_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def navigator_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    # Common
    def date(self, items: list[Any]) -> datetime:
        val = self._get_value(items[0])
        try:
            return datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            return datetime.strptime(val, "%Y-%m-%d-%H:%M")

    def _get_value(self, item: Any) -> Any:
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
