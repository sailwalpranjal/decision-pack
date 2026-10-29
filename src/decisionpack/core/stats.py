"""Statistics used by the rest of the package.

The formulas are written out here so they can be read and checked. Every function has a test
that compares it with SciPy or statsmodels, which are test-only dependencies.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm

Alternative = Literal["two-sided", "larger", "smaller"]
PowerMethod = Literal["arcsine", "normal"]


def _check_conf(conf: float) -> None:
    if not 0.0 < conf < 1.0:
        raise ValueError(f"conf must be in (0, 1); got {conf}")


# ---- two-proportion z-test ----------------------------------------------------------------


@dataclass(frozen=True)
class ZTestResult:
    """Test of ``p2 - p1``. ``larger`` means group 2 has the higher rate."""

    statistic: float
    p_value: float
    p1: float
    p2: float
    diff: float
    ci_low: float
    ci_high: float
    alternative: str


def two_proportion_ztest(
    x1: int,
    n1: int,
    x2: int,
    n2: int,
    *,
    alternative: Alternative = "two-sided",
    pooled: bool = True,
    conf: float = 0.95,
) -> ZTestResult:
    """z-test for the difference between two proportions, group 2 minus group 1.

    The statistic uses the pooled standard error under the null by default. The confidence
    interval for the difference always uses the unpooled (Wald) standard error.
    """
    for x, n in ((x1, n1), (x2, n2)):
        if n <= 0:
            raise ValueError(f"sample size must be positive; got {n}")
        if not 0 <= x <= n:
            raise ValueError(f"successes must be between 0 and n; got {x} of {n}")
    if alternative not in ("two-sided", "larger", "smaller"):
        raise ValueError(f"unknown alternative {alternative!r}")
    _check_conf(conf)

    p1, p2 = x1 / n1, x2 / n2
    diff = p2 - p1
    if pooled:
        p = (x1 + x2) / (n1 + n2)
        se0 = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    else:
        se0 = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    if se0 == 0:
        raise ValueError("standard error is zero (both groups are all successes or all failures)")
    z = diff / se0
    if alternative == "two-sided":
        p_value = 2 * float(norm.sf(abs(z)))
    elif alternative == "larger":
        p_value = float(norm.sf(z))
    else:
        p_value = float(norm.cdf(z))

    se_wald = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    crit = float(norm.ppf(1 - (1 - conf) / 2))
    return ZTestResult(
        z, p_value, p1, p2, diff, diff - crit * se_wald, diff + crit * se_wald, alternative
    )


def wilson_interval(x: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        raise ValueError(f"n must be positive; got {n}")
    if not 0 <= x <= n:
        raise ValueError(f"x must be between 0 and n; got {x} of {n}")
    _check_conf(conf)
    z = float(norm.ppf(1 - (1 - conf) / 2))
    phat = x / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    # At the edges the exact limits are 0 and 1; rounding can leave 1e-17 of slack.
    lo = 0.0 if x == 0 else max(0.0, centre - half)
    hi = 1.0 if x == n else min(1.0, centre + half)
    return lo, hi


# ---- bootstrap ----------------------------------------------------------------------------


def bootstrap_ci(
    data: ArrayLike,
    statistic: Callable[[NDArray[np.float64]], float] = np.mean,
    *,
    n_boot: int = 2000,
    conf: float = 0.95,
    seed: int | None = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for ``statistic`` of one sample."""
    arr = np.asarray(data, dtype=float)
    if arr.size == 0:
        raise ValueError("data is empty")
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    _check_conf(conf)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    stats = np.fromiter((statistic(arr[row]) for row in idx), dtype=float, count=n_boot)
    lo, hi = np.quantile(stats, [(1 - conf) / 2, 1 - (1 - conf) / 2])
    return float(lo), float(hi)


