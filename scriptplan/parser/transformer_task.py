"""Tasks: their dates, effort, dependencies, allocations and journal."""

from __future__ import annotations

from typing import Any, Optional, Union

from lark import Token, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.units import Duration, parse_calendar_duration, parse_working_hours



class TaskRules:
    """Transformer methods for tasks: their dates, effort, dependencies, allocations and journal."""

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
