from __future__ import annotations
from typing import Any


def get_path(data: dict, path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def evaluate_condition(condition: dict, facts: dict) -> bool | None:
    path = condition["fact"]
    actual = get_path(facts, path)
    op = condition.get("operator", "eq")
    expected = condition.get("value")
    if actual is None:
        return None
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        return actual in expected
    if op == "contains_any":
        if not isinstance(actual, list):
            return False
        return any(item in actual for item in expected)
    if op == "contains":
        if not isinstance(actual, list):
            return False
        return expected in actual
    raise ValueError(f"Unsupported operator: {op}")


def evaluate_expression(expr: dict, facts: dict) -> bool | None:
    if "all" in expr:
        results = [evaluate_expression(item, facts) for item in expr["all"]]
        if False in results:
            return False
        if None in results:
            return None
        return True
    if "any" in expr:
        results = [evaluate_expression(item, facts) for item in expr["any"]]
        if True in results:
            return True
        if None in results:
            return None
        return False
    if "not" in expr:
        value = evaluate_expression(expr["not"], facts)
        return None if value is None else not value
    return evaluate_condition(expr, facts)