def _into_blocks(
    num: NDArray[np.float64], den: NDArray[np.float64], k: int, rng: np.random.Generator
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Add rows into ``k`` random blocks so a huge sample can be bootstrapped cheaply."""
    assignment = rng.integers(0, k, size=num.size)
    return (
        np.bincount(assignment, weights=num, minlength=k),
        np.bincount(assignment, weights=den, minlength=k),
    )


def _resampled_ratio(
    num: NDArray[np.float64], den: NDArray[np.float64], idx: NDArray[np.int64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    return num[idx].sum(axis=1), den[idx].sum(axis=1)


def bootstrap_ratio_gap_ci(
    num_a: ArrayLike,
    den_a: ArrayLike,
    num_b: ArrayLike,
    den_b: ArrayLike,
    *,
    n_boot: int = 2000,
    conf: float = 0.95,
    seed: int | None = 0,
    max_rows: int = 20_000,
    n_blocks: int = 2_000,
) -> tuple[float, float, float]:
    """Gap in a ratio of sums, group B minus group A, with a percentile bootstrap interval.

    Each input is one value per row (ad set, customer, ...). Rows are resampled within their
    group, which respects that the rows, not the individual events, are the units that vary.
    A group with more than ``max_rows`` rows is first added into ``n_blocks`` random blocks and
    the blocks are resampled; for independent rows that gives nearly the same interval at a
    fraction of the cost. Returns ``(gap, low, high)``; the gap is always from the full data.
    """
    na, da = np.asarray(num_a, float), np.asarray(den_a, float)
    nb, db = np.asarray(num_b, float), np.asarray(den_b, float)
    if na.shape != da.shape or nb.shape != db.shape:
        raise ValueError("numerator and denominator must have the same length in each group")
    if na.size == 0 or nb.size == 0:
        raise ValueError("each group needs at least one row")
    if da.sum() <= 0 or db.sum() <= 0:
        raise ValueError("denominator totals must be positive")
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    _check_conf(conf)

    rng = np.random.default_rng(seed)
    point = float(nb.sum() / db.sum() - na.sum() / da.sum())
    if na.size > max_rows:
        na, da = _into_blocks(na, da, n_blocks, rng)
    if nb.size > max_rows:
        nb, db = _into_blocks(nb, db, n_blocks, rng)

    chunk = max(1, int(8_000_000 // max(na.size, nb.size)))
    gaps: list[NDArray[np.float64]] = []
    done = 0
    while done < n_boot:
        m = min(chunk, n_boot - done)
        ia = rng.integers(0, na.size, size=(m, na.size))
        ib = rng.integers(0, nb.size, size=(m, nb.size))
        sn_a, sd_a = _resampled_ratio(na, da, ia)
        sn_b, sd_b = _resampled_ratio(nb, db, ib)
        ok = (sd_a > 0) & (sd_b > 0)
        gaps.append(sn_b[ok] / sd_b[ok] - sn_a[ok] / sd_a[ok])
        done += m
    all_gaps = np.concatenate(gaps)
    lo, hi = np.quantile(all_gaps, [(1 - conf) / 2, 1 - (1 - conf) / 2])
    return point, float(lo), float(hi)


# ---- power and sample size ----------------------------------------------------------------


def _check_rates(p1: float, p2: float) -> None:
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError(f"rates must be strictly between 0 and 1; got {p1} and {p2}")
    if p1 == p2:
        raise ValueError("the two rates are equal, so no sample size detects a difference")


def _cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p2)) - 2 * math.asin(math.sqrt(p1))


def sample_size_two_proportions(
    p1: float,
    p2: float,
    *,
    alpha: float = 0.05,
    power: float = 0.8,
    method: PowerMethod = "arcsine",
) -> int:
    """Per-group sample size to detect ``p1`` against ``p2`` with a two-sided z-test.

    ``arcsine`` uses Cohen's h, the same approximation as statsmodels. ``normal`` uses the
    pooled/unpooled variance formula found in most textbooks.
    """
    _check_rates(p1, p2)
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not 0 < power < 1:
        raise ValueError("power must be in (0, 1)")
    za = float(norm.ppf(1 - alpha / 2))
    zb = float(norm.ppf(power))
    if method == "arcsine":
        n = 2 * ((za + zb) / _cohens_h(p1, p2)) ** 2
    elif method == "normal":
        pbar = (p1 + p2) / 2
        num = za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        n = (num / (p2 - p1)) ** 2
    else:
        raise ValueError(f"unknown method {method!r}")
    return math.ceil(n)


def power_two_proportions(
    p1: float,
    p2: float,
    n: int,
    *,
    alpha: float = 0.05,
    method: PowerMethod = "arcsine",
) -> float:
    """Power of a two-sided two-proportion z-test with ``n`` per group."""
    _check_rates(p1, p2)
    if n <= 0:
        raise ValueError("n must be positive")
    za = float(norm.ppf(1 - alpha / 2))
    if method == "arcsine":
        effect = abs(_cohens_h(p1, p2)) * math.sqrt(n / 2)
        return float(norm.sf(za - effect) + norm.cdf(-za - effect))
    if method == "normal":
        pbar = (p1 + p2) / 2
        se0 = math.sqrt(2 * pbar * (1 - pbar) / n)
        se1 = math.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / n)
        d = abs(p2 - p1)
        return float(norm.sf((za * se0 - d) / se1) + norm.cdf((-za * se0 - d) / se1))
    raise ValueError(f"unknown method {method!r}")


# ---- multiple comparisons -----------------------------------------------------------------


def _check_p(ps: Sequence[float]) -> None:
    for p in ps:
        if not 0.0 <= p <= 1.0 or math.isnan(p):
            raise ValueError(f"p-values must be in [0, 1]; got {p}")


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values (family-wise error control)."""
    ps = list(p_values)
    _check_p(ps)
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * ps[i]))
        adjusted[i] = running
    return adjusted


