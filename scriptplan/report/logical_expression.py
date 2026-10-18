"""Evaluate the logical expressions used by report filters.

`hidetask`, `hideresource`, `rolluptask` and `rollupresource` take an
expression over the property being considered:

    ~hasalert(0)                        a predicate, negated
    ~(delayed.end <= 2002-03-05)        a scenario-qualified attribute compared
    ~((plan.start <= X) & (plan.end > X))
    done                                a flag the property carries
    @all / @none                        everything / nothing

Before this existed the expression was kept as a string and evaluated with
``bool(expr)``, which is true of every non-empty string. A report that hid
anything hid everything and came back as a bare header.

An expression that cannot be read raises at parse time. Filters decide what a
reader sees, so one that is quietly ignored is worse than one that is rejected.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Union, cast

__all__ = ["PREDICATES", "ExpressionError", "LogicalExpression", "parse_expression"]


class ExpressionError(ValueError):
    """Raised when a filter expression cannot be read."""


# --------------------------------------------------------------------------
# predicates
# --------------------------------------------------------------------------


def _is_leaf(prop: Any, _scenario: int | None) -> bool:
    return bool(prop.leaf()) if hasattr(prop, "leaf") else False


def _attribute(prop: Any, name: str, scenario: int | None) -> Any:
    try:
        return prop.get(name, scenario if scenario is not None else 0)
    except Exception:
        try:
            return prop.get(name)
        except Exception:
            return None


def _is_milestone(prop: Any, scenario: int | None) -> bool:
    return bool(_attribute(prop, "milestone", scenario))


def _is_scheduled(prop: Any, scenario: int | None) -> bool:
    return bool(_attribute(prop, "scheduled", scenario))


def _is_resource(prop: Any, _scenario: int | None) -> bool:
    from scriptplan.core.resource import Resource

    return isinstance(prop, Resource)


def _is_task(prop: Any, _scenario: int | None) -> bool:
    from scriptplan.core.task import Task

    return isinstance(prop, Task)


def _has_alert(prop: Any, _scenario: int | None, level: Any = 0) -> bool:
    """True if this property, or one below it, carries a journal entry of at
    least ``level`` (0 green, 1 yellow, 2 red)."""
    project = getattr(prop, "project", None)
    journal = getattr(project, "attributes", {}).get("journal") if project is not None else None
    if journal is None:
        return False
    try:
        entries = list(journal.entries())
    except Exception:
        return False

    def covers(entry: Any) -> bool:
        node = getattr(entry, "property", None) or getattr(entry, "task", None)
        while node is not None:
            if node is prop:
                return True
            node = getattr(node, "parent", None)
        return False

    threshold = int(level)
    return any(int(getattr(e, "alert_level", 0)) >= threshold and covers(e) for e in entries)


#: Built-in predicates, by the name written in the file. `isleaf_` is
#: The .tjp format's "leaf of the report tree"; ScriptPlan does not prune the tree
#: before filtering, so it answers the same as `isleaf`.
PREDICATES: dict[str, Callable[..., bool]] = {
    "isleaf": _is_leaf,
    "isleaf_": _is_leaf,
    "ismilestone": _is_milestone,
    "isscheduled": _is_scheduled,
    "isresource": _is_resource,
    "istask": _is_task,
    "hasalert": _has_alert,
}


# --------------------------------------------------------------------------
# syntax tree
# --------------------------------------------------------------------------


class Node:
    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        raise NotImplementedError


class Constant(Node):
    def __init__(self, value: bool) -> None:
        self.value = value

    def evaluate(self, _prop: Any, _scenario: int | None) -> bool:
        return self.value


class Not(Node):
    def __init__(self, operand: Node) -> None:
        self.operand = operand

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        return not self.operand.evaluate(prop, scenario)


class And(Node):
    def __init__(self, left: Node, right: Node) -> None:
        self.left, self.right = left, right

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        return self.left.evaluate(prop, scenario) and self.right.evaluate(prop, scenario)


class Or(Node):
    def __init__(self, left: Node, right: Node) -> None:
        self.left, self.right = left, right

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        return self.left.evaluate(prop, scenario) or self.right.evaluate(prop, scenario)


class Call(Node):
    """A built-in predicate, with or without arguments."""

    def __init__(self, name: str, arguments: list[Any]) -> None:
        self.name, self.arguments = name, arguments

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        return PREDICATES[self.name](prop, scenario, *self.arguments)


class Flag(Node):
    """A flag the property carries, or a truthy attribute of the same name."""

    def __init__(self, name: str) -> None:
        self.name = name

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        flags = _attribute(prop, "flags", scenario) or []
        return self.name in flags


class Reference:
    """An attribute of the property, optionally qualified by scenario."""

    def __init__(self, text: str) -> None:
        parts = text.split(".")
        self.scenario: str | None = ".".join(parts[:-1]) or None
        self.attribute = parts[-1]

    def value(self, prop: Any, scenario: int | None) -> Any:
        index = scenario
        if self.scenario is not None:
            index = _scenario_index(prop, self.scenario)
        return _attribute(prop, self.attribute, index)


def _scenario_index(prop: Any, name: str) -> int | None:
    project = getattr(prop, "project", None)
    if project is None:
        return None
    for idx, scenario in enumerate(getattr(project, "scenarios", [])):
        if scenario.id == name:
            return idx
    return None


_COMPARISONS: dict[str, Callable[[Any, Any], bool]] = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "=": lambda a, b: a == b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class Comparison(Node):
    def __init__(self, left: Reference, operator: str, right: Any) -> None:
        self.left, self.operator, self.right = left, operator, right

    def evaluate(self, prop: Any, scenario: int | None) -> bool:
        left = self.left.value(prop, scenario)
        if left is None:
            # A property with no value for the attribute cannot satisfy a
            # comparison; saying so beats raising in the middle of a report.
            return False
        right = self.right
        if isinstance(left, datetime) and isinstance(right, str):
            right = _as_datetime(right)
        try:
            return _COMPARISONS[self.operator](left, right)
        except TypeError:
            return False


def _as_datetime(text: str) -> Any:
    for shape in ("%Y-%m-%d-%H:%M:%S", "%Y-%m-%d-%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, shape)
        except ValueError:
            continue
    return text


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<at>@(?:all|none))"
    r"|(?P<op><=|>=|!=|==|[<>=~&|()])"
    r"|(?P<call>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<args>[^()]*)\)"
    r"|(?P<date>\d{4}-\d{2}-\d{2}(?:-\d{2}:\d{2}(?::\d{2})?)?)"
    r"|(?P<number>-?\d+(?:\.\d+)?)"
    r"|(?P<string>\"[^\"]*\")"
    r"|(?P<name>[A-Za-z_][A-Za-z0-9_.]*)"
    r")"
)

Token = Union[str, tuple[str, Any]]


def _literal(text: str) -> Any:
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text.strip('"')


def _tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    position = 0
    while position < len(text):
        if text[position].isspace():
            position += 1
            continue
        match = _TOKEN.match(text, position)
        if not match or match.end() == position:
            raise ExpressionError(f"cannot read {text[position:position + 24]!r} in filter {text!r}")
        if match.group("at"):
            tokens.append(("const", match.group("at") == "@all"))
        elif match.group("op"):
            tokens.append(match.group("op"))
        elif match.group("call"):
            raw = (match.group("args") or "").strip()
            arguments = [_literal(part.strip()) for part in raw.split(",") if part.strip()]
            tokens.append(("call", (match.group("call"), arguments)))
        elif match.group("date"):
            tokens.append(("value", match.group("date")))
        elif match.group("number"):
            tokens.append(("value", _literal(match.group("number"))))
        elif match.group("string"):
            tokens.append(("value", match.group("string").strip('"')))
        else:
            tokens.append(("name", match.group("name")))
        position = match.end()
    return tokens


def parse_expression(text: str) -> LogicalExpression:
    """Parse a filter expression, or say why it cannot be read."""
    tokens = _tokenize(str(text))
    if not tokens:
        raise ExpressionError("filter expression is empty")
    position = 0

    def peek() -> Token | None:
        return tokens[position] if position < len(tokens) else None

    def take() -> Token:
        nonlocal position
        token = tokens[position]
        position += 1
        return token

    def parse_or() -> Node:
        node = parse_and()
        while peek() == "|":
            take()
            node = Or(node, parse_and())
        return node

    def parse_and() -> Node:
        node = parse_unary()
        while peek() == "&":
            take()
            node = And(node, parse_unary())
        return node

    def parse_unary() -> Node:
        token = peek()
        if token == "~":
            take()
            return Not(parse_unary())
        if token == "(":
            take()
            node = parse_or()
            if peek() != ")":
                raise ExpressionError(f"filter {text!r} is missing a closing bracket")
            take()
            return node
        return parse_atom()

    def parse_atom() -> Node:
        token = peek()
        if token is None:
            raise ExpressionError(f"filter {text!r} ends where a term was expected")
        if isinstance(token, tuple):
            take()
            kind, payload = token
            if kind == "const":
                return Constant(bool(payload))
            if kind == "call":
                name, arguments = cast("tuple[str, list[Any]]", payload)
                if name not in PREDICATES:
                    raise ExpressionError(
                        f"filter {text!r} calls '{name}', which is not a predicate ScriptPlan "
                        f"knows. Known predicates: {', '.join(sorted(PREDICATES))}."
                    )
                return Call(name, arguments)
            if kind == "name":
                return parse_name(str(payload))
            raise ExpressionError(f"filter {text!r} has a value where a term was expected")
        raise ExpressionError(f"filter {text!r} has '{token}' where a term was expected")

    def parse_name(name: str) -> Node:
        token = peek()
        if isinstance(token, str) and token in _COMPARISONS:
            operator = str(take())
            right = peek()
            if not isinstance(right, tuple) or right[0] not in ("value", "name"):
                raise ExpressionError(f"filter {text!r} has no value after '{operator}'")
            take()
            return Comparison(Reference(name), operator, right[1])
        if name in PREDICATES:
            return Call(name, [])
        return Flag(name)

    root = parse_or()
    if position != len(tokens):
        raise ExpressionError(f"filter {text!r} has text left over after the expression")
    return LogicalExpression(str(text), root)


class LogicalExpression:
    """A parsed filter expression."""

    def __init__(self, source: str, root: Node) -> None:
        self.source = source
        self._root = root

    def evaluate(self, prop: Any, scenario: int | None = None) -> bool:
        return self._root.evaluate(prop, scenario)

    def __repr__(self) -> str:
        return f"LogicalExpression({self.source!r})"
