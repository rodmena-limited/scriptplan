"""The attributes a project's tasks, resources, reports and the rest may carry.

Each row is (id, display name, type, inherited from parent, inherited from
project, scenario-specific, default). They live apart from Project because they
are a data definition rather than behaviour, and reading the scheduler should
not mean scrolling past two hundred rows of them.
"""

from __future__ import annotations

from typing import Any

from scriptplan.core.property import (
    AttributeBase,
    AttributeDefinition,
    BooleanAttribute,
    ColumnListAttribute,
    DateAttribute,
    FlagListAttribute,
    FloatAttribute,
    FormatListAttribute,
    IntegerAttribute,
    LeaveListAttribute,
    ListAttribute,
    LogicalExpressionAttribute,
    PropertyAttribute,
    ResourceListAttribute,
    RichTextAttribute,
    ScenarioListAttribute,
    ShiftAssignmentsAttribute,
    SortListAttribute,
    StringAttribute,
    SymbolAttribute,
    SymbolListAttribute,
    TaskDepListAttribute,
)
from scriptplan.utils.time import TjTime

__all__ = [
    "define_account_attributes",
    "define_report_attributes",
    "define_resource_attributes",
    "define_scenario_attributes",
    "define_shift_attributes",
    "define_task_attributes",
]


def define_scenario_attributes(property_set: Any) -> None:
    attrs: list[list[Any]] = [
        ["active", "Enabled", BooleanAttribute, True, False, False, True],
        ["ownbookings", "Own Bookings", BooleanAttribute, False, False, False, True],
        ["projection", "Projection Mode", BooleanAttribute, True, False, False, False],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))


def define_account_attributes(property_set: Any) -> None:
    attrs: list[list[Any]] = [
        # ID           Name            Type                     Inh   InhPrj Scen  Default
        ["aggregate", "Aggregate", SymbolAttribute, True, False, False, "tasks"],
        ["bsi", "BSI", StringAttribute, False, False, False, ""],
        ["credits", "Credits", ListAttribute, False, False, True, []],
        ["index", "Index", IntegerAttribute, False, False, False, -1],
        ["flags", "Flags", FlagListAttribute, True, False, True, []],
        ["tree", "Tree Index", StringAttribute, False, False, False, ""],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))


def define_shift_attributes(property_set: Any) -> None:
    attrs: list[list[Any]] = [
        # ID           Name            Type                     Inh   InhPrj Scen  Default
        ["bsi", "BSI", StringAttribute, False, False, False, ""],
        ["index", "Index", IntegerAttribute, False, False, False, -1],
        ["leaves", "Leaves", LeaveListAttribute, True, True, True, []],
        ["replace", "Replace", BooleanAttribute, True, False, True, False],
        ["timezone", "Time Zone", StringAttribute, True, True, True, TjTime.timeZone()],
        ["tree", "Tree Index", StringAttribute, False, False, False, ""],
        ["workinghours", "Working Hours", ShiftAssignmentsAttribute, True, True, True, None],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))


