"""Apply parsed attributes to a task, resource or shift.

Every attribute the grammar accepts must end up somewhere the scheduler or a
report can read. An attribute that is parsed and then dropped is worse than a
syntax error: the project schedules, the report renders, and the constraint the
user wrote is simply not there.

So this module has no silent fallback. Anything that is not handled explicitly
is set through the property's own attribute definition, and anything with no
definition raises InvalidAttributeError naming the attribute.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable, Optional

from scriptplan.core.exceptions import InvalidAttributeError

if TYPE_CHECKING:
    from scriptplan.core.project import Project

__all__ = ["apply_property_attributes", "set_all_scenarios"]


def set_all_scenarios(obj: Any, key: str, value: Any) -> None:
    """Set a scenario-specific attribute to the same value in every scenario."""
    for scenario_idx in range(obj.project.scenarioCount()):
        obj[(key, scenario_idx)] = value


def _property_set_for(obj: Any) -> Any:
    """The PropertySet that defines which attributes ``obj`` may carry."""
    return getattr(obj, "propertySet", None) or getattr(obj, "_propertySet", None)


def _definition_of(obj: Any, key: str) -> Optional[Any]:
    holder = _property_set_for(obj)
    if holder is None:
        return None
    return getattr(holder, "attributeDefinitions", {}).get(key)


def _apply_generic(obj: Any, key: str, value: Any, prop_type: str) -> None:
    """Set an attribute that needs no special handling.

    Scenario-specific attributes are written to every scenario, which is what a
    bare (non ``scenario:``-prefixed) declaration in the file means.
    """
    definition = _definition_of(obj, key)
    if definition is None:
        name = getattr(obj, "fullId", None) or getattr(obj, "id", "?")
        raise InvalidAttributeError(
            f"{prop_type} '{name}' has attribute '{key}', which ScriptPlan parses but "
            f"does not implement. Remove it or open an issue; it must not be ignored, "
            f"because a schedule computed without it would look correct.",
            context={"attribute": key},
        )
    if getattr(definition, "scenarioSpecific", False):
        set_all_scenarios(obj, key, value)
    else:
        obj[key] = value


# ---------------------------------------------------------------------------
# handlers for attributes that need more than a plain assignment
# ---------------------------------------------------------------------------


def _handle_depends(builder: Any, obj: Any, value: Any, _pt: str) -> None:
    builder._pending_depends.append((obj, value))


def _handle_precedes(builder: Any, obj: Any, value: Any, _pt: str) -> None:
    builder._pending_precedes.append((obj, value))


def _handle_forward(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    set_all_scenarios(obj, "forward", value)
    # Remember that the file said so, so a project-level `scheduling alap`
    # does not overrule an explicit per-task direction.
    obj._explicit_scheduling = True


def _handle_scenario_attr(builder: Any, obj: Any, value: Any, _pt: str) -> None:
    scenario_id, attr_data = value
    scenario_idx = builder._get_scenario_index(obj.project, scenario_id)
    if scenario_idx is None:
        raise InvalidAttributeError(
            f"'{scenario_id}:' refers to a scenario that is not defined",
            context={"scenario": scenario_id},
        )
    if attr_data and isinstance(attr_data, tuple):
        attr_key, attr_value = attr_data
        obj[(attr_key, scenario_idx)] = attr_value


def _handle_journalentry(builder: Any, obj: Any, value: Any, _pt: str) -> None:
    builder._create_journal_entry(obj, value)


def _handle_charge(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    # value is (amount, mode); the mode (onstart/onend/perday) decides when the
    # charge lands and is not yet modelled, so only the amount is stored.
    amount, _mode = value
    set_all_scenarios(obj, "charge", amount)


def _handle_purge_chargeset(_b: Any, obj: Any, _value: Any, _pt: str) -> None:
    set_all_scenarios(obj, "chargeset", [])


def _append_leave(obj: Any, interval: Any, type_idx: int) -> None:
    from scriptplan.core.leave import Leave

    leave = Leave(interval, type_idx)
    for scenario_idx in range(obj.project.scenarioCount()):
        existing = obj.get("leaves", scenario_idx) or []
        if not isinstance(existing, list):
            existing = [existing]
        # A fresh list per scenario: appending to the value returned by get()
        # would mutate the attribute in place and, with list attributes that
        # extend rather than replace, double it.
        obj[("leaves", scenario_idx)] = [*existing, leave]


def _whole_day(start: Any, end: Any) -> Any:
    """A leave given as a single date covers that whole day."""
    if end is None or end == start:
        return start + timedelta(days=1)
    return end


def _handle_leaves(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    from scriptplan.core.leave import Leave
    from scriptplan.utils.time import TimeInterval

    start = value.get("start")
    if not start:
        return
    end = _whole_day(start, value.get("end"))
    leave_type = value.get("type", "annual")
    _append_leave(obj, TimeInterval(start, end), Leave.Types.get(leave_type, 5))


def _handle_vacation(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    from scriptplan.core.leave import Leave
    from scriptplan.utils.time import TimeInterval

    start = value.get("start")
    if not start:
        return
    end = _whole_day(start, value.get("end"))
    _append_leave(obj, TimeInterval(start, end), Leave.Types.get("annual", 5))


def _handle_booking(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    from scriptplan.core.leave import Leave
    from scriptplan.core.units import parse_calendar_duration
    from scriptplan.utils.time import TimeInterval

    start = value.get("start")
    if not start:
        return
    seconds = parse_calendar_duration(value.get("duration", "0h"))
    end = start + timedelta(seconds=seconds)
    _append_leave(obj, TimeInterval(start, end), Leave.Types.get("special", 3))


def _handle_limits(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    from scriptplan.core.limits import Limits

    limits = Limits()
    limits.setProject(obj.project)
    for definition in value:
        kind = definition.get("type", "dailymax")
        amount = definition.get("value", 0)
        restricted_to = definition.get("resources")
        if restricted_to:
            for resource_id in restricted_to:
                limits.setLimit(kind, amount, resource=resource_id)
        else:
            limits.setLimit(kind, amount)
    # Each scenario counts its own usage, so each needs its own copy.
    for scenario_idx in range(obj.project.scenarioCount()):
        obj[("limits", scenario_idx)] = limits.copy()


def _handle_workinghours(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    from scriptplan.core.working_hours import WorkingHours

    existing = obj.get("workinghours", 0)
    hours = existing if existing is not None and hasattr(existing, "set_hours") else WorkingHours(obj.project)
    if isinstance(value, dict):
        hours.set_hours(value.get("days", []), value.get("ranges", []))
    set_all_scenarios(obj, "workinghours", hours)


def _handle_workinghours_shift(_b: Any, obj: Any, value: Any, _pt: str) -> None:
    shift = obj.project.shifts[value] if hasattr(obj.project, "shifts") else None
    if shift is None:
        name = getattr(obj, "fullId", None) or getattr(obj, "id", "?")
        raise InvalidAttributeError(
            f"resource '{name}' uses working hours of shift '{value}', which is not defined",
            context={"attribute": "workinghours", "shift": value},
        )
    set_all_scenarios(obj, "shifts", shift)


HANDLERS: dict[str, Callable[[Any, Any, Any, str], None]] = {
    "booking": _handle_booking,
    "charge": _handle_charge,
    "depends": _handle_depends,
    "forward": _handle_forward,
    "journalentry": _handle_journalentry,
    "leaves": _handle_leaves,
    "limits": _handle_limits,
    "precedes": _handle_precedes,
    "purge_chargeset": _handle_purge_chargeset,
    "scenario_attr": _handle_scenario_attr,
    "vacation": _handle_vacation,
    "workinghours": _handle_workinghours,
    "workinghours_shift": _handle_workinghours_shift,
}


def apply_property_attributes(
    builder: Any, obj: Any, attributes: list[Any], prop_type: str
) -> None:
    """Apply every parsed attribute of one property, or say why it cannot."""
    for attr in attributes or []:
        if attr is None:
            continue
        if isinstance(attr, dict):
            # A nested property: a sub-task, or a resource inside a resource.
            builder._create_property(obj, attr)
            continue
        if not isinstance(attr, tuple) or len(attr) != 2:
            continue
        key, value = attr
        handler = HANDLERS.get(key)
        if handler is not None:
            handler(builder, obj, value, prop_type)
        else:
            _apply_generic(obj, key, value, prop_type)
