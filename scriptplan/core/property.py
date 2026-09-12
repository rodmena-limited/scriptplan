"""The property model, re-exported.

This module was a single 1400-line file holding four separable things: the
attribute type system, the set of properties of one kind, an ordered list of
them, and the property tree node itself. They now live in their own modules;
this one keeps the import path that the rest of the codebase and its tests
already use.
"""

from __future__ import annotations

from scriptplan.core.attributes import (
    AccountAttribute,
    AlertLevelDefinitions,
    AttributeBase,
    AttributeDefinition,
    AttributeOverwrite,
    BooleanAttribute,
    ColumnListAttribute,
    DateAttribute,
    DefinitionListAttribute,
    FlagListAttribute,
    FloatAttribute,
    FormatListAttribute,
    IntegerAttribute,
    Journal,
    JournalSortListAttribute,
    KeywordArray,
    LeaveList,
    LeaveListAttribute,
    ListAttributeBase,
    LogicalExpressionAttribute,
    LogicalExpressionListAttribute,
    NodeListAttribute,
    PropertyAttribute,
    RealFormat,
    RealFormatAttribute,
    ReferenceAttribute,
    ResourceListAttribute,
    RichTextAttribute,
    ScenarioListAttribute,
    ShiftAssignmentsAttribute,
    SortListAttribute,
    StringAttribute,
    SymbolAttribute,
    SymbolListAttribute,
    TaskDepListAttribute,
    deep_clone,
)
from scriptplan.core.property_list import COMPUTED_SORT_CRITERIA, PropertyList
from scriptplan.core.property_set import PropertySet, PTNProxy
from scriptplan.core.property_tree_node import PropertyTreeNode

# Alias kept for callers that spell it this way.
ListAttribute = ListAttributeBase

__all__ = [
    "COMPUTED_SORT_CRITERIA",
    "AccountAttribute",
    "AlertLevelDefinitions",
    "AttributeBase",
    "AttributeDefinition",
    "AttributeOverwrite",
    "BooleanAttribute",
    "ColumnListAttribute",
    "DateAttribute",
    "DefinitionListAttribute",
    "FlagListAttribute",
    "FloatAttribute",
    "FormatListAttribute",
    "IntegerAttribute",
    "Journal",
    "JournalSortListAttribute",
    "KeywordArray",
    "LeaveList",
    "LeaveListAttribute",
    "ListAttribute",
    "ListAttributeBase",
    "LogicalExpressionAttribute",
    "LogicalExpressionListAttribute",
    "NodeListAttribute",
    "PTNProxy",
    "PropertyAttribute",
    "PropertyList",
    "PropertySet",
    "PropertyTreeNode",
    "RealFormat",
    "RealFormatAttribute",
    "ReferenceAttribute",
    "ResourceListAttribute",
    "RichTextAttribute",
    "ScenarioListAttribute",
    "ShiftAssignmentsAttribute",
    "SortListAttribute",
    "StringAttribute",
    "SymbolAttribute",
    "SymbolListAttribute",
    "TaskDepListAttribute",
    "deep_clone",
]
