"""TJP Parser for TaskJuggler project files."""

import contextlib
import os
from datetime import datetime
from typing import Any, Optional, Union

from lark import Lark, Token, Transformer, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task
from scriptplan.parser.macro_processor import preprocess_tjp


class TJPTransformer(Transformer[Any, Any]):
    """Transform the parse tree into a dictionary structure."""

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

    def duration_spec(self, items: list[Any]) -> Optional[str]:
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
        name: Optional[str] = None
        start_date: Optional[datetime] = None
        end_date: Optional[datetime] = None
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

    # Property declarations
    def property_declaration(self, items: list[Any]) -> Any:
        return items[0] if items else None

    # Resource
    def resource(self, items: list[Any]) -> dict[str, Any]:
        r_id: str = self._get_value(items[0])
        r_name: str = self._get_value(items[1])
        body: Any = items[2] if len(items) > 2 else []
        return {"type": "resource", "id": r_id, "name": r_name, "attributes": body}

    def resource_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def resource_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def resource_email(self, items: list[Any]) -> tuple[str, str]:
        return ("email", self._get_value(items[0]))

    def resource_rate(self, items: list[Any]) -> tuple[str, float]:
        return ("rate", float(self._get_value(items[0])))

    def resource_efficiency(self, items: list[Any]) -> tuple[str, float]:
        return ("efficiency", float(self._get_value(items[0])))

    def resource_timezone(self, items: list[Any]) -> tuple[str, str]:
        return ("timezone", self._get_value(items[0]))

    def resource_managers(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("managers", [self._get_value(i) for i in items])

    def resource_limits(self, items: list[Any]) -> tuple[str, Any]:
        return ("limits", items[0] if items else [])

    def limits_body(self, items: list[Any]) -> list[Any]:
        """Parse limits body containing limit_attr items."""
        return list(items) if items else []

    def limit_attr(self, items: list[Any]) -> Any:
        """Parse a single limit attribute - pass through the dailymax/weeklymax result."""
        return items[0] if items else None

    def limit_dailymax(self, items: list[Any]) -> dict[str, Any]:
        """Parse dailymax limit."""
        duration: Any = items[0] if items else "0h"
        resources: Optional[Any] = items[1] if len(items) > 1 else None
        # Store value in hours - conversion to slots happens in Limits class
        hours: Union[float, int] = (
            self._parse_duration_to_hours(duration, round_to_slots=False)
            if isinstance(duration, str)
            else float(duration)
        )
        return {"type": "dailymax", "value": hours, "resources": resources}

    def limit_weeklymax(self, items: list[Any]) -> dict[str, Any]:
        """Parse weeklymax limit."""
        duration: Any = items[0] if items else "0h"
        resources: Optional[Any] = items[1] if len(items) > 1 else None
        # Store value in hours - conversion to slots happens in Limits class
        hours: Union[float, int] = (
            self._parse_duration_to_hours(duration, round_to_slots=False)
            if isinstance(duration, str)
            else float(duration)
        )
        return {"type": "weeklymax", "value": hours, "resources": resources}

    def limits_resources(self, items: list[Any]) -> list[str]:
        """Parse limits resources: { resources id1, id2, ... }."""
        return [self._get_value(i) for i in items]

    def _parse_duration_to_hours(self, duration_str: str, round_to_slots: bool = False) -> Union[float, int]:
        """Parse duration string to hours.

        Args:
            duration_str: Duration string like '6.4h', '2d', '1w'
            round_to_slots: If True, round to integer hours (for limits)

        Returns:
            Duration in hours (float or int depending on round_to_slots)
        """
        import re

        match = re.match(r"(\d+(?:\.\d+)?)\s*([hdwmy]?)", str(duration_str))
        if match:
            value: float = float(match.group(1))
            unit: str = match.group(2) or "h"
            hours: float
            if unit == "h":
                hours = value
            elif unit == "d":
                hours = value * 8  # 8 hours per day
            elif unit == "w":
                hours = value * 40  # 40 hours per week
            elif unit == "m":
                hours = value * 160  # ~160 hours per month
            elif unit == "y":
                hours = value * 2000  # ~2000 hours per year
            else:
                hours = 0

            # TaskJuggler rounds limit values to integer slots
            if round_to_slots:
                return round(hours)
            return hours
        return 0

    def resource_leaves(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        """Handle resource leaves: leaves type start_date [- end_date]."""
        leave_type: Any = items[0] if items else "annual"
        start_date: Any = items[1] if len(items) > 1 else None
        end_date: Any = items[2] if len(items) > 2 else start_date
        return ("leaves", {"type": leave_type, "start": start_date, "end": end_date})

    def resource_flags(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("flags", [self._get_value(i) for i in items])

    def resource_vacation(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        """Handle resource vacation: vacation start_date [- end_date]."""
        start_date: Any = items[0] if items else None
        end_date: Any = items[1] if len(items) > 1 else start_date
        return ("vacation", {"start": start_date, "end": end_date})

    def resource_booking(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        """Handle resource booking: booking STRING date duration_value."""
        name: str = self._get_value(items[0])
        start: Any = items[1] if len(items) > 1 else None
        duration: str = self._get_value(items[2]) if len(items) > 2 else "0h"
        return ("booking", {"name": name, "start": start, "duration": duration})

    def resource_workinghours(self, items: list[Any]) -> tuple[str, Any]:
        """Handle resource workinghours: workinghours mon, tue, ... 08:00 - 17:00 or shift_id."""
        if not items:
            return ("workinghours", [])
        # Check if it's a shift reference (ID) or a workinghours_spec (list)
        item: Any = items[0]
        if isinstance(item, str):
            # It's a shift ID reference
            return ("workinghours_shift", item)
        elif hasattr(item, "type") and item.type == "ID":
            # It's a Token ID
            return ("workinghours_shift", str(item))
        else:
            # It's a workinghours_spec
            return ("workinghours", item)

    def resource_chargeset(self, items: list[Any]) -> tuple[str, str]:
        """Handle resource chargeset: chargeset account_id."""
        return ("chargeset", self._get_value(items[0]))

    def timingresolution(self, items: list[Any]) -> tuple[str, int]:
        """Handle timingresolution: timingresolution duration_value."""
        # Parse duration to seconds
        duration: Any = items[0] if items else "1h"
        import re

        match = re.match(r"(\d+(?:\.\d+)?)\s*([hdwmymin]+)", str(duration))
        if match:
            value: float = float(match.group(1))
            unit: str = match.group(2) or "h"
            seconds: int
            if unit == "min":
                seconds = int(value * 60)
            elif unit == "h":
                seconds = int(value * 3600)
            elif unit == "d":
                seconds = int(value * 86400)
            else:
                seconds = 3600  # default 1 hour
            return ("timingresolution", seconds)
        return ("timingresolution", 3600)

    def workinghours(self, items: list[Any]) -> tuple[str, Any]:
        """Handle workinghours at project or shift level."""
        return ("workinghours", items[0] if items else [])

    def workinghours_spec(self, items: list[Any]) -> dict[str, Any]:
        """Parse workinghours specification: mon, tue, ... 08:00 - 17:00, 13:00 - 14:00.

        Returns a dict mapping day names to list of (start_time, end_time) tuples.
        """
        # items[0] is day_list (list of days)
        # items[1:] are duration_range tuples
        days: Any = items[0] if items else []
        ranges: list[Any] = list(items[1:]) if len(items) > 1 else []

        return {"days": days, "ranges": ranges}

    def day_list(self, items: list[Any]) -> list[str]:
        """Parse day list: day_spec, day_spec, ..."""
        all_days: list[str] = []
        for item in items:
            if isinstance(item, list):
                all_days.extend(item)
            else:
                all_days.append(item)
        return all_days

    def day_spec(self, items: list[Any]) -> list[str]:
        """Parse day spec: single day or day range like mon - fri."""
        day_order: list[str] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

        if len(items) == 1:
            # Single day
            day: str = self._get_value(items[0]).lower()
            return [day]
        else:
            # Day range like mon - fri
            start_day: str = self._get_value(items[0]).lower()
            end_day: str = self._get_value(items[1]).lower()

            start_idx: int = day_order.index(start_day)
            end_idx: int = day_order.index(end_day)

            # Handle wrap-around if needed (e.g., fri - mon)
            if start_idx <= end_idx:
                return day_order[start_idx : end_idx + 1]
            else:
                # Wrap around (unusual but supported)
                return day_order[start_idx:] + day_order[: end_idx + 1]

    def duration_range(self, items: list[Any]) -> tuple[str, str]:
        """Parse duration range: TIME - TIME."""
        start_time: str = self._get_value(items[0]) if items else "09:00"
        end_time: str = self._get_value(items[1]) if len(items) > 1 else "17:00"
        return (start_time, end_time)

    def leaves_type(self, items: list[Any]) -> str:
        """Handle leaves type: annual, sick, holiday, special, unpaid."""
        return self._get_value(items[0]) if items else "annual"

    # Task
    def task(self, items: list[Any]) -> dict[str, Any]:
        t_id: str = self._get_value(items[0])
        t_name: str = self._get_value(items[1])
        body: Any = items[2] if len(items) > 2 else []
        return {"type": "task", "id": t_id, "name": t_name, "attributes": body}

    def task_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def task_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    # Named task attribute rules
    def task_start(self, items: list[Any]) -> tuple[str, Any]:
        return ("start", items[0])

    def task_end(self, items: list[Any]) -> tuple[str, Any]:
        return ("end", items[0])

    def task_effort(self, items: list[Any]) -> Any:
        return items[0]  # effort_value returns a tuple

    def task_duration(self, items: list[Any]) -> tuple[str, Any]:
        return ("duration", items[0])

    def task_length(self, items: list[Any]) -> tuple[str, Any]:
        return ("length", items[0])

    def task_milestone(self, items: list[Any]) -> tuple[str, bool]:
        return ("milestone", True)

    def task_scheduling(self, items: list[Any]) -> tuple[str, bool]:
        mode: str = self._get_value(items[0]).lower()
        # forward=True means ASAP, forward=False means ALAP
        return ("forward", mode == "asap")

    def task_depends(self, items: list[Any]) -> Any:
        return items[0]  # depends_list returns a tuple

    def task_precedes(self, items: list[Any]) -> tuple[str, Any]:
        return ("precedes", items[0][1] if isinstance(items[0], tuple) else items[0])

    def task_allocate(self, items: list[Any]) -> Any:
        return items[0]  # allocate_spec returns a tuple

    def task_responsible(self, items: list[Any]) -> tuple[str, str]:
        return ("responsible", self._get_value(items[0]))

    def task_priority(self, items: list[Any]) -> tuple[str, int]:
        return ("priority", int(self._get_value(items[0])))

    def task_complete(self, items: list[Any]) -> tuple[str, float]:
        return ("complete", float(self._get_value(items[0])))

    def task_note(self, items: list[Any]) -> tuple[str, str]:
        return ("note", self._get_value(items[0]))

    def task_chargeset(self, items: list[Any]) -> tuple[str, str]:
        return ("chargeset", self._get_value(items[0]))

    def task_purge_chargeset(self, items: list[Any]) -> tuple[str, bool]:
        return ("purge_chargeset", True)

    def task_charge(self, items: list[Any]) -> tuple[str, tuple[float, Optional[str]]]:
        return ("charge", (float(self._get_value(items[0])), self._get_value(items[1]) if len(items) > 1 else None))

    def task_limits(self, items: list[Any]) -> tuple[str, Any]:
        return ("limits", items[0] if items else [])

    def task_journalentry(self, items: list[Any]) -> tuple[str, dict[str, Any]]:
        # items: date, optional headline (STRING), journal_body
        date: Any = items[0] if items else None
        headline: Optional[str] = None
        body: dict[str, Any] = {}

        for item in items[1:]:
            if isinstance(item, str) or (hasattr(item, "type") and item.type == "STRING"):
                headline = self._get_value(item)
            elif isinstance(item, dict):
                body = item

        return ("journalentry", {"date": date, "headline": headline, "body": body})

    def journal_body(self, items: list[Any]) -> dict[str, Any]:
        # Collect all journal attributes into a dict
        result: dict[str, Any] = {"author": None, "alert": "green", "summary": None, "details": None}
        for item in items:
            if isinstance(item, tuple):
                key: str
                value: Any
                key, value = item
                result[key] = value
        return result

    def journal_attr(self, items: list[Any]) -> Any:
        # Pass through the inner journal_* rule result
        return items[0] if items else None

    def journal_author(self, items: list[Any]) -> tuple[str, str]:
        return ("author", self._get_value(items[0]))

    def journal_alert(self, items: list[Any]) -> tuple[str, Any]:
        return ("alert", items[0] if items else "green")

    def journal_summary(self, items: list[Any]) -> tuple[str, Optional[str]]:
        value: Any = items[0] if items else None
        return ("summary", self._extract_text(value))

    def journal_details(self, items: list[Any]) -> tuple[str, Optional[str]]:
        value: Any = items[0] if items else None
        return ("details", self._extract_text(value))

    def rich_text(self, items: list[Any]) -> str:
        # Rich text is wrapped in -8<- ... ->8-
        # The RICH_TEXT_BLOCK token contains the delimiters and content
        if items:
            text: str = self._get_value(items[0])
            # Strip the -8<- and ->8- markers
            if text.startswith("-8<-"):
                text = text[4:]
            if text.endswith("->8-"):
                text = text[:-4]
            return text.strip()
        return ""

    def _extract_text(self, value: Any) -> Optional[str]:
        """Extract text from a string or rich_text result."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, "type") and value.type == "STRING":
            result: Any = self._get_value(value)
            return str(result) if result else None
        # If it's already processed rich_text
        return str(value) if value else None

    def alert_level(self, items: list[Any]) -> str:
        # items[0] is a Token with the alert level value (green/yellow/red)
        return self._get_value(items[0]) if items else "green"

    def task_flags(self, items: list[Any]) -> tuple[str, list[str]]:
        return ("flags", [self._get_value(i) for i in items])

    def scenario_attr(self, items: list[Any]) -> tuple[str, tuple[str, Any]]:
        """Handle scenario-specific attribute like 'delayed:effort 40d'."""
        scenario_id: str = self._get_value(items[0])
        attr_data: Any = items[1]  # scenario_specific_attr result
        return ("scenario_attr", (scenario_id, attr_data))

    def scenario_specific_attr(self, items: list[Any]) -> Any:
        """Handle the attribute part of scenario-specific attribute."""
        # items[0] is the result from scenario_start/end/effort/etc
        return items[0] if items else None

    def scenario_start(self, items: list[Any]) -> tuple[str, Any]:
        """Handle scenario-specific start attribute."""
        return ("start", items[0])  # items[0] is the date

    def scenario_end(self, items: list[Any]) -> tuple[str, Any]:
        """Handle scenario-specific end attribute."""
        return ("end", items[0])

    def scenario_effort(self, items: list[Any]) -> Any:
        """Handle scenario-specific effort attribute."""
        return items[0]  # effort_value already returns ('effort', value)

    def scenario_duration(self, items: list[Any]) -> tuple[str, Any]:
        """Handle scenario-specific duration attribute."""
        return ("duration", items[0])

    def scenario_length(self, items: list[Any]) -> tuple[str, Any]:
        """Handle scenario-specific length attribute."""
        return ("length", items[0])

    # Task attribute helpers
    def effort_value(self, items: list[Any]) -> tuple[str, float]:
        num: float = float(self._get_value(items[0]))
        unit: str = self._get_value(items[1])
        # Convert to hours (the base unit internally)
        # d=day (8h), w=week (40h), h=hour, m=minute, y=year (2080h)
        multipliers: dict[str, float] = {"d": 8, "w": 40, "h": 1, "m": 1 / 60, "y": 2080, "min": 1 / 60}
        hours: float = num * multipliers.get(unit.lower(), 1)
        return ("effort", hours)

    def duration_value(self, items: list[Any]) -> str:
        num: str = self._get_value(items[0])
        unit: str = self._get_value(items[1])
        return f"{num}{unit}"

    def depends_list(self, items: list[Any]) -> tuple[str, list[Any]]:
        # Items are now dependency dicts with ref and optional gap
        return ("depends", list(items))

    def depends_item(self, items: list[Any]) -> dict[str, Any]:
        # First item is the DEPENDS_REF, optional second is depends_options dict
        ref: str = self._get_value(items[0])
        dep: dict[str, Any] = {"ref": ref}
        if len(items) > 1 and items[1]:
            dep.update(items[1])
        return dep

    def depends_options(self, items: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in items:
            if isinstance(item, dict):
                result.update(item)
        return result

    def dep_gapduration(self, items: list[Any]) -> dict[str, str]:
        return {"gapduration": self._get_value(items[0])}

    def dep_gaplength(self, items: list[Any]) -> dict[str, str]:
        return {"gaplength": self._get_value(items[0])}

    def dep_maxgapduration(self, items: list[Any]) -> dict[str, str]:
        return {"maxgapduration": self._get_value(items[0])}

    def dep_onend(self, items: list[Any]) -> dict[str, bool]:
        return {"onend": True}

    def dep_onstart(self, items: list[Any]) -> dict[str, bool]:
        return {"onstart": True}

    def allocate_spec(self, items: list[Any]) -> tuple[str, Any]:
        resources = []
        options = {}
        for item in items:
            if isinstance(item, Token):
                resources.append(item.value)
            elif isinstance(item, dict):
                # allocate_options dict
                options.update(item)
        # If there are alternatives, include them in the allocation structure
        if options:
            return ("allocate", {"resources": resources, "options": options})
        return ("allocate", resources)

    def allocate_options(self, items: list[Any]) -> dict[str, Any]:
        """Process allocation options like persistent, mandatory, alternative."""
        result = {}
        for item in items:
            if isinstance(item, dict):
                result.update(item)
            elif isinstance(item, list):
                # Flatten nested lists from allocate_option
                for subitem in item:
                    if isinstance(subitem, dict):
                        result.update(subitem)
        return result

    def allocate_option(self, items: list[Any]) -> dict[str, Any]:
        """
        Process a single allocation option.

        The grammar literals ("alternative", "persistent", etc.) are filtered out,
        so we detect the option type by the structure:
        - Empty items -> persistent or mandatory (no IDs)
        - ID tokens -> alternative (list of resource IDs)
        - Dict with limits -> limits
        """
        if not items:
            # This shouldn't happen for well-formed input
            return {}

        # Check if it's a limits block (dict)
        if isinstance(items[0], dict):
            return items[0]

        # Check if items are ID tokens -> alternative resources
        alternatives = []
        for item in items:
            if isinstance(item, Token) and item.type == "ID":
                alternatives.append(item.value)

        if alternatives:
            return {"alternative": alternatives}

        # Persistent and mandatory have no child items in the parse tree
        # They're handled at the grammar level as literals
        return {}

    # Account
    def account(self, items: list[Any]) -> dict[str, Any]:
        a_id = self._get_value(items[0])
        a_name = self._get_value(items[1])
        body = items[2] if len(items) > 2 else []
        return {"type": "account", "id": a_id, "name": a_name, "attributes": body}

    def account_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def account_attr(self, items: list[Any]) -> Any:
        return items[0] if items else None

    # Shift
    def shift(self, items: list[Any]) -> dict[str, Any]:
        s_id = self._get_value(items[0])
        # Name is optional (STRING?)
        # Body is the last item (a list)
        if len(items) >= 2 and isinstance(items[-1], list):
            body = items[-1]
            s_name = self._get_value(items[1]) if len(items) > 2 else s_id
        else:
            body = []
            s_name = self._get_value(items[1]) if len(items) > 1 else s_id
        return {"type": "shift", "id": s_id, "name": s_name, "attributes": body}

    def shift_body(self, items: list[Any]) -> list[Any]:
        return list(items)

    def shift_attr(self, items: list[Any]) -> Any:
        # shift_attr comes from workinghours workinghours_spec or leaves
        # The workinghours handler returns ('workinghours', spec)
        # But for shifts, the grammar directly uses workinghours_spec
        if items and isinstance(items[0], dict):
            # It's a workinghours_spec dict - wrap it as a tuple
            return ("workinghours", items[0])
        return items[0] if items else None

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

    def taskreport_hideresource(self, items: list[Any]) -> tuple[str, str]:
        return ("hideResource", self._get_value(items[0]))

    def taskreport_hidetask(self, items: list[Any]) -> tuple[str, str]:
        return ("hideTask", self._get_value(items[0]))

    def taskreport_sorttasks(self, items: list[Any]) -> Any:
        return items[0] if items else ("sort", [])

    def taskreport_sortresources(self, items: list[Any]) -> Any:
        return items[0] if items else ("sort", [])

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

    def resourcereport_hideresource(self, items: list[Any]) -> tuple[str, str]:
        return ("hideResource", self._get_value(items[0]))

    def resourcereport_hidetask(self, items: list[Any]) -> tuple[str, str]:
        return ("hideTask", self._get_value(items[0]))

    def resourcereport_sorttasks(self, items: list[Any]) -> Any:
        return items[0] if items else ("sort", [])

    def resourcereport_sortresources(self, items: list[Any]) -> Any:
        return items[0] if items else ("sort", [])

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
        """Parse sort list."""
        return ("sort", [item for item in items if item])

    def sort_item(self, items: list[Any]) -> Optional[str]:
        """Parse a single sort item."""
        return self._get_value(items[0]) if items else None

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


class ModelBuilder:
    """Build the Project model from the parsed data."""

    def __init__(self) -> None:
        self._pending_depends: list[tuple[Task, list[Any]]] = []  # Store (task, depends_list) for later resolution
        self._pending_precedes: list[tuple[Task, list[Any]]] = []  # Store (task, precedes_list) for later resolution

    def build(self, data: dict[str, Any]) -> Project:
        """Build a Project from parsed data."""
        if not data or not data.get("project"):
            raise ValueError("No project definition found")

        proj_data = data["project"]
        timeframe = proj_data.get("timeframe", {})
        start_date = timeframe.get("start")
        duration_str = timeframe.get("duration")

        # Create project
        project = Project(
            proj_data["id"],
            proj_data["name"],
            "",  # version is not used like this
        )

        # Set project start and end dates
        if start_date:
            project["start"] = start_date
            # Calculate end date from duration if provided
            if duration_str:
                import re

                from dateutil.relativedelta import relativedelta

                match = re.match(r"(\d+)([dwmy])", duration_str)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    if unit == "d":
                        end_date = start_date + relativedelta(days=amount)
                    elif unit == "w":
                        end_date = start_date + relativedelta(weeks=amount)
                    elif unit == "m":
                        end_date = start_date + relativedelta(months=amount)
                    elif unit == "y":
                        end_date = start_date + relativedelta(years=amount)
                    else:
                        end_date = start_date
                    project["end"] = end_date

        # Apply project attributes
        self._apply_project_attributes(project, proj_data.get("attributes", []))

        # Apply global attributes
        self._apply_global_attributes(project, data.get("global_attributes", []))

        # Apply property declarations (resources, tasks, accounts)
        for prop in data.get("property_declarations", []):
            self._create_property(project, prop)

        # Resolve dependencies after all tasks are created
        self._resolve_dependencies(project)

        # Resolve precedes relationships (convert to dependencies on target tasks)
        self._resolve_precedes(project)

        # Inherit attributes from parents for all tasks
        self._inherit_all_attributes(project)

        # Create reports
        for report_data in data.get("reports", []):
            self._create_report(project, report_data)

        return project

    def _inherit_all_attributes(self, project: Project) -> None:
        """Inherit attributes from parent nodes for all tasks and resources."""

        # Process tasks in tree order (parents before children)
        def inherit_recursive(node: Any) -> None:
            node.inheritAttributes()
            for child in node.children:
                inherit_recursive(child)

        # Get top-level items (no parent)
        for task in project.tasks:
            if not task.parent:
                inherit_recursive(task)

        for resource in project.resources:
            if not resource.parent:
                inherit_recursive(resource)

    def _resolve_dependencies(self, project: Project) -> None:
        """Resolve task dependency references to actual Task objects."""
        for task, depends_list in self._pending_depends:
            resolved: list[Any] = []
            for dep_item in depends_list:
                # dep_item can be a dict with 'ref' key or a string (for backwards compat)
                if isinstance(dep_item, dict):
                    dep_ref = dep_item.get("ref", "")
                    gapduration = dep_item.get("gapduration")
                    gaplength = dep_item.get("gaplength")
                    maxgapduration = dep_item.get("maxgapduration")
                    onstart = dep_item.get("onstart", False)
                    onend = dep_item.get("onend", False)
                else:
                    dep_ref = dep_item
                    gapduration = None
                    gaplength = None
                    maxgapduration = None
                    onstart = False
                    onend = False

                dep_task = self._resolve_task_reference(project, task, dep_ref)
                if dep_task:
                    # Store as dict if we have gap info or onstart/onend, else just the task
                    if gapduration or gaplength or maxgapduration or onstart or onend:
                        resolved.append(
                            {
                                "task": dep_task,
                                "gapduration": gapduration,
                                "gaplength": gaplength,
                                "maxgapduration": maxgapduration,
                                "onstart": onstart,
                                "onend": onend,
                            }
                        )
                    else:
                        resolved.append(dep_task)
            if resolved:
                # Set dependencies for all scenarios
                for scIdx in range(project.scenarioCount()):
                    task[("depends", scIdx)] = resolved

    def _resolve_precedes(self, project: Project) -> None:
        """Resolve precedes relationships by adding dependencies to target tasks.

        If task A precedes task B, then B depends on A.
        This is the inverse of the 'depends' relationship.
        """
        for source_task, precedes_list in self._pending_precedes:
            for prec_item in precedes_list:
                # prec_item can be a dict with 'ref' key or a string
                prec_ref = prec_item.get("ref", "") if isinstance(prec_item, dict) else prec_item

                target_task = self._resolve_task_reference(project, source_task, prec_ref)
                if target_task:
                    # Add source_task as a dependency of target_task
                    for scIdx in range(project.scenarioCount()):
                        existing_deps = target_task.get("depends", scIdx) or []
                        if not isinstance(existing_deps, list):
                            existing_deps = [existing_deps] if existing_deps else []
                        # Check if source_task is already in dependencies
                        already_exists = False
                        for dep in existing_deps:
                            dep_task = dep.get("task") if isinstance(dep, dict) else dep
                            if dep_task is source_task:
                                already_exists = True
                                break
                        if not already_exists:
                            existing_deps.append(source_task)
                            target_task[("depends", scIdx)] = existing_deps

    def _resolve_task_reference(self, project: Project, from_task: Task, ref: str) -> Optional[Task]:
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
        while ref.startswith("!"):
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
        parts = ref.split(".")

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
            return current  # type: ignore[return-value]
        else:
            # Search from project root
            for task in project.tasks:
                if task.id == parts[0]:
                    if len(parts) == 1:
                        return task  # type: ignore[return-value]
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
                    return current  # type: ignore[return-value]
        return None

    def _apply_project_attributes(self, project: Project, attributes: list[Any]) -> None:
        """Apply attributes to the project."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                if key == "scenario":
                    self._create_scenario(project, value)
                elif key == "extend":
                    pass  # Handle extensions later
                else:
                    with contextlib.suppress(ValueError, KeyError):
                        project[key] = value

    def _apply_global_attributes(self, project: Project, attributes: list[Any]) -> None:
        """Apply global attributes to the project."""
        from scriptplan.core.leave import Leave
        from scriptplan.utils.time import TimeInterval

        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, tuple):
                key, value = attr
                if key == "leaves":
                    # Global leaves - convert dict to Leave object
                    leave_type = value.get("type", "holiday")
                    start_date = value.get("start")
                    # For single-day holidays, end_date might be None
                    end_date = value.get("end")
                    if end_date is None:
                        # Single day - end is start + 1 day
                        from datetime import timedelta

                        end_date = start_date + timedelta(days=1)

                    if start_date:
                        interval = TimeInterval(start_date, end_date)
                        type_idx = Leave.Types.get(leave_type, 1)  # Default to 'holiday' (1)
                        leave = Leave(interval, type_idx)

                        # Add to project's leaves list
                        existing = project.attributes.get("leaves", [])
                        if not isinstance(existing, list):
                            existing = [existing] if existing else []
                        existing.append(leave)
                        project.attributes["leaves"] = existing
                elif key == "vacation":
                    # Global vacation - similar to leaves but always 'holiday' type
                    start_date = value.get("start")
                    end_date = value.get("end")
                    # If end_date equals start_date (single day vacation), extend to next day
                    from datetime import timedelta

                    if end_date is None or end_date == start_date:
                        end_date = start_date + timedelta(days=1)

                    if start_date:
                        interval = TimeInterval(start_date, end_date)
                        type_idx = Leave.Types.get("holiday", 1)
                        leave = Leave(interval, type_idx)

                        # Add to project's vacations/leaves list
                        existing = project.attributes.get("vacations", [])
                        if not isinstance(existing, list):
                            existing = [existing] if existing else []
                        existing.append(leave)
                        project.attributes["vacations"] = existing
                else:
                    with contextlib.suppress(ValueError, KeyError):
                        project[key] = value

    def _create_scenario(self, project: Project, scenario_data: dict[str, Any], parent: Optional[Any] = None) -> None:
        """Create a scenario in the project.

        Args:
            project: The project
            scenario_data: Dict with 'id', 'name', 'children'
            parent: Parent scenario for nested scenarios
        """
        from scriptplan.core.scenario import Scenario

        s_id = str(scenario_data.get("id", ""))
        s_name = str(scenario_data.get("name", "")).strip('"')
        children = scenario_data.get("children", [])

        # Clear default scenario on first scenario definition
        if parent is None and not hasattr(self, "_scenarios_cleared"):
            # Remove the default 'plan' scenario
            default_plan = project.scenarios["plan"]
            if default_plan:
                project.scenarios.removeProperty(default_plan)
            self._scenarios_cleared = True

        # Create the scenario
        scenario = Scenario(project, s_id, s_name, parent)

        # Create nested child scenarios
        for child in children:
            if isinstance(child, tuple) and child[0] == "scenario":
                self._create_scenario(project, child[1], scenario)

    def _create_property(self, parent: Union[Project, Task, Resource], prop_data: Any) -> None:
        """Create a property (resource, task, account) in the parent."""
        if not isinstance(prop_data, dict):
            return

        prop_type = prop_data.get("type")
        prop_id = prop_data.get("id", "")
        prop_name = prop_data.get("name", "")
        attributes = prop_data.get("attributes", [])

        # Determine project reference
        project = parent if isinstance(parent, Project) else parent.project

        obj: Union[Task, Resource, Any]
        if prop_type == "task":
            obj = Task(project, str(prop_id), str(prop_name), parent if isinstance(parent, Task) else None)
        elif prop_type == "resource":
            obj = Resource(project, str(prop_id), str(prop_name), parent if isinstance(parent, Resource) else None)
        elif prop_type == "account":
            # Skip accounts for now - need Account class
            return
        elif prop_type == "shift":
            from scriptplan.core.shift import Shift

            obj = Shift(project, str(prop_id), str(prop_name), parent if isinstance(parent, Shift) else None)
        else:
            return

        # Apply attributes to the created object
        self._apply_property_attributes(obj, attributes, prop_type)

    def _apply_property_attributes(
        self, obj: Union[Task, Resource, Any], attributes: list[Any], prop_type: str
    ) -> None:
        """Apply attributes to a property object."""
        for attr in attributes:
            if attr is None:
                continue
            if isinstance(attr, dict):
                # Nested property (e.g., nested resource or task)
                self._create_property(obj, attr)
            elif isinstance(attr, tuple):
                key, value = attr
                if key == "email":
                    obj["email"] = value
                elif key == "rate":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("rate", scIdx)] = value
                elif key == "efficiency":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("efficiency", scIdx)] = value
                elif key == "timezone":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("timezone", scIdx)] = value
                elif key == "effort":
                    # Set for all scenarios (no prefix means apply to all)
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("effort", scIdx)] = value
                elif key == "depends":
                    # Store for later resolution (after all tasks created)
                    self._pending_depends.append((obj, value))  # type: ignore[arg-type]
                elif key == "precedes":
                    # Store for later resolution - precedes creates reverse dependencies
                    # If A precedes B, then B depends on A
                    self._pending_precedes.append((obj, value))  # type: ignore[arg-type]
                elif key == "allocate":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("allocate", scIdx)] = value
                elif key == "start":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("start", scIdx)] = value
                elif key == "end":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("end", scIdx)] = value
                elif key == "milestone":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("milestone", scIdx)] = value
                elif key == "flags":
                    # Set flags for all scenarios (list of flag strings)
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("flags", scIdx)] = value
                elif key == "priority":
                    # Set for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("priority", scIdx)] = value
                elif key == "forward":
                    # Set scheduling direction for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("forward", scIdx)] = value
                    # Mark that this task has explicit scheduling (not inherited from project)
                    obj._explicit_scheduling = True  # type: ignore[union-attr]
                elif key == "scenario_attr":
                    # Handle scenario-specific attributes like ('delayed', ('effort', 320))
                    scenario_id, attr_data = value
                    scenario_idx = self._get_scenario_index(obj.project, scenario_id)
                    if scenario_idx is not None and attr_data and isinstance(attr_data, tuple):
                        attr_key, attr_value = attr_data
                        obj[(attr_key, scenario_idx)] = attr_value
                elif key == "journalentry":
                    # Create a journal entry for this task
                    self._create_journal_entry(obj, value)  # type: ignore[arg-type]
                elif key == "charge":
                    # charge is a tuple (amount, mode) where mode is 'onstart', 'onend', or 'perday'
                    amount, _mode = value
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("charge", scIdx)] = amount
                        # Note: mode (onstart/onend/perday) affects when charge is applied
                        # For now we store just the amount; mode handling can be added later
                elif key == "chargeset":
                    # chargeset specifies which account to charge to
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("chargeset", scIdx)] = value
                elif key == "purge_chargeset":
                    # Clear inherited chargeset
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("chargeset", scIdx)] = []
                elif key == "leaves":
                    # Resource leaves - create Leave objects and store on resource
                    from scriptplan.core.leave import Leave
                    from scriptplan.utils.time import TimeInterval

                    leave_type = value.get("type", "annual")
                    start_date = value.get("start")
                    end_date = value.get("end", start_date)

                    if start_date and end_date:
                        interval = TimeInterval(start_date, end_date)
                        type_idx = Leave.Types.get(leave_type, 5)  # Default to 'annual' (5)
                        leave = Leave(interval, type_idx)

                        # Store leaves as a list for all scenarios
                        for scIdx in range(obj.project.scenarioCount()):
                            existing = obj.get("leaves", scIdx) or []
                            if not isinstance(existing, list):
                                existing = [existing]
                            existing.append(leave)
                            obj[("leaves", scIdx)] = existing
                elif key == "limits":
                    # Task or resource limits - create Limits object
                    from scriptplan.core.limits import Limits

                    limits_obj = Limits()
                    limits_obj.setProject(obj.project)

                    # value is a list of limit dicts from parsing
                    for limit_def in value:
                        limit_type = limit_def.get("type", "dailymax")
                        limit_value = limit_def.get("value", 0)
                        limit_resources = limit_def.get("resources")

                        if limit_resources:
                            # Resource-specific limits
                            for res_id in limit_resources:
                                limits_obj.setLimit(limit_type, limit_value, resource=res_id)
                        else:
                            # General limit
                            limits_obj.setLimit(limit_type, limit_value)

                    # Store limits on task/resource for all scenarios
                    # IMPORTANT: Each scenario needs its own copy of the limits
                    # because they track usage counters independently
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("limits", scIdx)] = limits_obj.copy()
                elif key == "workinghours":
                    # Working hours for resource or shift
                    from scriptplan.core.working_hours import WorkingHours

                    # Check if working hours already exist
                    existing_wh = obj.get("workinghours", 0)
                    wh = existing_wh if existing_wh and hasattr(existing_wh, "set_hours") else WorkingHours(obj.project)

                    if isinstance(value, dict):
                        days = value.get("days", [])
                        ranges = value.get("ranges", [])
                        wh.set_hours(days, ranges)

                    # Store working hours for all scenarios
                    for scIdx in range(obj.project.scenarioCount()):
                        obj[("workinghours", scIdx)] = wh
                elif key == "workinghours_shift":
                    # Resource references a shift for its working hours
                    # Lookup the shift and copy its working hours
                    shift_id = value
                    shift = obj.project.shifts[shift_id] if hasattr(obj.project, "shifts") else None
                    if shift:
                        for scIdx in range(obj.project.scenarioCount()):
                            # Store the shift reference - ResourceScenario.onShift will use it
                            obj[("shifts", scIdx)] = shift
                elif key == "vacation":
                    # Resource vacation - similar to leaves but type is always vacation
                    from scriptplan.core.leave import Leave
                    from scriptplan.utils.time import TimeInterval

                    start_date = value.get("start")
                    end_date = value.get("end", start_date)

                    if start_date and end_date:
                        interval = TimeInterval(start_date, end_date)
                        type_idx = Leave.Types.get("annual", 5)  # Vacation treated as annual leave
                        leave = Leave(interval, type_idx)

                        # Store leaves as a list for all scenarios
                        for scIdx in range(obj.project.scenarioCount()):
                            existing = obj.get("leaves", scIdx) or []
                            if not isinstance(existing, list):
                                existing = [existing]
                            existing.append(leave)
                            obj[("leaves", scIdx)] = existing
                elif key == "booking":
                    # Resource booking - blocks resource during a time period
                    # booking "name" date +duration (e.g., "Maintenance" 2025-05-12-09:00 +6h)
                    import re
                    from datetime import timedelta

                    from scriptplan.core.leave import Leave
                    from scriptplan.utils.time import TimeInterval

                    start_date = value.get("start")
                    duration_str = value.get("duration", "0h")

                    if start_date:
                        # Parse duration to compute end date
                        match = re.match(r"(\d+(?:\.\d+)?)\s*([hdwmymin]+)", str(duration_str))
                        if match:
                            num = float(match.group(1))
                            unit = match.group(2)
                            if unit == "h":
                                delta = timedelta(hours=num)
                            elif unit == "min":
                                delta = timedelta(minutes=num)
                            elif unit == "d":
                                delta = timedelta(days=num)
                            else:
                                delta = timedelta(hours=num)
                        else:
                            delta = timedelta(hours=0)

                        end_date = start_date + delta
                        interval = TimeInterval(start_date, end_date)
                        # Use special type to mark as booking (treated as unavailable)
                        type_idx = Leave.Types.get("special", 3)
                        leave = Leave(interval, type_idx)

                        # Store as leaves (blocks resource availability)
                        for scIdx in range(obj.project.scenarioCount()):
                            existing = obj.get("leaves", scIdx) or []
                            if not isinstance(existing, list):
                                existing = [existing]
                            existing.append(leave)
                            obj[("leaves", scIdx)] = existing
                else:
                    with contextlib.suppress(ValueError, KeyError, AttributeError):
                        obj[key] = value

    def _get_scenario_index(self, project: Project, scenario_id: str) -> Optional[int]:
        """Get the index of a scenario by its ID."""
        for i, scenario in enumerate(project.scenarios):
            if scenario.id == scenario_id:
                return i
        return None

    def _create_journal_entry(self, task: Task, entry_data: dict[str, Any]) -> None:
        """Create a journal entry for a task.

        Args:
            task: The Task object this entry belongs to
            entry_data: Dict with 'date', 'headline', and 'body' keys
        """
        from scriptplan.core.journal import AlertLevel

        journal = task.project.attributes.get("journal")
        if journal is None:
            return

        date = entry_data.get("date")
        headline = entry_data.get("headline", "")
        body = entry_data.get("body", {})

        # Create the journal entry
        entry = journal.create_entry(date, headline, task)

        # Set body attributes
        if body.get("author"):
            # Look up the author resource
            author_id = body["author"]
            author = task.project.resources[author_id] if author_id else None
            entry.author = author

        alert_str = body.get("alert", "green")
        if alert_str == "red":
            entry.alert_level = AlertLevel.RED
        elif alert_str == "yellow":
            entry.alert_level = AlertLevel.YELLOW
        else:
            entry.alert_level = AlertLevel.GREEN

        entry.summary = body.get("summary")
        entry.details = body.get("details")

    def _create_report(self, project: Project, report_data: dict[str, Any], parent: Optional[Any] = None) -> Any:
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
            self._apply_report_attribute(report, attr, default_formats)

        # If no formats were set, use defaults
        if not report.get("formats"):
            report["formats"] = default_formats

        return report

    def _apply_report_attribute(self, report: Any, attr: Any, default_formats: list[Any]) -> None:
        """Apply a single attribute to a report.

        Args:
            report: The Report object
            attr: The attribute (can be tuple, dict, Token, Tree, or string)
            default_formats: List to accumulate format types
        """
        from lark import Token

        from scriptplan.report.report import ReportFormat

        if attr is None:
            return

        if isinstance(attr, dict):
            # Nested report definition
            attr_type = attr.get("type")
            if attr_type in ["taskreport", "resourcereport", "textreport", "accountreport"]:
                self._create_report(report.project, attr, report)
            return

        if isinstance(attr, tuple):
            key, value = attr
            if key == "columns":
                # value is list of column specs
                report["columns"] = value
            elif key == "formats":
                # value is list of format strings
                formats = []
                for fmt_str in value:
                    fmt_str = fmt_str.lower()
                    if fmt_str == "json":
                        formats.append(ReportFormat.JSON)
                    elif fmt_str == "csv":
                        formats.append(ReportFormat.CSV)
                    elif fmt_str == "ical":
                        formats.append(ReportFormat.ICAL)
                    elif fmt_str == "tjp":
                        formats.append(ReportFormat.TJP)
                    elif fmt_str == "niku":
                        formats.append(ReportFormat.NIKU)
                report["formats"] = formats
            elif key == "sort":
                report["sort"] = value
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
                # Filter expression for hideResource, hideTask, etc.
                # Store as filter
                if token_val.startswith("@") or token_val.startswith("~"):
                    # Could be hideResource or hideTask - store both
                    if not report.get("hideResource"):
                        report["hideResource"] = token_val
                    elif not report.get("hideTask"):
                        report["hideTask"] = token_val
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


class ProjectFileParser:
    """Parser for TJP project files."""

    def __init__(self) -> None:
        grammar_path: str = os.path.join(os.path.dirname(__file__), "tjp.lark")
        with open(grammar_path) as f:
            self.grammar: str = f.read()
        self.parser: Lark = Lark(self.grammar, start="start", parser="lalr")

    def parse(self, text: str, preprocess_macros: bool = True, schedule: bool = True) -> Project:
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
