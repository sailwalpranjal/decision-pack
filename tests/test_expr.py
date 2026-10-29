from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from decisionpack.core.expr import ExpressionError, evaluate


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 20, 30, 40], "g": ["x", "y", "x", "y"]})


def ns(df: pd.DataFrame) -> dict[str, object]:
    return {c: df[c] for c in df.columns}


def test_arithmetic_and_precedence(df):
    assert evaluate("1 + 2 * 3", {}) == 7
    assert evaluate("(1 + 2) * 3", {}) == 9
    assert evaluate("2 ** 3 ** 2", {}) == 512
    assert evaluate("-3 + 5", {}) == 2
    assert evaluate("7 % 4", {}) == 3


def test_column_arithmetic_is_vectorised(df):
    out = evaluate("a * 2 + b", ns(df))
    assert list(out) == [12, 24, 36, 48]


def test_aggregates(df):
    assert evaluate("sum(a)", ns(df)) == 10
    assert evaluate("mean(b)", ns(df)) == 25
    assert evaluate("count(a)", ns(df)) == 4
    assert evaluate("sum(a) / sum(b)", ns(df)) == pytest.approx(0.1)
    assert evaluate("max(b) - min(b)", ns(df)) == 30


def test_comparisons_and_boolean_logic(df):
    assert list(evaluate("a > 2", ns(df))) == [False, False, True, True]
    assert list(evaluate("a > 1 and b < 40", ns(df))) == [False, True, True, False]
    assert list(evaluate("a == 1 or a == 4", ns(df))) == [True, False, False, True]
    assert list(evaluate("not (a > 2)", ns(df))) == [True, True, False, False]
    assert list(evaluate("g == 'x'", ns(df))) == [True, False, True, False]


def test_sum_of_a_condition_counts_rows(df):
    assert evaluate("sum(a > 2)", ns(df)) == 2


def test_where_and_math_functions(df):
    assert list(evaluate("where(a > 2, 1, 0)", ns(df))) == [0, 0, 1, 1]
    assert evaluate("sqrt(16)", {}) == 4
    assert evaluate("log(exp(2))", {}) == pytest.approx(2)
    assert evaluate("abs(-3)", {}) == 3


def test_division_by_zero_gives_inf_not_an_exception(df):
    out = evaluate("a / 0", ns(df))
    assert np.isinf(out).all()


@pytest.mark.parametrize(
    "bad",
    [
        "__import__('os').system('echo hi')",
        "a.__class__",
        "open('x')",
        "a[0]",
        "lambda: 1",
        "[1, 2]",
        "(1).real",
        "exec('1')",
        "a if a else b",
    ],
)
def test_unsafe_or_unsupported_expressions_are_rejected(df, bad):
    with pytest.raises(ExpressionError):
        evaluate(bad, ns(df))


def test_unknown_name_is_reported_with_choices(df):
    with pytest.raises(ExpressionError, match="unknown name 'zzz'"):
        evaluate("zzz + 1", ns(df))


def test_syntax_error_is_wrapped():
    with pytest.raises(ExpressionError, match="cannot parse"):
        evaluate("1 +", {})


def test_function_arity_is_checked():
    with pytest.raises(ExpressionError, match="argument"):
        evaluate("sqrt(1, 2)", {})


def test_overlong_expression_rejected():
    with pytest.raises(ExpressionError, match="too long"):
        evaluate("1 + " * 400 + "1", {})
