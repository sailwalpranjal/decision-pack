from __future__ import annotations

import itertools
import math

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from decisionpack.core.bridge import (
    funnel_cost_factors,
    order_sensitivity,
    product_metric,
    sequential_bridge,
    shapley_bridge,
    shapley_by_permutations,
)

positive = st.floats(min_value=0.01, max_value=1000, allow_nan=False, allow_infinity=False)


def scale(base, comp) -> float:
    """Magnitude of the metric at either end, so tolerances track float rounding."""
    return max(1.0, abs(product_metric(base)), abs(product_metric(comp)))


def factor_dicts(n: int):
    names = [f"f{i}" for i in range(n)]
    return st.tuples(
        st.fixed_dictionaries(dict.fromkeys(names, positive)),
        st.fixed_dictionaries(dict.fromkeys(names, positive)),
    )


# ---- closed forms -------------------------------------------------------------------------


def test_two_factor_shapley_closed_form():
    a0, b0, a1, b1 = 2.0, 5.0, 3.0, 11.0
    bridge = shapley_bridge({"a": a0, "b": b0}, {"a": a1, "b": b1})
    assert bridge.attributions["a"] == pytest.approx((a1 - a0) * (b0 + b1) / 2)
    assert bridge.attributions["b"] == pytest.approx((b1 - b0) * (a0 + a1) / 2)
    assert bridge.total_gap == pytest.approx(a1 * b1 - a0 * b0)


def test_two_factor_sequential_closed_form():
    a0, b0, a1, b1 = 2.0, 5.0, 3.0, 11.0
    ab = sequential_bridge({"a": a0, "b": b0}, {"a": a1, "b": b1}, order=["a", "b"])
    assert ab.attributions["a"] == pytest.approx((a1 - a0) * b0)
    assert ab.attributions["b"] == pytest.approx(a1 * (b1 - b0))
    ba = sequential_bridge({"a": a0, "b": b0}, {"a": a1, "b": b1}, order=["b", "a"])
    assert ba.attributions["b"] == pytest.approx((b1 - b0) * a0)
    assert ba.attributions["a"] == pytest.approx(b1 * (a1 - a0))


def test_sequential_split_depends_on_order_but_shapley_does_not():
    base = {"a": 2.0, "b": 5.0, "c": 0.5}
    comp = {"a": 3.0, "b": 11.0, "c": 0.9}
    seen = {
        tuple(round(v, 9) for v in sequential_bridge(base, comp, o).attributions.values())
        for o in itertools.permutations(base)
    }
    assert len(seen) > 1
    ref = shapley_bridge(base, comp).attributions
    permuted = {k: base[k] for k in ["c", "a", "b"]}, {k: comp[k] for k in ["c", "a", "b"]}
    again = shapley_bridge(*permuted).attributions
    for k in ref:
        assert again[k] == pytest.approx(ref[k], rel=1e-12)


def test_unchanged_factor_gets_zero():
    bridge = shapley_bridge({"a": 2.0, "b": 5.0}, {"a": 2.0, "b": 9.0})
    assert bridge.attributions["a"] == pytest.approx(0.0, abs=1e-12)
    assert bridge.attributions["b"] == pytest.approx(bridge.total_gap)


def test_identical_segments_have_zero_gap_and_nan_shares():
    bridge = shapley_bridge({"a": 2.0, "b": 5.0}, {"a": 2.0, "b": 5.0})
    assert bridge.total_gap == 0
    assert all(math.isnan(v) for v in bridge.shares().values())


def test_single_factor_gets_the_whole_gap():
    bridge = shapley_bridge({"x": 4.0}, {"x": 10.0})
    assert bridge.attributions == {"x": pytest.approx(6.0)}


def test_non_product_metric_is_supported():
    def metric(f):
        return f["a"] * f["b"] + f["c"]

    base = {"a": 1.0, "b": 2.0, "c": 3.0}
    comp = {"a": 2.0, "b": 4.0, "c": 1.0}
    bridge = shapley_bridge(base, comp, metric)
    assert sum(bridge.attributions.values()) == pytest.approx(metric(comp) - metric(base))
    # c enters additively, so its attribution is exactly its own change
    assert bridge.attributions["c"] == pytest.approx(-2.0)


def test_subset_form_matches_permutation_form():
    base = {"a": 2.0, "b": 5.0, "c": 0.5, "d": 1.7}
    comp = {"a": 3.0, "b": 11.0, "c": 0.9, "d": 0.4}
    fast = shapley_bridge(base, comp).attributions
    slow = shapley_by_permutations(base, comp).attributions
    for k in base:
        assert fast[k] == pytest.approx(slow[k], rel=1e-10)


# ---- properties ---------------------------------------------------------------------------


@settings(max_examples=200, deadline=None)
@given(factor_dicts(3))
def test_property_shapley_sums_to_gap(pair):
    base, comp = pair
    bridge = shapley_bridge(base, comp)
    gap = product_metric(comp) - product_metric(base)
    tol = 1e-9 * scale(base, comp)
    assert sum(bridge.attributions.values()) == pytest.approx(gap, abs=tol)
    assert abs(bridge.residual) <= tol


@settings(max_examples=200, deadline=None)
@given(factor_dicts(4), st.randoms(use_true_random=False))
def test_property_shapley_invariant_to_factor_order(pair, rnd):
    base, comp = pair
    keys = list(base)
    ref = shapley_bridge(base, comp).attributions
    rnd.shuffle(keys)
    shuffled = shapley_bridge({k: base[k] for k in keys}, {k: comp[k] for k in keys}).attributions
    tol = 1e-9 * scale(base, comp)
    for k in ref:
        assert shuffled[k] == pytest.approx(ref[k], abs=tol)


