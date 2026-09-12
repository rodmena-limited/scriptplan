"""Resources, shifts, working hours and limits."""

from __future__ import annotations

from typing import Any, Optional, Union

from lark import Token, Tree  # type: ignore[import-untyped,unused-ignore]

from scriptplan.core.units import Duration, parse_calendar_duration, parse_working_hours



class ResourceRules:
    """Transformer methods for resources, shifts, working hours and limits."""

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
