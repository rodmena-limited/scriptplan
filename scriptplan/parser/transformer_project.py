"""The project block and the attributes declared outside any property."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from lark import Token  # type: ignore[import-untyped,unused-ignore]


class ProjectRules:
    """Transformer methods for the project block and the attributes declared outside any property."""

    def start(self, items: list[Any]) -> dict[str, Any]:
        return items[0] if items else {}

    def statements(self, items: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project": None,
            "global_attributes": [],
            "property_declarations": [],
            "reports": [],
            "navigators": [],
        }
        for item in items:
            if isinstance(item, dict):
                if item.get("type") == "project":
                    result["project"] = item
                elif item.get("type") in ["resource", "task", "account", "shift"]:
                    result["property_declarations"].append(item)
                elif item.get("type") in ["taskreport", "resourcereport", "textreport"]:
                    result["reports"].append(item)
                elif item.get("type") == "navigator":
                    result["navigators"].append(item)
            elif isinstance(item, tuple):
                result["global_attributes"].append(item)
        return result

    def statement(self, items: list[Any]) -> Any:
        return items[0] if items else None

    # Project definition
    def project(self, items: list[Any]) -> dict[str, Any]:
        # items[0] is always project_id
        # items[1] might be project_name (if present) or project_timeframe
        # We need to check the type to determine
        p_id: str = self._get_value(items[0])

        idx: int = 1
        # Check if items[1] is a string (project_name) or a dict (timeframe)
        p_name: str
        if len(items) > idx and isinstance(items[idx], str):
            p_name = items[idx]
            idx += 1
        else:
            p_name = p_id  # Use id as name if not specified

        timeframe: Any = items[idx] if len(items) > idx else {}
        idx += 1
        attrs: Any = items[idx] if len(items) > idx else []

        return {"type": "project", "id": p_id, "name": p_name, "timeframe": timeframe, "attributes": attrs}

    def project_id(self, items: list[Any]) -> Any:
        return self._get_value(items[0])

    def project_name(self, items: list[Any]) -> Any:
        return self._get_value(items[0])

    def project_timeframe(self, items: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {"start": items[0]}
        if len(items) > 1 and items[1]:
            result["duration"] = items[1]
        return result

    def duration_spec(self, items: list[Any]) -> str | None:
        return self._get_value(items[0]) if items else None

    def project_attributes(self, items: list[Any]) -> list[Any]:
        return list(items)

    def project_attribute(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def project_scheduling(self, items: list[Any]) -> tuple[str, str]:
        mode: str = self._get_value(items[0]).lower()
        # forward=True means ASAP, forward=False means ALAP
        return ("scheduling", mode)

    # Global attributes
    def global_attribute(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def copyright(self, items: list[Any]) -> tuple[str, str]:
        return ("copyright", self._get_value(items[0]))

    def rate(self, items: list[Any]) -> tuple[str, float]:
        return ("rate", float(self._get_value(items[0])))

    def leaves_global(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        return (
            "leaves",
            {
                "type": self._get_value(items[0]),
                "name": self._get_value(items[1]),
                "start": items[2],
                "end": items[3] if len(items) > 3 else None,
            },
        )

    def flags_global(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("flags", [self._get_value(i) for i in items])

    def balance(self, items: list[Any]) -> tuple[str, tuple[str, str]]:
        return ("balance", (self._get_value(items[0]), self._get_value(items[1])))

    def vacation_global(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        # vacation_global: "vacation" STRING? date ("-" date)?
        # After transformation, items contains: optional string name, datetime(s) from date rule
        name: str | None = None
        start_date: datetime | None = None
        end_date: datetime | None = None
        for item in items:
            if isinstance(item, datetime):
                if start_date is None:
                    start_date = item
                else:
                    end_date = item
            elif isinstance(item, str):
                name = item
        return ("vacation", {"name": name, "start": start_date, "end": end_date or start_date})

    # Project attribute handlers
    def timezone(self, items: list[Any]) -> tuple[str, str]:
        return ("timezone", self._get_value(items[0]))

    def timeformat(self, items: list[Any]) -> tuple[str, str]:
        return ("timeformat", self._get_value(items[0]))

    def numberformat(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("numberformat", [self._get_value(i) for i in items])

    def currencyformat(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("currencyformat", [self._get_value(i) for i in items])

    def currency(self, items: list[Any]) -> tuple[str, str]:
        return ("currency", self._get_value(items[0]))

    def now(self, items: list[Any]) -> tuple[str, Any]:
        return ("now", items[0])

    def dailyworkinghours(self, items: list[Any]) -> tuple[str, float]:
        return ("dailyworkinghours", float(self._get_value(items[0])))

    def yearlyworkingdays(self, items: list[Any]) -> tuple[str, float]:
        return ("yearlyworkingdays", float(self._get_value(items[0])))

    # Scenario
    def scenario_def(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        s_id: str = self._get_value(items[0])
        s_name: str = self._get_value(items[1])
        body: Any = items[2] if len(items) > 2 else []
        return ("scenario", {"id": s_id, "name": s_name, "children": body})

    def scenario_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    # Extend
    def extend(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        e_type: str = self._get_value(items[0])
        attrs: Any = items[1] if len(items) > 1 else []
        return ("extend", {"type": e_type, "attributes": attrs})

    def extend_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def extend_attribute(self, items: list[Any]) -> dict[str, str]:
        # Grammar: "text" ID STRING - "text" is literal, so only ID and STRING in items
        return {"type": "text", "name": self._get_value(items[0]), "label": self._get_value(items[1])}


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