def define_resource_attributes(property_set: Any) -> None:
    # Add attributes required by ResourceScenario
    attrs: list[list[Any]] = [
        ["alloctdeffort", "Allocated Effort", IntegerAttribute, True, False, True, 0],
        ["booking", "Booking", ResourceListAttribute, True, False, True, []],
        ["bsi", "BSI", StringAttribute, False, False, False, ""],
        ["email", "Email", StringAttribute, False, False, False, ""],
        ["index", "Index", IntegerAttribute, False, False, False, -1],
        ["chargeset", "Charge Set", StringAttribute, True, False, True, []],
        ["criticalness", "Criticalness", FloatAttribute, False, False, True, 0.0],
        ["directreports", "Direct Reports", ResourceListAttribute, True, False, True, []],
        ["duties", "Duties", TaskDepListAttribute, True, False, True, []],
        ["efficiency", "Efficiency", FloatAttribute, True, False, True, 1.0],
        ["effort", "Effort", IntegerAttribute, True, False, True, 0],
        ["flags", "Flags", FlagListAttribute, True, False, True, []],
        ["leaves", "Leaves", LeaveListAttribute, True, False, True, []],  # Changed to LeaveListAttribute
        ["leaveallowances", "Leave Allowances", AttributeBase, True, False, True, None],  # Placeholder
        ["limits", "Limits", AttributeBase, True, False, True, None],  # Placeholder
        ["managers", "Managers", ResourceListAttribute, True, False, True, []],
        ["note", "Note", StringAttribute, False, False, False, None],
        ["rate", "Rate", FloatAttribute, True, False, True, 0.0],
        ["reports", "Reports", ResourceListAttribute, True, False, True, []],
        ["shifts", "Shifts", ShiftAssignmentsAttribute, True, False, True, None],
        ["timezone", "Time Zone", StringAttribute, True, False, True, None],
        ["workinghours", "Working Hours", AttributeBase, True, False, True, None],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))


def define_task_attributes(property_set: Any) -> None:
    attrs: list[list[Any]] = [
        ["allocate", "Allocate", ListAttribute, True, False, True, []],
        ["assignedresources", "Assigned Resources", ListAttribute, False, False, True, []],
        ["booking", "Booking", ResourceListAttribute, True, False, True, []],
        ["bsi", "BSI", StringAttribute, False, False, False, ""],
        ["charge", "Charge", FloatAttribute, True, False, True, 0.0],
        ["chargeset", "Charge Set", StringAttribute, True, False, True, []],
        ["complete", "Complete", FloatAttribute, True, False, True, 0.0],
        ["competitors", "Competitors", ListAttribute, True, False, True, []],
        ["criticalness", "Criticalness", FloatAttribute, False, False, True, 0.0],
        ["depends", "Dependencies", TaskDepListAttribute, True, False, True, []],
        ["duration", "Duration", IntegerAttribute, True, False, True, 0],
        ["effort", "Effort", IntegerAttribute, True, False, True, 0],
        ["effortdone", "Effort Done", IntegerAttribute, True, False, True, 0],
        ["effortleft", "Effort Left", IntegerAttribute, True, False, True, 0],
        ["end", "End", DateAttribute, False, False, True, None],
        ["flags", "Flags", FlagListAttribute, True, False, True, []],
        ["forward", "Forward", BooleanAttribute, True, False, True, True],
        ["gauge", "Gauge", StringAttribute, True, False, True, None],
        ["index", "Index", IntegerAttribute, False, False, False, -1],
        ["length", "Length", IntegerAttribute, True, False, True, 0],
        ["limits", "Limits", PropertyAttribute, True, False, True, None],
        ["maxend", "Max End", DateAttribute, True, False, True, None],
        ["maxstart", "Max Start", DateAttribute, True, False, True, None],
        ["minend", "Min End", DateAttribute, True, False, True, None],
        ["minstart", "Min Start", DateAttribute, True, False, True, None],
        ["milestone", "Milestone", BooleanAttribute, True, False, True, False],
        ["note", "Note", StringAttribute, False, False, False, None],
        ["pathcriticalness", "Path Criticalness", FloatAttribute, False, False, True, 0.0],
        ["precedes", "Precedes", TaskDepListAttribute, True, False, True, []],
        ["priority", "Priority", IntegerAttribute, True, False, True, 500],
        ["projectionmode", "Projection Mode", BooleanAttribute, True, False, True, False],
        ["responsible", "Responsible", ListAttribute, True, False, True, []],
        ["scheduled", "Scheduled", BooleanAttribute, True, False, True, False],
        ["shifts", "Shifts", ShiftAssignmentsAttribute, True, False, True, None],
        ["start", "Start", DateAttribute, True, False, True, None],
        ["status", "Status", StringAttribute, True, False, True, ""],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))