@settings(max_examples=150, deadline=None)
@given(factor_dicts(4), st.randoms(use_true_random=False))
def test_property_sequential_sums_to_gap_for_any_order(pair, rnd):
    base, comp = pair
    order = list(base)
    rnd.shuffle(order)
    bridge = sequential_bridge(base, comp, order)
    gap = product_metric(comp) - product_metric(base)
    assert sum(bridge.attributions.values()) == pytest.approx(gap, abs=1e-9 * scale(base, comp))


@settings(max_examples=100, deadline=None)
@given(factor_dicts(3))
def test_property_swapping_segments_negates_attributions(pair):
    base, comp = pair
    forward = shapley_bridge(base, comp).attributions
    backward = shapley_bridge(comp, base).attributions
    for k in forward:
        assert backward[k] == pytest.approx(-forward[k], abs=1e-9 * scale(base, comp))


@settings(max_examples=100, deadline=None)
@given(factor_dicts(3))
def test_property_average_over_orders_is_shapley(pair):
    base, comp = pair
    fast = shapley_bridge(base, comp).attributions
    slow = shapley_by_permutations(base, comp).attributions
    for k in fast:
        assert fast[k] == pytest.approx(slow[k], abs=1e-9 * scale(base, comp))


# ---- input checks -------------------------------------------------------------------------


def test_mismatched_factor_names_rejected():
    with pytest.raises(ValueError, match="same factors"):
        shapley_bridge({"a": 1.0}, {"b": 1.0})


def test_empty_factors_rejected():
    with pytest.raises(ValueError, match="at least one"):
        shapley_bridge({}, {})


def test_non_finite_rejected():
    with pytest.raises(ValueError, match="not finite"):
        shapley_bridge({"a": math.nan}, {"a": 1.0})


def test_bad_order_rejected():
    with pytest.raises(ValueError, match="permutation"):
        sequential_bridge({"a": 1.0, "b": 2.0}, {"a": 2.0, "b": 3.0}, order=["a"])


def test_too_many_factors_rejected():
    big = {f"f{i}": 1.0 for i in range(17)}
    with pytest.raises(ValueError, match="limited to 16"):
        shapley_bridge(big, big)


def test_funnel_cost_factors_multiply_back_to_cost_per_outcome():
    f = funnel_cost_factors(1000.0, [("impressions", 1e6), ("clicks", 2e3), ("approved", 40.0)])
    assert math.prod(f.values()) == pytest.approx(1000.0 / 40.0)
    assert list(f) == ["cost_per_impressions", "impressions_per_clicks", "clicks_per_approved"]


def test_funnel_cost_factors_validation():
    with pytest.raises(ValueError, match="two stages"):
        funnel_cost_factors(1.0, [("a", 1.0)])
    with pytest.raises(ValueError, match="non-positive"):
        funnel_cost_factors(1.0, [("a", 1.0), ("b", 0.0)])


# ---- regression: the funnel lab numbers ---------------------------------------------------


def _funnel_factors(df: pd.DataFrame, campaign: str) -> dict[str, float]:
    s = df[df["campaign"] == campaign]
    return funnel_cost_factors(
        float(s["spent"].sum()),
        [
            ("impressions", float(s["impressions"].sum())),
            ("clicks", float(s["clicks"].sum())),
            ("approved", float(s["approved"].sum())),
        ],
    )


def test_funnel_lab_regression(funnel_df: pd.DataFrame):
    """936 vs 1178: $15.81 vs $63.83, a $48.02 gap. The old split next to the Shapley split."""
    n = funnel_df.groupby("campaign").size()
    assert (int(n["936"]), int(n["1178"])) == (464, 625)  # ad sets; campaigns, not rows, differ
    base = _funnel_factors(funnel_df, "936")
    comp = _funnel_factors(funnel_df, "1178")

    seq = sequential_bridge(base, comp)  # CPM, CTR, conversion: the order the lab used
    assert math.prod(base.values()) == pytest.approx(15.81, abs=0.005)
    assert math.prod(comp.values()) == pytest.approx(63.83, abs=0.005)
    assert seq.total_gap == pytest.approx(48.02, abs=0.005)
    vals = list(seq.attributions.values())
    assert vals == [
        pytest.approx(-3.74, abs=0.005),
        pytest.approx(4.66, abs=0.005),
        pytest.approx(47.10, abs=0.005),
    ]

    sh = shapley_bridge(base, comp)
    svals = list(sh.attributions.values())
    assert svals == [
        pytest.approx(-11.08, abs=0.005),
        pytest.approx(12.62, abs=0.005),
        pytest.approx(46.48, abs=0.005),
    ]
    assert sum(svals) == pytest.approx(48.02, abs=0.005)
    assert sh.shares()["clicks_per_approved"] == pytest.approx(0.968, abs=0.0005)
    assert seq.shares()["clicks_per_approved"] == pytest.approx(0.981, abs=0.0005)


def test_funnel_lab_order_sensitivity(funnel_df: pd.DataFrame):
    sens = order_sensitivity(_funnel_factors(funnel_df, "936"), _funnel_factors(funnel_df, "1178"))
    assert sens.n_orders == 6
    assert sens.min_share["clicks_per_approved"] == pytest.approx(0.708, abs=0.0005)
    assert sens.max_share["clicks_per_approved"] == pytest.approx(1.285, abs=0.0005)
    s = sens.shapley_share["clicks_per_approved"]
    assert sens.min_share["clicks_per_approved"] < s < sens.max_share["clicks_per_approved"]
