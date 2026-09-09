"""TJP Parser for TaskJuggler project files."""

import contextlib
import os
from datetime import datetime
from typing import Any, Optional, Union

from lark import Lark, Token, Transformer, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.exceptions import (
    DuplicateDefinitionError,
    SemanticError,
    UnsupportedFormatError,
)
from scriptplan.core.timezones import to_utc
from scriptplan.core.resolution import derive_resolution
from scriptplan.core.units import Duration, parse_calendar_duration, parse_working_hours
from scriptplan.core.project import Project
from scriptplan.core.resource import Resource
from scriptplan.core.task import Task
from scriptplan.parser.attribute_apply import apply_property_attributes
from scriptplan.report.logical_expression import parse_expression
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

    def _limit(self, kind: str, items: list[Any]) -> dict[str, Any]:
        """One limit of any kind: an amount of working time per period."""
        duration: Any = items[0] if items else "0h"
        resources: Optional[Any] = items[1] if len(items) > 1 else None
        hours: Union[float, int] = (
            self._parse_duration_to_hours(duration) if isinstance(duration, str) else float(duration)
        )
        return {"type": kind, "value": hours, "resources": resources}

    def limit_dailymax(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("dailymax", items)

    def limit_dailymin(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("dailymin", items)

    def limit_weeklymax(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("weeklymax", items)

    def limit_weeklymin(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("weeklymin", items)

    def limit_monthlymax(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("monthlymax", items)

    def limit_monthlymin(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("monthlymin", items)

    def limit_maximum(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("maximum", items)

    def limit_minimum(self, items: list[Any]) -> dict[str, Any]:
        return self._limit("minimum", items)

    def limits_resources(self, items: list[Any]) -> list[str]:
        """Parse limits resources: { resources id1, id2, ... }."""
        return [self._get_value(i) for i in items]

    def _parse_duration_to_hours(self, duration_str: str, round_to_slots: bool = False) -> Union[float, int]:
        """A limit is an amount of working time, read with the shared table.

        The previous regex matched a single optional unit letter, so `30min`
        was read as 30 months: a 30-minute cap became a 4800-hour one.
        """
        hours = parse_working_hours(duration_str)
        return round(hours) if round_to_slots else hours

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
        return ("timingresolution", int(parse_calendar_duration(duration)))

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
        """duration is calendar time: 2d is 48 hours, weekend or not."""
        return ("duration", Duration(items[0], Duration.CALENDAR))

    def task_length(self, items: list[Any]) -> tuple[str, Any]:
        """length is working time: 2d is two working days."""
        return ("length", Duration(items[0], Duration.WORKING))

    def task_maxend(self, items: list[Any]) -> tuple[str, Any]:
        return ("maxend", items[0])

    def task_maxstart(self, items: list[Any]) -> tuple[str, Any]:
        return ("maxstart", items[0])

    def task_minend(self, items: list[Any]) -> tuple[str, Any]:
        return ("minend", items[0])

    def task_minstart(self, items: list[Any]) -> tuple[str, Any]:
        return ("minstart", items[0])

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
        """Handle scenario-specific duration attribute (calendar time)."""
        return ("duration", Duration(items[0], Duration.CALENDAR))

    def scenario_length(self, items: list[Any]) -> tuple[str, Any]:
        """Handle scenario-specific length attribute (working time)."""
        return ("length", Duration(items[0], Duration.WORKING))

    # Task attribute helpers
    def effort_value(self, items: list[Any]) -> tuple[str, Duration]:
        """effort is working time: a day is dailyworkinghours long, m is months."""
        num: str = self._get_value(items[0])
        unit: str = self._get_value(items[1])
        return ("effort", Duration(f"{num}{unit}", Duration.WORKING))

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
        """One allocate statement: a list of allocations, each with its options."""
        allocations = [item for item in items if isinstance(item, dict)]
        return ("allocate", {"allocations": allocations})

    def allocate_item(self, items: list[Any]) -> dict[str, Any]:
        """One resource in an allocate statement, with the options bound to it."""
        resource_id = self._get_value(items[0])
        options: dict[str, Any] = {}
        for extra in items[1:]:
            if isinstance(extra, dict):
                options.update(extra)
        return {"resource": resource_id, **options}

    def allocate_options(self, items: list[Any]) -> dict[str, Any]:
        """Merge the options written for one resource."""
        merged: dict[str, Any] = {}
        for item in items:
            if isinstance(item, dict):
                merged.update(item)
        return merged

    def alloc_persistent(self, items: list[Any]) -> dict[str, Any]:
        """Once a resource is picked for this task, keep it for the whole task."""
        return {"persistent": True}

    def alloc_mandatory(self, items: list[Any]) -> dict[str, Any]:
        """This resource must be free for the task to make progress at all."""
        return {"mandatory": True}

    def alloc_alternative(self, items: list[Any]) -> dict[str, Any]:
        return {"alternative": [self._get_value(i) for i in items]}

    def alloc_select(self, items: list[Any]) -> dict[str, Any]:
        return {"select": self._get_value(items[0])}

    def alloc_limits(self, items: list[Any]) -> dict[str, Any]:
        return {"limits": items[0] if items else []}

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

        # The file is written in the project's timezone; scheduling happens in
        # UTC so that resources in different zones share one axis.
        self._timezone = project["timezone"]
        for key in ("start", "end", "markdate"):
            if isinstance(project[key], datetime):
                project[key] = to_utc(project[key], self._timezone)

        # With no explicit timingresolution, the slot size is derived from the
        # times the file actually uses, so a project written to the half hour
        # is scheduled to the half hour without the user having to say so, and
        # one written to the hour keeps hour-sized slots.
        self._explicit_resolution = any(
            isinstance(attr, tuple) and attr[0] == "timingresolution"
            for attr in proj_data.get("attributes", [])
        )

        # Apply global attributes
        self._apply_global_attributes(project, data.get("global_attributes", []))

        # Apply property declarations (resources, tasks, accounts)
        for prop in data.get("property_declarations", []):
            self._create_property(project, prop)

        # Resolve dependencies after all tasks are created
        self._resolve_dependencies(project)

        # Resolve precedes relationships (convert to dependencies on target tasks)
        self._resolve_precedes(project)

        # Every allocation must name a resource that exists.
        self._validate_allocations(project)

        # Inherit attributes from parents for all tasks
        self._inherit_all_attributes(project)

        # Now that every task, shift and resource is known, the slot size can
        # be chosen to fit the times they use.
        if not getattr(self, "_explicit_resolution", False):
            project["timingresolution"] = derive_resolution(project)

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
                if dep_task is None:
                    raise SemanticError(
                        f"task '{task.fullId}' depends on '{dep_ref}', which is not a task in "
                        f"this project. A dependency that does not resolve would silently "
                        f"disappear from the schedule."
                    )
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

    def _validate_allocations(self, project: Project) -> None:
        """Reject an allocation naming a resource that does not exist.

        Resource lookup is otherwise lazy and forgiving: an unknown id resolves
        to None at scheduling time and the task quietly books nothing.
        """
        known = {resource.id for resource in project.resources}
        known.update(resource.fullId for resource in project.resources)

        for task in project.tasks:
            for scIdx in range(project.scenarioCount()):
                for name in self._allocation_ids(task.get("allocate", scIdx)):
                    if name not in known:
                        raise SemanticError(
                            f"task '{task.fullId}' allocates '{name}', which is not a resource "
                            f"in this project. The task would silently book nothing."
                        )
                break  # allocate is set identically for every scenario here

    @staticmethod
    def _allocation_ids(allocations: Any) -> list[str]:
        """Resource ids named by an allocate attribute, primary and alternative."""
        from scriptplan.core.allocation_plan import AllocationPlan

        names: list[str] = []
        for entry in AllocationPlan._entries(allocations):
            resource = entry.get("resource")
            if isinstance(resource, str):
                names.append(resource)
            names.extend(name for name in entry.get("alternative", []) if isinstance(name, str))
        return names

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
                if target_task is None:
                    raise SemanticError(
                        f"task '{source_task.fullId}' precedes '{prec_ref}', which is not a task "
                        f"in this project."
                    )
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
                        interval = TimeInterval(
                            to_utc(start_date, project["timezone"]),
                            to_utc(end_date, project["timezone"]),
                        )
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
                        interval = TimeInterval(
                            to_utc(start_date, project["timezone"]),
                            to_utc(end_date, project["timezone"]),
                        )
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
        """Apply attributes to a property object.

        Delegates to parser.attribute_apply, which has no silent fallback: an
        attribute it cannot place raises rather than being dropped.
        """
        apply_property_attributes(self, obj, attributes, prop_type)

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

    def _resolve_sort_criteria(self, project: Project, criteria: Any) -> list[Any]:
        """Turn parsed sort criteria into (attribute, ascending, scenarioIdx)."""
        resolved: list[tuple[str, bool, int]] = []
        for item in criteria or []:
            if not isinstance(item, tuple) or len(item) != 3:
                continue
            attribute, ascending, scenario = item
            scenario_idx = -1
            if scenario:
                index = self._get_scenario_index(project, str(scenario))
                if index is None:
                    raise SemanticError(
                        f"sort criterion '{scenario}.{attribute}' names a scenario that is not defined"
                    )
                scenario_idx = index
            resolved.append((str(attribute), bool(ascending), scenario_idx))
        return resolved

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
                report[key] = self._resolve_sort_criteria(report.project, value)
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