def benjamini_hochberg_adjust(p_values: Iterable[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (false discovery rate control)."""
    ps = list(p_values)
    _check_p(ps)
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for offset, i in enumerate(order):
        rank = m - offset
        running = min(running, ps[i] * m / rank)
        adjusted[i] = min(1.0, running)
    return adjusted


# ---- sequential test ----------------------------------------------------------------------


@dataclass(frozen=True)
class SprtResult:
    decision: Literal["accept_h0", "accept_h1", "continue"]
    llr: float
    lower_bound: float
    upper_bound: float
    n_used: int


def sprt_bernoulli(
    observations: Iterable[int | bool | float],
    p0: float,
    p1: float,
    alpha: float = 0.05,
    beta: float = 0.2,
) -> SprtResult:
    """Wald's sequential probability ratio test of ``p = p0`` against ``p = p1`` (p1 > p0).

    Walk through the 0/1 observations and stop at the first crossing of a boundary. Anything
    after the stopping point is ignored. If neither boundary is crossed the result is
    ``continue``.
    """
    if not 0 < p0 < p1 < 1:
        raise ValueError("need 0 < p0 < p1 < 1")
    if not (0 < alpha < 1 and 0 < beta < 1):
        raise ValueError("alpha and beta must be in (0, 1)")
    lower = math.log(beta / (1 - alpha))
    upper = math.log((1 - beta) / alpha)
    win = math.log(p1 / p0)
    lose = math.log((1 - p1) / (1 - p0))
    llr = 0.0
    used = 0
    for obs in observations:
        if obs not in (0, 1):
            raise ValueError(f"observations must be 0 or 1; got {obs!r}")
        used += 1
        llr += win if obs else lose
        if llr >= upper:
            return SprtResult("accept_h1", llr, lower, upper, used)
        if llr <= lower:
            return SprtResult("accept_h0", llr, lower, upper, used)
    return SprtResult("continue", llr, lower, upper, used)
