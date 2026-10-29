"""Driver decomposition of the gap between two segments.

A metric that is a product (or any function) of factors changes between a baseline
segment and a comparison segment. The gap has to be split between the factors.

Sequential substitution swaps one factor at a time, so the answer depends on the order
in which factors are swapped. Shapley attribution averages each factor's marginal effect
over every order, which removes that dependence. Both split the gap exactly: the parts
sum to ``metric(comparison) - metric(baseline)``.

Shapley still depends on how the metric is factored. Writing cost per conversion as
CPM x 1/CTR x 1/conversion is a modelling choice and a different factorisation gives
different numbers.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

Factors = Mapping[str, float]
MetricFn = Callable[[Factors], float]

MAX_SHAPLEY_FACTORS = 16
MAX_ORDER_SCAN_FACTORS = 8


def product_metric(factors: Factors) -> float:
    """The usual case: the metric is the product of its factors."""
    return math.prod(factors.values())


@dataclass(frozen=True)
class Bridge:
    """Result of splitting a gap between factors."""

    method: str
    factors: tuple[str, ...]
    baseline_value: float
    comparison_value: float
    attributions: dict[str, float]
    order: tuple[str, ...] | None = None  # set for sequential bridges

    @property
    def total_gap(self) -> float:
        return self.comparison_value - self.baseline_value

    @property
    def residual(self) -> float:
        return self.total_gap - sum(self.attributions.values())

    def shares(self) -> dict[str, float]:
        gap = self.total_gap
        if gap == 0:
            return {k: math.nan for k in self.attributions}
        return {k: v / gap for k, v in self.attributions.items()}


@dataclass(frozen=True)
class OrderSensitivity:
    """How much a factor's share of the gap moves with the substitution order."""

    min_share: dict[str, float]
    max_share: dict[str, float]
    n_orders: int
    shapley_share: dict[str, float] = field(default_factory=dict)


def _check(baseline: Factors, comparison: Factors) -> tuple[str, ...]:
    if set(baseline) != set(comparison):
        raise ValueError(
            f"baseline and comparison need the same factors; got {sorted(baseline)} "
            f"and {sorted(comparison)}"
        )
    if not baseline:
        raise ValueError("at least one factor is required")
    for name, value in (*baseline.items(), *comparison.items()):
        if not math.isfinite(value):
            raise ValueError(f"factor {name!r} is not finite: {value}")
    return tuple(baseline)


def sequential_bridge(
    baseline: Factors,
    comparison: Factors,
    order: Sequence[str] | None = None,
    metric: MetricFn = product_metric,
) -> Bridge:
    """Swap factors from baseline to comparison one at a time, in ``order``.

    The first factor in ``order`` is swapped while all others are still at baseline, and so on.
    """
    names = _check(baseline, comparison)
    chosen = tuple(order) if order is not None else names
    if sorted(chosen) != sorted(names):
        raise ValueError(f"order must be a permutation of {sorted(names)}; got {list(chosen)}")
    current = dict(baseline)
    previous = metric(current)
    base_value = previous
    parts: dict[str, float] = {}
    for name in chosen:
        current[name] = comparison[name]
        now = metric(current)
        parts[name] = now - previous
        previous = now
    return Bridge(
        method="sequential",
        factors=names,
        baseline_value=base_value,
        comparison_value=previous,
        attributions={n: parts[n] for n in names},
        order=chosen,
    )