def define_report_attributes(property_set: Any) -> None:
    attrs: list[list[Any]] = [
        # ID               Name                Type                     Inh    InhPrj  Scen   Default
        ["accountRoot", "Account Root", StringAttribute, True, False, False, None],
        ["auxDir", "Aux Directory", StringAttribute, True, True, False, ""],
        ["balance", "Balance", ListAttribute, True, False, False, []],
        ["caption", "Caption", RichTextAttribute, True, False, False, None],
        ["center", "Center", RichTextAttribute, True, False, False, None],
        ["columns", "Columns", ColumnListAttribute, True, False, False, []],
        ["currencyFormat", "Currency Format", StringAttribute, True, True, False, None],
        ["end", "End Date", DateAttribute, True, True, False, None],
        ["epilog", "Epilog", RichTextAttribute, True, False, False, None],
        ["flags", "Flags", FlagListAttribute, True, False, False, []],
        ["footer", "Footer", RichTextAttribute, True, False, False, None],
        ["formats", "Formats", FormatListAttribute, True, False, False, []],
        ["header", "Header", RichTextAttribute, True, False, False, None],
        ["headline", "Headline", RichTextAttribute, True, False, False, None],
        ["hideAccount", "Hide Account", LogicalExpressionAttribute, True, False, False, None],
        ["hideResource", "Hide Resource", LogicalExpressionAttribute, True, False, False, None],
        ["hideTask", "Hide Task", LogicalExpressionAttribute, True, False, False, None],
        ["interactive", "Interactive", BooleanAttribute, True, False, False, False],
        ["journalAttributes", "Journal Attributes", SymbolListAttribute, True, False, False, []],
        ["journalMode", "Journal Mode", SymbolAttribute, True, False, False, None],
        ["leafTasksOnly", "Leaf Tasks Only", BooleanAttribute, True, False, False, False],
        ["left", "Left", RichTextAttribute, True, False, False, None],
        ["loadUnit", "Load Unit", SymbolAttribute, True, True, False, "days"],
        ["numberFormat", "Number Format", StringAttribute, True, True, False, None],
        ["openNodes", "Open Nodes", ListAttribute, True, False, False, []],
        ["period", "Period", StringAttribute, True, True, False, None],
        ["prolog", "Prolog", RichTextAttribute, True, False, False, None],
        ["resourceRoot", "Resource Root", StringAttribute, True, False, False, None],
        ["right", "Right", RichTextAttribute, True, False, False, None],
        ["rollupAccount", "Rollup Account", LogicalExpressionAttribute, True, False, False, None],
        ["rollupResource", "Rollup Resource", LogicalExpressionAttribute, True, False, False, None],
        ["rollupTask", "Rollup Task", LogicalExpressionAttribute, True, False, False, None],
        ["scenarios", "Scenarios", ScenarioListAttribute, True, True, False, []],
        ["selfContained", "Self Contained", BooleanAttribute, True, False, False, False],
        ["showResources", "Show Resources", BooleanAttribute, True, False, False, False],
        ["showTasks", "Show Tasks", BooleanAttribute, True, False, False, False],
        ["sort", "Sort", SortListAttribute, True, False, False, []],
        ["sortAccounts", "Sort Accounts", SortListAttribute, True, False, False, []],
        ["sortResources", "Sort Resources", SortListAttribute, True, False, False, []],
        ["sortTasks", "Sort Tasks", SortListAttribute, True, False, False, []],
        ["start", "Start Date", DateAttribute, True, True, False, None],
        ["taskRoot", "Task Root", StringAttribute, True, False, False, None],
        ["timeFormat", "Time Format", StringAttribute, True, True, False, "%Y-%m-%d"],
        ["timeZone", "Time Zone", StringAttribute, True, True, False, None],
        ["title", "Title", StringAttribute, True, False, False, None],
        ["width", "Width", IntegerAttribute, True, False, False, None],
    ]
    for a in attrs:
        property_set.addAttributeType(AttributeDefinition(*a))
