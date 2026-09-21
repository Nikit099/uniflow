from collections.abc import Mapping
from typing import Any

OPS = {"eq", "neq", "in", "not_in", "exists", "not_exists", "gt", "gte", "lt", "lte"}


class InvalidRule(ValueError):
    pass


def _field(context: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    value: Any = context
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return False, None
        value = value[part]
    return True, value


def evaluate_rule(rule: Mapping[str, Any] | None, context: Mapping[str, Any]) -> bool:
    if not rule:
        return True
    combinators = [key for key in ("all", "any") if key in rule]
    if combinators:
        if len(combinators) != 1 or len(rule) != 1:
            raise InvalidRule("A combinator rule must contain only all or any")
        items = rule[combinators[0]]
        if not isinstance(items, list) or not items:
            raise InvalidRule("Combinator requires a non-empty list")
        results = [evaluate_rule(item, context) for item in items]
        return all(results) if combinators[0] == "all" else any(results)
    if set(rule) != {"field", "op", "value"} and set(rule) != {"field", "op"}:
        raise InvalidRule("Condition requires field, op and optional value")
    field, op = rule["field"], rule["op"]
    if not isinstance(field, str) or op not in OPS:
        raise InvalidRule("Unknown field or operator")
    exists, actual = _field(context, field)
    if op == "exists":
        return exists and actual is not None
    if op == "not_exists":
        return not exists or actual is None
    if "value" not in rule:
        raise InvalidRule("Operator requires value")
    expected = rule["value"]
    try:
        return {
            "eq": lambda: actual == expected,
            "neq": lambda: actual != expected,
            "in": lambda: actual in expected,
            "not_in": lambda: actual not in expected,
            "gt": lambda: actual > expected,
            "gte": lambda: actual >= expected,
            "lt": lambda: actual < expected,
            "lte": lambda: actual <= expected,
        }[op]()
    except (TypeError, KeyError) as exc:
        raise InvalidRule("Invalid operands") from exc