def shapley_bridge(
    baseline: Factors,
    comparison: Factors,
    metric: MetricFn = product_metric,
) -> Bridge:
    """Order-independent attribution using the subset form of the Shapley value.

    For factor i, the attribution is the weighted average, over every subset S of the other
    factors, of ``metric(S + i at comparison) - metric(S at comparison)``, with weight
    ``|S|! (n - |S| - 1)! / n!``. That equals the average over all n! orderings.
    """
    names = _check(baseline, comparison)
    n = len(names)
    if n > MAX_SHAPLEY_FACTORS:
        raise ValueError(f"exact Shapley is limited to {MAX_SHAPLEY_FACTORS} factors; got {n}")

    cache: dict[int, float] = {}

    def value(mask: int) -> float:
        if mask not in cache:
            point = {
                name: comparison[name] if mask >> i & 1 else baseline[name]
                for i, name in enumerate(names)
            }
            cache[mask] = metric(point)
        return cache[mask]

    n_fact = math.factorial(n)
    attributions: dict[str, float] = {}
    for i, name in enumerate(names):
        others = [j for j in range(n) if j != i]
        total = 0.0
        for size in range(n):
            weight = math.factorial(size) * math.factorial(n - size - 1) / n_fact
            for subset in itertools.combinations(others, size):
                mask = sum(1 << j for j in subset)
                total += weight * (value(mask | 1 << i) - value(mask))
        attributions[name] = total

    return Bridge(
        method="shapley",
        factors=names,
        baseline_value=value(0),
        comparison_value=value((1 << n) - 1),
        attributions=attributions,
    )


def shapley_by_permutations(
    baseline: Factors,
    comparison: Factors,
    metric: MetricFn = product_metric,
) -> Bridge:
    """Shapley by explicit averaging over every order. Slower; used to check the subset form."""
    names = _check(baseline, comparison)
    if len(names) > MAX_ORDER_SCAN_FACTORS:
        raise ValueError(f"permutation form is limited to {MAX_ORDER_SCAN_FACTORS} factors")
    totals = dict.fromkeys(names, 0.0)
    orders = list(itertools.permutations(names))
    for order in orders:
        bridge = sequential_bridge(baseline, comparison, order, metric)
        for name, part in bridge.attributions.items():
            totals[name] += part
    count = len(orders)
    return Bridge(
        method="shapley-permutations",
        factors=names,
        baseline_value=metric(baseline),
        comparison_value=metric(comparison),
        attributions={n: totals[n] / count for n in names},
    )


def order_sensitivity(
    baseline: Factors,
    comparison: Factors,
    metric: MetricFn = product_metric,
) -> OrderSensitivity:
    """Range of each factor's share of the gap across every substitution order."""
    names = _check(baseline, comparison)
    if len(names) > MAX_ORDER_SCAN_FACTORS:
        raise ValueError(f"order scan is limited to {MAX_ORDER_SCAN_FACTORS} factors")
    lows = dict.fromkeys(names, math.inf)
    highs = dict.fromkeys(names, -math.inf)
    count = 0
    for order in itertools.permutations(names):
        shares = sequential_bridge(baseline, comparison, order, metric).shares()
        for name, share in shares.items():
            lows[name] = min(lows[name], share)
            highs[name] = max(highs[name], share)
        count += 1
    return OrderSensitivity(
        min_share=lows,
        max_share=highs,
        n_orders=count,
        shapley_share=shapley_bridge(baseline, comparison, metric).shares(),
    )


def funnel_cost_factors(
    spend: float,
    stages: Sequence[tuple[str, float]],
) -> dict[str, float]:
    """Factors for cost per final-stage outcome in a funnel.

    ``stages`` is the funnel from the top, for example
    ``[("impressions", 1e6), ("clicks", 2e3), ("enquiries", 150), ("approved", 40)]``.
    Cost per approved = spend/impressions x impressions/clicks x clicks/enquiries x
    enquiries/approved. Each factor is named for what it measures:
    ``cost_per_impressions``, ``impressions_per_clicks`` and so on.
    """
    if len(stages) < 2:
        raise ValueError("a funnel needs at least two stages")
    for name, count in stages:
        if count <= 0:
            raise ValueError(f"stage {name!r} has non-positive count {count}")
    factors = {f"cost_per_{stages[0][0]}": spend / stages[0][1]}
    for (upper, upper_n), (lower, lower_n) in itertools.pairwise(stages):
        factors[f"{upper}_per_{lower}"] = upper_n / lower_n
    return factors
