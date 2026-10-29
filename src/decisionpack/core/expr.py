"""A small, safe expression evaluator for specs.

Specs are YAML files that people write and, through the API, upload. They contain formulas
such as ``sum(approved) / sum(clicks)`` or ``pages > 0 and duration > 60``. Those must never
reach ``eval``. This module parses with ``ast`` and walks only a whitelist of node types.
"""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

MAX_LENGTH = 500


class ExpressionError(ValueError):
    """The expression is malformed, unsafe or refers to something unknown."""


def _agg(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    return lambda x: fn(np.asarray(x))


FUNCTIONS: dict[str, tuple[Callable[..., Any], int]] = {
    "sum": (_agg(np.sum), 1),
    "mean": (_agg(np.mean), 1),
    "count": (lambda x: len(np.asarray(x)), 1),
    "min": (_agg(np.min), 1),
    "max": (_agg(np.max), 1),
    "abs": (np.abs, 1),
    "sqrt": (np.sqrt, 1),
    "log": (np.log, 1),
    "exp": (np.exp, 1),
    "where": (np.where, 3),
}

_BINOPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: np.divide,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_CMPOPS: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}


def evaluate(expression: str, namespace: Mapping[str, Any]) -> Any:
    """Evaluate ``expression`` with names looked up in ``namespace``.

    Values may be scalars, NumPy arrays or pandas Series; arithmetic is vectorised. Division by
    zero gives ``inf`` or ``nan`` instead of raising, as NumPy does.
    """
    if len(expression) > MAX_LENGTH:
        raise ExpressionError(f"expression is too long ({len(expression)} > {MAX_LENGTH})")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"cannot parse {expression!r}: {exc.msg}") from exc
    with np.errstate(divide="ignore", invalid="ignore"):
        return _eval(tree.body, namespace)


def _eval(node: ast.AST, ns: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool | int | float | str):
            return node.value
        raise ExpressionError(f"unsupported constant {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id not in ns:
            known = ", ".join(sorted(ns)[:12])
            raise ExpressionError(f"unknown name {node.id!r}; known names include: {known}")
        return ns[node.id]
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise ExpressionError(f"operator {type(node.op).__name__} is not allowed")
        return op(_eval(node.left, ns), _eval(node.right, ns))
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, ns)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.Not):
            return np.logical_not(value)
        raise ExpressionError(f"operator {type(node.op).__name__} is not allowed")
    if isinstance(node, ast.BoolOp):
        combine = np.logical_and if isinstance(node.op, ast.And) else np.logical_or
        result = _eval(node.values[0], ns)
        for operand in node.values[1:]:
            result = combine(result, _eval(operand, ns))
        return result
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ns)
        result: Any = None
        for op_node, comparator in zip(node.ops, node.comparators, strict=True):
            cmp = _CMPOPS.get(type(op_node))
            if cmp is None:
                raise ExpressionError(f"comparison {type(op_node).__name__} is not allowed")
            right = _eval(comparator, ns)
            piece = cmp(left, right)
            result = piece if result is None else np.logical_and(result, piece)
            left = right
        return result
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
            raise ExpressionError(f"only these functions are allowed: {', '.join(FUNCTIONS)}")
        if node.keywords:
            raise ExpressionError("keyword arguments are not allowed")
        fn, arity = FUNCTIONS[node.func.id]
        if len(node.args) != arity:
            raise ExpressionError(
                f"{node.func.id}() takes {arity} argument(s); got {len(node.args)}"
            )
        return fn(*[_eval(a, ns) for a in node.args])
    raise ExpressionError(f"{type(node).__name__} expressions are not allowed")
